# EigenMiniSat AOT versus native MiniSat — 2026-09-10

The CDCL reduction precheck makes the production AOT solver **1.55x faster on
4x4 odd Tseitin**: five-run median process wall time falls from **15.711 s to
10.144 s**, a 35.4% reduction. Native MiniSat takes **0.266 s**, leaving a
**38.1x** wall-time gap. Native and EMS use different search policies; this gap
does not isolate language or compiler overhead. The native-performance target
and the unfinished 6x6 rung remain open.

The [machine-readable bank](native_aot_2026-09-10.json) retains all 45 timed
samples, stdout/stderr and native result files, VM references, input and binary
hashes, source revisions, build commands and summaries. Full local artifacts:
`/tmp/ems-native-20260910/wall-active-count`.

## Measurement

Host: Intel Celeron N3350, two cores, Linux x86-64. Both EMS binaries use
ouroboros `368603b` and its pinned EigenScript **v0.43.0** runtime
`a6c50fba6a6250ea347a34500d6c9fa503a5c931`. Baseline EMS is `ffa6b92`;
the candidate differs only in `cdcl_step`'s reduction precheck. The exact solver
patch and generated-C hash are in the bank. Native oracle:
`/usr/bin/minisat`, installed package `1:2.2.1-8build1`.

Both EMS arms run `--cdcl`, **regime C defaults**, with proof output disabled
for timing. MiniSat uses its own defaults. The existing native oracle validates
and prepares each CNF before timing. Every AOT sample must equal the complete
VM output except its trailing numeric `ms=` field; native output, result file,
exit status and its own conflict count must agree.

There are five repetitions per arm and input, in sequential groups with rotating
arm order. Process creation, parsing, solving, reporting and exit are inside the
external stopwatch. Build, preflight, warmup and validation are outside it.
No other build, suite or benchmark ran during these samples.

All times below are **seconds**, shown as median and observed min–max. The policy
for every EMS row is regime C; every native row uses MiniSat defaults.

| Input | Arm | Median | Min–max |
| --- | --- | ---: | ---: |
| Pigeonhole 6/5 | EMS baseline | 0.079682 | 0.070608–0.133804 |
| Pigeonhole 6/5 | EMS candidate | 0.077120 | 0.067904–0.097557 |
| Pigeonhole 6/5 | Native MiniSat | 0.007541 | 0.007351–0.011294 |
| Tseitin 3x3 odd | EMS baseline | 0.219606 | 0.218650–0.226152 |
| Tseitin 3x3 odd | EMS candidate | 0.201416 | 0.196816–0.209829 |
| Tseitin 3x3 odd | Native MiniSat | 0.009714 | 0.008334–0.010047 |
| Tseitin 4x4 odd | EMS baseline | 15.711226 | 15.634636–15.966564 |
| Tseitin 4x4 odd | EMS candidate | 10.144086 | 9.878219–10.361985 |
| Tseitin 4x4 odd | Native MiniSat | 0.266438 | 0.245767–0.290096 |

The 3x3 median improves by 1.09x, with separated observed ranges. Pigeonhole
ranges overlap substantially; no gain is claimed there. Native startup and
scheduler costs matter particularly on these very short instances.

Search is unchanged between EMS arms: conflicts are **140 / 592 / 9,986** for
pigeonhole / 3x3 / 4x4; the respective native counts are **138 / 731 / 84,150**.
EMS 3x3 and 4x4 resolutions remain **1,681 / 33,873**. Conflicts per second
across different policies are descriptive, not equivalent units of work.

Reproduction and runner interface: [NATIVE_TIMING.md](NATIVE_TIMING.md).
Production build command, from the ouroboros worktree:

```bash
env EIGS_DIR=/home/jon/src/wt/es-v043 \
  EIGS=/home/jon/src/wt/es-v043/src/eigenscript \
  bash aot/build.sh /home/jon/src/wt/ems-active-count-20260910/minisat.eigs \
  /tmp/ems-native-20260910/ems-active-count
```

The baseline used the same command with the `ffa6b92` EMS worktree and a separate
output. The production builder uses `-O3 -ffp-contract=off -march=native` and its
fixed alignment flags. The runner records caller-declared build provenance;
hashes alone do not prove a binary's relationship to its source.

## Change and attribution

A separate 199 Hz `perf record` profile on the real 4x4 workload attributed
about **36% inclusive** to `count_active_learnts`. A timing-only generated-C
probe replaced that numeric-list scan; its separate n=5 run measured 17.006 s
baseline versus 11.503 s probe. That experiment bounded the opportunity and
was not shipped. Its times are not mixed with the production A/B above.

The shipped change skips the reducer while the session's existing cumulative
`learnts - learnt_deleted` count is at or below its limit. It updates the
reported active count and preserves the exact reduction, peak, compaction and
restart schedule. The public reducer still scans its arrays, so direct callers
and hand-built states need no historical counter invariant. Compaction removes
clauses already counted as deleted; subtracting `compact_removed` again is wrong.

The candidate profile puts the counting routine at **0.36% inclusive** and
watched-literal propagation at **51.10%**. Generic indexing, reference counting
and cycle collection remain prominent. These are approximate diagnostic sample
shares with overlapping call stacks; they must not be added together. The next
performance investigation should profile that propagation path in the AOT.

## Correctness and review

- Native/VM/AOT oracle: **20 selected, 20 passed in all three arms**, including
  byte-exact regime-C anchors on 3x3 and 4x4.
- Full VM smoke, DRAT checks and size-1 proof benchmark: exit 0. AOT DRAT checks
  also passed: nine refutations verified, truncated proof rejected, SAT emitted
  no proof. The candidate's 3x3 proof is byte-identical to the baseline's.
- AOT differential fuzz, seeds 0–199: **200 instances**, four solver modes,
  **116 SAT / 84 UNSAT / 84 verified proofs / 0 failures**.
- AOT policy fuzz, seeds 0–39: **40 instances × six policies = 240 solves**,
  **138 verified proofs / 0 failures**. Reduction was reached in **60/240**
  solves; compaction, watch rebuilding and replay in **33/240** each.
- Six focused session cases pass. Eager/deferred/lazy each witness ten exact
  limit steps and nine strict crossings; eager/deferred each perform three
  compactions and continue learning afterward. All five planted faults fail.
- **27 timing-runner tests pass**, including production-preflight timeout and
  SIGINT/SIGTERM/SIGHUP cancellation, a signal during process creation, repeated
  cancellation during cleanup, and wrong or missing measurement evidence.
- Fresh Codex integration review passed. The compiler/runtime sources were
  unchanged; this is a solver change, not an AOT code-generation change.

Two review failures became mechanical checks. Comparing stepped and one-shot
solves alone accepted a one-conflict-delayed reduction because both used the
same faulty step function; the test now independently checks the prior metadata
count and exact reduction boundary. Killing one process group left the oracle's
GNU-timeout child group alive; the runner now owns cleanup of its full session
and tests real preflight cancellation before trusting a timing run.

## Larger-rung limit

An additional **unmeasured** 5x5 run with `--proof` enabled hit its **300-second
per-process cap** without a verdict or proof file. Its ordered torus identity
passed and native MiniSat returned UNSAT, but the candidate produced no completed
point and no DRAT check could run. This does not isolate proof-output cost, and
it is not a baseline/candidate speed comparison. No 6x6 result was obtained.
