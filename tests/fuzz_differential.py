#!/usr/bin/env python3
"""Differential fuzzer for EigenMiniSat.

Complete correctness oracle:
  * all four solver paths (scan/watched/persistent/cdcl) must agree on SAT/UNSAT
  * SAT  -> the reported model must satisfy every input clause
  * UNSAT -> the DRAT proof must verify with drat-trim

A wrong SAT is caught by the model check; a wrong UNSAT is caught by drat-trim.
So any real soundness bug surfaces as a mismatch, not as silence.

Deliberately includes the shapes that break watched-literal solvers:
tautological clauses (x or ~x), duplicate literals, units, empty-ish inputs,
unused variables, repeated clauses.
"""
import random, subprocess, sys, os, tempfile

ROOT = os.environ.get("EIGENMINISAT_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EIGS = os.environ.get("EIGENSCRIPT_BIN") or os.path.join(ROOT, "..", "EigenScript", "src", "eigenscript")
DTRIM = os.environ.get("DRAT_TRIM") or "drat-trim"
MODES = [([], "scan"), (["--watched"], "watched"), (["--persistent"], "persistent"), (["--cdcl"], "cdcl")]


def gen(rng, kind):
    """Return (nvars, clauses)."""
    if kind == "random3":
        n = rng.randint(3, 14)
        m = int(n * rng.uniform(1.0, 6.0))
        cl = []
        for _ in range(m):
            k = min(3, n)
            vs = rng.sample(range(1, n + 1), k)
            cl.append([v if rng.random() < 0.5 else -v for v in vs])
        return n, cl
    if kind == "mixed_width":
        n = rng.randint(2, 12)
        m = int(n * rng.uniform(1.0, 5.0))
        cl = []
        for _ in range(m):
            k = rng.randint(1, min(5, n))
            vs = rng.sample(range(1, n + 1), k)
            cl.append([v if rng.random() < 0.5 else -v for v in vs])
        return n, cl
    if kind == "tautology":
        # clauses containing both x and ~x, plus duplicate literals
        n = rng.randint(2, 10)
        cl = []
        for _ in range(rng.randint(2, 3 * n)):
            r = rng.random()
            v = rng.randint(1, n)
            if r < 0.3:
                cl.append([v, -v] + ([rng.choice([1, -1]) * rng.randint(1, n)] if n > 1 else []))
            elif r < 0.6:
                cl.append([v, v, -rng.randint(1, n)])
            else:
                k = rng.randint(1, min(3, n))
                vs = rng.sample(range(1, n + 1), k)
                cl.append([x if rng.random() < 0.5 else -x for x in vs])
        return n, cl
    if kind == "unit_heavy":
        n = rng.randint(2, 12)
        cl = []
        for _ in range(rng.randint(1, n)):
            v = rng.randint(1, n)
            cl.append([v if rng.random() < 0.5 else -v])
        for _ in range(rng.randint(1, 3 * n)):
            k = rng.randint(1, min(3, n))
            vs = rng.sample(range(1, n + 1), k)
            cl.append([x if rng.random() < 0.5 else -x for x in vs])
        return n, cl
    if kind == "unused_vars":
        n = rng.randint(4, 14)
        live = max(1, n // 3)
        cl = []
        for _ in range(rng.randint(2, 4 * live)):
            k = rng.randint(1, min(3, live))
            vs = rng.sample(range(1, live + 1), k)
            cl.append([x if rng.random() < 0.5 else -x for x in vs])
        return n, cl
    if kind == "dup_clauses":
        n = rng.randint(2, 10)
        base = []
        for _ in range(rng.randint(2, 2 * n)):
            k = rng.randint(1, min(3, n))
            vs = rng.sample(range(1, n + 1), k)
            base.append([x if rng.random() < 0.5 else -x for x in vs])
        cl = []
        for c in base:
            cl.extend([c] * rng.randint(1, 3))
        return n, cl
    raise ValueError(kind)


def write_cnf(path, n, cl):
    with open(path, "w") as f:
        f.write(f"c fuzz\np cnf {n} {len(cl)}\n")
        for c in cl:
            f.write(" ".join(map(str, c)) + " 0\n")


def run(args, cnf, proof=None, model=False):
    cmd = [EIGS, "minisat.eigs"] + args
    if model:
        cmd.append("--model")
    if proof:
        cmd += ["--proof", proof]
    cmd.append(cnf)
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=120)
    out = p.stdout
    if "s SATISFIABLE" in out:
        return "SAT", out
    if "s UNSATISFIABLE" in out:
        return "UNSAT", out
    return f"ERR(rc={p.returncode})", out + p.stderr


def sat_ok(cl, model_true):
    for c in cl:
        if not any((l > 0 and l in model_true) or (l < 0 and -l not in model_true) for l in c):
            return False, c
    return True, None


def main():
    seed0 = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    kinds = ["random3", "mixed_width", "tautology", "unit_heavy", "unused_vars", "dup_clauses"]
    work = tempfile.mkdtemp(prefix="eigfuzz-", dir=os.environ.get("FUZZ_WORKDIR") or tempfile.gettempdir())
    fails = []
    stats = {"SAT": 0, "UNSAT": 0, "verified": 0}
    for i in range(count):
        rng = random.Random(seed0 + i)
        kind = kinds[i % len(kinds)]
        n, cl = gen(rng, kind)
        cnf = os.path.join(work, f"c{i}.cnf")
        write_cnf(cnf, n, cl)

        verdicts = {}
        for args, name in MODES:
            try:
                v, out = run(args, cnf, model=True)
            except subprocess.TimeoutExpired:
                v, out = "TIMEOUT", ""
            verdicts[name] = v
            if v.startswith("ERR") or v == "TIMEOUT":
                fails.append((i, kind, f"{name} -> {v}", cnf, out[:400]))
                continue
            # every path that says SAT must hand back a model that satisfies
            # every input clause -- this is what catches a wrong SAT
            if v == "SAT":
                vl = [l for l in out.splitlines() if l.startswith("v ")]
                if not vl:
                    fails.append((i, kind, f"{name} SAT but no v-line", cnf, out[:200]))
                    continue
                lits = [int(x) for x in vl[0][2:].split() if x != "0"]
                if len(lits) != n:
                    fails.append((i, kind, f"{name} v-line has {len(lits)} lits, expected {n}", cnf, vl[0][:200]))
                    continue
                true_set = {abs(l) for l in lits if l > 0}
                ok, bad = sat_ok(cl, true_set)
                if not ok:
                    fails.append((i, kind, f"{name} MODEL DOES NOT SATISFY clause {bad}", cnf, vl[0][:200]))

        uniq = set(verdicts.values())
        if len(uniq) > 1:
            fails.append((i, kind, f"PATH DISAGREEMENT {verdicts}", cnf, ""))
            continue

        verdict = verdicts["cdcl"]
        if verdict == "SAT":
            stats["SAT"] += 1
        elif verdict == "UNSAT":
            stats["UNSAT"] += 1
            proof = os.path.join(work, f"c{i}.drat")
            v2, _ = run(["--cdcl"], cnf, proof=proof)
            if v2 != "UNSAT" or not os.path.exists(proof):
                fails.append((i, kind, "proof run disagreed or no proof file", cnf, ""))
                continue
            r = subprocess.run([DTRIM, cnf, proof], capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                fails.append((i, kind, "DRAT REJECTED the refutation", cnf, r.stdout[-400:]))
            else:
                stats["verified"] += 1

    print(f"instances={count}  SAT={stats['SAT']}  UNSAT={stats['UNSAT']}  proofs_verified={stats['verified']}")
    print(f"failures={len(fails)}")
    for f in fails[:25]:
        print(f"  #{f[0]} [{f[1]}] {f[2]}\n    {f[3]}\n    {f[4][:300]}")
    print(f"workdir={work}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
