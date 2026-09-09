# Native oracle validation — 2026-09-08

Builder-run transcript on the dev box. These are single-run instrument
readings, not an n=5 wall-time performance claim. The solver and emitter were
unchanged. The independent blind critics have not run as part of this report.

- EigenMiniSat base: `6dbfa7dcca83394fbefe4dd8cc27ff64dd371302`.
- EMS policy: CDCL current defaults, regime C.
- EigenScript v0.43.0: `a6c50fba6a6250ea347a34500d6c9fa503a5c931`.
- Ouroboros: `9ae3f59721e1399d88b8625c092800e9f2db0b54`.
- Native answer oracle: `/usr/bin/minisat`.

## Clean run (fresh AOT build)

Command: `KEEP_WORK=1 benchmarks/run_native_oracle.sh`. GNU time captured
the wall duration and exit code. Raw output follows.

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults
AOT: BUILD (once, runtime=v0.43.0, cap=600s)
AOT: ENABLED (EMS-VM is the byte-exact reference; only trailing ms stripped)
Selection: files=18 rungs=2 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
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
RUN tseitin-3x3-odd
PASS tseitin-3x3-odd                                       UNSATISFIABLE native=VM AOT=PASS
RUN tseitin-4x4-odd
PASS tseitin-4x4-odd                                       UNSATISFIABLE native=VM AOT=PASS
SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)
rung      EMS_conflicts native_conflicts   native_CPU_s         native/EMS
3x3                 592            731       0.004883             1.235x
4x4                9986          84150        0.22611             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.rzfIWU
CLEAN wall_seconds=327.57 exit=0
```

## Planted faults

Command: `KEEP_WORK=1 AOT_BINARY=/tmp/ems-native-oracle.rzfIWU/minisat-aot
benchmarks/run_native_oracle.sh --selftest` (one shell command). This reused
the binary built by the clean run above. Observed shell exit: **1**.

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults
AOT: ENABLED (explicit prebuilt binary=/tmp/ems-native-oracle.rzfIWU/minisat-aot; VM remains byte-exact reference)
RUN control-unsat
PASS control-unsat                                         UNSATISFIABLE native=VM AOT=PASS
RUN control-sat
PASS control-sat                                           SATISFIABLE   native=VM AOT=PASS
SELFTEST corrupted-cnf: RED (rc=1, verdict)
SELFTEST wrong-ems-verdict: RED (rc=1, verdict)
SELFTEST perturbed-aot: RED (rc=1, aot-diff)
SELFTEST zero-instances: RED (rc=1, vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST ALL RED caught=6 expected=6 (intentional exit 1)
Artifacts: /tmp/ems-native-oracle.scnMZ5
```

## Remove each comparator

Temporary copies beside the real harness preserve its root resolution. First
run an unmodified control; then replace the body of `check_verdict`,
`check_aot`, or `check_population` with `:` one at a time and run `--selftest`
with an explicitly reused AOT binary. Each lost detection must print MISS,
not RED, and the outer selftest must exit 2. Temporary copies were removed.

```text
MUTATION control: witnessed rc=1
SELFTEST corrupted-cnf: RED (rc=1, verdict)
SELFTEST wrong-ems-verdict: RED (rc=1, verdict)
SELFTEST perturbed-aot: RED (rc=1, aot-diff)
SELFTEST zero-instances: RED (rc=1, vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST ALL RED caught=6 expected=6 (intentional exit 1)
MUTATION verdict: witnessed rc=2
SELFTEST corrupted-cnf: MISS (rc=1, expected verdict)
SELFTEST wrong-ems-verdict: MISS (rc=1, expected verdict)
SELFTEST perturbed-aot: RED (rc=1, aot-diff)
SELFTEST zero-instances: RED (rc=1, vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST BROKEN caught=4 expected=6 missed=2 (exit 2)
MUTATION aot-diff: witnessed rc=2
SELFTEST corrupted-cnf: RED (rc=1, verdict)
SELFTEST wrong-ems-verdict: RED (rc=1, verdict)
SELFTEST perturbed-aot: MISS (rc=0, expected aot-diff)
SELFTEST zero-instances: RED (rc=1, vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST BROKEN caught=5 expected=6 missed=1 (exit 2)
MUTATION vacuity: witnessed rc=2
SELFTEST corrupted-cnf: RED (rc=1, verdict)
SELFTEST wrong-ems-verdict: RED (rc=1, verdict)
SELFTEST perturbed-aot: RED (rc=1, aot-diff)
SELFTEST zero-instances: MISS (rc=0, expected vacuity)
SELFTEST solver-timeout: RED (rc=1, vm)
SELFTEST empty-output: RED (rc=1, vm-output)
SELFTEST BROKEN caught=5 expected=6 missed=1 (exit 2)
MUTATION DONE control=1 disabled-comparators=3
```

## Configuration and error paths

Separate tiny invocations exercised the named paths: an empty directory and
no rungs; missing build/runtime in auto mode; missing build in required mode;
an empty CNF; native `/usr/bin/false`; an emitter wrapper exiting 7; and a VM
binary that differs from the AOT runtime. No full rung was repeated here.

```text
CONFIG vacuity: witnessed rc=1
CONFIG absent-build-auto: witnessed rc=0
CONFIG absent-runtime-auto: witnessed rc=0
CONFIG absent-build-on: witnessed rc=1
CONFIG empty-cnf: witnessed rc=1
CONFIG native-error: witnessed rc=1
CONFIG emitter-error: witnessed rc=1
CONFIG runtime-mismatch: witnessed rc=1
CONFIG DONE checked=8
```

## Measured constraints that differ from the builder brief

Native MiniSat rejects the existing SATLIB trailer. Command:
`/usr/bin/minisat tests/fixtures/satlib_trailer_sat.cnf /tmp/ems-oracle-probe/trailer.result`.
Observed exit 3; stderr:

```text
PARSE ERROR! Unexpected char: %
```

The harness therefore announces trailer removal and passes the same resulting
formula to all arms. This does not exercise the original trailer parser.

The VM did not finish 5x5 within the intended total fast-run budget. Command:
`KEEP_WORK=1 benchmarks/run_native_oracle.sh --aot off --rungs 5x5
--instances /tmp/ems-oracle-probe/empty --timeout 120` (one shell command;
the directory was empty). Observed shell exit 1:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults
AOT: SKIPPED (disabled explicitly)
Selection: files=0 rungs=1 per-solver-cap=120s
3x3: SKIPPED (budget; not selected in RUNGS)
4x4: SKIPPED (budget; not selected in RUNGS)
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
RUN tseitin-5x5-odd
FAIL tseitin-5x5-odd [vm]: rc=124 (timeout rc=124 or 137 is FAILURE); see /tmp/ems-native-oracle.wyIWJ5/case.XyZoUv/vm.out
Artifacts: /tmp/ems-native-oracle.wyIWJ5
```

The native solver did finish that same emitted instance; its report:

```text
conflicts             : 2236075        (287059 /sec)
CPU time              : 7.7896 s
UNSATISFIABLE
```

The clean-run timing above also includes a cold AOT build and exceeds a
couple of minutes. The default therefore selects 3x3 and 4x4; 4x5, 4x6, 5x5,
5x6, and 6x6 are explicitly budget-skipped. The harness can select each of
them, but this session does not bank completed EMS comparisons for them.
No EMS answer bug or AOT output mismatch was observed.
