# Native oracle round 3 — 2026-09-08

The worktree started clean on `feat-native-oracle-diff` at `69aff93`.
The solver, emitter, existing 3x3 input fixture, and both regime stdout
banks remain unchanged. All solver work ran sequentially. AOT reused
`/tmp/ems_aot` as requested; this round did not rebuild the actual AOT.
Single-run CPU and wall readings below are observations, not n=5 performance
claims. The orchestrator owns the next blind review and commit.

## Reproduce before fixing

The baseline harness was copied from `69aff93`, and only its production
`check_regime` call was deleted. Its full `--selftest` still claimed all
seven negative cases caught. Separately, emit 3x3 and 4x4 using
`/home/jon/src/wt/es-v043/src/eigenscript benchmarks/dump_tseitin_cnf.eigs R C`.
Swap zero-based vertex clause-blocks 1 and 2 of 3x3 (the eight-clause blocks
after the charged vertex), preserving the header and all clauses. Solve with
`eigenscript minisat.eigs --cdcl CNF`, remove only trailing numeric ` ms=`,
and compare with the committed regime stdout bank. Native MiniSat also
solved both the reordered 3x3 and captured 4x4:

```text
emitted-3x3 exit=0
emitted-4x4 exit=0
reordered-vm exit=0
reordered normalized-vs-bank=IDENTICAL
reordered-native exit=20
anchor4x4-vm exit=0
anchor4x4 normalized-vs-bank=IDENTICAL
anchor4x4-native exit=20
regime-disconnected-before exit=1
CONTROLS checked=15 expected=15 missed=0
SELFTEST ALL RED caught=7 expected=7 (intentional exit 1)
```

The replacement claim is scoped to those readings: the ordering pin requires
exact ordered input tokens. This particular reordering leaves normalized
VM output identical, so a regime-bank match does not detect it. The real
harness now has a standing production-path ordering plant:

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh
--plant vertex-order` (one command):

```text
PLANT vertex-order: discovery (explicit fault injection)
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
PLANT vertex-order: run (explicit fault injection)
Selection: files=18 requested-rungs=2 preflight-added=0 per-solver-cap=120s
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
FAIL 3x3 [rung-identity]: token 41: expected -2; got -3
Artifacts: /tmp/ems-native-oracle.DVzbUt
```

## Captured 4x4 input anchor

`oracle/tseitin_torus_4x4_odd.cnf` captures the unchanged emitter's output
above, with only its extra trailing blank line removed. It was not generated
by `torus_identity.awk`. Its normalized VM output matched the already
committed 4x4 regime bank before it was added. Normal production emission
compares ordered tokens directly with this capture as well as checking the
model; the existing 3x3 fixture remains the other captured input anchor.
Round-4 scope correction: this emitter capture cannot establish the emitter's
initial correctness. Its extra coverage is bank corruption and model drift or
weakening; see the round-4 single-token sweep. The planted reference corruption leaves the emitted input and model alone:

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh
--plant fixture-4x4` (one command):

```text
PLANT fixture-4x4: discovery (explicit fault injection)
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
PLANT fixture-4x4: run (explicit fault injection)
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
FAIL 4x4 [rung-fixture]: emitted CNF differs from /tmp/ems-native-oracle.HugbVk/corrupt-reference.cnf
Artifacts: /tmp/ems-native-oracle.HugbVk
```

## Clean run

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh`:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
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
IDENTITY 4x4: PASS (banked repository fixture, ordered DIMACS tokens)
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
3x3                 592            731       0.002613             1.235x
4x4                9986          84150       0.226566             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.VH50Z0
```

```text
clean exit=0 wall_seconds=49.34
```

