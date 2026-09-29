# Edge research: pre-registration

Written and committed **before** any of the data below was downloaded or tested.
The commit timestamp is the proof. Nothing here is changed after results are seen;
anything added later goes in a clearly labelled "post-hoc" section of the report.

## Goal
Find a trading edge for a normal broker account (no prop-firm rules) that
1. is documented in published research (so the idea was not mined from this data),
2. survives realistic costs on real TradeStation price history,
3. still works **after** its publication date (true out-of-sample), and
4. still works in the untouched final holdout: **2024-01-01 to 2026-09-25**.

No random numbers are used anywhere (no Monte Carlo, no bootstrap, no random
benchmarks). All statistics are deterministic.

## Hypotheses (rules fixed from the original publications, not tuned)

| id | edge | market / bars | rules | source |
|----|------|---------------|-------|--------|
| E1 | Short-term mean reversion in a rising index | SPY daily | long when close > SMA(200) and RSI(2) < 10; exit when close > SMA(5); fill at next open | Connors & Alvarez, *Short Term Trading Strategies That Work* (2008) |
| E2 | Turn-of-the-month | SPY daily | long from the close of the 2nd-to-last trading day of the month to the close of the 3rd trading day of the next month | Ariel (1987); Lakonishok & Smidt (1988); McConnell & Xu (2008) |
| E3 | Overnight drift | SPY daily | long close to next open, every day | Cliff, Cooper & Gulen (2008); Lou, Polk & Skouras (2019) |
| E4 | Trend filter on equities | SPY monthly | long when month-end close > 10-month SMA, else cash | Faber (2007) |
| E5 | Time-series momentum, multi-asset | monthly: SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, SLV, USO, DBC + 7 FX majors | each month, long if 12-month return > 0, short if < 0; each position scaled to 10% annual volatility (trailing 12m of monthly returns), equal risk across markets | Moskowitz, Ooi & Pedersen (2012); Hurst, Ooi & Pedersen (2017) |
| E6 | Time-series momentum, FX only | monthly: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, USDCHF, NZDUSD | same as E5 | same as E5 |

Confirmation market for E1-E3 (only tested if the edge passes on SPY): QQQ daily.

## Periods
* **Pre-publication**: data start up to the publication year (E1: <=2008, E2: <=1988 not available -> use data start to 2008 as the "early" block, E4: <=2007, E5/E6: <=2012).
* **Post-publication**: publication year+1 to 2023-12-31.
* **Holdout**: 2024-01-01 to 2026-09-25. Looked at once, at the end.

## Costs
* SPY/QQQ: 0.02% per side (spread + commission, conservative for a liquid ETF or a US500 CFD).
* Monthly ETFs: 0.05% per side; FX majors: 1.5 pips round turn as % of price.
* CFD overnight financing is reported separately as a sensitivity (3%/yr on held notional), since it depends on the broker.
* ETF prices from TradeStation are split-adjusted but **not** dividend-adjusted; this understates buy-and-hold and long exposure equally and is stated in the report.

## Pass criteria (all must hold)
1. Net of costs, positive in **every** period block (pre, post, holdout).
2. Full-sample t-statistic of the edge >= 2.0. For E1-E3: mean daily return while in the position minus SPY's unconditional mean daily return (the edge over just being long). For E4-E6: mean monthly strategy return.
3. Plateau: the rule's neighbours (E1: RSI 5/10/15/20/25 x exit SMA 3/5/10; E2: window -3..-1 to +2..+4; E5: lookback 3/6/12 months) are **all** net positive over the full sample. No neighbour is picked because it was best; the published rule is the one reported.
4. For E1-E3: the edge also holds on QQQ (positive net, t >= 1.5).

Anything failing any criterion is reported as failed, with its numbers.
