# Roadmap

## Milestone 1: Baseline DPLL

- DIMACS parsing
- simple assignment vector
- unit propagation by scanning clauses
- recursive DPLL
- fixture tests and generated benchmarks

## Milestone 2: MiniSat Data Structures

- literal encoding parity with MiniSat (`var * 2 + sign`)
- watch lists for propagation
- trail and decision levels
- binary heap variable ordering
- clause references

Status: initial watched propagation exists as a correctness/benchmark path, and
the persistent path keeps watch state across recursive DPLL nodes with trail
marks for backtracking. The next step is iterative decision levels, reasons,
and conflict analysis.

## Milestone 3: CDCL

- conflict analysis
- first-UIP learnt clauses
- activity bumping and decay
- restarts
- learnt-clause database reduction

## Milestone 4: EigenScript Feedback

Each benchmark regression should become one of:

- root EigenScript runtime/compiler issue
- EigenScript standard library candidate
- EigenMiniSat-local algorithmic correction
