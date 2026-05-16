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

## Current Decisions

### Local Binding Form

Classification: root language candidate.

Evidence: CDCL option handling exposed outward assignment hazards when generic
helper-local names collided with outer bindings. EigenMiniSat now uses specific
local names, but that is a convention, not a durable language boundary.

Next action: EigenScript should consider an explicit local-only binding form or
a stricter assignment mode. Until then, EigenMiniSat should keep helper-local
names specific and avoid generic `cfg`, `state`, or `result` names in broad
scope.

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
- Use `benchmarks/run_trends.sh evidence` for bounded larger-case decision
  snapshots before opening root or stdlib issues. Use
  `benchmarks/summarize_trend.sh` when comparing saved logs.
- Treat deferred/lazy compaction as algorithm-local unless larger cases show
  targeted watch-detach or compaction-copy churn needs a reusable primitive.
- Expand the checked-in corpus only with small, provenance-clear cases before
  relying on any single generated family.
- Keep root issues in EigenScript, but do not block EigenMiniSat-local
  experiments that are needed to identify the right root abstraction.
