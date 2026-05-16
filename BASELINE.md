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
bench scan chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=9.82191
bench watched chain-sat-40: status=SAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=0 ms=5.40093
bench scan chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=7.90217
bench watched chain-unsat-40: status=UNSAT vars=40 clauses=41 decisions=0 propagations=40 conflicts=1 ms=5.02972
bench scan pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=37.0674
bench watched pigeonhole-4-3: status=UNSAT vars=12 clauses=34 decisions=10 propagations=43 conflicts=6 ms=32.5955
bench scan xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=16.8886
bench watched xor-triangle-4: status=SAT vars=12 clauses=16 decisions=11 propagations=0 conflicts=0 ms=18.1412
```

The watched path currently rebuilds watch state at each DPLL node. The numbers
already show benefit on propagation-heavy cases, and they make the next target
explicit: persistent trail/watch state with decision-level backtracking.

Smoke command:

```bash
tests/run_smoke.sh
```

Status: passed.
