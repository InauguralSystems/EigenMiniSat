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
bench scan chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=3.45968
bench watched chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.06759
bench persistent chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.05893
bench cdcl chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=40 phase_flips=0 phase_pos=0 phase_neg=0 ms=3.47958
bench scan chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.38461
bench watched chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.65979
bench persistent chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=1.64792
bench cdcl chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=40 phase_flips=20 phase_pos=0 phase_neg=0 ms=3.15873
bench scan pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=12.673
bench watched pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=8.17323
bench persistent pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=3.19372
bench cdcl pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 backjumps=7 resolutions=39 bumps=18 decays=7 heap_pops=17 heap_inserts=14 heap_skips=7 clause_allocs=41 learnt_allocs=7 learnt_lits=18 clause_bumps=14 clause_decays=7 reduce_runs=1 reduce_scans=2 learnt_deleted=2 locked_kept=4 deleted_watch_skips=0 active_learnts=5 compact_runs=1 compact_removed=2 compact_kept=37 watch_rebuilds=1 compact_replays=7 restarts=1 restart_cancels=4 restart_budget=6 phase_saves=74 phase_flips=44 phase_pos=2 phase_neg=8 ms=11.029
bench scan xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=5.40114
bench watched xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=5.70935
bench persistent xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=3.09105
bench cdcl xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=11 heap_inserts=0 heap_skips=0 clause_allocs=16 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=11 phase_flips=0 phase_pos=11 phase_neg=0 ms=3.3311
```

The persistent path keeps watch state across DPLL nodes. It improves branchier
cases here, but chain cases expose rollback/list-truncation overhead. That is a
useful EigenScript pressure point for compact mutable vectors or list truncation.
The CDCL path shows actual learning on the pigeonhole case. The activity heap
now exposes pop/reinsert/skip churn in addition to list-heavy
conflict-resolution pressure. Learnt metadata and lazy reduction expose clause
allocation, locked-clause retention, deletion, and watch-list cleanup pressure.
Restart and phase counters now expose root-level cancellation, saved polarity,
and positive/negative decision splits.
Compaction counters show that `pigeonhole-4-3` now physically removes deleted
learnt clauses and rebuilds watches instead of carrying deleted watch entries.

Parse benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --parse-bench --size 2
```

Result:

```text
parse fixture grid-sat-6x6: text_len=559 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ms=2.24255
fixture cdcl grid-sat-6x6: status=SAT decisions=0 propagations=36 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=8.61288
parse fixture grid-unsat-6x6: text_len=562 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ms=2.09651
fixture cdcl grid-unsat-6x6: status=UNSAT decisions=0 propagations=36 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=3.79157
parse fixture chain-sat-120: text_len=1145 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ms=3.97127
fixture cdcl chain-sat-120: status=SAT decisions=0 propagations=120 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=12.4941
parse fixture chain-unsat-120: text_len=1148 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ms=3.8202
fixture cdcl chain-unsat-120: status=UNSAT decisions=0 propagations=120 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=9.52976
parse fixture wide-48-8-20: text_len=575 vars=48 clauses=20 declared_vars=48 declared_clauses=20 ms=1.51745
fixture cdcl wide-48-8-20: status=SAT decisions=41 propagations=0 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=11.4635
```

File-backed benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --file-bench --size 2
```

Result:

```text
file fixture grid-sat-6x6: text_len=559 wrote=1 removed=1 vars=36 clauses=62 declared_vars=36 declared_clauses=62 write_ms=0.21658 parse_file_ms=2.16879
file cdcl grid-sat-6x6: status=SAT decisions=0 propagations=36 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=4.73778
file fixture grid-unsat-6x6: text_len=562 wrote=1 removed=1 vars=36 clauses=62 declared_vars=36 declared_clauses=62 write_ms=0.2295 parse_file_ms=2.12466
file cdcl grid-unsat-6x6: status=UNSAT decisions=0 propagations=36 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=4.08448
file fixture chain-sat-120: text_len=1145 wrote=1 removed=1 vars=120 clauses=121 declared_vars=120 declared_clauses=121 write_ms=0.205195 parse_file_ms=5.20998
file cdcl chain-sat-120: status=SAT decisions=0 propagations=120 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=14.5854
file fixture chain-unsat-120: text_len=1148 wrote=1 removed=1 vars=120 clauses=121 declared_vars=120 declared_clauses=121 write_ms=0.263583 parse_file_ms=5.0476
file cdcl chain-unsat-120: status=UNSAT decisions=0 propagations=120 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=10.6663
file fixture wide-48-8-20: text_len=575 wrote=1 removed=1 vars=48 clauses=20 declared_vars=48 declared_clauses=20 write_ms=0.292288 parse_file_ms=1.7767
file cdcl wide-48-8-20: status=SAT decisions=41 propagations=0 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=8.94931
```

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
