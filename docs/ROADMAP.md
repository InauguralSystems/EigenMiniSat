# Roadmap

## Milestone 1: Baseline DPLL

- DIMACS parsing
- simple assignment vector
- unit propagation by scanning clauses
- recursive DPLL
- fixture tests and generated benchmarks

Status: DIMACS parsing now has a generated parse benchmark path that emits
larger CNF families, reparses the text, and solves parsed clauses through CDCL.
The same generated fixtures can also be written to temp files and parsed through
the file-backed DIMACS path to measure write/read/remove overhead.
Checked-in DIMACS corpus fixtures are now manifest-driven and cover comments,
multiline clauses, multiple clauses on one physical line, graph-coloring,
pigeonhole, wide-clause, and parity/XOR SAT/UNSAT cases.
The parser now returns diagnostics for malformed headers, declared count
mismatches, variable-bound mismatches, non-integer tokens, and missing headers.
A character-scanning parser path now shares the same diagnostics and can be
benchmarked against the split/trim parser. The benchmark also includes a
C-backed `scan_ints` parser path on generated fixtures and corpus files to
measure root scanner throughput separately from EigenScript-side clause
assembly. A lightweight trend runner now records selected pressure snapshots
under ignored local logs so parser, corpus, and metadata changes can be
compared without committing machine-specific output.

## Milestone 2: MiniSat Data Structures

- literal encoding parity with MiniSat (`var * 2 + sign`)
- watch lists for propagation
- trail and decision levels
- binary heap variable ordering
- clause references

Status: literal watch-list indexes now use MiniSat-style `var * 2 + sign`
encoding internally while keeping signed DIMACS literals at the parser/CLI
boundary. Initial watched propagation exists as a correctness/benchmark path,
and the persistent path keeps watch state across recursive DPLL nodes with
trail marks for backtracking. CDCL decisions now use a MiniSat-style variable
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
fixed-polarity comparison, geometric restarts, and a Luby restart comparison
path are in place. Deleted learnt clauses are now eagerly compacted by
remapping clause references and rebuilding watch lists. A synthetic metadata
benchmark now isolates learnt allocation, database reduction, compaction,
watch rebuild, and trail replay pressure without requiring a larger CNF corpus.
The next target is larger polarity/restart/metadata stress cases,
scanner diagnostic/token-span pressure, compact clause storage pressure, and a
larger third-party CNF corpus beyond the checked-in manifest fixtures.

## Milestone 4: EigenScript Feedback

Each benchmark regression should become one of:

- root EigenScript runtime/compiler issue
- EigenScript standard library candidate
- EigenMiniSat-local algorithmic correction
