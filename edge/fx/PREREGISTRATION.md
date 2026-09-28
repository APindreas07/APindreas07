# FX strategy research: pre-registration

Committed **before** the daily FX data below is downloaded. Nothing here is changed after results are seen;
anything added later is labelled post-hoc in the report.

## Data
TradeStation daily bars (get-bars, interval 1, unit Daily) for the 7 USD majors:
EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD, 2007-01 .. 2026-09-25. Spot prices only.

## Periods
* **Development (in-sample)**: 2007-01-01 .. 2016-12-31 (first 12 months are indicator warm-up only).
* **Validation (walk-forward out-of-sample)**: 2017-01-01 .. 2023-12-31. Parameters re-chosen every January
  on the trailing 5 years only, then traded for 12 months.
* **Holdout**: 2024-01-01 .. 2026-09-25. Looked at once, after the strategy set and portfolio are frozen.

## Costs (per round turn, in pips; applied on every position change)
Spread EURUSD 1.0, USDJPY 1.2, GBPUSD 1.5, AUDUSD 1.3, USDCAD 1.8, USDCHF 1.8, NZDUSD 2.0,
plus commission 0.5 pip and slippage 0.4 pip. Overnight swap cannot be observed from price bars:
reported as a sensitivity of -2%/yr on average gross exposure.

## Strategy families (rules fixed now; only the listed parameters are ever searched)
| id | family | rule | parameter ranges |
|----|--------|------|------------------|
| F1 | MA trend | long if SMA(fast) > SMA(slow) else short, per pair | fast 5..100, slow 50..300 (fast < slow/1.5) |
| F2 | Time-series momentum | sign of N-day return, per pair, rebalanced weekly | N 20..260 |
| F3 | Donchian breakout | long on N-day high close, short on N-day low close, exit on opposite M-day extreme | N 20..120, M 10..N |
| F4 | Cross-sectional momentum | rank the 7 currencies vs USD by N-day return; long top 2, short bottom 2; rebalance every H days | N 20..260, H 5..21 |
| F5 | Short-term reversal / mean reversion | z = (close - SMA(n))/stdev(n); short above +k, long below -k, exit at 0 | n 5..40, k 1.0..2.5 |

All signals are computed on the close and filled at the next day's open. Every position is sized to
10% annualised volatility (60-day stdev of daily returns); a portfolio of pairs is averaged equal-risk.

## Validation criteria (a strategy is "validated" only if all hold)
1. Walk-forward OOS 2017-2023: net annualised Sharpe >= 0.3 and net return > 0.
2. **Parameter Monte Carlo** (10,000 parameter sets drawn uniformly from the ranges above, seed 20260928):
   OOS 2017-2023 net Sharpe > 0 for >= 60% of the sets, and the median set is > 0. This tests whether the
   result depends on a lucky parameter choice.
3. **Return Monte Carlo** (10,000 block-bootstrap resamples, 20-day blocks, of the *real* OOS daily net
   returns, seed 20260928): the 5th percentile of annualised return is reported; the probability of a loss
   over the OOS length must be < 20%.
4. Development period net Sharpe > 0 for the walk-forward-chosen parameters (sanity: no sign flip).

Random numbers are used **only** for these two Monte Carlo tests: to pick parameter sets and to resample
real realised returns. No prices or returns are ever generated.

## Portfolio
Validated strategies are combined with equal risk (each scaled to 10% vol on trailing 60 days of its
own returns, then averaged). If none validate, the report says so and no portfolio is presented as tradable.
The portfolio curve, the holdout result and the Monte Carlo distributions are reported either way.
