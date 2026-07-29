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
