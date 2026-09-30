# Strategy lab round 9: pre-registration (machine learning across all instruments)

Written and pushed **before** any round-9 test is run, and never changed afterwards.
**Owner request (2026-09-30 20:45 UTC):** "craft, develop, test and validate new strategies and go over again all
the currencies + gold & silver ... use every technology possibly".

## Why this round
Rounds 1-8 each tested one hand-written rule at a time. This round tests whether a **statistical learning model**
that combines many technical features can find an edge that no single rule has. The honesty guards are unchanged:
- **no look-ahead:** the model is trained only on data before each test year;
- the same costs;
- the same pass criteria;
- **one model family = one hypothesis** (one ledger row), with a fixed feature list.

## Universe and data
- **18 instruments:** the 7 USD majors, 9 Scandinavian and Central European pairs (USDNOK, USDSEK, USDPLN,
  USDHUF, USDCZK, EURNOK, EURSEK, EURPLN, EURHUF), and XAUUSD, XAGUSD.
- **Data:** HistData daily bars closing at 17:00 New York (as in rounds 4 and 8), 2012 .. 2026-09-25.

## Features (fixed; all computed from closes up to and including day t)
For each instrument and day:
- log returns over 1, 5, 20, 60, 120 and 250 days, each divided by the 60-day daily stdev;
- z-score of the close against SMA 20, 60 and 200 (in 60-day-stdev units);
- volatility ratio stdev_10 / stdev_60;
- the 5-day return of the instrument's **USD leg** and of **SPY** (cross-market context, SPY close on or before
  day t);
- day-of-week dummies.

That is 17 features. Each feature is standardised with the mean and stdev of the **training window only**.

## Target and model
- **Target:** the next-H-day log return from the **next open** (t+1) to the close of t+H, divided by the 60-day
  stdev (volatility-normalised).
- **Model: ridge regression (closed form)**, pooled across all 18 instruments.
  - Retrained every January on the trailing 5 years only (the first model trains on 2012-2016 and is applied to
    2017).
  - Before 2017 the model is not used, except for the development-period check below.

## Trading rule
- Every H trading days, rebalance each instrument to sign(prediction) x 10%-volatility size, but **only if
  abs(prediction) > q**, the q-quantile of the absolute training-set predictions. Otherwise flat.
- Instruments are averaged with equal risk (sum / 18).

## Parameters (searched)
| parameter | range | walk-forward grid |
|-----------|-------|-------------------|
| H, horizon and rebalance interval (days) | 1..20 | {1, 5, 10, 20} |
| ridge lambda | 0.1..1000 (log-uniform) | {1, 10, 100} |
| q, trade threshold quantile | 0.0..0.8 | {0.0, 0.5, 0.8} |

## Costs
- Majors: the table spread + 0.9 pip.
- Scandinavian / CEE: 6 bp.
- Gold 2 bp, silver 4 bp per round turn.
- Swap: -2% a year (majors), -4% (Scandinavian / CEE), -3% (metals) on held notional.
- Rollover rule: daily bars close at 17:00 New York and fills are at the next open, which is after 18:30 in the
  data. The open of a trading day falls in the post-rollover window, so fills use the **first 5-minute bar at or
  after 18:30 New York** as the open (post-hoc-safe: this is decided before testing).

## Development check (criterion 4)
The walk-forward-chosen hyperparameters are applied in 2014-2016, with models trained on the preceding 2 years
(the data starts in 2012), and must show a Sharpe > 0.

## Pass criteria
- edge/lab/AGENT.md criteria 1-6.
- Parameter Monte Carlo: 10,000 random hyperparameter sets, seed 20261006.
- Deflated Sharpe: n_trials = 27 (26 earlier rows + P1).

**Only one hypothesis this round (P1).** It is expensive to run, and adding more would dilute the deflated
Sharpe.
