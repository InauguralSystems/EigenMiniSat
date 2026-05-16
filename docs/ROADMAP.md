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
assembly. A malformed-DIMACS diagnostic benchmark now compares split/trim and
character-scanning diagnostic paths on token/header/count failures while
intentionally leaving the validated-input `scan_ints` path out of that surface.
A lightweight trend runner now records selected pressure snapshots under
ignored local logs so parser, corpus, and metadata changes can be compared
without committing machine-specific output.

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
activity array and binary heap/order structure. A flat clause arena benchmark
now measures list scanning, arena build, flat scanning, watch seeding, and
reconstruction. It also measures deleted-clause compaction and synthetic reason
reference remapping before committing to a solver storage rewrite or root
compact vector support. A solver-local clause-store adapter now wraps the flat
arena with clause length/literal lookup, reconstruction, CDCL-style watch
seeding, and deletion-compaction mapping. CDCL propagation, conflict analysis,
learnt insertion, reduction scans, and deleted-clause compaction now use that
adapter. Compaction copies kept clauses directly store-to-store, and CDCL now
reports store-to-list copies, store-native conflict-analysis scans, remaining
analysis rebuild literals, deferred compaction checks, pending deleted clauses,
targeted watch-detach scans/removals, and compaction-copy literals. A focused
copy-pressure benchmark now runs conflict-heavy generated cases under tight
restart and polarity policies, including larger evidence cases and lazy
no-physical-compaction variants. It also emits deferred-vs-lazy delta summaries
before asking EigenScript for root arena support. Storage pressure now also
prints adapter scan, watch-seeding, and compaction overhead deltas to separate
solver-local adapter costs from root/runtime storage needs. Inline adapter
scan/watch rows further split helper-call overhead from the clause-store data
shape.

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
path are in place. A combined heuristic benchmark now sweeps restart and phase
policies over pigeonhole, complete-graph coloring, and XOR pressure cases.
Deleted learnt clauses are now eagerly compacted by remapping clause references
and rebuilding watch lists in the synthetic metadata path, while the CDCL solve
path now defers physical compaction behind deleted-clause thresholds and
detaches deleted learnt clauses from their current watch buckets without
copying the clause store or replaying the trail while compaction stays below
thresholds. Copy-pressure cases also expose a lazy no-physical-compaction policy
to compare against the default deferred policy when larger cases cross those
thresholds. Watched propagation also preserves unprocessed bucket
tails when a conflict stops propagation early, so deferred compaction no longer
depends on a full watch rebuild to repair missing watcher entries. A synthetic metadata
benchmark now isolates learnt allocation, database reduction, compaction, watch
rebuild, and trail replay pressure without requiring a larger CNF corpus. It
also runs repeated
learnt-churn waves with pinned reason references to expose locked-clause scans
and repeated reason remapping. The next target is measuring remaining
targeted watch-detach and physical compaction pressure across larger conflict
cases, then deciding whether that pressure belongs in EigenMiniSat, a reusable
library, or EigenScript root. The corpus now includes small vendored structural
fixtures with provenance notes; true third-party CNF imports should wait until
the provenance and size constraints are clear. Scanner token-span pressure
remains a parallel root/stdlib decision path.

## Milestone 4: EigenScript Feedback

Each benchmark regression should become one of:

- root EigenScript runtime/compiler issue
- EigenScript standard library candidate
- EigenMiniSat-local algorithmic correction

Status: `docs/EIGENSCRIPT_FEEDBACK.md` now records the current classification
ledger. Local-only binding and diagnostic token spans are root/runtime
candidates, string builders and priority queues are standard-library
candidates, compact integer vectors are still root-vs-stdlib pressure, and
clause arenas are being prototyped and measured locally in EigenMiniSat before
asking for a root primitive. The trend runner now has an evidence profile for
bounded larger-case decision runs, and its summary emits active
candidate-decision rows so the next experiment is scoped before any root or
stdlib request is made.
