# EigenMiniSat Gap Log

Every entry here should be tied to a concrete solver or benchmark failure.
Root EigenScript issues should be fixed upstream instead of worked around here.

## Open Watchlist

- Hot function-call overhead in propagation loops.
- Compact integer-vector ergonomics for literals, assignments, watches, and
  clause references.
- Priority queue / binary heap as a standard library candidate.
- Arena-like allocation for clauses and learnt-clause churn.
- Persistent mutable solver state is now implemented, and the benchmarks show
  rollback/list-truncation overhead on unit-chain cases. Compact mutable vectors
  or list truncation remain candidates if this pressure repeats.
- CDCL conflict analysis currently rebuilds learnt clauses as lists during
  resolution. If larger formulas amplify that cost, EigenScript needs either
  compact integer-vector helpers or a local clause arena before this becomes a
  downstream workaround.
