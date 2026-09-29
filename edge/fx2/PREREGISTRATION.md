# FX strategy research, round 2: pre-registration

Written **before** any of the tests below are run. Nothing here is changed after results are seen; anything added
later is labelled post-hoc in the report.

## Goal and target
The user's target is **2% a month**. That is about 26.8% a year compounded. A strategy counts as meeting the
target only if it validates (criteria 1-4 below) **and** criterion 5 holds.

## Honest limitations known in advance
* **The holdout is partly contaminated.** Round 1 (`edge/fx/REPORT.md`) showed that z-score mean reversion on
  the 7 USD majors did well in 2024-2026. Any mean-reversion idea tested here was therefore chosen by someone
  who has seen that window. The only fully clean test left is **forward (paper) trading after 2026-09-25**.
  The 2024-2026 holdout is still reported, but it is labelled "seen-adjacent" and cannot validate anything on
  its own.
* **Data.** Only the TradeStation daily bars already downloaded are used: 7 USD majors, 2006-10 .. 2026-09-25,
  plus SPY daily. There is no carry, no rate data and no intraday data.
* **Crosses are derived.** The 21 currency crosses (e.g. EURJPY = EURUSD x USDJPY, AUDNZD = AUDUSD / NZDUSD)
  are computed exactly from the real USD-leg opens and closes, which share the same 17:00 New York timestamp.
  This is arithmetic on real prices, not generated data. Highs and lows cannot be derived, so no rule uses them.

## Periods (same as round 1)
* **Development**: 2008-01-01 .. 2016-12-31 (2007 is warm-up only).
* **Walk-forward out-of-sample**: 2017-2023. Parameters are re-chosen each January on the trailing 5 years.
* **Holdout (seen-adjacent)**: 2024-01-01 .. 2026-09-25.

## Costs
* **USD majors**: as in round 1, the spread (EURUSD 1.0, USDJPY 1.2, GBPUSD 1.5, AUDUSD 1.3, USDCAD 1.8,
  USDCHF 1.8, NZDUSD 2.0 pips) plus commission 0.5 pip and slippage 0.4 pip, per round turn.
* **Derived crosses**: the **sum** of the two legs' round-turn costs, expressed as a fraction of price. This is
  deliberately conservative; a direct cross quote is usually cheaper.
* **Swap**: reported as a sensitivity of -2% a year on average gross exposure.

## Hypotheses (rules fixed now; only the listed parameters are ever searched)
| id | idea | rule | parameter ranges | source of the idea |
|----|------|------|------------------|--------------------|
| G1 | Cross-pair mean reversion | For each of the 21 crosses: z = (log close - SMA_n(log close)) / stdev_n. Short above +k, long below -k, exit when z crosses 0. | n 5..60, k 1.0..3.0 | Pairs of economically linked currencies revert (e.g. AUDNZD, EURCHF, EURGBP) |
| G2 | Short-term cross-sectional reversal | Rank the 7 currencies vs USD by their N-day return. Long the 2 weakest, short the 2 strongest, hold H days. | N 1..10, H 1..5 | Short-term FX reversal (the opposite of F4, which used N >= 20) |
| G3 | Month-end equity-hedge flow | On the trading day D days before month-end: if SPY's month-to-date return is > +x, short USD against an equal-risk basket of the 7 non-USD currencies (the 7 majors); if it is < -x, long USD. Exit at the close of the month's last trading day. | D 1..5, x 0.0%..3.0% | Melvin & Prins (2015): foreign investors re-hedge US equity holdings at month-end |
| G4 | Trend on crosses | For each of the 21 crosses: long if SMA(fast) > SMA(slow), else short. | fast 5..100, slow 50..300, fast < slow / 1.5 | Round 1's F1 applied to the crosses instead of the USD pairs |

All signals are computed on the close and filled at the next open. Every position is sized to 10% annualised
volatility (60-day stdev of daily returns), and the instruments within a hypothesis are averaged with equal risk.

## Validation criteria (all of 1-4 must hold)
1. Walk-forward out-of-sample 2017-2023: net Sharpe >= 0.3 and net return > 0.
2. **Parameter Monte Carlo** (10,000 sets drawn uniformly from the ranges, seed 20260929): >= 60% of sets have
   an out-of-sample Sharpe > 0, and the median set is > 0.
3. **Return Monte Carlo** (10,000 block-bootstraps, 20-day blocks, of the real out-of-sample daily net returns,
   seed 20260929): the probability of a loss over the out-of-sample period is < 20%.
4. Development-period net Sharpe > 0 for the walk-forward-chosen parameters (equal blend of the yearly choices).

## Criterion 5: can it reach 2% a month?
For a validated strategy, compute the leverage L that scales its out-of-sample 2017-2023 annual return to 26.8%.
The target counts as reachable only if **both** hold:
* the out-of-sample Sharpe is >= 0.8, and
* the out-of-sample maximum drawdown at leverage L is <= 30%.

If this fails, the report states the monthly return the strategy would have made at the leverage that keeps the
out-of-sample maximum drawdown at 20%.

## Portfolio
Validated hypotheses are combined with equal risk, as in round 1, and criterion 5 is applied to the portfolio as
well. If nothing validates, that is the result.

Random numbers are used **only** for the two Monte Carlo tests. No prices or returns are ever generated.
