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

Classification: root language fix in progress.

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

Classification: root or standard-library candidate.

Evidence: `--scan-parse-bench`, `--corpus-bench`, and `--diagnostic-bench`
show that the fast `scan_ints` path is useful for validated input, while full
DIMACS diagnostics still need parser-local token strings, line tracking, and
error text assembly. The character scanner shares diagnostics with split/trim
but pays repeated substring and token concatenation costs.

Next action: keep `scan_ints` as the numeric fast path. Add root or stdlib
token-span support only if larger corpora keep diagnostic overhead visible.
The useful abstraction is not just integer scanning; it is token text, span,
line, and recoverable error reporting.

### String Builder Or Buffered Text Output

Classification: standard-library candidate.

Evidence: generated DIMACS fixtures and malformed diagnostic cases build text
with repeated string concatenation. This is not solver-specific; it affects any
EigenScript program producing structured text.

Next action: keep measuring generated fixture and diagnostic text construction
before adding a project-local builder. If the pressure grows, prefer a stdlib
builder/buffer API over a MiniSat-only helper.

### Compact Mutable Integer Vectors

Classification: root runtime or standard-library candidate.

Evidence: assignments, encoded literals, watch lists, heap positions, clause
metadata, reason references, and trail levels are all integer-heavy arrays.
Persistent rollback and CDCL heap churn repeatedly rebuild list prefixes or
mutate list slots.

Next action: continue collecting evidence through solver counters. A compact
mutable vector API is broader than SAT solving and should be considered before
EigenMiniSat grows many local list wrappers.

### Hot Helper Calls In Tight Loops

Classification: root/compiler candidate.

Evidence: `--storage-bench` now reports inline-vs-helper clause-store overhead
for the same flat clause-store shape. A size-1 evidence run with
`inline_rows=4` split adapter scan overhead into `1.240ms` data-shape overhead
and `0.860ms` helper-call overhead. Watch seeding split into `0.136ms` inline
overhead and `0.239ms` helper-call overhead. This is not SAT-specific: small
helper functions wrapping list/dict field access are a common abstraction shape
in EigenScript programs.

Next action: keep helper-mediated solver paths as the stress surface. Use the
inline comparison rows as evidence for EigenScript compiler/root work such as
function inlining, call specialization, or field-access lowering. Do not
replace the main solver path with direct field access just to bypass the
pressure.

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

Next action: grow copy-pressure cases and use the deferred/lazy compaction
counters to decide whether remaining targeted watch-detach and physical
compaction pressure belongs in EigenMiniSat, a reusable library, or EigenScript
root. Use the `evidence` trend profile and the small vendored structural corpus
to keep runs self-contained while collecting that evidence. The adapter
preserves signed DIMACS literals at the boundary and should prove whether arena
references simplify conflict analysis and database reduction.

Current evidence checkpoint: `benchmarks/run_trends.sh evidence 2` shows the
larger pigeonhole and graph-coloring cases crossing the physical-compaction
threshold. The summarized copy deltas report 3820 avoided compaction-copy
literals, 8 avoided watch rebuilds, and 146 avoided trail replays under lazy
compaction, while also adding 498 pending deleted clauses and 780 watch-detach
scans. That keeps both `physical_compaction_pressure` and `lazy_debt_pressure`
active; this is still evidence for a solver/storage decision, not yet a root
EigenScript arena request.

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

### Bitwise Integer Operations

Classification: root runtime candidate, lower priority.

Evidence: MiniSat-style literal indexes are encoded as `var * 2 + sign`, with
negation toggling adjacent indexes. Today arithmetic helpers are sufficient,
but bit operations would make encoded-literal churn cheaper and clearer.

Next action: defer until larger watch/propagation cases show this cost clearly.
Compact integer vectors and token spans are higher-value root candidates today.

## Near-Term EigenMiniSat Work

- Keep benchmarks as the evidence surface, not just performance demos.
- Use `--copy-bench` counters to decide whether remaining clause-reference
  pressure should stay local, become a library, or move to root.
- Use storage overhead rows to separate adapter lookup, watch seeding, and
  compaction costs before asking EigenScript for root arena/reference support.
  Prefer new logs with `inline_rows > 0` when deciding whether the pressure is
  data shape, helper-call overhead, or both.
- Preserve helper-mediated hot paths when they are the language stress surface;
  use inline variants for measurement, not as a workaround.
- Use `benchmarks/run_trends.sh evidence` for bounded larger-case decision
  snapshots before opening root or stdlib issues. Use
  `benchmarks/summarize_trend.sh` when comparing saved logs. Its
  `decision_candidate` rows are the current scoped next actions, not final
  EigenScript requests.
- Treat deferred/lazy compaction as algorithm-local unless larger cases show
  targeted watch-detach or compaction-copy churn needs a reusable primitive.
- Expand the checked-in corpus only with small, provenance-clear cases before
  relying on any single generated family.
- Keep root issues in EigenScript, but do not block EigenMiniSat-local
  experiments that are needed to identify the right root abstraction.
