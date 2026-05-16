# EigenMiniSat Gap Log

Every entry here should be tied to a concrete solver or benchmark failure.
Root EigenScript issues should be fixed upstream instead of worked around here.

## Open Watchlist

- Hot function-call overhead in propagation loops.
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
  `ok`/`errors` counts. If larger corpora amplify the extra validation cost,
  EigenScript may need cheaper character classification or a streaming
  tokenizer.
- The corpus manifest is deliberately plain text, so EigenScript parses case
  metadata itself instead of relying on a host-side runner. This exposes
  repeated split/trim/numeric conversion and validates whether simple
  structured-data ingestion belongs in the standard library.
- The benchmark trend runner captures repeatable pressure snapshots without
  committing machine-local logs. This should make regressions easier to compare
  while keeping the constrained dev machine's output explicit and local.
- A character-scanning DIMACS parser now matches the split/trim parser's
  diagnostics and clauses, but repeated `substr` and token string concatenation
  are often slower than split/trim on these fixtures. EigenScript now exposes
  the root `scan_ints` primitive, and EigenMiniSat benchmarks all three parser
  paths on both generated fixtures and the manifest corpus. The remaining
  pressure is clause assembly from scanned integers and whether a future
  tokenizer should expose token spans/error reporting for full diagnostics
  instead of only numeric extraction.
- Compact integer-vector ergonomics for literals, assignments, watches, and
  clause references.
- The storage benchmark now builds a flat clause arena from list-of-lists input
  and measures list scanning, arena build, flat scanning, watch seeding, and
  reconstruction. It also compacts deleted arena clauses and remaps synthetic
  reason references. This gives concrete evidence before replacing solver
  storage or promoting compact vectors/arena references into EigenScript root
  support.
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
  replays the trail after deleted learnt clauses are removed. The
  `compact_runs`, `compact_removed`, `watch_rebuilds`, and `compact_replays`
  counters should guide whether root EigenScript needs better in-place list
  compaction or arena/reference primitives.
- The metadata compaction benchmark now creates synthetic learnt clauses,
  reduces the learnt database, and forces compaction without depending on a
  large external CNF. This isolates parallel metadata arrays, clause allocation
  churn, deleted-clause filtering, reason remapping, watch rebuilds, and trail
  replay cost as their own benchmark surface.
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
