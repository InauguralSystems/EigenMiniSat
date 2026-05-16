#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    printf 'usage: %s <trend-log>\n' "$0" >&2
    exit 2
fi

LOG="$1"

if [[ ! -r "$LOG" ]]; then
    printf 'missing or unreadable trend log: %s\n' "$LOG" >&2
    exit 2
fi

printf '# EigenMiniSat trend summary\n'
printf 'trend_summary_log=%s\n' "$LOG"

awk '
function field_value(key,    i, pair) {
    for (i = 4; i <= NF; i += 1) {
        split($i, pair, "=")
        if (pair[1] == key) {
            return pair[2] + 0
        }
    }
    return 0
}

/^## evidence summary/ {
    stop = 1
    next
}

stop != 0 {
    next
}

/^(profile|size|git_commit|git_branch)=/ {
    print
    next
}

/^copy delta / {
    case_name = $3
    sub(/:$/, "", case_name)
    delta_compact_lits = field_value("delta_compact_lits")
    delta_watch_rebuilds = field_value("delta_watch_rebuilds")
    delta_pending_deleted = field_value("delta_pending_deleted")
    delta_watch_detach_scans = field_value("delta_watch_detach_scans")
    delta_compact_replays = field_value("delta_compact_replays")

    printf "copy_delta case=%s delta_compact_lits=%d delta_watch_rebuilds=%d delta_pending_deleted=%d delta_watch_detach_scans=%d delta_compact_replays=%d\n", case_name, delta_compact_lits, delta_watch_rebuilds, delta_pending_deleted, delta_watch_detach_scans, delta_compact_replays

    cases += 1
    if (delta_compact_lits < 0) {
        compact_lit_savings += 0 - delta_compact_lits
    }
    if (delta_watch_rebuilds < 0) {
        watch_rebuild_savings += 0 - delta_watch_rebuilds
    }
    if (delta_compact_replays < 0) {
        replay_savings += 0 - delta_compact_replays
    }
    if (delta_pending_deleted > 0) {
        pending_deleted_debt += delta_pending_deleted
    }
    if (delta_watch_detach_scans > 0) {
        watch_detach_scan_debt += delta_watch_detach_scans
    }
}

END {
    printf "copy_delta_totals cases=%d compact_lit_savings=%d watch_rebuild_savings=%d replay_savings=%d pending_deleted_debt=%d watch_detach_scan_debt=%d\n", cases, compact_lit_savings, watch_rebuild_savings, replay_savings, pending_deleted_debt, watch_detach_scan_debt
    if (compact_lit_savings > 0 || watch_rebuild_savings > 0 || replay_savings > 0) {
        physical_compaction_pressure = 1
    } else {
        physical_compaction_pressure = 0
    }
    if (pending_deleted_debt > 0 || watch_detach_scan_debt > 0) {
        lazy_debt_pressure = 1
    } else {
        lazy_debt_pressure = 0
    }
    printf "decision_flags physical_compaction_pressure=%d lazy_debt_pressure=%d\n", physical_compaction_pressure, lazy_debt_pressure
}
' "$LOG"
