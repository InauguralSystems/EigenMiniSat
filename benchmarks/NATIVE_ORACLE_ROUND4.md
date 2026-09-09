# Native oracle: round 4 validation

Started from `df32c52` on `feat-native-oracle-diff`; `git status --short` was
empty. All changes remain under `benchmarks/`. The solver, loaded libraries,
emitter and existing fixtures are unchanged. The user reserved the commit for
the orchestrator; the proposed message is `/tmp/ems-oracle-round4-commitmsg.txt`.

All executions below were sequential, using the pinned v0.43.0 VM and
`AOT_BINARY=/tmp/ems_aot`. No actual AOT rebuild was needed; build-policy plants
use a temporary build script that exits 7.

## Shared preparation has its own post-condition

`prepare_cnf` now calls a separate Python parser after the existing awk stage.
It validates both inputs' headers, clause counts, terminators and literal
bounds, then compares ordered DIMACS tokens. Comments/whitespace and the
source's documented SATLIB tail are the only ignored material. Ordered equality
is stronger than clause-multiset preservation. Agreement between solvers cannot
validate their shared input transformation.

The `normalization-corruption` plant executes the real normalizer, substitutes
a header-consistent SAT formula in its output, and requires the full named
preservation failure before any solver runs. The positive `satlib-trailers`
control uses the repository's real SAT and UNSAT trailer fixtures. It requires
both normalized-input announcements, both correct verdicts, and exact completion
and AOT counts through the production CLI.

A separate reproduction changes the production awk itself, inserting these
rules before its `{print}` rule:

```awk
$1=="p" {print "p cnf " $3 " 1"; print "1 0"; changed=1; next}
changed {next}
```

