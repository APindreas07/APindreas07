# Strategy lab round 3: pre-registration (intraday)

Written and pushed **before** any round-3 test is run, and never changed afterwards. Anything added later is
labelled post-hoc in the report.

## Data (owner's decision, 2026-09-29)
- **Source.** TradeStation's MCP connector returns at most 100 five-minute bars per request, which makes years of
  intraday history impossible to fetch. The owner chose **Dukascopy** historical data instead: real bank/ECN
  1-minute **bid and ask** candles, downloaded by `tools/dukascopy.py` and aggregated to 5-minute bid/ask bars
  (UTC, labelled by bar start).
- **Cross-check.** USDJPY 2019-06-03, 20:45-20:50 UTC: the Dukascopy bid close (108.066) equals TradeStation's
  close exactly.
- **Coverage.** The 7 USD majors (EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD), 2012-01-01 ..
  2026-09-25.
- **Storage.** The raw files are git-ignored. `data/dukascopy_MANIFEST.csv` records each file's row count and
  SHA-256.

## Periods
- **Development:** 2012-2016. The first 60 trading days are volatility warm-up only.
- **Walk-forward out-of-sample:** 2017-2023. Parameters are re-chosen each January on the trailing 5 years.
- **Holdout:** 2024-01-01 .. 2026-09-25.

## Execution and costs
- **Fills.** Signals are computed on a bar's close and filled at the **next bar's open**. Buys fill at the
  **ask**, sells at the **bid**, so the real spread is paid on every trade.
- **Retail minimum.** Dukascopy spreads are tighter than a retail account's. Each fill is therefore charged the
  extra amount needed to reach the retail spread table (EURUSD 1.0, USDJPY 1.2, GBPUSD 1.5, AUDUSD 1.3, USDCAD
  1.8, USDCHF 1.8, NZDUSD 2.0 pips), which is max(0, table - real spread) / 2 per side.
- **Commission and slippage:** 0.5 + 0.4 pip per round turn, charged as 0.45 pip per side.
- **Swap.** All positions are closed the same day, so no swap applies.

## Sizing and aggregation
- Each pair's daily P&L is scaled by 10% / (its trailing 60-day annualised volatility of daily close-to-close
  returns, known before the day).
- Pairs are averaged with equal risk: the sum divided by 7, as in rounds 1-2. For a single-pair hypothesis, that
  pair alone.

## Time conventions
- London times are **Europe/London local time**, converted from UTC with daylight saving (DST) handled.

## Hypotheses (only the listed parameters are ever searched)

| id | idea | rule | parameters | source |
|----|------|------|------------|--------|
| H1 | London-open momentum, 7 majors | Each trading day, per pair: s = sign(mid at 08:00+W minus mid at 08:00, London time). If s != 0, enter in direction s at the open of the bar starting at 08:00+W and exit at the open of the bar starting at local time X. | W 15..60 min (step 5), X 10:00..16:30 (step 30 min) | Seeck (SSRN 7008318) |
| H2 | London-open momentum, **USDJPY only** | Same rule as H1, USDJPY only. Chosen a priori because Seeck reports only USDJPY clears retail costs. | same as H1 | Seeck |
| H3 | London 4pm fix reversal, USD vs 6 others | Each trading day: long USD in every pair from 16:00 - P (London) until 16:00. Then short USD from 16:05 until 16:05 + Q. | P 15..120 min (step 5), Q 15..240 min (step 15) | Krohn, Mueller & Whelan (J. Finance 2024); Melvin & Prins (2015) |
| H4 | Regime-filtered intraday mean reversion, 7 majors, **15-minute bars** | z = (mid - SMA_n) / stdev_n on 15-min mid closes. Kaufman efficiency ratio ER = abs(mid_t - mid_{t-32}) / sum of the last 32 abs changes (8 hours). New entries are allowed only from 07:00 to 19:00 London and only when ER < e: long if z < -k, short if z > k. Exit when z crosses 0, after 16 bars (4 hours), or at 20:00 London, whichever comes first. | n 12..96 bars, k 1.5..3.0, e 0.10..0.40 | Bhatti (SSRN 6087107); short-horizon FX reversal literature |

For H1 and H2, "mid" = (bid close + ask close) / 2 of the named bar. Days with a missing bar at any required time
are skipped.

**Walk-forward grids.**
- H1 and H2: W in {15, 30, 45, 60} x X in {10:00, 12:00, 14:00, 16:00}.
- H3: P in {15, 30, 60, 120} x Q in {15, 60, 120, 240}.
- H4: n in {12, 24, 48, 96} x k in {1.5, 2.0, 2.5, 3.0} x e in {0.15, 0.25, 0.35}.

Parameter Monte Carlo sets are drawn uniformly from the full ranges, with steps where the table gives them.

## Pass criteria (edge/lab/AGENT.md; all must hold)
1. Walk-forward out-of-sample 2017-2023: net Sharpe >= 0.3 and net return > 0.
2. Parameter Monte Carlo (10,000 sets, seed 20260930): >= 60% of sets have an out-of-sample Sharpe > 0, and the
   median is > 0.
3. Return Monte Carlo (10,000 block-bootstraps, 20-day blocks, of the real out-of-sample daily net returns):
   P(loss) < 20%.
4. Development-period Sharpe > 0 (equal blend of the walk-forward choices).
5. Target: 2% a month (26.8% a year) is reachable, meaning an out-of-sample Sharpe >= 0.8 and a maximum drawdown
   <= 30% at the leverage that gives 26.8% a year.
6. Deflated Sharpe >= 0.95, with n_trials = 13 (9 earlier FX rows + H1-H4) and the ledger's FX Sharpes.

Random numbers are used only to pick parameter sets and to resample real returns. No prices or returns are
generated.

## Amendment 1 (2026-09-29, before any round-3 data was downloaded or any test run)
The owner set conservative risk limits for deployment: 1% risk per trade, 5x maximum leverage and a -10%
drawdown kill switch. Criterion 5 therefore becomes **stricter**: at the leverage that gives 26.8% a year, the
out-of-sample maximum drawdown must be <= **10%** (was 30%), and that leverage must be <= **5x**. Criteria 1-4
and 6 are unchanged. The report states the monthly return reachable within the limits.
