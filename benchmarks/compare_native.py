#!/usr/bin/env python3
"""Five external-process wall samples after the existing native/VM/AOT oracle.

The preflight owns CNF preparation, identity and VM/AOT correctness. This
runner consumes its retained inputs/references and validates every timed run.
Linux/POSIX only: a signal deadline leaves waitpid blocking, avoiding Python's
wait(timeout=...) polling/rounding on MiniSat's millisecond-scale runs.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time

sys.dont_write_bytecode = True
import certificate_validation

ROOT = Path(__file__).resolve().parents[1]
REPETITIONS = 5
ARMS = ("aot", "native")
EMS_POLICY = "CDCL current defaults (regime C); --cdcl; no policy overrides"
NATIVE_POLICY = "native MiniSat executable defaults; no policy overrides"
TIMING = ("perf_counter_ns before process launch through blocking waitpid return; "
          "includes launch, input parsing, solving, output and process exit; "
          "excludes preflight and sample validation")
TIMING_SUFFIX = re.compile(rb" ms=[0-9]+(?:[.][0-9]+)?(?:[eE][-+]?[0-9]+)?$")


class Failure(RuntimeError):
    pass


class ProcessCancelled(Exception):
    pass


def require(condition, message):
    if not condition:
        raise Failure(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def executable(value):
    path = Path(value).resolve()
    require(path.is_file() and os.access(path, os.X_OK), f"not executable: {path}")
    return path


def native_package(path):
    """Package metadata is attributed as metadata, not assumed build provenance."""
    if not shutil.which("dpkg-query"):
        return {"status": "unavailable; binary SHA256 is recorded"}
    owner = subprocess.run(["dpkg-query", "-S", str(path)], capture_output=True, text=True)
    if owner.returncode != 0:
        return {"status": "no package owner found; binary SHA256 is recorded"}
    package = owner.stdout.split(": ", 1)[0]
    detail = subprocess.run(["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${source:Package}\t${source:Version}\n", package],
                            capture_output=True, text=True)
    return {"owner_query": owner.stdout, "package_version_source_package_source_version": detail.stdout,
            "status": "installed package metadata; does not certify that executable bytes are unmodified"}


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args])


def source_snapshot(directory):
    """Record tracked and nonignored untracked bytes, including local edits."""
    directory = Path(directory).resolve()
    files = {}
    for raw in git(directory, "ls-files", "-z", "--cached", "--others", "--exclude-standard").split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = directory / name
        if path.is_symlink():
            files[name] = {"symlink": os.readlink(path)}
        elif path.is_file():
            files[name] = {"sha256": sha256(path)}
        else:
            files[name] = {"missing": True}
    return {"path": str(directory), "head": git(directory, "rev-parse", "HEAD").decode().strip(),
            "status": git(directory, "status", "--porcelain=v1", "--untracked-files=all").decode(),
            "files": files}


def normalized_ems(data):
    # Same narrow output contract as run_native_oracle.sh: preserve every byte
    # except a trailing numeric timing field on a comment line, including EOF.
    lines = data.split(b"\n")
    return b"\n".join(TIMING_SUFFIX.sub(b"", line) if line.startswith(b"c ") else line
                      for line in lines)


def ems_report(data):
    verdicts = re.findall(rb"^s (SATISFIABLE|UNSATISFIABLE)$", data, re.M)
    all_verdicts = re.findall(rb"^s .*?$", data, re.M)
    counts = []
    for line in data.split(b"\n"):
        if line.startswith(b"c "):
            counts.extend(field.removeprefix(b"conflicts=") for field in line.split()
                          if field.startswith(b"conflicts="))
    require(len(verdicts) == len(all_verdicts) == 1 and len(counts) == 1
            and re.fullmatch(rb"[0-9]+", counts[0]) is not None,
            "EMS report needs exactly one verdict and integer conflicts field")
    return verdicts[0].decode(), int(counts[0])


def native_report(data, result, returncode):
    verdicts = re.findall(rb"^(SATISFIABLE|UNSATISFIABLE)$", data, re.M)
    counts = [line.split() for line in data.split(b"\n") if re.match(rb"^conflicts[ \t]*:", line)]
    cpu = [line.split() for line in data.split(b"\n") if re.match(rb"^CPU time[ \t]*:", line)]
    require(len(verdicts) == len(counts) == len(cpu) == 1 and len(counts[0]) >= 3
            and re.fullmatch(rb"[0-9]+", counts[0][2]) is not None
            and len(cpu[0]) == 5 and cpu[0][4] == b"s"
            and re.fullmatch(rb"[0-9]+(?:[.][0-9]+)?(?:[eE][-+]?[0-9]+)?", cpu[0][3]) is not None
            and math.isfinite(float(cpu[0][3])),
            "native report needs exactly one verdict, integer conflicts and CPU time")
    require(result.is_file(), "native result file missing")
    status, separator, _ = result.read_bytes().partition(b"\n")
    expected_status = b"SAT" if verdicts[0] == b"SATISFIABLE" else b"UNSAT"
    expected_code = 10 if expected_status == b"SAT" else 20
    require(separator and status == expected_status and returncode == expected_code,
            "native stdout/result/exit disagree")
    return verdicts[0].decode(), int(counts[0][2])


def session_members(session_id):
    """Linux process ownership includes all GNU timeout-created process groups."""
    members = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            # comm is parenthesized and may itself contain spaces or ')'.
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[3]) == session_id and fields[0] not in ("Z", "X"):
            members.append(int(entry.name))
    return members


def kill_session(session_id):
    """Stop spawning, kill every owned session member, and verify quiescence.

    start_new_session makes the launched PID the session ID. GNU timeout
    changes process groups but stays in that session. Scanning/killing only
    occurs on failure, outside any accepted timing sample. This contains the
    trusted oracle topology; it is not a sandbox for children calling setsid.
    """
    deadline = time.monotonic() + 5
    signaled = set()
    while True:
        members = session_members(session_id)
        if not members:
            return {"session_id": session_id, "signaled_pids": sorted(signaled), "remaining_live": []}
        # Freeze parents before the second snapshot to narrow the fork race.
        # Repeat to include children created while the first scan was running.
        for pid in members:
            try:
                os.kill(pid, signal.SIGSTOP)
            except ProcessLookupError:
                pass
        for pid in session_members(session_id):
            try:
                os.kill(pid, signal.SIGKILL)
                signaled.add(pid)
            except ProcessLookupError:
                pass
        if time.monotonic() >= deadline:
            return {"session_id": session_id, "signaled_pids": sorted(signaled),
                    "remaining_live": session_members(session_id)}
        time.sleep(0.005)


def run_process(command, directory, timeout, environment, cwd=ROOT):
    """Retain output/exit evidence even on failure; no timeout polling in timer."""
    directory.mkdir(parents=True, exist_ok=False)
    process = None
    received_signal = None
    can_raise = False
    cleanup = None
    handled_signals = (signal.SIGALRM, signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    previous_handlers = {number: signal.getsignal(number) for number in handled_signals}
    require(signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0), "an existing process alarm is active")

    def cancelled(number, _frame):
        nonlocal received_signal
        if received_signal is None:
            received_signal = number
        # Defer ALL cancellation during Popen until its child handle reaches
        # us. Blocking signals instead would pass the mask into the child.
        # Further signals during cleanup must not interrupt session ownership.
        if can_raise:
            raise ProcessCancelled()

    try:
        for number in handled_signals:
            signal.signal(number, cancelled)
        with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
            signal.setitimer(signal.ITIMER_REAL, timeout)
            start = time.perf_counter_ns()
            try:
                if received_signal is not None:
                    raise ProcessCancelled()
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr, cwd=cwd,
                                           env=environment, start_new_session=True)
                can_raise = True
                if received_signal is not None:
                    raise ProcessCancelled()
                returncode = process.wait()
                elapsed_ns = time.perf_counter_ns() - start
                can_raise = False
            except (ProcessCancelled, KeyboardInterrupt):
                can_raise = False
                if received_signal is None:
                    received_signal = signal.SIGINT
                signal.setitimer(signal.ITIMER_REAL, 0)
                if process is not None:
                    cleanup = kill_session(process.pid)
                    # This polling wait is on a rejected timeout path only.
                    # Keep cleanup bounded even for uninterruptible I/O.
                    try:
                        process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        pass
                elapsed_ns = time.perf_counter_ns() - start
                returncode = process.returncode if process is not None else None
            finally:
                can_raise = False
                signal.setitimer(signal.ITIMER_REAL, 0)
        interrupted_signal = received_signal if received_signal != signal.SIGALRM else None
        record = {"command": [str(arg) for arg in command], "cwd": str(cwd),
                  "wall_ns": elapsed_ns, "returncode": returncode, "timeout_seconds": timeout,
                  "timed_out": received_signal == signal.SIGALRM, "interrupted_signal": interrupted_signal,
                  "directory": str(directory), "cleanup": cleanup}
        write_json(directory / "process.json", record)
        require(cleanup is None or not cleanup["remaining_live"], f"cancellation cleanup left live session members: {directory}")
        require(received_signal != signal.SIGALRM, f"process timeout/interruption: {directory}")
        require(received_signal is None,
                f"process interrupted by {signal.Signals(received_signal).name if received_signal is not None else 'unknown'}: {directory}")
        return record
    finally:
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)


def remaining(deadline, cap):
    budget = deadline - time.monotonic()
    require(budget > 0, "total run budget exhausted")
    return min(cap, budget)


def oracle_preflight(args, output, environment, deadline):
    inputs = output / "preflight-inputs"
    inputs.mkdir()
    pigeonhole = inputs / "pigeonhole_6_5.cnf"
    shutil.copyfile(ROOT / "tests/fixtures/pigeonhole_6_5.cnf", pigeonhole)
    certificate_mode = getattr(args, "validation", "vm-differential") == "certificate"
    rungs = ["3x3", "4x4", *([] if certificate_mode else args.extra_rung)]
    if certificate_mode:
        shutil.copyfile(ROOT / "tests/fixtures/simple_sat.cnf", inputs / "simple_sat.cnf")
    command = ["bash", str(ROOT / "benchmarks/run_native_oracle.sh"), "--aot", "on",
               "--rungs", " ".join(rungs), "--instances", str(inputs),
               "--timeout", str(args.timeout)]
    env = dict(environment, KEEP_WORK="1", EIGS_DIR=str(args.runtime_dir),
               EIGENSCRIPT_BIN=str(args.vm), MINISAT_BIN=str(args.minisat_binary),
               AOT_BUILD=str(args.aot_source_dir / "aot/build.sh"), AOT_BINARY=str(args.aot_binary))
    record = run_process(command, output / "preflight-process",
                         remaining(deadline, args.budget_seconds), env)
    require(record["returncode"] == 0, "correctness preflight failed; see preflight-process/stdout and stderr")
    data = (output / "preflight-process/stdout").read_text()
    count = len(rungs) + 1 + int(certificate_mode)
    summary = f"SUMMARY PASS selected={count} passed={count} native={count} VM={count} AOT={count}"
    require([line for line in data.splitlines() if line.startswith("SUMMARY ")] == [summary],
            "correctness preflight completion population differs")
    artifacts = [line.removeprefix("Artifacts: ") for line in data.splitlines() if line.startswith("Artifacts: ")]
    require(len(artifacts) == 1, "correctness preflight did not retain one artifact directory")
    work = Path(artifacts[0]).resolve()
    require(work.parent == Path("/tmp") and work.name.startswith("ems-native-oracle.") and work.is_dir(),
            "unexpected oracle artifact directory")
    shutil.move(str(work), output / "oracle")
    expected = {f"tseitin-{rung}-odd": f"tseitin-{rung}-odd" for rung in rungs}
    expected[str(pigeonhole)] = "pigeonhole-6-5"
    if certificate_mode:
        expected[str(inputs / "simple_sat.cnf")] = "simple-sat"
    cases = []
    seen = set()
    for directory in sorted((output / "oracle").glob("case.*")):
        name = (directory / "name").read_text().removesuffix("\n")
        require(name in expected and name not in seen, f"unexpected/duplicate oracle case: {name}")
        seen.add(name)
        reference = (directory / "vm.out.normalized").read_bytes()
        verdict, ems_conflicts = ems_report(reference)
        native_verdict, native_conflicts = native_report((directory / "native.out").read_bytes(),
                                                        directory / "native.result",
                                                        10 if verdict == "SATISFIABLE" else 20)
        expected_verdict = "SATISFIABLE" if expected[name] == "simple-sat" else "UNSATISFIABLE"
        require(native_verdict == verdict == expected_verdict, f"unexpected baseline verdict: {name}")
        cases.append({"name": expected[name], "cnf": directory / "input.cnf",
                      "sha256": sha256(directory / "input.cnf"), "reference": reference,
                      "verdict": verdict, "aot_conflicts": ems_conflicts, "native_conflicts": native_conflicts,
                      "validation": "vm-differential",
                      "input_evidence": [str(path) for path in directory.rglob("*") if path.is_file()]})
    require(seen == set(expected), "oracle artifact cases are incomplete")
    return sorted(cases, key=lambda case: case["name"])


def validate_sample(case, arm, record):
    directory = Path(record["directory"])
    data = (directory / "stdout").read_bytes()
    if arm != "native":
        require(record["returncode"] == 0, "AOT exit must be 0")
        verdict, conflicts = ems_report(data)
        label = "certificate reference" if "certificate_evidence" in case else "preflight VM reference"
        require(normalized_ems(data) == case["reference"], "AOT output differs from " + label)
    else:
        verdict, conflicts = native_report(data, directory / "native.result", record["returncode"])
        if "certificate_evidence" in case and verdict == "SATISFIABLE":
            certificate_validation.check_model(case["cnf"], (directory / "native.result").read_bytes(), native=True)
    require(verdict == case["verdict"], "verdict differs from correctness preflight")
    require(conflicts == case[("native" if arm == "native" else "aot") + "_conflicts"],
            "conflicts differ from correctness preflight")
    return conflicts


def summarize(cases, samples, arms=ARMS, candidate_label=None):
    expected = {(case["name"], arm, repetition) for case in cases
                for arm in arms for repetition in range(1, REPETITIONS + 1)}
    keys = [(sample["case"], sample["arm"], sample["repetition"]) for sample in samples]
    require(cases and len(keys) == len(expected) and set(keys) == expected,
            "incomplete/duplicate sample population; no performance summary")
    rows = []
    for case in cases:
        row = {"case": case["name"], "input_sha256": case["sha256"], "n": REPETITIONS,
               "aot_policy": EMS_POLICY, "native_policy": NATIVE_POLICY,
               "validation": case.get("validation", "vm-differential")}
        if "candidate" in arms:
            row["candidate_policy"] = EMS_POLICY + "; candidate=" + candidate_label
        for arm in arms:
            group = [sample for sample in samples if sample["case"] == case["name"] and sample["arm"] == arm]
            require(all(sample.get("validated") is True and sample["wall_ns"] > 0 for sample in group),
                    "invalid/unvalidated sample; no performance summary")
            seconds = [sample["wall_ns"] / 1e9 for sample in group]
            conflicts = case[("native" if arm == "native" else "aot") + "_conflicts"]
            row[arm] = {"median_wall_s": statistics.median(seconds), "min_wall_s": min(seconds),
                        "max_wall_s": max(seconds), "conflicts": conflicts,
                        "median_conflicts_per_wall_second_descriptive": statistics.median(conflicts / value for value in seconds)}
        row["aot_over_native_wall_ratio_policy_confounded"] = row["aot"]["median_wall_s"] / row["native"]["median_wall_s"]
        if "candidate" in arms:
            row["baseline_over_candidate_wall_ratio_same_policy"] = row["aot"]["median_wall_s"] / row["candidate"]["median_wall_s"]
        rows.append(row)
    return rows


def measure(cases, commands, output, environment, timeout, deadline, candidate_label=None):
    samples = []
    require(cases and len({case["name"] for case in cases}) == len(cases), "empty/duplicate case population")
    arms = tuple(commands)
    require(arms in (ARMS, ("aot", "candidate", "native")), "invalid solver arm population")
    require("candidate" not in arms or candidate_label, "candidate needs an explicit label")
    binary_hashes = {arm: sha256(commands[arm]) for arm in arms}
    repetitions = range(0 if "candidate" in arms else 1, REPETITIONS + 1)
    with (output / "samples.jsonl").open("x") as ledger:
        for repetition in repetitions:
            for index, case in enumerate(cases):
                offset = (repetition + index - 1) % len(arms)
                order = ("candidate",) if repetition == 0 else arms[offset:] + arms[:offset]
                for arm in order:
                    directory = output / "samples" / case["name"] / f"{repetition}-{arm}"
                    require(sha256(case["cnf"]) == case["sha256"], f"input changed before {case['name']} {arm}")
                    require(sha256(commands[arm]) == binary_hashes[arm], f"binary changed before {case['name']} {arm}")
                    if "certificate" in case.get("validation", ""):
                        certificate_validation.verify_evidence(sys.modules[__name__], case)
                        require(arm == "native" or arm in case["certificate_evidence"]["arms"],
                                "timed arm lacks a certificate")
                    command = [str(commands[arm])]
                    if arm != "native":
                        command += ["--cdcl", str(case["cnf"])]
                    else:
                        command += [str(case["cnf"]), str(directory / "native.result")]
                    phase = "WARMUP" if repetition == 0 else "SAMPLE"
                    print(f"{phase} case={case['name']} repetition={repetition}/{REPETITIONS} arm={arm}", flush=True)
                    try:
                        record = run_process(command, directory, remaining(deadline, timeout), environment)
                        require(sha256(case["cnf"]) == case["sha256"], "input changed during timed process")
                        require(sha256(commands[arm]) == binary_hashes[arm], "binary changed during timed process")
                        conflicts = validate_sample(case, arm, record)
                        if "certificate" in case.get("validation", ""):
                            certificate_validation.verify_evidence(sys.modules[__name__], case)
                    except Failure as error:
                        raise Failure(f"case={case['name']} repetition={repetition} arm={arm}: {error}") from error
                    record.update(case=case["name"], arm=arm, repetition=repetition,
                                  conflicts=conflicts, validated=True, input_sha256=case["sha256"],
                                  binary_sha256=binary_hashes[arm], validation=case.get("validation", "vm-differential"))
                    write_json(directory / "validation.json", record)
                    if repetition == 0:
                        continue
                    ledger.write(json.dumps(record, sort_keys=True) + "\n")
                    ledger.flush()
                    samples.append(record)
    return summarize(cases, samples, arms, candidate_label)


def write_summary_tsv(path, rows, arms):
    with Path(path).open("w") as table:
        table.write("case\tvalidation\tarm\tpolicy\tn\tmedian_wall_s\tmin_wall_s\tmax_wall_s\tconflicts\tdescriptive_conflicts_per_wall_second\n")
        for row in rows:
            for arm in arms:
                value = row[arm]
                table.write(f"{row['case']}\t{row['validation']}\t{arm}\t{row[arm + '_policy']}\t{REPETITIONS}\t"
                            f"{value['median_wall_s']:.9f}\t{value['min_wall_s']:.9f}\t{value['max_wall_s']:.9f}\t"
                            f"{value['conflicts']}\t{value['median_conflicts_per_wall_second_descriptive']:.3f}\n")


def arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aot-binary", required=True, type=Path, help="fresh prebuilt EMS binary; never builds")
    parser.add_argument("--aot-source-dir", required=True, type=Path, help="compiler source used for this binary")
    parser.add_argument("--runtime-dir", type=Path, default=Path("/home/jon/src/wt/es-v043"))
    parser.add_argument("--minisat-binary", type=Path, default=Path("/usr/bin/minisat"))
    parser.add_argument("--output", required=True, type=Path, help="new artifact directory (must not exist)")
    parser.add_argument("--extra-rung", action="append", default=[], metavar="ROWSxCOLS")
    parser.add_argument("--validation", choices=("vm-differential", "certificate"), default="vm-differential",
                        help="certificate keeps VM anchors but verifies extra rungs through DRAT/models")
    parser.add_argument("--drat-trim", type=Path, help="required executable for certificate validation")
    parser.add_argument("--aot-generated-source", type=Path, help="exact generated C used for AOT; required in certificate mode")
    parser.add_argument("--pilot-only", action="store_true", help="certificate preflight/pilots only; no n=5 timing report")
    parser.add_argument("--timeout", type=int, help="seconds per process; default 120; mandatory for extra rungs")
    parser.add_argument("--budget-seconds", type=int, help="total preflight/timing budget; default 1800; mandatory for extra rungs")
    parser.add_argument("--cpu", type=int, help="pin this runner and child processes to an available Linux CPU")
    parser.add_argument("--build-command", required=True, help="exact command used to build supplied AOT binary (recorded, never executed)")
    parser.add_argument("--build-log", type=Path, help="copy build transcript into provenance")
    parser.add_argument("--candidate-binary", type=Path, help="optional second prebuilt AOT in the same sampling schedule")
    parser.add_argument("--candidate-label", help="explicit experiment label, e.g. 'timing-only count-scan ceiling'")
    parser.add_argument("--candidate-source", type=Path, help="exact modified generated C source used for the candidate")
    parser.add_argument("--candidate-build-command", help="exact candidate build command (recorded, never executed)")
    parser.add_argument("--candidate-build-log", type=Path)
    args = parser.parse_args(argv)
    require(sys.platform.startswith("linux"), "this timing runner requires Linux")
    require(not args.extra_rung or (args.timeout is not None and args.budget_seconds is not None),
            "extra rungs require explicit --timeout and --budget-seconds")
    args.timeout = 120 if args.timeout is None else args.timeout
    args.budget_seconds = 1800 if args.budget_seconds is None else args.budget_seconds
    require(0 < args.timeout <= 7200 and 0 < args.budget_seconds <= 604800, "invalid timeout or total budget (process maximum 7200s)")
    if args.validation == "certificate":
        require(args.drat_trim is not None, "certificate validation requires --drat-trim")
        args.drat_trim = executable(args.drat_trim)
        require(args.aot_generated_source is not None, "certificate validation requires --aot-generated-source")
    else:
        require(args.drat_trim is None and not args.pilot_only, "--drat-trim/--pilot-only require --validation certificate")
    if args.aot_generated_source:
        args.aot_generated_source = args.aot_generated_source.resolve()
        require(args.aot_generated_source.is_file(), "AOT generated source is not a file")
    seen = {"3x3", "4x4"}
    for rung in args.extra_rung:
        require(re.fullmatch(r"[1-9][0-9]?x[1-9][0-9]?", rung) is not None, f"invalid extra rung: {rung}")
        require(all(3 <= int(value) <= 99 for value in rung.split("x")) and rung not in seen,
                f"extra rung must be unique, dimensions 3..99: {rung}")
        seen.add(rung)
    for field in ("aot_source_dir", "runtime_dir", "output"):
        setattr(args, field, getattr(args, field).resolve())
    require(not any(character in str(args.output) for character in "\n\r\t"), "output path must not contain record separators")
    args.aot_binary = executable(args.aot_binary)
    args.minisat_binary = executable(args.minisat_binary)
    args.vm = executable(args.runtime_dir / "src/eigenscript")
    if args.candidate_binary:
        args.candidate_binary = executable(args.candidate_binary)
        require(args.candidate_label and args.candidate_build_command and args.candidate_source,
                "candidate requires --candidate-label, --candidate-source and --candidate-build-command")
        args.candidate_source = args.candidate_source.resolve()
        require(args.candidate_source.is_file(), "candidate source is not a file")
    else:
        require(not any((args.candidate_label, args.candidate_source, args.candidate_build_command, args.candidate_build_log)),
                "candidate provenance requires --candidate-binary")
    require((args.aot_source_dir / "aot/build.sh").is_file(), "AOT source directory lacks aot/build.sh")
    require(args.build_command.strip(), "build command must be nonempty")
    if args.cpu is not None:
        require(args.cpu in os.sched_getaffinity(0), "requested CPU is outside current affinity")
        os.sched_setaffinity(0, {args.cpu})
    return args


def main(argv=None):
    output = None
    try:
        args = arguments(argv)
        args.output.mkdir(parents=True, exist_ok=False)
        output = args.output
        for tree in (ROOT, args.runtime_dir, args.aot_source_dir):
            if output.is_relative_to(tree):
                ignored = subprocess.run(["git", "-C", str(tree), "check-ignore", "-q", str(output) + "/placeholder"])
                require(ignored.returncode == 0, "output inside a source checkout must be gitignored (or use /tmp)")
        deadline = time.monotonic() + args.budget_seconds
        environment = dict(os.environ, LC_ALL="C")
        sources = {label: source_snapshot(path) for label, path in
                   (("ems", ROOT), ("runtime", args.runtime_dir), ("aot", args.aot_source_dir))}
        commands = {"aot": args.aot_binary}
        if args.candidate_binary:
            commands["candidate"] = args.candidate_binary
        commands["native"] = args.minisat_binary
        tools_used = {**commands, "vm": args.vm}
        if args.drat_trim:
            tools_used["drat-trim"] = args.drat_trim
        binaries = {label: {"path": str(path), "sha256": sha256(path)} for label, path in tools_used.items()}
        provenance = output / "provenance"
        provenance.mkdir()
        for label, snapshot in sources.items():
            (provenance / f"{label}.patch").write_bytes(git(snapshot["path"], "diff", "--binary", "HEAD"))
        if args.build_log:
            shutil.copyfile(args.build_log, provenance / "aot-build.log")
        generated_source = None
        if args.aot_generated_source:
            generated_source = {"path": str(args.aot_generated_source), "sha256": sha256(args.aot_generated_source)}
            shutil.copyfile(args.aot_generated_source, provenance / "aot-source.c")
        candidate = None
        if args.candidate_binary:
            candidate = {"label": args.candidate_label, "source_path": str(args.candidate_source),
                         "source_sha256": sha256(args.candidate_source),
                         "build_command_declared_by_caller": args.candidate_build_command,
                         "scope": "timing experiment; measured stdout matches the selected validation reference; no broader correctness claim"}
            shutil.copyfile(args.candidate_source, provenance / "candidate-source.c")
            if args.candidate_build_log:
                shutil.copyfile(args.candidate_build_log, provenance / "candidate-build.log")
        manifest = {"schema": 2, "status": "incomplete", "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "validation": args.validation, "pilot_only": args.pilot_only,
                    "n": REPETITIONS, "timing_scope": TIMING, "aot_policy": EMS_POLICY, "native_policy": NATIVE_POLICY,
                    "warmup": ("strict VM anchors, each AOT arm certified on every case, extra-rung proof-off pilots" if args.validation == "certificate"
                               else "one unmeasured native/VM/baseline-AOT correctness preflight per case; optional candidate gets one unmeasured validated run per case"),
                    "ordering": "sequential arm groups; rotate first arm by repetition and case index",
                    "arms": list(commands), "candidate": candidate,
                    "generated_source": generated_source,
                    "timeout_seconds": args.timeout, "budget_seconds": args.budget_seconds,
                    "extra_rungs": args.extra_rung, "sources": sources, "binaries": binaries,
                    "build_command_declared_by_caller": args.build_command,
                    "build_provenance_limit": "source and binary hashes are captured; caller supplies their build relationship",
                    "native_package": native_package(args.minisat_binary),
                    "host": {"platform": platform.platform(), "python": sys.version, "machine": platform.machine(),
                             "affinity": sorted(os.sched_getaffinity(0)), "cpuinfo": Path("/proc/cpuinfo").read_text(),
                             "loadavg_at_start": os.getloadavg()},
                    "runtime_environment": {key: value for key, value in environment.items()
                                            if key.startswith(("EIGS", "AOT_", "OMP_", "MALLOC_", "LD_")) or key == "LC_ALL"}}
        write_json(output / "manifest.json", manifest)
        cases = oracle_preflight(args, output, environment, deadline)
        if args.validation == "certificate":
            cases = certificate_validation.preflight(sys.modules[__name__], args, output, environment, deadline, cases, commands)
        write_json(output / "cases.json", [{key: str(value) if isinstance(value, Path) else value
                                            for key, value in case.items() if key != "reference"} for case in cases])
        rows = None if args.pilot_only else measure(cases, commands, output, environment, args.timeout, deadline, args.candidate_label)
        require(time.monotonic() <= deadline, "total run budget exhausted before completion")
        require(all(sha256(entry["path"]) == entry["sha256"] for entry in binaries.values()), "binary changed during run")
        require(candidate is None or sha256(candidate["source_path"]) == candidate["source_sha256"],
                "candidate source changed during run")
        require(generated_source is None or sha256(generated_source["path"]) == generated_source["sha256"],
                "AOT generated source changed during run")
        require(all(source_snapshot(snapshot["path"]) == snapshot for snapshot in sources.values()), "source changed during run")
        if args.validation == "certificate":
            for case in cases:
                certificate_validation.verify_evidence(sys.modules[__name__], case)
        if args.pilot_only:
            manifest["status"] = "pilot-complete"
            manifest["validated_samples"] = 0
            manifest["performance_status"] = "incomplete; no five-run measurements requested"
            write_json(output / "manifest.json", manifest)
            print(f"PILOT COMPLETE cases={len(cases)} arms={len(commands)} validated_samples=0 performance=incomplete artifacts={output}")
            return 0
        write_json(output / "summary.json", {"status": "complete", "timing_scope": TIMING, "rows": rows,
                                            "validation": args.validation,
                                            "interpretation": "AOT/native wall ratios and conflicts/sec are descriptive across different solver policies"})
        write_summary_tsv(output / "summary.tsv", rows, commands)
        manifest["status"] = "complete"
        manifest["validated_samples"] = len(cases) * len(commands) * REPETITIONS
        write_json(output / "manifest.json", manifest)
        print(f"SUMMARY COMPLETE cases={len(cases)} arms={len(commands)} n={REPETITIONS} validated_samples={manifest['validated_samples']} artifacts={output}")
        return 0
    except (Failure, OSError, subprocess.SubprocessError, ValueError) as error:
        if output is not None:
            write_json(output / "failure.json", {"status": "failed", "error": str(error)})
        print(f"FAIL {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
