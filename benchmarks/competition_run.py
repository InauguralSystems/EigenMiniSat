#!/usr/bin/env python3
"""SAT Competition baseline (#131): solved count and PAR-2 per arm, every answer checked.

Arms, in one harness: Kissat, Kissat again (the A/A arm that measures the
runner's wall-clock noise floor), CaDiCaL, MiniSat 2.2 and EigenMiniSat on the
EigenScript VM. Instances: the committed GBD manifest (competition_select.py)
plus the odd Tseitin torus ladder, measured under the same metric in the same
run. Each instance runs every arm consecutively, in a per-instance random order
drawn from a logged seed; the instance order is drawn from the same seed.

Answers: every SAT model is checked against the formula, and every UNSAT answer
from a DRAT-writing arm (Kissat, CaDiCaL, EMS) is checked by drat-trim. As in
the competition, an answer counts as solved only with a completed certificate:
a verified model or a verified refutation. An answer that a certificate or GBD's
recorded result refutes (odd tori are UNSAT by construction) is WRONG and fails
the run (exit 1), whatever the timings. An unverified UNSAT answer is never
solved; when another arm's certificate or GBD's record confirms it, it counts in
a separate cross-checked score, a declared departure. An unverified UNSAT that
nothing confirms or refutes cannot be judged, and counts in neither score.
"""
import argparse
import csv
import hashlib
import json
import lzma
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace
import urllib.request

sys.dont_write_bytecode = True
import certificate_validation as certificates
import cnf_preservation
import compare_native as base
import competition_select as select
from competition_select import key

ROOT = base.ROOT
MANIFEST = select.MANIFEST
FRAME = select.FRAME
ARMS = ("kissat", "kissat-aa", "cadical", "minisat", "ems")
PROOF_ARMS = ("kissat", "kissat-aa", "cadical", "ems")
TOOLS = {"kissat": "kissat", "kissat-aa": "kissat", "cadical": "cadical", "minisat": "minisat", "ems": "eigenscript"}
LADDER = ("3x3", "4x4", "4x5", "4x6", "5x5", "5x6", "6x6")
ANCHORS = {"3x3": ROOT / "tests/fixtures/tseitin_torus_3x3_odd.cnf",
           "4x4": ROOT / "benchmarks/oracle/tseitin_torus_4x4_odd.cnf"}
OVERHEAD = 30  # seconds per instance allowed in the arithmetic for parsing and model checks
FIELDS = ("order", "instance", "kind", "stratum", "family", "expected", "arm", "verdict", "certificate",
          "solved", "wall_s", "par2_s", "solved_crosschecked", "par2_crosschecked_s", "timed_out", "returncode", "note")
VERDICT = {"SATISFIABLE": "SAT", "UNSATISFIABLE": "UNSAT"}
VERIFIED = ("model-verified", "drat-verified")
require = base.require
Failure = base.Failure


def gbd_hash(stream):
    """GBD's instance identity (gbdc CNF::gbdhash): MD5 over the clause tokens joined
    by single spaces, comment and header lines skipped, a final unterminated
    clause closed with 0. Fuzz-tested against gbdc 0.4.3: the only differences
    are files that end without trailing whitespace and skip a comment or header
    line in gbdc's last 16 KiB buffer, whose re-alignment drops the final token.
    Such a file mismatches its manifest hash here and fails; it never passes."""
    digest = hashlib.md5()
    inside = started = seen = False
    plain = re.compile(rb"[ \t\x0b\x0c]*-?[0-9]+(?:[ \t\x0b\x0c]+-?[0-9]+)*[ \t\x0b\x0c\r]*\n?")
    for raw in stream:
        seen = True
        if b"\r" not in raw.rstrip(b"\r\n") and plain.fullmatch(raw):
            tokens = raw.split()
            digest.update((b" " if started else b"") + b" ".join(tokens))
            started, inside = True, tokens[-1] != b"0"
            continue
        for part in raw.split(b"\r"):
            out = []
            for token in part.split():
                if not inside and token[:1] in (b"c", b"p"):
                    break
                if re.fullmatch(rb"[-+]?[0-9]+", token) is None:
                    raise ValueError(f"unexpected DIMACS token {token[:20]!r}")
                token = token[1:] if token[:1] == b"+" else token
                out.append(token)
                inside = token != b"0"
            if out:
                digest.update((b" " if started else b"") + b" ".join(out))
                started = True
    require(seen, "empty CNF")
    if inside:
        digest.update(b" 0")
    return digest.hexdigest()


