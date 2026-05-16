# Baseline

Date: 2026-05-16

Machine context: constrained Gateway-era laptop. Use these as local trend
numbers, not universal performance claims.

Command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --bench --size 2
```

Result:

```text
bench scan chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.63876
bench watched chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.23913
bench persistent chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=1.98476
bench cdcl chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 backjumps=0 resolutions=0 ms=2.35981
bench scan chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.38028
bench watched chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=2.05803
bench persistent chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.64561
bench cdcl chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 backjumps=0 resolutions=0 ms=1.86652
bench scan pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=13.1913
bench watched pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=9.72644
bench persistent pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=3.48999
bench cdcl pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=5 propagations=48 conflicts=6 learnts=5 backjumps=5 resolutions=30 ms=6.11919
bench scan xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=5.34359
bench watched xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=7.0837
bench persistent xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=2.11439
bench cdcl xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 backjumps=0 resolutions=0 ms=2.18668
```

The persistent path keeps watch state across DPLL nodes. It improves branchier
cases here, but chain cases expose rollback/list-truncation overhead. That is a
useful EigenScript pressure point for compact mutable vectors or list truncation.
The CDCL path shows actual learning on the pigeonhole case and starts exposing
list-heavy conflict-resolution pressure.

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
