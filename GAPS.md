# EigenMiniSat Gap Log

Every entry here should be tied to a concrete solver or benchmark failure.
Root EigenScript issues should be fixed upstream instead of worked around here.

## Open Watchlist

- Hot function-call overhead in propagation loops.
- Compact integer-vector ergonomics for literals, assignments, watches, and
  clause references.
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
- Restarts now cancel trail levels back to root and reinsert variables into the
  order heap while preserving phase state. The `restarts`, `restart_cancels`,
  and phase counters make repeated backtracking churn visible.
- Persistent mutable solver state is now implemented, and the benchmarks show
  rollback/list-truncation overhead on unit-chain cases. Compact mutable vectors
  or list truncation remain candidates if this pressure repeats.
- CDCL conflict analysis currently rebuilds learnt clauses as lists during
  resolution. If larger formulas amplify that cost, EigenScript needs either
  compact integer-vector helpers or a local clause arena before this becomes a
  downstream workaround.
