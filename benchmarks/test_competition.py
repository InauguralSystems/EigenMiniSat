#!/usr/bin/env python3
"""Synthetic tests for the competition baseline harness; no real solver, no download.

Stub solvers speak each arm's real output contract; every plant names the check
it must turn red. Real Kissat/CaDiCaL/MiniSat/EMS/drat-trim run only in the
workflow and the local smoke.
"""
import csv
import io
import json
import lzma
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

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
STUB = r'''#!/usr/bin/env python3
import sys, time
from pathlib import Path
role, mode, root = {role!r}, {mode!r}, {root!r}
args = sys.argv[1:]
if mode == "slow":
    time.sleep(5)
if role == "drat-trim":
    if mode == "exit0-timeout":
        print("s TIMEOUT"); sys.exit(0)
    if mode == "reject-cadical" and "cadical" in Path(args[1]).name:
        print("\ns NOT VERIFIED"); sys.exit(1)
    good = Path(args[0]).read_bytes().startswith(b"p cnf 1 2") and Path(args[1]).read_bytes() == b"0\n"
    print("\rs VERIFIED" if good else "\ns NOT VERIFIED"); sys.exit(0 if good else 1)
cnf = Path(args[-1] if role == "eigenscript" else args[0])
if role == "eigenscript" and cnf.name.startswith("tseitin_torus_"):
    rung = cnf.name.split("_")[2]
    bank = Path(root, "benchmarks/oracle/regime-c-%s.stdout" % rung).read_bytes()
    sys.stdout.buffer.write(bank.replace(b" conflicts=", b" conflicts=1") if mode == "drift" else bank); sys.exit(0)
sat = cnf.read_bytes().startswith(b"p cnf 2 1")
if mode == "lie":
    sat = not sat
model = "-1 -2 0" if mode == "bad-model" else "1 -2 0"
if role in ("kissat", "cadical"):
    proof = Path(args[1])
    proof.write_bytes(b"" if sat else b"0\n")
    print("c stub " + role)
    print("s SATISFIABLE" if sat else "s UNSATISFIABLE")
    if sat:
        print("v " + model.split()[0]); print("v " + model.split(" ", 1)[1])
    sys.exit((20 if sat else 10) if mode == "mismatch" else (10 if sat else 20))
if role == "minisat":
    print("conflicts             : 0              (0 /sec)\nCPU time              : 0.001 s")
    print("SATISFIABLE" if sat else "UNSATISFIABLE")
    Path(args[1]).write_text(("SAT\n" + model + "\n") if sat else "UNSAT\n")
    sys.exit(10 if sat else 20)
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
'''


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
        path.write_text(STUB.format(role=role, mode=mode, root=str(runner.ROOT)))
        path.chmod(0o700)
        return path

    def context(self, limit=3):
        work = Path(tempfile.mkdtemp(dir=self.root))
        (work / "proofs").mkdir()
        (work / "runs").mkdir()
        return SimpleNamespace(work=work, tools=self.tools, limit=limit, proof_limit=limit, environment=dict(os.environ),
                               deadline=time.monotonic() + 120, order=0, limited=lambda command: [str(x) for x in command])

    def run_case(self, name, expected=None, limit=3):
        case = {"id": name, "kind": "competition", "stratum": "s", "family": "f",
                "expected": expected or name, "cnf": self.cnf[name]}
        ctx = self.context(limit)
        rows = {o["arm"]: runner.row(case, o, limit) for o in runner.run_instance(case, runner.ARMS, ctx)}
        self.assertEqual(sorted(rows), sorted(runner.ARMS))
        self.assertEqual(list((ctx.work / "proofs").iterdir()), [])
        return rows

    def test_clean_instances_are_solved_and_certified(self):
        sat, unsat = self.run_case("sat"), self.run_case("unsat")
        self.assertEqual({arm: r["certificate"] for arm, r in sat.items()}, dict.fromkeys(runner.ARMS, "model-verified"))
        self.assertEqual({arm: r["certificate"] for arm, r in unsat.items()},
                         {**dict.fromkeys(runner.PROOF_ARMS, "drat-verified"), "minisat": "no-proof+agrees"})
        self.assertTrue(all(r["solved"] and r["par2_s"] == r["wall_s"] for r in [*sat.values(), *unsat.values()]))

    def test_wrong_model_is_a_wrong_answer(self):
        self.tools["kissat"] = self.stub("kissat", "bad-model")
        rows = self.run_case("sat")
        self.assertEqual((rows["kissat"]["verdict"], rows["kissat"]["certificate"]), ("WRONG-SAT", "model-invalid"))
        self.assertEqual((rows["kissat"]["solved"], rows["kissat"]["par2_s"]), (0, 6))

    def test_unproven_unsat_contradicting_verified_models_is_wrong(self):
        self.tools["minisat"] = self.stub("minisat", "lie")
        self.assertEqual(self.run_case("sat", expected="unknown")["minisat"]["verdict"], "WRONG-UNSAT")

    def test_rejected_refutation_is_wrong_even_when_the_answer_is_right(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "reject-cadical")
        rows = self.run_case("unsat", expected="unknown")
        self.assertEqual((rows["cadical"]["verdict"], rows["cadical"]["certificate"]), ("WRONG-UNSAT", "drat-rejected"))
        self.assertEqual(rows["kissat"]["certificate"], "drat-verified")

    def test_checker_timeout_is_unverified_not_wrong(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "slow")
        rows = self.run_case("unsat", limit=1)
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-timeout+agrees"})
        self.assertTrue(all(rows[arm]["solved"] for arm in runner.ARMS))

    def test_a_run_is_never_shortened_to_fit_the_budget(self):
        case = {"id": "sat", "kind": "competition", "stratum": "s", "family": "f", "expected": "sat", "cnf": self.cnf["sat"]}
        ctx = self.context(limit=3)
        ctx.deadline = time.monotonic() + 4
        with self.assertRaisesRegex(runner.Failure, "budget exhausted before run"):
            runner.run_instance(case, runner.ARMS, ctx)

    def test_checker_exit_zero_without_verified_line_is_not_verification(self):
        self.tools["drat-trim"] = self.stub("drat-trim", "exit0-timeout")
        rows = self.run_case("unsat")
        self.assertEqual({rows[arm]["certificate"] for arm in runner.PROOF_ARMS}, {"drat-error+agrees"})

    def test_contradicting_the_recorded_result_fails_the_run(self):
        with self.assertRaisesRegex(runner.Failure, "contradicts the recorded result unsat"):
            self.run_case("sat", expected="unsat")

    def test_timeout_is_unsolved_and_charged_twice_the_limit(self):
        self.tools["kissat"] = self.stub("kissat", "slow")
        row = self.run_case("sat", limit=1)["kissat"]
        self.assertEqual((row["verdict"], row["solved"], row["timed_out"], row["par2_s"]), ("TIMEOUT", 0, 1, 2))

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

    def manifest(self, hashes=None):
        cache = self.root / "cache"
        cache.mkdir(exist_ok=True)
        instances = []
        for name, data in (("sat", SAT), ("unsat", UNSAT)):
            digest = runner.gbd_hash(io.BytesIO(data))
            (cache / f"{(hashes or {}).get(name, digest)}.cnf.xz").write_bytes(lzma.compress(data))
            instances.append({"hash": (hashes or {}).get(name, digest), "stratum": name, "family": name, "gbd_result": name})
        path = self.root / "manifest.json"
        path.write_text(json.dumps({"seed": 131, "per_stratum": 1, "instances": instances,
                                    "strata": {"sat": {"selected": 1}, "unsat": {"selected": 1}}}))
        return path, cache

    def main(self, *extra):
        manifest, cache = self.manifest()
        output = self.root / f"out{len(list(self.root.glob('out*')))}"
        argv = ["--output", str(output), "--manifest", str(manifest), "--cache", str(cache), "--ladder", "",
                "--limit", "3", "--budget-seconds", "600", *extra]
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
        self.assertEqual({arm: v["solved"] for arm, v in summary["competition"].items()}, dict.fromkeys(runner.ARMS, 2))
        self.assertEqual(summary["aa"]["pairs"], 2)
        status, other = self.main("--order-seed", "7")
        self.assertEqual(status, 0)
        self.assertNotEqual((other / "order.tsv").read_text(), (output / "order.tsv").read_text())

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
        manifest, cache = self.manifest({"unsat": "0" * 32})
        (cache / f"{'0' * 32}.cnf.xz").write_bytes(lzma.compress(UNSAT + b"1 0\n"))
        with self.assertRaisesRegex(runner.Failure, "hashes to"):
            runner.prepare_gbd({"hash": "0" * 32, "stratum": "s", "family": "f", "gbd_result": "unsat"},
                               self.root / "instance", cache)

    def test_manifest_population_is_checked(self):
        manifest, _ = self.manifest()
        data = json.loads(manifest.read_text())
        for plant in ("duplicate", "count"):
            broken = json.loads(json.dumps(data))
            if plant == "duplicate":
                broken["instances"][1]["hash"] = broken["instances"][0]["hash"]
            else:
                broken["strata"]["sat"]["selected"] = 2
            manifest.write_text(json.dumps(broken))
            with self.subTest(plant=plant), self.assertRaises(runner.Failure):
                runner.load_manifest(manifest)

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
