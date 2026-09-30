# Strategy lab round 4: pre-registration (multi-day holds)

Written and pushed **before** any round-4 data is built or any test is run, and never changed afterwards.
Anything added later is labelled post-hoc.

## Why this round
Round 3 showed that intraday FX signals earn well under 1 pip per trade, gross, against 2-6 pips of retail cost.
Round 4 therefore tests only **multi-day holds**, where the expected move per trade is many times the cost.
Each hypothesis states that ratio up front (below).

## Data
- **Source:** HistData 1-minute bid bars (`tools/histdata.py`), aggregated into **daily bars that close at
  17:00 New York**. HistData provides bid highs and lows for its own pairs.
- **7 USD majors:** as in round 3. Their **21 crosses** are computed exactly from the majors' daily opens and
  closes, as in round 2.
- **9 Scandinavian / Central European (CEE) pairs:** USDNOK, USDSEK, USDPLN, USDHUF, USDCZK, EURNOK, EURSEK,
  EURPLN, EURHUF. All are available on HistData from 2012.
- **Excluded:** USDMXN, USDZAR, USDTRY and similar high-carry pairs. Their interest-rate differential (swap)
  cannot be modelled from price data, and ignoring it would badly overstate trend returns.
- **Periods:** development 2012-2016 (the first 100 trading days are warm-up); walk-forward out-of-sample
  2017-2023 (yearly re-selection on the trailing 5 years); holdout 2024-01-01 .. 2026-09-25.

## Costs
- **Majors:** retail table spread (EURUSD 1.0, USDJPY 1.2, GBPUSD 1.5, AUDUSD 1.3, USDCAD 1.8, USDCHF 1.8,
  NZDUSD 2.0 pips) + 0.9 pip per round turn.
- **Crosses:** the sum of the two legs' costs (conservative).
- **Scandinavian / CEE pairs:** **6 basis points per round turn** (5 bp spread + 1 bp commission and
  slippage), which is conservative for retail quotes on these pairs.
- **Swap sensitivity**, charged on every day a position is held:
  - -2% a year on majors and crosses;
  - **-4% a year on Scandinavian / CEE pairs.** Note that the HUF rate differential exceeded 10% in 2022-23,
    so HUF results in those years may be flattered.

## Execution and sizing (all hypotheses)
- **Timing:** signals on the daily close (17:00 New York), filled at the next daily open.
- **Sizing:** each position is sized to 10% annualised volatility using the trailing 60-day stdev of daily
  close-to-close returns. Instruments within a hypothesis are averaged with equal risk.
- **Stops:** a protective stop is evaluated on daily **closes**. When a close breaches it, the position is
  exited at the next open. This is conservative, since an exchange-held stop would usually fill earlier.

## Hypotheses (only the listed parameters are searched)

| id | idea | instruments | rule | parameters | expected gross per trade vs cost |
|----|------|-------------|------|------------|----------------------------------|
| J1 | Volatility-squeeze breakout | 7 majors + 21 crosses | Squeeze when stdev_s / stdev_L < c. **Entry:** during a squeeze, a close above the prior N-day high close goes long; below the prior N-day low close goes short. **Exit:** first of (a) a close beyond a trailing stop m x stdev_L x price from the best close since entry, (b) H days held. | s 5..10, L 50..100, c 0.5..0.9, N 10..40, m 1.5..3.0, H 10..40 | Holds ~10-40 days. Daily sd ~0.6%, so a typical move of 2-4% = 200-400 pips vs 2-5 pips cost (>40x). |
| J2 | Bollinger mean reversion, Scandinavian / CEE | 9 pairs | z = (close - SMA_n) / stdev_n. **Entry:** long when z < -k, short when z > +k. **Exit:** first of z crossing 0, H days held, or a close 3 x stdev_n x price beyond entry (fixed stop). | n 10..40, k 1.5..2.5, H 5..20 | Reversion of ~1-2 sd ~ 1-2% vs 0.06% cost (>15x). |
| J3 | Moving-average trend, Scandinavian / CEE | 9 pairs | **Entry:** long when SMA_f > SMA_s, short when below; enter at the next open after a crossover. **Exit:** at the opposite crossover (reverse into the new direction), or a close beyond a stop 3 x stdev_60 x price from entry. After a stop-out, stay flat until the next crossover. | f 5..50, s 50..200, f < s / 2 | Trend legs of weeks to months ~ 3-6% vs 0.06% cost (>50x). |

**Sources.** J2 and J3 follow Hsu, Taylor & Wang (2016) and the 22-currency study summarised in the literature
(Bollinger, RSI and MACD robust on managed CEE currencies such as HUF; trend rules better on less-efficient
currencies). J1 is a practitioner idea (volatility compression followed by expansion); no academic
out-of-sample evidence was found, so its prior is weaker.

**Walk-forward grids.**
- J1: s {5, 10} x L {50, 100} x c {0.6, 0.8} x N {20, 40} x m {2, 3} x H {20, 40} (64 sets).
- J2: n {10, 20, 40} x k {1.5, 2.0, 2.5} x H {5, 10, 20} (27 sets).
- J3: (f, s) in {(10, 50), (20, 100), (50, 200), (5, 50), (20, 200)}.

## Pass criteria (edge/lab/AGENT.md)
1. Walk-forward out-of-sample net Sharpe >= 0.3 and net return > 0.
2. Parameter Monte Carlo (10,000 sets, seed 20261001): >= 60% of sets have an out-of-sample Sharpe > 0, and the
   median is > 0.
3. Return Monte Carlo (10,000 block-bootstraps, 20-day blocks): P(loss over the out-of-sample period) < 20%.
4. Development-period Sharpe > 0.
5. Target: at the leverage that gives 26.8% a year, the leverage is <= 5x and the out-of-sample maximum drawdown
   is <= 10%. Otherwise the report states the monthly return reachable within those limits.
6. Deflated Sharpe >= 0.95, with n_trials = 16 (13 earlier FX rows + J1-J3).

All returns are net of the costs and swap above. Random numbers are used only to pick parameter sets and to
resample real returns.
