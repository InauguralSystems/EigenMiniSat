# EigenScript Feedback

This ledger turns EigenMiniSat benchmark pressure into decisions. The point is
to avoid downstream workarounds when the root language or standard library is
the right place to fix a repeated cost.

## Decision Rules

- Root language/runtime: semantics or primitives that affect many EigenScript
  programs, not only SAT solving.
- Standard library: reusable data structures or parsing helpers that can be
  written in EigenScript but should not be hand-rolled in every project.
- EigenMiniSat-local: solver representation choices that still need a local
  prototype before they justify root support.
- Stress-test discipline: do not hide repeated language pressure with local
  bypasses in the main stress path. Use comparison benchmarks to isolate a
  possible fix, then address the gap as a library or at EigenScript root.

## Current Decisions

### Local Binding Form

Classification: merged root language fix.

Evidence: CDCL option handling exposed outward assignment hazards when generic
helper-local names collided with outer bindings. EigenScript PR #117 adds
`local name is expr` so a helper can bind in the active evaluator scope without
mutating a parent binding.

Next action: keep the EigenMiniSat CDCL stress path on `local` for genuine
function-local temporaries, and keep sentinel tests that prove common solver
names like `store`, `state`, `level`, and `analysis` do not mutate outer scope.
Do not reintroduce name-avoidance conventions as a substitute for the root
language feature.

### Token Spans And Diagnostic Tokenizer

Classification: root runtime path active.

Evidence: `--scan-parse-bench`, `--corpus-bench`, and `--diagnostic-bench`
show that the fast `scan_ints` path is useful for validated input, while full
DIMACS diagnostics still need parser-local token strings, line tracking, and
error text assembly. EigenScript PR #118 adds `scan_tokens`, a C-backed
whitespace token scanner returning `[text, line, col, start, end]` rows.
EigenScript PR #122 adds `scan_int_tokens`, which keeps that row shape and
appends integer validity/value metadata. EigenMiniSat uses that for the
token-span DIMACS parser and emits `parse tokens`, `diagnostic tokens`, and
`corpus parse tokens` rows beside split, hand-scan, and integer-scan paths.

Next action: compare `scan_int_tokens` against split/scan diagnostics and the
validated `scan_ints` fast path on larger corpus runs before asking for a
domain-specific parser or richer recoverable-error API.

### String Builder Or Buffered Text Output

Classification: root runtime consumed; standard-library API retained.

Evidence: generated DIMACS fixtures and malformed diagnostic cases build text
with repeated string concatenation. EigenScript PR #119 added the shared
`lib/text_builder.eigs` API, and EigenScript PR #123 moved the implementation
onto the native `VAL_TEXT_BUILDER` root runtime value while keeping that module
load-compatible. EigenMiniSat uses that builder for the main generated-DIMACS
and diagnostic text paths while `--parse-bench` keeps concat generation rows as
comparison evidence. The `evidence` profile runs that bounded parse benchmark
so `text_build_totals`, `text_builder_overhead_ms`, and
`text_builder_native_win` stay visible in the same decision summary as parser,
storage, and copy pressure. A size-1 evidence run with the merged native
builder reported `generated_cases=5`, `concat_ms=2.198`,
`text_builder_ms=1.231`, `text_builder_overhead_ms=-0.967`, and emitted
`decision_candidate area=text_builder scope=root_runtime_consumed`. This is not
solver-specific; it affects any EigenScript program producing structured text.

Next action: keep the native builder in the stress path, measure larger
generated fixtures, and only ask for deeper text streaming or buffer primitives
if the root-backed builder still shows pressure.

### Compact Mutable Integer Vectors

Classification: standard-library path active; root runtime still under
measurement.

Evidence: assignments, encoded literals, watch lists, heap positions, clause
metadata, reason references, and trail levels are all integer-heavy arrays.
Persistent rollback and CDCL heap churn repeatedly rebuild list prefixes or
mutate list slots.

