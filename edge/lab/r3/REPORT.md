# Lab round 3 (intraday): results

**Verdict: all four intraday hypotheses fail every pass criterion.** The reason is simple and robust: before
costs, the signals earn about zero, roughly ±0.5 pip per trade. After retail costs of 2-6 pips per trade, every
version loses money. **No parameter choice rescues them**: in the parameter Monte Carlo, 0-1.2% of 10,000 random
settings were profitable out of sample.

- **Data:** HistData 1-minute bid bars aggregated to 5 minutes, 7 USD majors, 2012-01-02 .. 2026-09-25 (3,840
  London trading days). Timestamps were verified against Dukascopy. See amendment 2 in `PREREGISTRATION.md`.
- **Costs:** every trade pays the retail spread table, plus 0.9 pip per round turn in commission and slippage.
- **Rules:** fixed in `PREREGISTRATION.md`, committed before any test was run.
- **Engine check:** a day-by-day loop on USDJPY H1(30, 12) matches the vectorised engine to 4.7e-10.
- **Reproduce:** `python -m edge.lab.r3.research` (about 65 minutes).

## Results

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC: sets > 0 (median) | P(loss) | dev 2012-16 | holdout 2024-26 | deflated Sharpe | result |
|----|------------|-------------------------------------------|-----------------------------|---------|-------------|-----------------|-----------------|--------|
| H1 | London-open momentum, 7 majors | -2.14 / -8.4% / -47% | 0.0% (-2.94) | 100% | -1.50 | -1.58 | 0.000 | **FAIL** (all) |
| H2 | London-open momentum, USDJPY | -0.94 / -6.5% / -40% | 0.0% (-1.79) | 99% | +0.05 | +0.22 | 0.000 | **FAIL** (c1-3, 5, 6) |
| H3 | London 4pm fix reversal | -3.36 / -15.2% / -70% | 0.0% (-4.38) | 100% | -2.27 | -4.31 | 0.000 | **FAIL** (all) |
| H4 | Regime-filtered intraday mean reversion | -0.35 / -0.1% / -2% | 1.2% (-2.80) | 80% | -0.85 | -1.51 | 0.000 | **FAIL** (all) |

**Why they fail.** Gross edge per trade, in pips, for the reference settings:

| hypothesis | EURUSD | GBPUSD | USDJPY | AUDUSD | USDCAD | USDCHF | NZDUSD | cost per trade |
|------------|--------|--------|--------|--------|--------|--------|--------|----------------|
| H1 (30 min, exit 12:00) | -0.17 | -0.32 | +0.09 | +0.38 | +0.51 | -0.55 | +0.30 | 1.9-2.9 pips |
| H3 (60 min pre, 120 min post) | +0.65 | +0.12 | -0.96 | -0.28 | -0.17 | +0.03 | -0.31 | 3.8-5.8 pips |

None of these is statistically meaningful (|t| < 2.3), and every one is far smaller than the cost of trading.
Two findings:

- **Seeck's USDJPY London-open effect** is near zero in this sample (+0.09 pip per trade gross).
- **The fix pattern of Krohn et al.** may exist at the scale of institutional costs. At retail costs it is not
  tradable.

**H4 (mean reversion)** barely lost money only because the walk-forward kept choosing the most extreme entry
threshold (k = 3.0), which trades almost never. Its random settings were negative 98.8% of the time.

## What this teaches the next rounds
Strategies that trade every day on the majors pay 2-6 pips per trade, and short-horizon FX moves carry well
under 1 pip of predictable edge. **Future rounds should favour fewer, larger trades**, meaning multi-day holds
where the expected move is many times the cost, and should require every hypothesis to state its expected gross
edge per trade relative to cost before testing.

Charts: `results/equity.png`, `results/param_mc.png`, `results/return_mc.png`. All numbers are in
`results/summary.json`.
