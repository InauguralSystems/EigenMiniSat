# CLAUDE.md

Guidance for working in this repository.

## What this is

EigenMiniSat is a **SAT solver written in EigenScript**, working its
way from a correct DPLL baseline toward a MiniSat/Glucose-style CDCL
implementation. The repo has two missions:

1. Ship a working solver (DIMACS in, `s SATISFIABLE` / `s UNSATISFIABLE`
   out, with MiniSat-shaped counters).
2. **Stress EigenScript itself** — every bench mode is also a
   pressure surface for a runtime/stdlib decision. When a workaround
   would speed the solver up, keep it as a *comparison benchmark*
   so the data drives a root or library decision instead of hiding
   it locally.

Sibling stress repo to EigenGauntlet, EigenRegex, and Tidepool. The
solver's progress is real; the benchmarks are the forcing function.

## Toolchain

EigenScript is **not** vendored. Point at a built binary:

```bash
EIGS=${EIGENSCRIPT_BIN:-../EigenScript/src/eigenscript}
$EIGS minisat.eigs tests/fixtures/simple_sat.cnf
```

Minimum is **v0.11.8** — the earliest release that runs the CDCL suite
green. The floor is set by a v0.11.x VM fix, not by stdlib integer
vectors (those shipped in v0.11.2, but that release still crashes the
CDCL path).
CI builds and tests against EigenScript **v0.34.0** (pinned in
`.github/workflows/ci.yml`): the correctness suite is green — all
`test_solver.eigs` assertions and the full `run_smoke.sh` pass. The
`Inline tiny accessors in CDCL hot path` commit captures the hoist
pattern needed for the inline-cache JIT — now load-bearing for the CDCL
hot path.

## Run / test / benchmark

```bash
EIGS=../EigenScript/src/eigenscript

# Solve a CNF file with each propagation path
$EIGS minisat.eigs                       tests/fixtures/simple_sat.cnf  # DPLL
$EIGS minisat.eigs --watched             tests/fixtures/simple_sat.cnf  # watched literals
$EIGS minisat.eigs --persistent          tests/fixtures/simple_sat.cnf  # persistent watch trail
$EIGS minisat.eigs --cdcl                tests/fixtures/simple_sat.cnf  # CDCL

# Correctness sweep (fixtures, parser shapes, generated cases)
./tests/run_smoke.sh

# External oracle for UNSAT: emit DRAT refutations and have drat-trim check them
DRAT_TRIM=/path/to/drat-trim ./tests/run_proof_check.sh

# Trend logs into benchmarks/runs/ (ignored)
./benchmarks/run_trends.sh quick    1   # quick profile, size 1
./benchmarks/run_trends.sh evidence 2 /tmp/eigenminisat-evidence.log  # bounded larger-case decisions
./benchmarks/run_trends.sh full         # every bench mode
./benchmarks/summarize_trend.sh /tmp/eigenminisat-evidence.log
```

The bench modes (`--bench`, `--restart-bench`, `--phase-bench`,
`--copy-bench`, `--storage-bench`, `--metadata-bench`, `--parse-bench`,
`--scan-parse-bench`, `--diagnostic-bench`, `--file-bench`,
`--corpus-bench`, `--heuristic-bench`, `--random-bench`, `--proof-bench`) each
isolate a specific pressure surface — see `README.md` for the per-mode counter
list. `--proof-bench` is the odd one out: it measures the refutation's shape
(size / space / depth), not the runtime, and is deliberately NOT in
`run_smoke.sh` because the hard families cost seconds per solve. It runs as its
own CI step.

## Layout

