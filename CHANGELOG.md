# Changelog

## [Unreleased]

### CDCL Solver
- **Variable-activity rescaling (#84).** `bump_var_activity` added `var_inc`
  and nothing ever rescaled, so `var_inc = 1 / var_decay^conflicts` reached the
  double ceiling on conflict **13,828**. `1e308 + 1e308 == 1e308`, so every
  bump past that is a no-op: activities tie, `order_better` falls through to
  its `a < b` tie-break, and branching silently becomes static
  lowest-index-first while the heap keeps running. MiniSat's
  `varRescaleActivity` — divide every activity and the increment by 1e100 once
  an activity exceeds 1e100 — had no counterpart here.

  Measured on Tseitin 4x4 at a 16,000-conflict budget: **10 of 33** distinct
  variable activities before, **31 of 33** after, `var_inc` 1e308 (saturated)
  before and 2.4e58 (live) after, at equal wall clock. Banked in BASELINE.md.

  Rescaling is a pure reparameterisation — uniform scaling preserves every
  comparison, so the heap needs no re-heapify and a run is bit-identical
  wherever the limit sits. `tests/test_solver.eigs` gates exactly that: the
  same instance at limits 0.001, 1, 1000 and the default produces identical
  decisions, conflicts and resolutions, with `var_rescales` the only counter
  that moves. Instances that never cross the limit are unchanged, so nothing
  banked below ~4,500 conflicts shifts.

  `var_rescale_limit` is a CDCL option (default `1e100`); **0 selects the
  pre-#84 unrescaled behaviour**, which is what every ladder rung banked before
  this fix ran under — comparing across the change needs both arms in one
  binary. New counter `var_rescales`, printed by the CLI.

### Parser
- **Genuine SATLIB files parse (#83).** Every instance in the `uf`/`uuf`
  archives ends with a two-line trailer — a line holding only `%`, then a
  line holding only `0`. Neither belongs to the formula. `%` reached the
  token loop and raised `non-integer token %`, and the `0` closed an empty
  `state.current` into a phantom clause, so `assert_dimacs_ok` aborted before
  anything was solved. The parser now cuts the text at the `%` line **before
  tokenizing**, in one place shared by all four parse paths — including
  `parse_dimacs_text_ints`, whose `scan_ints` swallows the `%` silently and
  would otherwise be left with only the clause-count mismatch.

  The solver was never implicated: with the trailer stripped by hand, 40
  `uf20-91` instances (all SAT, models verified) and 15 `uuf50-218` (all
  UNSAT, refutations drat-trim'd) came back 55/55 correct. This was input
  fidelity only.

- **A bare `0` with no preceding literals is a parse error.** Skipping `%`
  without discarding the `0` leaves the phantom empty clause in place, which
  makes any instance trivially unsatisfiable — and the DRAT oracle does not
  catch it: the one-line refutation drat-trim verifies is genuinely RUP
  against the clause list it was handed, and a checker cannot know those
  clauses are not the file. A corrupted parse would then produce a wrong
  verdict *with a signed proof*, the over-pruning failure mode arriving
  through the parser instead of the search. The guard closes it even when the
  header's declared count happens to reconcile with the phantom, which is the
  case no count check can see.

- **The vendored corpus carries the trailer** and `run_smoke.sh` gates on the
  **verdict** of a known-SAT SATLIB-shaped fixture on every propagation path,
  not on `ok == 1`. The fixtures were generated locally by the same author as
  the parser, so they shared its assumption that the archives are clean
  DIMACS: they agreed with the parser and both disagreed with the outside
  world. A parse-only assertion cannot tell the fix from the trap above.

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
