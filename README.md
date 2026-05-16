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
/home/jon/EigenScript/src/eigenscript minisat.eigs --restart-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --phase-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --metadata-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --parse-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --scan-parse-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --file-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --corpus-bench [--manifest tests/corpus/manifest.txt]
tests/run_smoke.sh
benchmarks/run_trends.sh quick 1
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
`--restart-bench` compares the default geometric CDCL restart schedule with a
Luby schedule on the same generated cases and reports restart budgets, restart
indexes, cancellations, compaction, and elapsed milliseconds.
`--phase-bench` compares saved phase decisions with fixed positive and fixed
negative polarity on the same generated cases, reporting phase save/flip and
positive/negative decision counters.
`--metadata-bench` builds synthetic learnt-clause pressure, runs database
reduction, compacts deleted clauses, and reports allocation, deletion, watch
rebuild, and trail replay counters without needing a larger external CNF.
`--parse-bench` emits larger generated DIMACS fixtures, parses the generated
text back through the DIMACS parser, then solves the parsed clauses with CDCL.
`--scan-parse-bench` compares the current split/trim parser, a
character-scanning parser that shares the same diagnostics and output shape,
and a C-backed integer-token fast path built on EigenScript `scan_ints`. The
`scan_ints` path is intentionally for validated DIMACS-style input and
benchmark pressure; the split/trim and character scanners remain the diagnostic
parsers for malformed token/header reporting.
`--file-bench` writes the same generated fixtures through EigenScript temp-file
I/O, reparses them with `parse_dimacs_file`, removes the temp file, then solves
the parsed clauses with CDCL.
`--corpus-bench` loads checked-in DIMACS files from a pipe-delimited manifest.
The default corpus covers comments, multiline clauses, multi-clause lines,
graph coloring, pigeonhole, wide clauses, and parity/XOR SAT/UNSAT instances.
For each case it compares split/trim parsing, character scanning, and the
C-backed `scan_ints` path before solving with CDCL.
`benchmarks/run_trends.sh` records selected pressure outputs to ignored
timestamped logs under `benchmarks/runs/`. The default `quick` profile runs
solver tests, metadata compaction, scan parser comparison, and the manifest
corpus; the `full` profile runs every benchmark mode.

## Scope

Current:

- DIMACS CNF parsing
- DPLL with unit propagation
- MiniSat-style literal encoding for watch-list indexing
- watched-literal propagation path for correctness and benchmark comparison
- persistent watched trail/backtracking path
- first CDCL path with reason/level arrays, learnt clauses, and backjumping
- MiniSat-style variable activity and a binary heap order structure for CDCL
- learnt-clause metadata, activity, locked-clause protection, and lazy reduction
- saved/fixed phase polarity benchmarks, geometric restarts, and Luby restart benchmarks
- eager deleted-clause compaction with reason remapping and watch rebuild/replay
- synthetic learnt metadata and compaction benchmark pressure
- larger generated DIMACS fixture families for parser and scale pressure
- file-backed generated DIMACS fixtures for write/read/temp cleanup pressure
- manifest-driven DIMACS corpus fixtures for real file-shape coverage
- lightweight trend runner for repeatable pressure snapshots
- DIMACS parser diagnostics for header/count/token problems
- character-scanning DIMACS parser comparison path
- C-backed `scan_ints` DIMACS parser comparison path
- fixture correctness tests
- generated benchmark families

Next:

- larger polarity, restart-schedule, and metadata stress cases
- compact clause/vector storage if metadata and lazy deletion pressure grows
- larger third-party CNF corpus once checked-in corpus pressure stabilizes

## EigenScript Pressure

This repo is expected to stress:

- hot integer/list loops
- signed DIMACS literal conversion to MiniSat-style encoded literal indexes
- mutable list and dict state
- recursive search and backtracking
- parser/string throughput for DIMACS
- heap and queue library candidates, including pop/reinsert churn
- allocator behavior under clause metadata, learnt churn, and lazy deletion
- phase-saving and fixed-polarity decision churn across CDCL cases
- restart cancellation and phase-saving churn across repeated backtracking
- restart schedule arithmetic and option plumbing for geometric/Luby comparison
- clause compaction and watch rebuild/replay overhead
- synthetic learnt-clause allocation, deletion, and compaction pressure
- generated DIMACS string throughput and parse-token allocation
- temp-file write/read/remove overhead around parser throughput
- parser robustness across checked-in DIMACS formatting variants
- manifest parsing and corpus-family metadata plumbing
- repeatable trend-log capture without committing machine-local run output
- parser diagnostic overhead while validating larger CNF input
- character-at-a-time scanner overhead versus split/trim tokenization
- C-backed integer scan throughput versus EigenScript-side clause assembly
