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
- `evidence`: quick profile coverage plus generated fixture parse/text-build
  pressure and malformed-DIMACS diagnostics, with default size `2` for bounded
  larger-case pressure. It appends a compact evidence summary with copy,
  metadata, storage, parser, diagnostic, corpus, and text-build totals, storage
  overhead deltas, decision flags, and active candidate-decision rows.
- `full`: solver tests plus every benchmark mode, including malformed-DIMACS
  diagnostics.

Use `EIGENSCRIPT_BIN=/path/to/eigenscript` to override the interpreter.

The summary flags are evidence markers, not automatic root decisions.
`decision_candidate` rows turn active flags into the current scoped next action:
EigenMiniSat-local, root/runtime, or root-or-standard-library exploration. They
are intended to keep the next EigenMiniSat-vs-EigenScript decision grounded in
small repeatable counters instead of full raw logs.

Storage overhead summaries include `inline_rows`. When it is nonzero, the log
has inline adapter scan/watch rows that use the clause-store shape without
helper calls in the hot loop, so `helper_*` and `inline_*` overhead can be read
separately. Older logs summarize with `inline_rows=0`.

Parse summaries include `tokens_ms` fields when logs contain the
`scan_int_tokens`-backed DIMACS parser. Older logs summarize those fields as
zero, so split/scan/ints comparisons remain readable across checkpoints.

Text build summaries include `concat_ms`, `text_builder_ms`, and
`text_builder_overhead_ms` when generated fixture logs contain text-builder
rows. Negative overhead marks a native-builder win over repeated concat, and
the summary reports that as `text_builder_native_win=1`. This keeps
string-assembly pressure visible after the main generated-DIMACS path moves to
EigenScript's root-backed builder API.

## Native MiniSat differential oracle

```bash
benchmarks/run_native_oracle.sh
benchmarks/run_native_oracle.sh --selftest
# Larger rungs are opt-in; every selected solve must finish within its cap.
SOLVE_TIMEOUT=3600 benchmarks/run_native_oracle.sh --rungs '3x3 4x4 5x5'
SOLVE_TIMEOUT=7200 benchmarks/run_native_oracle.sh --rungs '5x6 6x6'
# File-only run, without the optional AOT toolchain:
benchmarks/run_native_oracle.sh --aot off --rungs ''
# Deliberately empty selection: must fail before building or solving.
mkdir -p /tmp/ems-oracle-empty
benchmarks/run_native_oracle.sh --rungs '' --instances /tmp/ems-oracle-empty
```

Native MiniSat supplies the **ground-truth SAT/UNSAT answer**. Each instance
must agree with EMS under `--cdcl` and current default policies (regime C in
`TSEITIN_LADDER.md`). The table reports native conflicts / EMS conflicts as a
search comparison; it does not gate the ratio or claim a runtime speedup.
Native conflicts and CPU seconds are read from its report, and its stdout
verdict must agree with its result file and exit status (SAT=10, UNSAT=20).

Every emitted rung must also match the ordered DIMACS encoding of the named
odd torus: header dimensions, all edge numbers, each clause and literal in
order, and charge at vertex `(0,0)`. `torus_identity.awk` checks this separately
from the EigenScript emitter. Ordering matters because it affects search.
For 3x3, an additional comparison anchors the emitted token stream directly
to `tests/fixtures/tseitin_torus_3x3_odd.cnf`; comments and whitespace are
ignored, while clause/literal order remains significant. Another UNSAT
formula of the same size cannot substitute for the named torus.

Any run selecting ladder rungs first solves both 3x3 and 4x4 and requires
their full EMS-VM stdout, excluding timing, to match the banked regime-C
outputs in [`oracle/`](oracle/README.md). This implements CLAUDE.md's lane
preflight rule. Each anchor is solved once; an anchor also selected for
measurement reuses that solve. Extra anchors print `PREFLIGHT`, are included
in completion counts as `preflight-added`, and do not enter the requested
search-gap table. File-only runs need no ladder preflight, and an empty
selection still fails before any preflight is added.

The second oracle is **EMS-VM stdout for the AOT byte comparison**. With AOT
enabled, the harness builds `minisat.eigs` once and compares each AOT stdout
file byte for byte with VM stdout, stripping only a final numeric ` ms=`
field on comment lines. All other bytes, including final newlines, remain
significant. Stderr is retained for diagnostics. This checks answers and CLI
output; it does not replace SAT model checking or DRAT proof verification.

