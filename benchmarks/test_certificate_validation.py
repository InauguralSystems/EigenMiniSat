#!/usr/bin/env python3
"""Synthetic process tests for certificate gating; no real solver or build."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import compare_native as runner
import certificate_validation as certificate


STUB = '''#!/usr/bin/env python3
from pathlib import Path
import sys, time
arm, mode = {arm!r}, {mode!r}
if mode == "timeout":
    time.sleep(2)
if arm == "checker":
    print("\\rs VERIFIED")
    if mode == "rewrite-proof":
        Path(sys.argv[-1]).write_text("changed\\n")
        sys.exit(0)
    if mode == "rewrite-output":
        (Path(sys.argv[-1]).parent / "aot/stdout").write_text("changed\\n")
        sys.exit(0)
    if mode == "rewrite-input":
        Path(sys.argv[-2]).write_text("p cnf 1 1\\n1 0\\n")
    sys.exit(1 if mode == "reject" or Path(sys.argv[-1]).read_text() != "0\\n" else 0)
cnf = Path(sys.argv[-2] if arm == "native" else sys.argv[-1])
sat = "p cnf 1 1" in cnf.read_text()
verdict = "SATISFIABLE" if sat else "UNSATISFIABLE"
if arm == "native":
    if mode == "wrong-verdict":
        verdict = "SATISFIABLE"
    print("conflicts : 3 (100 /sec)\\nCPU time : 0.001 s\\n" + verdict)
    Path(sys.argv[-1]).write_text("SAT\\n-1 0\\n" if sat and mode == "bad-model" else
                                "SAT\\n1 0\\n" if verdict == "SATISFIABLE" else "UNSAT\\n")
    sys.exit(10 if verdict == "SATISFIABLE" else 20)
proof = Path(sys.argv[sys.argv.index("--proof") + 1]) if "--proof" in sys.argv else None
print("s " + verdict)
if sat and "--model" in sys.argv and mode != "missing-model":
    print("v -1 0" if mode == "bad-model" else "v 1 0")
count = 8 if proof and mode == "wrong-count" else 2
print("c vars=1 clauses=" + ("1" if sat else "2") + " conflicts=" + str(count) + " decisions=1 ms=1.5")
if mode == "extra-output" and not proof:
    print("c planted counter")
if proof:
    if sat:
        print("c satisfiable: no refutation to write (check the model instead)")
    else:
        if mode != "missing-proof":
            proof.write_text("corrupt\\n" if mode == "bad-proof" else "0\\n")
        if mode != "missing-report":
            print("c proof written to " + str(proof))
        if mode == "duplicate-report":
            print("c proof written to " + str(proof))
sys.exit(7 if mode == "nonzero" else 0)
'''


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ems-certificate-selftest-")
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        self.output.mkdir()
        self.cnf = self.root / "input.cnf"
        self.cnf.write_text("p cnf 1 2\n1 0\n-1 0\n")
        self.case = {"name": "synthetic", "cnf": self.cnf, "sha256": runner.sha256(self.cnf),
                     "verdict": "UNSATISFIABLE", "validation": "certificate", "extra_rung": True}
        self.commands = {arm: self.stub(arm) for arm in ("aot", "native")}
        self.args = SimpleNamespace(drat_trim=self.stub("checker"), timeout=1, pilot_only=False, extra_rung=[])

    def tearDown(self):
        self.temporary.cleanup()

    def stub(self, arm, mode="clean"):
        path = self.root / (arm + ".py")
        path.write_text(STUB.format(arm=arm, mode=mode))
        path.chmod(0o700)
        return path

    def certify(self):
        certificate.certify_case(runner, self.args, self.output, dict(os.environ),
                                 time.monotonic() + 5, self.case, self.commands)

    def rejected(self, arm, mode, message):
        if arm == "checker":
            self.args.drat_trim = self.stub(arm, mode)
        else:
            self.commands[arm] = self.stub(arm, mode)
        with self.assertRaisesRegex((runner.Failure, ValueError), message):
            self.certify()

    def test_valid_unsat_and_proof_off_five_samples(self):
        self.certify()
        rows = runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 10)
        self.assertEqual(rows[0]["validation"], "certificate")
        samples = [json.loads(x) for x in (self.output / "samples.jsonl").read_text().splitlines()]
        self.assertEqual(len(samples), 10)
        self.assertTrue(all("--proof" not in x["command"] and "--model" not in x["command"] for x in samples))
        self.assertEqual(self.case["reference"], b"s UNSATISFIABLE\nc vars=1 clauses=2 conflicts=2 decisions=1\n")
        self.assertIn("checker.py", " ".join(self.case["certificate_evidence"]["files"]))

    def test_checker_exit_beats_forged_verified_text(self):
        self.rejected("checker", "reject", "certificate command failed rc=1")

    def test_corrupt_proof_is_rejected(self):
        self.rejected("aot", "bad-proof", "certificate command failed rc=1")

    def test_missing_proof_is_rejected(self):
        self.rejected("aot", "missing-proof", "proof missing or empty")

    def test_missing_report_is_rejected(self):
        self.rejected("aot", "missing-report", "exactly the requested proof report")

    def test_duplicate_report_is_rejected(self):
        self.rejected("aot", "duplicate-report", "exactly the requested proof report")

    def test_native_disagreement_is_rejected(self):
        self.rejected("native", "wrong-verdict", "native verdict differs")

    def test_nonzero_aot_is_rejected(self):
        self.rejected("aot", "nonzero", "certificate command failed rc=7")

    def test_checker_timeout_is_rejected(self):
        self.args.timeout = 0.5
        self.rejected("checker", "timeout", "process timeout/interruption")
        record = json.loads((self.output / "certificates/synthetic/aot-checker/process.json").read_text())
        self.assertEqual(record["cleanup"]["remaining_live"], [])

    def test_checker_input_mutation_is_rejected(self):
        self.rejected("checker", "rewrite-input", "missing/stale/corrupt certificate artifact")

    def test_checker_proof_mutation_is_rejected(self):
        self.rejected("checker", "rewrite-proof", "proof changed during verification")

    def test_checker_output_mutation_is_rejected(self):
        self.rejected("checker", "rewrite-output", "missing/stale/corrupt certificate artifact")

    def test_artifact_faults_are_red_before_any_samples(self):
        self.certify()
        files = self.case["certificate_evidence"]["files"]
        targets = [self.cnf, self.commands["aot"], self.args.drat_trim,
                   self.output / "certificates/synthetic/aot.drat",
                   self.output / "certificates/synthetic/aot/stdout",
                   self.output / "certificates/synthetic/aot-checker/process.json",
                   self.output / "certificates/synthetic/evidence.json"]
        self.assertTrue(all(str(path) in files for path in targets))
        for index, target in enumerate(targets):
            for fault in ("corrupt", "missing"):
                with self.subTest(target=target.name, fault=fault):
                    data = target.read_bytes()
                    mode = target.stat().st_mode
                    if fault == "corrupt":
                        target.write_bytes(data + b"stale")
                    else:
                        target.unlink()
                    try:
                        with self.assertRaisesRegex((runner.Failure, OSError), "changed before|certificate artifact|No such file"):
                            certificate.verify_evidence(runner, self.case)
                    finally:
                        target.write_bytes(data)
                        target.chmod(mode)

    def test_missing_evidence_cannot_downgrade_validation(self):
        self.certify()
        del self.case["certificate_evidence"]
        with self.assertRaisesRegex(runner.Failure, "missing certificate evidence"):
            runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 5)

    def test_certificate_counter_change_fails_vm_anchor(self):
        self.case["reference"] = b"s UNSATISFIABLE\nc vars=1 clauses=2 conflicts=2 decisions=1\n"
        self.rejected("aot", "wrong-count", "certificate output differs from preflight reference")

    def test_proof_off_counter_change_is_rejected(self):
        self.commands["aot"] = self.stub("aot", "wrong-count")
        self.certify()
        with self.assertRaisesRegex(runner.Failure, "AOT output differs from certificate reference"):
            runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 5)

    def test_unexpected_proof_off_output_is_not_filtered(self):
        self.commands["aot"] = self.stub("aot", "extra-output")
        self.certify()
        with self.assertRaisesRegex(runner.Failure, "AOT output differs from certificate reference"):
            runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 5)

    def sat(self):
        self.cnf.write_text("p cnf 1 1\n1 0\n")
        self.case.update(sha256=runner.sha256(self.cnf), verdict="SATISFIABLE")

    def test_valid_sat_and_native_model_checks(self):
        self.sat()
        self.certify()
        rows = runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 10)
        self.assertEqual(rows[0]["n"], 5)
        self.assertNotIn(b"v ", self.case["reference"])

    def test_invalid_aot_model_is_rejected(self):
        self.sat()
        self.rejected("aot", "bad-model", "does not satisfy input clause")

    def test_missing_aot_model_is_rejected(self):
        self.sat()
        self.rejected("aot", "missing-model", "exactly one v-line")

    def test_invalid_native_model_is_rejected(self):
        self.sat()
        self.rejected("native", "bad-model", "does not satisfy input clause")

    def test_model_shapes_are_fail_closed(self):
        self.sat()
        for data in (b"v 0\n", b"v 1 1 0\n", b"v 1 -1 0\n", b"v 2 0\n", b"v 1\n", b"v 1 0 extra\n", b"v 1 0\nv 1 0\n"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                certificate.check_model(self.cnf, data)

    def test_candidate_needs_its_own_certificate(self):
        self.commands = {"aot": self.commands["aot"], "candidate": self.stub("candidate"), "native": self.commands["native"]}
        self.certify()
        self.assertEqual(self.case["certificate_evidence"]["arms"], ["aot", "candidate"])
        self.assertTrue((self.output / "certificates/synthetic/candidate-checker/process.json").is_file())
        self.case["certificate_evidence"]["arms"].remove("candidate")
        with self.assertRaisesRegex(runner.Failure, "timed arm lacks a certificate"):
            runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 5, "synthetic")

    def test_missing_vm_anchor_is_rejected(self):
        with self.assertRaisesRegex(runner.Failure, "requires both VM regime anchors"):
            certificate.preflight(runner, self.args, self.output, dict(os.environ), time.monotonic() + 5,
                                  [{"name": "tseitin-3x3-odd"}], self.commands)

    def test_shared_normalizer_preserves_valid_tail_and_rejects_junk(self):
        source = self.root / "source.cnf"
        prepared = self.root / "prepared.cnf"
        for tail, expected in ((b"%\n0\n\n", 0), (b"%\nJUNK\n", 65)):
            source.write_bytes(self.cnf.read_bytes() + tail)
            result = subprocess.run(["awk", "-f", str(runner.ROOT / "benchmarks/normalize_cnf.awk"), str(source)], capture_output=True)
            self.assertEqual(result.returncode, expected)
            if not expected:
                prepared.write_bytes(result.stdout)
                certificate.cnf_preservation.compare(source, prepared)
                prepared.write_text("p cnf 1 1\n1 0\n")
                with self.assertRaisesRegex(ValueError, "ordered DIMACS token lines changed"):
                    certificate.cnf_preservation.compare(source, prepared)

    def test_preparation_runs_existing_identity_and_preservation_checks(self):
        emitter = self.root / "emitter.py"
        emitter.write_text("#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\n"
                           "sys.stdout.buffer.write(Path(" + repr(str(runner.ROOT / "tests/fixtures/tseitin_torus_3x3_odd.cnf")) + ").read_bytes())\n")
        emitter.chmod(0o700)
        self.args.vm = emitter
        case = certificate.prepare_rung(runner, self.args, self.output, dict(os.environ), time.monotonic() + 5, "3x3")
        self.assertEqual(case["validation"], "certificate")
        certificate.cnf_preservation.compare(runner.ROOT / "tests/fixtures/tseitin_torus_3x3_odd.cnf", case["cnf"])
        with self.assertRaisesRegex(runner.Failure, "certificate command failed rc=1.*identity"):
            certificate.prepare_rung(runner, self.args, self.output, dict(os.environ), time.monotonic() + 5, "4x5")

    def pilot(self, slow, pilot_only=False):
        self.args.extra_rung = ["4x5"]
        self.args.pilot_only = pilot_only
        anchors = [dict(self.case, name="tseitin-" + rung + "-odd", extra_rung=False) for rung in ("3x3", "4x4")]
        extra = dict(self.case, name="tseitin-4x5-odd")
        real_run = runner.run_process
        def process(command, directory, *args, **kwargs):
            record = real_run(command, directory, *args, **kwargs)
            if slow and "pilots" in directory.parts:
                record["wall_ns"] = 601_000_000_000
            return record
        with patch.object(certificate, "prepare_rung", return_value=extra), patch.object(runner, "run_process", side_effect=process):
            return certificate.preflight(runner, self.args, self.output, dict(os.environ), time.monotonic() + 10,
                                         anchors, self.commands)

    def test_extra_rung_pilots_are_complete_and_proof_off(self):
        cases = self.pilot(False)
        pilots = json.loads((self.output / "pilots.json").read_text())
        self.assertEqual({row["arm"] for row in pilots}, {"aot", "native"})
        self.assertEqual(len(pilots), 2)
        self.assertTrue(all(row["validated"] and "--proof" not in row["command"] for row in pilots))
        self.assertEqual({case["validation"] for case in cases}, {"certificate", "vm-differential+certificate"})

    def test_slow_pilot_prevents_five_run_timing(self):
        with self.assertRaisesRegex(runner.Failure, "pilot exceeded 600 seconds"):
            self.pilot(True)
        self.assertTrue((self.output / "pilots.json").is_file())
        self.assertFalse((self.output / "samples.jsonl").exists())

    def test_explicit_pilot_only_keeps_slow_pilot_evidence(self):
        self.assertEqual(len(self.pilot(True, pilot_only=True)), 3)
        self.assertFalse((self.output / "summary.json").exists())


class CertificateOptionsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ems-certificate-options-")
        self.root = Path(self.temporary.name)
        (self.root / "aot").mkdir()
        (self.root / "aot/build.sh").write_text("# never executed\n")
        (self.root / "src").mkdir()
        (self.root / "src/eigenscript").symlink_to(sys.executable)
        self.argv = ["--aot-binary", sys.executable, "--aot-source-dir", str(self.root),
                     "--runtime-dir", str(self.root), "--minisat-binary", sys.executable,
                     "--output", str(self.root / "new-output"), "--build-command", "synthetic"]
        self.source = self.root / "generated.c"
        self.source.write_text("/* synthetic source */\n")

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_stays_vm_differential(self):
        self.assertEqual(runner.arguments(self.argv).validation, "vm-differential")

    def test_certificate_requires_checker_and_generated_source(self):
        with self.assertRaisesRegex(runner.Failure, "requires --drat-trim"):
            runner.arguments(self.argv + ["--validation", "certificate"])
        with self.assertRaisesRegex(runner.Failure, "requires --aot-generated-source"):
            runner.arguments(self.argv + ["--validation", "certificate", "--drat-trim", sys.executable])

    def test_certificate_selection_is_explicit(self):
        with self.assertRaisesRegex(runner.Failure, "require --validation certificate"):
            runner.arguments(self.argv + ["--pilot-only"])
        args = runner.arguments(self.argv + ["--validation", "certificate", "--drat-trim", sys.executable,
                                           "--aot-generated-source", str(self.source), "--pilot-only"])
        self.assertEqual(args.validation, "certificate")
        self.assertTrue(args.pilot_only)

    def test_process_ceiling_is_two_hours(self):
        self.assertEqual(runner.arguments(self.argv + ["--timeout", "7200"]).timeout, 7200)
        with self.assertRaisesRegex(runner.Failure, "process maximum 7200s"):
            runner.arguments(self.argv + ["--timeout", "7201"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
