# Strategy lab round 10: pre-registration (P1 with real financing)

Written and pushed **before** any round-10 test is run, and never changed afterwards. Announced to the owner in
report #10, with no objection.

## Why
Round 9's model P1 had a **gross** Sharpe of about 0.39 (2017-2026, most-chosen setting) but was negative after
costs, mainly because of a **flat swap charge of 2-4% a year in both directions**. Real FX financing depends on
the interest-rate differential: it is earned on some positions and paid on others. This round replaces the flat
charge with **real daily carry** and asks whether P1 then passes.

## Data
Monthly 3-month interbank rates (OECD IR3TIB, % per year) for USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD, NOK, SEK,
PLN, HUF and CZK, 2006-01 .. 2026-08, forward-filled (`tools/rates.py` -> `data/rates/ir3m_monthly.csv`).
- Each day uses the rate of the **previous** month, so there is no look-ahead.
- Rates are used **only for financing**, never as model features or signals.

## Financing model (replaces the flat swap charge)
For an instrument BASE/QUOTE held long overnight (each 17:00 New York rollover):
- daily carry = (r_BASE - r_QUOTE) / 100 / 360;
- short positions receive the negative of that;
- **minus a broker markup of 1.0% a year** on notional, in either direction (conservative retail).

For **XAUUSD and XAGUSD**, the long carry is -r_USD (the metal lease rate is taken as zero, which is
conservative), minus the same 1.0% markup.

## Hypothesis
**Q1 = P1 exactly as pre-registered in round 9**, with the same:
- features;
- target;
- ridge model;
- walk-forward retraining;
- rebalance rule;
- transaction costs;
- grids (H {1, 5, 10, 20} x lambda {1, 10, 100} x q {0, 0.5, 0.8});
- parameter Monte Carlo ranges.

**Only the financing term changes.** Parameter Monte Carlo seed 20261007.

## Pass criteria
- edge/lab/AGENT.md criteria 1-6.
- Deflated Sharpe with n_trials = 28 (27 earlier rows + Q1).
- Q1 is a new trial, because it re-uses P1's model with a different cost assumption.
