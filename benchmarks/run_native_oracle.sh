#!/usr/bin/env bash
# Native MiniSat is the answer oracle. EMS-VM is the AOT output oracle.
# All heavy work is sequential; a timeout is always a named failure.
set -Eeuo pipefail
export LC_ALL=C
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

fail() { printf 'FAIL %s [%s]: %s\n' "$1" "$2" "$3" >&2; exit 1; }
trap 'rc=$?; printf "FAIL harness [execution]: line=%s rc=%s\n" "$LINENO" "$rc" >&2; exit 1' ERR

usage() {
    cat <<'EOF'
Usage: benchmarks/run_native_oracle.sh [--selftest] [--rungs '3x3 4x4']
       [--instances DIR] [--aot auto|on|off] [--timeout SECONDS]

Defaults: rungs 3x3 4x4; all tests/corpus/**/*.cnf and tests/fixtures/*.cnf.
--instances replaces BOTH default file directories (recursively); an empty
directory together with --rungs '' is a deliberate zero-instance FAILURE.
Omitted standard ladder rungs print SKIPPED (budget), never PASS.

Environment (CLI options take precedence):
  RUNGS='3x3 4x4'            Space- or comma-separated dimensions, each >= 3
  INSTANCE_DIR=...           Replacement file directory (empty is an error)
  EIGS_DIR=...               Default /home/jon/src/wt/es-v043
  EIGENSCRIPT_BIN=...        VM; with AOT must be EIGS_DIR/src/eigenscript
  MINISAT_BIN=...            Default /usr/bin/minisat
  AOT=auto                  auto/on/off; auto skips only absent toolchains
  AOT_BUILD=.../aot/build.sh  Default dev-box ouroboros toolchain
  AOT_BINARY=...             Explicit reuse of a previously built EMS binary
  SOLVE_TIMEOUT=120          Seconds per solver AND emitter; timeout FAILS
  BUILD_TIMEOUT=600          Seconds for the one AOT build
  KEEP_WORK=1               Keep logs, CNFs, and build under /tmp

--selftest runs clean controls and the real gate against planted faults.
Exit 1 = every enabled plant caught (intentional RED); exit 2 = selftest broken
or a plant escaped. Setup/tool failures exit 1 without SELFTEST ALL RED.
Normal run: exit 0 only for a nonempty, fully completed selection.
EOF
}

RUNGS=${RUNGS-'3x3 4x4'}
instances_set=0
[[ ! ${INSTANCE_DIR+x} ]] || instances_set=1
INSTANCE_DIR=${INSTANCE_DIR-}
AOT=${AOT:-auto}
SOLVE_TIMEOUT=${SOLVE_TIMEOUT:-120}
BUILD_TIMEOUT=${BUILD_TIMEOUT:-600}
selftest=0
while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --selftest) selftest=1; shift ;;
        --rungs|--instances|--aot|--timeout)
            (($# >= 2)) || fail options configuration "$1 needs a value"
            case "$1" in
                --rungs) RUNGS=$2 ;;
                --instances) INSTANCE_DIR=$2; instances_set=1 ;;
                --aot) AOT=$2 ;;
                --timeout) SOLVE_TIMEOUT=$2 ;;
            esac
            shift 2 ;;
        *) fail options configuration "unknown option: $1" ;;
    esac
done
for setting in SOLVE_TIMEOUT BUILD_TIMEOUT; do
    [[ ${!setting} =~ ^[1-9][0-9]*$ ]] || fail options configuration "$setting must be positive integer seconds"
done
[[ "$AOT" =~ ^(auto|on|off)$ ]] || fail options configuration 'AOT must be auto, on, or off'

EIGS_DIR=${EIGS_DIR:-/home/jon/src/wt/es-v043}
if [[ ${EIGENSCRIPT_BIN+x} ]]; then
    EIGS=$EIGENSCRIPT_BIN
elif [[ -x "$EIGS_DIR/src/eigenscript" ]]; then
    EIGS=$EIGS_DIR/src/eigenscript
else
    EIGS=eigenscript
fi
MINISAT=${MINISAT_BIN:-/usr/bin/minisat}
AOT_BUILD=${AOT_BUILD:-/home/jon/src/InauguralSystems/EigenScriptEcosystem/ouroboros/aot/build.sh}
for tool in timeout awk sed cmp diff find sort tar realpath grep; do
    command -v "$tool" >/dev/null || fail setup toolchain "missing $tool"
done
EIGS=$(command -v "$EIGS") || fail setup toolchain 'EMS-VM binary missing (set EIGENSCRIPT_BIN)'
MINISAT=$(command -v "$MINISAT") || fail setup toolchain 'native MiniSat binary missing (set MINISAT_BIN)'
EIGS=$(realpath "$EIGS")
MINISAT=$(realpath "$MINISAT")
[[ -x "$EIGS" && -x "$MINISAT" ]] || fail setup toolchain 'solver is not executable'
vm_cmd=("$EIGS" "$ROOT/minisat.eigs")
aot_cmd=()
work=$(mktemp -d /tmp/ems-native-oracle.XXXXXX)
cleanup() {
    if [[ ${KEEP_WORK:-0} == 1 ]]; then
        printf 'Artifacts: %s\n' "$work"
    else
        rm -rf -- "$work"
    fi
}
trap cleanup EXIT

# Validate and enumerate BEFORE building or solving. Discovery errors and empty
# explicitly selected directories are not hidden by process substitutions.
files=()
rungs=()
declare -A seen=()
RUNGS=${RUNGS//$'\n'/ }
read -r -a rungs <<< "${RUNGS//,/ }" || true
for rung in "${rungs[@]}"; do
    [[ "$rung" =~ ^[1-9][0-9]*x[1-9][0-9]*$ ]] || fail "$rung" configuration 'expected rowsxcols'
    rows=${rung%x*}; cols=${rung#*x}
    ((${#rows} <= 3 && ${#cols} <= 3 && rows >= 3 && cols >= 3)) || fail "$rung" configuration 'dimensions must be 3..999'
    [[ ! ${seen[$rung]+yes} ]] || fail "$rung" configuration 'duplicate rung'
    seen[$rung]=1
done
if ((instances_set)); then
    [[ -n "$INSTANCE_DIR" && -d "$INSTANCE_DIR" ]] || fail instances configuration 'INSTANCE_DIR must be a directory'
    dirs=("$INSTANCE_DIR")
else
    dirs=("tests/corpus" "tests/fixtures")
fi
find "${dirs[@]}" -type f -name '*.cnf' -print0 > "$work/discovered" || fail instances enumeration 'find failed'
sort -z "$work/discovered" > "$work/sorted" || fail instances enumeration 'sort failed'
mapfile -d '' -t files < "$work/sorted"
selected=$((${#files[@]} + ${#rungs[@]}))
passed=0
native_runs=0
vm_runs=0
aot_runs=0
aot_enabled=0

check_population() {
    ((selected > 0)) || fail instances vacuity 'zero instances selected; zero solvers ran'
}
((selftest)) || check_population

run_zero() {
    local name=$1 arm=$2 out=$3 err=$4 cap=$5 rc
    shift 5
    if timeout --kill-after=5s "${cap}s" "$@" > "$out" 2> "$err"; then
        return 0
    else
        rc=$?
        cat "$err" >&2
        fail "$name" "$arm" "rc=$rc (timeout rc=124 or 137 is FAILURE); see $out"
    fi
}

prepare_aot() {
    if [[ "$AOT" == off ]]; then
        echo 'AOT: SKIPPED (disabled explicitly)'
        return
    fi
    if [[ ! -f "$AOT_BUILD" || ! -x "$EIGS_DIR/src/eigenscript" || ! -f "$EIGS_DIR/src/vm.c" ]]; then
        [[ "$AOT" == auto ]] || fail AOT toolchain 'requested toolchain absent'
        echo 'AOT: SKIPPED (toolchain absent: need AOT_BUILD and EIGS_DIR v0.43.0)'
        return
    fi
    EIGS_DIR=$(realpath "$EIGS_DIR")
    [[ "$EIGS" == "$(realpath "$EIGS_DIR/src/eigenscript")" ]] || fail AOT toolchain 'VM must be the same EIGS_DIR/src/eigenscript used to build AOT'
    local version source_root
    version=$(git -C "$EIGS_DIR" describe --tags --exact-match 2>/dev/null) || fail AOT toolchain 'runtime checkout has no exact version tag'
    [[ "$version" == v0.43.0 ]] || fail AOT toolchain "expected v0.43.0, got $version"
    if [[ ${AOT_BINARY+x} ]]; then
        [[ -n "$AOT_BINARY" && -f "$AOT_BINARY" && -x "$AOT_BINARY" ]] || fail AOT toolchain 'AOT_BINARY must be an executable regular file'
        aot_cmd=("$(realpath "$AOT_BINARY")")
        aot_enabled=1
        printf 'AOT: ENABLED (explicit prebuilt binary=%s; VM remains byte-exact reference)\n' "${aot_cmd[0]}"
        return
    fi
    source_root=$(cd "$(dirname "$AOT_BUILD")/.." && pwd)
    # build.sh hardcodes a writable cache beside itself. Snapshot SOURCE only;
    # no toolchain checkout or runtime binary is modified/copied. Include the
    # whole source directories so future local include dependencies stay visible.
    mkdir -p "$work/ouroboros"
    tar -C "$source_root" --exclude='build' --exclude='*.o' --exclude='*.a' \
        -cf "$work/toolchain.tar" eigs.json aot src || fail AOT build 'cannot snapshot source toolchain'
    tar -C "$work/ouroboros" -xf "$work/toolchain.tar" || fail AOT build 'cannot unpack source toolchain'
    echo "AOT: BUILD (once, runtime=$version, cap=${BUILD_TIMEOUT}s)"
    run_zero AOT build "$work/build.out" "$work/build.err" "$BUILD_TIMEOUT" \
        env EIGS_DIR="$EIGS_DIR" EIGS="$EIGS" bash "$work/ouroboros/aot/$(basename "$AOT_BUILD")" \
        "$ROOT/minisat.eigs" "$work/minisat-aot"
    [[ -x "$work/minisat-aot" ]] || fail AOT build 'build returned without an executable'
    aot_cmd=("$work/minisat-aot")
    aot_enabled=1
    echo 'AOT: ENABLED (EMS-VM is the byte-exact reference; only trailing ms stripped)'
}

# MiniSat rejects SATLIB %/0 trailers. Remove ONLY a standalone %, optional
# standalone 0, and blank tail. Reject any other tail; leave all formula bytes
# alone. Both solvers receive this same temporary file. Never change fixtures.
prepare_cnf() {
    local name=$1 input=$2 output=$3
    [[ -s "$input" ]] || fail "$name" input 'CNF missing or empty'
    awk '
        /^[[:space:]]*%[[:space:]]*$/ && !tail {tail=1; next}
        tail && /^[[:space:]]*$/ {next}
        tail && /^[[:space:]]*0[[:space:]]*$/ && !zero {zero=1; next}
        tail {bad=1; exit 1}
        {print}
        END {if (bad) exit 1}
    ' "$input" > "$output" || fail "$name" input 'unsupported data after SATLIB trailer'
    [[ -s "$output" ]] || fail "$name" input 'CNF contains no formula'
    if ! cmp -s "$input" "$output"; then
        printf 'INPUT %s: normalized SATLIB trailer / final newline for every arm\n' "$name"
    fi
}

parse_native() {
    local name=$1 out=$2 result=$3 rc=$4 parsed status
    parsed=$(awk '
        /^(SATISFIABLE|UNSATISFIABLE)$/ {verdict=$0; nv++}
        /^conflicts[[:space:]]*:/ {if ($3 !~ /^[0-9]+$/) bad=1; conflicts=$3; nc++}
        /^CPU time[[:space:]]*:/ {if ($4 !~ /^[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$/ || $5!="s") bad=1; cpu=$4; nt++}
        END {if (bad || nv!=1 || nc!=1 || nt!=1) exit 1; print verdict, conflicts, cpu}
    ' "$out") || fail "$name" native-output 'need exactly one verdict, conflicts count and CPU time'
    read -r native_verdict native_conflicts native_cpu <<< "$parsed"
    [[ -s "$result" ]] || fail "$name" native-output 'MiniSat result file missing or empty'
    IFS= read -r status < "$result" || fail "$name" native-output 'unterminated result status'
    case "$native_verdict:$status:$rc" in
        SATISFIABLE:SAT:10|UNSATISFIABLE:UNSAT:20) ;;
        *) fail "$name" native-output "inconsistent stdout/result/exit: $native_verdict/$status/$rc" ;;
    esac
}

parse_vm() {
    local name=$1 out=$2 parsed
    parsed=$(awk '
        /^s / {nv++; if ($0!="s SATISFIABLE" && $0!="s UNSATISFIABLE") bad=1; verdict=$2}
        /^c / {for (i=2;i<=NF;i++) if ($i ~ /^conflicts=/) {
            value=$i; sub(/^conflicts=/,"",value); nc++;
            if (value !~ /^[0-9]+$/) bad=1; conflicts=value
        }}
        END {if (bad || nv!=1 || nc!=1) exit 1; print verdict, conflicts}
    ' "$out") || fail "$name" vm-output 'need exactly one EMS verdict and conflicts count'
    read -r vm_verdict vm_conflicts <<< "$parsed"
}

check_verdict() {
    [[ "$native_verdict" == "$vm_verdict" ]] || fail "$1" verdict "DISAGREE native-MiniSat=$native_verdict EMS-VM=$vm_verdict"
}

check_aot() {
    local name=$1 vm=$2 aot=$3
    # File comparison preserves newlines, blank lines, and every other byte.
    # In particular, never strip the entire suffix beginning with an arbitrary
    # ms= token: that could hide a second output field or a planted comment.
    sed -E '/^c /s/ ms=[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$//' "$vm" > "$vm.normalized" || fail "$name" normalize 'VM normalization failed'
    sed -E '/^c /s/ ms=[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$//' "$aot" > "$aot.normalized" || fail "$name" normalize 'AOT normalization failed'
    if ! cmp -s "$vm.normalized" "$aot.normalized"; then
        diff -u "$vm.normalized" "$aot.normalized" >&2 || true
        fail "$name" aot-diff 'DIVERGENCE EMS-VM reference != EMS-AOT (bytes excluding trailing ms)'
    fi
}

run_instance() {
    local name=$1 input=$2 rung=${3:-} dir rc aot_status=SKIPPED ratio
    dir=$(mktemp -d "$work/case.XXXXXX")
    prepare_cnf "$name" "$input" "$dir/input.cnf"
    printf '%s\n' "$name" > "$dir/name"
    echo "RUN $name"
    if timeout --kill-after=5s "${SOLVE_TIMEOUT}s" "$MINISAT" "$dir/input.cnf" "$dir/native.result" > "$dir/native.out" 2> "$dir/native.err"; then
        rc=0
    else
        rc=$?
    fi
    case "$rc" in
        10|20) ;;
        *) cat "$dir/native.err" >&2; fail "$name" native "rc=$rc (expected SAT=10/UNSAT=20; timeout is FAILURE)" ;;
    esac
    parse_native "$name" "$dir/native.out" "$dir/native.result" "$rc"
    native_runs=$((native_runs+1))
    run_zero "$name" vm "$dir/vm.out" "$dir/vm.err" "$SOLVE_TIMEOUT" "${vm_cmd[@]}" --cdcl "$dir/input.cnf"
    parse_vm "$name" "$dir/vm.out"
    vm_runs=$((vm_runs+1))
    check_verdict "$name"
    if [[ -n "$rung" && "$native_verdict" != UNSATISFIABLE ]]; then
        fail "$name" odd-torus "expected UNSATISFIABLE, oracle returned $native_verdict"
    fi
    if ((aot_enabled)); then
        run_zero "$name" aot "$dir/aot.out" "$dir/aot.err" "$SOLVE_TIMEOUT" "${aot_cmd[@]}" --cdcl "$dir/input.cnf"
        # stderr is retained separately: stdout is the solver CLI contract.
        check_aot "$name" "$dir/vm.out" "$dir/aot.out"
        aot_runs=$((aot_runs+1))
        aot_status=PASS
    fi
    passed=$((passed+1))
    printf 'PASS %-53s %-13s native=VM AOT=%s\n' "$name" "$vm_verdict" "$aot_status"
    printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$native_verdict" "$native_conflicts" "$native_cpu" "$vm_conflicts" >> "$work/results.tsv"
    if [[ -n "$rung" ]]; then
        ratio=$(awk -v n="$native_conflicts" -v e="$vm_conflicts" 'BEGIN {if (e==0) print "n/a (EMS=0)"; else printf "%.3fx", n/e}')
        printf '%-8s %14s %14s %14s %18s\n' "$rung" "$vm_conflicts" "$native_conflicts" "$native_cpu" "$ratio" >> "$work/search-table"
    fi
}

finish_run() {
    check_population
    ((passed == selected && native_runs == selected && vm_runs == selected)) || fail instances coverage "selected=$selected passed=$passed native=$native_runs VM=$vm_runs"
    ((!aot_enabled || aot_runs == selected)) || fail instances coverage "selected=$selected AOT=$aot_runs"
    printf 'SUMMARY PASS selected=%s passed=%s native=%s VM=%s AOT=%s\n' "$selected" "$passed" "$native_runs" "$vm_runs" "$aot_runs"
}

selftest_run() {
    local name reason rc caught=0 missed=0 expected=5
    # Tiny real SAT/UNSAT controls prove the gates do not simply always fail.
    run_instance control-unsat tests/fixtures/unit_unsat.cnf
    run_instance control-sat tests/fixtures/simple_sat.cnf
    # Deleting the negative unit makes this SAT; ONLY EMS receives this copy.
    # Corrupting the common CNF would correctly make both solvers agree on SAT.
    sed -e 's/^p cnf 1 2$/p cnf 1 1/' -e '/^-1 0$/d' tests/fixtures/unit_unsat.cnf > "$work/corrupt.cnf"
    export ORACLE_REAL_VM="$EIGS" ORACLE_CORRUPT="$work/corrupt.cnf"
    cat > "$work/corrupt-vm.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args=("$@")
args[${#args[@]}-1]=$ORACLE_CORRUPT
exec "$ORACLE_REAL_VM" "${args[@]}"
EOF
    cat > "$work/wrong-vm.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
"$ORACLE_REAL_VM" "$@" | sed 's/^s UNSATISFIABLE$/s SATISFIABLE/'
EOF
    cat > "$work/perturbed-aot.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
"$ORACLE_REAL_AOT" "$@"
printf 'c planted AOT byte\n'
EOF
    cat > "$work/dead-vm.sh" <<'EOF'
#!/usr/bin/env bash
exec sleep 10
EOF
    export ORACLE_REAL_AOT="${aot_cmd[0]:-}"
    ((aot_enabled)) && expected=6
    for name in corrupted-cnf wrong-ems-verdict perturbed-aot zero-instances solver-timeout empty-output; do
        if [[ "$name" == perturbed-aot ]] && ((!aot_enabled)); then
            echo 'SELFTEST perturbed-aot: SKIPPED (AOT disabled or absent)'
            continue
        fi
        case "$name" in
            corrupted-cnf|wrong-ems-verdict) reason=verdict ;;
            perturbed-aot) reason=aot-diff ;;
            zero-instances) reason=vacuity ;;
            solver-timeout) reason=vm ;;
            empty-output) reason=vm-output ;;
        esac
        # Subshells use the SAME production runner and comparators. Match the
        # intended failure category as well as rc; an unrelated crash is MISS.
        if (
            case "$name" in
                corrupted-cnf) vm_cmd=(bash "$work/corrupt-vm.sh" "$ROOT/minisat.eigs") ;;
                wrong-ems-verdict) vm_cmd=(bash "$work/wrong-vm.sh" "$ROOT/minisat.eigs") ;;
                perturbed-aot) aot_cmd=(bash "$work/perturbed-aot.sh") ;;
                zero-instances) selected=0; passed=0; native_runs=0; vm_runs=0; aot_runs=0; finish_run; exit 0 ;;
                solver-timeout) vm_cmd=(bash "$work/dead-vm.sh"); SOLVE_TIMEOUT=1 ;;
                empty-output) vm_cmd=(true) ;;
            esac
            run_instance "$name" tests/fixtures/unit_unsat.cnf
        ) > "$work/selftest-$name.log" 2>&1; then rc=0; else rc=$?; fi
        local failure_name=$name
        [[ "$name" != zero-instances ]] || failure_name=instances
        if [[ "$rc" == 1 ]] && grep -qF "FAIL $failure_name [$reason]:" "$work/selftest-$name.log"; then
            printf 'SELFTEST %s: RED (rc=%s, %s)\n' "$name" "$rc" "$reason"
            caught=$((caught+1))
        else
            printf 'SELFTEST %s: MISS (rc=%s, expected %s)\n' "$name" "$rc" "$reason"
            cat "$work/selftest-$name.log"
            missed=$((missed+1))
        fi
    done
    if ((missed != 0 || caught != expected)); then
        printf 'SELFTEST BROKEN caught=%s expected=%s missed=%s (exit 2)\n' "$caught" "$expected" "$missed"
        exit 2
    fi
    printf 'SELFTEST ALL RED caught=%s expected=%s (intentional exit 1)\n' "$caught" "$expected"
    exit 1
}

printf 'Oracle: native MiniSat=%s; EMS-VM=%s; policy=CDCL current defaults\n' "$MINISAT" "$EIGS"
prepare_aot
((selftest)) && selftest_run
printf 'Selection: files=%s rungs=%s per-solver-cap=%ss\n' "${#files[@]}" "${#rungs[@]}" "$SOLVE_TIMEOUT"
for rung in 3x3 4x4 4x5 4x6 5x5 5x6 6x6; do
    [[ ${seen[$rung]+yes} ]] || printf '%s: SKIPPED (budget; not selected in RUNGS)\n' "$rung"
done
for file in "${files[@]}"; do run_instance "$file" "$file"; done
for rung in "${rungs[@]}"; do
    run_zero "$rung" emitter "$work/$rung.cnf" "$work/$rung.emitter.err" "$SOLVE_TIMEOUT" \
        "$EIGS" benchmarks/dump_tseitin_cnf.eigs "${rung%x*}" "${rung#*x}"
    run_instance "tseitin-$rung-odd" "$work/$rung.cnf" "$rung"
done
echo 'SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)'
printf '%-8s %14s %14s %14s %18s\n' rung EMS_conflicts native_conflicts native_CPU_s native/EMS
if [[ -s "$work/search-table" ]]; then cat "$work/search-table"; else echo 'No ladder rungs selected; file-instance checks only.'; fi
finish_run