Current path: EigenScript now exposes `lib/int_vector.eigs` over root buffers,
and EigenMiniSat uses it for CDCL reason references, decision levels, saved
phase values, heap positions, and conflict-analysis seen marks.

Next action: measure the int-vector-backed CDCL path before asking for deeper
root storage. Remaining pressure should distinguish fixed integer state from
growable clause metadata and clause-arena storage.

### Hot Helper Calls In Tight Loops

Classification: root fix merged — EigenScript #366, fixed by PR #367
(2026-07-03, on EigenScript main; unreleased, so the v0.23.0 CI pin does
not see it until the next release).

Resolution: EigenScript now flags "leaf accessor" chunks at compile time
(single pure expression over params — field gets, list/buffer index gets,
numeric arithmetic) and runs exactly-fed calls framelessly against the
caller's stack, bailing to the generic call path on any surprise so errors
and tracebacks stay identical. Re-measured against the merged fix (n=5,
size 3): helper-call scan overhead median `1.417ms -> 0.536ms` (-62%), and
helper-mediated watch seeding now beats its inline comparison row. On the
upstream micro-repro the per-call overhead fell ~198ns -> ~40ns. Residual
helper cost here is mostly `clause_store_len`, whose `len of` body contains
a call and stays deliberately on the generic path.

Evidence: `--storage-bench` reports inline-vs-helper clause-store overhead
for the same flat clause-store shape. Confirmed with n=5 on v0.23.0
(2026-07-03, cc9f790): at `--size 3`, helper-call scan overhead has median
`1.417ms` (range 1.15–1.54) beside `1.981ms` data-shape overhead — roughly
70% added on top of identical inline access. At `--size 2` the effect is
below the dev box's ~±1ms noise floor (median `-0.090ms`), so only larger
cases show it; single runs at small sizes are misleading in both directions.
A standalone 30-line micro-repro (200K-iteration accessor loop) isolates the
cost at ~185ns per helper call, +44% wall-clock versus the inline loop, with
tight n=5 variance. This is a call-dispatch cost, not a global-hoist issue —
the operands are already function locals. Not SAT-specific: small helper
functions wrapping list/dict field access are a common abstraction shape in
EigenScript programs.