def download(digest, target, attempts=3):
    url = f"https://benchmark-database.de/file/{digest}"
    partial = target.with_name(target.name + ".part")
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out, 1 << 20)
            os.replace(partial, target)
            return
        except OSError as error:
            if attempt == attempts:
                raise Failure(f"download failed {attempts} times: {url}: {error}") from error
            time.sleep(10 * attempt)


def prepare_gbd(instance, directory, cache):
    """Download by GBD hash, re-derive that hash, then the repo's normalizer and its post-condition."""
    digest = instance["hash"]
    directory.mkdir(parents=True)
    packed = (cache or directory) / f"{digest}.cnf.xz"
    if not packed.is_file():
        download(digest, packed)
    source = directory / "source.cnf"
    try:
        with lzma.open(packed) as stream, source.open("wb") as out:
            shutil.copyfileobj(stream, out, 1 << 20)
    except (lzma.LZMAError, EOFError) as error:
        raise Failure(f"{digest}: {packed} is not a complete .xz file: {error}") from error
    with source.open("rb") as stream:
        actual = gbd_hash(stream)
    require(actual == digest, f"{digest}: the downloaded instance hashes to {actual}")
    normalized = directory / "normalized.cnf"
    with source.open("rb") as stream, normalized.open("wb") as out:
        rc = subprocess.run(["awk", "-f", str(ROOT / "benchmarks/normalize_cnf.awk")], stdin=stream, stdout=out).returncode
    require(rc == 0, f"{digest}: normalize_cnf.awk rc={rc} (65: data after a SATLIB trailer)")
    prepared = directory / "input.cnf"
    strip_comments(normalized, prepared)
    try:
        cnf_preservation.compare(source, prepared)
    except ValueError as error:
        raise Failure(f"{digest}: {error}") from error
    source.unlink()
    normalized.unlink()
    return {"id": digest, "kind": "competition", "stratum": instance["stratum"], "family": instance["family"],
            "expected": instance["gbd_result"], "cnf": prepared}


def prepare_rung(rung, work, vm, environment, deadline, cap):
    """The repo's emitter, identity model, normalizer and preservation check (certificate_validation)."""
    case = certificates.prepare_rung(base, SimpleNamespace(vm=vm, timeout=cap), work, environment, deadline, rung)
    formula = case["cnf"].with_name("formula.cnf")
    strip_comments(case["cnf"], formula)
    try:
        cnf_preservation.compare(case["cnf"], formula)
    except ValueError as error:
        raise Failure(f"tseitin-{rung}-odd: {error}") from error
    return {"id": case["name"], "kind": "ladder", "stratum": "ladder", "family": "tseitin-torus-odd",
            "expected": "unsat", "cnf": formula}


def strip_comments(source, target):
    """Every arm and drat-trim get the formula without comment lines. drat-trim skips
    a comment line only while its binary mode is 0 (drat-trim.c parse); binary
    detection, -i and -I all leave it nonzero, and a comment after the header then
    reads as an empty clause: "c trivial UNSAT", "s VERIFIED", exit 1.
    cnf_preservation.compare checks that only comments went."""
    with Path(source).open("rb") as stream, Path(target).open("wb") as out:
        for line in stream:
            if line.lstrip()[:1] != b"c":
                out.write(line)


def preflight(vm, work, environment, deadline, cap):
    """CLAUDE.md's lane rule: EMS reproduces the regime-C banks byte for byte (excluding ms)."""
    for rung, cnf in ANCHORS.items():
        record = base.run_process([str(vm), str(ROOT / "minisat.eigs"), "--cdcl", str(cnf)],
                                  work / f"preflight-{rung}", base.remaining(deadline, cap), environment)
        require(record["returncode"] == 0, f"regime-C preflight {rung}: EMS exited {record['returncode']}")
        output = base.normalized_ems((work / f"preflight-{rung}/stdout").read_bytes())
        bank = ROOT / f"benchmarks/oracle/regime-c-{rung}.stdout"
        require(output == bank.read_bytes(), f"regime-C preflight {rung}: EMS output differs from {bank.name}")
        print(f"PREFLIGHT {rung}: PASS (regime C, byte-exact excluding ms)", flush=True)


def solver_command(arm, tools, cnf, proof, result):
    if arm == "minisat":
        return [tools["minisat"], cnf, result]
    if arm == "ems":
        return [tools["eigenscript"], ROOT / "minisat.eigs", "--cdcl", "--model", "--proof", proof, cnf]
    return [tools[TOOLS[arm]], cnf, proof]


