#!/usr/bin/env python3
"""Production-CLI controls with source-derived failure-site enrollment.

The scanner masks shell comments, quoted strings and heredoc bodies before
finding calls to fail. It does not enumerate a preferred subset of gate tags.
Each case names its intended function/ordinal and a complete, independent
expected diagnostic. Actual BASH_LINENO witnesses tie accepted reports back to
that source site. Missing enrollment is checked even for a partial selection.
"""
import collections
from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


def failure_sites(source):
    masked = []
    quote = None
    heredoc = None
    substitutions = []
    for line in source.splitlines():
        if heredoc:
            masked.append('')
            if line.lstrip('\t') == heredoc:
                heredoc = None
            continue
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == '`' and quote != "'":
                raise ValueError('use $(...) instead of backticks in production gate source')
            if ch == '$' and line[i:i+2] == '$(' and quote != "'":
                substitutions.append([quote, 1])
                quote = None
                result.extend('$('); i += 2; continue
            if quote:
                if ch == '\\' and quote == '"':
                    result.extend('  '); i += 2; continue
                if ch == quote:
                    quote = None
                result.append(' ')
            elif ch in "\"'":
                quote = ch; result.append(' ')
            elif ch == '#' and (i == 0 or line[i-1].isspace() or line[i-1] in ';|&('):
                result.extend(' ' * (len(line)-i)); break
            elif ch == '\\':
                result.extend('  '); i += 2; continue
            else:
                result.append(ch)
                if substitutions:
                    if ch == '(':
                        substitutions[-1][1] += 1
                    elif ch == ')':
                        substitutions[-1][1] -= 1
                        if not substitutions[-1][1]:
                            quote = substitutions.pop()[0]
            i += 1
        code = ''.join(result)
        # Only shell syntax outside quotes may introduce a heredoc. Here-strings
        # (<<<) are not heredocs. All production heredocs use literal delimiters.
        start = re.search(r'(?<!<)<<-?(?!<)', code)
        if start:
            match = re.match(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z_0-9]*)['\"]?", line[start.start():])
            if not match:
                raise ValueError('unsupported heredoc in failure-site scanner')
            heredoc = match[1]
        masked.append(code)
    if quote or heredoc or substitutions:
        raise ValueError('unclosed quote/heredoc in failure-site scanner')
    function = 'main'
    counts = collections.Counter()
    sites = {}
    for number, code in enumerate(masked, 1):
        definition = re.match(r'^([a-zA-Z_][a-zA-Z_0-9]*)\(\)\s*\{', code)
        if definition:
            function = definition[1]
        calls = list(re.finditer(r'\bfail\b(?!\s*\()', code))
        if len(calls) > 1:
            raise ValueError(f'multiple failure sites on line {number}; put each on its own line')
        if calls:
            counts[function] += 1
            sites[number] = f'{function}:{counts[function]}'
        if code == '}':
            function = 'main'
    if not sites:
        raise ValueError('zero production failure sites')
    return sites


@dataclass
class Case:
    name: str
    site: str = ''
    subject: str = ''
    tag: str = ''
    evidence: str = ''
    args: tuple = ()
    aot: bool = False
    pinned: bool = False
    control: bool = False


def cases():
    # This is the case inventory, not the required gate inventory. The latter
    # is derived afresh from the actual harness source (including mutant copies).
    result = []
    def add(name, site, subject, tag, evidence, **kw):
        result.append(Case(name, site, subject, tag, evidence, **kw))
    N = 'tseitin-3x3-odd'
    add('execution-error', 'execution_failed:1', 'harness', 'execution', 'unexpected command failure rc=7')
    add('missing-argument', 'main:1', 'options', 'configuration', '--instances needs a value', args=('--instances',))
    add('unknown-option', 'main:2', 'options', 'configuration', 'unknown option: --unknown', args=('--unknown',))
    add('conflicting-modes', 'main:3', 'options', 'configuration', 'selftest and plant modes are separate', args=('--selftest',))
    add('invalid-timeout', 'main:4', 'options', 'configuration', 'SOLVE_TIMEOUT must be positive integer seconds', args=('--timeout','0'))
    add('invalid-aot-mode', 'main:5', 'options', 'configuration', 'AOT must be auto, on, or off', args=('--aot','invalid'))
    add('missing-tool', 'main:6', 'setup', 'toolchain', 'missing awk')
    add('missing-vm', 'main:7', 'setup', 'toolchain', 'EMS-VM binary missing (set EIGENSCRIPT_BIN)')
    add('missing-native', 'main:8', 'setup', 'toolchain', 'native MiniSat binary missing (set MINISAT_BIN)')
    add('not-executable', 'main:9', 'setup', 'toolchain', 'solver is not executable')
    add('invalid-rung', 'main:10', 'invalid', 'configuration', 'expected rowsxcols', args=('--rungs','invalid'))
    add('invalid-dimensions', 'main:11', '2x3', 'configuration', 'dimensions must be 3..999', args=('--rungs','2x3'))
    add('duplicate-rung', 'main:12', '3x3', 'configuration', 'duplicate rung', args=('--rungs','3x3 3x3'))
    add('invalid-directory', 'main:13', 'instances', 'configuration', 'INSTANCE_DIR must be a directory', args=('--instances','/nonexistent/oracle-inputs'))
    add('find-error', 'main:14', 'instances', 'enumeration', 'find failed')
    add('sort-error', 'main:15', 'instances', 'enumeration', 'sort failed')
    for name, stage in [('zero-instances','discovery'),('vacuity-discovery','discovery'),('vacuity-completion','completion')]:
        add(name, 'check_population:1', f'instances-{stage}', 'vacuity', 'zero instances selected')
    add('solver-timeout', 'run_zero:1', N, 'vm', 'rc=124 (timeout rc=124 or 137 is FAILURE); see {CASE}/vm.out')
    add('required-build-fails','aot_build_failed:1','AOT','build','rc=7; required AOT build failed; logs={WORK}/build.*',pinned=True)
    add('absent-aot','prepare_aot:1','AOT','toolchain','requested toolchain absent')
    add('mismatched-vm','prepare_aot:2','AOT','toolchain','VM must be the same EIGS_DIR/src/eigenscript used to build AOT',pinned=True)
    add('version-missing','prepare_aot:3','AOT','toolchain','runtime checkout has no exact version tag',pinned=True)
    add('version-wrong','prepare_aot:4','AOT','toolchain','expected v0.43.0, got v0.42.0',pinned=True)
    add('invalid-aot-binary','prepare_aot:5','AOT','toolchain','AOT_BINARY must be an executable regular file',pinned=True)
    for name in ('unreadable-input','unopenable-input'):
        add(name,'prepare_cnf:1',N,'input-open','CNF is not a readable regular file')
    add('open-race','prepare_cnf:2',N,'input-open','cannot open CNF for reading')
    add('empty-input','prepare_cnf:3',N,'input','CNF is empty')
    add('normalizer-error','prepare_cnf:4',N,'input-read','CNF read/normalization failed rc=7')
    add('trailer-junk','prepare_cnf:5',N,'input-trailer','unsupported data after SATLIB trailer')
    add('normalizer-empty','prepare_cnf:6',N,'input','CNF contains no formula')
    for name, evidence in (
        ('normalization-corruption','ordered DIMACS tokens changed during shared preparation'),
        ('header-count','source: clause count declared=73 actual=72'),
        ('variable-bound','source: literal exceeds declared variable bound'),
        ('unterminated-clause','source: unterminated clause'),
        ('missing-header','source: missing DIMACS header'),
        ('invalid-header','source: invalid DIMACS header counts'),
        ('invalid-literal','source: non-integer clause token'),
    ):
        add(name,'check_prepared_cnf:1',N,'input-preservation',evidence)
    add('emitted-read-error','check_rung_fixture:1','3x3','rung-fixture','cannot read emitted CNF')
    add('fixture-read-error','check_rung_fixture:2','3x3','rung-fixture','cannot read banked fixture')
    for rung in ('3x3','4x4'):
        add('fixture-'+rung,'check_rung_fixture:3',rung,'rung-fixture','emitted CNF differs from {WORK}/corrupt-reference.cnf')
        add('regime-'+rung,'check_regime:1',rung,'regime','EMS-VM differs byte-for-byte from banked regime C (excluding ms)')
    for name,rung,evidence in (
        ('resized-emitter','4x4','expected p cnf 32 128; got p cnf 24 96'),
        ('identity-clauses','3x3','token 1: expected 1; got -1'),
        ('vertex-order','3x3','token 41: expected -2; got -3'),
    ):
        add(name,'check_rung_identity:1',rung,'rung-identity',evidence)
    add('output-normalize-error','normalize_output:1','3x3','normalize','output normalization failed')
    for name,ordinal,evidence in (
        ('native-empty-report',1,'need exactly one verdict, conflicts count and CPU time'),
        ('native-empty-result',2,'MiniSat result file missing or empty'),
        ('native-unterminated-result',3,'unterminated result status'),
        ('native-inconsistent-result',4,'inconsistent stdout/result/exit: UNSATISFIABLE/SAT/20'),
    ):
        add(name,f'parse_native:{ordinal}',N,'native-output',evidence)
    add('empty-output','parse_vm:1',N,'vm-output','need exactly one EMS verdict and conflicts count')
    for name in ('corrupted-cnf','wrong-ems-verdict'):
        add(name,'check_verdict:1',N,'verdict','DISAGREE native-MiniSat=UNSATISFIABLE EMS-VM=SATISFIABLE')
    add('perturbed-aot','check_aot:1',N,'aot-diff','DIVERGENCE EMS-VM reference != EMS-AOT (bytes excluding trailing ms)',aot=True)
    add('native-error','run_instance:1',N,'native','rc=3 (expected SAT=10/UNSAT=20; timeout is FAILURE)')
    add('odd-torus-answer','run_instance:2',N,'odd-torus','expected UNSATISFIABLE, oracle returned SATISFIABLE')
    for label in ('passed','native','vm'):
        evidence = 'selected=4 passed={passed} native={native} VM={vm}'.format(**{x:3 if x==label else 4 for x in ('passed','native','vm')})
        add('coverage-'+label,'check_coverage:1','instances','coverage',evidence)
    add('coverage-aot','check_coverage:2','instances','coverage','selected=4 AOT=3',aot=True)
    result.extend([Case('clean',control=True),Case('satlib-trailers',control=True),Case('auto-degrades',control=True,pinned=True),Case('enrollment')])
    return result


def enrollment(source, inventory):
    sites = failure_sites(source)
    required = set(sites.values())
    enrolled = {c.site for c in inventory if c.site}
    errors = []
    if required-enrolled:
        errors.append('uncovered production sites: '+', '.join(sorted(required-enrolled)))
    if enrolled-required:
        errors.append('cases reference absent production sites: '+', '.join(sorted(enrolled-required)))
    if any(c.site and not (c.subject and c.tag and c.evidence) for c in inventory):
        errors.append('incomplete expected diagnostic')
    if len({c.name for c in inventory}) != len(inventory):
        errors.append('duplicate case names')
    if errors:
        raise ValueError('; '.join(errors))
    return sites


def diagnostic(case, context):
    return 'FAIL {} [{}]: {}'.format(case.subject.format(**context),case.tag,case.evidence.format(**context))


def check_failure(case, rc, output, event_path, sites, root):
    fields = event_path.read_bytes().split(b'\0') if event_path.exists() else []
    if len(fields) != 8 or fields[-1] != b'':
        return False, 'expected exactly one seven-field production failure witness'
    try:
        line, function, subject, tag, evidence, work, directory = [v.decode() for v in fields[:-1]]
        line = int(line)
    except (ValueError, UnicodeError):
        return False, 'malformed production failure witness'

    context = dict(ROOT=str(root),WORK=work,CASE=directory)
    expected = diagnostic(case,context)
    observed = f'FAIL {subject} [{tag}]: {evidence}'
    actual_site = sites.get(line)
    if function == 'execution_failed':
        # Bash ERR traps report the triggering command's BASH_LINENO even
        # inside handler functions. The observed FUNCNAME identifies the sole
        # handler failure site; no other reporter is exempt from line matching.
        candidates = [v for v in sites.values() if v.startswith(function+':')]
        actual_site = candidates[0] if len(candidates)==1 else None
    elif actual_site and not actual_site.startswith(function+':'):
        actual_site = None
    human = [v for v in output.splitlines() if v.startswith('FAIL ')]
    ok = rc == 1 and actual_site == case.site and observed == expected and human == [expected]
    return ok, f'expected {case.site}: {expected}; observed site={actual_site}, diagnostic={human!r}'


def check_control(case, rc, output, mode, inputs, child_work):
    lines = output.splitlines()
    if rc != 0 or any(l.startswith('FAIL ') for l in lines):
        return False, 'expected clean production exit 0'
    if case.name == 'auto-degrades':
        expected = [f'AOT: SKIPPED (build failed rc=7; logs={child_work}/build.*; native/VM checks continue)',
                    'SUMMARY PASS selected=2 passed=2 native=2 VM=2 AOT=0']
        aot = 'SKIPPED'; files = [('sat.cnf','SATISFIABLE'),('unit.cnf','UNSATISFIABLE')]
    elif case.name == 'satlib-trailers':
        expected = [f'SUMMARY PASS selected=2 passed=2 native=2 VM=2 AOT={2*mode}']
        aot = 'PASS' if mode else 'SKIPPED'
        files = [('trailer-sat.cnf','SATISFIABLE'),('trailer-unsat.cnf','UNSATISFIABLE')]
        for name,_ in files:
            expected.append(f'INPUT {inputs/name}: normalized SATLIB trailer / final newline for every arm')
    else:
        expected = [f'SUMMARY PASS selected=4 passed=4 native=4 VM=4 AOT={4*mode}']
        for rung in ('3x3','4x4'):
            expected += [f'IDENTITY {rung}: PASS (header, every ordered literal and clause, odd charge)',
                         f'IDENTITY {rung}: PASS (banked repository fixture, ordered DIMACS tokens)',
                         f'PREFLIGHT {rung}: PASS (regime C, byte-exact EMS-VM output excluding ms)']
        aot = 'PASS' if mode else 'SKIPPED'; files = [('sat.cnf','SATISFIABLE'),('unit.cnf','UNSATISFIABLE')]
        for rung in ('3x3','4x4'):
            expected.append(f"PASS {'tseitin-'+rung+'-odd':53s} {'UNSATISFIABLE':13s} native=VM AOT={aot}")
    for name,verdict in files:
        expected.append(f'PASS {str(inputs/name):53s} {verdict:13s} native=VM AOT={aot}')
    # Full lines, exactly once: no prefix/tag-only or arbitrary evidence matching.
    ok = all(lines.count(line)==1 for line in expected)
    for prefix in ('PASS ', 'SUMMARY '):
        ok &= sorted(l for l in lines if l.startswith(prefix)) == sorted(l for l in expected if l.startswith(prefix))
    if case.name == 'auto-degrades':
        ok &= not any(l.startswith('AOT: ENABLED') for l in lines)
    return ok, 'expected full control lines: '+repr(expected)


def run(harness, work, mode, binary, selection):
    root = harness.parent.parent
    inventory = cases()
    try:
        sites = enrollment(harness.read_text(),inventory)
    except ValueError as error:
        print(f'FAIL harness [enrollment]: {error}',flush=True)
        print('SELFTEST enrollment: MISS (exit 2)',flush=True)
        return 2
    print(f'ENROLLMENT derived={len(sites)} enrolled={len({c.site for c in inventory if c.site})} (actual production source)',flush=True)
    if selection:
        inventory = [c for c in inventory if c.name==selection]
        if not inventory:
            print(f'SELFTEST {selection}: MISS (unknown case; exit 2)',flush=True); return 2
        print(f'SELFTEST selection={selection} (partial; not the full suite)',flush=True)
    inputs=work/'probe-inputs';inputs.mkdir()
    trailers=work/'trailer-inputs';trailers.mkdir()
    empty=work/'empty';empty.mkdir()
    for source,target in [('simple_sat.cnf',inputs/'sat.cnf'),('unit_unsat.cnf',inputs/'unit.cnf'),
                          ('satlib_trailer_sat.cnf',trailers/'trailer-sat.cnf'),('satlib_trailer_unsat.cnf',trailers/'trailer-unsat.cnf')]:
        shutil.copyfile(root/'tests/fixtures'/source,target)
    runtime=Path(os.environ.get('EIGS_DIR','/home/jon/src/wt/es-v043'))
    try:
        pinned = subprocess.run(['git','-C',str(runtime),'describe','--tags','--exact-match'],capture_output=True,text=True).stdout.strip()=='v0.43.0'
        pinned &= (runtime/'src/eigenscript').resolve() == Path(os.environ.get('ORACLE_VM_REF','/missing')).resolve()
    except OSError:
        pinned = False
    caught=controls=missed=skipped=0
    witnessed=set()
    for case in inventory:
        if (case.aot and not mode) or (case.pinned and not pinned):
            print(f'SELFTEST {case.name}: SKIPPED (required AOT arm or pinned runtime absent)',flush=True);skipped+=1;continue
        log=work/f'selftest-{case.name}.log'
        event=work/f'selftest-{case.name}.event'
        selected_inputs = trailers if case.name=='satlib-trailers' else inputs
        args=['--timeout',os.environ.get('ORACLE_SOLVE_TIMEOUT','120'),'--rungs','3x3 4x4','--instances',str(selected_inputs),'--aot','on' if mode or case.pinned else 'off','--plant',case.name]
        if case.name in ('auto-degrades','satlib-trailers'):
            args+=['--rungs','']
        if case.name=='zero-instances':
            args+=['--rungs','','--instances',str(empty)]
        args.extend(case.args)
        env=dict(os.environ,AOT_BINARY=binary,KEEP_WORK='0',ORACLE_FAILURE_LOG=str(event))
        if case.name=='enrollment':
            # A real new failure call, unreachable in this run, must still be
            # discovered. No helper invocation or hand-maintained expected count.
            uncovered = 'FAIL harness [enrollment]: uncovered production sites: uncovered_gate:1'
            shapes = []
            for call in ("fail planted-gate new-gate 'no enrolled case'",
                         "printf '%s' \"$(fail planted-gate new-gate 'no enrolled case')\""):
                shapes.append((harness.read_text()+"\n# fail comment-only ignored\nuncovered_gate() {\n    "+call+"\n}\n",uncovered))
            # Reverse membership gets a separate plant: remove one registered
            # reporter call. It cannot be absorbed by the uncovered-site check.
            original=harness.read_text().splitlines(keepends=True)
            first=min(sites)
            original[first-1]=re.sub(r'\bfail(?=\s)', ':', original[first-1], count=1)
            shapes.append((''.join(original),'FAIL harness [enrollment]: cases reference absent production sites: '+sites[first]))
            outputs = []
            failures = []
            ok = True
            for mutated_source,expected in shapes:
                with tempfile.NamedTemporaryFile(mode='w',prefix='.oracle-uncovered-',suffix='.sh',dir=harness.parent,delete=False) as f:
                    mutant=Path(f.name)
                    f.write(mutated_source)
                try:
                    child=subprocess.run(['bash',str(mutant),'--selftest-case','missing-argument','--aot','off'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                finally:
                    mutant.unlink()
                outputs.append(child.stdout)
                rc=child.returncode
                shape_ok = rc==2 and [l for l in child.stdout.splitlines() if l.startswith('FAIL ')]==[expected] and 'SELFTEST enrollment: MISS (exit 2)' in child.stdout.splitlines()
                ok &= shape_ok
                if not shape_ok:
                    failures.append(f'expected {expected}; got rc={rc}')
            output=''.join(outputs)
            reason='; '.join(failures)
        else:
            child=subprocess.run(['bash',str(harness),*args],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            output=child.stdout;rc=child.returncode
            if case.control:
                # For dynamic build-log paths use a dedicated context record,
                # never an unconstrained pattern over the diagnostic being tested.
                ctx=Path(str(event)+'.context')
                child_work=ctx.read_text().strip() if ctx.exists() else ''
                ok,reason=check_control(case,rc,output,mode,selected_inputs,child_work)
            else:
                ok,reason=check_failure(case,rc,output,event,sites,root)
        log.write_text(output)
        if ok:
            if case.control:
                controls+=1; print(f'CONTROL {case.name}: PASS (production CLI rc=0; exact report)',flush=True)
            else:
                caught+=1; witnessed.add(case.site)
                print(f'SELFTEST {case.name}: RED (production CLI rc={rc}; exact subject/class/evidence)',flush=True)
                if case.name in ('normalization-corruption','enrollment'):
                    for line in dict.fromkeys(l for l in output.splitlines() if l.startswith('FAIL ')):
                        print(line,flush=True)
        else:
            missed+=1
            print(f'SELFTEST {case.name}: MISS (production CLI rc={rc}; {reason})',flush=True)
            print(output,flush=True)
    if not selection:
        eligible={c.site for c in inventory if c.site and not ((c.aot and not mode) or (c.pinned and not pinned))}
        missing=eligible-witnessed
        if missing:
            missed+=1;print('SELFTEST witnesses: MISS (unwitnessed: '+', '.join(sorted(missing))+')',flush=True)
        print(f'WITNESSES observed={len(witnessed-{""})} eligible={len(eligible)}',flush=True)
    checked=caught+controls+missed
    if missed or (not caught and not controls):
        print(f'SELFTEST BROKEN caught={caught} controls={controls} missed={missed} skipped={skipped} (exit 2)',flush=True)
        return 2
    label = 'ALL RED' if caught else 'CONTROL PASS'
    print(f'SELFTEST {label} checked={checked} caught={caught} controls={controls} skipped={skipped} (intentional exit 1)',flush=True)
    return 1


if __name__=='__main__':
    if sys.argv[1:] == ['--list']:
        print('\n'.join(c.name for c in cases()))
    elif sys.argv[1:] == ['--sites']:
        for line,site in failure_sites(Path(__file__).with_name('run_native_oracle.sh').read_text()).items():
            print(f'{site}\t{line}')
    else:
        sys.exit(run(Path(sys.argv[1]),Path(sys.argv[2]),int(sys.argv[3]),sys.argv[4],sys.argv[5]))
