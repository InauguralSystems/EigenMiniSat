# External process wall-time comparison

The first production comparison and reduction-precheck result are recorded in
[the 2026-09-10 report](NATIVE_AOT_2026-09-10.md), with all 45 raw timed samples.

`compare_native.py` compares a freshly built EMS AOT binary with native MiniSat
on identical validated CNFs. It records **five actual process wall times per
solver per input**, their median and range. This measures CLI throughput,
including process startup, parsing, solve, reporting and exit. MiniSat's CPU
seconds and EMS's internal `ms=` are retained in raw logs but never used as
the wall-time denominator.

Run on Linux with Python 3.9 or newer, one benchmark at a time. Build the AOT
binary first; this runner never builds. From the EigenMiniSat repository root:

```bash
python3 benchmarks/compare_native.py \
  --aot-binary /tmp/ems-native-20260910/ems-baseline \
  --aot-source-dir /home/jon/src/wt/ouro-ems-20260910 \
  --runtime-dir /home/jon/src/wt/es-v043 \
  --build-command 'env EIGS_DIR=/home/jon/src/wt/es-v043 EIGS=/home/jon/src/wt/es-v043/src/eigenscript bash aot/build.sh /home/jon/src/wt/ems-native-20260910/minisat.eigs /tmp/ems-native-20260910/ems-baseline' \
  --build-log /tmp/ems-native-20260910/build-baseline.log \
  --output /tmp/ems-native-wall-baseline
```

Use a new output directory for every run. A directory inside a source checkout
must be gitignored. `--cpu N` optionally pins the runner and all children to an
available CPU; the effective affinity is always recorded. The default process
cap is 120 seconds and total preflight/timing budget is 1,800 seconds. A timeout,
incorrect report, source/input/binary change, missing sample, or failed oracle
exits nonzero and prevents a completed performance report.

Default inputs are odd Tseitin torus **3x3 and 4x4**, and **pigeonhole 6/5**.
Larger tori are explicit additions and require both budgets, for example:

```bash
# Add these options to the command above, with a fresh --output directory:
--extra-rung 4x5 --timeout 600 --budget-seconds 7200
```

An added rung also requires its VM correctness preflight to finish. Native
MiniSat's speed is not an estimate of the time that VM preflight needs.

## Correctness and input ownership

The first step invokes **the existing `run_native_oracle.sh`**, with AOT required,
the supplied prebuilt binary, the selected tori, and a directory containing only
the pigeonhole fixture. That harness owns emission, CNF normalization, formula
preservation, torus identity checks, regime anchors, native verdict checks and
VM/AOT byte comparisons. The timing runner retains its artifact directory and
uses its already prepared `input.cnf` files directly. There is no second CNF
normalizer or formula checker in the timing runner.

Both anchors must match regime C: 3x3 has 592 conflicts / 1,681 resolutions;
4x4 has 9,986 / 33,873. EMS runs `--cdcl` with current defaults and no overrides.
Native MiniSat uses its own executable defaults. These policies differ.

The preflight is an unmeasured run of each solver on each input. Then the
runner executes sequential groups of solver arms, rotating the first arm by
repetition and case. Before accepting **every sample**, it checks:

- Input and executable SHA256 remain unchanged around the process.
- AOT exits 0, reports one verdict and conflicts count, and matches the complete
  preflight VM reference, excluding only trailing numeric ` ms=` on comment
  lines, as in the correctness harness.
- Native stdout, result file and exit status agree; conflicts remain equal to
  its own preflight reading. SAT exit 10 and UNSAT exit 20 are handled explicitly.
- Exactly five distinct, validated samples exist for each selected input/arm.

