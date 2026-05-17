# EigenMiniSat Gap Log

Every entry here should be tied to a concrete solver or benchmark failure.
Root EigenScript issues should be fixed upstream instead of worked around here.

## Open Watchlist

- Hot function-call overhead in propagation loops.
- Stress benchmarks should not hide root/runtime pressure with local bypasses.
  Inline or alternate forms can exist as comparison surfaces, but the main
  stress path should continue exposing the language gap until EigenScript root
  or a deliberate library abstraction addresses it.
- `docs/EIGENSCRIPT_FEEDBACK.md` now classifies current pressure into
  EigenScript root/runtime candidates, standard-library candidates, and
  EigenMiniSat-local work. The current direction is local-only binding and
  diagnostic token spans as root candidates, string builders and priority
  queues as standard-library candidates, compact integer vectors as root-vs
  stdlib pressure, and clause arenas as an EigenMiniSat-local prototype first.
- DIMACS parser throughput is now measured with generated text fixtures. The
  current path builds strings by repeated concatenation and tokenizes each line
  through split/trim/num conversion, so larger fixtures should tell us whether
  EigenScript needs string-builder or streaming-tokenizer support.
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
  malformed diagnostics without running every benchmark mode. Its summary
  collapses copy, metadata, storage, parser, diagnostic, and corpus output into
  decision flags and active `decision_candidate` rows for the
  root-vs-library-vs-local ledger.
- A character-scanning DIMACS parser now matches the split/trim parser's
  diagnostics and clauses, but repeated `substr` and token string concatenation
  are often slower than split/trim on these fixtures. EigenScript now exposes
  the root `scan_ints` primitive, and EigenMiniSat benchmarks all three parser
  paths on both generated fixtures and the manifest corpus. The remaining
  pressure is clause assembly from scanned integers and whether a future
  tokenizer should expose token spans/error reporting for full diagnostics
  instead of only numeric extraction.
- The diagnostic benchmark now feeds malformed DIMACS cases through the
  split/trim and character-scanning parsers, checking error counts and
  diagnostic text sizes. This isolates malformed-token/header/count overhead and
  keeps pressure on whether EigenScript should expose tokenizer spans for
  diagnostics instead of forcing parser-local string assembly.
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
