# Contributing

EigenMiniSat is part of the [EigenScript](https://github.com/InauguralSystems/EigenScript)
ecosystem. It serves as a SAT solver benchmark suite that drives language expansion.

## Getting Started

1. Clone EigenScript and build it:
   ```
   git clone https://github.com/InauguralSystems/EigenScript.git
   cd EigenScript && make build && make install
   ```

2. Clone this repo and run tests:
   ```
   git clone https://github.com/InauguralSystems/EigenMiniSat.git
   cd EigenMiniSat && tests/run_smoke.sh
   ```

## Development Workflow

- All solver code is in `lib/solver.eigs`, `lib/dimacs.eigs`, `lib/bench.eigs`
- Tests are in `tests/test_solver.eigs` and `tests/run_smoke.sh`
- Benchmarks are run via `eigenscript minisat.eigs --bench --size N`

## Reporting Issues

Open an issue on this repo for solver bugs, or on EigenScript for language-level issues.

## License

MIT. See [LICENSE](LICENSE).
