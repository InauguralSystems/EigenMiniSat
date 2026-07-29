#!/usr/bin/env bash
# Second pass: retry the fixed-expansion case that ran out of cap.
#
# 4x5 is the case that actually tests the registered prediction about the
# fixed-expansion axis, and a 90-minute cap was not enough (it reached 452,569
# resolutions without closing). A lower bound cannot test a ratio prediction,
# so it gets a much larger cap in the idle window after the first pass ends.
#
# Only the CAP changes. The registered predictions are untouched -- a timeout
# budget is an operational parameter, not a hypothesis, and the number 4x5
# produces is the same number whenever it is produced.
#
# Waits for the first pass to release the ladder lock (4GB box: one heavy job
# at a time), then runs. Safe to launch at any time.
set -uo pipefail

D="${TSEITIN_LADDER_OUT:-$HOME/eigenminisat-runs/tseitin-ladder}"
R="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="$D/.lock"
mkdir -p "$D"

while true; do
    if ( exec 9>"$LOCK"; flock -n 9 ); then
        break
    fi
    sleep 120
done

echo "$(date -Is) SECOND-PASS-START 4x5 extended cap" >>"$D/results.log"
TSEITIN_LADDER_SPEC="4 5 16200" "$R/benchmarks/run_tseitin_ladder.sh" >>"$D/second-pass.log" 2>&1
echo "$(date -Is) SECOND-PASS-END" >>"$D/results.log"
