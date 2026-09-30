# Lab round 4 (multi-day holds): results

**Verdict: all three hypotheses fail every pass criterion.** Moving to multi-day holds fixed the cost problem
from round 3 but not the underlying one: **before any costs or swap, the signals themselves earn nothing.**
Over 2012-2023 their gross Sharpe ratios were -0.36 (J1), +0.07 (J2) and -0.34 (J3).

- **Data:** HistData bid bars built into daily bars that close at 17:00 New York. There are 16 pairs (7 majors
  + 9 Scandinavian and Central European (CEE) pairs) plus 21 crosses computed from the majors.
  - Period: 2012-01-02 .. 2026-09-24, 3,816 days common to all pairs.
- **Rules:** `PREREGISTRATION.md`, committed and pushed before any data was built or any test was run.
- **Engine check:** an explicit day-by-day loop for J2(20, 2.0, 10) reproduces the engine's positions on 34,338
  of 34,344 pair-days. The 6 differences are all on the final day, where the engine closes open trades. They
  have no effect on returns.
- **Reproduce:** `python -m edge.lab.r4.research` (about 22 minutes).

## Results (net of costs and swap)

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC: sets > 0 (median) | P(loss) | dev 2012-16 | holdout 2024-26 | deflated Sharpe | result |
|----|------------|-------------------------------------------|-----------------------------|---------|-------------|-----------------|-----------------|--------|
| J1 | Volatility-squeeze breakout, 7 majors + 21 crosses | -0.90 / -1.0% / -8% | 0.0% (-0.85) | 100% | -0.92 | -1.67 | 0.000 | **FAIL** (all) |
| J2 | Bollinger mean reversion, 9 Scandinavian / CEE | -0.76 / -1.8% / -16% | 0.0% (-0.99) | 99% | -0.26 | -0.47 | 0.000 | **FAIL** (all) |
| J3 | Moving-average trend, 9 Scandinavian / CEE | -1.01 / -4.6% / -29% | 0.0% (-1.17) | 100% | -1.69 | -1.33 | 0.000 | **FAIL** (all) |

**Where the losses come from.** Sharpe over 2012-2023 for the reference settings:

| id | net | without swap | gross (no costs, no swap) |
|----|-----|--------------|---------------------------|
| J1 | -1.01 | -0.60 | -0.36 |
| J2 | -0.69 | -0.17 | +0.07 |
| J3 | -1.29 | -0.43 | -0.34 |

The swap sensitivity is severe: 4% a year, charged in both directions. Even so, removing every cost leaves
nothing tradable.

- **The 2016 finding** that oscillator rules pay on managed CEE currencies does not hold in 2012-2026. J2 is flat
  before costs.
- **Trend on these pairs (J3)** lost money even before costs.
- **In the parameter Monte Carlo, none of the 30,000 random settings** (10,000 per hypothesis) had a positive
  out-of-sample Sharpe.

## Cumulative picture after 4 rounds
- **Tested:** 20 FX strategy families across daily, intraday and multi-day horizons, on majors, crosses and
  Scandinavian / CEE pairs.
- **Result:** none validated. The best out-of-sample results were the round-2 near-misses G1 and G3 (Sharpe
  about 0.2), both far from the target.
- **What the evidence says:** price-only technical signals on liquid FX have not carried a retail-tradable edge
  since about 2016. The agent will keep searching, but the honest expectation for the 2%-a-month target, on this
  evidence, is low.

Charts: `results/equity.png`, `results/param_mc.png`. All numbers are in `results/summary.json`.
