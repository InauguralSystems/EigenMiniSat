## What does this PR do?

<!-- Brief description of the change -->

## Checklist

- [ ] The solver is **correct on the corpus** — SAT/UNSAT verdicts are verified
      against the known-satisfiability fixtures (`tests/fixtures/`, `tests/corpus/`)
- [ ] `tests/run_smoke.sh` passes locally and **CI passes**
- [ ] Any EigenScript language/runtime gap surfaced by this change is filed
      upstream in the [EigenScript repo](https://github.com/InauguralSystems/EigenScript/issues)
      (and kept as a comparison benchmark, not hidden with a local bypass)
- [ ] Benchmark or heuristic changes note any BASELINE.md impact
