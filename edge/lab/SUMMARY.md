# FX strategy search: summary after 6 rounds (2026-09-30)

## The question
Can technical analysis on FX reach **2% a month net, compounded (26.8% a year)** within the owner's limits:
at most 1% risk per trade, at most 5x leverage, and trading stopped at a -10% drawdown?

## What was done
- **25 FX strategy families** tested in 6 rounds, plus 6 non-FX edges in the first study.
- **Every hypothesis** had:
  - its rules committed before testing;
  - real data (TradeStation, HistData);
  - retail costs;
  - annual walk-forward testing on unseen years;
  - 10,000 random parameter sets;
  - 10,000 return reshuffles;
  - a luck check (deflated Sharpe).
- **Coverage:**
  - Horizons: intraday (5-minute), daily, multi-day and weekly.
  - Markets: 7 majors, 21 crosses, and 9 Scandinavian and Central European pairs.
  - Families: trend, breakout, momentum, mean reversion, session effects, fix flows, month-end flows,
    equity-regime filters, and combinations.

## What was found

| rank | best results | out-of-sample Sharpe (2017-23) | notes |
|------|--------------|--------------------------------|-------|
| 1 | K3, a combination of G1 + G3 | 0.24 | Positive development period, 68% of random settings positive; negative 2024-26; about 0.09% a month within the limits |
| 2 | G3, month-end hedging flow | 0.20 | Strong 2008-16 (Sharpe 0.65), fading since, negative 2024-26 |
| 3 | G1, cross-pair mean reversion | 0.16 | Negative 2008-16 |
| - | Everything else | below 0 | Most were negative even before costs |

**No strategy passed.** The best result would have earned roughly **0.1% a month** within the risk limits,
about a twentieth of the target.

## Why
1. **No gross edge.** Before any costs, the daily and multi-day technical signals earned roughly zero in
   2012-2026.
2. **Costs.** Intraday signals carry well under 1 pip of edge per trade, while retail costs are 2-6 pips.
3. **Faded effects.** Effects documented in the academic literature have weakened or disappeared since
   publication, as the adaptive-markets research predicts: trend following faded in the early 1990s, month-end
   flows faded after 2015, and the equity/FX risk link weakened after 2013.

## The one real edge found anywhere
**E5, multi-asset trend following** (first study): about **2.5% a year** unlevered, positive in the holdout.
Its gains came mainly from **stock indices and gold**, not currencies.

## Options for the owner
1. **Continue the FX-only search** (up to 30 rounds). Honest expectation: low probability of success, with
   ongoing usage cost.
2. **Widen the instruments** to gold and silver, which trade on FX platforms, and possibly index CFDs. This is
   where the only real edge was found.
3. **Keep FX, lower the target**: aim for a robust small edge (e.g. K3-like diversification) instead of 2% a
   month.
4. **Stop the search**, keeping all tools, data and reports for later.
