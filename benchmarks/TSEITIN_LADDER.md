# Tseitin torus ladder — pre-registration

Registered **2026-07-29 ~11:10 CDT, before any ladder data was collected.**
Predictions below are committed ahead of the run so the result can falsify
them. Do not edit the predictions after reading results — append an outcome
section instead.

> **2026-07-30:** every counter in this document up to the *Post-soundness-fix
> status* section at the bottom was measured on the pre-fix solver (#74,
> `clause_locked`). Read that section before comparing against any number here.

## What is being measured

Resolution refutation size, clause space, and depth for Tseitin formulas over
a `rows x cols` toroidal grid with odd total charge (UNSAT). CDCL emits a
resolution refutation, so `resolutions` / `learnt_lits` are proof-size
measurements, `peak_learnts` is clause space, `max_level` is depth.

Tseitin refutations require size `2^Omega(e)` where `e` is the graph's
expansion (Urquhart 1987). For an `r x c` torus the expansion is governed by
`min(r, c)`. That gives two distinct axes, and separating them is the point of
this ladder:

- **Expansion axis** — the square cases `3x3, 4x4, 5x5`. This is where the
  exponential is claimed to live.
- **Fixed-expansion axis** — `4x4, 4x5, 4x6, 4x7`. The formula grows while
  `min(r,c)` stays at 4, so hardness should grow much more slowly.

## Prior measurements (already banked, this box)

| case | resolutions | conflicts | wall |
|---|---|---|---|
| 3x3-odd | 1,974 | 673 | ~1.7s |
| 4x4-odd | 95,516 | 27,388 | ~450s |

3x3 → 4x4 is **x48 in resolutions** for one step of the expansion axis.
Reference for the cheap axis, measured at rows=3: 3x3 → 3x4 → 3x5 → 3x6 gave
resolutions 1,974 → 5,008 → 6,747 → 11,888 (x2.5, x1.3, x1.8).

## Ladder and caps

Ordered cheap-and-certain first, with 5x5 placed early enough to get real time.

| order | case | cap |
|---|---|---|
| 1 | 4x4 | 30 min (re-confirm the banked number) |
| 2 | 4x5 | 90 min |
| 3 | 5x5 | 6 h |
| 4 | 4x6 | 3 h |
| 5 | 4x7 | 3 h |

## Predictions

1. **Expansion axis stays exponential.** 5x5 resolutions `>= 20x` the 4x4
   figure, i.e. `>= ~1.9M`. A 5x5 result within ~5x of 4x4 falsifies the claim
   that `min(rows,cols)` is the hardness axis — suspect the generator (is the
   charge actually odd? are all four incident edges distinct?) before
   suspecting Urquhart.
2. **Fixed-expansion axis is much flatter.** Each 4xN → 4x(N+1) step multiplies
   resolutions by roughly 1.3x–5x, matching the rows=3 reference. A step above
   ~20x would mean the rectangular axis is also exponential and the
   two-axis story is wrong.
3. **Space grows far slower than size.** `peak_learnts` grows sub-linearly in
   `resolutions` — the learnt-DB reduction bounds it. If `peak_learnts` tracks
   `resolutions` proportionally, clause-DB reduction is not doing its job and
   that is a solver finding, not a proof-complexity one.
4. **5x5 may not finish.** Extrapolating x48 on size and the observed
   ~265x wall-clock blowup from 3x3 → 4x4, 5x5 plausibly exceeds the 6h cap.
   A capped result is still a result: the progress trajectory
   (conflicts vs elapsed) is banked either way and bounds the answer from
   below.

## Where results land

`~/eigenminisat-runs/tseitin-ladder/` — **never `/tmp`**, which this box wipes
on its daily ~05:57 reboot.

- `banked.log` — one `DONE` / `TIMEOUT` / `KILLED` line per case: the record.
- `results.log` — full driver history including every attempt.
- `<case>.log` — per-case progress trajectory, accumulated across attempts.

## Operational notes

- `benchmarks/run_tseitin_ladder.sh` is **resumable and idempotent**: cases
  already in `banked.log` are skipped, so re-running after the daily reboot
  continues the ladder. Re-running is always the correct recovery action.
