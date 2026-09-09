# Native oracle: D1/D2 final fixes

Started clean at `34aab66` on `feat-native-oracle-diff`. This round changes only
D1 (CNF line preservation) and D2 (sourced-file enrollment), their controls and
documentation. The commit is reserved for the orchestrator; proposed message:
`/tmp/ems-oracle-round5-commitmsg.txt`. Solves ran sequentially with
`AOT_BINARY=/tmp/ems_aot`; no real AOT rebuild was needed.

## D1: preserve data-line structure

The preparation checker now compares per-line token tuples, splits records on
LF as EMS does, and requires each header to occupy its own four-token line.
Comments, blank lines and within-line whitespace remain ignored. The actual
post-condition is stated in benchmarks/README.md:

> The torus check verifies the named encoding; the preparation post-condition
> guarantees that header and literal tokens retain their data-line grouping,
> modulo the documented trailer, comment and whitespace handling. It therefore
> rejects moving a literal onto the header line, which the two parsers treat
> differently.

The new `header-line-merge` plant applies exactly the reported transformation
at the production preparation boundary. The normal production checker must
reject it before solving. An additional repro inserts the critic's two rules
into the production awk itself and runs the K4 fixture file-only:

```awk
$1=="p" {hdr=$0; next}
hdr && NF && $1!="c" {print hdr" "$1; $1=""; print; hdr=""; next}
```

`mech_ref.cnf` is copied from `tests/corpus/k4_3color_unsat.cnf`; `mech.cnf`
applies those rules. The before/fixed checker commands are respectively:

```bash
python3 /tmp/ems-oracle-round5/cnf_preservation.before.py /tmp/ems-oracle-round5/mech_ref.cnf /tmp/ems-oracle-round5/mech.cnf
python3 benchmarks/cnf_preservation.py /tmp/ems-oracle-round5/mech_ref.cnf /tmp/ems-oracle-round5/mech.cnf
```

The production repro uses `bash <temporary-mutant> --rungs '' --instances
/tmp/ems-oracle-round5/repro-inputs --aot on` with the prebuilt AOT. Output:

```text
CNF CHECKER before exit=0: 
CNF CHECKER fixed exit=1: prepared: DIMACS header must occupy its own four-token line
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
Selection: files=1 requested-rungs=0 preflight-added=0 per-solver-cap=120s
3x3: SKIPPED (budget; not selected in RUNGS)
4x4: SKIPPED (budget; not selected in RUNGS)
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
FAIL /tmp/ems-oracle-round5/repro-inputs/k4.cnf [input-preservation]: prepared: DIMACS header must occupy its own four-token line
Artifacts: /tmp/ems-native-oracle.7z1F1E
HEADER-LINE REPRO exit=1
PREPARED DATA: p cnf 12 34 1 / 2 3 0 / 4 5 6 0 / 7 8 9 0 / 10 11
```
Exact repro driver:

```python
from pathlib import Path
import os, subprocess, tempfile
root=Path('/home/jon/src/wt/ems-oracle'); out=Path('/tmp/ems-oracle-round5')
for version,checker in [('before',out/'cnf_preservation.before.py'),('fixed',root/'benchmarks/cnf_preservation.py')]:
    result=subprocess.run(['python3',str(checker),str(out/'mech_ref.cnf'),str(out/'mech.cnf')],capture_output=True,text=True)
    print(f'CNF CHECKER {version} exit={result.returncode}: {result.stdout.strip()}',flush=True)
    assert result.returncode == (0 if version=='before' else 1)
inputs=out/'repro-inputs';inputs.mkdir(exist_ok=True)
(inputs/'k4.cnf').write_bytes((out/'mech_ref.cnf').read_bytes())
script=(root/'benchmarks/run_native_oracle.sh').read_text()
needle='        {print}\n'
assert script.count(needle)==1
script=script.replace(needle, '''        $1=="p" {hdr=$0; next}
        hdr && NF && $1!="c" {print hdr" "$1; $1=""; print; hdr=""; next}
'''+needle)
with tempfile.NamedTemporaryFile(mode='w',prefix='.oracle-r5-repro-',suffix='.sh',dir=root/'benchmarks',delete=False) as f:
    mutant=Path(f.name);f.write(script)
try:
    result=subprocess.run(['bash',str(mutant),'--rungs','','--instances',str(inputs),'--aot','on'],env=dict(os.environ,AOT_BINARY='/tmp/ems_aot',KEEP_WORK='1'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
finally:mutant.unlink()
print(result.stdout,end='')
print(f'HEADER-LINE REPRO exit={result.returncode}',flush=True)
assert result.returncode==1
expected=f'FAIL {inputs}/k4.cnf [input-preservation]: prepared: DIMACS header must occupy its own four-token line'
assert expected in result.stdout.splitlines()
work=Path(next(line[11:] for line in result.stdout.splitlines() if line.startswith('Artifacts: ')))
prepared=next(work.glob('case.*/input.cnf'))
print('PREPARED DATA:', ' / '.join(line.strip() for line in prepared.read_text().splitlines() if line.strip() and not line.startswith('c'))[:50])
```
## D2: follow the source graph

`production_sites()` recursively follows `source` and `.` commands from the
actual entry script, without a file list. It scans conditional source commands
too. Literal paths and `$ROOT` paths resolve from the CLI's project root;
unresolved dynamic operands fail enrollment. A visited-file set handles repeated
edges, and every failure location carries its source filename as well as its
line number. Sourced sites also have file-qualified case identifiers.