def interpret(arm, record, directory, proof, result):
    """Verdict SAT/UNSAT/UNKNOWN/TIMEOUT/ERROR plus its certificate material.

    An answer whose exit status and report disagree is an instrument failure; a
    SAT answer whose model cannot be read is kept, and judged wrong."""
    if record["timed_out"]:
        return {"verdict": "TIMEOUT"}
    data = (directory / "stdout").read_bytes()
    rc = record["returncode"]
    tail = (directory / "stderr").read_bytes()[-200:].decode(errors="replace").strip().replace("\n", " | ")
    if arm == "minisat":
        if rc not in (10, 20):
            return {"verdict": "UNKNOWN" if rc == 0 else "ERROR", "note": f"rc={rc} {tail}".strip()}
        verdict = VERDICT[base.native_report(data, result, rc)[0]]
        return with_model(verdict, lambda: result.read_bytes(), "native")
    if arm == "ems":
        if rc != 0:
            return {"verdict": "ERROR", "note": f"rc={rc} {tail}".strip()}
        verdict = VERDICT[base.ems_report(data)[0]]
        if verdict == "UNSAT":
            reports = data.split(b"\n").count(b"c proof written to " + os.fsencode(proof))
            require(reports == 1, f"ems: UNSAT needs exactly one report of {proof}, found {reports}")
        return with_model(verdict, lambda: data, "ems")
    lines = [line.rstrip(b"\r") for line in data.split(b"\n") if line.startswith(b"s ")]
    answer = {10: b"s SATISFIABLE", 20: b"s UNSATISFIABLE"}.get(rc)
    if answer is None:
        require(not set(lines) & {b"s SATISFIABLE", b"s UNSATISFIABLE"}, f"{arm}: an answer line with exit {rc}")
        return {"verdict": "UNKNOWN" if rc == 0 else "ERROR", "note": f"rc={rc} {tail}".strip()}
    require(lines == [answer], f"{arm}: exit {rc} needs exactly the line {answer.decode()}, got {lines}")
    return with_model("SAT" if rc == 10 else "UNSAT", lambda: data, "competition")


def with_model(verdict, read, form):
    if verdict != "SAT":
        return {"verdict": verdict}
    try:
        return {"verdict": verdict, "model": certificates.model_literals(read(), form)}
    except (OSError, ValueError) as error:
        return {"verdict": verdict, "model_error": str(error)}


def check_proof(arm, cnf, proof, directory, ctx):
    """drat-trim's exit status AND its status line: it exits 0 on its own timeout and on
    memory exhaustion (drat-trim.c), so the exit status alone can certify an unchecked proof.

    drat-trim opens argv[1] and argv[2] as formula and proof, whatever else is on the
    line, so the files come first and the format flag after them (flag first, it
    opens "-I" as the formula). -I/-i set the mode after drat-trim's own format
    detection, overriding it; the formula is comment-free (strip_comments)."""
    record = base.run_process(ctx.limited([ctx.tools["drat-trim"], cnf, proof, "-I" if arm == "ems" else "-i"]),
                              directory, ctx.proof_limit, ctx.environment, allow_timeout=True)
    status = [line.strip() for line in re.split(rb"[\r\n]", (directory / "stdout").read_bytes())
              if line.strip().startswith(b"s ")]
    if record["timed_out"]:
        return "drat-timeout", f"after {ctx.proof_limit}s"
    if record["returncode"] == 0 and status == [b"s VERIFIED"]:
        return "drat-verified", ""
    if record["returncode"] == 1 and status == [b"s NOT VERIFIED"]:
        return "drat-rejected", ""
    return "drat-error", f"rc={record['returncode']} status={[line.decode(errors='replace') for line in status]}"


def schedule(cases, arms, seed):
    """Instance order and each instance's arm order: keyed SHA-256 permutations of the seed."""
    return [(case, sorted(arms, key=lambda arm: key(seed, "arm", case["id"], arm)))
            for case in sorted(cases, key=lambda case: key(seed, "instance", case["id"]))]


