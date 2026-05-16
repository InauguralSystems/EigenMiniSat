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
bench scan chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=4.19352
bench watched chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=2.89948
bench persistent chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=3.72201
bench cdcl chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=40 phase_flips=0 phase_pos=0 phase_neg=0 ms=14.2035
bench scan chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=5.01534
bench watched chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=2.89585
bench persistent chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=2.00607
bench cdcl chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=0 heap_inserts=0 heap_skips=0 clause_allocs=41 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=40 phase_flips=20 phase_pos=0 phase_neg=0 ms=4.21335
bench scan pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=17.023
bench watched pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=12.2603
bench persistent pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=4.14721
bench cdcl pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 backjumps=7 resolutions=39 bumps=18 decays=7 heap_pops=17 heap_inserts=14 heap_skips=7 clause_allocs=41 learnt_allocs=7 learnt_lits=18 clause_bumps=14 clause_decays=7 reduce_runs=1 reduce_scans=2 learnt_deleted=2 locked_kept=4 deleted_watch_skips=0 active_learnts=5 compact_runs=1 compact_removed=2 compact_kept=37 watch_rebuilds=1 compact_replays=7 restarts=1 restart_cancels=4 restart_budget=6 phase_saves=74 phase_flips=44 phase_pos=2 phase_neg=8 ms=31.2688
bench scan xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=6.82306
bench watched xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=8.6891
bench persistent xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=6.13854
bench cdcl xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 backjumps=0 resolutions=0 bumps=0 decays=0 heap_pops=11 heap_inserts=0 heap_skips=0 clause_allocs=16 learnt_allocs=0 learnt_lits=0 clause_bumps=0 clause_decays=0 reduce_runs=0 reduce_scans=0 learnt_deleted=0 locked_kept=0 deleted_watch_skips=0 active_learnts=0 compact_runs=0 compact_removed=0 compact_kept=0 watch_rebuilds=0 compact_replays=0 restarts=0 restart_cancels=0 restart_budget=3 phase_saves=11 phase_flips=0 phase_pos=11 phase_neg=0 ms=3.32908
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
Watch-list indexes now use MiniSat-style encoded literal slots, which reduces
the table shape to the active `2 * nvars` literal domain while leaving signed
DIMACS literals at the solver boundary.

Restart benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --restart-bench --size 2
```

Result:

```text
restart geometric chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=7.36801
restart luby chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=10.1841
restart geometric chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=4.08667
restart luby chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=6.87912
restart geometric pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 restart_budget=6 restart_index=1 restart_cancels=4 compact_runs=1 ms=14.5979
restart luby pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 restart_budget=3 restart_index=1 restart_cancels=4 compact_runs=1 ms=19.2224
restart geometric xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=6.60422
restart luby xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 restart_cancels=0 compact_runs=0 ms=3.79334
```

Phase benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --phase-bench --size 2
```

Result:

```text
phase saved chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 restarts=0 phase_saves=40 phase_flips=0 phase_pos=0 phase_neg=0 ms=9.82238
phase positive chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 restarts=0 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=0 ms=12.9072
phase negative chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 learnts=0 restarts=0 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=0 ms=12.0934
phase saved chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 restarts=0 phase_saves=40 phase_flips=20 phase_pos=0 phase_neg=0 ms=7.30841
phase positive chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 restarts=0 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=0 ms=8.86436
phase negative chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 learnts=0 restarts=0 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=0 ms=10.5063
phase saved pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 phase_saves=74 phase_flips=44 phase_pos=2 phase_neg=8 ms=20.2755
phase positive pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=6 propagations=60 conflicts=7 learnts=6 restarts=0 phase_saves=0 phase_flips=0 phase_pos=6 phase_neg=0 ms=11.8391
phase negative pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=11 propagations=63 conflicts=8 learnts=7 restarts=1 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=11 ms=13.0765
phase saved xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 phase_saves=11 phase_flips=0 phase_pos=11 phase_neg=0 ms=5.28083
phase positive xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 phase_saves=0 phase_flips=0 phase_pos=11 phase_neg=0 ms=3.53143
phase negative xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=17 conflicts=4 learnts=4 restarts=1 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=11 ms=6.19751
```

Parse benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --parse-bench --size 2
```

Result:

```text
parse fixture grid-sat-6x6: text_len=559 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ok=1 errors=0 ms=4.72074
fixture cdcl grid-sat-6x6: status=SAT decisions=0 propagations=36 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=11.2563
parse fixture grid-unsat-6x6: text_len=562 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ok=1 errors=0 ms=6.66856
fixture cdcl grid-unsat-6x6: status=UNSAT decisions=0 propagations=36 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=6.3806
parse fixture chain-sat-120: text_len=1145 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ok=1 errors=0 ms=9.33596
fixture cdcl chain-sat-120: status=SAT decisions=0 propagations=120 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=18.1059
parse fixture chain-unsat-120: text_len=1148 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ok=1 errors=0 ms=13.737
fixture cdcl chain-unsat-120: status=UNSAT decisions=0 propagations=120 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=32.8037
parse fixture wide-48-8-20: text_len=575 vars=48 clauses=20 declared_vars=48 declared_clauses=20 ok=1 errors=0 ms=7.84979
fixture cdcl wide-48-8-20: status=SAT decisions=41 propagations=0 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=24.5102
```

Scan parser benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --scan-parse-bench --size 2
```

