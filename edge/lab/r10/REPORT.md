# Lab round 10 (P1 with real financing): results

**Verdict: Q1 fails every criterion.** Replacing the flat swap charge with real interest-rate carry (OECD 3-month
rates, minus a 1% a year broker markup) improves the machine-learning model, but not nearly enough.

| | round 9 (P1, flat swap) | round 10 (Q1, real carry) |
|---|---|---|
| WF OOS 2017-23 Sharpe / per year / max DD | -0.88 / -2.5% / -20% | **-0.50 / -1.4% / -15%** |
| holdout 2024-26 Sharpe | -0.42 | -0.19 |
| development 2014-16 Sharpe | -0.51 | -0.01 |
| param MC: sets with OOS Sharpe > 0 | 2% | 14% |
| P(loss), return MC | 99% | 92% |
| deflated Sharpe | 0.000 | 0.000 |

- **Carry check:** June 2023, long USDJPY earned +5.2% a year and long AUDUSD cost -1.3% a year, consistent with
  the rate differentials.
- **What real carry does:** for the most-chosen setting (H = 20, lambda = 1, q = 0.8), the 2017-2026 Sharpe rises
  from -0.07 to +0.15. The swap assumption mattered, but the model's gross edge (about 0.39) is still too small
  once spreads and the retail markup are paid.
- **Reproduce:** `python -m tools.rates`, then `python -m edge.lab.r10.research` (about 26 minutes).

## Cumulative (10 rounds, 30 trials)
No validated strategy. Every signal with a real gross edge (gotobi, the 20-day ML signal, the month-end flow) is
roughly the size of retail trading costs or smaller.
