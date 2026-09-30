# Strategy lab round 8: pre-registration (gold and silver)

Written and pushed **before** any round-8 test is run, and never changed afterwards. The owner added gold and
silver to the scope on 2026-09-30.

## Data
- **Source:** HistData 1-minute bid bars for XAUUSD and XAGUSD, 2012-01 .. 2026-09-25, built into 5-minute bars
  and daily bars that close at 17:00 New York (as in round 4).
- **Honesty note:** the general direction of gold's price over 2012-2026 (down 2012-15, strongly up 2019-26) is
  common knowledge. The holdout is therefore not "unseen" in a strict sense. The test relies on walk-forward
  selection, the parameter Monte Carlo and the deflated Sharpe, not on the holdout alone.

## Costs (retail, conservative)
- **Gold:** 2 bp per round turn (1.5 bp spread + 0.5 bp commission and slippage).
- **Silver:** 4 bp per round turn (3 bp spread + 1 bp).
- **Swap:** -3% a year on notional held through the 17:00 New York rollover, in either direction. Retail metal
  swaps are typically negative for both longs and shorts.

## Sizing and periods
- **Sizing:** 10% volatility (60-day stdev of daily returns); gold and silver averaged with equal risk.
- **Timing:** signals on the close, fills at the next open.
- **Periods:** development 2012-2016; walk-forward out-of-sample 2017-2023 (yearly re-selection on the trailing
  5 years); holdout 2024 .. 2026-09-25.

## Hypotheses

| id | idea | rule | parameters | expected gross per trade vs cost |
|----|------|------|------------|----------------------------------|
| N1 | Time-series momentum on gold and silver | Every Friday close: position = sign(close / close N days ago - 1), long or short, held until the next Friday. | N 20..260 | Trend legs of weeks to months ~ 3-10% vs 2-4 bp (>100x). Documented in Moskowitz, Ooi & Pedersen (2012); drove the E5 gains in study 1. |
| N2 | Gold's Asian-session drift | Every weekday: buy XAUUSD at the open of the 5-min bar at New York time E; sell at the open of the bar at time X, the same trading day. Both times are after the 17:00 rollover, so there is **no swap**. | E {18:00, 19:00, 20:00} NY, X {02:00, 03:00, 04:00} NY | Documented tendency of gold to gain during Asian hours. A drift of ~2-5 bp a night vs 2 bp cost (about 1-2x): thin. |
| N3 | Gold/silver ratio mean reversion | z = (log(XAU / XAG) - SMA_n) / stdev_n of the log ratio. If z > k, short gold / long silver; if z < -k, the reverse (equal risk per leg). Exit when z crosses 0, after H days, or at abs(z) > k + 2 (stop). | n 60..250, k 1.5..2.5, H 20..120 | Ratio reversions of ~5-10% vs about 6 bp for both legs (>50x). |

**Walk-forward grids:**
- N1: N {20, 60, 120, 180, 260}.
- N2: all 9 combinations of E and X.
- N3: n {60, 120, 250} x k {1.5, 2.0, 2.5} x H {20, 60, 120}.

**Parameter Monte Carlo:** 10,000 sets, seed 20261005. N2 is drawn from its 9 discrete combinations.

## Pass criteria
edge/lab/AGENT.md criteria 1-6, with deflated-Sharpe n_trials = 26 (all 23 earlier FX rows + N1-N3; counted
conservatively even though metals are a different market).

**Implementation note.** A stop in N1 is not included: its weekly always-in rule has no natural stop. If N1
validates, a stop variant must be pre-registered and tested before deployment (charter rule 5).