def run_instance(case, arms, ctx):
    outcomes = []
    records = None
    for arm in arms:
        ctx.order += 1
        name = f"{ctx.order:04d}-{arm}"
        proof, result = ctx.work / "proofs" / (name + ".drat"), ctx.work / "proofs" / (name + ".result")
        need = ctx.limit + (ctx.proof_limit if arm in PROOF_ARMS else 0)
        require(ctx.deadline - time.monotonic() >= need, f"budget exhausted before run {name}; no run is shortened")
        print(f"RUN {ctx.order} {case['id']} {arm}", flush=True)
        record = base.run_process(ctx.limited(solver_command(arm, ctx.tools, case["cnf"], proof, result)),
                                  ctx.work / "runs" / name, ctx.limit, ctx.environment, allow_timeout=True)
        outcome = interpret(arm, record, ctx.work / "runs" / name, proof, result)
        outcome.update(arm=arm, order=ctx.order, record=record, certificate="", note=outcome.get("note", ""))
        if record["leftover"]:
            outcome["note"] = (f"killed {len(record['leftover']['signaled_pids'])} process(es) it left behind; "
                               + outcome["note"]).strip()
        if outcome["verdict"] == "SAT":
            if "model" in outcome:
                if records is None:
                    records = cnf_preservation.formula(case["cnf"], False)
                try:
                    certificates.check_assignment(records, outcome.pop("model"), complete=False)
                    outcome["certificate"] = "model-verified"
                except ValueError as error:
                    outcome.update(certificate="model-invalid", note=str(error))
            else:
                outcome.update(certificate="model-invalid", note=outcome.pop("model_error"))
        elif outcome["verdict"] == "UNSAT":
            if arm not in PROOF_ARMS:
                outcome["certificate"] = "no-proof"
            else:
                require(proof.is_file(), f"{arm}: UNSAT on {case['id']} without the requested proof file")
                outcome["certificate"], note = check_proof(arm, case["cnf"], proof, ctx.work / "runs" / (name + "-drat"), ctx)
                outcome["note"] = f"proof {proof.stat().st_size} bytes {note}".strip()
        for path in (proof, result):
            path.unlink(missing_ok=True)
        outcomes.append(outcome)
    return judge(case, outcomes)


def judge(case, outcomes):
    """Certified evidence decides the truth; GBD's recorded result must not contradict it."""
    certified = {o["verdict"] for o in outcomes if o["certificate"] in ("model-verified", "drat-verified")}
    require(len(certified) <= 1, f"{case['id']}: both a verified model and a verified refutation")
    recorded = {"sat": "SAT", "unsat": "UNSAT"}.get(case["expected"])
    require(not (certified and recorded and certified != {recorded}),
            f"{case['id']}: certified {certified} contradicts the recorded result {case['expected']}")
    truth = next(iter(certified), recorded)
    for outcome in outcomes:
        answered = outcome["verdict"] in ("SAT", "UNSAT")
        outcome["wrong"] = answered and (outcome["certificate"] in ("model-invalid", "drat-rejected")
                                         or (truth is not None and outcome["verdict"] != truth))
        if answered and not outcome["wrong"] and outcome["certificate"] not in ("model-verified", "drat-verified"):
            outcome["certificate"] += "+agrees" if truth else "+unchecked"
        outcome["solved"] = outcome["certificate"] in VERIFIED and not outcome["wrong"]
        outcome["solved_crosschecked"] = outcome["solved"] or (not outcome["wrong"]
                                                               and outcome["certificate"].endswith("+agrees"))
    return outcomes


def row(case, outcome, limit):
    wall = outcome["record"]["wall_ns"] / 1e9
    return {"order": outcome["order"], "instance": case["id"], "kind": case["kind"], "stratum": case["stratum"],
            "family": case["family"], "expected": case["expected"], "arm": outcome["arm"],
            "verdict": "WRONG-" + outcome["verdict"] if outcome["wrong"] else outcome["verdict"],
            "certificate": outcome["certificate"], "solved": int(outcome["solved"]), "wall_s": round(wall, 6),
            "par2_s": round(wall if outcome["solved"] else 2 * limit, 6),
            "solved_crosschecked": int(outcome["solved_crosschecked"]),
            "par2_crosschecked_s": round(wall if outcome["solved_crosschecked"] else 2 * limit, 6),
            "timed_out": int(outcome["record"]["timed_out"]), "returncode": outcome["record"]["returncode"],
            "note": outcome["note"]}


