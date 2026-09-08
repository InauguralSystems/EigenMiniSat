# Native oracle round 2 — 2026-09-08

Builder validation on branch `feat-native-oracle-diff`, starting from clean
`fb031b7`. The tracked solver, emitter, and existing CNFs were unchanged.
These are single-run instrument readings, not n=5 wall-time performance
claims. New blind-critic review is left to the orchestrator.

## F1: actual emitter regression, before and after

In a scratch copy, change the emitter assignment
`dump_cols is floor of (num of dump_argv[1])` to `dump_cols is 3`.
Run `benchmarks/run_native_oracle.sh --aot off --rungs '3x3 4x4'
--instances /tmp/ems-oracle-round2/empty` (one command; directory empty).
The baseline harness was copied byte-for-byte from `fb031b7`.

Before, observed exit 0:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults
AOT: SKIPPED (disabled explicitly)
Selection: files=0 rungs=2 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
RUN tseitin-3x3-odd
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=SKIPPED
RUN tseitin-4x4-odd
PASS tseitin-4x4-odd                                       UNSATISFIABLE native=VM AOT=SKIPPED
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
3x3                 592            731       0.004064             1.235x
4x4                4127           1565       0.005985             0.379x
SUMMARY PASS selected=2 passed=2 native=2 VM=2 AOT=0
```

After, same scratch emitter regression with the corrected harness, observed
exit 1 before solving the mislabeled 4x4:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: SKIPPED (disabled explicitly)
Selection: files=0 requested-rungs=2 preflight-added=0 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
RUN tseitin-3x3-odd
PREFLIGHT 3x3: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=SKIPPED
FAIL 4x4 [rung-identity]: expected p cnf 32 128; got p cnf 24 96
```

The fix checks the entire ordered torus encoding per rung, separately compares
3x3 with the existing repository CNF, and preflights both 3x3 and 4x4 against
full regime-C stdout banks. The banks were captured from a fresh correct run
and checked against the existing fixture and documented regime-C counters;
[`oracle/README.md`](oracle/README.md) records their provenance.

## Clean run

