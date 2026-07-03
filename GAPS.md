# EigenMiniSat Gap Log

Every entry here should be tied to a concrete solver or benchmark failure.
Root EigenScript issues should be fixed upstream instead of worked around here.

## Open Watchlist

- **Deferred-vs-lazy compaction: decided for deferred (2026-07-03).** Evidence
  runs at sizes 2 and 3 on v0.23.0 show lazy no-physical-compaction slower in
  all six policy/case pairs despite avoiding every compaction copy: +1.3–3.2%
  at size 2, 2.4×–5.3× at size 3 (pigeonhole-7-6-larger deferred 18.6s/30.9s
  vs lazy 45.0s/163.9s). Pending-deleted debt (1,990 clauses at size 3) makes
  propagation pay skip costs on every encounter, and watch-detach scan debt
  was zero under both policies. Compaction copies (~6.6K literals) are also
  small next to conflict-analysis traffic (~97K literals), so no EigenScript
  root arena/reference request comes from this pressure. The lazy policy stays
  as a comparison knob.
- **Hot helper-call overhead: FIXED upstream (EigenScript #366 → PR #367,
  2026-07-03).** The confirmed cost (n=5 size 3: median 1.417ms helper-call
  scan overhead beside 1.981ms data-shape; micro-repro ~185ns/call, +44%)
  drove an upstream frameless leaf-accessor call fast path. Re-measured
  against the merged fix: helper-call scan overhead `1.417ms -> 0.536ms`
  (-62%); per-call ~198ns -> ~40ns on the micro-repro; helper-mediated watch
  seeding now beats its inline row. The fix is on EigenScript main
  (unreleased) — the v0.23.0 CI pin sees it at the next release; re-record
  pinned numbers then. Measurement caveat stands: size-2 deltas sit inside
  the ~±1ms noise floor, so compare only at size 3+ with n=5.
- Learnt-clause reduction now uses lazy watch cleanup instead of eager
  per-clause detach. Deleted clauses are skipped during propagation
  (`deleted_watch_skips`) and cleaned up during compaction watch rebuilds.
  At pigeonhole-8-7 (56 vars, 372 clauses) this eliminated 33K detach
  scans. The remaining propagation-time skip cost is O(1) per encounter.
- Compaction thresholds raised from 25% waste / 32 min to 50% waste / 64
  min, matching MiniSat's less-frequent-but-larger compaction pattern.
  At pigeonhole-8-7 this reduced compaction runs from 46 to 16 and
  compaction literal copies from 93K to 33K. The remaining pressure is
  the full clause-store copy during each compaction — an EigenScript
  root arena/reference primitive would eliminate this.
- `list_truncate` is now a merged root builtin from EigenScript PR #124.
  Trail backjump, trail_lim truncation, and heap pop now use in-place
  truncation instead of `copy_prefix` list rebuilds. The `copy_prefix`
  helper remains for non-destructive copies.
- `sort_by` is now a merged root builtin from EigenScript PR #124.
  Learnt-clause reduction now collects candidates in one pass and sorts
  by activity via `sort_by`, replacing the O(n^2) loop-of-scans.
- `clause_locked` now uses O(1) first-watched-literal reason check
  instead of linear reason vector scan. This is a solver-local fix.
- The redundant `all_clauses_satisfied` check on the original clause list
  in the CDCL main loop has been removed. The `choose_var_cdcl` return
  of 0 already implies SAT when no conflict was found.
- `bump_clause_activity` now uses a generation-counted `bump_seen`
  int_vector for O(n) dedup instead of O(n^2) `clause_has_lit` scans.
- Hot function-call overhead in propagation loops — now quantified and
  tracked upstream as EigenScript #366 (see the confirmed entry above).
- Stress benchmarks should not hide root/runtime pressure with local bypasses.
  Inline or alternate forms can exist as comparison surfaces, but the main
  stress path should continue exposing the language gap until EigenScript root
  or a deliberate library abstraction addresses it.
- `docs/EIGENSCRIPT_FEEDBACK.md` now classifies current pressure into
  EigenScript root/runtime candidates, standard-library candidates, and
  EigenMiniSat-local work. Local-only binding is now a merged root-language fix
  from EigenScript PR #117 and is exercised by EigenMiniSat CDCL sentinel
  tests. Diagnostic token spans are now a merged root-runtime path from
  EigenScript PR #118, with integer-aware token spans from PR #122, and are
  exercised by a DIMACS token-span parser. String builders are now a merged
  root-backed path from EigenScript PR #119 and PR #123 and are exercised by
  generated DIMACS text construction.
  Priority queues are a standard-library candidate, compact integer vectors are
  root-vs-stdlib pressure, and clause arenas remain an EigenMiniSat-local
  prototype first.