def block(rows, arms):
    table = {}
    for arm in arms:
        mine = [r for r in rows if r["arm"] == arm]
        table[arm] = {"n": len(mine), "solved": sum(r["solved"] for r in mine),
                      "sat": sum(r["solved"] and r["verdict"] == "SAT" for r in mine),
                      "unsat": sum(r["solved"] and r["verdict"] == "UNSAT" for r in mine),
                      "par2_total_s": round(sum(r["par2_s"] for r in mine), 3),
                      "par2_mean_s": round(statistics.fmean(r["par2_s"] for r in mine), 3) if mine else None,
                      "unsat_agrees": sum(r["certificate"].endswith("+agrees") for r in mine),
                      "solved_crosschecked": sum(r["solved_crosschecked"] for r in mine),
                      "par2_crosschecked_total_s": round(sum(r["par2_crosschecked_s"] for r in mine), 3),
                      "unsat_unchecked": sum(r["certificate"].endswith("+unchecked") for r in mine),
                      "timeouts": sum(r["verdict"] == "TIMEOUT" for r in mine),
                      "unknown_or_error": sum(r["verdict"] in ("UNKNOWN", "ERROR") for r in mine)}
    return table


def noise_floor(rows):
    """Kissat against itself. The resolution is a magnitude, sum |delta PAR-2| over the
    pairs (with its median): the signed sum lets opposite deltas cancel, so it is
    kept only as a labelled diagnostic, and swapping the two labels flips it."""
    runs = {}
    for r in rows:
        runs.setdefault(r["instance"], {})[r["arm"]] = r
    pairs = [(item["kissat"], item["kissat-aa"]) for item in runs.values() if {"kissat", "kissat-aa"} <= item.keys()]
    both = [(a["wall_s"], b["wall_s"]) for a, b in pairs if a["solved"] and b["solved"]]
    relative = [abs(x - y) / ((x + y) / 2) for x, y in both if x + y > 0]
    deltas = [abs(a["par2_s"] - b["par2_s"]) for a, b in pairs]
    return {"pairs": len(pairs), "both_solved": len(both),
            "solved_status_disagreements": sum(a["solved"] != b["solved"] for a, b in pairs),
            "par2_abs_diff_total_s": round(sum(deltas), 3),
            "par2_abs_diff_median_s": round(statistics.median(deltas), 6) if deltas else None,
            "median_abs_diff_s": round(statistics.median(abs(x - y) for x, y in both), 6) if both else None,
            "median_rel_diff": round(statistics.median(relative), 6) if relative else None,
            "max_rel_diff": round(max(relative), 6) if relative else None,
            "par2_signed_diff_total_s_diagnostic": round(sum(a["par2_s"] - b["par2_s"] for a, b in pairs), 3)}


def summarize(rows, arms, cases, limit):
    require(len(rows) == len(cases) * len(arms) > 0
            and all(sum(r["arm"] == arm for r in rows) == len(cases) for arm in arms),
            f"run population: {len(rows)} rows for {len(cases)} instances x {len(arms)} arms")
    competition = [r for r in rows if r["kind"] == "competition"]
    groups = lambda field: {value: block([r for r in competition if r[field] == value], arms)
                            for value in sorted({r[field] for r in competition})}
    return {"limit_s": limit, "par2_penalty_s": 2 * limit, "arms": list(arms),
            "competition": block(competition, arms),
            "ladder": block([r for r in rows if r["kind"] == "ladder"], arms),
            "strata": groups("stratum"), "families": groups("family"),
            "aa": noise_floor(rows) if {"kissat", "kissat-aa"} <= set(arms) else None,
            "wrong": [r for r in rows if r["verdict"].startswith("WRONG-")]}