- A `@reboot` cron entry relaunches it automatically after the daily reboot.
- A `flock` guard prevents the cron resume from racing a manual run — this is
  a 4GB box and the ladder must be the only heavy job.
- Progress lines are emitted every 300s with `stdbuf -oL`, so a case killed
  mid-run still leaves a conflicts-vs-time trajectory instead of nothing.
- Proof (DRAT) recording is deliberately **off** for this ladder: proofs buffer
  whole in memory and a multi-million-step refutation would exhaust RAM.

## Amendment 1 — 2026-07-29 12:50 CDT (mid-run, operational only)

Recorded while the run is in progress, before any conclusion is drawn.
**No prediction above is edited.** Only a timeout cap changed; a cap is an
operational parameter, not a hypothesis, and 4x5 produces the same number
whenever it is produced.

**What happened.** 4x4 closed in 429s (95,516 resolutions, matching the
previously banked figure exactly through the budgeted-session path). 4x5 then
**exhausted its 90-minute cap without closing**, having reached 452,569
resolutions at 4,959s and still climbing.

**Consequence for the schedule.** The 4xN axis is materially slower at
`min = 4` than the rows=3 reference suggested, so the 3h caps on 4x6 and 4x7
are near-certain to time out as well. That would spend ~6h producing lower
bounds on the *cheap* axis while 4x5 — the case that actually tests
prediction 2 — stays unmeasured.

**Change.** `benchmarks/tseitin_second_pass.sh` waits for the first pass to
release the ladder lock and re-runs **4x5 with a 4.5h cap** in the idle window
before the ~05:57 reboot. Nothing else is altered.

**Standing of prediction 2 as of this amendment.** Predicted band was
1.3x-5x per 4xN step, with ~20x set as the falsification threshold. Observed
so far: `>= 4.74x` and *unfinished*, so this is a lower bound, not a
measurement. The narrow band will be exceeded; whether the two-axis story
breaks depends on where 4x5 actually lands, and a lower bound cannot settle
that. This is exactly why the cap was raised rather than the prediction
reworded.

**Standing of prediction 1.** Unaffected, and note that a *timeout* can still
confirm it: prediction 1 is a `>=` claim (5x5 `>=` ~1.9M resolutions), so a
5x5 that exceeds that figure without closing confirms it from below. Only a
5x5 that closes *small* could falsify it.

## Amendment 2 — 2026-07-29 18:50 CDT (mid-run, operational only)

Again: **no prediction above is edited.** Only the remaining schedule changes.

**State after the first pass.**

| case | resolutions | wall | status | ratio vs 4x4 |
|---|---|---|---|---|
| 4x4 | 95,516 | 429s | DONE | — |
| 4x5 | >= 452,569 | >5,400s | TIMEOUT | **>= 4.74x** |
| 5x5 | >= 1,194,575 | >21,600s | TIMEOUT | **>= 12.5x** |

**Both registered ratio predictions are unresolved, and neither is confirmed.**
5x5 reached only 12.5x against a `>= 20x` prediction, so prediction 1 is *not*
confirmed from below the way Amendment 1 hoped — it needs ~1.9M and stopped at
1.19M. Observed steady rates: 4x5 ~91 resolutions/s, 5x5 ~57 resolutions/s.

**My time estimates in the original registration were wrong by roughly 5-10x.**
Stating that plainly rather than quietly re-tuning: the caps were set from a
3x3->4x4 extrapolation that badly underestimated how the per-conflict cost
grows with the formula. That estimation error, not the hardware, is what cost
this run its headroom.

**Change.** 4x6 was killed mid-run (strictly harder than a 4x5 that could not
close in 90 min, so a guaranteed timeout), 4x7 dropped, and the whole
remaining window given to **4x5 alone with a 9.5h cap** (18:50 -> 04:20,
leaving buffer before the ~05:57 reboot). The `@reboot` cron now resumes the
same single-case plan.

**Why 4x5 and not 5x5**, given ~10.9h left and only room for one:
- A closed case is a **measurement**; every other outcome is a bound. 4x5 is
  by far the likeliest of the remaining cases to close, so it is the only
  route to a second real number tonight.
- Prediction 2 is the claim most likely to be *wrong* — the whole two-axis
  framing rests on the rectangular axis being flat, and at `>= 4.74x` it is
  already leaving the predicted 1.3x-5x band. Testing your own weakest claim
  beats adding support to the stronger one.
