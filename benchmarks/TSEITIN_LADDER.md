# Tseitin torus ladder — pre-registration

Registered **2026-07-29 ~11:10 CDT, before any ladder data was collected.**
Predictions below are committed ahead of the run so the result can falsify
them. Do not edit the predictions after reading results — append an outcome
section instead.

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