The command used the otherwise unchanged harness in a temporary adjacent script:
`bash <mutant> --rungs '' --instances /tmp/ems-oracle-round4/unit-only --aot off`.
The directory contains a copy of the repo's `unit_unsat.cnf`. Output:

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: SKIPPED (disabled explicitly)
Selection: files=1 requested-rungs=0 preflight-added=0 per-solver-cap=120s
3x3: SKIPPED (budget; not selected in RUNGS)
4x4: SKIPPED (budget; not selected in RUNGS)
4x5: SKIPPED (budget; not selected in RUNGS)
4x6: SKIPPED (budget; not selected in RUNGS)
5x5: SKIPPED (budget; not selected in RUNGS)
5x6: SKIPPED (budget; not selected in RUNGS)
6x6: SKIPPED (budget; not selected in RUNGS)
FAIL /tmp/ems-oracle-round4/unit-only/unit_unsat.cnf [input-preservation]: ordered DIMACS tokens changed during shared preparation
EXIT=1
```
## Enrollment and attribution

`python3 benchmarks/oracle_selftest.py --sites` derives failure calls from the
actual harness source. Cases refer to these function/ordinal sites, not to a
separate hand-maintained list of required gates. Forward and reverse membership
are checked before a partial or full selftest. The full run also requires a
runtime witness for every eligible enrolled site. There is no fixed total to
bump when a new gate appears.

Each negative case supplies an independently written subject, class and evidence
template. The failure reporter records the actual call site and separate context
paths. The controller requires that site, the complete diagnostic fields and the
identical printed failure line. Dynamic paths are filled from the separate
context, never extracted from the diagnostic under test. Positive controls
require complete verdict and summary lines, including exact AOT status/counts.

The enrollment plant adds an unexecuted failure call in two syntactic forms
(direct and inside a quoted command substitution) and requires the exact
uncovered-site diagnostic. Its reverse-membership plant removes an enrolled
reporter call and requires the exact absent-site diagnostic. They invoke the
same CLI's selftest entry point; they do not call the enrollment helper.

Bash ERR traps report the triggering command's `BASH_LINENO`, even inside the
handler. That measured exception uses the observed `FUNCNAME` plus the unique
source-derived handler failure site. All other witnesses require line and
function agreement. The execution-error plant and trap-call deletion both ran.

Diagnostic mutations, with the actual mismatch evidence:

```text
MUTATION wrong-name: MISS exit=2
SELFTEST unreadable-input: MISS (production CLI rc=1; expected prepare_cnf:1: FAIL tseitin-3x3-odd [input-open]: CNF is not a readable regular file; observed site=prepare_cnf:1, diagnostic=['FAIL WRONG-INSTANCE [input-open]: CNF is not a readable regular file'])
MUTATION class-swap: MISS exit=2
SELFTEST unreadable-input: MISS (production CLI rc=1; expected prepare_cnf:1: FAIL tseitin-3x3-odd [input-open]: CNF is not a readable regular file; observed site=prepare_cnf:1, diagnostic=['FAIL tseitin-3x3-odd [WRONG-CLASS]: CNF is not a readable regular file'])
MUTATION wrong-evidence: MISS exit=2
SELFTEST unreadable-input: MISS (production CLI rc=1; expected prepare_cnf:1: FAIL tseitin-3x3-odd [input-open]: CNF is not a readable regular file; observed site=prepare_cnf:1, diagnostic=['FAIL tseitin-3x3-odd [input-open]: WRONG-EVIDENCE'])
```
## Deletion and mutation sweep

Each mutant is a temporary adjacent copy of the production shell script. Child
controls invoke that actual path. Failure-expression deletions are derived from
`failure_sites()`; production helper-call deletions use the appropriate negative
case, or the positive clean case where a later comparison can also catch the
planted fault. This preserves detection of disconnected call sites.

```text
MUTATION wrong-name: MISS exit=2
MUTATION class-swap: MISS exit=2
MUTATION wrong-evidence: MISS exit=2
MUTATION failure-execution_failed-1: MISS exit=2
MUTATION failure-main-1: MISS exit=2
MUTATION failure-main-2: MISS exit=2
MUTATION failure-main-3: MISS exit=2
MUTATION failure-main-4: MISS exit=2
MUTATION failure-main-5: MISS exit=2
MUTATION failure-main-6: MISS exit=2
MUTATION failure-main-7: MISS exit=2
MUTATION failure-main-8: MISS exit=2
MUTATION failure-main-9: MISS exit=2
MUTATION failure-main-10: MISS exit=2
MUTATION failure-main-11: MISS exit=2
MUTATION failure-main-12: MISS exit=2
MUTATION failure-main-13: MISS exit=2
MUTATION failure-main-14: MISS exit=2
MUTATION failure-main-15: MISS exit=2
MUTATION failure-check_population-1: MISS exit=2
MUTATION failure-run_zero-1: MISS exit=2
MUTATION failure-aot_build_failed-1: MISS exit=2
MUTATION failure-prepare_aot-1: MISS exit=2
MUTATION failure-prepare_aot-2: MISS exit=2
MUTATION failure-prepare_aot-3: MISS exit=2
MUTATION failure-prepare_aot-4: MISS exit=2
MUTATION failure-prepare_aot-5: MISS exit=2
MUTATION failure-prepare_cnf-1: MISS exit=2
MUTATION failure-prepare_cnf-2: MISS exit=2
MUTATION failure-prepare_cnf-3: MISS exit=2
MUTATION failure-prepare_cnf-4: MISS exit=2
MUTATION failure-prepare_cnf-5: MISS exit=2
MUTATION failure-prepare_cnf-6: MISS exit=2
MUTATION failure-check_prepared_cnf-1: MISS exit=2
MUTATION failure-check_rung_fixture-1: MISS exit=2
MUTATION failure-check_rung_fixture-2: MISS exit=2
MUTATION failure-check_rung_fixture-3: MISS exit=2
MUTATION failure-check_rung_identity-1: MISS exit=2
MUTATION failure-normalize_output-1: MISS exit=2
MUTATION failure-check_regime-1: MISS exit=2
MUTATION failure-parse_native-1: MISS exit=2
MUTATION failure-parse_native-2: MISS exit=2
MUTATION failure-parse_native-3: MISS exit=2
MUTATION failure-parse_native-4: MISS exit=2
MUTATION failure-parse_vm-1: MISS exit=2
MUTATION failure-check_verdict-1: MISS exit=2
MUTATION failure-check_aot-1: MISS exit=2
MUTATION failure-run_instance-1: MISS exit=2
MUTATION failure-run_instance-2: MISS exit=2
MUTATION failure-check_coverage-1: MISS exit=2
MUTATION failure-check_coverage-2: MISS exit=2
MUTATION call-discovery-population: MISS exit=2
MUTATION call-completion-population: MISS exit=2
MUTATION call-coverage: MISS exit=2
MUTATION call-finalization: MISS exit=2
MUTATION call-input-preparation: MISS exit=2
MUTATION call-input-preservation: MISS exit=2
MUTATION call-identity: MISS exit=2
MUTATION call-fixture: MISS exit=2
MUTATION call-emitted-token-read: MISS exit=2
MUTATION call-fixture-token-read: MISS exit=2
MUTATION call-regime: MISS exit=2
MUTATION call-regime-normalization: MISS exit=2
MUTATION call-vm-normalization: MISS exit=2
MUTATION call-aot-normalization: MISS exit=2
MUTATION call-verdict: MISS exit=2
MUTATION call-aot-diff: MISS exit=2
MUTATION call-native-parse: MISS exit=2
MUTATION call-vm-parse: MISS exit=2
MUTATION call-aot-setup: MISS exit=2
MUTATION call-aot-build: MISS exit=2
MUTATION call-aot-build-failure: MISS exit=2
MUTATION call-emission: MISS exit=2
MUTATION call-emitter-process: MISS exit=2
MUTATION call-vm-process: MISS exit=2
MUTATION call-aot-process: MISS exit=2
MUTATIONS DONE diagnostic=3 failure-sites=48 production-calls=25
MUTATION call-rung-instance: MISS exit=2
MUTATION call-file-instance: MISS exit=2
MUTATION normalization-injection: MISS exit=2
MUTATION reject-all-trailers: MISS exit=2
MUTATION enrollment-forward: MISS exit=2
MUTATION enrollment-reverse: MISS exit=2
EXTRA MUTATIONS DONE production-calls=2 injection=1 trailer-control=1 enrollment-directions=2
MUTATION call-error-trap: MISS exit=2
MUTATION enrollment-forward-final: MISS exit=2
MUTATION enrollment-reverse-final: MISS exit=2
FINAL PROBES DONE production-calls=1 enrollment-directions=2 actual-awk-corruption=1
```
The extra probes also removed the normalization injection (its case returned
`MISS` with a clean child exit), made the awk reject every `%` trailer (the real
trailer control returned `MISS`), and disabled each enrollment membership check
individually (the enrollment plant returned `MISS`). All reported mutation
`MISS` results had harness exit 2.

The exact mutation drivers used here are included below for reproduction. They
write temporary mutant scripts beside the harness and logs under `/tmp`:

```python
from pathlib import Path
import os, re, runpy, subprocess, tempfile
root=Path('/home/jon/src/wt/ems-oracle')
out=Path('/tmp/ems-oracle-round4')
harness=root/'benchmarks/run_native_oracle.sh'
source=harness.read_text()
api=runpy.run_path(str(root/'benchmarks/oracle_selftest.py'),run_name='oracle_api')

