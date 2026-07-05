#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
EIGS="${EIGENSCRIPT_BIN:-../EigenScript/src/eigenscript}"
PROFILE="${1:-quick}"
SIZE="${2:-}"

if [[ "$PROFILE" != "quick" && "$PROFILE" != "evidence" && "$PROFILE" != "full" ]]; then
    printf 'usage: %s [quick|evidence|full] [size] [output-log]\n' "$0" >&2
    exit 2
fi

if [[ "$SIZE" == "" ]]; then
    SIZE=1
    if [[ "$PROFILE" == "evidence" ]]; then
        SIZE=2
    fi
fi

case "$SIZE" in
    ''|*[!0-9]*)
        printf 'size must be a positive integer\n' >&2
        exit 2
        ;;
esac

if [[ "$SIZE" -lt 1 ]]; then
    printf 'size must be a positive integer\n' >&2
    exit 2
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${3:-$ROOT/benchmarks/runs/${STAMP}-${PROFILE}-size${SIZE}.log}"

mkdir -p "$(dirname "$OUT")"

cd "$ROOT"

{
    printf '# EigenMiniSat trend run\n'
    printf 'timestamp_utc=%s\n' "$STAMP"
    printf 'profile=%s\n' "$PROFILE"
    printf 'size=%s\n' "$SIZE"
    printf 'eigenscript_bin=%s\n' "$EIGS"
    printf 'git_commit=%s\n' "$(git rev-parse --short HEAD 2>/dev/null || printf unknown)"
    printf 'git_branch=%s\n' "$(git branch --show-current 2>/dev/null || printf unknown)"
    printf '\n'
} | tee "$OUT"

run_cmd() {
    printf '\n## command:' | tee -a "$OUT"
    printf ' %q' "$@" | tee -a "$OUT"
    printf '\n' | tee -a "$OUT"
    "$@" 2>&1 | tee -a "$OUT"
}

run_cmd "$EIGS" tests/test_solver.eigs

if [[ "$PROFILE" == "full" ]]; then
    run_cmd "$EIGS" minisat.eigs --bench --size "$SIZE"
    run_cmd "$EIGS" minisat.eigs --restart-bench --size "$SIZE"
    run_cmd "$EIGS" minisat.eigs --phase-bench --size "$SIZE"
    run_cmd "$EIGS" minisat.eigs --heuristic-bench --size "$SIZE"
    run_cmd "$EIGS" minisat.eigs --random-bench --size "$SIZE"
fi

run_cmd "$EIGS" minisat.eigs --metadata-bench --size "$SIZE"
run_cmd "$EIGS" minisat.eigs --copy-bench --size "$SIZE"
run_cmd "$EIGS" minisat.eigs --storage-bench --size "$SIZE"

if [[ "$PROFILE" == "evidence" || "$PROFILE" == "full" ]]; then
    run_cmd "$EIGS" minisat.eigs --parse-bench --size "$SIZE"
fi

if [[ "$PROFILE" == "evidence" || "$PROFILE" == "full" ]]; then
    run_cmd "$EIGS" minisat.eigs --diagnostic-bench --size "$SIZE"
fi

run_cmd "$EIGS" minisat.eigs --scan-parse-bench --size "$SIZE"

if [[ "$PROFILE" == "full" ]]; then
    run_cmd "$EIGS" minisat.eigs --file-bench --size "$SIZE"
fi

run_cmd "$EIGS" minisat.eigs --corpus-bench

if [[ "$PROFILE" == "evidence" ]]; then
    SUMMARY="$(benchmarks/summarize_trend.sh "$OUT")"
    printf '\n## evidence summary\n%s\n' "$SUMMARY" | tee -a "$OUT"
fi

printf '\ntrend_log=%s\n' "$OUT" | tee -a "$OUT"
