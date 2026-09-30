# Strategy lab round 7: pre-registration (the gotobi Tokyo-fix effect)

Written and pushed **before** any round-7 test is run, and never changed afterwards. Currencies only; the owner
has not answered report #6, so the agent continues with option 1 (FX only, slow pace).

## Idea
On **gotobi days**, Japanese corporates settle payments and customer orders are tilted toward buying dollars.
Banks buy USD ahead of the **09:55 Tokyo fix**, pushing USDJPY up before the fix, followed by a partial reversal
afterwards.
- **Mechanism:** Ito & Yamada (2017), "Was the forex fixing fixed?".
- **Reported size:** about +7 pips on USDJPY before the fix (practitioner statistics, HAC and Holm-corrected).

## Data and definitions
- **Data:** HistData USDJPY 5-minute bid bars, 2012-01 .. 2026-09-25. Ask = bid + 1.2 pips (the retail table).
- **Time:** Tokyo time = UTC + 9 hours (Japan has no daylight saving).
- **Gotobi day:** a Tokyo calendar day whose day of month is 5, 10, 15, 20, 25 or 30, or the last day of the
  month if that is the 31st. If it falls on a Saturday or Sunday, the preceding Friday is the gotobi day.
  Japanese public holidays are not modelled (a known limitation: on those days the trade is taken anyway).
- **Costs:** 1.2 pips spread (via the ask) + 0.9 pip commission and slippage per round turn.
- **Sizing:** 10% volatility (60-day daily returns), as in round 3.
- **Periods:** development 2012-2016; walk-forward out-of-sample 2017-2023 (yearly re-selection on the trailing
  5 years); holdout 2024 .. 2026-09-25.

## Hypotheses

| id | idea | rule | parameters | expected gross per trade vs cost |
|----|------|------|------------|----------------------------------|
| M1 | **Buy before the fix** on gotobi days | Buy USDJPY at the open of the bar starting at Tokyo time E, sell at the open of the 09:55 bar. | E 07:00..09:30 (step 30 min) | About 5-7 pips vs 2.1 pips cost (about 3x) |
| M2 | **Fade after the fix** on gotobi days | Sell USDJPY at the open of the 10:00 Tokyo bar, buy back at the open of the bar starting at X. | X 10:30..15:00 (step 30 min) | Partial reversal of about 3-5 pips vs 2.1 pips (about 2x) |

Days with a missing bar at any required time are skipped. There is no stop; the holding time is under 5 hours.

**Walk-forward grids:** M1: all 6 values of E. M2: all 10 values of X.

**Parameter Monte Carlo:** 10,000 draws from the same discrete ranges, seed 20261004. With only 6 and 10
possible settings, this mostly measures how robust the result is across all of them.

## Pass criteria
edge/lab/AGENT.md criteria 1-6, with deflated-Sharpe n_trials = 23 (21 earlier FX rows + M1 + M2).

**Descriptive only (not a criterion):** the same trades on non-gotobi days, as a control.
