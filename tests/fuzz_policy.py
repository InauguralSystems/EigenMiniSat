#!/usr/bin/env python3
"""Policy-differential fuzzer -- targets the clause-DB reduction, physical
compaction and watch-rebuild machinery that the small-instance fuzzer never
reaches (0 of 180 instances hit compaction).

A heuristic policy must never change the ANSWER, only the search. So:
  * every policy combination must agree on SAT/UNSAT
  * SAT   -> that policy's model must satisfy every clause
  * UNSAT -> that policy's DRAT proof must verify

Instances are sized to be conflict-rich (near-threshold random 3-SAT plus
pigeonhole), and eager compaction is included precisely because it forces
compact_runs / watch_rebuilds / compact_replays on small inputs -- that is the
reason-pointer remapping path.
"""
import random, subprocess, sys, os, tempfile

ROOT = os.environ.get("EIGENMINISAT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT_BIN") or os.path.join(ROOT, "..", "EigenScript", "src", "eigenscript")
DTRIM = os.environ.get("DRAT_TRIM") or "drat-trim"

POLICIES = [
    (["--compact-policy", "deferred"], "deferred"),
    (["--compact-policy", "eager"], "eager"),
    (["--compact-policy", "lazy"], "lazy"),
    (["--compact-policy", "eager", "--restart-policy", "luby"], "eager+luby"),
    (["--compact-policy", "eager", "--phase-policy", "negative"], "eager+neg"),
    (["--compact-policy", "lazy", "--restart-policy", "luby", "--phase-policy", "positive"], "lazy+luby+pos"),
]


def php(pigeons, holes):
    v = lambda p, h: p * holes + h + 1
    cl = [[v(p, h) for h in range(holes)] for p in range(pigeons)]
    for p in range(pigeons):
        for a in range(holes):
            for b in range(a + 1, holes):
                cl.append([-v(p, a), -v(p, b)])
    for h in range(holes):
        for a in range(pigeons):
            for b in range(a + 1, pigeons):
                cl.append([-v(a, h), -v(b, h)])
    return pigeons * holes, cl


def gen(rng, i):
    if i % 4 == 3:
        n = rng.choice([4, 5, 6])
        return php(n + 1, n)
    n = rng.randint(16, 28)
    m = int(n * rng.uniform(4.0, 4.7))
    cl = []
    for _ in range(m):
        vs = rng.sample(range(1, n + 1), 3)
        cl.append([v if rng.random() < 0.5 else -v for v in vs])
    return n, cl


def write_cnf(path, n, cl):
    with open(path, "w") as f:
        f.write(f"c policy fuzz\np cnf {n} {len(cl)}\n")
        for c in cl:
            f.write(" ".join(map(str, c)) + " 0\n")


def run(pol, cnf, proof=None):
    cmd = [EIGS, "minisat.eigs", "--cdcl", "--model"] + pol
    if proof:
        cmd += ["--proof", proof]
    cmd.append(cnf)
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    out = p.stdout
    st = "SAT" if "s SATISFIABLE" in out else ("UNSAT" if "s UNSATISFIABLE" in out else f"ERR{p.returncode}")
    return st, out


def counter(out, name):
    for tok in out.split():
        if tok.startswith(name + "="):
            return int(tok.split("=")[1])
    return 0


def main():
    seed0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    work = tempfile.mkdtemp(prefix="eigpolfuzz-", dir=os.environ.get("FUZZ_WORKDIR") or tempfile.gettempdir())
    fails, cov = [], {"compact": 0, "reduce": 0, "rebuild": 0, "replay": 0}
    nsat = nunsat = nver = 0
    for i in range(count):
        rng = random.Random(seed0 + i)
        n, cl = gen(rng, i)
        cnf = os.path.join(work, f"p{i}.cnf")
        write_cnf(cnf, n, cl)
        verdicts = {}
        for pol, name in POLICIES:
            try:
                st, out = run(pol, cnf)
            except subprocess.TimeoutExpired:
                st, out = "TIMEOUT", ""
            verdicts[name] = st
            if st.startswith("ERR") or st == "TIMEOUT":
                fails.append((i, f"{name} -> {st}", cnf))
                continue
            if counter(out, "compact_runs") > 0:
                cov["compact"] += 1
            if counter(out, "reduce_runs") > 0:
                cov["reduce"] += 1
            if counter(out, "watch_rebuilds") > 0:
                cov["rebuild"] += 1
            if counter(out, "compact_replays") > 0:
                cov["replay"] += 1
            if st == "SAT":
                vl = [l for l in out.splitlines() if l.startswith("v ")]
                if not vl:
                    fails.append((i, f"{name} SAT no v-line", cnf)); continue
                lits = [int(x) for x in vl[0][2:].split() if x != "0"]
                true_set = {abs(l) for l in lits if l > 0}
                for c in cl:
                    if not any((l > 0 and l in true_set) or (l < 0 and -l not in true_set) for l in c):
                        fails.append((i, f"{name} MODEL FAILS clause {c}", cnf)); break
            else:
                proof = os.path.join(work, f"p{i}.{name.replace('+','_')}.drat")
                st2, _ = run(pol, cnf, proof=proof)
                if st2 != "UNSAT" or not os.path.exists(proof):
                    fails.append((i, f"{name} proof run mismatch", cnf)); continue
                r = subprocess.run([DTRIM, cnf, proof], capture_output=True, text=True, timeout=600)
                if r.returncode != 0:
                    fails.append((i, f"{name} DRAT REJECTED (exit {r.returncode})", cnf))
                else:
                    nver += 1
        u = set(verdicts.values())
        if len(u) > 1:
            fails.append((i, f"POLICY DISAGREEMENT {verdicts}", cnf))
        elif verdicts.get("deferred") == "SAT":
            nsat += 1
        else:
            nunsat += 1
    tot = count * len(POLICIES)
    print(f"instances={count} policies={len(POLICIES)} solves={tot}  SAT={nsat} UNSAT={nunsat} proofs_verified={nver}")
    print(f"coverage (solves hitting path): reduce={cov['reduce']}/{tot} compaction={cov['compact']}/{tot} "
          f"watch_rebuild={cov['rebuild']}/{tot} compact_replay={cov['replay']}/{tot}")
    print(f"failures={len(fails)}")
    for f in fails[:25]:
        print(f"  #{f[0]} {f[1]}\n    {f[2]}")
    print(f"workdir={work}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
