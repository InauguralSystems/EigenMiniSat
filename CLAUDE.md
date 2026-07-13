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
CI builds and tests against EigenScript **v0.30.0** (pinned in
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

# Trend logs into benchmarks/runs/ (ignored)
./benchmarks/run_trends.sh quick    1   # quick profile, size 1
./benchmarks/run_trends.sh evidence 2 /tmp/eigenminisat-evidence.log  # bounded larger-case decisions
./benchmarks/run_trends.sh full         # every bench mode
./benchmarks/summarize_trend.sh /tmp/eigenminisat-evidence.log
```

The bench modes (`--bench`, `--restart-bench`, `--phase-bench`,
`--copy-bench`, `--storage-bench`, `--metadata-bench`, `--parse-bench`,
`--scan-parse-bench`, `--diagnostic-bench`, `--file-bench`,
`--corpus-bench`, `--heuristic-bench`, `--random-bench`) each isolate a specific
pressure surface — see `README.md` for the per-mode counter list.

## Layout

| Path | Role |
|---|---|
| `minisat.eigs` | CLI entry — dispatches solver / bench modes |
| `lib/solver.eigs` | DPLL / watched / persistent / CDCL solver paths |
| `lib/dimacs.eigs` | DIMACS parsers (split/trim, char-scan, token-span, `scan_ints`) |
| `lib/bench.eigs` | Generated case families + bench harnesses |
| `tests/fixtures/*.cnf` | Hand-written small cases |
| `tests/corpus/` | Manifest-driven CNF corpus (graph color, pigeonhole, parity, etc.) |
| `tests/corpus/vendor/` | Small vendored structural corpus + provenance |
| `tests/test_solver.eigs` | Correctness assertions (run by `run_smoke.sh`) |
| `benchmarks/run_trends.sh` | Profile runner (`quick` / `evidence` / `full`) |
| `benchmarks/runs/` | Trend logs (ignored — machine-local) |
| `docs/ROADMAP.md` | What's next in the solver |
| `docs/EIGENSCRIPT_FEEDBACK.md` | Root/stdlib/local decisions by pressure point |
| `GAPS.md` | Per-friction ledger (same format as Tidepool / EigenRegex) |
| `BASELINE.md` | Recorded timings |

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
  comparisons.
- **Don't add a "true third-party" CNF file** unless its provenance
  and size are routine-validation friendly. The vendored structural
  corpus is the bar.

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
EigenScript v0.30.0 (correctness suite only; not an `n=5` perf claim).

## Gotchas

- `gmon.out` is gprof output from past profiling — don't commit it.
- `benchmarks/runs/*` is ignored on purpose (machine-local trend logs).
- The bench surface is large; don't add modes silently — update the
  README mode table when adding one, and decide up-front which
  pressure surface it isolates.
- Don't compare bench numbers across hosts; the README's pressure
  inventory is meaningful, the absolute milliseconds are not.