The stopwatch uses `perf_counter_ns` around process launch and blocking
`waitpid`. A signal deadline stops and kills every live process in the launched
session, including GNU timeout's separate process groups, and verifies that no
live member remains. Cleanup is bounded to five seconds plus at most one second
to reap the launcher; any remaining process is an explicit cleanup failure.
This covers the oracle's trusted process topology, not children deliberately
escaping their session with `setsid`. SIGINT, SIGTERM and SIGHUP cancellation
uses the same cleanup and retains the signal number, process record and failure
report before exiting nonzero. Signal handling is deferred until process launch
returns a child handle; repeated signals cannot interrupt cleanup. The accepted timing path does not
use `wait(timeout=...)`, whose polling can distort millisecond-scale readings.
Validation, binary hashing and formula emission are outside the stopwatch.
Startup and scheduler noise still matter for short native solves; retain the
range and compare runs on the same host.

This measures checked answers and deterministic CLI output. It does not replace
SAT model checks, DRAT verification, or the compiler's full differential gates.

## Optional candidate in the same run

A second prebuilt AOT executable can join the same schedule. This is useful
for a baseline/candidate A/B while retaining native MiniSat as a reference.
Supply all of the following additional options:

```bash
--candidate-binary /tmp/ems-native-20260910/ems-count-ceiling \
--candidate-label 'timing-only count-scan ceiling' \
--candidate-source /tmp/path/to/exact-candidate.c \
--candidate-build-command 'the exact C compiler command used for this binary' \
--candidate-build-log /tmp/path/to/candidate-build.log
```

The source argument is the exact modified generated C source, copied into the
result bundle and hashed. The candidate gets one unmeasured validated warmup per
input, then five samples interleaved with baseline AOT and native MiniSat. Its
stdout and counters must match the baseline preflight's VM reference on every
run. The JSON summary includes `baseline_over_candidate_wall_ratio_same_policy`.
An experiment labelled timing-only remains a timing experiment: matching these
inputs does not certify its semantics on other programs or instances.

## Artifacts and interpretation

- `manifest.json`: completion state, timing scope, arm order, policy, host,
  affinity, relevant runtime environment, binary paths/hashes, source revisions,
  dirty status and hashes of tracked/nonignored source files.
- `provenance/`: tracked diffs, supplied build logs, optional candidate C source.
  The build command is recorded verbatim and never executed. The caller supplies
  the relationship between a prebuilt binary and its source; source/binary hashes
  alone cannot establish that relationship. Native package metadata is recorded
  when available, alongside the executable hash.
- `oracle/` and `preflight-process/`: existing correctness-harness artifacts,
  VM references, prepared inputs and the preflight transcript.
- `cases.json`, `samples.jsonl`, `samples/`: input identities and every validated
  measurement, plus raw stdout, stderr, process exit/time and validation records.
- `summary.json` and `summary.tsv`: complete per-case medians, minima, maxima,
  conflict counts and descriptive conflicts per **external wall second**.
- `failure.json`: explanation for an incomplete run. Retained partial samples
  are diagnostic evidence, not an n=5 result.

A normal baseline run completes with `cases=3 arms=2 n=5 validated_samples=30`;
adding one candidate gives `cases=3 arms=3 n=5 validated_samples=45`. Warmups do
not count. AOT/native wall ratios describe these two solvers on the same inputs;
their different policies confound attribution to the language runtime. Conflicts
per second are also descriptive across policies: a conflict need not involve
equal work in both implementations. Baseline/candidate AOT ratios use the same
EMS policy and require identical preflight output on every measured run.

## Focused tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 benchmarks/test_compare_native.py
```

These lightweight tests launch synthetic child processes through the production
timing/validation path. They check five samples per arm, candidate interleaving,
external-time scope, known medians/ranges, and planted output, exit, result,
counter, input-mutation, timeout, descendant-cleanup and coverage faults. The
timeout regressions include GNU timeout's separate process group and the real,
unchanged oracle CLI with a synthetic sleeping emitter. Cancellation regressions
send SIGINT/SIGTERM/SIGHUP through that CLI and inject signals during process
creation and cleanup. They do not launch real
solvers or builds and do not replace the existing oracle selftests. CI runs this
focused suite before building EigenScript.
