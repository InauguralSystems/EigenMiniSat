#!/usr/bin/env python3
"""Synthetic tests for the competition baseline harness; no real solver, no download.

Stub solvers speak each arm's real output contract, and the drat-trim stub
enforces the invocation the real one needs. Every plant names the check it must
turn red. Real Kissat/CaDiCaL/MiniSat/EMS/drat-trim run only in the workflow
and the local smoke.
"""
import ast
import contextlib
import csv
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import certificate_validation as certificates
import competition_run as runner
import competition_select as select

SAT = b"p cnf 2 1\n1 2 0\n"
UNSAT = b"p cnf 1 2\n1 0\n-1 0\n"
# (input, hash computed by GBD's own gbdc 0.4.3) - an oracle outside this harness.
GBDC = [
    (b"c comment\np cnf 3 2\n1 -2 0\n3 0\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 3 2\r\n1 -2 0\r\n3 0\r\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 3 2\n1\n -2 0 3\n0\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 3 2\n1 -2 0 c trailing comment\n3 0\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 3 2\n+1 -2 0\n3 0\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 3 2\n\n\n  1   -2\t0\n   c indented\n3 0\n\n", "e8f7bd612409cfb57be740d3ecddfb6f"),
    (b"p cnf 4 2\n1 -2 0\n3 4\n", "57ebda82d67bef329351598959cd7314"),
    (b"p cnf 3 3\n0\n1 -2 0\n3 0\n", "ccfc0f1e3e69a5d01fbf42b88fb9dbb9"),
    (b"p cnf 3 2\n01 -2 0\n3 0\n", "a6647e3408bd077d58be8d47b1216cea"),
    (SAT, "4a2a81c6e15de07704f091753d10ba32"),
    (UNSAT, "673c3d2399f86574afca269499120ad5"),
]
STUB = r'''#!/usr/bin/env -S python3 -S
import subprocess, sys, time
from pathlib import Path
role, mode, root, tmp = {role!r}, {mode!r}, {root!r}, {tmp!r}
args = sys.argv[1:]
if mode == "slow":
    time.sleep(5)
if role == "drat-trim":
    # The real drat-trim opens argv[1] and argv[2]; it needs a comment-free formula
    # and the proof format's flag after the files (-I ASCII for EMS, -i binary).
    cnf, proof, flag = Path(args[0]), Path(args[1]), (args[2] if len(args) > 2 else "")
    layout = not any(line.lstrip()[:1] == b"c" for line in cnf.read_bytes().split(b"\n"))
    layout = layout and flag == ("-I" if "-ems." in proof.name else "-i")
    if mode == "exit0-timeout":
        print("s TIMEOUT"); sys.exit(0)
    if mode == "trivial-unsat":
        print("\rc trivial UNSAT\ns VERIFIED"); sys.exit(1)
    if mode == "reject-cadical" and "cadical" in proof.name:
        print("\ns NOT VERIFIED"); sys.exit(1)
    refutes = cnf.read_bytes().startswith(b"p cnf 1 2") and proof.read_bytes() == b"0\n"
    good = layout and (mode == "verify-all" or refutes)
    print("\rs VERIFIED" if good else "\ns NOT VERIFIED"); sys.exit(0 if good else 1)
if mode == "rewrite":
    # A solver that rewrites its input into a different, satisfiable formula.
    import os
    os.chmod(args[0], 0o644); Path(args[0]).write_bytes(b"p cnf 1 1\n1 0\n")
    Path(args[1]).write_bytes(b""); print("s SATISFIABLE"); print("v 1 0"); sys.exit(10)
if role == "eigenscript" and args and args[0].endswith("dump_tseitin_cnf.eigs"):
    sys.stdout.buffer.write(Path(root, "tests/fixtures/tseitin_torus_3x3_odd.cnf").read_bytes()); sys.exit(0)
cnf = Path(args[-1] if role == "eigenscript" else args[0])
if role == "eigenscript" and cnf.name.startswith("tseitin_torus_"):
    rung = cnf.name.split("_")[2]
    bank = Path(root, "benchmarks/oracle/regime-c-%s.stdout" % rung).read_bytes()
    sys.stdout.buffer.write(bank.replace(b" conflicts=", b" conflicts=1") if mode == "drift" else bank); sys.exit(0)
if mode == "fork":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    Path(tmp, "forked.pid").write_text(str(child.pid))
if mode == "unknown":
    # A quick non-answer: no certificate, no timeout.
    if role == "minisat":
        print("conflicts             : 0              (0 /sec)\nCPU time              : 0.001 s\nINDETERMINATE")
        sys.exit(0)
    if role == "eigenscript":
        sys.stderr.write("stub: gave up\n"); sys.exit(1)
    print("s UNKNOWN"); sys.exit(0)
sat = cnf.read_bytes().startswith(b"p cnf 2 1")
if mode in ("lie", "lie-rc1"):
    sat = not sat
model = "-1 -2 0" if mode == "bad-model" else "1 -2 0"
if role in ("kissat", "cadical"):
    proof = Path(args[1])
    if mode != "no-proof-file":
        proof.write_bytes(b"" if sat else b"0\n")
    print("c stub " + role)
    print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
    if sat:
        print("v " + model.split()[0]); print("v " + model.split(" ", 1)[1])
    if mode == "answer-rc1":
        sys.exit(1)
    sys.exit((20 if sat else 10) if mode == "mismatch" else (10 if sat else 20))
if role == "minisat":
    print("conflicts             : 0              (0 /sec)\nCPU time              : 0.001 s")
    print("SATISFIABLE" if sat else "UNSATISFIABLE")
    Path(args[1]).write_text(("SAT\n" + model + "\n") if sat else "UNSAT\n")
    sys.exit(0 if mode == "answer-rc0" else 10 if sat else 20)
proof = Path(args[args.index("--proof") + 1])
print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
if sat:
    print("v " + model)
print("c vars=2 clauses=1 conflicts=0 ms=1.5")
if sat:
    print("c satisfiable: no refutation to write (check the model instead)")
else:
    proof.write_bytes(b"0\n")
    if mode != "no-report":
        print("c proof written to " + str(proof))
if mode in ("answer-rc1", "lie-rc1"):
    sys.exit(1)
'''


