#!/usr/bin/env bash
# Native MiniSat is the answer oracle. EMS-VM is the AOT output oracle.
# All heavy work is sequential; solver/emitter timeouts are named failures.
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
Any ladder selection also runs the mandatory 3x3/4x4 regime preflights.
Other omitted standard rungs print SKIPPED (budget), never PASS.

Environment (CLI options take precedence):
  RUNGS='3x3 4x4'            Space- or comma-separated dimensions, each >= 3
  INSTANCE_DIR=...           Replacement file directory (empty is an error)
  EIGS_DIR=...               Default /home/jon/src/wt/es-v043
  EIGENSCRIPT_BIN=...        VM; with AOT must be EIGS_DIR/src/eigenscript
  MINISAT_BIN=...            Default /usr/bin/minisat
  AOT=auto                  auto skips absent/unbuildable tools; on requires AOT
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
emitter_cmd=("$EIGS" "$ROOT/benchmarks/dump_tseitin_cnf.eigs")
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

# A ladder lane always preflights both regime anchors, even when the requested
# measurement omits one. File-only and empty selections do not acquire rungs.
lane_rungs=()
preflight_added=0
if ((${#rungs[@]})); then
    lane_rungs=(3x3 4x4)
    for rung in 3x3 4x4; do
        [[ ${seen[$rung]+yes} ]] || preflight_added=$((preflight_added+1))
    done
    for rung in "${rungs[@]}"; do
        [[ "$rung" == 3x3 || "$rung" == 4x4 ]] || lane_rungs+=("$rung")
    done
    selected=$((selected+preflight_added))
fi

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

build_aot() {
    local source_root=$1
    mkdir -p "$work/ouroboros" || return
    tar -C "$source_root" --exclude='build' --exclude='*.o' --exclude='*.a' \
        -cf "$work/toolchain.tar" eigs.json aot src || return
    tar -C "$work/ouroboros" -xf "$work/toolchain.tar" || return
    timeout --kill-after=5s "${BUILD_TIMEOUT}s" \
        env EIGS_DIR="$EIGS_DIR" EIGS="$EIGS" bash "$work/ouroboros/aot/$(basename "$AOT_BUILD")" \
        "$ROOT/minisat.eigs" "$work/minisat-aot" > "$work/build.out" 2> "$work/build.err" || return
    [[ -x "$work/minisat-aot" ]] || { echo 'Build produced no executable' >&2; return 1; }
}

aot_build_failed() {
    local rc=$1
    if [[ "$AOT" == auto ]]; then
        printf 'AOT: SKIPPED (build failed rc=%s; logs=%s/build.*; native/VM checks continue)\n' "$rc" "$work"
    else
        fail AOT build "rc=$rc; required AOT build failed; logs=$work/build.*"
    fi
}

prepare_aot() {
    # Reset even when called after a successful setup (selftest witnesses it).
    # Failed/absent AOT must never retain the enabled arm or its executable.
    aot_enabled=0
    aot_cmd=()
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
    local version source_root rc
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
    echo "AOT: BUILD (once, runtime=$version, cap=${BUILD_TIMEOUT}s)"
    if build_aot "$source_root" > "$work/build.setup.log" 2>&1; then
        :
    else
        rc=$?
        aot_build_failed "$rc"
        return
    fi
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

cnf_tokens() {
    awk 'NF && $1 != "c" {for (i=1;i<=NF;i++) print $i}' "$1"
}

check_rung_fixture() {
    local rung=$1 cnf=$2
    [[ "$rung" == 3x3 ]] || return 0
    cnf_tokens "$cnf" > "$work/3x3.tokens" || fail "$rung" rung-fixture 'cannot read emitted CNF'
    cnf_tokens "$ROOT/tests/fixtures/tseitin_torus_3x3_odd.cnf" > "$work/3x3.fixture.tokens" || fail "$rung" rung-fixture 'cannot read banked fixture'
    cmp -s "$work/3x3.tokens" "$work/3x3.fixture.tokens" || fail "$rung" rung-fixture 'emitted CNF differs from tests/fixtures/tseitin_torus_3x3_odd.cnf'
    echo 'IDENTITY 3x3: PASS (banked repository fixture, ordered DIMACS tokens)'
}

check_rung_identity() {
    local rung=$1 cnf=$2
    if ! awk -v rows="${rung%x*}" -v cols="${rung#*x}" -f "$ROOT/benchmarks/torus_identity.awk" "$cnf" > "$work/identity.out" 2> "$work/identity.err"; then
        fail "$rung" rung-identity "$(cat "$work/identity.err")"
    fi
    printf 'IDENTITY %s: PASS (header, every ordered literal and clause, odd charge)\n' "$rung"
    check_rung_fixture "$rung" "$cnf"
}

emit_rung() {
    local rung=$1
    run_zero "$rung" emitter "$work/$rung.cnf" "$work/$rung.emitter.err" "$SOLVE_TIMEOUT" \
        "${emitter_cmd[@]}" "${rung%x*}" "${rung#*x}"
    check_rung_identity "$rung" "$work/$rung.cnf"
}

normalize_output() {
    sed -E '/^c /s/ ms=[0-9]+([.][0-9]+)?([eE][-+]?[0-9]+)?$//' "$1" > "$2" || fail "$3" normalize 'output normalization failed'
}

check_regime() {
    local rung=$1 output=$2 normalized="$work/regime-$1.stdout"
    [[ "$rung" == 3x3 || "$rung" == 4x4 ]] || return 0
    # Controls also pass the read-only banks as input: never write beside them.
    normalize_output "$output" "$normalized" "$rung"
    if ! cmp -s "$normalized" "$ROOT/benchmarks/oracle/regime-c-$rung.stdout"; then
        fail "$rung" regime 'EMS-VM differs byte-for-byte from banked regime C (excluding ms)'
    fi
    printf 'PREFLIGHT %s: PASS (regime C, byte-exact EMS-VM output excluding ms)\n' "$rung"
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
    normalize_output "$vm" "$vm.normalized" "$name"
    normalize_output "$aot" "$aot.normalized" "$name"
    if ! cmp -s "$vm.normalized" "$aot.normalized"; then
        diff -u "$vm.normalized" "$aot.normalized" >&2 || true
        fail "$name" aot-diff 'DIVERGENCE EMS-VM reference != EMS-AOT (bytes excluding trailing ms)'
    fi
}

run_instance() {
    local name=$1 input=$2 rung=${3:-} measure=${4:-1} dir rc aot_status=SKIPPED ratio
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
    [[ -z "$rung" ]] || check_regime "$rung" "$dir/vm.out"
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
    if [[ -n "$rung" && "$measure" == 1 ]]; then
        ratio=$(awk -v n="$native_conflicts" -v e="$vm_conflicts" 'BEGIN {if (e==0) print "n/a (EMS=0)"; else printf "%.3fx", n/e}')
        printf '%-8s %14s %14s %14s %18s\n' "$rung" "$vm_conflicts" "$native_conflicts" "$native_cpu" "$ratio" >> "$work/search-table"
    fi
}

check_coverage() {
    ((passed == selected && native_runs == selected && vm_runs == selected)) || fail instances coverage "selected=$selected passed=$passed native=$native_runs VM=$vm_runs"
    ((!aot_enabled || aot_runs == selected)) || fail instances coverage "selected=$selected AOT=$aot_runs"
}

finish_run() {
    check_population
    check_coverage
    printf 'SUMMARY PASS selected=%s passed=%s native=%s VM=%s AOT=%s\n' "$selected" "$passed" "$native_runs" "$vm_runs" "$aot_runs"
}

expect_control() {
    local label=$1 expected_rc=$2 markers=$3 rc marker ok=1
    shift 3
    if ("$@") > "$work/control-$label.log" 2>&1; then rc=0; else rc=$?; fi
    [[ "$rc" == "$expected_rc" ]] || ok=0
    while IFS= read -r marker; do
        grep -qF "$marker" "$work/control-$label.log" || ok=0
    done <<< "$markers"
    controls=$((controls+1))
    if ((ok)); then
        printf 'CONTROL %s: PASS (expected rc=%s)\n' "$label" "$rc"
    else
        printf 'CONTROL %s: MISS (rc=%s, expected rc=%s and named evidence)\n' "$label" "$rc" "$expected_rc"
        cat "$work/control-$label.log"
        control_missed=$((control_missed+1))
    fi
}

coverage_control() {
    # F3: simulate losing each completion record in turn, independently of
    # process errors (which terminate before finish_run). Exercise the actual
    # aggregate assertion, so deleting it is observed as a missed detection.
    selected=1; passed=1; native_runs=1; vm_runs=1; aot_runs=1; aot_enabled=1
    [[ "$1" == complete ]] || printf -v "$1" '%s' 0
    finish_run
}

build_failure_control() {
    AOT=$1
    AOT_BUILD="$work/failed-toolchain/aot/build.sh"
    # Inherit neither a cached binary nor a stale enabled arm. prepare_aot is
    # responsible for clearing the latter; the control deliberately seeds it.
    unset AOT_BINARY
    aot_enabled=1; aot_cmd=(false)
    # expect_control owns a subshell. Keep work in that subshell scope: a
    # function-local work would disappear before EXIT and delete the parent
    # harness directory through the restored outer value.
    work=$(mktemp -d /tmp/ems-aot-failure-control.XXXXXX)
    trap 'rm -rf -- "$work"' EXIT
    selected=1; passed=0; native_runs=0; vm_runs=0; aot_runs=0
    prepare_aot
    run_instance build-failure-control "$ROOT/tests/fixtures/unit_unsat.cnf"
    finish_run
}

selftest_controls() {
    local rung counter expected_controls=13
    expect_control identity-3x3 0 'IDENTITY 3x3: PASS (banked repository fixture' emit_rung 3x3
    expect_control identity-4x4 0 'IDENTITY 4x4: PASS' emit_rung 4x4
    # Same dimensions, wrong literal: a header-only check must fail this test.
    awk 'NF && $1!="c" && $1!="p" && !changed {$1=-$1; changed=1} {print}' \
        "$work/3x3.cnf" > "$work/wrong-clause.cnf"
    expect_control identity-clauses 1 'FAIL 3x3 [rung-identity]:' check_rung_identity 3x3 "$work/wrong-clause.cnf"
    # Directly exercise the independent fixture comparison; the structural
    # identity guard must not absorb this plant and conceal an untested check.
    expect_control fixture-reference 1 'FAIL 3x3 [rung-fixture]:' check_rung_fixture 3x3 "$work/wrong-clause.cnf"
    for rung in 3x3 4x4; do
        expect_control "regime-$rung" 0 "PREFLIGHT $rung: PASS" check_regime "$rung" "$ROOT/benchmarks/oracle/regime-c-$rung.stdout"
        sed -E 's/ conflicts=[0-9]+/ conflicts=0/' "$ROOT/benchmarks/oracle/regime-c-$rung.stdout" > "$work/wrong-regime-$rung.stdout"
        expect_control "regime-$rung-drift" 1 "FAIL $rung [regime]:" check_regime "$rung" "$work/wrong-regime-$rung.stdout"
    done
    expect_control coverage-complete 0 'SUMMARY PASS selected=1 passed=1 native=1 VM=1 AOT=1' coverage_control complete
    for counter in passed native_runs vm_runs aot_runs; do
        expect_control "coverage-$counter" 1 'FAIL instances [coverage]:' coverage_control "$counter"
    done
    if [[ -x "$EIGS_DIR/src/eigenscript" && "$(realpath "$EIGS_DIR/src/eigenscript")" == "$EIGS" ]] &&
        [[ "$(git -C "$EIGS_DIR" describe --tags --exact-match 2>/dev/null || true)" == v0.43.0 ]]; then
        expected_controls=15
        mkdir -p "$work/failed-toolchain/aot" "$work/failed-toolchain/src"
        printf '{}\n' > "$work/failed-toolchain/eigs.json"
        printf '#!/usr/bin/env bash\nexit 7\n' > "$work/failed-toolchain/aot/build.sh"
        expect_control auto-degrades 0 $'AOT: SKIPPED (build failed rc=7;\nSUMMARY PASS selected=1 passed=1 native=1 VM=1 AOT=0' build_failure_control auto
        expect_control required-build-fails 1 'FAIL AOT [build]: rc=7;' build_failure_control on
    else
        echo 'CONTROL build-failure modes: SKIPPED (matching pinned runtime absent)'
    fi
    ((controls == expected_controls)) || control_missed=$((control_missed+1))
    printf 'CONTROLS checked=%s expected=%s missed=%s\n' "$controls" "$expected_controls" "$control_missed"
}

selftest_run() {
    local name reason rc caught=0 missed=0 expected=6 controls=0 control_missed=0
    # Tiny real SAT/UNSAT controls prove the gates do not simply always fail.
    run_instance control-unsat tests/fixtures/unit_unsat.cnf
    run_instance control-sat tests/fixtures/simple_sat.cnf
    selftest_controls
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
    cat > "$work/resized-emitter.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
args=("$@")
args[${#args[@]}-1]=3
exec "$ORACLE_REAL_VM" "${args[@]}"
EOF
    export ORACLE_REAL_AOT="${aot_cmd[0]:-}"
    ((aot_enabled)) && expected=7
    for name in corrupted-cnf wrong-ems-verdict perturbed-aot zero-instances solver-timeout empty-output resized-emitter; do
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
            resized-emitter) reason=rung-identity ;;
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
                resized-emitter)
                    emitter_cmd=(bash "$work/resized-emitter.sh" "$ROOT/benchmarks/dump_tseitin_cnf.eigs")
                    emit_rung 4x4; exit 0 ;;
            esac
            run_instance "$name" tests/fixtures/unit_unsat.cnf
        ) > "$work/selftest-$name.log" 2>&1; then rc=0; else rc=$?; fi
        local failure_name=$name
        [[ "$name" != zero-instances ]] || failure_name=instances
        [[ "$name" != resized-emitter ]] || failure_name=4x4
        if [[ "$rc" == 1 ]] && grep -qF "FAIL $failure_name [$reason]:" "$work/selftest-$name.log"; then
            printf 'SELFTEST %s: RED (rc=%s, %s)\n' "$name" "$rc" "$reason"
            caught=$((caught+1))
        else
            printf 'SELFTEST %s: MISS (rc=%s, expected %s)\n' "$name" "$rc" "$reason"
            cat "$work/selftest-$name.log"
            missed=$((missed+1))
        fi
    done
    if ((missed != 0 || caught != expected || control_missed != 0)); then
        printf 'SELFTEST BROKEN caught=%s expected=%s missed=%s control_missed=%s (exit 2)\n' "$caught" "$expected" "$missed" "$control_missed"
        exit 2
    fi
    printf 'SELFTEST ALL RED caught=%s expected=%s (intentional exit 1)\n' "$caught" "$expected"
    exit 1
}

printf 'Oracle: native MiniSat=%s; EMS-VM=%s; policy=CDCL current defaults (regime C)\n' "$MINISAT" "$EIGS"
prepare_aot
((selftest)) && selftest_run
printf 'Selection: files=%s requested-rungs=%s preflight-added=%s per-solver-cap=%ss\n' "${#files[@]}" "${#rungs[@]}" "$preflight_added" "$SOLVE_TIMEOUT"
for rung in 3x3 4x4 4x5 4x6 5x5 5x6 6x6; do
    if ((${#lane_rungs[@]})) && [[ ! ${seen[$rung]+yes} && ( "$rung" == 3x3 || "$rung" == 4x4 ) ]]; then
        printf '%s: PREFLIGHT (required regime anchor; not selected for measurement)\n' "$rung"
        continue
    fi
    [[ ${seen[$rung]+yes} ]] || printf '%s: SKIPPED (budget; not selected in RUNGS)\n' "$rung"
done
for rung in "${lane_rungs[@]}"; do
    emit_rung "$rung"
    measure=0
    [[ ! ${seen[$rung]+yes} ]] || measure=1
    run_instance "tseitin-$rung-odd" "$work/$rung.cnf" "$rung" "$measure"
done
for file in "${files[@]}"; do run_instance "$file" "$file"; done
echo 'SEARCH GAP (measurement only; native conflicts / EMS conflicts, not a speed ratio)'
printf '%-8s %14s %14s %14s %18s\n' rung EMS_conflicts native_conflicts native_CPU_s native/EMS
if [[ -s "$work/search-table" ]]; then cat "$work/search-table"; else echo 'No ladder rungs selected; file-instance checks only.'; fi
finish_run
