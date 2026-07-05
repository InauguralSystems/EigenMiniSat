# Changelog

## [Unreleased]

### CDCL Solver
- Budgeted CDCL sessions: `cdcl_begin of [nvars, clauses, opts]` returns a
  resumable session; `cdcl_step of [session, budget]` runs a bounded slice
  (one budget unit = a propagation round ending in a conflict resolution or
  a decision) and returns `"RUNNING"` / `"SAT"` / `"UNSAT"`. MiniSat's
  `solve_limited` shape — lets a cooperative host (the EigenOS desktop)
  interleave solving with a UI loop. `solve_cnf_cdcl_with_options` is
  re-derived from the session API; counters and CLI output are
  byte-identical to the previous run-to-completion loop.
- `lib/solver.eigs` is now composition-free: the `load_file` of
  `int_vector.eigs` moved to the entry points (`minisat.eigs`, tests), the
  tidelog cbor/store convention. A self-loading library can't be embedded
  byte-unmodified where `load_file` doesn't exist (the EigenOS ROM bundle
  concatenates library files instead).

## [0.1.0] — 2026-07-01

### CDCL Solver
- MiniSat-style clause minimization (litRedundant / first-UIP redundant literal removal)
- LBD-based clause management (Glucose-style glue clauses, LBD ≤ 2 kept forever)
- Lazy watch cleanup (skip eager detach, rely on propagation-time skip)
- Raised compaction thresholds (50% waste / 64 min, matching MiniSat)

### Benchmarks
- Random 3-SAT generator (`--random-bench --size N`) at phase transition
- Validated on real random structure up to uf150 (150 vars, 645 clauses)

### EigenScript Integration
- Consume `list_truncate` and `sort_by` builtins
- Sort-based `reduce_learnt_db` (O(n log n) replaces O(n²) scan loop)
- O(1) `clause_locked` via first-watched-literal reason check
- Generation-counted `bump_clause_activity` (O(n) dedup)

## [Initial Release]

- DIMACS CNF parser with split/trim, character-scan, and C-backed scan paths
- DPLL solver with unit propagation
- Watched literal propagation (basic and persistent)
- Full CDCL with conflict analysis, first-UIP, activity heap, restarts
- Geometric and Luby restart schedules
- Phase-saving and fixed-polarity comparison
- Clause store with flat arena and compaction
- Benchmark suite with generated families (chain, pigeonhole, graph-coloring, XOR/parity)
- Manifest-driven DIMACS corpus
- Comprehensive `test_solver.eigs` correctness suite