def frame_for(rows, per_stratum=1):
    """A synthetic frozen frame: rows are (stratum, data, gbd_result)."""
    strata = {}
    for stratum, data, result in rows:
        item = strata.setdefault(stratum, {"excluded": {}, "families": {}, "pool": {}})
        item["pool"].setdefault("f", []).append([runner.gbd_hash(io.BytesIO(data)), result, len(data)])
        item["families"]["f"] = {"eligible": len(item["pool"]["f"]), "excluded": 0}
    return {"schema": 1, "issue": "synthetic", "seed": 131, "per_stratum": per_stratum, "max_bytes": 1 << 30,
            "first_main_year": 2017, "random_3sat": {}, "rules": [], "not_parity": {}, "structure": {}, "gbd": {},
            "design_history": [], "population": {"gbd_rows_with_a_track": len(rows), "outside_population": 0},
            "strata": strata}


def pair_rows(*pairs):
    """noise_floor input: one (kissat par2, kissat-aa par2, kissat solved, aa solved) tuple per instance."""
    rows = []
    for index, (a, b, solved_a, solved_b) in enumerate(pairs):
        rows += [{"instance": f"i{index}", "arm": "kissat", "wall_s": a, "par2_s": a, "solved": solved_a},
                 {"instance": f"i{index}", "arm": "kissat-aa", "wall_s": b, "par2_s": b, "solved": solved_b}]
    return rows


class CompetitionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ems-competition-selftest-")
        self.root = Path(self.temporary.name)
        self.cnf = {"sat": self.root / "sat.cnf", "unsat": self.root / "unsat.cnf"}
        self.cnf["sat"].write_bytes(SAT)
        self.cnf["unsat"].write_bytes(UNSAT)
        self.tools = {tool: self.stub(tool) for tool in ("kissat", "cadical", "minisat", "eigenscript", "drat-trim")}

    def tearDown(self):
        self.temporary.cleanup()

    def stub(self, role, mode="clean"):
        path = self.root / f"{role}-{mode}.py"
        path.write_text(STUB.format(role=role, mode=mode, root=str(runner.ROOT), tmp=str(self.root)))
        path.chmod(0o700)
        return path

    def context(self, limit=10, proof_limit=None):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / "proofs").mkdir()
        (work / "runs").mkdir()
        return SimpleNamespace(work=work, tools=self.tools, limit=limit, proof_limit=proof_limit or limit,
                               environment=dict(os.environ), deadline=time.monotonic() + 120, order=0,
                               limited=lambda command: [str(x) for x in command])

    def run_case(self, name, expected=None, limit=10, proof_limit=None, arms=runner.ARMS):
        case = {"id": name, "kind": "competition", "stratum": "s", "family": "f",
                "expected": expected or name, "cnf": self.cnf[name], **runner.seal(self.cnf[name])}
        ctx = self.context(limit, proof_limit)
        rows = {o["arm"]: runner.row(case, o, limit) for o in runner.run_instance(case, arms, ctx)}
        self.assertEqual(sorted(rows), sorted(arms))
        self.assertEqual(list((ctx.work / "proofs").iterdir()), [])
        return rows

    def test_clean_instances_score_only_verified_answers(self):
        sat, unsat = self.run_case("sat"), self.run_case("unsat")
        self.assertEqual({arm: r["certificate"] for arm, r in sat.items()}, dict.fromkeys(runner.ARMS, "model-verified"))
        self.assertEqual({arm: r["certificate"] for arm, r in unsat.items()},
                         {**dict.fromkeys(runner.PROOF_ARMS, "drat-verified"), "minisat": "no-proof+agrees"})
        for r in [*sat.values(), *unsat.values()]:
            verified = r["certificate"] in runner.VERIFIED
            self.assertEqual((r["solved"], r["solved_crosschecked"]), (int(verified), 1))
            self.assertEqual(r["par2_s"], r["wall_s"] if verified else 20)
            self.assertEqual(r["par2_crosschecked_s"], r["wall_s"])

    def test_wrong_model_is_a_wrong_answer(self):
        self.tools["kissat"] = self.stub("kissat", "bad-model")
        rows = self.run_case("sat")
        self.assertEqual((rows["kissat"]["verdict"], rows["kissat"]["certificate"]), ("WRONG-SAT", "model-invalid"))
        self.assertEqual((rows["kissat"]["solved"], rows["kissat"]["solved_crosschecked"], rows["kissat"]["par2_s"]), (0, 0, 20))

    def test_unproven_unsat_contradicting_verified_models_is_wrong(self):
        self.tools["minisat"] = self.stub("minisat", "lie")
        self.assertEqual(self.run_case("sat", expected="unknown")["minisat"]["verdict"], "WRONG-UNSAT")

    def test_an_unsat_lie_nothing_can_check_is_never_solved(self):
        # The critic's first plant: MiniSat claims UNSAT on a satisfiable formula,
        # GBD records "unknown" and no other arm answers.
        for role in ("kissat", "cadical", "eigenscript"):
            self.tools[role] = self.stub(role, "unknown")
        self.tools["minisat"] = self.stub("minisat", "lie")
        row = self.run_case("sat", expected="unknown")["minisat"]
        self.assertEqual((row["verdict"], row["certificate"]), ("UNSAT", "no-proof+unchecked"))
        self.assertEqual((row["solved"], row["solved_crosschecked"], row["par2_s"], row["par2_crosschecked_s"]), (0, 0, 20, 20))

    def test_a_refutation_the_checker_cannot_finish_is_never_solved(self):
        # The critic's second plant: Kissat claims UNSAT on a satisfiable formula and
        # drat-trim reaches its cap.
        for role in ("cadical", "minisat", "eigenscript"):
            self.tools[role] = self.stub(role, "unknown")
        self.tools["kissat"] = self.stub("kissat", "lie")
        self.tools["drat-trim"] = self.stub("drat-trim", "slow")
        row = self.run_case("sat", expected="unknown", proof_limit=1, arms=("kissat", "cadical", "minisat", "ems"))["kissat"]
        self.assertEqual((row["verdict"], row["certificate"], row["solved"], row["solved_crosschecked"], row["par2_s"]),
                         ("UNSAT", "drat-timeout+unchecked", 0, 0, 20))

    def test_a_misparsed_refutation_is_not_verified(self):
        # drat-trim reading a comment as an empty clause prints "s VERIFIED" and exits 1.
        self.tools["drat-trim"] = self.stub("drat-trim", "trivial-unsat")
        rows = self.run_case("unsat")
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-error+agrees"})
        self.assertEqual({(rows[arm]["solved"], rows[arm]["solved_crosschecked"]) for arm in runner.ARMS}, {(0, 1)})

    def test_rejected_refutation_is_wrong_even_when_the_answer_is_right(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "reject-cadical")
        rows = self.run_case("unsat", expected="unknown")
        self.assertEqual((rows["cadical"]["verdict"], rows["cadical"]["certificate"]), ("WRONG-UNSAT", "drat-rejected"))
        self.assertEqual(rows["kissat"]["certificate"], "drat-verified")

    def test_checker_timeout_is_unverified_not_wrong(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "slow")
        rows = self.run_case("unsat", proof_limit=1)
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-timeout+agrees"})
        self.assertEqual({(rows[arm]["solved"], rows[arm]["solved_crosschecked"]) for arm in runner.ARMS}, {(0, 1)})

    def test_checker_exit_zero_without_verified_line_is_not_verification(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "exit0-timeout")
        rows = self.run_case("unsat")
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-error+agrees"})

    def test_drat_trim_gets_the_files_first_and_the_format_flag_after(self):
        # The stub refutes only with the formula and proof at argv[1..2], no comment in
        # the formula, and -I (EMS, ASCII) or -i (binary) after them.
        rows = self.run_case("unsat")
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-verified"})

    def test_missing_proof_file_stops_the_run(self):
        self.tools["kissat"] = self.stub("kissat", "no-proof-file")
        with self.assertRaisesRegex(runner.Failure, "without the requested proof file"):
            self.run_case("unsat")

    def test_two_contradicting_certificates_stop_the_run(self):
        self.tools["kissat"] = self.stub("kissat", "lie")
        self.tools["drat-trim"] = self.stub("drat-trim", "verify-all")
        with self.assertRaisesRegex(runner.Failure, "both a verified model and a verified refutation"):
            self.run_case("sat", expected="unknown")

    def test_an_answer_with_a_non_answer_exit_stops_the_run_for_every_arm(self):
        # EMS: a WRONG UNSAT on a satisfiable formula, proof report and all, then exit 1.
        # MiniSat: UNSATISFIABLE and an UNSAT result file, then exit 0.
        for role, mode, message in (("kissat", "answer-rc1", "kissat: an answer line with exit 1"),
                                    ("eigenscript", "lie-rc1", "ems: an answer line with exit 1"),
                                    ("minisat", "answer-rc0", "minisat: an answer with exit 0")):
            with self.subTest(role=role):
                self.tools = {tool: self.stub(tool) for tool in self.tools}
                self.tools[role] = self.stub(role, mode)
                with self.assertRaisesRegex(runner.Failure, message):
                    self.run_case("sat")

    def test_a_formula_changed_by_a_run_stops_it(self):
        sealed = runner.seal(self.cnf["unsat"])
        self.assertEqual((self.cnf["unsat"].stat().st_mode & 0o777, sealed["empty_clause"]), (0o444, False))
        self.tools["kissat"] = self.stub("kissat", "rewrite")  # makes the file writable, then rewrites it
        with self.assertRaisesRegex(runner.Failure, "the formula changed during run"):
            self.run_case("unsat", expected="unknown")

    def test_a_trivially_unsat_formula_is_verified_without_a_proof(self):
        # The pinned drat-trim prints "s VERIFIED" with exit 1 on an empty clause; a slow
        # checker stub proves it is never asked.
        self.cnf["unsat"].write_bytes(b"p cnf 2 2\n1 2 0\n0\n")
        self.tools["drat-trim"] = self.stub("drat-trim", "slow")
        rows = self.run_case("unsat", proof_limit=1)
        self.assertEqual({r["certificate"] for r in rows.values()}, {"empty-clause"})
        self.assertEqual({r["solved"] for r in rows.values()}, {1})

    def test_a_run_is_never_shortened_to_fit_the_budget(self):
        case = {"id": "sat", "kind": "competition", "stratum": "s", "family": "f", "expected": "sat", "cnf": self.cnf["sat"]}
        ctx = self.context(limit=3)
        ctx.deadline = time.monotonic() + 4
        with self.assertRaisesRegex(runner.Failure, "budget exhausted before run"):
            runner.run_instance(case, runner.ARMS, ctx)

    def test_contradicting_the_recorded_result_fails_the_run(self):
        with self.assertRaisesRegex(runner.Failure, "contradicts the recorded result unsat"):
            self.run_case("sat", expected="unsat")

    def test_timeout_is_unsolved_and_charged_twice_the_limit(self):
        self.tools["kissat"] = self.stub("kissat", "slow")
        row = self.run_case("sat", limit=1, arms=("kissat",))["kissat"]
        self.assertEqual((row["verdict"], row["solved"], row["timed_out"], row["par2_s"]), ("TIMEOUT", 0, 1, 2))

    def test_processes_left_behind_are_killed_and_reported(self):
        self.tools["kissat"] = self.stub("kissat", "fork")
        row = self.run_case("sat")["kissat"]
        pid = int((self.root / "forked.pid").read_text())
        stat = Path(f"/proc/{pid}/stat")
        self.assertTrue(not stat.exists() or stat.read_text().rsplit(")", 1)[1].split()[0] in ("Z", "X"))
        self.assertTrue(row["note"].startswith("killed 1 process(es) it left behind"), row["note"])
        self.assertEqual(row["certificate"], "model-verified")

    def test_exit_status_and_report_must_agree(self):
        self.tools["kissat"] = self.stub("kissat", "mismatch")
        with self.assertRaisesRegex(runner.Failure, "needs exactly the line s UNSATISFIABLE"):
            self.run_case("sat")

    def test_ems_unsat_without_its_proof_report_fails(self):
        self.tools["eigenscript"] = self.stub("eigenscript", "no-report")
        with self.assertRaisesRegex(runner.Failure, "UNSAT needs exactly one report"):
            self.run_case("unsat")

    def test_gbd_hash_matches_gbdc(self):
        for data, expected in GBDC:
            with self.subTest(data=data):
                self.assertEqual(runner.gbd_hash(io.BytesIO(data)), expected)

    def test_partial_model_is_sound_and_malformed_literals_fail(self):
        records = certificates.cnf_preservation.formula(self.cnf["sat"], False)
        certificates.check_assignment(records, [1], complete=False)
        for literals in ([1, 1], [0], [3], [-1]):
            with self.subTest(literals=literals), self.assertRaises(ValueError):
                certificates.check_assignment(records, literals, complete=False)
        empty = self.root / "empty.cnf"
        empty.write_bytes(b"p cnf 2 2\n1 2 0\n0\n")
        with self.assertRaisesRegex(ValueError, "does not satisfy input clause"):
            certificates.check_assignment(certificates.cnf_preservation.formula(empty, False), [1, 2], complete=False)

    def test_summary_counts_and_par2_totals(self):
        # Rows as row() writes them (limit 10): every certificate class, exact sums.
        spec = {  # arm: [(instance, verdict, certificate, wall)]
            "kissat": [("a", "TIMEOUT", "", 10.5), ("b", "UNSAT", "drat-verified", 1.0), ("c", "UNKNOWN", "", 0.1)],
            "kissat-aa": [("a", "SAT", "model-verified", 2.0), ("b", "UNSAT", "drat-timeout+agrees", 1.5),
                          ("c", "UNKNOWN", "", 0.1)],
            "cadical": [("a", "WRONG-SAT", "model-invalid", 0.5), ("b", "UNSAT", "drat-verified", 0.7),
                        ("c", "UNKNOWN", "", 0.1)],
            "minisat": [("a", "SAT", "model-verified", 0.3), ("b", "UNSAT", "no-proof+agrees", 0.4),
                        ("c", "UNSAT", "no-proof+unchecked", 0.2)],
            "ems": [("a", "ERROR", "", 0.2), ("b", "UNSAT", "drat-verified", 3.0), ("c", "TIMEOUT", "", 10.4)],
        }
        rows = []
        for arm, runs in spec.items():
            for instance, verdict, certificate, wall in runs:
                solved = certificate in runner.VERIFIED and not verdict.startswith("WRONG")
                crosschecked = solved or certificate.endswith("+agrees")
                rows.append({"instance": instance, "kind": "competition", "stratum": "s", "family": "f", "arm": arm,
                             "verdict": verdict, "certificate": certificate, "solved": int(solved), "wall_s": wall,
                             "par2_s": wall if solved else 20, "solved_crosschecked": int(crosschecked),
                             "par2_crosschecked_s": wall if crosschecked else 20})
        summary = runner.summarize(rows, runner.ARMS, [{"id": "a"}, {"id": "b"}, {"id": "c"}], 10)
        got = {arm: tuple(v[k] for k in ("solved", "sat", "unsat", "par2_total_s", "unsat_agrees", "solved_crosschecked",
                                         "par2_crosschecked_total_s", "unsat_unchecked", "timeouts", "unknown_or_error"))
               for arm, v in summary["competition"].items()}
        self.assertEqual(got, {"kissat": (1, 0, 1, 41.0, 0, 1, 41.0, 0, 1, 1),
                               "kissat-aa": (1, 1, 0, 42.0, 1, 2, 23.5, 0, 0, 1),
                               "cadical": (1, 0, 1, 40.7, 0, 1, 40.7, 0, 0, 1),
                               "minisat": (1, 1, 0, 40.3, 1, 2, 20.7, 1, 0, 0),
                               "ems": (1, 0, 1, 43.0, 0, 1, 43.0, 0, 1, 1)})
        self.assertEqual([(r["instance"], r["arm"]) for r in summary["wrong"]], [("a", "cadical")])

    def test_aa_resolution_is_a_magnitude(self):
        cases = {
            "aa slower": ([(1.0, 11.0, 1, 1)], 10.0, 10.0, -10.0),
            "aa faster": ([(11.0, 1.0, 1, 1)], 10.0, 10.0, 10.0),
            "zero": ([(5.0, 5.0, 1, 1)], 0.0, 0.0, 0.0),
            "cancelling 9 s pairs": ([(1.0, 10.0, 1, 1), (10.0, 1.0, 1, 1)], 18.0, 9.0, 0.0),
            "boundary flips": ([(59.0, 120.0, 1, 0), (120.0, 59.0, 0, 1)], 122.0, 61.0, 0.0),
        }
        for name, (pairs, total, median, signed) in cases.items():
            with self.subTest(name):
                aa = runner.noise_floor(pair_rows(*pairs))
                self.assertEqual((aa["par2_abs_diff_total_s"], aa["par2_abs_diff_median_s"],
                                  aa["par2_signed_diff_total_s_diagnostic"]), (total, median, signed))
                swapped = runner.noise_floor(pair_rows(*[(b, a, sb, sa) for a, b, sa, sb in pairs]))
                self.assertEqual((swapped["par2_abs_diff_total_s"], swapped["par2_abs_diff_median_s"],
                                  swapped["par2_signed_diff_total_s_diagnostic"]), (total, median, -signed or 0.0))
        flips = runner.noise_floor(pair_rows((59.0, 120.0, 1, 0), (120.0, 59.0, 0, 1)))
        self.assertEqual((flips["solved_status_disagreements"], flips["both_solved"], flips["median_abs_diff_s"]), (2, 0, None))
        both = runner.noise_floor(pair_rows((1.0, 3.0, 1, 1), (2.0, 2.5, 1, 1)))
        self.assertEqual((both["median_abs_diff_s"], both["max_rel_diff"]), (1.25, 1.0))

    def test_aa_summary_text_states_the_magnitude(self):
        # Two competition pairs plus a ladder pair that must not enter the resolution.
        rows = [dict(r, kind="competition", stratum="s", family="f", verdict="SAT", certificate="model-verified",
                     solved_crosschecked=r["solved"], par2_crosschecked_s=r["par2_s"])
                for r in pair_rows((1.0, 11.0, 1, 1), (12.0, 2.0, 1, 1))]
        rows += [dict(r, instance="tseitin-3x3-odd", kind="ladder", stratum="ladder", family="t", verdict="SAT",
                      certificate="model-verified", solved_crosschecked=r["solved"], par2_crosschecked_s=r["par2_s"])
                 for r in pair_rows((1.0, 100.0, 1, 1))]
        summary = runner.summarize(rows, ("kissat", "kissat-aa"), [{"id": "i0"}, {"id": "i1"}, {"id": "3x3"}], 60)
        self.assertEqual((summary["aa"]["pairs"], summary["aa"]["par2_abs_diff_total_s"]), (2, 20.0))
        text = runner.markdown(summary, rows, {"proof_limit_s": 60, "memory_mb": 1, "order_seed": 1,
                                               "manifest_seed": 1, "subset": None})
        self.assertIn("## A/A noise floor", text)
        self.assertIn("sum of |delta PAR-2| over the 2 competition pairs = 20.000000 s (median |delta PAR-2| 10.0 s)", text)
        self.assertIn("relative wall difference over the 2 pairs both runs solved: median 154.8%, max 166.7%", text)
        self.assertIn("PAR-2 totals differ by |D| < 20.000000 s", text)
        self.assertIn("Diagnostic only, not a resolution: the signed sum of (kissat - kissat-aa) PAR-2 = 0.000000 s", text)

    def test_documented_arithmetic_is_the_codes(self):
        args = runner.arguments(["--output", str(self.root / "o"), "--arms", "minisat", "--ladder", "",
                                 "--minisat", str(self.tools["minisat"])])
        instances = len(json.loads(runner.MANIFEST.read_text())["instances"]) + len(runner.LADDER)
        expected = (instances, len(runner.ARMS), args.limit, len(runner.PROOF_ARMS), args.limit, runner.OVERHEAD,
                    runner.worst_case(instances, runner.ARMS, args.limit, args.limit))
        readme = (runner.ROOT / "benchmarks/README.md").read_text()
        workflow = (runner.ROOT / ".github/workflows/competition.yml").read_text()
        for name, text, pattern in (
                ("README", readme, r"= (\d+) × \((\d+) × (\d+) \+ (\d+) × (\d+) \+ (\d+)\) = ([\d,]+) s"),
                ("workflow", workflow, r"(\d+) instances x \((\d+) runs x (\d+) s \+ (\d+) DRAT checks x (\d+) s \+ (\d+) s\) = ([\d,]+) s")):
            with self.subTest(document=name):
                found = [tuple(float(value.replace(",", "")) for value in match) for match in re.findall(pattern, text)]
                self.assertEqual(found, [expected])
        for name, text in (("README", readme), ("workflow", workflow)):
            with self.subTest(budget=name):
                self.assertIn(f"{args.budget_seconds:,.0f} s budget", text)

    def test_version_is_never_silently_empty(self):
        silent = self.root / "silent.sh"
        silent.write_text("#!/bin/sh\nexit 3\n")
        silent.chmod(0o700)
        self.assertEqual(runner.version(silent), "unknown: --version printed nothing (exit 3)")
        self.assertTrue(runner.version(self.root / "missing").startswith("unknown: --version failed:"))

    def manifest(self, rows=(("sat", SAT, "sat"), ("unsat", UNSAT, "unsat"))):
        cache = self.root / "cache"
        cache.mkdir(exist_ok=True)
        for _, data, _ in rows:
            (cache / f"{runner.gbd_hash(io.BytesIO(data))}.cnf.xz").write_bytes(lzma.compress(data))
        frame = self.root / "frame.json"
        frame.write_text(json.dumps(frame_for(rows)))
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(select.derive_manifest(json.loads(frame.read_text()))))
        return manifest, frame, cache

    def main(self, *extra, rows=(("sat", SAT, "sat"), ("unsat", UNSAT, "unsat"))):
        manifest, frame, cache = self.manifest(rows)
        output = self.root / f"out{len(list(self.root.glob('out*')))}"
        argv = ["--output", str(output), "--manifest", str(manifest), "--frame", str(frame), "--cache", str(cache),
                "--ladder", "", "--limit", "10", "--budget-seconds", "900", *extra]
        for tool, path in self.tools.items():
            argv += ["--" + tool, str(path)]
        return runner.main(argv), output

    def test_end_to_end_population_order_and_exit_status(self):
        status, output = self.main()
        self.assertEqual(status, 0)
        rows = list(csv.DictReader((output / "results.csv").open()))
        plan = [line.split("\t") for line in (output / "order.tsv").read_text().splitlines()]
        self.assertEqual([int(r["order"]) for r in rows], list(range(1, 11)))
        self.assertEqual([(r["instance"], r["arm"]) for r in rows],
                         [(case, arm) for case, arms in plan for arm in arms.split(",")])
        self.assertEqual([sorted(arms.split(",")) for _, arms in plan], [sorted(runner.ARMS)] * 2)
        summary = json.loads((output / "summary.json").read_text())
        self.assertEqual({arm: v["solved"] for arm, v in summary["competition"].items()},
                         {**dict.fromkeys(runner.ARMS, 2), "minisat": 1})
        self.assertEqual(summary["aa"]["pairs"], 2)
        self.assertIsNone(json.loads((output / "run.json").read_text())["subset"])
        self.assertNotIn("SUBSET", (output / "summary.md").read_text())
        status, other = self.main("--order-seed", "7")
        self.assertEqual(status, 0)
        self.assertNotEqual((other / "order.tsv").read_text(), (output / "order.tsv").read_text())

    def test_comments_never_reach_an_arm(self):
        # A comment after the header: hashed as GBD hashes it, then stripped for every
        # arm (the stubs see "p cnf 2 1" first) and for the drat-trim stub, which
        # refuses a commented formula.
        commented = b"p cnf 1 2\nc a comment after the header\n1 0\n-1 0\n"
        status, output = self.main(rows=(("sat", SAT, "sat"), ("unsat", commented, "unsat")))
        self.assertEqual(status, 0)
        rows = list(csv.DictReader((output / "results.csv").open()))
        self.assertEqual({r["certificate"] for r in rows if r["arm"] in runner.PROOF_ARMS and r["expected"] == "unsat"},
                         {"drat-verified"})

    def smoke(self):
        larger = b"p cnf 2 2\n1 2 0\n1 -2 0\n"
        controls = {runner.gbd_hash(io.BytesIO(SAT)): "sat control", runner.gbd_hash(io.BytesIO(UNSAT)): "unsat control"}
        with patch.object(runner, "SMOKE", controls):
            return self.main("--smoke", rows=(("big", larger, "sat"), ("sat", SAT, "sat"), ("unsat", UNSAT, "unsat")))

    def test_smoke_runs_the_positive_controls_and_requires_every_arm_to_solve_them(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "verify-all")
        status, output = self.smoke()
        self.assertEqual(status, 0)
        rows = list(csv.DictReader((output / "results.csv").open()))
        self.assertEqual({r["instance"] for r in rows},
                         {runner.gbd_hash(io.BytesIO(SAT)), runner.gbd_hash(io.BytesIO(UNSAT)), "tseitin-3x3-odd"})
        self.assertEqual(json.loads((output / "summary.json").read_text())["smoke_failures"], [])
        subset = json.loads((output / "run.json").read_text())["subset"]
        self.assertIn("positive controls", subset)
        text = (output / "summary.md").read_text()
        self.assertTrue(text.startswith(f"**SUBSET RUN: {subset}.**"))
        self.assertIn("Every arm solved every smoke instance with a completed certificate.", text)

    def test_smoke_fails_on_a_total_ems_or_checker_failure(self):
        for role, mode, broken in (("eigenscript", "unknown", "ems: ERROR"), ("drat-trim", "exit0-timeout", "drat-error")):
            with self.subTest(role=role):
                self.tools = {tool: self.stub(tool) for tool in self.tools}
                self.tools["drat-trim"] = self.stub("drat-trim", "verify-all")
                self.tools[role] = self.stub(role, mode)
                status, output = self.smoke()
                self.assertEqual(status, 1)
                failures = json.loads((output / "summary.json").read_text())["smoke_failures"]
                self.assertTrue(failures and all(broken.split(": ")[-1] in line for line in failures), failures)
                self.assertEqual(json.loads((output / "run.json").read_text())["status"], "failed: smoke positive control")
                self.assertIn("- FAILED: ", (output / "summary.md").read_text())

    def test_end_to_end_wrong_answer_exits_nonzero(self):
        self.tools["kissat"] = self.stub("kissat", "bad-model")
        status, output = self.main()
        self.assertEqual(status, 1)
        self.assertIn("WRONG ANSWERS", (output / "summary.md").read_text())
        self.assertEqual(json.loads((output / "run.json").read_text())["status"], "failed: wrong answers")

    def test_regime_preflight_drift_fails_the_run(self):
        self.tools["eigenscript"] = self.stub("eigenscript", "drift")
        status, output = self.main()
        self.assertEqual(status, 1)
        self.assertIn("regime-C preflight 3x3", json.loads((output / "failure.json").read_text())["error"])

    def test_a_sample_that_cannot_fit_the_budget_is_refused(self):
        status, output = self.main("--budget-seconds", "60")
        self.assertEqual(status, 1)
        self.assertIn("does not fit the remaining budget", json.loads((output / "failure.json").read_text())["error"])
        self.assertFalse((output / "results.csv").exists())

    def test_downloaded_bytes_must_hash_to_the_manifest_hash(self):
        cache = self.root / "cache"
        cache.mkdir()
        (cache / f"{'0' * 32}.cnf.xz").write_bytes(lzma.compress(UNSAT + b"1 0\n"))
        with self.assertRaisesRegex(runner.Failure, "hashes to"):
            runner.prepare_gbd({"hash": "0" * 32, "stratum": "s", "family": "f", "gbd_result": "unsat"},
                               self.root / "instance", cache)

    def test_manifest_population_is_checked(self):
        manifest, frame, _ = self.manifest()
        data = json.loads(manifest.read_text())
        for plant in ("duplicate", "count"):
            broken = json.loads(json.dumps(data))
            if plant == "duplicate":
                broken["instances"][1]["hash"] = broken["instances"][0]["hash"]
            else:
                broken["strata"]["sat"]["selected"] = 2
            manifest.write_text(json.dumps(broken))
            with self.subTest(plant=plant), self.assertRaises(runner.Failure):
                runner.load_manifest(manifest, frame)

    def test_committed_manifest_is_the_draw_from_the_frozen_frame(self):
        self.assertEqual(select.main(["--check"]), 0)
        manifest = runner.load_manifest(runner.MANIFEST, runner.FRAME)
        self.assertEqual(len(manifest["instances"]), 24)
        committed = json.loads(runner.MANIFEST.read_text())
        for plant in ("swapped hashes", "relabelled result"):
            broken = json.loads(json.dumps(committed))
            first, second = broken["instances"][0], broken["instances"][1]
            if plant == "swapped hashes":
                first["hash"], second["hash"] = second["hash"], first["hash"]
            else:
                first["gbd_result"] = "sat" if first["gbd_result"] != "sat" else "unsat"
            path = self.root / f"{plant.replace(' ', '-')}.json"
            path.write_text(json.dumps(broken))
            with self.subTest(plant=plant):
                with self.assertRaisesRegex(runner.Failure, "is not the draw re-derived from the frozen frame"):
                    runner.load_manifest(path, runner.FRAME)
                self.assertEqual(select.main(["--check", "--manifest", str(path)]), 1)

    def test_frame_accounting_is_checked(self):
        frame = json.loads(runner.FRAME.read_text())
        select.validate_frame(frame)
        plants = {
            "dropped row": lambda f: f["strata"]["tseitin"]["pool"]["tseitin-formulas"].pop(),
            "repeated hash": lambda f: f["strata"]["tseitin"]["pool"]["tseitin-formulas"][1].__setitem__(
                0, f["strata"]["tseitin"]["pool"]["tseitin-formulas"][0][0]),
            "bad result": lambda f: f["strata"]["tseitin"]["pool"]["tseitin-formulas"][0].__setitem__(1, "maybe"),
            "zero size": lambda f: f["strata"]["tseitin"]["pool"]["tseitin-formulas"][0].__setitem__(2, 0),
            "oversize": lambda f: f["strata"]["tseitin"]["pool"]["tseitin-formulas"][0].__setitem__(2, f["max_bytes"] + 1),
            "orphan pool family": lambda f: f["strata"]["tseitin"]["pool"].__setitem__(
                "unlisted", [["f" * 32, "unsat", 10]]),
            "family exclusions": lambda f: f["strata"]["tseitin"]["excluded"].__setitem__("over 25000000 bytes", 2),
            "population sum": lambda f: f["population"].__setitem__("outside_population",
                                                                    f["population"]["outside_population"] + 1),
        }
        for plant, change in plants.items():
            broken = json.loads(json.dumps(frame))
            change(broken)
            with self.subTest(plant=plant), self.assertRaises(ValueError):
                select.validate_frame(broken)

    def test_preparation_changing_more_than_comments_stops_the_run(self):
        def lossy(source, target):  # a comment stripper that also drops the last clause line
            lines = Path(source).read_bytes().splitlines(keepends=True)
            Path(target).write_bytes(b"".join(line for line in lines[:-1] if not line.startswith(b"c")))
        _, frame, cache = self.manifest()
        digest = runner.gbd_hash(io.BytesIO(UNSAT))
        with patch.object(runner, "strip_comments", lossy):
            with self.assertRaisesRegex(runner.Failure, f"{digest}: .*clause count"):
                runner.prepare_gbd({"hash": digest, "stratum": "s", "family": "f", "gbd_result": "unsat"},
                                   self.root / "instance", cache)
            work = self.root / "rung-work"
            work.mkdir()
            with self.assertRaisesRegex(runner.Failure, "tseitin-3x3-odd: "):
                runner.prepare_rung("3x3", work, self.tools["eigenscript"], dict(os.environ), time.monotonic() + 60, 30)

    def test_frame_is_checked_against_the_archived_databases(self):
        # Tiny GBD databases: five rows per stratum, plus two "ktf" rows in other.
        directory = self.root / "gbd"
        directory.mkdir()
        meta, base = directory / "meta.db", directory / "base.db"
        with sqlite3.connect(meta) as m, sqlite3.connect(base) as b:
            m.execute("CREATE TABLE features (hash TEXT, family TEXT, result TEXT)")
            m.execute("CREATE TABLE track (hash TEXT, value TEXT)")
            b.execute("CREATE TABLE features (hash TEXT, bytes TEXT, variables TEXT, clauses TEXT, cls3 TEXT)")
            families = [("tseitin-formulas", 5), ("minimum-disagreement-parity", 5), ("pigeon-hole", 5),
                        ("uniform-random", 5), ("cryptography", 5), ("coloring", 5), ("ktf", 2)]
            for family, count in families:
                for index in range(count):
                    digest = hashlib.md5(f"{family}{index}".encode()).hexdigest()
                    m.execute("INSERT INTO features VALUES (?, ?, ?)", (digest, family, "unsat"))
                    random_track = family == "uniform-random"
                    m.execute("INSERT INTO track VALUES (?, ?)", (digest, "random_2010" if random_track else "main_2020"))
                    b.execute("INSERT INTO features VALUES (?, ?, ?, ?, ?)",
                              (digest, "1000", "100", "426", "426" if random_track else "0"))
        frame, manifest = directory / "frame.json", directory / "manifest.json"
        self.assertEqual(select.main(["--refresh", "--meta", str(meta), "--base", str(base),
                                      "--frame", str(frame), "--manifest", str(manifest)]), 0)
        data = json.loads(frame.read_text())
        for name, path in (("meta", meta), ("base", base)):
            data["gbd"][name]["archive"] = path.as_uri()

        def write(frame_data):
            frame.write_text(select.dump_frame(frame_data))
            manifest.write_text(json.dumps(select.derive_manifest(frame_data), indent=1) + "\n")

        write(data)
        argv = ["--frame", str(frame), "--manifest", str(manifest)]
        self.assertEqual((select.main(["--check", *argv]), select.main(["--check-frame", *argv])), (0, 0))
        dropped = json.loads(json.dumps(data))
        other = dropped["strata"]["other"]
        moved = other["families"].pop("ktf")
        other["pool"].pop("ktf")
        dropped["population"]["outside_population"] += moved["eligible"] + moved["excluded"]
        write(dropped)
        self.assertEqual((select.main(["--check", *argv]), select.main(["--check-frame", *argv])), (0, 1))
        write(data)
        meta.write_bytes(meta.read_bytes() + b"x")
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            self.assertEqual(select.main(["--check-frame", *argv]), 1)
        self.assertIn("archived meta database", printed.getvalue())
        self.assertIn("does not hash to", printed.getvalue())

    def test_schedule_is_a_seeded_interleaved_permutation(self):
        cases = [{"id": f"case{index}"} for index in range(40)]
        plan = runner.schedule(cases, runner.ARMS, 131)
        self.assertEqual(plan, runner.schedule(list(reversed(cases)), runner.ARMS, 131))
        self.assertEqual(sorted(case["id"] for case, _ in plan), sorted(case["id"] for case in cases))
        self.assertTrue(all(sorted(arms) == sorted(runner.ARMS) for _, arms in plan))
        self.assertGreater(len({tuple(arms) for _, arms in plan}), 10)
        self.assertNotEqual([case["id"] for case, _ in plan], [case["id"] for case in cases])
        other = runner.schedule(cases, runner.ARMS, 132)
        self.assertNotEqual([(case["id"], arms) for case, arms in plan], [(case["id"], arms) for case, arms in other])

    def test_summary_requires_every_run(self):
        rows = list(self.run_case("sat").values())
        case = {"id": "sat"}
        with self.assertRaisesRegex(runner.Failure, "run population"):
            runner.summarize(rows[:-1], runner.ARMS, [case], 3)

    def test_workflow_paths_are_exactly_what_the_harness_reads(self):
        """The pull_request path filter is derived, not picked: every repository file
        the harness opens or hands to a child, its local imports, the EigenScript files
        those children load, and the files the workflow steps name."""
        root = runner.ROOT
        read, active = set(), [True]

        def note(value):
            try:
                path = Path(os.fsdecode(value)).resolve()
            except (TypeError, ValueError):
                return
            if path.is_file() and root in path.parents:
                read.add(path.relative_to(root).as_posix())

        def hook(event, args):
            if active[0] and event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
                note(args[0])
            elif active[0] and event == "subprocess.Popen" and isinstance(args[1], (list, tuple)):
                for value in args[1]:
                    note(value)

        self.tools["drat-trim"] = self.stub("drat-trim", "verify-all")
        sys.addaudithook(hook)
        try:
            runner.load_manifest(runner.MANIFEST, runner.FRAME)
            status, _ = self.main("--ladder", "3x3")
        finally:
            active[0] = False
        self.assertEqual(status, 0)
        workflow = root / ".github/workflows/competition.yml"
        text = workflow.read_text()
        steps = text[text.index("\n    steps:"):]
        read |= {token for token in re.findall(r"[A-Za-z0-9_.][A-Za-z0-9_./-]*", steps) if (root / token).is_file()}
        pending = [path for path in sorted(read) if path.endswith(".py")]
        while pending:
            for node in ast.walk(ast.parse((root / pending.pop()).read_text())):
                names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else \
                    [node.module] if isinstance(node, ast.ImportFrom) and node.module else []
                for name in names:
                    local = f"benchmarks/{name}.py"
                    if (root / local).is_file() and local not in read:
                        read.add(local)
                        pending.append(local)
        pending = [path for path in read if path.endswith(".eigs")]
        while pending:
            for name in re.findall(r'^\s*load_file of "([^"]+)"', (root / pending.pop()).read_text(), re.M):
                if (root / name).is_file() and name not in read:
                    read.add(name)
                    pending.append(name)
        read.add(".github/workflows/competition.yml")
        block = re.search(r"\n    paths:\n((?:      - .+\n)+)", text)
        self.assertIsNotNone(block, "competition.yml has no pull_request paths list")
        listed = re.findall(r"      - (.+)\n", block.group(1))
        self.assertEqual(sorted(listed), sorted(read))