The existing `unknown plant` guard is now enrolled, with an exact diagnostic
case using `--plant bogus-plant-name`. The `enrollment-sourced` plant creates a
new gate two source edges away (including a `.` edge) and requires the exact
uncovered-site rejection. Both original enrollment directions still run:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
ENROLLMENT derived=49 enrolled=49 (production source graph)
SELFTEST selection=enrollment (partial; not the full suite)
SELFTEST enrollment: RED (production CLI rc=2; exact subject/class/evidence)
FAIL harness [enrollment]: uncovered production sites: uncovered_gate:1
FAIL harness [enrollment]: cases reference absent production sites: execution_failed:1
SELFTEST ALL RED checked=1 caught=1 controls=0 skipped=0 (intentional exit 1)
```
```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
ENROLLMENT derived=49 enrolled=49 (production source graph)
SELFTEST selection=enrollment-sourced (partial; not the full suite)
SELFTEST enrollment-sourced: RED (production CLI rc=2; exact subject/class/evidence)
FAIL harness [enrollment]: uncovered production sites: /tmp/ems-native-oracle.CDW1V3/source-inner.sh::sourced_gate:1
SELFTEST ALL RED checked=1 caught=1 controls=0 skipped=0 (intentional exit 1)
```
Scoped mutation controls restore the old flattened checker and disable only
recursive traversal beyond the entry script's immediate sources. Both controls
must report MISS and exit 2:

```text
MUTATION flattened-preparation: MISS exit=2
SELFTEST header-line-merge: MISS (production CLI rc=1; expected check_prepared_cnf:1: FAIL tseitin-3x3-odd [input-preservation]: prepared: DIMACS header must occupy its own four-token line; observed site=check_regime:1, diagnostic=['FAIL 3x3 [regime]: EMS-VM differs byte-for-byte from banked regime C (excluding ms)'])
MUTATION source-recursion: MISS exit=2
SELFTEST enrollment-sourced: MISS (production CLI rc=1; expected FAIL harness [enrollment]: uncovered production sites: /tmp/ems-native-oracle.faGs7E/source-inner.sh::sourced_gate:1; got rc=1)
```
## Clean run

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 bash benchmarks/run_native_oracle.sh`

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
3x3                 592            731       0.001778             1.235x
4x4                9986          84150       0.239762             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.CKuduO
EXIT=0
```
## Full selftest

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 bash benchmarks/run_native_oracle.sh --selftest`

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
ENROLLMENT derived=49 enrolled=49 (production source graph)
SELFTEST unknown-plant: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST execution-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST missing-argument: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST unknown-option: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST conflicting-modes: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-timeout: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-aot-mode: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST missing-tool: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST missing-vm: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST missing-native: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST not-executable: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-rung: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-dimensions: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST duplicate-rung: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-directory: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST find-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST sort-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST zero-instances: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST vacuity-discovery: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST vacuity-completion: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST solver-timeout: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST required-build-fails: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST absent-aot: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST mismatched-vm: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST version-missing: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST version-wrong: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-aot-binary: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST unreadable-input: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST unopenable-input: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST open-race: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST empty-input: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST normalizer-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST trailer-junk: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST normalizer-empty: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST normalization-corruption: RED (production CLI rc=1; exact subject/class/evidence)
FAIL tseitin-3x3-odd [input-preservation]: ordered DIMACS token lines changed during shared preparation
SELFTEST header-line-merge: RED (production CLI rc=1; exact subject/class/evidence)
FAIL tseitin-3x3-odd [input-preservation]: prepared: DIMACS header must occupy its own four-token line
SELFTEST header-count: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST variable-bound: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST unterminated-clause: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST missing-header: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-header: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST invalid-literal: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST emitted-read-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST fixture-read-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST fixture-3x3: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST regime-3x3: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST fixture-4x4: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST regime-4x4: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST resized-emitter: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST identity-clauses: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST vertex-order: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST output-normalize-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST native-empty-report: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST native-empty-result: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST native-unterminated-result: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST native-inconsistent-result: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST empty-output: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST corrupted-cnf: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST wrong-ems-verdict: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST perturbed-aot: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST native-error: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST odd-torus-answer: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST coverage-passed: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST coverage-native: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST coverage-vm: RED (production CLI rc=1; exact subject/class/evidence)
SELFTEST coverage-aot: RED (production CLI rc=1; exact subject/class/evidence)
CONTROL clean: PASS (production CLI rc=0; exact report)
CONTROL satlib-trailers: PASS (production CLI rc=0; exact report)
CONTROL auto-degrades: PASS (production CLI rc=0; exact report)
SELFTEST enrollment: RED (production CLI rc=2; exact subject/class/evidence)
FAIL harness [enrollment]: uncovered production sites: uncovered_gate:1
FAIL harness [enrollment]: cases reference absent production sites: execution_failed:1
SELFTEST enrollment-sourced: RED (production CLI rc=2; exact subject/class/evidence)
FAIL harness [enrollment]: uncovered production sites: /tmp/ems-native-oracle.DWplOa/source-inner.sh::sourced_gate:1
WITNESSES observed=49 eligible=49
SELFTEST ALL RED checked=71 caught=68 controls=3 skipped=0 (intentional exit 1)
Artifacts: /tmp/ems-native-oracle.DWplOa
EXIT=1
```
No EMS or toolchain behavior contradicting the final brief was observed.
Solver, emitter and fixture sources are unchanged. Larger rungs remain budget
skips as before.