- 5x5 would need ~9.25h from scratch just to cross 1.9M (the search is
  deterministic, so a shorter re-run only re-treads the same trajectory and
  banks nothing new). That would buy a one-directional bound instead of a
  measurement.

**Left open, and worth a follow-up run:** 5x5's `>= 12.5x` sits well below the
48x measured for 3x3 -> 4x4. If 5x5's true ratio lands near 15-25x, the
expansion-axis multiplier is *decreasing*, which contradicts the rising-
multiplier pattern pigeonhole shows. This ladder cannot settle that on this
hardware — it needs either much more time or a faster runtime.

# Outcome

Banked 2026-07-29 20:40 CDT. Written after the predictions above, which are
unedited. **5x5 is still running** — see the open item at the end.

## Measurements (closed cases only)

| case | vars | clauses | resolutions | conflicts | learnt_lits | peak_learnts | max_level | wall |
|---|---|---|---|---|---|---|---|---|
| 3x3 | 18 | 72 | 1,974 | 673 | 3,557 | 143 | 11 | 1.7s |
| 4x4 | 32 | 128 | 95,516 | 27,388 | 208,781 | 832 | 20 | 429s |
| 4x5 | 40 | 160 | 551,098 | 135,285 | 1,109,225 | 1,619 | 27 | 6,285s |

## Prediction 2 — band missed, core claim CONFIRMED

Predicted 1.3x-5x per fixed-expansion step, with ~20x as the falsification
threshold. **Measured 4x4 -> 4x5 = 5.77x.**

The narrow band is missed (5.77 > 5), so the prediction as stated is wrong at
the margin. The claim it was testing survives cleanly: 5.77x is nowhere near
the 20x that would mean the rectangular axis is also exponential.

**The axis separation is real and now measured on both sides with closed cases:**

| axis | step | multiplier |
|---|---|---|
| expansion (`min(r,c)` grows) | 3x3 -> 4x4 | **x48.4** |
| fixed-expansion (formula grows) | 4x4 -> 4x5 | **x5.77** |

The expansion axis is **8.4x steeper per step**. That is the ladder's central
result and it holds.

## Prediction 3 — CONFIRMED

Space grows far slower than size; the size/space ratio climbs steadily, so
learnt-DB reduction is bounding clause space rather than letting it track proof
size.

| case | resolutions | peak_learnts | size/space |
|---|---|---|---|
| 3x3 | 1,974 | 143 | 14 |
| 4x4 | 95,516 | 832 | 115 |
| 4x5 | 551,098 | 1,619 | 340 |

## Prediction 4 — correct

5x5 did exceed its 6h cap, and the trajectory bounded it from below as designed.

## Calibration lesson

4x5 closed at **6,285s** against an original cap of 5,400s — it missed by
**884 seconds, under 15 minutes.** The first cap was within ~15% of sufficient
and still produced nothing but a bound. Two things follow for future long runs
on this box: budget caps with a real margin rather than a point estimate, and
prefer one case with generous headroom over several that each nearly finish.
A case that nearly closes banks exactly as little as one that never starts.

## Open: prediction 1

Unresolved. 5x5 needs `>= ~1.9M` resolutions to confirm; the 6h attempt reached
1,194,575 (`>= 12.5x`) without closing. Relaunched 2026-07-29 20:35 with an
8.5h cap. Outcomes:

- closes anywhere `>= 1.9M` -> prediction 1 confirmed
- closes below `~1.9M` -> prediction 1 **falsified**, and the expansion-axis
  multiplier is *decreasing* (48.4x then under 20x), which would contradict the
  rising-multiplier pattern pigeonhole shows and is the more interesting result
- times out again -> bound tightens toward ~18x, still unresolved

Note the asymmetry: a timeout can confirm this prediction but cannot falsify
it. Only a closed 5x5 can do that.

## Prediction 1 — UNRESOLVED (final, 2026-07-30 05:05)

5x5 timed out again at the 8.5h cap: **1,549,543 resolutions = 16.22x**, short
of the `>= 20x` threshold by 360,777. Not confirmed, not falsified. Two
attempts totalling 14.5h of compute produced only a lower bound, and because
there is no single-solve resume the second attempt re-derived the first
attempt's entire trajectory before adding anything.