def probe(name,case,mutant):
    with tempfile.NamedTemporaryFile(mode='w',prefix='.oracle-round4-',suffix='.sh',dir=harness.parent,delete=False) as f:
        path=Path(f.name);f.write(mutant)
    try:
        r=subprocess.run(['bash',str(path),'--selftest-case',case],env=dict(os.environ,AOT_BINARY='/tmp/ems_aot',KEEP_WORK='0'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    finally:path.unlink()
    (out/('mutation-'+name+'.log')).write_text(r.stdout)
    lines=[line for line in r.stdout.splitlines() if ': MISS' in line]
    ok=r.returncode==2 and bool(lines)
    print(f'MUTATION {name}: {"MISS" if ok else "ESCAPED"} exit={r.returncode}',flush=True)
    if lines: print(lines[0],flush=True)
    if not ok: raise SystemExit(r.stdout)

def replace(name,case,old,new):
    assert source.count(old)==1,(name,source.count(old))
    probe(name,case,source.replace(old,new,1))

replace('wrong-name','unreadable-input','    prepare_cnf "$name" "$input" "$dir/input.cnf"','    prepare_cnf "WRONG-INSTANCE" "$input" "$dir/input.cnf"')
replace('class-swap','unreadable-input','fail "$name" input-open \'CNF is not a readable regular file\'','fail "$name" WRONG-CLASS \'CNF is not a readable regular file\'')
replace('wrong-evidence','unreadable-input','CNF is not a readable regular file','WRONG-EVIDENCE')
# Each production failure expression is derived, not enumerated here either.
for line,site in api['failure_sites'](source).items():
    lines=source.splitlines(keepends=True)
    assert re.search(r'\bfail\s',lines[line-1]),site
    lines[line-1]=re.sub(r'\bfail(?=\s)',':',lines[line-1],count=1)
    case=next(c.name for c in api['cases']() if c.site==site)
    probe('failure-'+site.replace(':','-'),case,''.join(lines))

calls=[
 ('discovery-population','vacuity-discovery','check_population discovery'),
 ('completion-population','vacuity-completion','check_population completion'),
 ('coverage','coverage-passed','    check_coverage\n'),
 ('finalization','vacuity-completion','\nfinish_run\n'),
 ('input-preparation','unreadable-input','    prepare_cnf "$name" "$input" "$dir/input.cnf"'),
 ('input-preservation','normalization-corruption','    check_prepared_cnf "$name" "$input" "$output"'),
 ('identity','identity-clauses','    check_rung_identity "$rung" "$work/$rung.cnf"'),
 ('fixture','fixture-3x3','    check_rung_fixture "$rung" "$cnf"'),
 ('emitted-token-read','emitted-read-error','cnf_tokens "$cnf"'),
 ('fixture-token-read','fixture-read-error','cnf_tokens "$fixture"'),
 ('regime','regime-3x3','check_regime "$rung" "$dir/vm.out"'),
 ('regime-normalization','output-normalize-error','normalize_output "$output" "$normalized" "$rung"'),
 ('vm-normalization','clean','normalize_output "$vm" "$vm.normalized" "$name"'),
 ('aot-normalization','clean','normalize_output "$aot" "$aot.normalized" "$name"'),
 ('verdict','wrong-ems-verdict','    check_verdict "$name"'),
 ('aot-diff','perturbed-aot','        check_aot "$name" "$dir/vm.out" "$dir/aot.out"'),
 ('native-parse','native-empty-report','    parse_native "$name" "$dir/native.out" "$dir/native.result" "$rc"'),
 ('vm-parse','empty-output','    parse_vm "$name" "$dir/vm.out"'),
 ('aot-setup','auto-degrades','\nprepare_aot\n'),
 ('aot-build','required-build-fails','if build_aot "$source_root"'),
 ('aot-build-failure','required-build-fails','        aot_build_failed "$rc"'),
 ('emission','identity-clauses','    emit_rung "$rung"'),
 ('emitter-process','clean','run_zero "$rung" emitter'),
 ('vm-process','solver-timeout','run_zero "$name" vm'),
 ('aot-process','clean','run_zero "$name" aot'),
]
for name,case,needle in calls:
    target=needle.split()[1] if needle.startswith('if ') else needle.split()[0]
    replace('call-'+name,case,needle,needle.replace(target,':',1))
print(f'MUTATIONS DONE diagnostic=3 failure-sites={len(api["failure_sites"](source))} production-calls={len(calls)}',flush=True)
```

```python
from pathlib import Path
exec(Path('/tmp/ems-oracle-round4/mutations.py').read_text().split("replace('wrong-name'")[0])
replace('call-rung-instance','clean','    run_instance "tseitin-$rung-odd" "$work/$rung.cnf" "$rung" "$measure"','    : "tseitin-$rung-odd" "$work/$rung.cnf" "$rung" "$measure"')
replace('call-file-instance','clean','do run_instance "$file" "$file"; done','do : "$file" "$file"; done')
replace('normalization-injection','normalization-corruption','    [[ -z "$plant" ]] || plant_fault normalized','    [[ -z "$plant" ]] || : normalized')
replace('reject-all-trailers','satlib-trailers','!tail {tail=1; next}','!tail {bad=1; exit 65}')
controller=root/'benchmarks/oracle_selftest.py'
saved=controller.read_text()
for label,old in [('enrollment-forward','if required-enrolled:'),('enrollment-reverse','if enrolled-required:')]:
    assert saved.count(old)==1
    try:
        controller.write_text(saved.replace(old,'if False:',1))
        probe(label,'enrollment',source)
    finally:
        controller.write_text(saved)
print('EXTRA MUTATIONS DONE production-calls=2 injection=1 trailer-control=1 enrollment-directions=2',flush=True)
```

```python
from pathlib import Path
exec(Path('/tmp/ems-oracle-round4/mutations.py').read_text().split("replace('wrong-name'")[0])
replace('call-error-trap','execution-error',"trap 'execution_failed \"$?\"' ERR","trap ':' ERR")
controller=root/'benchmarks/oracle_selftest.py'; saved=controller.read_text()
for label,old in [('enrollment-forward-final','if required-enrolled:'),('enrollment-reverse-final','if enrolled-required:')]:
    try:
        controller.write_text(saved.replace(old,'if False:',1))
        probe(label,'enrollment',source)
    finally:controller.write_text(saved)
inputs=out/'unit-only';inputs.mkdir(exist_ok=True)
(inputs/'unit_unsat.cnf').write_bytes((root/'tests/fixtures/unit_unsat.cnf').read_bytes())
mutant=source.replace('        {print}\n', '''        $1=="p" {print "p cnf " $3 " 1"; print "1 0"; changed=1; next}
        changed {next}
        {print}
''',1)
assert mutant!=source
with tempfile.NamedTemporaryFile(mode='w',prefix='.oracle-normalization-',suffix='.sh',dir=harness.parent,delete=False) as f:
    path=Path(f.name);f.write(mutant)
try:
    r=subprocess.run(['bash',str(path),'--rungs','','--instances',str(inputs),'--aot','off'],env=dict(os.environ,AOT_BINARY='/tmp/ems_aot'),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
finally:path.unlink()
(out/'actual-normalization-regression.log').write_text(r.stdout)
expected=f'FAIL {inputs}/unit_unsat.cnf [input-preservation]: ordered DIMACS tokens changed during shared preparation'
assert r.returncode==1 and expected in r.stdout.splitlines(),r.stdout
print('ACTUAL AWK CORRUPTION exit=1 '+expected,flush=True)
print('FINAL PROBES DONE production-calls=1 enrollment-directions=2 actual-awk-corruption=1',flush=True)
```

```text
MUTATION AUDIT production-calls=28 failure-sites=48 all-MISS=yes all-exit=2
```

## What the 4x4 capture buys

The bank is captured from the emitter being checked, so it cannot establish the
emitter's initial correctness. It adds bank-corruption and model-drift or
model-weakening detection. In this single-token sweep it adds no semantically
meaningful rejection beyond the model. Each ordered header/clause token was
mutated twice: numeric increment (text suffix for non-numbers), and sign toggle.
Every model acceptance was checked against the bank using `cmp`:

```text
ANCHOR SWEEP cases=1288 model-rejected=1160 model-accepted=128 accepted-only-0-to-minus0=yes bank-rejected-model-accepted=128
```
```python
from pathlib import Path
import subprocess
root=Path('/home/jon/src/wt/ems-oracle')
out=Path('/tmp/ems-oracle-round4')
lines=(root/'benchmarks/oracle/tseitin_torus_4x4_odd.cnf').read_text().splitlines()
positions=[(i,j,t) for i,line in enumerate(lines) if line.split() and line.split()[0]!='c' for j,t in enumerate(line.split())]
bank=out/'bank.tokens';candidate=out/'mutated.tokens'
bank.write_text(''.join(t+'\n' for _,_,t in positions))
rejected=accepted=bank_rejected=0
for i,j,t in positions:
    for new in (str(int(t)+1) if t.lstrip('-').isdigit() else t+'X', t[1:] if t.startswith('-') else '-'+t):
        changed=lines.copy(); fields=changed[i].split(); fields[j]=new; changed[i]=' '.join(fields)
        result=subprocess.run(['awk','-v','rows=4','-v','cols=4','-f',str(root/'benchmarks/torus_identity.awk')],input='\n'.join(changed)+'\n',text=True,capture_output=True)
        assert result.returncode in (0,1),result.stderr
        if result.returncode:
            rejected+=1
        else:
            accepted+=1
            assert t=='0' and new=='-0',(t,new)
            candidate.write_text(''.join(v+'\n' for line in changed if line.split() and line.split()[0]!='c' for v in line.split()))
            comparison=subprocess.run(['cmp','-s',str(bank),str(candidate)])
            assert comparison.returncode==1
            bank_rejected+=1
print(f'ANCHOR SWEEP cases={rejected+accepted} model-rejected={rejected} model-accepted={accepted} accepted-only-0-to-minus0=yes bank-rejected-model-accepted={bank_rejected}')
```
## Clean run

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh`

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
3x3                 592            731       0.003254             1.235x
4x4                9986          84150       0.226753             8.427x
SUMMARY PASS selected=20 passed=20 native=20 VM=20 AOT=20
Artifacts: /tmp/ems-native-oracle.2Xrmqq
EXIT=0
```
## Full selftest

`AOT_BINARY=/tmp/ems_aot KEEP_WORK=1 benchmarks/run_native_oracle.sh --selftest`

```text
Oracle: native MiniSat=/usr/bin/minisat; EMS-VM=/home/jon/src/wt/es-v043/src/eigenscript; policy=CDCL current defaults (regime C)
AOT: ENABLED (explicit prebuilt binary=/tmp/ems_aot; VM remains byte-exact reference)
ENROLLMENT derived=48 enrolled=48 (actual production source)
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
FAIL tseitin-3x3-odd [input-preservation]: ordered DIMACS tokens changed during shared preparation
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
WITNESSES observed=48 eligible=48
SELFTEST ALL RED checked=68 caught=65 controls=3 skipped=0 (intentional exit 1)
Artifacts: /tmp/ems-native-oracle.UBH7di
EXIT=1
```
## Scope

No EMS or AOT toolchain behavior contradicting the brief was observed. The
current default population is 18 existing CNFs plus two rungs. Larger standard
rungs remain explicit budget skips and are opt-in. Python 3 (stdlib only) is now
required for preparation verification and selftest enrollment. This gate checks
answers and output; SAT-model and DRAT proof checks remain separate.

The round-4 failure class is retained as enforcement: shared transformations
need preservation checks, new failure sites need enrolled production cases,
and a case's expected failure includes its subject and evidence as well as its
tag. No other repository, skill or memory file was changed.