- DIMACS parser throughput is now measured with generated text fixtures. The
  current path builds generated fixtures through EigenScript's root-backed
  text-builder API, keeps repeated concatenation as benchmark comparison, and
  tokenizes each line through split/trim/num conversion, so larger fixtures
  should tell us whether the native builder is enough before asking for deeper
  buffered text or streaming-tokenizer support.
- File-backed DIMACS fixtures now add `mktemp`, `write_text`, `read_text`
  through `parse_dimacs_file`, and `rm` pressure. This separates parser cost
  from file I/O cost and may expose whether EigenScript needs streaming file
  parsing or buffered write helpers for larger CNF corpora.
- The manifest-driven DIMACS corpus adds multiline clauses, multiple clauses on
  one physical line, comment-heavy files, graph-coloring, pigeonhole, wide
  clause, and parity/XOR instances. Parser diagnostics now report
  header/count/token problems directly, and benchmark parse lines expose
  `ok`/`errors` counts. The corpus now includes a small vendored structural set
  with provenance notes for larger self-contained graph-coloring, pigeonhole,
  and parity pressure. If larger corpora amplify the extra validation cost,
  EigenScript may need cheaper character classification or a streaming
  tokenizer.
- The corpus manifest is deliberately plain text, so EigenScript parses case
  metadata itself instead of relying on a host-side runner. This exposes
  repeated split/trim/numeric conversion and validates whether simple
  structured-data ingestion belongs in the standard library.
- The benchmark trend runner captures repeatable pressure snapshots without
  committing machine-local logs. This should make regressions easier to compare
  while keeping the constrained dev machine's output explicit and local. The
  `evidence` profile now defaults to bounded larger-case pressure and includes
  generated fixture parse/text-build rows plus malformed diagnostics without
  running every benchmark mode. Its summary collapses copy, metadata, storage,
  parser, diagnostic, corpus, and text-build output into decision flags and
  active `decision_candidate` rows for the
  root-vs-library-vs-local ledger.
- A character-scanning DIMACS parser now matches the split/trim parser's
  diagnostics and clauses, but repeated `substr` and token string concatenation
  are often slower than split/trim on these fixtures. EigenScript now exposes
  the root `scan_ints` and `scan_int_tokens` primitives, and EigenMiniSat
  benchmarks split/trim, character-scan, integer-token-span, and integer-scan
  paths on both generated fixtures and the manifest corpus. The remaining
  pressure is clause assembly from scanned integers and whether a future
  tokenizer should expose richer recoverable errors beyond token spans and
  integer metadata.
- The diagnostic benchmark now feeds malformed DIMACS cases through the
  split/trim, character-scanning, and `scan_int_tokens` parsers, checking error
  counts and diagnostic text sizes. This isolates malformed-token/header/count
  overhead and keeps pressure on whether EigenScript integer-aware token spans
  are enough for diagnostics instead of forcing parser-local string assembly.
- CRLF (`\r\n`) line endings exposed a parser-path divergence. The split/trim
  `_tokens` helper only normalized `\t`, so a trailing `\r` stuck to the last
  token of every line and a valid Windows-saved DIMACS file was rejected with
  spurious "non-integer" diagnostics — and since the CLI parses through
  `parse_dimacs_file` -> `parse_dimacs_text`, that broke real solves. Fixed
  locally by also normalizing `\r` in `_tokens`; the character-scan path already
  handled `\r` inline. **Retraction (2026-06-16):** an earlier note here
  claimed `scan_int_tokens` mishandled real CRLF while `scan_ints` tolerated
  it. That diagnosis was wrong — both C scanners correctly treat ASCII CR
  (0x0D) as whitespace via `isspace`, and a file written with `printf '1
  2\r\n3 4\r\n'` round-trips through both. The bug had been reproduced inline
  with `"1 2\r\n3 4\r\n"`, which silently produced `"1 2r\n3 4r\n"` because
  the EigenScript lexer didn't escape `\r` (fixed upstream in commit
  `3a48820`, `\r` now escapes to CR). The split/trim `_tokens` `\r` strip
  remains correct and load-bearing for real Windows-saved CNFs.
- Compact integer-vector ergonomics for literals, assignments, watches, and
  clause references.
- The storage benchmark now builds a flat clause arena from list-of-lists input
  and measures list scanning, arena build, flat scanning, watch seeding, and
  reconstruction. It also compacts deleted arena clauses and remaps synthetic
  reason references. This gives concrete evidence before replacing solver
  storage or promoting compact vectors/arena references into EigenScript root
  support.
- A solver-local clause-store adapter now wraps the flat arena with length,
  literal lookup, clause reconstruction, CDCL-style watch seeding, and
  compaction mapping. The benchmark compares direct flat-array scans against
  adapter-mediated access and now prints scan, watch-seeding, and compaction
  overhead deltas so adapter pressure can be reduced locally before becoming a
  root arena/reference request. Inline adapter scan/watch rows keep the same
  clause-store shape while avoiding helper calls inside the hot literal loop,
  separating data-shape pressure from helper-call overhead. Those inline rows
  are measurement evidence, not a replacement for the helper-mediated stress
  path.
