# Benchmark Trend Runner

`run_trends.sh` records selected EigenMiniSat pressure outputs without running
the entire smoke suite by hand. Logs are written to `benchmarks/runs/`, which
is ignored by git.

```bash
benchmarks/run_trends.sh
benchmarks/run_trends.sh quick 1
benchmarks/run_trends.sh full 2
benchmarks/run_trends.sh quick 1 /tmp/eigenminisat-trend.log
```

Profiles:

- `quick`: solver tests, metadata compaction, clause storage pressure, scan
  parser comparison, and the manifest corpus benchmark.
- `full`: solver tests plus every benchmark mode.

Use `EIGENSCRIPT_BIN=/path/to/eigenscript` to override the interpreter.
