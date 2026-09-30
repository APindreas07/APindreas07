# Lab round 5 (equity-regime and combined signals): results

**Verdict: all three hypotheses fail.** K3, the combination of the round-2 near-misses, is the closest
result so far, but it still fails four of the six criteria and loses money in the holdout.

- **Data:** TradeStation daily bars for the 7 majors and SPY, 2006-10 .. 2026-09-25. The 6-cross risk basket
  (AUD, NZD and CAD against JPY and CHF) is computed from the majors.
- **Rules:** `PREREGISTRATION.md`, pushed before any test was run.
- **Engine:** the return engine is the round-2 `Book` engine, validated earlier against an explicit loop. The K1
  and K2 position logic is itself written as an explicit day-by-day loop.
- **Direction check:** the basket fell 22-37% in 2008 and rose 10-28% in 2009, in line with SPY. This confirms
  the long-risk direction is coded correctly.
- **Reproduce:** `python -m edge.lab.r5.research` (about 5 minutes).

## Results (net of costs and swap)

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC: sets > 0 (median) | P(loss) | dev 2008-16 | holdout 2024-26 | deflated Sharpe | result |
|----|------------|-------------------------------------------|-----------------------------|---------|-------------|-----------------|-----------------|--------|
| K1 | SPY-regime risk-currency trend | -0.84 / -7.3% / -44% | 0.0% (-0.80) | 99% | -0.37 | -0.22 | 0.000 | **FAIL** (all) |
| K2 | Rebound after equity stress | -0.10 / -0.4% / -10% | 7.4% (-0.47) | 62% | -0.08 | +0.09 | 0.000 | **FAIL** (all) |
| K3 | G1 + G3 combined (new trial) | **+0.24 / +1.3% / -12%** | **67.6% (+0.19)** | 30% | **+0.54** | -0.41 | 0.000 | **FAIL** (c1, c3, c5, c6) |

## What it means
- **K1.** The equity-to-currency link was strong in 2008-09 but has weakened since about 2013. In 2022, for
  example, SPY fell about 20% while the yen crosses rose on Bank of Japan policy. Trading risk currencies on the
  equity trend lost money out of sample for every one of the 10,000 random settings.
- **K2.** Buying risk currencies after equity sell-offs is roughly break-even.
- **K3.** Diversifying the two near-misses helped:
  - development Sharpe 0.54, and 68% of random parameter pairs positive out of sample;
  - but the out-of-sample Sharpe of 0.24 is below the 0.3 bar, P(loss) is 30%, and the holdout is negative;
  - within the owner's limits (drawdown <= 10%, leverage <= 5x) it would have made about **0.09% a month**,
    against the 2% target;
  - after 19 trials, the deflated Sharpe rules out luck only for a far stronger result.

## Cumulative picture after 5 rounds
- 23 FX strategy families tested; none validated.
- The best candidate (K3) makes about a twentieth of the target within the risk limits.
- The evidence remains that liquid-FX price and technical signals do not support 2% a month at retail costs.

Chart: `results/equity.png`. All numbers are in `results/summary.json`.
