#!/usr/bin/env python3
"""Lightweight process-level timing tests; no EigenScript/AOT builds or solves.

Synthetic child programs drive the same measure/validate/summarize path as the
real CLI. Formula preparation and VM/AOT correctness remain run_native_oracle.sh's
separately tested responsibility. These tests are not performance measurements.
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import compare_native as runner


EMS = b"s UNSATISFIABLE\nc vars=1 clauses=2 conflicts=2 compact_policy=deferred\n"
STUB = '''#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import sys
import time
mode = {mode!r}
arm = {arm!r}
if mode == "timeout":
    time.sleep(2)
if mode == "descendant":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
    Path(sys.argv[-1] + ".pid").write_text(str(child.pid))
    time.sleep(2)
time.sleep(0.01)
if arm == "aot":
    output = {ems!r}[:-1] + b" ms=0.000001\\n"
    if mode == "wrong-output":
        output += b"c planted extra byte\\n"
    if mode == "wrong-verdict":
        output = output.replace(b"UNSATISFIABLE", b"SATISFIABLE")
    if mode == "input-change":
        with open(sys.argv[-1], "ab") as f:
            f.write(b"c changed\\n")
    sys.stdout.buffer.write(output)
    sys.exit(7 if mode == "nonzero" else 0)
conflicts = 4 if mode == "wrong-count" else 3
print("conflicts :", conflicts, "(999999 /sec)")
print("CPU time : 0.000001 s")
print("UNSATISFIABLE")
if mode == "duplicate-cpu":
    print("CPU time : bad s")
if mode != "missing-result":
    Path(sys.argv[-1]).write_text("SAT\\n" if mode == "wrong-result" else "UNSAT\\n")
sys.exit(0 if mode == "nonzero" else 20)
'''


class ProcessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ems-wall-selftest-")
        self.root = Path(self.temporary.name)
        self.output = self.root / "output"
        self.output.mkdir()
        cnf = self.root / "input.cnf"
        cnf.write_text("p cnf 1 2\n1 0\n-1 0\n")
        self.case = {"name": "synthetic-unsat", "cnf": cnf, "sha256": runner.sha256(cnf),
                     "reference": EMS, "verdict": "UNSATISFIABLE", "aot_conflicts": 2, "native_conflicts": 3}
        self.commands = {arm: self.stub(arm, "clean") for arm in runner.ARMS}

    def tearDown(self):
        self.temporary.cleanup()

    def stub(self, arm, mode):
        path = self.root / (arm + ".py")
        path.write_text(STUB.format(mode=mode, arm=arm, ems=EMS))
        path.chmod(0o700)
        return path

    def run_samples(self, timeout=1):
        return runner.measure([self.case], self.commands, self.output, dict(os.environ),
                              timeout, time.monotonic() + 10)

    def rejected(self, arm, mode, evidence, timeout=1):
        self.commands[arm] = self.stub(arm, mode)
        with self.assertRaisesRegex(runner.Failure, evidence):
            self.run_samples(timeout)
        self.assertFalse((self.output / "summary.json").exists())

    def test_real_processes_five_samples_each(self):
        previous_handlers = {sig: signal.getsignal(sig) for sig in
                             (signal.SIGALRM, signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        rows = self.run_samples()
        self.assertEqual({sig: signal.getsignal(sig) for sig in previous_handlers}, previous_handlers)
        samples = [json.loads(line) for line in (self.output / "samples.jsonl").read_text().splitlines()]
        self.assertEqual(len(samples), 10)
        self.assertEqual([(sample["repetition"], sample["arm"]) for sample in samples],
                         [(1, "aot"), (1, "native"), (2, "native"), (2, "aot"),
                          (3, "aot"), (3, "native"), (4, "native"), (4, "aot"), (5, "aot"), (5, "native")])
        for sample in samples:
            self.assertGreaterEqual(sample["wall_ns"], 10_000_000)
            self.assertEqual(sample["input_sha256"], self.case["sha256"])
            self.assertTrue((Path(sample["directory"]) / "process.json").is_file())
        self.assertEqual(rows[0]["n"], 5)
        self.assertEqual(rows[0]["aot"]["conflicts"], 2)
        self.assertEqual(rows[0]["native"]["conflicts"], 3)
        # Child reports microsecond internal/CPU time. The external stopwatch
        # must include its 10 ms sleep and startup for BOTH implementations.
        self.assertGreaterEqual(rows[0]["aot"]["median_wall_s"], 0.01)
        self.assertGreaterEqual(rows[0]["native"]["median_wall_s"], 0.01)

    def test_aot_added_output_is_red(self):
        self.rejected("aot", "wrong-output", "arm=aot: AOT output differs")

    def test_candidate_is_interleaved_and_separately_counted(self):
        candidate = self.root / "candidate.py"
        candidate.write_text(STUB.format(mode="clean", arm="aot", ems=EMS))
        candidate.chmod(0o700)
        commands = {"aot": self.commands["aot"], "candidate": candidate, "native": self.commands["native"]}
        rows = runner.measure([self.case], commands, self.output, dict(os.environ), 1,
                              time.monotonic() + 10, "timing-only synthetic ceiling")
        samples = [json.loads(line) for line in (self.output / "samples.jsonl").read_text().splitlines()]
        self.assertEqual(len(samples), 15)
        self.assertEqual([sample["arm"] for sample in samples[:9]],
                         ["aot", "candidate", "native", "candidate", "native", "aot", "native", "aot", "candidate"])
        self.assertEqual({arm: sum(sample["arm"] == arm for sample in samples) for arm in commands},
                         {"aot": 5, "candidate": 5, "native": 5})
        self.assertEqual(rows[0]["candidate"]["conflicts"], 2)
        self.assertIn("timing-only synthetic ceiling", rows[0]["candidate_policy"])
        self.assertGreater(rows[0]["baseline_over_candidate_wall_ratio_same_policy"], 0)
        self.assertTrue((self.output / "samples/synthetic-unsat/0-candidate/validation.json").is_file())

    def test_candidate_bad_output_is_red_before_samples(self):
        candidate = self.root / "candidate.py"
        candidate.write_text(STUB.format(mode="wrong-output", arm="aot", ems=EMS))
        candidate.chmod(0o700)
        commands = {"aot": self.commands["aot"], "candidate": candidate, "native": self.commands["native"]}
        with self.assertRaisesRegex(runner.Failure, "repetition=0 arm=candidate: AOT output differs"):
            runner.measure([self.case], commands, self.output, dict(os.environ), 1,
                           time.monotonic() + 10, "timing-only broken ceiling")
        self.assertEqual((self.output / "samples.jsonl").read_text(), "")

    def test_wrong_verdict_is_red(self):
        self.rejected("aot", "wrong-verdict", "arm=aot: AOT output differs")

    def test_aot_nonzero_is_red(self):
        self.rejected("aot", "nonzero", "arm=aot: AOT exit must be 0")

    def test_native_nonstandard_exit_is_red(self):
        self.rejected("native", "nonzero", "arm=native: native stdout/result/exit disagree")

    def test_native_result_disagreement_is_red(self):
        self.rejected("native", "wrong-result", "arm=native: native stdout/result/exit disagree")

    def test_native_missing_result_is_red(self):
        self.rejected("native", "missing-result", "arm=native: native result file missing")

    def test_native_counter_change_is_red(self):
        self.rejected("native", "wrong-count", "arm=native: conflicts differ")

    def test_native_malformed_duplicate_cpu_is_red(self):
        self.rejected("native", "duplicate-cpu", "arm=native: native report needs exactly one")

    def test_input_mutation_is_red(self):
        self.rejected("aot", "input-change", "arm=aot: input changed during")

    def test_timeout_is_red(self):
        previous_handlers = {sig: signal.getsignal(sig) for sig in
                             (signal.SIGALRM, signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
        self.rejected("aot", "timeout", "arm=aot: process timeout", timeout=0.1)
        self.assertEqual({sig: signal.getsignal(sig) for sig in previous_handlers}, previous_handlers)
        record = json.loads((self.output / "samples/synthetic-unsat/1-aot/process.json").read_text())
        self.assertTrue(record["timed_out"])
        self.assertEqual(record["returncode"], -9)

    def test_timeout_kills_process_group(self):
        self.rejected("aot", "descendant", "arm=aot: process timeout", timeout=0.2)
        pid = int(Path(str(self.case["cnf"]) + ".pid").read_text())
        state = Path(f"/proc/{pid}/stat")
        for _ in range(20):
            if not state.exists() or state.read_text().split()[2] == "Z":
                break
            time.sleep(0.01)
        self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z")

    def test_timeout_kills_gnu_timeout_process_group(self):
        self.assertIsNotNone(shutil.which("timeout"), "GNU timeout is required by the production oracle")
        child = self.root / "timeout-child.py"
        pidfile = self.root / "timeout-child.pid"
        child.write_text("import os,time\nfrom pathlib import Path\nPath(" + repr(str(pidfile))
                         + ").write_text(str(os.getpid()))\ntime.sleep(10)\n")
        try:
            with self.assertRaisesRegex(runner.Failure, "process timeout/interruption"):
                runner.run_process(["bash", "-c", 'timeout 10 "$1" "$2"; true', "probe", sys.executable, str(child)],
                                   self.output / "timeout-process", 0.4, dict(os.environ))
            pid = int(pidfile.read_text())
            self.assertFalse(self.alive(pid), "GNU timeout child escaped the runner's deadline cleanup")
        finally:
            if pidfile.exists():
                self.kill_if_alive(int(pidfile.read_text()))

    @staticmethod
    def alive(pid):
        try:
            return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] not in ("Z", "X")
        except FileNotFoundError:
            return False

    @classmethod
    def kill_if_alive(cls, pid):
        if cls.alive(pid):
            os.kill(pid, signal.SIGKILL)

    def preflight_fixture(self, budget=3):
        # The real CLI and unchanged oracle must reach their real GNU timeout
        # invocation. Only the executable it starts is synthetic; no solve/build.
        runtime = self.root / "runtime"
        (runtime / "src").mkdir(parents=True)
        pidfile = self.root / "emitter.pid"
        vm = runtime / "src/eigenscript"
        # File existence is the parent's readiness signal. Publish only a
        # complete PID: open-before-write once exposed an empty file to it.
        # Delaying the staged write keeps that window exercised every run.
        vm.write_text("#!/usr/bin/env python3\nimport os,time\nfrom pathlib import Path\npidfile=Path("
                      + repr(str(pidfile)) + ")\npending=pidfile.with_suffix('.pending')\n"
                      "with pending.open('w') as stream:\n    time.sleep(0.05)\n    stream.write(str(os.getpid()))\n"
                      "pending.replace(pidfile)\ntime.sleep(10)\n")
        vm.chmod(0o700)
        (runtime / "src/vm.c").write_text("/* synthetic runtime; never compiled */\n")
        compiler = self.root / "compiler"
        (compiler / "aot").mkdir(parents=True)
        (compiler / "aot/build.sh").write_text("# synthetic compiler; never invoked\n")
        for directory in (runtime, compiler):
            for command in (["git", "init", "-q"], ["git", "add", "."],
                            ["git", "-c", "user.name=Timing test", "-c", "user.email=timing-test@example.invalid",
                             "commit", "-qm", "Synthetic deadline fixture"]):
                subprocess.run(command, cwd=directory, check=True, capture_output=True)
        subprocess.run(["git", "tag", "v0.43.0"], cwd=runtime, check=True)
        output = self.root / "preflight-output"
        command = [sys.executable, str(Path(runner.__file__).resolve()), "--aot-binary", shutil.which("true"),
                   "--aot-source-dir", str(compiler), "--runtime-dir", str(runtime),
                   "--minisat-binary", shutil.which("true"), "--output", str(output),
                   "--build-command", "synthetic timeout test; no build or solver executes",
                   "--timeout", "20", "--budget-seconds", str(budget)]
        return command, output, pidfile

    def test_real_preflight_total_budget_kills_emitter(self):
        command, output, pidfile = self.preflight_fixture()
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("FAIL process timeout/interruption:", result.stderr)
            self.assertFalse((output / "summary.json").exists())
            record = json.loads((output / "preflight-process/process.json").read_text())
            self.assertTrue(record["timed_out"])
            self.assertTrue(pidfile.is_file(), "test must reach the actual oracle emitter process")
            pid = int(pidfile.read_text())
            self.assertFalse(self.alive(pid), "real preflight emitter escaped the total budget")
        finally:
            if pidfile.exists():
                self.kill_if_alive(int(pidfile.read_text()))

    def interrupt_preflight(self, sig):
        command, output, pidfile = self.preflight_fixture(budget=30)
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   start_new_session=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        session = None
        try:
            deadline = time.monotonic() + 8
            while not pidfile.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertTrue(pidfile.is_file(), "test must reach the actual oracle emitter before cancellation")
            session = os.getsid(int(pidfile.read_text()))
            self.assertGreaterEqual(len(runner.session_members(session)), 3, "test must include bash, timeout and emitter")
            process.send_signal(sig)
            stdout, stderr = process.communicate(timeout=8)
            self.assertEqual(runner.session_members(session), [], "signal cancellation left the preflight session alive")
            self.assertEqual(process.returncode, 1, stdout + stderr)
            self.assertIn(f"process interrupted by {sig.name}", stderr)
            self.assertFalse((output / "summary.json").exists())
            self.assertTrue((output / "failure.json").is_file())
            record = json.loads((output / "preflight-process/process.json").read_text())
            self.assertEqual(record["interrupted_signal"], sig)
            self.assertFalse(record["timed_out"])
            self.assertEqual(record["cleanup"]["remaining_live"], [])
        finally:
            if session is not None:
                runner.kill_session(session)
            if process.poll() is None:
                # Let the CLI clean up even if an assertion failed before we
                # recorded its child's session. Always close captured pipes.
                process.terminate()
            try:
                process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()

    def test_real_preflight_sigterm_cleans_session(self):
        self.interrupt_preflight(signal.SIGTERM)

    def test_real_preflight_sighup_cleans_session(self):
        self.interrupt_preflight(signal.SIGHUP)

    def test_real_preflight_sigint_cleans_session(self):
        self.interrupt_preflight(signal.SIGINT)

    def test_signals_during_popen_and_cleanup_are_deferred(self):
        # Launch a REAL process, deliver a signal before Popen returns the
        # handle to run_process, and send it again during cleanup. Run this
        # isolated so removing the handler fails the test without killing us.
        for sig in (signal.SIGALRM, signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            with self.subTest(signal=sig.name):
                root = self.root / sig.name
                root.mkdir()
                pidfile = root / "child.pid"
                driver = root / "driver.py"
                driver.write_text(f'''import os, signal, subprocess, sys
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, {str(Path(runner.__file__).resolve().parent)!r})
import compare_native as runner
real_popen = subprocess.Popen
real_cleanup = runner.kill_session
def launch(*args, **kwargs):
    child = real_popen(*args, **kwargs)
    Path({str(pidfile)!r}).write_text(str(child.pid))
    os.kill(os.getpid(), {int(sig)})
    return child
def cleanup(session_id):
    os.kill(os.getpid(), {int(sig)})
    return real_cleanup(session_id)
runner.subprocess.Popen = launch
runner.kill_session = cleanup
try:
    runner.run_process([sys.executable, "-c", "import time; time.sleep(10)"],
                       Path({str(root / 'process')!r}), 5, dict(os.environ))
except runner.Failure as error:
    print(error)
else:
    raise AssertionError("cancellation was not rejected")
''')
                try:
                    result = subprocess.run([sys.executable, "-B", str(driver)], capture_output=True, text=True, timeout=8)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue(pidfile.is_file(), "launch signal test must create a child before sending the signal")
                    self.assertFalse(self.alive(int(pidfile.read_text())), "child escaped during Popen cancellation")
                    record = json.loads((root / "process/process.json").read_text())
                    self.assertEqual(record["timed_out"], sig == signal.SIGALRM)
                    self.assertEqual(record["interrupted_signal"], None if sig == signal.SIGALRM else sig)
                    self.assertEqual(record["cleanup"]["remaining_live"], [])
                finally:
                    if pidfile.exists():
                        runner.kill_session(int(pidfile.read_text()))

    def test_expired_total_budget_is_red(self):
        with self.assertRaisesRegex(runner.Failure, "total run budget exhausted"):
            runner.measure([self.case], self.commands, self.output, dict(os.environ), 1, time.monotonic() - 1)

    def test_empty_cases_are_red(self):
        with self.assertRaisesRegex(runner.Failure, "empty/duplicate case population"):
            runner.measure([], self.commands, self.output, dict(os.environ), 1, time.monotonic() + 1)


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.cases = [{"name": "case", "sha256": "identity", "aot_conflicts": 10, "native_conflicts": 20}]
        self.samples = [{"case": "case", "arm": arm, "repetition": rep, "validated": True,
                         "wall_ns": wall * 1_000_000_000}
                        for arm in runner.ARMS for rep, wall in enumerate((9, 1, 5, 7, 3), start=1)]

    def test_known_median_and_range(self):
        row = runner.summarize(self.cases, self.samples)[0]
        self.assertEqual(row["aot"]["median_wall_s"], 5)
        self.assertEqual(row["aot"]["min_wall_s"], 1)
        self.assertEqual(row["aot"]["max_wall_s"], 9)
        self.assertEqual(row["native"]["median_conflicts_per_wall_second_descriptive"], 4)
        self.assertEqual(row["aot_over_native_wall_ratio_policy_confounded"], 1)

    def test_missing_sample_cannot_complete(self):
        with self.assertRaisesRegex(runner.Failure, "incomplete/duplicate sample population"):
            runner.summarize(self.cases, self.samples[:-1])

    def test_duplicate_cannot_replace_missing_sample(self):
        self.samples[-1] = dict(self.samples[0])
        with self.assertRaisesRegex(runner.Failure, "incomplete/duplicate sample population"):
            runner.summarize(self.cases, self.samples)

    def test_unvalidated_sample_cannot_complete(self):
        self.samples[0]["validated"] = False
        with self.assertRaisesRegex(runner.Failure, "invalid/unvalidated sample"):
            runner.summarize(self.cases, self.samples)

    def test_nonpositive_time_cannot_complete(self):
        self.samples[0]["wall_ns"] = 0
        with self.assertRaisesRegex(runner.Failure, "invalid/unvalidated sample"):
            runner.summarize(self.cases, self.samples)


if __name__ == "__main__":
    unittest.main(verbosity=2)
