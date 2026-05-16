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

Heuristic benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --heuristic-bench --size 1
```

Result:

```text
heuristic geom-saved pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 restart_budget=6 restart_index=1 phase_saves=74 phase_flips=44 phase_pos=2 phase_neg=8 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=16.1252
heuristic luby-saved pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=64 conflicts=8 learnts=7 restarts=1 restart_budget=3 restart_index=1 phase_saves=74 phase_flips=44 phase_pos=2 phase_neg=8 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=17.5148
heuristic geom-positive pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=6 propagations=60 conflicts=7 learnts=6 restarts=0 restart_budget=3 restart_index=0 phase_saves=0 phase_flips=0 phase_pos=6 phase_neg=0 heap_pops=14 heap_inserts=9 compact_runs=1 compact_removed=1 ms=15.6191
heuristic geom-negative pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=11 propagations=63 conflicts=8 learnts=7 restarts=1 restart_budget=6 restart_index=1 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=11 heap_pops=16 heap_inserts=13 compact_runs=1 compact_removed=2 ms=15.4659
heuristic luby-negative pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=12 propagations=68 conflicts=8 learnts=7 restarts=2 restart_budget=4 restart_index=2 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=12 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=13.0782
heuristic summary pigeonhole-4-3: policies=5 status=UNSAT min_decisions=6 max_decisions=12 min_conflicts=7 max_conflicts=8 max_restarts=2 max_compact_runs=1
heuristic geom-saved k5-3color: status=UNSAT vars=15 clauses=50 decisions=10 propagations=82 conflicts=8 learnts=7 restarts=1 restart_budget=6 restart_index=1 phase_saves=92 phase_flips=54 phase_pos=2 phase_neg=8 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=14.581
heuristic luby-saved k5-3color: status=UNSAT vars=15 clauses=50 decisions=10 propagations=82 conflicts=8 learnts=7 restarts=1 restart_budget=3 restart_index=1 phase_saves=92 phase_flips=54 phase_pos=2 phase_neg=8 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=24.1671
heuristic geom-positive k5-3color: status=UNSAT vars=15 clauses=50 decisions=6 propagations=77 conflicts=7 learnts=6 restarts=0 restart_budget=3 restart_index=0 phase_saves=0 phase_flips=0 phase_pos=6 phase_neg=0 heap_pops=14 heap_inserts=9 compact_runs=1 compact_removed=1 ms=23.3627
heuristic geom-negative k5-3color: status=UNSAT vars=15 clauses=50 decisions=11 propagations=81 conflicts=8 learnts=7 restarts=1 restart_budget=6 restart_index=1 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=11 heap_pops=16 heap_inserts=13 compact_runs=1 compact_removed=2 ms=16.0963
heuristic luby-negative k5-3color: status=UNSAT vars=15 clauses=50 decisions=12 propagations=87 conflicts=8 learnts=7 restarts=2 restart_budget=4 restart_index=2 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=12 heap_pops=17 heap_inserts=14 compact_runs=1 compact_removed=2 ms=21.4544
heuristic summary k5-3color: policies=5 status=UNSAT min_decisions=6 max_decisions=12 min_conflicts=7 max_conflicts=8 max_restarts=2 max_compact_runs=1
heuristic geom-saved xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 phase_saves=11 phase_flips=0 phase_pos=11 phase_neg=0 heap_pops=11 heap_inserts=0 compact_runs=0 compact_removed=0 ms=3.44361
heuristic luby-saved xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 phase_saves=11 phase_flips=0 phase_pos=11 phase_neg=0 heap_pops=11 heap_inserts=0 compact_runs=0 compact_removed=0 ms=2.9969
heuristic geom-positive xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 learnts=0 restarts=0 restart_budget=3 restart_index=0 phase_saves=0 phase_flips=0 phase_pos=11 phase_neg=0 heap_pops=11 heap_inserts=0 compact_runs=0 compact_removed=0 ms=5.70466
heuristic geom-negative xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=17 conflicts=4 learnts=4 restarts=1 restart_budget=6 restart_index=1 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=11 heap_pops=21 heap_inserts=11 compact_runs=0 compact_removed=0 ms=5.68804
heuristic luby-negative xor-triangle-4: status=SAT vars=12 clauses=16 decisions=14 propagations=22 conflicts=4 learnts=4 restarts=2 restart_budget=4 restart_index=2 phase_saves=0 phase_flips=0 phase_pos=0 phase_neg=14 heap_pops=25 heap_inserts=18 compact_runs=0 compact_removed=0 ms=6.49177
heuristic summary xor-triangle-4: policies=5 status=SAT min_decisions=11 max_decisions=14 min_conflicts=0 max_conflicts=4 max_restarts=2 max_compact_runs=0
```

Metadata compaction benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --metadata-bench --size 2
```

Result:

