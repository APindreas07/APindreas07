# FX strategy search: FINAL REPORT (2026-10-01)

**Status: search stopped at the owner's request** ("do 1 now, give the final report, and stop everything till I
decide", 2026-10-01 10:04 UTC). All work is paused until the owner gives new instructions.

## The goal
Technical analysis on FX (later also gold and silver), aiming for **2% a month, compounded (26.8% a year)**,
within the owner's conservative limits:
- at most 1% risk per trade;
- at most 5x leverage;
- trading stops at a -10% drawdown;
- deployment to the TradeStation SIM account only.

## Verdict
**No strategy validated. The 2% a month target is not supported by any evidence found.** The best real effects
are about the size of retail trading costs. None reliably earns even 0.5% a month within the limits.

## What was done
- **Scale:** 11 lab rounds plus 3 earlier studies, **32 lab trials** (ledger: `edge/lab/LEDGER.md`), plus 6
  non-FX edges in study 1.
- **Every trial had:**
  - rules committed and pushed **before** testing;
  - real data;
  - retail costs;
  - annual walk-forward testing on unseen years;
  - 10,000 random parameter sets;
  - 10,000 block-bootstrap resamples of real returns;
  - a deflated-Sharpe luck check;
  - an engine check against an explicit trade-by-trade loop.
- **Markets:**
  - 7 USD majors;
  - 21 crosses;
  - 9 Scandinavian and Central European pairs (NOK, SEK, PLN, HUF, CZK against USD and EUR);
  - gold and silver.
- **Horizons:** 5-minute, daily, weekly, multi-week.
- **Strategy families:**
  - trend and breakout;
  - time-series and cross-sectional momentum;
  - mean reversion (single pairs, crosses, Scandinavian/CEE, gold/silver ratio);
  - session effects (London open, Asian range);
  - the London 4pm fix;
  - the Tokyo fix (gotobi);
  - month-end flows;
  - equity-regime filters and post-stress rebounds;
  - combinations of near-misses;
  - **machine learning** (a pooled ridge model on 17 features, retrained yearly);
  - all with both flat and **real interest-rate financing** (OECD 3-month rates).
- **Data sources:**
  - TradeStation daily bars;
  - HistData 1-minute bars (Dukascopy throttled bulk downloads);
  - OECD interest rates (FRED refused automated downloads).

## Best results found (none validated)

| trial | idea | out-of-sample 2017-23 | honest assessment |
|-------|------|-----------------------|-------------------|
| K3 | Combination of cross-pair mean reversion + month-end flow | Sharpe 0.24, +1.3%/yr | Negative 2024-26; about 0.09%/month within the limits |
| M1 / M1b | Gotobi: buy USDJPY before the 09:55 Tokyo fix | Sharpe 0.70 reported, **inflated by a rollover-spread artifact** | The real effect is +1.6 to +2.3 pips over ordinary days; **about break-even** after 2.1 pips of retail cost |
| P1 / Q1 | Machine learning, 18 instruments | Gross Sharpe of about 0.4 at a 20-day horizon | Negative after costs, even with real carry (-1.4%/yr) |
| G3 | Month-end equity-hedge flow | Sharpe 0.20 | Strong 2008-16, faded since, negative 2024-26 |

## Why nothing works (the evidence)
1. **No gross edge.** For most technical signals on these markets, returns before costs are about zero in
   2012-2026.
2. **Costs.** Intraday signals carry well under 1 pip of edge per trade, against 2-6 pips of retail cost.
3. **Decay.** Published effects faded after publication (trend in the 1990s, month-end flows after 2015, the
   equity/FX risk link after 2013), as the adaptive-markets research predicts.
4. **Data traps found and fixed along the way.**
   - Bid-only data inflates any trade at the 17:00-18:30 New York rollover. A permanent rule now bans such
     entries unless real bid/ask data is used.
   - HistData timestamps are New York time with daylight saving (verified against Dukascopy).

## The one robust edge found anywhere
**E5: multi-asset time-series momentum** (study 1, `edge/REPORT.md`). About **2.5% a year unlevered**, positive in
the 2024-26 holdout, with its gains mainly from stock indices and gold. It is not an FX strategy, and it needs
futures or ETF access rather than CFDs.

## State left behind (for when the owner resumes)
- **Code and results:**
  - `edge/lab/r3` .. `r11`: each round's pre-registration, engine and report;
  - `edge/lab/common.py`, `edge/lab/dsr.py`, `edge/lab/deploy/risk.py`;
  - tools: `tools/histdata.py`, `tools/dukascopy.py`, `tools/rates.py`.
- **Data:** `data/histdata/` (git-ignored, reproducible; hashes in `data/histdata_MANIFEST.csv`) and
  `data/rates/ir3m_monthly.csv`.
- **Deployment:** nothing deployed, and no orders were ever placed. The TradeStation SIM accounts cannot trade
  spot FX. The **gotobi shadow test is paused** before its first trade; its plan is in
  `edge/lab/deploy/M1_FORWARD.md`.
- **To resume:** tell the agent the new direction. `edge/lab/AGENT.md`, `STATE.md` and `LEDGER.md` hold
  everything needed.