Command: `KEEP_WORK=1 benchmarks/run_native_oracle.sh`. The default path built
AOT afresh under the pinned v0.43.0 runtime. GNU time captured the exit code.

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: BUILD (once, runtime=v0.43.0, cap=600s)
AOT: ENABLED (EMS-VM is the byte-exact reference; only trailing ms stripped)
Selection: files=18 requested-rungs=2 preflight-added=0 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
RUN tseitin-3x3-odd
PREFLIGHT 3x3: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=PASS
IDENTITY 4x4: PASS (header, every ordered literal and clause, odd charge)
RUN tseitin-4x4-odd
PREFLIGHT 4x4: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-4x4-odd                                       UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/k4_3color_unsat.cnf
PASS tests/corpus/k4_3color_unsat.cnf                      UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/long_clause_sat.cnf
PASS tests/corpus/long_clause_sat.cnf                      SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/multi_clause_line_unsat.cnf
PASS tests/corpus/multi_clause_line_unsat.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/multiline_sat.cnf
PASS tests/corpus/multiline_sat.cnf                        SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/pigeonhole_4_3.cnf
PASS tests/corpus/pigeonhole_4_3.cnf                       UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/triangle_3color_sat.cnf
PASS tests/corpus/triangle_3color_sat.cnf                  SATISFIABLE   native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_k5_4color.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_k5_4color.cnf
PASS tests/corpus/vendor/satlib_style_k5_4color.cnf        UNSATISFIABLE native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf
PASS tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf   UNSATISFIABLE native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_xor_triangle_8.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_xor_triangle_8.cnf
PASS tests/corpus/vendor/satlib_style_xor_triangle_8.cnf   SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/xor_contradiction_unsat.cnf
PASS tests/corpus/xor_contradiction_unsat.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/xor_ladder_sat.cnf
PASS tests/corpus/xor_ladder_sat.cnf                       SATISFIABLE   native=VM AOT=PASS
RUN tests/fixtures/pigeonhole_3_2.cnf
PASS tests/fixtures/pigeonhole_3_2.cnf                     UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/pigeonhole_6_5.cnf
PASS tests/fixtures/pigeonhole_6_5.cnf                     UNSATISFIABLE native=VM AOT=PASS
INPUT tests/fixtures/satlib_trailer_sat.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/fixtures/satlib_trailer_sat.cnf
PASS tests/fixtures/satlib_trailer_sat.cnf                 SATISFIABLE   native=VM AOT=PASS
INPUT tests/fixtures/satlib_trailer_unsat.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/fixtures/satlib_trailer_unsat.cnf
PASS tests/fixtures/satlib_trailer_unsat.cnf               UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/simple_sat.cnf
PASS tests/fixtures/simple_sat.cnf                         SATISFIABLE   native=VM AOT=PASS
RUN tests/fixtures/tseitin_torus_3x3_odd.cnf
PASS tests/fixtures/tseitin_torus_3x3_odd.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/unit_unsat.cnf
PASS tests/fixtures/unit_unsat.cnf                         UNSATISFIABLE native=VM AOT=PASS
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
3x3                 592            731        0.00176             1.235x
4x4                9986          84150       0.223485             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.748efz
```

```text
CLEAN wall_seconds=322.49 exit=0
```

## Final source verification

After moving all regime-normalization scratch output under `/tmp`, repeat the
entire clean selection on the final harness, explicitly reusing the AOT binary
built above (the solver and compiler sources are unchanged):
`KEEP_WORK=1 AOT_BINARY=/tmp/ems-native-oracle.748efz/minisat-aot
benchmarks/run_native_oracle.sh` (one command). Observed exit 0. Selftest,
mutation tests, and the actual emitter-regression repro below also ran on this
final source. The oracle directory contained exactly its README and two banks
before and after selftest; no generated sidecars were left in the repository.

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems-native-oracle.748efz/minisat-aot; VM remains byte-exact reference)
Selection: files=18 requested-rungs=2 preflight-added=0 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
RUN tseitin-3x3-odd
PREFLIGHT 3x3: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=PASS
IDENTITY 4x4: PASS (header, every ordered literal and clause, odd charge)
RUN tseitin-4x4-odd
PREFLIGHT 4x4: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-4x4-odd                                       UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/k4_3color_unsat.cnf
PASS tests/corpus/k4_3color_unsat.cnf                      UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/long_clause_sat.cnf
PASS tests/corpus/long_clause_sat.cnf                      SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/multi_clause_line_unsat.cnf
PASS tests/corpus/multi_clause_line_unsat.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/multiline_sat.cnf
PASS tests/corpus/multiline_sat.cnf                        SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/pigeonhole_4_3.cnf
PASS tests/corpus/pigeonhole_4_3.cnf                       UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/triangle_3color_sat.cnf
PASS tests/corpus/triangle_3color_sat.cnf                  SATISFIABLE   native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_k5_4color.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_k5_4color.cnf
PASS tests/corpus/vendor/satlib_style_k5_4color.cnf        UNSATISFIABLE native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf
PASS tests/corpus/vendor/satlib_style_pigeonhole_5_4.cnf   UNSATISFIABLE native=VM AOT=PASS
INPUT tests/corpus/vendor/satlib_style_xor_triangle_8.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/corpus/vendor/satlib_style_xor_triangle_8.cnf
PASS tests/corpus/vendor/satlib_style_xor_triangle_8.cnf   SATISFIABLE   native=VM AOT=PASS
RUN tests/corpus/xor_contradiction_unsat.cnf
PASS tests/corpus/xor_contradiction_unsat.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/corpus/xor_ladder_sat.cnf
PASS tests/corpus/xor_ladder_sat.cnf                       SATISFIABLE   native=VM AOT=PASS
RUN tests/fixtures/pigeonhole_3_2.cnf
PASS tests/fixtures/pigeonhole_3_2.cnf                     UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/pigeonhole_6_5.cnf
PASS tests/fixtures/pigeonhole_6_5.cnf                     UNSATISFIABLE native=VM AOT=PASS
INPUT tests/fixtures/satlib_trailer_sat.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/fixtures/satlib_trailer_sat.cnf
PASS tests/fixtures/satlib_trailer_sat.cnf                 SATISFIABLE   native=VM AOT=PASS
INPUT tests/fixtures/satlib_trailer_unsat.cnf: normalized SATLIB trailer / final newline for every arm
RUN tests/fixtures/satlib_trailer_unsat.cnf
PASS tests/fixtures/satlib_trailer_unsat.cnf               UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/simple_sat.cnf
PASS tests/fixtures/simple_sat.cnf                         SATISFIABLE   native=VM AOT=PASS
RUN tests/fixtures/tseitin_torus_3x3_odd.cnf
PASS tests/fixtures/tseitin_torus_3x3_odd.cnf              UNSATISFIABLE native=VM AOT=PASS
RUN tests/fixtures/unit_unsat.cnf
PASS tests/fixtures/unit_unsat.cnf                         UNSATISFIABLE native=VM AOT=PASS
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
3x3                 592            731       0.003798             1.235x
4x4                9986          84150       0.223714             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.XdqyJa
```

