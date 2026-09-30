# Lab round 7 (gotobi Tokyo-fix effect): results

**Verdict: neither hypothesis validates.** However, **M1 is the first real, persistent signal found in 7
rounds**, and it is documented here in detail.

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC: sets > 0 | P(loss) | dev 2012-16 | holdout 2024-26 | deflated Sharpe | result |
|----|------------|-------------------------------------------|--------------------|---------|-------------|-----------------|-----------------|--------|
| M1 | Gotobi: buy USDJPY before the 09:55 Tokyo fix | **+0.70 / +1.13% / -1.8%** | 33% | **2%** | +0.18 | **+0.61** | 0.005 | **FAIL** (c2, c5, c6) |
| M2 | Gotobi: fade USDJPY after the fix | -0.26 / -0.58% | 0% | 81% | +0.44 | -0.52 | 0.000 | **FAIL** (c1-3, c5, c6) |

- **Data:** HistData USDJPY 5-minute bars, 2012-01-02 .. 2026-09-25 (3,841 Tokyo days, 1,060 gotobi days).
- **Engine check:** 398 out-of-sample M1 trades recomputed directly from the raw 5-minute data match the engine
  to within 4e-19.
- **Reproduce:** `python -m edge.lab.r7.research` (under 1 minute).

## M1 in detail
- **Stable parameter choice.** The walk-forward chose a **07:00 Tokyo entry in every year** from 2017 to 2026.
- **Gross move** (mid to mid, before costs) on out-of-sample gotobi days, by entry time:

  | entry | 07:00 | 07:30 | 08:00 | 08:30 | 09:00 | 09:30 |
  |-------|-------|-------|-------|-------|-------|-------|
  | pips  | +3.57 | +2.30 | +2.02 | +2.05 | +1.22 | +0.75 |

  Retail cost is 2.1 pips per round trip, so only the 07:00 entry clears it clearly. This is why only 33% of the
  random settings were profitable (criterion 2 fails).
- **Control:** the same trade on non-gotobi days has an out-of-sample Sharpe of -1.55. **The effect is specific
  to gotobi days**, consistent with Ito & Yamada's mechanism of corporate dollar demand at the fix.
- **Out of sample and holdout:** both positive (Sharpe 0.70 and 0.61), and P(loss) over 2017-23 is only 2%.
- **Size, the main problem.** Unlevered it makes 1.1% a year, because it trades only about 6 mornings a month.
  - At the owner's leverage cap (5x) that is about **0.45% a month**, with a maximum drawdown of about 9%.
  - Reaching 2% a month would need about 36x leverage (criterion 5 fails).
- **Deflated Sharpe 0.005 (criterion 6 fails).** After 23 trials the luck threshold is Sharpe 1.67. That
  threshold is inflated by the very negative intraday trials in the ledger, which widen the spread of trial
  Sharpes. The pre-registered criterion is applied as written: M1 is **not validated**.

## M2
The reversal after the fix exists but is too small: 1-2.6 pips gross against 2.1 pips of cost. It does not
survive costs.

## What this means
M1 is a genuine, mechanism-backed, out-of-sample-stable edge, but it is **small**, far below 2% a month. It is
not validated under the pre-registered rules, so **it is not deployed**. A clean next step, which is the
owner's decision, is a **paper-trading forward test on the SIM account**. That would provide new evidence that
none of the 23 trials have seen.