| attempt | cap | reached | ratio |
|---|---|---|---|
| 1 | 6h | 1,194,575 | >= 12.5x |
| 2 | 8.5h | 1,549,543 | >= 16.22x |

### Root cause of every bad estimate this run: the rate decays

Measured on attempt 2 — resolutions/s falls by half over the run as the learnt
database grows:

| elapsed | resolutions | rate |
|---|---|---|
| 0.4 h | 157,860 | 76 res/s |
| 1.3 h | 400,993 | 65 res/s |
| 2.6 h | 660,221 | 52 res/s |
| 4.4 h | 980,865 | 45 res/s |
| 6.3 h | 1,267,570 | 39 res/s |
| 8.4 h | 1,549,543 | 35 res/s |

Every projection made during this run extrapolated an early-phase rate and
therefore overshot — three times, in the same direction, for the same reason.
**Any cap or ETA for this workload must assume a decaying rate.** A linear
extrapolation from the first hour is worthless. If 5x5's true size is near the
48x that 3x3 -> 4x4 showed (~4.6M resolutions), finishing it in the
interpreter needs on the order of 40h, not one night.

### What should have been done first

1. **Probe before scheduling.** A 10-minute run measuring rate *and its decay*
   would have shown 5x5 was out of reach and collapsed the five-case ladder
   into one decision. Instead the whole schedule was extrapolated from a single
   data point (3x3 -> 4x4).
2. **Check that a timeout is recoverable before relying on timeouts.** The
   design leaned on "a capped case still yields a trajectory." True, but nearly
   worthless: with no resume the trajectory cannot be extended, only
   re-derived. That makes cap sizing a bet-the-run decision rather than a
   hedge, and it was sized as though it were a hedge.
3. **Question the runtime instead of accepting it.** "The square axis goes
   intractable under the interpreter" was recorded as a *finding* and then a
   night was spent confirming it, while `ouroboros/aot` exists. Fixing the
   instrument comes before spending nights measuring around it.

### Recommended next step — not another night of interpreter 5x5

Either of these before any further 5x5 attempt:

- **AOT feasibility probe** (`ouroboros/aot`): can the solver be compiled, and
  what is the real speedup on this workload? If it lands anywhere near the
  order of magnitude the AOT path has shown elsewhere, 5x5 becomes a
  single-session run rather than a multi-day one.
- **Serializable CDCL session state.** `cdcl_begin`/`cdcl_step` is already a
  checkpoint mechanism in every respect except that the session cannot be
  written to disk and reloaded. With that, a capped run resumes instead of
  restarting, and long-run cap sizing stops being load-bearing.

The ladder's central result (axis separation, x48.4 vs x5.77) does not depend
on 5x5 and stands.

# Adversarial review — 2026-07-30

Review of this document's own claims. Two are withdrawn.

## F1 — RETRACTED: the axis-separation result

The "expansion axis is 8.4x steeper" headline compared **steps with unequal
variable increments**: 3x3 -> 4x4 adds 14 variables, 4x4 -> 4x5 adds 8. Part of
the x48.4 vs x5.77 gap is simply the bigger jump.

Normalised per variable:

| step | axis | +vars | ratio | per-variable |
|---|---|---|---|---|
| 3x3 -> 4x4 | expansion | +14 | x48.39 | 1.319x |
| 4x4 -> 4x5 | flat | +8 | x5.77 | 1.245x |
| 4x5 -> 5x5 | expansion | +10 | `>=`x2.81 | `>=`1.109x |

Growth per variable is **monotonically decreasing and indifferent to which axis
moved.** And the one clean single-dimension expansion step available
(4x5 -> 5x5, where `min` goes 4 -> 5) is `>=`2.81x — *lower* than the flat
step's 5.77x, i.e. currently the opposite direction.

Note the design confound: starting from a square torus you cannot raise
`min(r,c)` without adding both a row and a column, so "square cases" bundles
expansion with a double-size jump. The step that breaks the confound is a
**size-matched pair: 4x6 (48 vars, min=4) vs 5x5 (50 vars, min=5)**. 4x6 was
killed mid-run as "more of the same on the cheap axis" — that judgement
destroyed the control for the headline claim.

