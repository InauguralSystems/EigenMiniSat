# Changelog

## [Unreleased]

### Proofs
- **DRAT proof emission.** `--cdcl --proof FILE` writes a DRAT refutation of
  an UNSAT instance: one line per learnt clause plus the final empty clause.
  Enabled per-solve through the new `"proof"` CDCL option; off by default and
  it does not perturb the search (`resolutions` identical with and without).
  Additions only, no `d` deletion lines — deletions are a checker-speed
  optimization, and withholding them leaves the checker a superset of our
  clauses, which can only make a RUP check succeed, never fail.
- **`tests/run_proof_check.sh`** verifies those refutations with `drat-trim`,
  which shares no code with this solver. This is the first external oracle
  the UNSAT path has had: a SAT answer self-verifies against its model, an
  UNSAT answer previously had nothing checking it, so an over-pruning bug
  would report `s UNSATISFIABLE` with the suite still green. Includes a
  planted-fault case (lemmas removed from a valid proof) that the checker
  must reject — without it, a misconfigured checker passes everything.
  Wired into CI as its own step.
- **Tseitin-on-torus generator** (`tseitin_torus_case`): the hard parity
  family, one variable per edge of a 4-regular toroidal grid with each
  vertex constraining the XOR of its incident edges to a charge. Odd total
  charge is UNSAT and needs resolution refutations of size
  2^Omega(min(rows,cols)) (Urquhart 1987) — hardness from parity plus graph
  expansion, a different mechanism from pigeonhole's counting. The existing
  `xor_triangle_case` is the tractable regime (SAT, zero conflicts) and stays
  as the easy baseline. `tests/fixtures/tseitin_torus_3x3_odd.cnf` is the
  checked-in instance.
- **`--proof-bench`**: reports refutation size (`size_resolutions`,
  `size_learnt_lits`, `size_learnts`), clause space (`space_peak_learnts`),
  and depth (`depth_max_level`) per policy per family, with per-family
  ladders and size-growth ratios. The three axes trade against each other —
  at pigeonhole-6-5, `geom-saved` gives size 1276 / space 56 while
  `geom-negative` gives 1605 / 42, so size-only and space-only views pick
  different winners. Not in `run_smoke.sh` (seconds per solve on the hard
  families); runs as its own CI step.
- New solver counters `peak_learnts` (clause-space high-water mark, distinct
  from the surviving `active_learnts`) and `max_level` (deepest decision
  level).

### CLI
- Fixed: the CLI ran the scan/DPLL solver unconditionally and then discarded
  its result whenever `--watched`, `--persistent`, or `--cdcl` was given, so
  every non-default solve paid for a full DPLL solve it threw away. On
  pigeonhole-6-5 (n=5 medians) the discarded DPLL solve was 531ms against
  614ms of CDCL, so `--cdcl` went ~1145ms -> 614ms. The saving grows with how
  badly DPLL does on the instance. Counters were never affected — the
  discarded result was overwritten — so no reported measurement changes.

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
