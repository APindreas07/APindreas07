# Lab round 6: results

**Verdict: both hypotheses fail every criterion.**

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC: sets > 0 (median) | P(loss) | dev | holdout 2024-26 | deflated Sharpe | result |
|----|------------|-------------------------------------------|-----------------------------|---------|-----|-----------------|-----------------|--------|
| L1 | Asian-range breakout at the London session (EURUSD, GBPUSD, USDJPY) | -1.37 / -4.8% / -32% | 0.0% (-1.31) | 100% | -0.41 (2012-16) | -0.42 | 0.000 | **FAIL** (all) |
| L4 | Weekly reversal after extreme weeks (7 majors + 21 crosses) | -0.14 / -0.2% / -3% | 6.7% (-0.13) | 63% | -0.37 (2008-16) | -0.19 | 0.000 | **FAIL** (all) |

- **Engine check:** an explicit per-day loop for L1 (EURUSD, f = 0.1, window to 10:00) reproduces the engine over
  2,920 trades with a maximum difference of 1.7e-18.
- **Rules:** `PREREGISTRATION.md`, pushed before any test.
- **Reproduce:** `python -m edge.lab.r6.research` (about 8 minutes).

**Observations.**
- **L1:** the London-session breakout loses consistently. Across the 10,000 random settings, none was profitable
  out of sample.
- **L4:** reversal after extreme weeks is essentially flat; there is no exploitable overreaction at the weekly
  horizon.

See `edge/lab/SUMMARY.md` for the picture across all rounds.