**Status: the two-axis story is unsupported by this data.** Prediction 2's
falsification threshold (20x) still was not crossed, so nothing here shows the
rectangular axis *is* exponential either. The question is open, and 4x6 is the
cheapest experiment that would move it.

## F2 — WITHDRAWN: prediction 3 was vacuous

"Space grows sub-linearly in size" is true but says nothing about Tseitin.
`resolutions` is cumulative and unbounded; `peak_learnts` is pinned to the
reduction schedule — `learnt_limit` starts at 4 and grows +2 per reduce run, so
`peak_learnts ~= 4 + 2 * reduce_runs` (143, 832, 1619, 1842 imply ~70, ~414,
~808, ~919 reduce runs). The ratio climbing is a restatement of the DB policy.
A real size-vs-space result needs proof space for a *fixed* refutation.

## F3 — REFUTED (a review hypothesis, not a prior claim)

Hypothesis: the rate decay (76 -> 35 res/s) is an implementation artifact,
because `count_active_learnts` is O(total clauses) and runs every conflict.
Tested with an incrementally maintained counter: 4x4 went 429.2s -> **410.4s,
just 4.4%**, with byte-identical counters. **Refuted.** The decay is not that
scan, and the conclusion that 5x5 is out of reach under the interpreter stands.

## F4 — the O(1) counter is a bad trade regardless

It introduces an invariant only `build_cdcl_state` maintains. The hand-built
`reduce_state` in `tests/test_solver.eigs` broke instantly with "cannot compare
none and num". `count_active_learnts` derives from the arrays and needs no
invariant — worth keeping for 4%, especially with the EigenOS ROM-bundle path
constructing state independently.

## What survives the review

- **The generator is genuine.** Every edge appears in exactly two vertices'
  incident lists, every vertex has degree 4 with four distinct edges, verified
  for 3x3, 3x4, 4x4, 4x5, 5x5, 3x7, 6x4. That incidence-exactly-2 property is
  what makes XOR-ing all vertex constraints cancel every edge and leave
  `0 = sum(charges)`, so odd charge really does imply UNSAT.
- **The closed measurements**: 3x3 = 1,974, 4x4 = 95,516, 4x5 = 551,098.
- **The DRAT oracle.** Only one `add_cdcl_clause` site emits (learnt=1);
  compaction does not route through it, so there is no double-emission. With
  drat-trim verification plus the planted-fault rejection, the claim holds.
- **Pigeonhole == coloring**, refined: the CNFs are *not* byte-identical (clause
  order differs) but have identical variable and clause counts and produce
  byte-identical solver counters. Same principle, as claimed.

# Post-soundness-fix status — 2026-07-30

