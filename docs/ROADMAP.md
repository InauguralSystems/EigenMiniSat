# Roadmap

## Milestone 1: Baseline DPLL

- DIMACS parsing
- simple assignment vector
- unit propagation by scanning clauses
- recursive DPLL
- fixture tests and generated benchmarks

Status: DIMACS parsing now has a generated parse benchmark path that emits
larger CNF families, reparses the text, and solves parsed clauses through CDCL.

## Milestone 2: MiniSat Data Structures

- literal encoding parity with MiniSat (`var * 2 + sign`)
- watch lists for propagation
- trail and decision levels
- binary heap variable ordering
- clause references

Status: initial watched propagation exists as a correctness/benchmark path, and
the persistent path keeps watch state across recursive DPLL nodes with trail
marks for backtracking. CDCL decisions now use a MiniSat-style variable
activity array and binary heap/order structure.

## Milestone 3: CDCL

- conflict analysis
- first-UIP learnt clauses
- activity bumping and decay
- restarts
- learnt-clause database reduction

Status: a first CDCL path exists with reason arrays, assignment levels,
conflict-clause resolution, learnt clauses, and non-chronological backjumping.
Variable activity bump/decay, a heap-backed decision order, learnt metadata,
locked-clause protection, lazy learnt-clause reduction, saved phase decisions,
and a geometric restart policy are in place. Deleted learnt clauses are now
eagerly compacted by remapping clause references and rebuilding watch lists.
The next target is richer restart schedules, polarity heuristics, and larger
external CNF fixtures.

## Milestone 4: EigenScript Feedback

Each benchmark regression should become one of:

- root EigenScript runtime/compiler issue
- EigenScript standard library candidate
- EigenMiniSat-local algorithmic correction