Pinned-runtime numbers (v0.24.0, 2026-07-03, n=5 `--storage-bench --size 3`
against the tagged release build): helper_scan_overhead per case —
chain-unsat-240 median **0.616ms** (range 0.539–0.691; this case carries the
signal), grid-unsat-8x8 −0.056, pigeonhole-6-5 −0.088, wide-120-12-60
+0.001 (all three inside the dev box's noise floor); sum-across-cases
median 0.456ms (range 0.317–0.527). Helper-mediated watch seeding still
beats its inline row (summed watch overhead median −0.94ms). Consistent
with the pre-release measurement of the merged fix (0.536ms) — the
leaf-accessor fast path holds at the pin.

Next action: none — resolved and pinned. Keep helper-mediated solver paths
as the stress surface; they are the regression canary for the upstream
fast path. Do not replace the main solver path with direct field access.

### Priority Queue

Classification: standard-library candidate.

Evidence: CDCL already carries a binary heap for variable ordering and reports
`heap_pops`, `heap_inserts`, and `heap_skips`. The heap behavior is reusable,
but EigenMiniSat still needs solver-specific activity comparison and assignment
filtering.

Next action: leave the current heap local until one more non-solver repo needs
the same structure. If it repeats in DMG, Tidepool, or iLambdaAi, promote a
small priority-queue library with custom comparison hooks.

### Clause Arena And Clause References

Classification: EigenMiniSat-local prototype active.

Evidence: `--storage-bench` measures flat arena build, direct scan,
adapter-mediated lookup, CDCL-style watch seeding, reconstruction, deletion
compaction, and synthetic reason remapping. Metadata churn also amplifies
reference remapping, locked-clause scans, watch rebuilds, and trail replay. The
CDCL path now uses the clause-store adapter for propagation, conflict analysis,
learnt insertion, reduction scans, and deleted-clause compaction. It also
reports store-to-list copies, store-native conflict-analysis scans, remaining
analysis rebuild literals, deferred compaction checks, pending deleted clauses,
targeted watch-detach scans/removals, and direct compaction-copy literals.
`--copy-bench` now puts those counters under conflict-heavy generated cases with
tight restart and polarity policies, with lazy no-physical-compaction variants
beside the default deferred policy and larger evidence cases that emit
deferred-vs-lazy delta summaries. Store-native conflict analysis removes the
hot list rebuild path locally. Deferred physical compaction removes the hot
clause-copy path in small conflict cases; targeted watch detaching keeps the
solve path from shifting that cost into full watch-table pruning, full watch
rebuilds, or trail replays until larger cases cross the compaction thresholds.
The lazy policy is an evidence knob for that larger-case tradeoff, not a root
language ask by itself. The
copy-pressure cases also exposed a watched-propagation invariant bug: a
conflict return must preserve the unprocessed tail of the current watch bucket.
That is an EigenMiniSat-local algorithmic correction, not a root-language ask.
The evidence is strong that the solver wants
clause-reference discipline, but not yet strong enough to demand a root arena
primitive.

Next action: the deferred-vs-lazy decision is closed (see below). Remaining
open pressure in this area is split: the helper-call half is now upstream
(EigenScript #366, see "Hot Helper Calls In Tight Loops"), and the data-shape
half (compact vectors / arena references, ~2.0ms of the size-3 adapter scan
overhead) stays an EigenMiniSat-local prototype. Revisit a root arena ask only
if a case family shows compaction or store traffic dominating conflict
analysis, which no current case does.

Decision (2026-07-03, v0.23.0, cc9f790): **deferred compaction stays the
default; no root arena/reference request from compaction pressure.** Evidence
runs at sizes 2 and 3 settled the deferred-vs-lazy question on wall clock,
against the direction the counter "savings" suggested. Lazy avoids all
compaction copies (14,092 literals, 16 watch rebuilds, 380 replays saved at
size 3) but is slower in all six measured policy/case pairs: +1.3–3.2% at
size 2, compounding to 2.4×–5.3× at size 3 (pigeonhole-7-6-larger: deferred
18.6s/30.9s vs lazy 45.0s/163.9s), because 1,990 pending deleted clauses
bloat the store and propagation pays the skip on every encounter. Two
supporting facts: watch-detach scan debt was zero under both policies at both
sizes, so targeted detaching is not a cost center; and compaction-copy
literals on the largest case (~6.6K) are dwarfed by conflict-analysis literal
traffic (~97K), so compaction is not the dominant copy pressure anyway. The
old size-2 checkpoint (3,820 avoided literals / 780 detach scans, recorded on
an earlier runtime and host) is superseded. The lazy policy remains a
comparison knob, and `physical_compaction_pressure` / `lazy_debt_pressure`
flags will stay active in summaries by construction (they are zero-threshold)
— they no longer indicate an open decision.

The same checkpoint also keeps the other pressure surfaces visible: generated
parse totals are `split=36.006ms`, `scan=45.676ms`, `scan_ints=5.328ms`;
corpus parse totals are `split=26.689ms`, `scan=37.823ms`,
`scan_ints=4.708ms`; diagnostic scan is slower than split/trim on 20 malformed
errors; storage adapter scans total `9.816ms` versus `5.849ms` flat scans; and
the storage overhead summary breaks that into `3.967ms` adapter scan overhead,
`2.559ms` adapter watch-seeding overhead, `0.649ms` adapter compaction
overhead, and `1.639ms` flat-vs-list compaction overhead. Metadata churn
reports 996 compacted literals, 5 watch rebuilds, 227 watch detaches, and 168
trail replays. These activate diagnostic-tokenizer, validated-scan,
storage-adapter, and compact-vector pressure flags without turning them into
final root requests.

A fresh size-1 inline-overhead check reports `inline_rows=4`, with storage
adapter scan overhead split into `1.240ms` inline data-shape overhead and
`0.860ms` helper-call overhead. Watch seeding similarly splits into `0.136ms`
inline overhead and `0.239ms` helper-call overhead. This keeps the
clause-store adapter decision from collapsing into a vague arena request: part
of the pressure is now a root/compiler candidate around hot helper calls, and
part remains data-shape pressure for compact vectors or arena references.

### In-Place List Truncation

Classification: merged root builtin.

Evidence: CDCL trail backjumps, trail_lim truncation, and heap pop all
rebuilt lists via `copy_prefix`, allocating a fresh list each call. The C
list struct already has `count` and `capacity`, so truncation is just
`count = new_len` plus decrefing removed items. EigenScript PR #124 adds
`list_truncate of [list, new_len]` as a root builtin. EigenMiniSat now
uses it at 5 call sites. This is not solver-specific; any list-heavy
program benefits from in-place truncation instead of copy-and-replace.

Next action: consumed. Monitor whether `list_resize` (grow + fill) or
`list_splice` become future pressure points.

### Sort By Key Function

Classification: merged root builtin.

Evidence: learnt-clause reduction called `find_low_activity_learnt` in a
loop — O(active x store_len). Needed O(n log n) sort by a key function.
The pure-EigenScript `sort_by` in `lib/sort.eigs` used insertion sort
(O(n^2)). EigenScript PR #124 adds a C-backed `sort_by of [list, key_fn]`
that evaluates the key function once per element and uses `qsort` with
stable tiebreak by original index. EigenMiniSat now uses it for
single-pass learnt-clause reduction. This is not solver-specific; any
program needing sort-by-computed-key benefits.

Next action: consumed. The pure-EigenScript `sort_by` has been removed
from `lib/sort.eigs` to avoid shadowing.

### Bitwise Integer Operations

Classification: root runtime candidate, lower priority.

Evidence: MiniSat-style literal indexes are encoded as `var * 2 + sign`, with
negation toggling adjacent indexes. Today arithmetic helpers are sufficient,
but bit operations would make encoded-literal churn cheaper and clearer.

Next action: defer until larger watch/propagation cases show this cost clearly.
Compact integer vectors and token spans are higher-value root candidates today.

## Near-Term EigenMiniSat Work

- Keep benchmarks as the evidence surface, not just performance demos.
- The `--copy-bench` deferred-vs-lazy decision is closed (2026-07-03):
  deferred compaction stays the solver default on wall-clock evidence at
  sizes 2–3. Re-open only if a new case family reverses the direction.
- Storage overhead is now split by owner: helper-call dispatch was fixed
  upstream (EigenScript #366 / PR #367, −62% measured here); data-shape
  pressure stays local. Measure inline-vs-helper only at `--size 3` or larger
  with n=5 — size-2 deltas sit inside the noise floor.
- Preserve helper-mediated hot paths when they are the language stress surface;
  use inline variants for measurement, not as a workaround.
- Track `int_vector_state_active` in evidence summaries before expanding
  compact vectors into more solver state.
- Use `benchmarks/run_trends.sh evidence` for bounded larger-case decision
  snapshots before opening root or stdlib issues. Use
  `benchmarks/summarize_trend.sh` when comparing saved logs. Its
  `decision_candidate` rows are the current scoped next actions, not final
  EigenScript requests.
- Deferred/lazy compaction is settled as algorithm-local: lazy loses on wall
  clock in every measured pair and targeted watch-detach churn never
  materialized (zero detach-scan debt at both sizes).
- Expand the checked-in corpus only with small, provenance-clear cases before
  relying on any single generated family.
- Keep root issues in EigenScript, but do not block EigenMiniSat-local
  experiments that are needed to identify the right root abstraction.