```text
FINAL-CLEAN wall_seconds=49.19 exit=0
```

## Seven main plants and supporting controls

Command: `KEEP_WORK=1 AOT_BINARY=/tmp/ems-native-oracle.748efz/minisat-aot
benchmarks/run_native_oracle.sh --selftest` (one command), reusing the binary
from the clean run. Observed exit 1, the intentional RED demonstration:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems-native-oracle.748efz/minisat-aot; VM remains byte-exact reference)
RUN control-unsat
PASS control-unsat                                         UNSATISFIABLE native=VM AOT=PASS
RUN control-sat
PASS control-sat                                           SATISFIABLE   native=VM AOT=PASS
CONTROL identity-3x3: PASS (expected rc=0)
CONTROL identity-4x4: PASS (expected rc=0)
CONTROL identity-clauses: PASS (expected rc=1)
CONTROL fixture-reference: PASS (expected rc=1)
CONTROL regime-3x3: PASS (expected rc=0)
CONTROL regime-3x3-drift: PASS (expected rc=1)
CONTROL regime-4x4: PASS (expected rc=0)
CONTROL regime-4x4-drift: PASS (expected rc=1)
CONTROL coverage-complete: PASS (expected rc=0)
CONTROL coverage-passed: PASS (expected rc=1)
CONTROL coverage-native_runs: PASS (expected rc=1)
CONTROL coverage-vm_runs: PASS (expected rc=1)
CONTROL coverage-aot_runs: PASS (expected rc=1)
CONTROL auto-degrades: PASS (expected rc=0)
CONTROL required-build-fails: PASS (expected rc=1)
CONTROLS checked=15 expected=15 missed=0
SELFTEST corrupted-cnf: RED (rc=1, verdict)
SELFTEST wrong-ems-verdict: RED (rc=1, verdict)
SELFTEST perturbed-aot: RED (rc=1, aot-diff)
SELFTEST zero-instances: RED (rc=1, vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST resized-emitter: RED (rc=1, rung-identity)
SELFTEST ALL RED caught=7 expected=7 (intentional exit 1)
Artifacts: /tmp/ems-native-oracle.wVMtXR
```

## Gut each new check

An unmodified temporary harness copy first served as the control. Then each
named function body was replaced by `:` in a separate temporary copy beside
the harness, preserving root resolution. The reset mutation deleted only
the AOT arm reset; the injection mutation deleted only the resized-emitter
argument rewrite. Every mutation exited 2 with its own missing detection.
The copies were removed after execution.

```text
MUTATION control: witnessed exit=1
SELFTEST ALL RED caught=7 expected=7 (intentional exit 1)
MUTATION identity: witnessed exit=2
CONTROL identity-3x3: MISS (rc=0, expected rc=0 and named evidence)
CONTROL identity-4x4: MISS (rc=0, expected rc=0 and named evidence)
CONTROL identity-clauses: MISS (rc=0, expected rc=1 and named evidence)
SELFTEST resized-emitter: MISS (rc=0, expected rung-identity)
SELFTEST BROKEN caught=6 expected=7 missed=1 control_missed=3 (exit 2)
MUTATION fixture: witnessed exit=2
CONTROL identity-3x3: MISS (rc=0, expected rc=0 and named evidence)
CONTROL fixture-reference: MISS (rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN caught=7 expected=7 missed=0 control_missed=2 (exit 2)
MUTATION regime: witnessed exit=2
CONTROL regime-3x3: MISS (rc=0, expected rc=0 and named evidence)
CONTROL regime-3x3-drift: MISS (rc=0, expected rc=1 and named evidence)
CONTROL regime-4x4: MISS (rc=0, expected rc=0 and named evidence)
CONTROL regime-4x4-drift: MISS (rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN caught=7 expected=7 missed=0 control_missed=4 (exit 2)
MUTATION coverage: witnessed exit=2
CONTROL coverage-passed: MISS (rc=0, expected rc=1 and named evidence)
CONTROL coverage-native_runs: MISS (rc=0, expected rc=1 and named evidence)
CONTROL coverage-vm_runs: MISS (rc=0, expected rc=1 and named evidence)
CONTROL coverage-aot_runs: MISS (rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN caught=7 expected=7 missed=0 control_missed=4 (exit 2)
MUTATION auto-policy: witnessed exit=2
CONTROL auto-degrades: MISS (rc=0, expected rc=0 and named evidence)
CONTROL required-build-fails: MISS (rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN caught=7 expected=7 missed=0 control_missed=2 (exit 2)
MUTATION aot-reset: witnessed exit=2
CONTROL auto-degrades: MISS (rc=1, expected rc=0 and named evidence)
SELFTEST BROKEN caught=7 expected=7 missed=0 control_missed=1 (exit 2)
MUTATION emitter-injection: witnessed exit=2
SELFTEST resized-emitter: MISS (rc=0, expected rung-identity)
SELFTEST BROKEN caught=6 expected=7 missed=1 control_missed=0 (exit 2)
MUTATION DONE control=1 mutations=7
```

## F2: present but unbuildable toolchain

The fake source toolchain has `eigs.json`, `src/`, and `aot/build.sh` containing
`exit 7`; the real pinned runtime still supplies the VM. Commands use
`AOT_BUILD=/tmp/ems-oracle-round2/failed-toolchain/aot/build.sh` and
`--rungs '' --instances /tmp/ems-oracle-round2/one` (one real unit CNF).

Baseline `--aot auto`:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults
AOT: BUILD (once, runtime=v0.43.0, cap=600s)
FAIL AOT [build]: rc=7 (timeout rc=124 or 137 is FAILURE); see /tmp/ems-native-oracle.XHc9as/build.out
BUILD-REPRO exit=1
```

Corrected `--aot auto`:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: BUILD (once, runtime=v0.43.0, cap=600s)
AOT: SKIPPED (build failed rc=7; logs=/tmp/ems-native-oracle.vyJk3T/build.*; native/VM checks continue)
Selection: files=1 requested-rungs=0 preflight-added=0 per-solver-cap=120s
3x3: SKIPPED (budget; not selected in RUNGS)
4x4: SKIPPED (budget; not selected in RUNGS)
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
RUN /tmp/ems-oracle-round2/one/unit.cnf
PASS /tmp/ems-oracle-round2/one/unit.cnf                   UNSATISFIABLE native=VM AOT=SKIPPED
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
No ladder rungs selected; file-instance checks only.
SUMMARY PASS selected=1 passed=1 native=1 VM=1 AOT=0
BUILD-REPRO exit=0
```

Corrected `--aot on`:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: BUILD (once, runtime=v0.43.0, cap=600s)
FAIL AOT [build]: rc=7; required AOT build failed; logs=/tmp/ems-native-oracle.jwhUUh/build.*
BUILD-REPRO exit=1
```

The standing selftest repeats both modes through the actual `prepare_aot`
path. It requires the named skip AND a completed native/VM row with AOT=0;
it seeds a stale enabled arm to detect failure to clear that state.

## F3 and additional boundary checks

The coverage assertions now live in `check_coverage`, called by the real
`finish_run`. Four controls independently remove one completion record
(passed, native, VM, AOT) from an otherwise complete accounting state. All
must fail through `[coverage]`; a complete state must pass. These are direct
accounting fault injections, not an exemption based on current control flow.
Removing only the original F3 assertion was also tested separately: its three
controls MISS, while the separate AOT coverage control continues to pass.

Additional checks exercised rectangular/larger CNF identities without solving
those larger instances, a transposition with identical header counts, empty
selection, missing toolchains, and both auto/on behavior for timed-out builds
and builds that produce no executable:

```text
IDENTITY PROBE 3x4: PASS (emitter and validator only; no solve)
IDENTITY PROBE 4x3: PASS (emitter and validator only; no solve)
IDENTITY PROBE 4x5: PASS (emitter and validator only; no solve)
IDENTITY PROBE 4x6: PASS (emitter and validator only; no solve)
IDENTITY PROBE 5x5: PASS (emitter and validator only; no solve)
IDENTITY PROBE 5x6: PASS (emitter and validator only; no solve)
IDENTITY PROBE 6x6: PASS (emitter and validator only; no solve)
IDENTITY PROBE 3x4 mislabeled 4x3: RED exit=1; token 2: expected 3; got 4
EXTRA empty-selection: witnessed exit=1
EXTRA absent-build: witnessed exit=0
EXTRA absent-runtime-selftest: witnessed exit=1
EXTRA build-timeout-auto: witnessed exit=0
EXTRA build-timeout-on: witnessed exit=1
EXTRA build-no-executable-auto: witnessed exit=0
EXTRA build-no-executable-on: witnessed exit=1
MUTATION only-F3-core-assertion: exit=2; passed/native/VM MISS, AOT control still PASS
EXTRA DONE identity-positive=7 identity-negative=1 configuration=7 isolated-coverage-mutation=1
```

## Mandatory preflight even when not selected for measurement

Command: `KEEP_WORK=1 AOT_BINARY=/tmp/ems-native-oracle.rzfIWU/minisat-aot
benchmarks/run_native_oracle.sh --rungs 3x3
--instances /tmp/ems-oracle-round2/empty` (one command). Observed exit 0.
4x4 runs as a preflight and contributes to completion counts, while only 3x3
enters the requested search table:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems-native-oracle.rzfIWU/minisat-aot; VM remains byte-exact reference)
Selection: files=0 requested-rungs=1 preflight-added=1 per-solver-cap=120s
4x4: PREFLIGHT (required regime anchor; not selected for measurement)
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
RUN tseitin-3x3-odd
PREFLIGHT 3x3: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=PASS
IDENTITY 4x4: PASS (header, every ordered literal and clause, odd charge)
RUN tseitin-4x4-odd
PREFLIGHT 4x4: PASS (regime C, byte-exact EMS-VM output excluding ms)
PASS tseitin-4x4-odd                                       UNSATISFIABLE native=VM AOT=PASS
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
3x3                 592            731         0.0031             1.235x
SUMMARY PASS selected=2 passed=2 native=2 VM=2 AOT=2
Artifacts: /tmp/ems-native-oracle.c4lJlo
```

## Verification discipline

One initial cold run was invalidated by editing help text while Bash was
still reading the running script; it built AOT but then exited on a shell
syntax error. That invocation is excluded. The clean run recorded above was
repeated with the harness left unchanged throughout, and exited 0. When
developing this harness, freeze its file for the entire invocation, including
the AOT build wait. A build-failure control also exposed an EXIT-trap scope
mistake during development; its correction is documented at the control's
`work` assignment and covered by the surviving output checks.

No EMS answer bug, AOT output mismatch, or behavior contradicting the round-2
brief was observed. Larger solver rungs remain opt-in as agreed. Commit is
delegated to the orchestrator because Git metadata is read-only here.
