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
/home/jon/EigenScript/src/eigenscript minisat.eigs --cdcl tests/fixtures/simple_sat.cnf
/home/jon/EigenScript/src/eigenscript minisat.eigs --bench --size 1
tests/run_smoke.sh
```

The CLI prints MiniSat-like `s SATISFIABLE` or `s UNSATISFIABLE` lines for CNF
files, plus baseline counters. Benchmarks print `scan`, `watched`,
`persistent`, and `cdcl` lines per generated case with elapsed milliseconds,
variable count, clause count, decisions, propagations, and conflicts. The CDCL
line also reports learnt clauses, backjumps, conflict-resolution steps, variable
activity bumps/decays, heap operation counters, and learnt-clause database
counters. CDCL output also includes restart and phase-saving counters.
Compaction counters show when deleted learnt clauses are removed and watch lists
are rebuilt.

## Scope

Current:

- DIMACS CNF parsing
- DPLL with unit propagation
- watched-literal propagation path for correctness and benchmark comparison
- persistent watched trail/backtracking path
- first CDCL path with reason/level arrays, learnt clauses, and backjumping
- MiniSat-style variable activity and a binary heap order structure for CDCL
- learnt-clause metadata, activity, locked-clause protection, and lazy reduction
- saved phase/polarity decisions and geometric restart policy
- eager deleted-clause compaction with reason remapping and watch rebuild/replay
- fixture correctness tests
- generated benchmark families

Next:

- richer restart schedules and polarity heuristics
- compact clause/vector storage if metadata and lazy deletion pressure grows

## EigenScript Pressure

This repo is expected to stress:

- hot integer/list loops
- mutable list and dict state
- recursive search and backtracking
- parser/string throughput for DIMACS
- heap and queue library candidates, including pop/reinsert churn
- allocator behavior under clause metadata, learnt churn, and lazy deletion
- restart cancellation and phase-saving churn across repeated backtracking
- clause compaction and watch rebuild/replay overhead