## Full selftest through the production CLI

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh --selftest`:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
CONTROL clean: PASS (production CLI rc=0)
SELFTEST corrupted-cnf: RED (production CLI rc=1)
SELFTEST wrong-ems-verdict: RED (production CLI rc=1)
SELFTEST perturbed-aot: RED (production CLI rc=1)
SELFTEST zero-instances: RED (production CLI rc=1)
SELFTEST solver-timeout: RED (production CLI rc=1)
SELFTEST empty-output: RED (production CLI rc=1)
SELFTEST resized-emitter: RED (production CLI rc=1)
SELFTEST identity-clauses: RED (production CLI rc=1)
SELFTEST vertex-order: RED (production CLI rc=1)
SELFTEST fixture-3x3: RED (production CLI rc=1)
SELFTEST fixture-4x4: RED (production CLI rc=1)
SELFTEST regime-3x3: RED (production CLI rc=1)
SELFTEST regime-4x4: RED (production CLI rc=1)
SELFTEST vacuity-discovery: RED (production CLI rc=1)
SELFTEST vacuity-completion: RED (production CLI rc=1)
SELFTEST coverage-passed: RED (production CLI rc=1)
SELFTEST coverage-native: RED (production CLI rc=1)
SELFTEST coverage-vm: RED (production CLI rc=1)
SELFTEST coverage-aot: RED (production CLI rc=1)
SELFTEST unreadable-input: RED (production CLI rc=1)
SELFTEST unopenable-input: RED (production CLI rc=1)
CONTROL auto-degrades: PASS (production CLI rc=0)
SELFTEST required-build-fails: RED (production CLI rc=1)
SELFTEST ALL RED checked=24 expected=24 caught=22 controls=2 (intentional exit 1)
Artifacts: /tmp/ems-native-oracle.f1Nwui
```

```text
selftest exit=1 wall_seconds=408.87
```

The selftest support file calls no production comparator helpers. Each case
starts the current harness file in a fresh Bash process, with the ordinary
CLI selection, discovery, preflight, emission, solving, and finalization.
Fault setup changes inputs, command output, or accounting state; the normal
path must find the fault. No solver output is replayed. Check the child logs
under the reported parent artifact directory for raw named failures.

Comparator plants select nonempty 3x3/4x4 rungs and real SAT/UNSAT files. The
empty-selection case additionally exercises truly empty CLI discovery. A
population check necessarily stops before solving when its population is
zero; the nonempty discovery plant corrupts only the discovered count.
Distinct discovery/completion failure names stop the second guard from
masking deletion of the first. Coverage plants offset each completion count
before real solves and reach the final production assertion. There is no
helper-only or unreachable-by-construction exemption for these comparators.
The build-policy auto control is file-only because it tests build fallback,
not rung checking.

## Delete each production call site

For each row below, copy the current harness beside itself (preserving root
resolution), delete exactly the named production call, and invoke that copy
with `AOT_BINARY=/tmp/ems_aot bash COPY --selftest-case CASE`. The child uses
that same mutant pathname, never the unmodified harness. Each invocation
explicitly labels itself a partial selftest; it runs the same case used by
the full suite, with the full nonempty rung/file population. Both the named
MISS and exit 2 were required. Copies were removed afterward.

```text
DELETE rung-identity: exit=2
SELFTEST identity-clauses: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE banked-fixture: exit=2
SELFTEST fixture-4x4: MISS (production CLI rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE regime-preflight: exit=2
SELFTEST regime-3x3: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE native-verdict: exit=2
SELFTEST wrong-ems-verdict: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE aot-diff: exit=2
SELFTEST perturbed-aot: MISS (production CLI rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE vacuity-discovery: exit=2
SELFTEST vacuity-discovery: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE vacuity-completion: exit=2
SELFTEST vacuity-completion: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE coverage: exit=2
SELFTEST coverage-passed: MISS (production CLI rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE emission-entry: exit=2
SELFTEST resized-emitter: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE rung-solve-entry: exit=2
SELFTEST regime-3x3: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE file-solve-entry: exit=2
SELFTEST unreadable-input: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE finish-entry: exit=2
SELFTEST coverage-passed: MISS (production CLI rc=0, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
DELETE input-preparation: exit=2
SELFTEST unreadable-input: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
CALL-SITE MUTATIONS checked=13 missed=0
```

The exact mutation driver used for this sweep was:

```python
from pathlib import Path
import subprocess, os, time
root=Path('/home/jon/src/wt/ems-oracle'); out=Path('/tmp/ems-oracle-round3')
src=(root/'benchmarks/run_native_oracle.sh').read_text()
cases=[
 ('rung-identity','    check_rung_identity "$rung" "$work/$rung.cnf"\n','identity-clauses'),
 ('banked-fixture','    check_rung_fixture "$rung" "$cnf"\n','fixture-4x4'),
 ('regime-preflight','    [[ -z "$rung" ]] || check_regime "$rung" "$dir/vm.out"\n','regime-3x3'),
 ('native-verdict','    check_verdict "$name"\n','wrong-ems-verdict'),
 ('aot-diff','        check_aot "$name" "$dir/vm.out" "$dir/aot.out"\n','perturbed-aot'),
 ('vacuity-discovery','((selftest)) || check_population discovery\n','vacuity-discovery'),
 ('vacuity-completion','    check_population completion\n','vacuity-completion'),
 ('coverage','    check_coverage\n','coverage-passed'),
 ('emission-entry','    emit_rung "$rung"\n','resized-emitter'),
 ('rung-solve-entry','    run_instance "tseitin-$rung-odd" "$work/$rung.cnf" "$rung" "$measure"\n','regime-3x3'),
 ('file-solve-entry','for file in "${files[@]}"; do run_instance "$file" "$file"; done\n','unreadable-input'),
 ('finish-entry','\nfinish_run\n','coverage-passed'),
 ('input-preparation','    prepare_cnf "$name" "$input" "$dir/input.cnf"\n','unreadable-input'),
]
env=dict(os.environ,AOT_BINARY='/tmp/ems_aot',KEEP_WORK='0')
for name,needle,case in cases:
    assert src.count(needle)==1,(name,src.count(needle))
    path=root/('benchmarks/.round3-mutant-'+name+'.sh')
    path.write_text(src.replace(needle,'\n',1))
    try:
        with (out/('mutation-'+name+'.log')).open('w') as log:
            p=subprocess.run(['bash',str(path),'--selftest-case',case],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        data=(out/('mutation-'+name+'.log')).read_text()
        print(f'DELETE {name}: exit={p.returncode}',flush=True)
        print('\n'.join(s for s in data.splitlines() if ': MISS ' in s or 'SELFTEST BROKEN' in s),flush=True)
        assert p.returncode==2 and f'SELFTEST {case}: MISS' in data,name
    finally: path.unlink()
print(f'CALL-SITE MUTATIONS checked={len(cases)} missed=0',flush=True)
```

## Input failures and remaining boundaries

For the raw unreadable-file check, copy `tests/fixtures/unit_unsat.cnf` to
`/tmp/ems-oracle-round3/unreadable/input.cnf`, chmod it to 000, then run:
`AOT_BINARY=/tmp/ems_aot benchmarks/run_native_oracle.sh --aot off --rungs ''
--instances /tmp/ems-oracle-round3/unreadable` (one command). Permissions are
restored after the test. This fails under its input-open name; actual tail
junk has a different name. The rest of this boundary sweep also checks the
actual corrupted-rung disagreement, explicit empty selection, unknown or
unavailable-only selftest selections, and auto/on build failure policy:

```text
ordering-rejected exit=1
FAIL 3x3 [rung-identity]: token 41: expected -2; got -3
anchor4x4-plant exit=1
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
PREFLIGHT 3x3: PASS (regime C, byte-exact EMS-VM output excluding ms)
IDENTITY 4x4: PASS (header, every ordered literal and clause, odd charge)
FAIL 4x4 [rung-fixture]: emitted CNF differs from /tmp/ems-native-oracle.HugbVk/corrupt-reference.cnf
corrupted-rung exit=1
IDENTITY 3x3: PASS (header, every ordered literal and clause, odd charge)
IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)
FAIL tseitin-3x3-odd [verdict]: DISAGREE native-MiniSat=UNSATISFIABLE EMS-VM=SATISFIABLE
unreadable exit=1
AOT: SKIPPED (disabled explicitly)
FAIL /tmp/ems-oracle-round3/unreadable/input.cnf [input-open]: CNF is not a readable regular file
trailer-junk exit=1
AOT: SKIPPED (disabled explicitly)
FAIL /tmp/ems-oracle-round3/trailer-junk/input.cnf [input-trailer]: unsupported data after SATLIB trailer
empty exit=1
FAIL instances-discovery [vacuity]: zero instances selected
unknown-case exit=1
FAIL options [configuration]: unknown selftest case: not-a-case
disabled-only-case exit=2
AOT: SKIPPED (disabled explicitly)
SELFTEST selection=perturbed-aot (partial; not the full suite)
SELFTEST perturbed-aot: SKIPPED (AOT not enabled)
SELFTEST BROKEN checked=0 expected=0 caught=0 controls=0 missed=0 (exit 2)
auto-degrade exit=0
AOT: SKIPPED (build failed rc=7; logs=/tmp/ems-native-oracle.kssc26/build.*; native/VM checks continue)
SUMMARY PASS selected=7 passed=7 native=7 VM=7 AOT=0
required-build exit=1
FAIL AOT [build]: rc=7; required AOT build failed; logs=/tmp/ems-native-oracle.dLVhCd/build.*
corrupted-native exit=10 verdict=SAT (independent confirmation of clause deletion)
unreadable-before exit=1
FAIL /tmp/ems-oracle-round3/unreadable/input.cnf [input]: unsupported data after SATLIB trailer
anchor-model-disabled exit=1
FAIL 4x4 [rung-fixture]: emitted CNF differs from /home/jon/src/wt/ems-oracle/benchmarks/oracle/tseitin_torus_4x4_odd.cnf
BOUNDARIES checked=13 unexpected=0
```

The boundary sweep also disables only the identity model and runs the resized
emitter: the banked 4x4 fixture still rejects it through
`[rung-fixture]`. This witnesses that the new anchor does not depend on the
model identifying its own error.

## Forward the caller's cap into production probes

During closeout, `--selftest-case clean --timeout 1` exposed a plumbing error:
the new child CLI had inherited the default cap rather than the caller's CLI
value. Before correction it incorrectly completed its positive control:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
SELFTEST selection=clean (partial; not the full suite)
CONTROL clean: PASS (production CLI rc=0)
SELFTEST CONTROL PASS checked=1 controls=1 (no negative case selected; exit 1)
Artifacts: /tmp/ems-native-oracle.0RV5Fr
```

The child invocation now explicitly forwards `--timeout`. The same command
then reports its one-second cap and the named 4x4 VM timeout; the incomplete
positive control becomes MISS, exit 2:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
SELFTEST selection=clean (partial; not the full suite)
SELFTEST clean: MISS (production CLI rc=1, expected rc=0 and named evidence)
PLANT clean: discovery (explicit fault injection)
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
PLANT clean: run (explicit fault injection)
Selection: files=2 requested-rungs=2 preflight-added=0 per-solver-cap=1s
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
IDENTITY 4x4: PASS (banked repository fixture, ordered DIMACS tokens)
RUN tseitin-4x4-odd
FAIL tseitin-4x4-odd [vm]: rc=124 (timeout rc=124 or 137 is FAILURE); see /tmp/ems-native-oracle.9P3tth/case.AfWYDb/vm.out
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
Artifacts: /tmp/ems-native-oracle.fAKJiW
```

The clean run and full selftest above were repeated after that correction.
The headline production-call deletion was also repeated on the final source:

```text
final regime call-site deletion exit=2
SELFTEST regime-3x3: MISS (production CLI rc=1, expected rc=1 and named evidence)
SELFTEST BROKEN checked=1 expected=1 caught=0 controls=0 missed=1 (exit 2)
```

## Scope and handoff

No EMS or toolchain behavior contradicting the round-3 brief was observed.
Larger rungs remain budget-skipped and opt-in. Two input anchors do not imply
independently captured fixtures for every larger dimension. A full source
bank update still requires reviewing the emitter, identity, and regime;
there is no automatic bank regeneration.

The lesson from the reproduced hole is enforced here: testing a helper body
is insufficient evidence that production calls it. Negative probes start
above those call sites, and deleting each site has a recorded MISS.
Commit-message handoff: `/tmp/ems-oracle-round3-commitmsg.txt`. Git metadata
is read-only for the builder; no commit or push was attempted.