Default coverage is every `.cnf` recursively beneath `tests/corpus` and
`tests/fixtures`, plus odd-torus 3x3 and 4x4. Larger standard ladder rungs
print `SKIPPED (budget)` and contribute no passes. `RUNGS` or `--rungs`
replaces the rung list; `INSTANCE_DIR` or `--instances` replaces both file
directories. Explicit empty selections fail, as do missing inputs, malformed
solver reports, emitter errors, solver errors, and timeouts. The default
per-command cap is 120 seconds; an attempted rung timing out is **FAIL**,
never a budget skip. The default excludes 5x5 because native MiniSat's short
solve time is not a budget estimate for the EMS VM. A cold AOT build can also
take longer than the solves; its separate default cap is 600 seconds.

Native MiniSat rejects the SATLIB `%` / `0` trailers present in this repo.
The harness announces their removal and feeds the same temporary formula
to every arm. It accepts only a standalone `%`, an optional standalone `0`,
and blank trailing lines; other trailing data fails. It leaves clause order
and literals intact. Original fixtures are unchanged; this entry point
does not test EMS's handling of the original trailers.

The dev-box defaults are `/usr/bin/minisat`, the VM/runtime at
`/home/jon/src/wt/es-v043`, and `ouroboros/aot/build.sh` beneath
`/home/jon/src/InauguralSystems/EigenScriptEcosystem`. Override with
`MINISAT_BIN`, `EIGS_DIR`, `EIGENSCRIPT_BIN`, and `AOT_BUILD` (see `--help`).
`AOT=auto` enables the arm when the toolchains exist and build successfully.
Absence or a build failure (including a build timeout or missing executable)
prints a named `AOT: SKIPPED` line and continues the native/VM oracle; the
disabled arm contributes zero AOT passes. `AOT=on` makes both absence and
build failure hard failures. `AOT=off` explicitly disables the arm. Invalid
configuration, including a mismatched runtime/VM or invalid explicit
`AOT_BINARY`, still fails in auto mode. An enabled arm requires the v0.43.0
checkout and its own VM binary. Source is staged and all build artifacts are created under `/tmp`,
so neither external checkout is written. `KEEP_WORK=1` retains raw reports,
result files, normalized output, per-instance `results.tsv`, and build logs;
the path is printed at exit. Run one harness at a time.

For repeated gate-development/selftest runs, `AOT_BINARY=/tmp/.../minisat-aot`
explicitly reuses a previously built binary and announces that choice. The
default always builds afresh. This override leaves binary provenance to the
caller; the VM/runtime version checks and every per-instance byte comparison
still run. It is useful with the binary retained by `KEEP_WORK=1`.

`--selftest` first runs real SAT and UNSAT controls, then drives the same
production runner with seven faults (six when AOT is disabled): a clause
deleted from **only EMS's copy** of an UNSAT CNF, a rewritten EMS verdict,
an extra AOT output line, a zero-instance selection, a solver that times
out, a solver that exits successfully with no output, and an emitter that
replaces the requested column count with three. The last fault requests
4x4, so a correct 3x3 output cannot mask it. Corrupting the
shared CNF would make two correct solvers agree on its changed answer, so
the first plant deliberately models input corruption between the two arms.
Each plant must fail through its intended named check; an unrelated crash
counts as `MISS`. `SELFTEST ALL RED` exits **1 intentionally**, as a red
demonstration. A missing detection prints `MISS` / `SELFTEST BROKEN` and
exits **2**. Treat neither nonzero code alone as proof of working selftests:
require the named RED lines and `SELFTEST ALL RED` summary.

Supporting controls independently exercise the fixture comparison, a wrong
clause with unchanged dimensions, both regime comparisons, and each missing
completion count (passed/native/VM/AOT). They also plant a build script that
exits 7: auto mode must finish a real native/VM solve with `AOT=0`, and on
mode must fail. The auto control seeds a stale enabled arm so failure to
clear it is observable. Build-failure controls skip explicitly if a matching
pinned runtime is absent. Any missing control or detection makes the whole
selftest report `MISS` / `SELFTEST BROKEN`, exit 2; the seven main plants
remain separately counted. Normal runs never inject these faults.

The initial [validation transcript](NATIVE_ORACLE_VALIDATION.md) records the
clean run, planted faults, comparator mutations, and measured budget limits.
The [round 2 transcript](NATIVE_ORACLE_ROUND2.md) records the wrong-rung
regression going from a silent pass to a named failure and the new controls.
