# Benchmark Trend Runner

`run_trends.sh` records selected EigenMiniSat pressure outputs without running
the entire smoke suite by hand. Logs are written to `benchmarks/runs/`, which
is ignored by git.

```bash
benchmarks/run_trends.sh
benchmarks/run_trends.sh quick 1
benchmarks/run_trends.sh evidence
benchmarks/run_trends.sh evidence 2 /tmp/eigenminisat-evidence.log
benchmarks/summarize_trend.sh /tmp/eigenminisat-evidence.log
benchmarks/run_trends.sh full 2
benchmarks/run_trends.sh quick 1 /tmp/eigenminisat-trend.log
```

Profiles:

- `quick`: solver tests, metadata compaction/churn, conflict-copy pressure,
  clause storage pressure, scan parser comparison, and the manifest corpus
  benchmark.
- `evidence`: quick profile coverage plus malformed-DIMACS diagnostics, with
  default size `2` for bounded larger-case pressure. It appends a compact
  evidence summary with copy, metadata, storage, parser, diagnostic, and corpus
  totals plus decision flags and active candidate-decision rows.
- `full`: solver tests plus every benchmark mode, including malformed-DIMACS
  diagnostics.

Use `EIGENSCRIPT_BIN=/path/to/eigenscript` to override the interpreter.

The summary flags are evidence markers, not automatic root decisions.
`decision_candidate` rows turn active flags into the current scoped next action:
EigenMiniSat-local, root/runtime, or root-or-standard-library exploration. They
are intended to keep the next EigenMiniSat-vs-EigenScript decision grounded in
small repeatable counters instead of full raw logs.
