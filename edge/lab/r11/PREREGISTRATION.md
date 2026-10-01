# Strategy lab round 11: pre-registration (momentum on 18 instruments with real financing)

Written and pushed **before** any round-11 test is run, and never changed afterwards.

## Why
Time-series and cross-sectional momentum failed in round 1. But that test used only the 7 USD majors and a flat
-2% a year swap. Since then:
- the universe has grown to 18 instruments, adding Scandinavian/Central European pairs and the metals;
- **real carry** is available (round 10).

Momentum is the most-documented technical edge across asset classes (Moskowitz, Ooi & Pedersen 2012; Asness,
Moskowitz & Pedersen 2013), and E5 is the one real edge found so far. These are **new trials**, because the
universe and the cost model differ from round 1.

## Common setup (from rounds 9-10, unchanged)
- **Data:** 18 instruments (7 majors, USDNOK, USDSEK, USDPLN, USDHUF, USDCZK, EURNOK, EURSEK, EURPLN, EURHUF,
  XAUUSD, XAGUSD). Daily bars close at 17:00 New York; fills at the first bar at or after 18:30 New York.
- **Costs:** the round-9 transaction costs.
- **Financing:** real daily carry from OECD 3-month rates (previous month), minus a 1% a year markup (round 10).
- **Sizing:** each instrument at 10% volatility (60-day), averaged with equal risk.
- **Rebalancing:** on Friday closes only.
- **Periods:** walk-forward out-of-sample 2017-2023 (yearly re-selection on the trailing 5 years);
  development 2014-2016; holdout 2024 .. 2026-09-25.

## Hypotheses

| id | idea | rule | parameters |
|----|------|------|------------|
| R1 | Time-series momentum, 18 instruments | Every Friday: position = sign(log return over the last N days) for each instrument, held to the next Friday. | N 20..260 |
| R2 | Cross-sectional momentum, 18 instruments | Every Friday: rank the instruments by N-day return divided by their 60-day stdev. **Long the top K, short the bottom K** (each at 10% volatility); the rest are flat. | N 20..260, K 2..6 |

**Walk-forward grids:**
- R1: N {20, 60, 120, 180, 260}.
- R2: N {20, 60, 120, 260} x K {2, 4, 6}.

## Pass criteria
- edge/lab/AGENT.md criteria 1-6.
- Parameter Monte Carlo: 10,000 sets, seed 20261008.
- Deflated Sharpe: n_trials = 30 (28 earlier rows + R1 + R2).