class SelectionTests(unittest.TestCase):
    def test_strata_rules(self):
        expected = {"tseitin-formulas": "tseitin", "minimum-disagreement-parity": "parity", "xor-chain": "parity",
                    "parity-games": "other", "xor-shifting": "other", "relativized-pigeon-hole": "pigeonhole",
                    "sudoku-php": "pigeonhole", "hardware-model-checking": "application",
                    "cryptography-simon": "application", "circuit-equialence-checking": "application",
                    "coloring": "other"}
        self.assertEqual({family: select.main_stratum(family) for family in expected}, expected)

    def test_draw_spreads_by_family_and_is_seeded(self):
        rows = [{"family": family, "hash": f"{family}{index}"} for family, size in (("a", 3), ("b", 1), ("c", 2))
                for index in range(size)]
        chosen = select.draw("s", rows, 131, 4)
        self.assertEqual(len({row["family"] for row in chosen[:3]}), 3)
        self.assertEqual(chosen, select.draw("s", list(reversed(rows)), 131, 4))
        self.assertEqual(sorted(row["hash"] for row in select.draw("s", rows, 131, 6)), sorted(row["hash"] for row in rows))
        with self.assertRaisesRegex(ValueError, "6 eligible instances, 7 required"):
            select.draw("s", rows, 131, 7)


if __name__ == "__main__":
    unittest.main()
