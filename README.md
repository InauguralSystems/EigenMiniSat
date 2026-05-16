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
/home/jon/EigenScript/src/eigenscript minisat.eigs --heuristic-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --copy-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --storage-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --metadata-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --parse-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --scan-parse-bench --size 1
/home/jon/EigenScript/src/eigenscript minisat.eigs --diagnostic-bench --size 1
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
Clause-store counters show store-to-list copies, store-native conflict-analysis
scans, any remaining analysis list rebuilds, and direct compaction copies.
Compaction counters show when deleted learnt clauses are deferred or physically
removed, how many deleted clauses remain pending, and when watch lists are
rebuilt.
`--restart-bench` compares the default geometric CDCL restart schedule with a
Luby schedule on the same generated cases and reports restart budgets, restart
indexes, cancellations, compaction, and elapsed milliseconds.
`--phase-bench` compares saved phase decisions with fixed positive and fixed
negative polarity on the same generated cases, reporting phase save/flip and
positive/negative decision counters.
`--heuristic-bench` sweeps combined restart and polarity policies across
pigeonhole, complete-graph coloring, and XOR pressure cases, then prints
per-policy counters plus per-case decision/conflict/restart ranges.
`--copy-bench` runs conflict-heavy generated cases through tight restart and
polarity policies, then reports store-to-list copy, store-native analysis scan,
remaining analysis rebuild, deferred compaction, active watch rebuild, and
direct compaction-copy counters for deciding whether clause references should
stay local or become an EigenScript root primitive.
`--storage-bench` builds a solver-local clause-store adapter beside the
existing list-of-lists representation and compares list scanning, arena build,
flat scanning, adapter-mediated access, CDCL-style watch seeding,
reconstruction, deletion compaction, and reason-reference remapping costs.
`--metadata-bench` builds synthetic learnt-clause pressure, runs database
reduction, compacts deleted clauses, then runs repeated learnt-churn waves with
pinned reason references. It reports allocation, deletion, locked-clause, watch
rebuild, reason remap, direct compaction-copy, and trail replay counters
without needing a larger external CNF.
`--parse-bench` emits larger generated DIMACS fixtures, parses the generated
text back through the DIMACS parser, then solves the parsed clauses with CDCL.
`--scan-parse-bench` compares the current split/trim parser, a
character-scanning parser that shares the same diagnostics and output shape,
and a C-backed integer-token fast path built on EigenScript `scan_ints`. The
`scan_ints` path is intentionally for validated DIMACS-style input and
benchmark pressure; the split/trim and character scanners remain the diagnostic
parsers for malformed token/header reporting.
`--diagnostic-bench` feeds malformed DIMACS text into the split/trim and
character-scanning diagnostic parsers and reports error counts, diagnostic text
lengths, and checksums. The C-backed `scan_ints` path is deliberately omitted
because it is a fast validated-input path, not a full diagnostic parser.
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
solver tests, metadata compaction, copy pressure, scan parser comparison, and
the manifest corpus plus clause storage pressure; the `full` profile runs every
benchmark mode.
`docs/EIGENSCRIPT_FEEDBACK.md` tracks which benchmark pressure points currently
look like EigenScript root/runtime candidates, standard-library candidates, or
EigenMiniSat-local work.

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
- combined restart/polarity heuristic stress benchmarks
- conflict-copy pressure benchmarks over clause-store CDCL counters
- eager deleted-clause compaction with reason remapping and watch rebuild/replay
- flat clause arena benchmark for compact clause/vector storage pressure
- solver-local clause-store adapter for clause references, watch seeding, and
  compaction mapping pressure
- CDCL propagation, conflict analysis, learnt insertion, reduction, and
  compaction over the solver-local clause-store adapter
- store-native CDCL conflict analysis over clause references
- deferred CDCL clause-store compaction with active watch rebuilds
- clause-store copy/native-scan/rebuild counters for conflict analysis and
  direct compaction-copy pressure
- synthetic learnt metadata compaction and churn benchmark pressure
- larger generated DIMACS fixture families for parser and scale pressure
- file-backed generated DIMACS fixtures for write/read/temp cleanup pressure
- manifest-driven DIMACS corpus fixtures for real file-shape coverage
- lightweight trend runner for repeatable pressure snapshots
- root-pressure feedback ledger for EigenScript/std-lib/local decisions
- DIMACS parser diagnostics for header/count/token problems
- character-scanning DIMACS parser comparison path
- malformed DIMACS diagnostic benchmark pressure
- C-backed `scan_ints` DIMACS parser comparison path
- fixture correctness tests
- generated benchmark families

Next:

- larger heuristic and copy-pressure stress cases
- use deferred compaction counters to decide whether watch rebuild/replay
  pressure belongs in EigenMiniSat, a library, or EigenScript root
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
- combined restart/polarity option sweeps across branch-heavy cases
- conflict-heavy copy pressure across tight restart and polarity policies
- restart schedule arithmetic and option plumbing for geometric/Luby comparison
- clause compaction and watch rebuild/replay overhead
- flat clause arena build/scan/reconstruct/watch-seeding/compaction pressure
- clause-store adapter lookup, watch seeding, and compaction mapping overhead
- CDCL clause-store propagation and conflict-analysis access patterns
- store-to-list copy counts, store-native analysis scans, remaining
  conflict-analysis rebuild literals, and direct compaction-copy literals
- deferred deleted-clause pressure, pending deleted clauses, and active watch
  rebuild/replay churn
- synthetic learnt-clause allocation, deletion, compaction, and churn pressure
- generated DIMACS string throughput and parse-token allocation
- temp-file write/read/remove overhead around parser throughput
- parser robustness across checked-in DIMACS formatting variants
- manifest parsing and corpus-family metadata plumbing
- repeatable trend-log capture without committing machine-local run output
- parser diagnostic overhead while validating larger CNF input
- malformed parser diagnostic text allocation and consistency checks
- character-at-a-time scanner overhead versus split/trim tokenization
- C-backed integer scan throughput versus EigenScript-side clause assembly
