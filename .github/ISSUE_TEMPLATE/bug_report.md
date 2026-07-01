---
name: Bug Report
about: Report a bug in EigenMiniSat (a wrong SAT/UNSAT verdict, a mis-solved corpus instance, or a crash)
title: ""
labels: bug
assignees: ""
---

**Describe the bug**
What went wrong — e.g. the solver returns the wrong SAT/UNSAT verdict, a corpus
instance is mis-solved, the DIMACS parser rejects a valid `.cnf`, or the solver
crashes.

**To reproduce**
Which instance and how you ran it:
```sh
eigenscript minisat.eigs tests/fixtures/simple_sat.cnf   # or --cdcl / --watched / a corpus file
```

**Expected vs actual**
The expected verdict (SAT or UNSAT, and the known satisfiability of the fixture)
vs what the solver reported (include output).

**Environment**
- OS: [e.g., Ubuntu 24.04]
- EigenScript version: [output of `eigenscript --version`]
- EigenMiniSat version/tag: [e.g. v0.1.0]

> If the root cause is the EigenScript language, runtime, or an observer
> predicate itself, it belongs in the
> [EigenScript repo](https://github.com/InauguralSystems/EigenScript/issues).
