# Lab round 8 (gold and silver): results, and a correction to round 7

**Verdict: none of N1-N3 validates.** More importantly, this round uncovered a **data artifact** that inflated
N2 and the round-7 M1 result.

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC > 0 | P(loss) | dev 2012-16 | holdout 2024-26 Sharpe / per year | DSR | result |
|----|------------|-------------------------------------------|--------------|---------|-------------|-----------------------------------|-----|--------|
| N1 | Time-series momentum, gold + silver | -0.31 / -3.0% / -27% | 4% | 85% | +0.01 | +1.54 / +16.4% | 0.000 | **FAIL** |
| N2 | Gold Asian-session drift | +0.51 / +1.1% / -4% | 33% | 11% | +0.19 | +2.06 / +5.9% | 0.001 | **FAIL** (c2, c5, c6); **mostly an artifact** (see below) |
| N3 | Gold/silver ratio mean reversion | -0.36 / -0.6% / -7% | 0% | 78% | +0.13 | -0.50 / -1.4% | 0.000 | **FAIL** |

## Finding: the rollover-spread artifact (affects N2 and round-7 M1)
- **Why it happens.** HistData provides **bid prices only**. At the daily rollover (17:00 New York), dealer
  spreads widen sharply for 30-60 minutes, so the **bid dips** and then recovers. In the data, a strategy that
  "buys" at 18:00 New York appears to buy cheaply. In reality it would pay the wide ask, and that cheap price
  does not exist.
- **The evidence:**
  - Gold's bid rises **+2.4 to +2.9 bp in the first 30 minutes after 18:00** on all days (the same in 2012-26).
    From 18:30 onward the drift is flat (18:30-19:00: -0.4 bp out of sample).
  - USDJPY on **non-gotobi** days rises **+0.9 pips from 07:00 to 07:30 Tokyo** (18:00-18:30 New York), after
    dipping -0.4 pips into the rollover.
- **N2 corrected.** The post-artifact drift (19:00-04:00 New York) is about +1.2 bp a night out of sample,
  against 2 bp of cost. That is negative after costs. The strong holdout mostly reflects gold's 2024-26 bull
  market: a long-only overnight position benefits from the trend.
- **M1 (round 7) corrected, post-hoc.** The gotobi-specific part of the move is real:

  | window | gotobi days | non-gotobi days | gotobi excess |
  |--------|-------------|-----------------|---------------|
  | 07:00-09:55 | +3.57 pips | +1.28 pips | +2.3 |
  | 07:30-09:55 | +2.30 pips | +0.72 pips | +1.6 |

  A realistic entry outside the artifact window (07:30 Tokyo) makes **about +2.3 pips gross against 2.1 pips of
  cost, so roughly zero net**. **M1's reported Sharpe of 0.70 overstated the tradable edge.**
- **N1.** Trend on metals failed in 2017-23 (choppy gold) and did very well in 2024-26 (the gold rally), so it is
  inconsistent. The walk-forward switched lookbacks often.

## Consequences
1. **New charter rule:** no entry or exit between **16:55 and 18:30 New York** unless the test uses real bid/ask
   data for that window.
2. **The M1 shadow forward test is redefined** to track the artifact-free variant (entry 07:30 Tokyo = 18:30 New
   York), labelled **M1b** (a new trial), alongside the original frozen M1 for comparison. The expected net for
   M1b is about zero, and the owner is told plainly.
3. **The cumulative verdict is unchanged, and slightly worse:** no validated edge. The gotobi effect exists but is
   roughly the size of retail costs.