```text
metadata compaction metadata-2: vars=40 base=40 learnts_added=160 clauses_after=120 active_learnts=80 clause_allocs=200 learnt_allocs=160 learnt_lits=480 reduce_runs=1 reduce_scans=80 learnt_deleted=80 compact_runs=1 compact_removed=80 compact_kept=120 watch_rebuilds=1 compact_replays=40 build_add_ms=13.019 reduce_ms=195.196 compact_ms=3.49531
```

Storage benchmark command:

```bash
/home/jon/EigenScript/src/eigenscript minisat.eigs --storage-bench --size 1
```

Result:

```text
storage arena wide-40-12-20: vars=40 clauses=20 lits=240 flat_lits=240 offsets=20 list_scan_ms=1.22928 build_ms=0.202821 flat_scan_ms=1.09644 watch_seed_ms=0.506003 reconstruct_ms=0.319596 watch_links=40 watch_buckets=34 max_watch_bucket=2 checksum=1230396
storage compact wide-40-12-20: clauses=20 removed=7 kept=13 kept_lits=156 list_compact_ms=0.073264 flat_compact_ms=0.274967 remap_ms=0.046235 remap_active=10 remap_checksum=1003 compact_checksum=531704
storage arena pigeonhole-4-3: vars=12 clauses=34 lits=72 flat_lits=72 offsets=34 list_scan_ms=0.402498 build_ms=0.118661 flat_scan_ms=0.369044 watch_seed_ms=0.548327 reconstruct_ms=0.200795 watch_links=68 watch_buckets=20 max_watch_bucket=5 checksum=36634
storage compact pigeonhole-4-3: clauses=34 removed=11 kept=23 kept_lits=49 list_compact_ms=0.079341 flat_compact_ms=0.212598 remap_ms=0.068654 remap_active=18 remap_checksum=5268 compact_checksum=18597
storage arena grid-unsat-6x6: vars=36 clauses=62 lits=122 flat_lits=122 offsets=62 list_scan_ms=0.674391 build_ms=0.199607 flat_scan_ms=0.584226 watch_seed_ms=1.03079 reconstruct_ms=0.34397 watch_links=122 watch_buckets=72 max_watch_bucket=2 checksum=357195
storage compact grid-unsat-6x6: clauses=62 removed=21 kept=41 kept_lits=81 list_compact_ms=0.147785 flat_compact_ms=1.24975 remap_ms=0.155817 remap_active=32 remap_checksum=27840 compact_checksum=157763
storage arena chain-unsat-80: vars=80 clauses=81 lits=160 flat_lits=160 offsets=81 list_scan_ms=0.891111 build_ms=0.270288 flat_scan_ms=0.761275 watch_seed_ms=1.52807 reconstruct_ms=0.483235 watch_links=160 watch_buckets=160 max_watch_bucket=1 checksum=1378160
storage compact chain-unsat-80: clauses=81 removed=27 kept=54 kept_lits=106 list_compact_ms=0.181798 flat_compact_ms=0.441469 remap_ms=0.158611 remap_active=42 remap_checksum=61743 compact_checksum=605393
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
corpus manifest path=tests/corpus/manifest.txt cases=8
corpus parse split multiline-sat: family=layout path=tests/corpus/multiline_sat.cnf text_len=128 vars=4 clauses=4 declared_vars=4 declared_clauses=4 ok=1 errors=0 ms=0.489173
corpus parse scan multiline-sat: family=layout text_len=128 vars=4 clauses=4 ok=1 errors=0 ms=0.938255
corpus parse ints multiline-sat: family=layout text_len=128 vars=4 clauses=4 ok=1 errors=0 ms=0.10574
corpus cdcl multiline-sat: family=layout expected=SAT status=SAT decisions=1 propagations=2 conflicts=0 learnts=0 backjumps=0 heap_pops=1 heap_inserts=0 restarts=0 compact_runs=0 clause_allocs=4 learnt_allocs=0 ms=0.713993
corpus parse split multi-clause-line-unsat: family=layout path=tests/corpus/multi_clause_line_unsat.cnf text_len=80 vars=2 clauses=4 declared_vars=2 declared_clauses=4 ok=1 errors=0 ms=0.436232
corpus parse scan multi-clause-line-unsat: family=layout text_len=80 vars=2 clauses=4 ok=1 errors=0 ms=0.529332
corpus parse ints multi-clause-line-unsat: family=layout text_len=80 vars=2 clauses=4 ok=1 errors=0 ms=0.101829
corpus cdcl multi-clause-line-unsat: family=layout expected=UNSAT status=UNSAT decisions=0 propagations=2 conflicts=1 learnts=0 backjumps=0 heap_pops=0 heap_inserts=0 restarts=0 compact_runs=0 clause_allocs=4 learnt_allocs=0 ms=0.454531
corpus parse split triangle-3color-sat: family=graph-coloring path=tests/corpus/triangle_3color_sat.cnf text_len=399 vars=9 clauses=21 declared_vars=9 declared_clauses=21 ok=1 errors=0 ms=1.71483
corpus parse scan triangle-3color-sat: family=graph-coloring text_len=399 vars=9 clauses=21 ok=1 errors=0 ms=2.76211
corpus parse ints triangle-3color-sat: family=graph-coloring text_len=399 vars=9 clauses=21 ok=1 errors=0 ms=0.36632
corpus cdcl triangle-3color-sat: family=graph-coloring expected=SAT status=SAT decisions=2 propagations=7 conflicts=0 learnts=0 backjumps=0 heap_pops=5 heap_inserts=0 restarts=0 compact_runs=0 clause_allocs=21 learnt_allocs=0 ms=3.04971
corpus parse split k4-3color-unsat: family=graph-coloring path=tests/corpus/k4_3color_unsat.cnf text_len=546 vars=12 clauses=34 declared_vars=12 declared_clauses=34 ok=1 errors=0 ms=4.31441
corpus parse scan k4-3color-unsat: family=graph-coloring text_len=546 vars=12 clauses=34 ok=1 errors=0 ms=5.00103
corpus parse ints k4-3color-unsat: family=graph-coloring text_len=546 vars=12 clauses=34 ok=1 errors=0 ms=0.500976
corpus cdcl k4-3color-unsat: family=graph-coloring expected=UNSAT status=UNSAT decisions=10 propagations=64 conflicts=8 learnts=7 backjumps=7 heap_pops=17 heap_inserts=14 restarts=1 compact_runs=1 clause_allocs=41 learnt_allocs=7 ms=12.4291
corpus parse split pigeonhole-4-3-unsat: family=pigeonhole path=tests/corpus/pigeonhole_4_3.cnf text_len=521 vars=12 clauses=34 declared_vars=12 declared_clauses=34 ok=1 errors=0 ms=2.5479
corpus parse scan pigeonhole-4-3-unsat: family=pigeonhole text_len=521 vars=12 clauses=34 ok=1 errors=0 ms=3.85366
corpus parse ints pigeonhole-4-3-unsat: family=pigeonhole text_len=521 vars=12 clauses=34 ok=1 errors=0 ms=0.414023
corpus cdcl pigeonhole-4-3-unsat: family=pigeonhole expected=UNSAT status=UNSAT decisions=10 propagations=64 conflicts=8 learnts=7 backjumps=7 heap_pops=17 heap_inserts=14 restarts=1 compact_runs=1 clause_allocs=41 learnt_allocs=7 ms=11.6686
corpus parse split long-clause-sat: family=wide path=tests/corpus/long_clause_sat.cnf text_len=213 vars=20 clauses=6 declared_vars=20 declared_clauses=6 ok=1 errors=0 ms=0.982815
corpus parse scan long-clause-sat: family=wide text_len=213 vars=20 clauses=6 ok=1 errors=0 ms=1.50852
corpus parse ints long-clause-sat: family=wide text_len=213 vars=20 clauses=6 ok=1 errors=0 ms=0.208688
corpus cdcl long-clause-sat: family=wide expected=SAT status=SAT decisions=16 propagations=1 conflicts=0 learnts=0 backjumps=0 heap_pops=16 heap_inserts=0 restarts=0 compact_runs=0 clause_allocs=6 learnt_allocs=0 ms=2.91045
corpus parse split xor-contradiction-unsat: family=parity path=tests/corpus/xor_contradiction_unsat.cnf text_len=98 vars=2 clauses=4 declared_vars=2 declared_clauses=4 ok=1 errors=0 ms=0.503909
corpus parse scan xor-contradiction-unsat: family=parity text_len=98 vars=2 clauses=4 ok=1 errors=0 ms=0.620475
corpus parse ints xor-contradiction-unsat: family=parity text_len=98 vars=2 clauses=4 ok=1 errors=0 ms=0.134306
corpus cdcl xor-contradiction-unsat: family=parity expected=UNSAT status=UNSAT decisions=1 propagations=3 conflicts=2 learnts=1 backjumps=1 heap_pops=1 heap_inserts=1 restarts=0 compact_runs=0 clause_allocs=5 learnt_allocs=1 ms=0.711689
corpus parse split xor-ladder-sat: family=parity path=tests/corpus/xor_ladder_sat.cnf text_len=136 vars=6 clauses=10 declared_vars=6 declared_clauses=10 ok=1 errors=0 ms=0.824763
corpus parse scan xor-ladder-sat: family=parity text_len=136 vars=6 clauses=10 ok=1 errors=0 ms=1.24416
corpus parse ints xor-ladder-sat: family=parity text_len=136 vars=6 clauses=10 ok=1 errors=0 ms=0.170833
corpus cdcl xor-ladder-sat: family=parity expected=SAT status=SAT decisions=1 propagations=5 conflicts=0 learnts=0 backjumps=0 heap_pops=1 heap_inserts=0 restarts=0 compact_runs=0 clause_allocs=10 learnt_allocs=0 ms=1.18598
```

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
