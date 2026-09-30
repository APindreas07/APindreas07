# Strategy lab round 5: pre-registration (equity-regime and combined signals)

Written and pushed **before** any round-5 test is run, and never changed afterwards. The owner has not yet
answered the gold question (report #4), so this round is **currencies only**.

## Why this round
Rounds 3 and 4 showed that FX-only price signals have about zero gross edge. This round tests whether the
**equity market's own trend or stress** carries information about **risk-sensitive currencies**. The signal uses
SPY prices only, so it remains technical analysis. It also tests one combination of the best earlier
near-misses.

## Data
- **FX:** TradeStation daily bars for the 7 USD majors, 2006-10 .. 2026-09-25, as in rounds 1-2 (longer
  history than HistData).
- **Risk basket:** 6 crosses computed exactly from the majors: AUDJPY, NZDJPY, CADJPY, AUDCHF, NZDCHF,
  CADCHF, each defined as the risk currency against the safe haven.
- **SPY:** TradeStation daily closes (`data/tradestation/SPY_daily.csv`). Each FX date takes the latest SPY close
  **on or before** that date, so no future information is used.
- **Periods:** development 2008-2016; walk-forward out-of-sample 2017-2023 (yearly re-selection on the trailing
  5 years); holdout 2024-01-01 .. 2026-09-25.

## Costs
- **Crosses:** the sum of both legs' retail costs (table spread + 0.9 pip per round turn), as in round 2.
- **Swap:** a sensitivity of -2% a year on held notional. This is conservative: long risk/short haven positions
  usually earned positive carry over this period, which is **not** credited.

## Execution and sizing
- **Timing:** signals on the daily close, filled at the next open.
- **Sizing:** each cross is sized to 10% volatility (60-day), and the 6 crosses are averaged with equal risk.
- **Stops:** where stated, a stop is checked on closes and the exit fills at the next open.

## Hypotheses

| id | idea | rule | parameters | expected gross per trade vs cost |
|----|------|------|------------|----------------------------------|
| K1 | Equity-regime risk-currency trend | At each **Friday** close: risk-on if SPY > SMA_n(SPY) x (1 + b); risk-off if SPY < SMA_n x (1 - b); otherwise keep the previous state. Risk-on: **long** the basket. Risk-off: **short** the basket if s = 1, flat if s = 0. | n 50..250, b 0.00..0.02, s {0, 1} | Regimes last weeks to months; the basket moves several % per regime vs ~5-6 pips per switch (>20x). |
| K2 | Rebound after equity stress | If SPY's N-day return < -x at a close (and no position is open), go **long** the basket at the next open. Exit after H days, or when a basket cross closes 3 x stdev_60 x price below its entry (per cross). | N 3..10, x 0.03..0.10, H 5..40 | Rebounds after sell-offs of ~2-5% in the risk crosses vs ~6 pips of cost (>30x). A rare event (a few per year). |
| K3 | Combined near-misses G1 + G3 (new trial) | The round-2 walk-forward return streams of G1 (cross mean reversion) and G3 (month-end flow), each scaled to 10% volatility on its own trailing 60 days (cap 4x), averaged with equal risk. | the G1 and G3 parameters as pre-registered in `edge/fx2` | Inherits G1 and G3; its purpose is diversification. |

**Sources.** Risk-on/risk-off co-movement of AUD, NZD and CAD against JPY and CHF with equities is well
documented (carry-crash literature; e.g. Brunnermeier, Nagel & Pedersen 2008). K2 follows the evidence that
safe-haven overshoots reverse after equity sell-offs.

**Walk-forward grids.**
- K1: n {50, 100, 150, 200, 250} x b {0, 0.01, 0.02} x s {0, 1} (30 sets).
- K2: N {3, 5, 10} x x {0.03, 0.05, 0.08} x H {10, 20, 40} (27 sets).
- K3: none; its parameter Monte Carlo pairs random G1 set *i* with random G3 set *i*.

## Pass criteria (edge/lab/AGENT.md, all must hold)
1. Walk-forward out-of-sample net Sharpe >= 0.3 and net return > 0.
2. Parameter Monte Carlo (10,000 sets, seed 20261002): >= 60% of sets have an out-of-sample Sharpe > 0, and the
   median is > 0.
3. Return Monte Carlo (10,000 block-bootstraps): P(loss over the out-of-sample period) < 20%.
4. Development-period Sharpe > 0.
5. 2% a month reachable at <= 5x leverage with an out-of-sample maximum drawdown <= 10%.
6. Deflated Sharpe >= 0.95, with n_trials = 19 (16 earlier FX rows + K1-K3).

Random numbers are used only to pick parameter sets and to resample real returns.