- CDCL propagation, conflict analysis, learnt insertion, reduction scans, and
  deleted-clause compaction now operate over the solver-local clause store.
  The solver now reports store-to-list copies, conflict-analysis rebuild
  literals, and direct compaction-copy literals. Remaining pressure is the list
  reconstruction still needed for learnt-clause assembly. Larger copy-pressure
  cases and deferred-vs-lazy summary deltas should decide whether that pressure
  stays local or justifies EigenScript root arena/reference primitives.
- Watch-list slots now use MiniSat-style encoded literal indexes, but
  conversion still uses arithmetic helpers around signed DIMACS literals. If
  encoded-literal churn becomes hot, EigenScript may need cheaper bitwise
  operations or compact integer arrays before this should be pushed further
  into local solver representation.
- Priority queue / binary heap as a standard library candidate.
- Heap-backed CDCL decisions now rebuild list prefixes for pop/truncate and
  reinsert variables on backjump. The `heap_pops`, `heap_inserts`, and
  `heap_skips` counters are useful evidence for whether EigenScript needs
  compact mutable vector or priority-queue library support.
- Arena-like allocation for clauses and learnt-clause churn.
- Learnt-clause metadata and lazy deletion now add parallel arrays for learnt
  flags, deleted flags, activity, and level-span estimates. This is a direct
  pressure point for struct-like storage, arena-backed clause references, and
  watch-list compaction support.
- Eager compaction now remaps clause references, rebuilds watch lists, and
  replays the trail after deleted learnt clauses are removed. Compaction now
  copies kept clauses directly between clause stores and reports
  `compact_clause_copies` and `compact_clause_lits` alongside `compact_runs`,
  `compact_removed`, `watch_rebuilds`, and `compact_replays`. These counters
  should guide whether root EigenScript needs better in-place list compaction
  or arena/reference primitives.
- The metadata compaction benchmark now creates synthetic learnt clauses,
  reduces the learnt database, and forces compaction without depending on a
  large external CNF. This isolates parallel metadata arrays, clause allocation
  churn, deleted-clause filtering, reason remapping, watch rebuilds, and trail
  replay cost as their own benchmark surface.
- Metadata churn now adds repeated learnt-clause allocation/reduction/compaction
  waves with pinned reason references. This amplifies locked-clause scans,
  reason-reference remapping, watch rebuilds, and trail replay counters before
  deciding whether EigenScript needs root arena/reference primitives beyond the
  active EigenMiniSat-local clause-store prototype.
- CDCL option handling exposed a real EigenScript scoping hazard: generic local
  names such as `cfg` can mutate an outer binding through the language's
  outward assignment semantics. That behavior is intentional today, but solver
  helpers need specific local names until EigenScript has a clearer local-only
  binding form or convention.
- Restarts now cancel trail levels back to root and reinsert variables into the
  order heap while preserving phase state. The `restarts`, `restart_cancels`,
  and phase counters make repeated backtracking churn visible.
- The phase benchmark exposes saved-phase bookkeeping versus fixed positive and
  fixed negative polarity. On current small cases, the policy can change
  decisions, conflicts, propagation volume, and restarts while keeping the same
  public solver result. Larger cases should show whether this remains solver
  heuristic work or becomes root pressure around option dispatch and phase-list
  mutation.
- The heuristic benchmark now sweeps geometric/Luby restarts with saved,
  positive, and negative polarity over pigeonhole, complete-graph coloring, and
  XOR cases. This makes combined option dispatch, heap pop/reinsert churn,
  phase-list mutation, restart cancellation, and compaction side effects visible
  in one run instead of requiring separate restart and phase comparisons.
- The copy-pressure benchmark now includes larger generated pigeonhole,
  graph-coloring, and parity cases. Delta summaries compare deferred and lazy
  maxima for compaction copies, watch rebuilds, pending deleted clauses,
  watch-detach scans, and trail replays.
- The Luby restart benchmark adds small but repeated `floor`, modulo, and
  integer-power schedule calculations around CDCL conflicts. If larger restart
  sweeps make schedule overhead visible, EigenScript may need cheaper integer
  bit operations or this should become a small standard-library helper.
- Persistent mutable solver state is now implemented, and the benchmarks show
  rollback/list-truncation overhead on unit-chain cases. Compact mutable vectors
  or list truncation remain candidates if this pressure repeats.
- CDCL conflict analysis currently rebuilds learnt clauses as lists during
  resolution. If larger formulas amplify that cost, EigenScript needs either
  compact integer-vector helpers or a local clause arena before this becomes a
  downstream workaround.
