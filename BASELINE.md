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
bench scan chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.92965
bench watched chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.29067
bench persistent chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.0912
bench cdcl chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 ms=3.70091
bench scan chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.38363
bench watched chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.69485
bench persistent chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.77789
bench cdcl chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 ms=3.50117
bench scan pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=12.3713
bench watched pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=8.21877
bench persistent pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=3.39012
bench cdcl pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=6 propagations=60 conflicts=7 learnts=6 backjumps=6 resolutions=36 bumps=15 decays=6 heap_pops=14 heap_inserts=9 heap_skips=8 clause_allocs=40 learnt_allocs=6 learnt_lits=15 clause_bumps=12 clause_decays=6 reduce_runs=1 reduce_scans=2 learnt_deleted=1 locked_kept=4 deleted_watch_skips=1 active_learnts=5 ms=9.6969
bench scan xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=7.54214
bench watched xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=6.51281
bench persistent xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=2.33809
bench cdcl xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=11 heap_inserts=0 heap_skips=0 clause_allocs=16 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 ms=2.91233
```

The persistent path keeps watch state across DPLL nodes. It improves branchier
cases here, but chain cases expose rollback/list-truncation overhead. That is a
useful EigenScript pressure point for compact mutable vectors or list truncation.
The CDCL path shows actual learning on the pigeonhole case. The activity heap
now exposes pop/reinsert/skip churn in addition to list-heavy
conflict-resolution pressure. Learnt metadata and lazy reduction expose clause
allocation, locked-clause retention, deletion, and watch-list cleanup pressure.

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
