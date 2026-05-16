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
analysis rebuild literals, and direct compaction-copy literals. `--copy-bench`
now puts those counters under conflict-heavy generated cases with tight restart
and polarity policies. Store-native conflict analysis removes the hot list
rebuild path locally while keeping the evidence surface for remaining
compaction-copy pressure. The evidence is strong that the solver wants
clause-reference discipline, but not yet strong enough to demand a root arena
primitive.

Next action: grow copy-pressure cases and use the native analysis counters to
decide whether the remaining compaction-copy pressure belongs in EigenMiniSat, a
reusable library, or EigenScript root. The adapter preserves signed DIMACS
literals at the boundary and should prove whether arena references simplify
conflict analysis and database reduction.

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
- Expand the checked-in corpus with larger real-shaped CNF cases before relying
  on any single generated family.
- Keep root issues in EigenScript, but do not block EigenMiniSat-local
  experiments that are needed to identify the right root abstraction.
