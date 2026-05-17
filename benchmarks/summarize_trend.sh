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

function emit_candidate(area, scope, evidence, next_action) {
    printf "decision_candidate area=%s scope=%s evidence=%s next=%s\n", area, scope, evidence, next_action
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

/^metadata compaction / {
    metadata_compact_clause_lits += field_value("compact_clause_lits")
    metadata_watch_rebuilds += field_value("watch_rebuilds")
    metadata_watch_detaches += field_value("watch_detaches")
    metadata_compact_replays += field_value("compact_replays")
    metadata_rows += 1
}

/^metadata churn summary / {
    metadata_compact_clause_lits += field_value("compact_clause_lits")
    metadata_watch_rebuilds += field_value("watch_rebuilds")
    metadata_watch_detaches += field_value("watch_detaches")
    metadata_compact_replays += field_value("compact_replays")
    metadata_locked_kept += field_value("locked_kept")
    metadata_rows += 1
}

/^build concat / {
    build_concat_ms += field_value("ms")
    build_rows += 1
}

/^build text_builder / {
    build_text_builder_ms += field_value("ms")
}

/^storage arena / {
    storage_list_scan_ms += field_value("list_scan_ms")
    storage_flat_scan_ms += field_value("flat_scan_ms")
    storage_watch_seed_ms += field_value("watch_seed_ms")
    storage_arena_build_ms += field_value("build_ms")
    storage_reconstruct_ms += field_value("reconstruct_ms")
    storage_rows += 1
}

/^storage adapter / {
    storage_adapter_scan_ms += field_value("adapter_scan_ms")
    storage_adapter_watch_seed_ms += field_value("adapter_watch_seed_ms")
}

/^storage adapter inline / {
    storage_inline_scan_ms += field_value("inline_scan_ms")
    storage_inline_watch_seed_ms += field_value("inline_watch_seed_ms")
    storage_inline_rows += 1
}

/^storage compact / {
    storage_list_compact_ms += field_value("list_compact_ms")
    storage_flat_compact_ms += field_value("flat_compact_ms")
    storage_remap_ms += field_value("remap_ms")
}

/^storage adapter compact / {
    storage_adapter_compact_ms += field_value("adapter_compact_ms")
}

/^parse split / {
    parse_split_ms += field_value("ms")
    parse_rows += 1
}

/^parse scan / {
    parse_scan_ms += field_value("ms")
}

/^parse tokens / {
    parse_tokens_ms += field_value("ms")
}

/^parse ints / {
    parse_ints_ms += field_value("ms")
}

/^diagnostic split / {
    diagnostic_split_ms += field_value("ms")
    diagnostic_errors += field_value("errors")
    diagnostic_rows += 1
}

/^diagnostic scan / {
    diagnostic_scan_ms += field_value("ms")
}

/^diagnostic tokens / {
    diagnostic_tokens_ms += field_value("ms")
}

/^corpus parse split / {
    corpus_split_ms += field_value("ms")
    corpus_rows += 1
}

/^corpus parse scan / {
    corpus_scan_ms += field_value("ms")
}

/^corpus parse tokens / {
    corpus_tokens_ms += field_value("ms")
}

/^corpus parse ints / {
    corpus_ints_ms += field_value("ms")
}

END {
    if (storage_inline_rows == 0) {
        storage_inline_scan_ms = storage_adapter_scan_ms
        storage_inline_watch_seed_ms = storage_adapter_watch_seed_ms
    }

    adapter_scan_overhead_ms = storage_adapter_scan_ms - storage_flat_scan_ms
    inline_scan_overhead_ms = storage_inline_scan_ms - storage_flat_scan_ms
    helper_scan_overhead_ms = storage_adapter_scan_ms - storage_inline_scan_ms
    adapter_watch_overhead_ms = storage_adapter_watch_seed_ms - storage_watch_seed_ms
    inline_watch_overhead_ms = storage_inline_watch_seed_ms - storage_watch_seed_ms
    helper_watch_overhead_ms = storage_adapter_watch_seed_ms - storage_inline_watch_seed_ms
    adapter_compact_overhead_ms = storage_adapter_compact_ms - storage_flat_compact_ms
    flat_compact_overhead_ms = storage_flat_compact_ms - storage_list_compact_ms

    printf "copy_delta_totals cases=%d compact_lit_savings=%d watch_rebuild_savings=%d replay_savings=%d pending_deleted_debt=%d watch_detach_scan_debt=%d\n", cases, compact_lit_savings, watch_rebuild_savings, replay_savings, pending_deleted_debt, watch_detach_scan_debt
    printf "metadata_totals rows=%d compact_clause_lits=%d watch_rebuilds=%d watch_detaches=%d compact_replays=%d locked_kept=%d\n", metadata_rows, metadata_compact_clause_lits, metadata_watch_rebuilds, metadata_watch_detaches, metadata_compact_replays, metadata_locked_kept
    printf "text_build_totals generated_cases=%d concat_ms=%.3f text_builder_ms=%.3f\n", build_rows, build_concat_ms, build_text_builder_ms
    printf "storage_totals rows=%d list_scan_ms=%.3f flat_scan_ms=%.3f adapter_scan_ms=%.3f arena_build_ms=%.3f reconstruct_ms=%.3f list_compact_ms=%.3f flat_compact_ms=%.3f adapter_compact_ms=%.3f remap_ms=%.3f\n", storage_rows, storage_list_scan_ms, storage_flat_scan_ms, storage_adapter_scan_ms, storage_arena_build_ms, storage_reconstruct_ms, storage_list_compact_ms, storage_flat_compact_ms, storage_adapter_compact_ms, storage_remap_ms
    printf "storage_overhead_totals rows=%d inline_rows=%d adapter_scan_overhead_ms=%.3f inline_scan_overhead_ms=%.3f helper_scan_overhead_ms=%.3f adapter_watch_overhead_ms=%.3f inline_watch_overhead_ms=%.3f helper_watch_overhead_ms=%.3f adapter_compact_overhead_ms=%.3f flat_compact_overhead_ms=%.3f\n", storage_rows, storage_inline_rows, adapter_scan_overhead_ms, inline_scan_overhead_ms, helper_scan_overhead_ms, adapter_watch_overhead_ms, inline_watch_overhead_ms, helper_watch_overhead_ms, adapter_compact_overhead_ms, flat_compact_overhead_ms
    printf "parse_totals generated_cases=%d split_ms=%.3f scan_ms=%.3f tokens_ms=%.3f ints_ms=%.3f diagnostic_cases=%d diagnostic_errors=%d diagnostic_split_ms=%.3f diagnostic_scan_ms=%.3f diagnostic_tokens_ms=%.3f corpus_cases=%d corpus_split_ms=%.3f corpus_scan_ms=%.3f corpus_tokens_ms=%.3f corpus_ints_ms=%.3f\n", parse_rows, parse_split_ms, parse_scan_ms, parse_tokens_ms, parse_ints_ms, diagnostic_rows, diagnostic_errors, diagnostic_split_ms, diagnostic_scan_ms, diagnostic_tokens_ms, corpus_rows, corpus_split_ms, corpus_scan_ms, corpus_tokens_ms, corpus_ints_ms
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
    if (diagnostic_scan_ms > diagnostic_split_ms) {
        diagnostic_tokenizer_pressure = 1
    } else {
        diagnostic_tokenizer_pressure = 0
    }
    if (parse_tokens_ms > 0 || diagnostic_tokens_ms > 0 || corpus_tokens_ms > 0) {
        token_span_path_active = 1
    } else {
        token_span_path_active = 0
    }
    if (build_text_builder_ms > 0) {
        text_builder_path_active = 1
    } else {
        text_builder_path_active = 0
    }
    if ((parse_ints_ms > 0 && parse_ints_ms < parse_split_ms) || (corpus_ints_ms > 0 && corpus_ints_ms < corpus_split_ms)) {
        validated_scan_ints_win = 1
    } else {
        validated_scan_ints_win = 0
    }
    if (adapter_scan_overhead_ms > 0 || adapter_watch_overhead_ms > 0 || adapter_compact_overhead_ms > 0) {
        storage_adapter_pressure = 1
    } else {
        storage_adapter_pressure = 0
    }
    if (metadata_compact_clause_lits > 0 || storage_flat_compact_ms > storage_list_compact_ms) {
        compact_vector_pressure = 1
    } else {
        compact_vector_pressure = 0
    }
    printf "decision_flags physical_compaction_pressure=%d lazy_debt_pressure=%d diagnostic_tokenizer_pressure=%d token_span_path_active=%d text_builder_path_active=%d validated_scan_ints_win=%d storage_adapter_pressure=%d compact_vector_pressure=%d\n", physical_compaction_pressure, lazy_debt_pressure, diagnostic_tokenizer_pressure, token_span_path_active, text_builder_path_active, validated_scan_ints_win, storage_adapter_pressure, compact_vector_pressure

    if (physical_compaction_pressure != 0) {
        emit_candidate("clause_physical_compaction", "eigenminisat_local", "active", "compare_deferred_lazy_before_root_request")
    }
    if (lazy_debt_pressure != 0) {
        emit_candidate("clause_lazy_deletion_debt", "eigenminisat_local", "active", "measure_targeted_detach_vs_physical_compaction")
    }
    if (diagnostic_tokenizer_pressure != 0) {
        emit_candidate("diagnostic_token_spans", "root_or_stdlib", "active", "prototype_span_tokenizer_if_larger_corpus_repeats")
    }
    if (token_span_path_active != 0) {
        emit_candidate("scan_token_spans", "root_runtime", "active", "compare_token_path_against_split_scan_and_ints")
    }
    if (text_builder_path_active != 0) {
        emit_candidate("text_builder", "stdlib", "active", "compare_stdlib_builder_against_concat_generation")
    }
    if (validated_scan_ints_win != 0) {
        emit_candidate("validated_integer_scan", "root_runtime", "active", "keep_fast_path_and_measure_clause_assembly")
    }
    if (storage_adapter_pressure != 0) {
        emit_candidate("clause_store_adapter", "eigenminisat_local", "active", "compare_inline_helper_overhead_before_root_arena_request")
    }
    if (compact_vector_pressure != 0) {
        emit_candidate("compact_integer_vectors", "root_or_stdlib", "active", "prototype_reusable_int_vector_before_solver_wrappers")
    }
}
' "$LOG"
