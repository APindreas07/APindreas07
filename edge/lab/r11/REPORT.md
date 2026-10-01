# Lab round 11 (momentum on 18 instruments, real financing): results

**Verdict: both hypotheses fail.**

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC > 0 | P(loss) | dev 2014-16 | holdout 2024-26 | DSR | result |
|----|------------|-------------------------------------------|--------------|---------|-------------|-----------------|-----|--------|
| R1 | Time-series momentum, 18 instruments | -0.67 / -3.5% / -24% | 0% | 97% | +0.13 | -0.58 / -2.8% | 0.000 | **FAIL** |
| R2 | Cross-sectional momentum, 18 instruments | -0.73 / -1.7% / -13% | 1% | 98% | -0.03 | -0.33 / -0.8% | 0.000 | **FAIL** |

- **Setup:** the same data, costs and real carry as rounds 9-10; weekly rebalancing on Fridays; fills at 18:30 New York.
- **Result:** momentum across all 18 instruments loses money in 2017-2023 and in 2024-2026, even with real financing
  and a universe 2.5 times larger than in round 1.
- **Parameter Monte Carlo:** almost no random setting works (0-1% positive).
- **Reproduce:** `python -m edge.lab.r11.research`.

## Cumulative after 11 rounds (32 trials)
- **No validated strategy.**
- **Every family has now been tested:** trend, breakout, momentum (time-series and cross-sectional), mean reversion
  (single pairs, crosses, Scandinavian/CEE, gold/silver ratio), session effects, the London fix, the Tokyo fix
  (gotobi), month-end flows, equity-regime filters, and machine learning.
- **Horizons covered:** 5-minute, daily and weekly.
- **Cost models:** both flat and real financing.
- **The only real effects found** (gotobi, the 20-day ML signal, month-end flows) are about the size of retail
  costs.