def markdown(summary, rows, meta):
    arms, limit = summary["arms"], summary["limit_s"]
    out = [f"# SAT Competition baseline (EigenMiniSat #131)", "",
           f"Time limit {limit:g} s per run (PAR-2 penalty {2 * limit:g} s), DRAT checks capped at "
           f"{meta['proof_limit_s']:g} s, {meta['memory_mb']} MiB address space per process. "
           f"Order seed {meta['order_seed']}; manifest seed {meta['manifest_seed']}. Arms: {', '.join(arms)}.", ""]
    if meta["subset"]:
        out[0:0] = [f"**SUBSET RUN: {meta['subset']}.**", ""]
    def table(title, data):
        out.extend([f"## {title}", "",
                    "Solved and PAR-2 count only verified answers (a checked model or a refutation drat-trim "
                    "verified), as in the competition. The cross-checked columns also credit an UNSAT that another "
                    "arm's certificate or GBD's record confirms (a declared departure). An UNSAT nothing confirms "
                    "(unchecked) counts in neither, and is charged twice the limit.", "",
                    "| arm | n | solved (verified) | SAT | UNSAT | PAR-2 total (s) | PAR-2 mean (s) | UNSAT confirmed, "
                    "not verified | solved (cross-checked) | PAR-2 total, cross-checked (s) | UNSAT unchecked "
                    "| timeouts | unknown/error |", "|---|" + "---:|" * 12])
        for arm, v in data.items():
            out.append(f"| {arm} | {v['n']} | {v['solved']} | {v['sat']} | {v['unsat']} | {v['par2_total_s']:.2f} | "
                       f"{v['par2_mean_s'] if v['par2_mean_s'] is None else format(v['par2_mean_s'], '.2f')} | "
                       f"{v['unsat_agrees']} | {v['solved_crosschecked']} | {v['par2_crosschecked_total_s']:.2f} | "
                       f"{v['unsat_unchecked']} | {v['timeouts']} | {v['unknown_or_error']} |")
        out.append("")
    table("Competition sample", summary["competition"])
    for label, noun in (("strata", "stratum"), ("families", "family")):
        out.extend([f"## Solved / PAR-2 total (s) per {noun}, verified answers only", "",
                    f"| {noun} | n | " + " | ".join(arms) + " |",
                    "|---|---:|" + "---:|" * len(arms)])
        for name, data in summary[label].items():
            out.append(f"| {name} | {data[arms[0]]['n']} | " + " | ".join(
                f"{data[arm]['solved']} / {data[arm]['par2_total_s']:.2f}" for arm in arms) + " |")
        out.append("")
    table("Tseitin ladder (odd torus, same metric)", summary["ladder"])
    ladder = [r for r in rows if r["kind"] == "ladder"]
    if ladder:
        out.extend(["| rung | " + " | ".join(arms) + " |", "|---|" + "---:|" * len(arms)])
        for instance in sorted({r["instance"] for r in ladder}, key=lambda name: [int(x) for x in name.split("-")[1].split("x")]):
            cells = {r["arm"]: (f"{r['wall_s']:.2f}" if r["solved"] else f"{r['wall_s']:.2f}*" if r["solved_crosschecked"]
                                else r["verdict"]) for r in ladder if r["instance"] == instance}
            out.append(f"| {instance} | " + " | ".join(cells[arm] for arm in arms) + " |")
        out.extend(["", "Seconds; * marks an UNSAT confirmed by the construction or another arm, not verified."])
        out.append("")
    aa = summary["aa"]
    if aa:
        out.extend(["## A/A noise floor (Kissat twice, same binary and options)", "",
                    f"Resolution: sum of |delta PAR-2| over the {aa['pairs']} pairs = {aa['par2_abs_diff_total_s']:.3f} s "
                    f"(median |delta PAR-2| {aa['par2_abs_diff_median_s']} s). Two arms whose PAR-2 totals differ by "
                    f"|D| < {aa['par2_abs_diff_total_s']:.3f} s are not resolved by this run.", "",
                    f"Wall time over the {aa['both_solved']} pairs both runs solved: median |dt| {aa['median_abs_diff_s']} s, "
                    f"median relative |dt| {aa['median_rel_diff']}, max relative |dt| {aa['max_rel_diff']}. "
                    f"Solved-status disagreements: {aa['solved_status_disagreements']}.", "",
                    f"Diagnostic only, not a resolution: the signed sum of (kissat - kissat-aa) PAR-2 = "
                    f"{aa['par2_signed_diff_total_s_diagnostic']:.3f} s; opposite deltas cancel in it.", ""])
    if summary["wrong"]:
        out.extend(["## WRONG ANSWERS (the run fails)", ""] +
                    [f"- {r['instance']} {r['arm']}: {r['verdict']} {r['certificate']} {r['note']}" for r in summary["wrong"]] + [""])
    return "\n".join(out)