(`ls lib/ tests/` for the inventory. The parts that aren't obvious:)

- `lib/solver.eigs` holds **all four solver paths** (DPLL / watched /
  persistent / CDCL) — a change to one usually needs the others checked.
- `benchmarks/runs/` is gitignored and machine-local; `benchmarks/run_trends.sh`
  takes a profile (`quick` / `evidence` / `full`).
- `docs/EIGENSCRIPT_FEEDBACK.md` — root/stdlib/local decisions by pressure
  point; `GAPS.md` — per-friction ledger (same format as Tidepool / EigenRegex).

## Architecture notes

- **Solver paths layer**: DPLL → watched literals → persistent watch
  trail → CDCL. Each is selectable on the CLI so benchmarks can
  isolate any single one. Don't delete the older paths — they're
  comparison baselines.
- **MiniSat-style literal encoding**: signed DIMACS lits convert to
  unsigned `lit = 2*var + sign` for O(1) watch indexing. Conversion is
  hot — `lib/solver.eigs`'s inline pattern is load-bearing.
- **CDCL state lives in stdlib integer vectors** (reason, level,
  phase, heap-position) — not generic lists. This was a deliberate
  choice driven by `--copy-bench` / `--storage-bench` evidence.
- **Clause-store adapter** (solver-local) sits beside the
  list-of-lists representation. `--storage-bench` compares them.
- **Compaction modes**: deferred (default) vs lazy
  (no-physical-compaction) — `--copy-bench` reports both so the
  tradeoff is visible.

## Hard-won rules

- **Don't bypass an EigenScript gap silently.** If a workaround would
  help, keep both paths and let the bench compare them. The data
  decides whether it becomes a root, a library, or stays local.
- **Hoist hot-path globals to function locals** so the v0.12.0+ JIT's
  inline caches fire (the `Inline tiny accessors` commit pattern).
- **n=5 for any perf claim.** Trend logs help — `run_trends.sh evidence`
  emits a compact summary line for paste-into-commit-msg style
  comparisons. **This is a wall-time rule, not a counter rule.** The solver
  is deterministic: conflicts, resolutions, learnts, peak_learnts and
  max_level are byte-identical across runs of the same input and policy
  (verified). Claims about *counters* need n=1; re-running them five times
  is wasted budget.
- **CDCL on UNSAT emits a resolution refutation**, so `resolutions` /
  `learnt_lits` are proof-size measurements, not just search telemetry, and
  the restart policy is not only a perf knob — CDCL *with* restarts
  p-simulates general resolution while without them it is weaker. Changing
  restart behavior changes which proof system is being measured.
- **Never gate a DRAT check on grepping `s VERIFIED`.** drat-trim prefixes
  that line with a carriage return, so `grep "^s VERIFIED"` never matches
  and the check passes unconditionally. Gate on the exit code (0 verified,
  1 not verified), and keep the planted-fault case in
  `run_proof_check.sh` — it is what proves the checker is gating at all.
- **`xor_triangle_case` is the easy XOR regime**, not a hardness probe: it is
  SAT and closes with zero conflicts. The hard parity family is
  `tseitin_torus_case` (odd charge). Keep both — the matched odd/even pair at
  the same size is the control showing the blowup is the parity obstruction
  and not the encoding.
- **Pigeonhole and complete-graph coloring are the same family.** k(n+1) with
  n colors is pigeonhole relabelled; `--proof-bench` shows them producing
  byte-identical size/space/depth triples. A change that helps only these two
  is exploiting counting structure — check it against Tseitin before
  believing it generalizes.
- **Don't add a "true third-party" CNF file** unless its provenance
  and size are routine-validation friendly. The vendored structural
  corpus is the bar.

## Solver correctness: what actually gates it

- **`--proof` + drat-trim is the only thing that catches unsound search.** It
  found a real soundness bug on 2026-07-30 (see below) that every assertion in
  the suite missed, because the *answer* was still UNSAT — pigeonhole is
  unsatisfiable either way. A correct verdict reached by unsound reasoning is
  invisible to a status assertion.
- **`--model` emits DIMACS v-lines** so a SAT answer is externally checkable
  too. Without it only UNSAT had an oracle.
- **`tests/fuzz_differential.py`** — random instances across six shape families
  (incl. tautological clauses, duplicate literals, unit-heavy, unused vars),
  all four solver paths must agree, SAT models checked, UNSAT proofs
  drat-trim'd. **`tests/fuzz_policy.py`** — the same oracle across compaction /
  restart / phase policies on conflict-rich instances. Run both after any
  change to propagation, conflict analysis, reduction or compaction.
- **Small instances do not exercise the hard code.** 0 of 180 random instances
  reached compaction; 4 reached clause-DB reduction. Reaching compaction needs
  `--compact-policy eager` plus a few hundred conflicts. Any test that matters
  for reduction/compaction must say so explicitly.
- **`clause_locked` must scan the whole clause** (fixed 2026-07-30). It checked
  position 0, which is wrong here: unlike MiniSat this solver never swaps
  literals into slots 0/1, it tracks watch POSITIONS in `watch_a`/`watch_b`,
  propagation moves them to arbitrary indices, and `rebuild_watches` resets
  them to 0/1 regardless of which literal is asserting. So a learnt clause
  still serving as a reason looked unlocked, got deleted, and the next
  compaction remapped `state.reason[v]` to -1 — after which conflict analysis
  reads an implied literal as a decision and can learn an unsound clause.
  drat-trim REJECTED the resulting refutations. Regression:
  `tests/fixtures/pigeonhole_6_5.cnf` under eager+luby in `run_proof_check.sh`.
- **Counters banked before 2026-07-30 came from the buggy solver and shift
  under the fix** — more clauses are correctly kept locked, so the search
  differs. Tseitin 3x3 went 673 -> 619 learnt clauses. Re-measure before
  comparing anything to a pre-fix number.

## Proof complexity surface

The solver doubles as a proof-complexity instrument, because a CDCL refutation
*is* a resolution refutation:

- `--cdcl --proof FILE` writes a DRAT refutation; `drat-trim` verifies it.
  This is the only external oracle the UNSAT path has ever had — before it,
  an over-pruning bug reported UNSAT and every assertion still passed.
- `--proof-bench` reports size / space / depth per policy per family.
- The two UNSAT families are hard for *different* reasons: pigeonhole by
  counting (Haken 1985, 2^Omega(n)) and Tseitin by parity plus graph expansion
  (Urquhart 1987, 2^Omega(min(rows,cols))). Both must blow up exponentially;
  a ladder that comes back polynomial means the generator or the counters
  are broken, not that the theorem is wrong. That makes the bench
  self-validating in the way a planted fault validates a checker.
- Measured on this box: pigeonhole resolutions 39 -> 210 -> 1276 -> 12397 for
  n = 3..6 (x5.4, x6.1, x9.7, multiplier rising).
- **Tseitin closed measurements** (ladder run 2026-07-29,
  `benchmarks/TSEITIN_LADDER.md` is the record of record): 3x3 = 1,974
  resolutions (1.7s), 4x4 = 95,516 (429s), 4x5 = 551,098 (6,285s). 5x5 is out
  of reach here — two attempts totalling 14.5h reached only 1,549,543 without
  closing.
- **RETRACTED 2026-07-30 (adversarial review): there is no measured "two axis"
  separation.** An earlier version of this file claimed the expansion axis was
  8.4x steeper than the fixed-expansion axis and told you to scale the square
  dimension for hardness. That compared steps with unequal variable increments
  (3x3->4x4 adds 14 vars, 4x4->4x5 adds 8). Normalised per variable the growth
  is 1.319x, 1.245x, then `>=`1.109x — *decreasing*, and indifferent to which
  axis moved. Worse, the only clean single-dimension expansion step in the data
  (4x5 -> 5x5) is `>=`2.81x, which is *lower* than the flat step's 5.77x. The
  size-matched control that could settle it is **4x6 (48 vars, min=4) against
  5x5 (50 vars, min=5)** — and 4x6 was killed mid-run as "more of the same on
  the cheap axis", destroying the control. Do not repeat the claim without
  running 4x6.
- **Do not read `resolutions` / `peak_learnts` as a size-vs-space finding.**
  That ratio climbs by construction: `resolutions` is cumulative and unbounded
  while `peak_learnts` is pinned to the reduction schedule
  (`learnt_limit` starts at 4 and grows +2 per reduce run, so
  `peak_learnts ~= 4 + 2 * reduce_runs`). It measures the DB policy, not the
  formula family. A real size-vs-space result needs proof space for a *fixed*
  refutation, not a policy-capped high-water mark.
- **`count_active_learnts` is O(total clauses) and runs every conflict** (via
  `reduce_learnt_db`), but it is NOT the bottleneck: replacing it with an
  incrementally maintained counter bought only **4.4%** at 4x4 (429.2s ->
  410.4s, counters byte-identical). Do not "fix" it — the incremental version
  adds a state invariant that only `build_cdcl_state` maintains, and the
  hand-built `reduce_state` in `tests/test_solver.eigs` breaks immediately
  ("cannot compare none and num"). `count_active_learnts` derives from the
  arrays and needs no invariant; that robustness is worth 4%.
- **Long-run caps need margin, not point estimates.** 4x5 closed at 6,285s
  against a 5,400s cap — missed by under 15 minutes and banked nothing but a
  bound. A case that nearly closes banks exactly as little as one that never
  started. Prefer one case with generous headroom over several that each nearly
  finish.

Honest ceiling: measurement bounds proof size from *above*. Every result that
matters in proof complexity is a lower bound, and those are theorems. This
instrument validates that a family behaves as theory predicts and falsifies
"that family is easy" claims — it does not settle anything.

## Current state

CDCL working with watched literals, learnt-clause activity and
locked-clause protection, lazy + eager reduction, geometric and Luby
restarts, saved-phase polarity, MiniSat-style activity heap.
LBD-based clause management (Glucose-style) landed via PR #43.
Latest commits are the budgeted, resumable CDCL sessions
(`cdcl_begin`/`cdcl_step`) with `lib/solver.eigs` made composition-free
(the one-shot solve is re-derived from them), landed via PR #56. The
benchmark surface is mature — most current work is data-driven
decisions out of `docs/EIGENSCRIPT_FEEDBACK.md`. Verified green on
EigenScript v0.34.0 (correctness suite only; not an `n=5` perf claim).

## Gotchas

- `gmon.out` is gprof output from past profiling — don't commit it.
- `benchmarks/runs/*` is ignored on purpose (machine-local trend logs).
- The bench surface is large; don't add modes silently — update the
  README mode table when adding one, and decide up-front which
  pressure surface it isolates.
- Don't compare bench numbers across hosts; the README's pressure
  inventory is meaningful, the absolute milliseconds are not.