Result:

```text
parse split grid-sat-6x6: text_len=559 vars=36 clauses=62 ok=1 errors=0 ms=5.02396
parse scan grid-sat-6x6: text_len=559 vars=36 clauses=62 ok=1 errors=0 ms=6.08026
parse ints grid-sat-6x6: text_len=559 vars=36 clauses=62 ok=1 errors=0 ms=0.708899
ints fixture cdcl grid-sat-6x6: status=SAT decisions=0 propagations=36 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=4.359
parse split grid-unsat-6x6: text_len=562 vars=36 clauses=62 ok=1 errors=0 ms=4.52208
parse scan grid-unsat-6x6: text_len=562 vars=36 clauses=62 ok=1 errors=0 ms=6.28133
parse ints grid-unsat-6x6: text_len=562 vars=36 clauses=62 ok=1 errors=0 ms=0.665107
ints fixture cdcl grid-unsat-6x6: status=UNSAT decisions=0 propagations=36 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=3.87275
parse split chain-sat-120: text_len=1145 vars=120 clauses=121 ok=1 errors=0 ms=9.88422
parse scan chain-sat-120: text_len=1145 vars=120 clauses=121 ok=1 errors=0 ms=13.0697
parse ints chain-sat-120: text_len=1145 vars=120 clauses=121 ok=1 errors=0 ms=1.50098
ints fixture cdcl chain-sat-120: status=SAT decisions=0 propagations=120 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=11.2676
parse split chain-unsat-120: text_len=1148 vars=120 clauses=121 ok=1 errors=0 ms=10.8568
parse scan chain-unsat-120: text_len=1148 vars=120 clauses=121 ok=1 errors=0 ms=14.1833
parse ints chain-unsat-120: text_len=1148 vars=120 clauses=121 ok=1 errors=0 ms=1.43721
ints fixture cdcl chain-unsat-120: status=UNSAT decisions=0 propagations=120 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=10.049
parse split wide-48-8-20: text_len=575 vars=48 clauses=20 ok=1 errors=0 ms=3.66085
parse scan wide-48-8-20: text_len=575 vars=48 clauses=20 ok=1 errors=0 ms=5.76939
parse ints wide-48-8-20: text_len=575 vars=48 clauses=20 ok=1 errors=0 ms=0.798576
ints fixture cdcl wide-48-8-20: status=SAT decisions=41 propagations=0 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=8.98758
```

File-backed benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --file-bench --size 2
```

Result:

```text
file fixture grid-sat-6x6: text_len=559 wrote=1 removed=1 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ok=1 errors=0 write_ms=10.5863 parse_file_ms=5.25936
file cdcl grid-sat-6x6: status=SAT decisions=0 propagations=36 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=8.94386
file fixture grid-unsat-6x6: text_len=562 wrote=1 removed=1 vars=36 clauses=62 declared_vars=36 declared_clauses=62 ok=1 errors=0 write_ms=16.1515 parse_file_ms=8.35636
file cdcl grid-unsat-6x6: status=UNSAT decisions=0 propagations=36 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=8.61337
file fixture chain-sat-120: text_len=1145 wrote=1 removed=1 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ok=1 errors=0 write_ms=0.430016 parse_file_ms=13.1423
file cdcl chain-sat-120: status=SAT decisions=0 propagations=120 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=12.5546
file fixture chain-unsat-120: text_len=1148 wrote=1 removed=1 vars=120 clauses=121 declared_vars=120 declared_clauses=121 ok=1 errors=0 write_ms=0.202332 parse_file_ms=8.4651
file cdcl chain-unsat-120: status=UNSAT decisions=0 propagations=120 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=14.6798
file fixture wide-48-8-20: text_len=575 wrote=1 removed=1 vars=48 clauses=20 declared_vars=48 declared_clauses=20 ok=1 errors=0 write_ms=0.407876 parse_file_ms=8.50966
file cdcl wide-48-8-20: status=SAT decisions=41 propagations=0 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=12.0022
```

Corpus benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --corpus-bench
```

Result:

```text
corpus parse multiline-sat: path=tests/corpus/multiline_sat.cnf vars=4 clauses=4 declared_vars=4 declared_clauses=4 ok=1 errors=0 ms=0.578708
corpus cdcl multiline-sat: status=SAT decisions=1 propagations=2 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=0.520391
corpus parse multi-clause-line-unsat: path=tests/corpus/multi_clause_line_unsat.cnf vars=2 clauses=4 declared_vars=2 declared_clauses=4 ok=1 errors=0 ms=0.32665
corpus cdcl multi-clause-line-unsat: status=UNSAT decisions=0 propagations=2 conflicts=1 learnts=0 restarts=0 compact_runs=0 ms=0.285862
corpus parse triangle-3color-sat: path=tests/corpus/triangle_3color_sat.cnf vars=9 clauses=21 declared_vars=9 declared_clauses=21 ok=1 errors=0 ms=1.47052
corpus cdcl triangle-3color-sat: status=SAT decisions=2 propagations=7 conflicts=0 learnts=0 restarts=0 compact_runs=0 ms=1.84738
corpus parse k4-3color-unsat: path=tests/corpus/k4_3color_unsat.cnf vars=12 clauses=34 declared_vars=12 declared_clauses=34 ok=1 errors=0 ms=2.32322
corpus cdcl k4-3color-unsat: status=UNSAT decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 compact_runs=1 ms=11.5785
```

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
