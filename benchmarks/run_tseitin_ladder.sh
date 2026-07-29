#!/usr/bin/env bash
# ============================================================
# Tseitin torus ladder -- long-run driver, resumable across reboots
# ============================================================
# This box reboots daily around 05:57 (mac80211 CSA kernel bug) and that wipes
# /tmp and kills whatever is running. So:
#
#   * results land under $OUTDIR (default ~/eigenminisat-runs), NEVER /tmp
#   * every case is a separate `timeout`-capped process, appending as it goes
#   * a case already present in banked.log is skipped, so re-running resumes
#   * stdbuf -oL keeps progress lines flushed, so a killed case still leaves a
#     conflicts-vs-time trajectory rather than nothing
#   * a lock file keeps a @reboot resume from racing a manual run (4GB box:
#     one heavy job at a time)
#
# Re-running this script is always safe and always the right recovery action.
#
# Usage: benchmarks/run_tseitin_ladder.sh [outdir]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="${1:-${TSEITIN_LADDER_OUT:-$HOME/eigenminisat-runs/tseitin-ladder}}"
EIGS="${EIGENSCRIPT_BIN:-$ROOT/../EigenScript/src/eigenscript}"

mkdir -p "$OUTDIR"
RESULTS="$OUTDIR/results.log"
BANKED="$OUTDIR/banked.log"
LOCK="$OUTDIR/.lock"

# rows cols timeout_seconds
# Ordered cheap-and-certain first so the night banks something even if it ends
# early. 5x5 is the scientifically valuable one -- it is the third point on the
# expansion axis (min(rows,cols) = 3, 4, 5), which is where the exponential
# lives -- so it gets the biggest cap and runs while there is still night left.
# 4xN cases grow the formula at FIXED expansion and are the cheap axis.
# TSEITIN_LADDER_SPEC overrides it (used to smoke-test the driver on cheap cases
# without waiting on the real ladder).
LADDER="${TSEITIN_LADDER_SPEC:-
4 4 1800
4 5 5400
5 5 21600
4 6 10800
4 7 10800
}"

exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date -Is) another ladder run holds $LOCK; exiting" | tee -a "$RESULTS"
    exit 0
fi

if [ ! -x "$EIGS" ]; then
    echo "$(date -Is) FATAL eigenscript not found at $EIGS" | tee -a "$RESULTS"
    exit 1
fi

echo "$(date -Is) LADDER-START host=$(hostname) outdir=$OUTDIR eigs=$EIGS" >>"$RESULTS"

while read -r rows cols cap; do
    [ -z "${rows:-}" ] && continue
    name="tseitin-torus-${rows}x${cols}-odd"

    if [ -f "$BANKED" ] && grep -q "DONE case=$name " "$BANKED"; then
        echo "$(date -Is) SKIP $name already banked" >>"$RESULTS"
        continue
    fi

    echo "$(date -Is) CASE-START $name cap_s=$cap" >>"$RESULTS"
    start=$(date +%s)

    # Progress every 300s. Each attempt writes a fresh file so a retry after a
    # reboot does not re-append earlier attempts into the shared log; the
    # per-case history file accumulates attempts on purpose (the trajectory of
    # a case that keeps getting killed is itself the data).
    casefile="$OUTDIR/$name.log"
    attempt="$OUTDIR/.$name.attempt"
    : >"$attempt"
    timeout "$cap" stdbuf -oL "$EIGS" "$ROOT/benchmarks/tseitin_ladder.eigs" "$rows" "$cols" 300 \
        >>"$attempt" 2>&1
    rc=$?
    end=$(date +%s)
    elapsed=$((end - start))

    cat "$attempt" >>"$casefile"
    cat "$attempt" >>"$RESULTS"

    if [ "$rc" -eq 0 ]; then
        # Bank only the DONE line -- that is the result of record.
        grep "^DONE case=$name " "$attempt" >>"$BANKED"
        echo "$(date -Is) CASE-DONE $name wall_s=$elapsed" >>"$RESULTS"
    elif [ "$rc" -eq 124 ]; then
        last="$(grep "^PROGRESS " "$attempt" | tail -1)"
        echo "TIMEOUT case=$name cap_s=$cap wall_s=$elapsed last_progress=${last:-none}" >>"$BANKED"
        echo "$(date -Is) CASE-TIMEOUT $name cap_s=$cap" >>"$RESULTS"
    else
        last="$(grep "^PROGRESS " "$attempt" | tail -1)"
        echo "KILLED case=$name rc=$rc wall_s=$elapsed last_progress=${last:-none}" >>"$BANKED"
        echo "$(date -Is) CASE-KILLED $name rc=$rc (reboot/OOM/interrupt -- re-run to resume)" >>"$RESULTS"
    fi
done <<<"$LADDER"

echo "$(date -Is) LADDER-END" >>"$RESULTS"
echo "banked results:"
cat "$BANKED" 2>/dev/null