def version(path, flag="--version"):
    try:
        result = subprocess.run([str(path), flag], capture_output=True, timeout=30)
        return result.stdout.decode(errors="replace").strip().splitlines()[0] if result.stdout.strip() else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, type=Path, help="new directory for results (must not exist)")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--frame", type=Path, default=FRAME, help="frozen sampling frame the manifest must re-derive from")
    parser.add_argument("--arms", default=",".join(ARMS), help="comma-separated subset of " + ",".join(ARMS))
    parser.add_argument("--ladder", default=" ".join(LADDER), help="odd torus rungs, space separated ('' for none)")
    parser.add_argument("--limit", type=float, default=60, help="seconds per solver run (PAR-2 charges 2x)")
    parser.add_argument("--proof-limit", type=float, help="seconds per drat-trim check (default: --limit)")
    parser.add_argument("--memory-mb", type=int, default=12288, help="address-space cap per process (prlimit --as)")
    parser.add_argument("--budget-seconds", type=float, default=19800, help="wall budget for the whole harness")
    parser.add_argument("--order-seed", type=int, help="run-order seed (default: the manifest seed)")
    parser.add_argument("--cache", type=Path, help="directory reused for downloaded .cnf.xz files")
    parser.add_argument("--smoke", action="store_true",
                        help="SMOKE ONLY: the manifest's smallest SAT and smallest UNSAT instance (labelled a subset)")
    for tool in ("kissat", "cadical", "minisat", "eigenscript", "drat-trim"):
        parser.add_argument("--" + tool, type=Path)
    args = parser.parse_args(argv)
    args.arms = tuple(arm for arm in args.arms.split(",") if arm)
    require(args.arms and len(set(args.arms)) == len(args.arms) and set(args.arms) <= set(ARMS), f"invalid --arms {args.arms}")
    args.arms = tuple(arm for arm in ARMS if arm in args.arms)
    args.ladder = tuple(args.ladder.split())
    require(len(set(args.ladder)) == len(args.ladder) and set(args.ladder) <= set(LADDER), f"invalid --ladder {args.ladder}")
    args.proof_limit = args.limit if args.proof_limit is None else args.proof_limit
    require(args.limit > 0 and args.proof_limit > 0 and args.memory_mb > 0 and args.budget_seconds > 0, "limits must be positive")
    needed = {TOOLS[arm] for arm in args.arms} | ({"drat-trim"} if set(args.arms) & set(PROOF_ARMS) else set())
    needed |= {"eigenscript"} if args.ladder else set()
    args.tools = {}
    for tool in sorted(needed):
        given = getattr(args, tool.replace("-", "_"))
        require(given is not None, f"--{tool} is required for arms {','.join(args.arms)}")
        args.tools[tool] = base.executable(given)
    return args


def load_manifest(path, frame=FRAME):
    """The sample must be exactly the seeded draw from the frozen frame."""
    manifest = json.loads(Path(path).read_text())
    instances = manifest["instances"]
    strata = manifest["strata"]
    require(instances and len({i["hash"] for i in instances}) == len(instances)
            and all(re.fullmatch(r"[0-9a-f]{32}", i["hash"]) for i in instances),
            "manifest needs a nonempty set of unique 32-hex GBD hashes")
    for name, item in strata.items():
        count = sum(i["stratum"] == name for i in instances)
        require(count == item["selected"] == manifest["per_stratum"],
                f"manifest stratum {name}: {count} instances, {item['selected']} declared, {manifest['per_stratum']} per stratum")
    require({i["stratum"] for i in instances} == set(strata), "manifest instances name an undeclared stratum")
    require(manifest == select.derive_manifest(select.load_frame(frame)),
            f"{path} is not the draw re-derived from the frozen frame {frame}")
    return manifest


def smoke_instances(manifest):
    """The smallest SAT and the smallest UNSAT instance by GBD bytes, so a smoke checks real models and proofs."""
    picks = []
    for result in ("sat", "unsat"):
        candidates = [i for i in manifest["instances"] if i["gbd_result"] == result]
        require(candidates, f"the manifest has no {result} instance for the smoke")
        picks.append(min(candidates, key=lambda i: (i["bytes"], i["hash"])))
    return picks


