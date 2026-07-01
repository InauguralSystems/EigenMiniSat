---
name: Feature Request
about: Suggest a new heuristic, benchmark, or corpus fixture to exercise
title: ""
labels: enhancement
assignees: ""
---

**What would this exercise?**
EigenMiniSat ports a MiniSat-style CDCL solver in EigenScript and turns solver
pressure into repeatable benchmarks that expose language/runtime gaps. Which
part would a new feature stress — a decision heuristic (VSIDS-style ordering,
phase saving), a restart/reduction policy, the DIMACS parser, or a benchmark
family?

**Proposed heuristic / benchmark / fixture**
What it adds and how it'd run (e.g. a new `--*-bench` mode, or a `.cnf` fixture
with known satisfiability for the corpus).

**Alternatives considered**
Any existing solver mode, benchmark, or fixture that already covers part of this.

> If it needs a new EigenScript language or runtime primitive, note that — the
> gap belongs upstream in the
> [EigenScript repo](https://github.com/InauguralSystems/EigenScript/issues).