Every counter above this section was measured on the **pre-fix solver**: the
`clause_locked` position-0 bug (fixed in `0a9fe58`, #74) let learnt clauses
still serving as reasons be deleted, so the search trajectory — and therefore
every counter — differs under the fixed solver. The UNSAT verdicts stand (odd
charge is UNSAT by construction), but pre-fix counters must not be compared
against post-fix runs.

Post-fix re-measurements (this box, same generator, default policies):

| case | resolutions | conflicts | wall | pre-fix banked |
|---|---|---|---|---|
| 3x3-odd | 1,850 | 619 | ~2.2s | 1,974 / 673 |
| 4x4-odd | 96,733 | 27,421 | ~671s | 95,516 / 27,388 |

- Counter shifts are small (3x3 −6.3%, 4x4 +1.3% in resolutions) — the searches
  are different but the family's shape is unchanged. The 3x3 → 4x4 step is now
  **x52.3** (was x48.4).
- Wall times are single runs (counter claims need n=1; the solver is
  deterministic). The 4x4 wall (671s vs ~450s pre-fix) is not a measured
  regression claim — the fix makes `clause_locked` O(width) and the box was not
  idle; an n=5 comparison would be needed to attribute it.
- **4x5 and 5x5 are not re-measured.** 4x5 cost 6,285s pre-fix and 5x5 never
  closed in 14.5h; both stay blocked on a faster tier. The AOT probe this
  document recommended was run 2026-07-30 and **failed to compile**: the
  emitter has no `dot_assign` statement emission (72 sites in
  `lib/solver.eigs`), filed as ouroboros#86. That issue is now the critical
  path for 5x5 and for the 4x6-vs-5x5 control from the F1 retraction.
- The review's retractions (F1 axis-separation, F2 vacuous space prediction)
  are methodological and stand regardless of the counter shifts. "The closed
  measurements" listed under *What survives the review* survive only as
  pre-fix values — superseded by the table here for 3x3 and 4x4, and 4x5's
  551,098 carries the pre-fix caveat until re-measured.

## Third regime check — EigenScript #772 (v0.34.0, 2026-07-31): NO-OP at these sizes

EigenScript #772 (fixed in v0.34.0) revealed the runtime had been silently
breaking the running loop every 1e8 cumulative *in-frame* iterations, which
put every long ladder run under suspicion of a third counter regime.
Re-measured on the released v0.34.0 (tag-verified binary):

| case | resolutions | conflicts | vs post-clause_locked bank |
|---|---|---|---|
| 3x3-odd | 1,850 | 619 | **byte-identical** |
| 4x4-odd | 96,733 | 27,421 | **byte-identical** (655s wall) |

The pre-#772 cap counter reset at every call frame, and this harness solves
via `cdcl_begin`/`cdcl_step` with a 300-conflict budget per step — each step
is its own frame and stays far under 1e8 iterations, so the cap never fired
inside the ladder. **Regimes 2 and 3 coincide: the post-clause_locked bank
(2026-07-30) stands as-is on v0.34.0.** Only two counter regimes exist in
this document: pre-clause_locked (all numbers above the post-fix section)
and post-clause_locked (its table, unchanged by #772). Caveat kept: this
no-op finding is about the *stepped* harness — a monolithic solve call at 4x5+
scale on a pre-v0.34.0 runtime could still have crossed 1e8 in one frame,
so the 4x5 551,098 figure keeps its pre-fix caveat on both counts.

## Off-box control launch — 2026-07-31 (operational note, no new predictions)

The F1-retraction control (**4x6, 48 vars, min=4 vs 5x5, 50 vars, min=5**)
launched as two HF Space CPU lanes — `ems-tseitin-4x6` and `ems-tseitin-5x5`,
tag `tseitin-control-2026-07-31`, results to the private
`InauguralSystems/eigenminisat-results` dataset. Pins: EigenScript v0.34.0
(tag), EigenMiniSat 92cb48b. Harness: `benchmarks/tseitin_ladder.eigs`
(stepped sessions, progress every 300s), no cap — the calibration lesson
applied; periodic log uploads mean a killed lane still banks a bound.

**Preflight gate, run per-lane before the long case:** 3x3 and 4x4 must
reproduce the post-clause_locked v0.34.0 bank **byte-identically**
(1,850/619 and 96,733/27,421 resolutions/conflicts). Counters are the result
of record and the control compares lane counters against the devbox-banked
4x4, so cross-host counter portability is load-bearing; a preflight mismatch
kills the lane loudly and is itself a finding. Wall times from the lanes are
per-host color only and must not be compared with devbox walls.

What the control decides when both cases close: if 5x5 resolutions clearly
exceed 4x6's at matched size (~±2 vars), the expansion axis survives the F1
retraction; if they land close, the "min(r,c) is the hardness axis" story is
dead at this scale. Prediction 1's `>= 20x` threshold (>= ~1.9M resolutions
vs the 4x4 bank) also finally resolves if 5x5 closes.

## Control result — 2026-08-05: both lanes closed; the expansion axis survives

Both control lanes closed UNSAT with green preflights (3x3 and 4x4
byte-identical to the devbox v0.34.0 bank on both lanes, so every number
below is one counter regime — post-clause_locked — and directly comparable).
The 4x6 lane was then reused to re-measure 4x5 post-fix, retiring the last
pre-fix figure in the ladder.

**The post-clause_locked bank, now complete (resolutions / conflicts):**

| case | vars | min(r,c) | resolutions | conflicts | host |
|---|---|---|---|---|---|
| 3x3 | 18 | 3 | 1,850 | 619 | devbox + both lanes (preflight) |
| 4x4 | 32 | 4 | 96,733 | 27,421 | devbox + both lanes (preflight) |
| 4x5 | 40 | 4 | 489,112 | 118,082 | HF lane (supersedes pre-fix 551,098) |
| 4x6 | 48 | 4 | 3,798,224 | 695,815 | HF lane |
| 5x5 | 50 | 5 | 13,292,633 | 3,305,826 | HF lane |

**The control verdict: at matched size, min=5 costs x3.50 what min=4 costs**
(5x5 = 13,292,633 vs 4x6 = 3,798,224; 50 vs 48 vars). That is not "close" —
the expansion axis survives its retraction *as measured at this scale*. The
per-variable view that drove the F1 retraction agrees now that the control
exists: the flat step 4x5→4x6 grows x7.77 over 8 added vars (x1.29/var),
while the cross-axis step 4x6→5x5 jumps x3.50 over 2 added vars (x1.87/var).
Raising min(r,c) is the more expensive way to add variables, which is what
"expansion drives hardness" predicts and what the pre-retraction data could
not legitimately show.

**Prediction 1 — CONFIRMED.** The threshold was 5x5 >= 20x the 4x4 bank
(>= ~1.9M resolutions). Measured: **x137.4**. For the axis ladder: the
expansion steps are 3x3→4x4 = x52.3 and 4x4→5x5 = x137.4 — the multiplier
itself grows, as an exponential-in-min(r,c) family should — while the flat
steps at min=4 run x5.06, x7.77.

Scope kept honest: this is one family, one size point per step, an
upper-bound instrument (the solver's refutation bounds proof size from
above), and the x3.50 is a two-case comparison, not a fitted curve. It
settles what the retraction demanded settled — the size-matched control now
exists and it did not kill the axis — nothing more.

Operational notes for the next long lane: free HF Spaces auto-sleep on HTTP
inactivity (dataset polling generates none) — the 5x5 lane slept at 24.0h /
8.55M resolutions and was restarted 2026-08-02; the deterministic rerun
retraced and closed at 76.6h wall (run-1 partial preserved as
`run1-partial-24h.log` in the dataset). Keep-alive pings must target the
Space itself; a devbox cron entry (every 30 min) plus a daily monotone
frontier snapshot in the dataset is the pattern that held. Wall times above
are per-host color; counters are the record.

---

## RE-MEASUREMENT REQUIRED — 2026-08-09 (#84 / #85 / #86)

Every number above was measured under three CDCL defects that have since been
fixed, and all three change the search:

- **#84** — variable activity never rescaled, so `var_inc` saturated at 1e308 on
  conflict 13,828 and VSIDS collapsed to static lowest-index-first branching.
  3x3 (619 conflicts) ran entirely in the healthy regime; 4x4 (27,388) spent
  most of its run in the degenerate one; 4x5 and beyond were wholly degenerate.
- **#85** — the deletion key packed LBD and activity into one scalar with a
  fixed 1e6 factor, so LBD stopped being the major term at ~13,805 conflicts.
- **#86** — the learnt DB was sized by a constant (4, +2 per reduce run) rather
  than against the instance.

Re-measured on the same instance and binary, options-selected arms (BASELINE.md
has the full table):

| case | resolutions (banked, ALL-OLD) | resolutions (new defaults) |
|---|---|---|
| 3x3 | 1,974 *(1,850 re-run under ALL-OLD)* | 1,681 |
| 4x4 | 95,516 *(96,733 re-run under ALL-OLD)* | 33,873 |
| 4x5 | 551,098 | **not re-measured** |
| 5x5 | (never closed) | **not re-measured** |

The ALL-OLD re-runs reproduce the banked 4x4 to within 1.3%, so the banked
figures are sound *for the policy they were measured under*.

**What this does and does not do to the ladder's result.** The expansion step
`3x3 -> 4x4` moves from **x48.4** to **x20.2**. The ladder's central claim is
not that multiplier but the *separation* between the expansion axis and the
fixed-expansion axis (`4x4 -> 4x5 = x5.77`), and that comparison no longer has
both sides measured under the same policy. Nothing here refutes the
separation — 4x5 has simply not been re-run. Until it is, treat every
multiplier above as a measurement of the old DB/heuristic policy as much as of
the formula family, which is exactly the confound #86 was filed about.

Cost of the re-measurement: 4x5 was 6,285 s under the old policy; the new
defaults closed 4x4 in 350 s against 769 s, so a 4x5 re-run is plausibly ~1 h
on this box and belongs on the off-box lanes rather than in a session.