def main(argv=None):
    output = None
    try:
        started = time.monotonic()
        args = arguments(argv)
        manifest = load_manifest(args.manifest, args.frame)
        instances = smoke_instances(manifest) if args.smoke else manifest["instances"]
        args.output.mkdir(parents=True, exist_ok=False)
        output = args.output
        work = output / "work"
        (work / "proofs").mkdir(parents=True)
        (work / "runs").mkdir()
        deadline = started + args.budget_seconds
        if args.cache:
            args.cache.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ, LC_ALL="C")
        prlimit = shutil.which("prlimit")
        require(prlimit, "prlimit (util-linux) is required for the per-process memory cap")
        seed = manifest["seed"] if args.order_seed is None else args.order_seed
        meta = {"status": "incomplete", "manifest": str(args.manifest), "manifest_sha256": base.sha256(args.manifest),
                "frame": str(args.frame), "frame_sha256": base.sha256(args.frame),
                "manifest_seed": manifest["seed"], "order_seed": seed, "arms": list(args.arms),
                "ladder": list(args.ladder), "limit_s": args.limit, "proof_limit_s": args.proof_limit,
                "memory_mb": args.memory_mb, "budget_s": args.budget_seconds,
                "subset": None if not args.smoke else
                "smoke: the smallest SAT and the smallest UNSAT of the "
                f"{len(manifest['instances'])} manifest instances by GBD bytes (not the baseline)",
                "tools": {name: {"path": str(path), "sha256": base.sha256(path),
                                 "version": version(path) if name in ("kissat", "cadical", "eigenscript") else ""}
                          for name, path in args.tools.items()},
                "minisat_package": base.native_package(args.tools["minisat"]) if "minisat" in args.tools else None,
                "host": {"platform": platform.platform(), "python": sys.version.split()[0], "cpus": os.cpu_count(),
                         "cpu": next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                                      if line.startswith("model name")), ""), "loadavg_at_start": os.getloadavg()}}
        base.write_json(output / "run.json", meta)
        print(f"Competition baseline: {len(instances)} GBD instances, ladder {' '.join(args.ladder) or 'none'}, "
              f"arms {','.join(args.arms)}, limit {args.limit:g}s, DRAT cap {args.proof_limit:g}s", flush=True)
        if "ems" in args.arms:
            preflight(args.tools["eigenscript"], work, environment, deadline, 600)
        cases = []
        for instance in instances:
            print(f"PREPARE {instance['hash']} ({instance['stratum']}/{instance['family']})", flush=True)
            cases.append(prepare_gbd(instance, work / "instances" / instance["hash"], args.cache))
        for rung in args.ladder:
            print(f"PREPARE tseitin-{rung}-odd", flush=True)
            cases.append(prepare_rung(rung, work, args.tools["eigenscript"], environment, deadline, 600))
        proof_arms = sum(arm in PROOF_ARMS for arm in args.arms)
        worst = len(cases) * (len(args.arms) * args.limit + proof_arms * args.proof_limit + OVERHEAD)
        remaining = deadline - time.monotonic()
        meta["arithmetic"] = {"instances": len(cases), "runs_per_instance": len(args.arms), "drat_checks_per_instance": proof_arms,
                              "worst_case_s": worst, "formula": "instances * (runs * limit + drat checks * proof limit + overhead)",
                              "overhead_per_instance_s": OVERHEAD, "remaining_after_preparation_s": round(remaining, 1)}
        base.write_json(output / "run.json", meta)
        print(f"ARITHMETIC {len(cases)} x ({len(args.arms)} x {args.limit:g} + {proof_arms} x {args.proof_limit:g} + {OVERHEAD}) "
              f"= {worst:.0f}s worst case; {remaining:.0f}s of budget remain", flush=True)
        require(worst <= remaining, "the worst case does not fit the remaining budget; shrink the sample or the limits")
        ctx = SimpleNamespace(work=work, tools=args.tools, limit=args.limit, proof_limit=args.proof_limit,
                              environment=environment, deadline=deadline, order=0,
                              limited=lambda command: [prlimit, f"--as={args.memory_mb << 20}", "--", *map(str, command)])
        plan = schedule(cases, args.arms, seed)
        (output / "order.tsv").write_text("".join(f"{case['id']}\t{','.join(arms)}\n" for case, arms in plan))
        rows = []
        with (output / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, FIELDS)
            writer.writeheader()
            for case, arms in plan:
                for outcome in run_instance(case, arms, ctx):
                    rows.append(row(case, outcome, args.limit))
                    writer.writerow(rows[-1])
                stream.flush()
        summary = summarize(rows, args.arms, cases, args.limit)
        base.write_json(output / "summary.json", summary)
        (output / "summary.md").write_text(markdown(summary, rows, meta))
        meta.update(status="failed: wrong answers" if summary["wrong"] else "complete",
                    elapsed_s=round(time.monotonic() - started, 1))
        base.write_json(output / "run.json", meta)
        if summary["wrong"]:
            print(f"FAIL {len(summary['wrong'])} wrong answer(s); see {output}/summary.md", file=sys.stderr)
            return 1
        print(f"SUMMARY COMPLETE instances={len(cases)} arms={len(args.arms)} runs={len(rows)} "
              f"wrong=0 artifacts={output}")
        return 0
    except (Failure, OSError, ValueError, KeyError, subprocess.SubprocessError, lzma.LZMAError, EOFError) as error:
        if output is not None:
            base.write_json(output / "failure.json", {"status": "failed", "error": str(error)})
        print(f"FAIL {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
