# EigenMiniSat

EigenMiniSat is a MiniSat-targeted SAT solver and benchmark suite written in
EigenScript. The point is twofold:

- port a well-known working solver toward MiniSat-style CDCL
- create repeatable benchmarks that expose EigenScript language/runtime gaps

The first milestone is a correct DPLL baseline with DIMACS parsing, fixtures,
and generated benchmark families. Later milestones should add watched literals,
clause activity, VSIDS-style variable ordering, learnt clauses, and database
reduction.

## Usage

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs tests/fixtures/simple_sat.cnf
/home/jon/EigenScript/src/eigenscript minisat.eigs --watched tests/fixtures/simple_sat.cnf
/home/jon/EigenScript/src/eigenscript minisat.eigs --persistent tests/fixtures/simple_sat.cnf
/home/jon/EigenScript/src/eigenscript minisat.eigs --bench --size 1
tests/run_smoke.sh
```

The CLI prints MiniSat-like `s SATISFIABLE` or `s UNSATISFIABLE` lines for CNF
files, plus baseline counters. Benchmarks print `scan`, `watched`, and
`persistent` lines per generated case with elapsed milliseconds, variable
count, clause count, decisions, and propagations.

## Scope

Current:

- DIMACS CNF parsing
- DPLL with unit propagation
- watched-literal propagation path for correctness and benchmark comparison
- persistent watched trail/backtracking path
- fixture correctness tests
- generated benchmark families

Next:

- MiniSat-style trail and decision levels
- binary heap variable ordering
- clause allocator / arena pressure
- conflict analysis and learnt clauses

## EigenScript Pressure

This repo is expected to stress:

- hot integer/list loops
- mutable list and dict state
- recursive search and backtracking
- parser/string throughput for DIMACS
- heap and queue library candidates
- allocator behavior under clause churn
