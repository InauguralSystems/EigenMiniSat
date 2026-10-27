# Benchmarks

The baseline measurement device is the field's standard one: SAT Competition
instances scored by solved count and PAR-2 against Kissat, CaDiCaL and MiniSat.
See [SAT Competition baseline](#sat-competition-baseline-131).

For five-sample **external process wall-time** comparisons of prebuilt EMS AOT
and native MiniSat, including an optional interleaved AOT candidate, use
[`compare_native.py`](NATIVE_TIMING.md). It first runs the existing correctness
oracle below, then times its prepared inputs with per-sample validation.

[`props_per_second.sh`](props_per_second.sh) reports EigenMiniSat's throughput
as **propagations per second** against native MiniSat on the same CNF — the
solver equivalent of an emulator's MHz, and the bar `compare_native.py` stops
short of. Wall-time-to-solve is policy-confounded: two solvers that pick
different decision literals do different amounts of work, so a wall ratio
measures the search's luck as much as the runtime's speed. A propagation is the
same unit of work whoever performs it.

```bash
bash benchmarks/props_per_second.sh                       # the 4x4 torus oracle CNF
bash benchmarks/props_per_second.sh path/to/other.cnf
```

On `tseitin_torus_4x4_odd.cnf` (2026-09-17, idle ASUS X540NA, EMS under the VM):

| arm | propagations | seconds | props/sec |
| --- | ---: | ---: | ---: |
| EigenMiniSat | 44,166 | 19.55 | 2,259 |
| native MiniSat | 546,950 | 0.2295 | 2,383,256 |

EigenMiniSat is **0.095% of native — 1,053x slower per propagation**, while the
wall ratio for the same pair is only **85x**. They differ because native needed
**12.4x more propagations** to close the instance: our propagation loop is three
orders of magnitude off, and our CDCL policy is the strong part. Only the rate
separates those.

The propagation *count* is a bonus determinism fingerprint — 44,166 on this
instance held byte-identical across release and sanitizer builds. The script
refuses to run against a sanitizer binary, which is ~5x slower and which
`--version` does not distinguish.

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

## SAT Competition baseline (#131)

The field's standard device: SAT Competition instances, the competition's metric
(instances solved within a time limit, and PAR-2, which charges an unsolved
instance twice the limit) and its reference solvers. The Tseitin ladder is the
specialized device; this run re-measures it under the same metric, in the same
job, so the two devices can be compared.

```bash
# The full measurement runs in GitHub Actions: workflow "Competition baseline",
# run it with workflow_dispatch. Locally, with the five tools built:
python3 benchmarks/competition_run.py --output /tmp/competition \
  --kissat /path/kissat --cadical /path/cadical --minisat /usr/bin/minisat \
  --eigenscript /path/EigenScript/src/eigenscript --drat-trim /path/drat-trim
# A labelled subset (smoke), as a pull request touching the harness runs it:
python3 benchmarks/competition_run.py --output /tmp/competition-smoke \
  --first 2 --ladder 3x3 --limit 10 ...   # same tool options
# Re-derive the committed sample from the same GBD databases and compare:
python3 benchmarks/competition_select.py --check
```

**Sample.** `competition_select.py` reads GBD's own `meta` and `base` databases
(their SHA-256 is recorded in `competition_manifest.json`). The population is
every GBD instance of a SAT Competition main track from 2017 (`main_YYYY`, the
years with one combined main-track set), plus, for the random 3-SAT stratum,
the competition's random tracks, because main tracks hold no uniform random
3-SAT. Five strata of five instances each, drawn with seed 131, which was fixed
before the first draw:

| stratum | rule on the GBD family label (first match wins) |
|---|---|
| parity | contains `tseitin`, `parity` or `xor`, except `parity-games` and `xor-shifting` |
| pigeonhole | contains `pigeon` or `php` |
| random-3sat | random track, `uniform-random`, every clause has 3 literals, \|clauses/variables − 4.267\| ≤ 0.1 |
| application | verification, model checking, BMC, equivalence checking, miters, cryptography, planning, scheduling, timetabling |
| other | every other main-track family |

Within a stratum the draw visits families in a keyed order (SHA-256 of seed,
stratum and family) and takes one instance from each family before it takes a
second from any. The manifest lists every family under its stratum, with the
eligible and excluded counts. Each instance is downloaded at run time from
`benchmark-database.de/file/<hash>`, and its GBD hash is re-derived from the
downloaded bytes before any solver sees it. `gbd_hash` was fuzz-tested against
GBD's own `gbdc` 0.4.3 on 2,500 generated files. Every difference was a file
that ends without trailing whitespace and contains a skipped comment or header
line: gbdc's buffer re-alignment then drops the final token. Such a file fails
the check here; it never passes.

**Arms.** These run in one harness: Kissat 4.0.4 and CaDiCaL 3.0.1 (the latest
releases, built from pinned commits), MiniSat 2.2.1 (Ubuntu 24.04's
`1:2.2.1-8build1` package; the design EigenMiniSat follows), EigenMiniSat `--cdcl` with its regime C defaults
on the VM built at the EigenScript pin read from `ci.yml`, and Kissat a second
time as the A/A arm. Each instance runs its five arms back to back, so the arms
are interleaved and never blocked. The instance order and each instance's arm
order are SHA-256 permutations of the seed, written to `order.tsv`. Before any
timed run, EMS must reproduce the regime-C banks for 3x3 and 4x4 byte for byte.
The AOT arm is not run: the repo's AOT build path (`run_native_oracle.sh`)
requires EigenScript v0.43.0, not the v0.47.0 pin.

**Metric.** Per arm, per stratum and per family: the solved count and PAR-2
(total and mean) at 60 s of wall-clock time per run. The time runs from process
launch to exit (`compare_native.run_process`). A run that reaches the limit is
killed, with its whole process session, and is charged 120 s.

**Answers are checked.**
- Every SAT model is checked against the formula. A partial model passes only
  if it satisfies every clause.
- Every UNSAT answer from Kissat, CaDiCaL and EMS is checked by drat-trim. The
  proof is written during the timed run, as in the competition. drat-trim
  verifies only if it exits 0 AND prints `s VERIFIED`, because `drat-trim.c`
  also exits 0 on its own timeout and on memory exhaustion.
- All answers are checked across the arms and against GBD's recorded result.
  Odd tori are UNSAT by construction.

A failed model, a refutation that drat-trim rejects, or an answer that
contradicts a certified one is a WRONG answer: the run exits 1 and the summary
lists it. A verified model together with a verified refutation, or certified
evidence that contradicts GBD's record, stops the run. MiniSat writes no proofs,
and a drat-trim check can reach its cap: those UNSAT answers count as solved,
are marked `+agrees` (another arm's refutation or GBD's record agrees) or
`+unchecked`, and are counted in the last column of the summary table.

**Departures from the competition.**
- The time limit is 60 s, not 5,000 s. Every run must fit one 6-hour GitHub
  job (see the arithmetic below).
- The sample is 25 instances in equal strata, not a full set. Instances over
  25 MB (GBD `bytes`) are excluded, because downloading, hashing, validating
  and model-checking them do not fit the budget. The manifest records each
  stratum's exclusions.
- The hardware is one GitHub-hosted ubuntu-24.04 runner, running one process at
  a time, with a 12 GiB address-space cap per process (`prlimit --as`).
- Each arm runs once per instance, as in the competition. The Kissat A/A pair
  measures the noise floor in place of five replicates.
- A drat-trim check is capped at 60 s per proof; the competition's proof
  checking is allowed far longer.

**Arithmetic.** worst case = instances × (runs × limit + DRAT checks × check
cap + 30 s overhead) = 32 × (5 × 60 + 4 × 60 + 30) = 18,240 s (304 min). The
builds are estimated at 10 minutes, and the job cap is 355 minutes of GitHub's 360.
The harness recomputes the worst case after the downloads and refuses to start
if it does not fit what remains of its 19,800 s budget. It never shortens a run
to make it fit.

**Reading the table.** The Kissat A/A difference is this device's resolution. A
PAR-2 difference between two arms that is smaller than the A/A difference is
not resolved by one run.

**Outputs.** These go to `$RUNNER_TEMP/competition`, uploaded as the
`competition-baseline` artifact:
- `results.csv`: one row per run (verdict, certificate, solved, wall time, PAR-2);
- `summary.md` and `summary.json`: per arm, stratum, family and rung, plus A/A;
- `run.json`: seeds, limits, tool paths with SHA-256 and versions, host, arithmetic;
- `order.tsv`: the run order;
- `work/runs/`: each run's stdout and stderr.

`test_competition.py` drives the harness with stub solvers that speak each
arm's output contract. CI runs it with the other benchmark unit tests. Each of
its plants turns a named check red: an invalid model, a rejected refutation,
drat-trim exiting 0 without `s VERIFIED`, an unproven UNSAT that contradicts
verified models, certified evidence that contradicts GBD, an exit status that
disagrees with its report, a checker timeout, the PAR-2 charge for a timeout, a
budget too small for the sample, a run that would need shortening, regime-C
drift, a download whose hash differs, a malformed manifest, a missing run, and
the seeded schedule.

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
from the EigenScript emitter. The ordering pin requires the exact ordered
token stream; it does not imply that every reordering changes search counters.
Swapping zero-based vertex clause-blocks 1 and 2 of 3x3 was measured to leave
normalized EMS-VM stdout byte-identical to the regime bank, while the identity
check rejects that input. The regime bank therefore does not detect that
reordering. Additional comparisons anchor 3x3 directly to the existing
`tests/fixtures/tseitin_torus_3x3_odd.cnf` and 4x4 to the emitter capture in
[`oracle/tseitin_torus_4x4_odd.cnf`](oracle/tseitin_torus_4x4_odd.cnf).
Neither anchor is generated by the identity model. The 4x4 capture comes from
this emitter, so it cannot establish the emitter's initial correctness. Its
additional coverage is bank corruption or weakening/drift of the identity
model. In the single-token mutation experiment, the model rejected 1,160 of
1,288 mutations; the 128 accepted mutations were all `0` to `-0` terminators.
The anchor adds no rejection of semantically meaningful faults in that sweep.
Comments and whitespace are ignored; clause/literal order remains significant.

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
and literals intact. Before any solver runs, `cnf_preservation.py` independently
parses the source (allowing that trailer) and prepared file (allowing no trailer).
It validates the header, literal bounds, terminated clauses and actual clause
count, requires a four-token header line, and compares ordered token tuples
per data line. It ignores comments, blank lines and within-line whitespace,
but preserves LF-delimited data-line boundaries. Unused declared variables
and empty clauses are legal. The post-condition requires Python 3's standard library.

Emission and input preparation precede all solver arms: they are **differential
blind spots**. Agreement can hold after a shared wrong-instance or normalization
bug. The torus check verifies the named encoding; the preparation post-condition
guarantees that header and literal tokens retain their data-line grouping,
modulo the documented trailer, comment and whitespace handling. It therefore
rejects moving a literal onto the header line, which the two parsers treat
differently. Output normalization is
also shared by the VM/AOT byte comparison; its deliberately narrow timing-field
strip defines which bytes that comparison observes. The regime banks check
normalized VM output at both preflights, and the AOT byte plant checks that an
added non-timing line remains observable. Original fixtures are
unchanged; this entry point does not test EMS's handling of original trailers.

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

`--selftest` starts separate executions of **this invocation's harness file**
through its normal CLI. `native_oracle_selftest.sh` injects faults at production
boundaries; it never invokes a comparator. `oracle_selftest.py` derives every
production `fail` call from the entry script and its recursively followed
`source`/`.` graph, masking comments, literal strings and heredocs while retaining
command substitutions. Source paths may be literal or use `$ROOT`; unresolved
dynamic source paths fail enrollment. There is no hand-maintained list of
required sites or total count.
Each derived file/function/ordinal must have an enrolled case, and every case's site
must still exist. Adding an uncovered gate breaks even a partial selftest
before solving; the `enrollment` plant adds such a gate in a temporary script
and requires exactly that rejection. A reverse-membership plant removes an
enrolled failure site and requires the missing-site diagnostic. The
`enrollment-sourced` plant adds a gate two source edges away from the entry
script; the existing unknown-plant gate in the sourced helper is enrolled too.

The failure reporter records the source filename and site, and separate
temporary-path context. A negative case requires its intended site, exit status, and the
**entire expected diagnostic: subject, class and evidence**. It also compares
the printed diagnostic with that expectation; a wrong instance name, wrong
class, different evidence, or an unrelated failure is a `MISS`. Expectations
come from the case catalog, never from observed diagnostics. A full run also
requires a runtime failure witness for every eligible production site. Gates
requiring unavailable AOT tools stay enrolled and print explicit case skips;
they contribute no successful witnesses.

Positive controls check complete per-instance verdict lines and summary counts.
The trailer control sends the repo's real SAT and UNSAT `%` fixtures through
production preparation and all enabled solvers. The normalization-corruption
plant substitutes a header-consistent SAT formula after the real normalizer;
it must fail the preservation post-condition before solver agreement could
conceal it. Other controls exercise configuration and I/O failures, parsers,
identity/fixture/regime checks, oracle comparisons, both vacuity checks, and all
completion counts. Fixture plants corrupt reference copies, testing bank drift.

Build-failure controls plant a script exiting 7: auto must complete real file
solves with every AOT status skipped and the AOT count zero; on must fail. The
auto control seeds stale AOT state. An intact full selftest intentionally exits
**1**, with every eligible negative case `RED` and positive controls `PASS`.
Missing enrollment, missing detection or wrong attribution prints `MISS` and
exits **2**. All production probes remain sequential.

`--selftest-case NAME` runs one case and explicitly labels the result partial;
an unknown or unavailable-only selection cannot pass. `--plant NAME` exposes
the fault injection for diagnosis and then follows the normal production path
with its raw exit status. For example:

```bash
AOT_BINARY=/tmp/ems_aot benchmarks/run_native_oracle.sh --selftest-case regime-3x3
AOT_BINARY=/tmp/ems_aot benchmarks/run_native_oracle.sh --plant vertex-order
```

Unreadable or unopenable CNFs fail as `[input-open]`; read/normalization errors
are `[input-read]`, and actual unsupported SATLIB tail data is `[input-trailer]`.

The initial [validation transcript](NATIVE_ORACLE_VALIDATION.md) records the
clean run, planted faults, comparator mutations, and measured budget limits.
The [round 2 transcript](NATIVE_ORACLE_ROUND2.md) records the wrong-rung
regression going from a silent pass to a named failure and the new controls.
The [round 3 transcript](NATIVE_ORACLE_ROUND3.md) records production call-site
deletions, the ordering measurement, and the second input anchor.

The [round 4 transcript](NATIVE_ORACLE_ROUND4.md) records shared-preparation
post-conditions, derived enrollment, exact attribution and their mutations.
