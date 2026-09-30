# Lab round 9 (machine learning, 18 instruments): results

**Verdict: P1 fails every criterion.**

| id | hypothesis | WF OOS 2017-23 Sharpe / per year / max DD | param MC > 0 (median) | P(loss) | dev 2014-16 | holdout 2024-26 | DSR | result |
|----|------------|-------------------------------------------|-----------------------|---------|-------------|-----------------|-----|--------|
| P1 | Pooled ridge model, 17 technical features, 7 majors + 9 Scandinavian/CEE + gold + silver | -0.88 / -2.5% / -20% | 2% (-0.88) | 99% | -0.51 | -0.42 / -0.8% | 0.000 | **FAIL** (all) |

- **No look-ahead:** each year's model is trained only on the trailing 5 years, and only on rows whose targets
  end before the test year. Features are standardised on the training window only.
- **Rollover rule respected:** fills are at the first bar at or after 18:30 New York.
- **Walk-forward choices:** the hyperparameters settled on a 20-day horizon with an 80% confidence threshold from
  2020 onward.
- **Reproduce:** `python -m edge.lab.r9.research` (about 26 minutes).

## Gross versus net
For the most-chosen setting (H = 20, lambda = 1, q = 0.8), over 2017-2026:

| | Sharpe |
|---|---|
| net of costs and swap | -0.07 |
| gross (no costs, no swap) | **+0.39** |

So the model does find **some predictive information** at a 20-day horizon, but it is small, and trading costs
plus the **swap sensitivity** remove it. The swap is charged at 2-4% a year in both directions, which is
conservative: real swap is sometimes earned. This remains an open question that needs **interest-rate data** to
settle. Rates are allowed for cost modelling (not signals) under the charter. On the current, conservative
assumptions the result is a failure.

## Cumulative picture after 9 rounds
- 29 strategy families across FX majors, crosses, Scandinavian/CEE pairs, gold and silver, including machine
  learning. None validated.
- Two partial signals exist but do not survive realistic costs:
  - the gotobi USDJPY effect (about break-even after correcting the rollover artifact);
  - a weak 20-day predictive signal in the ML model (gross Sharpe of about 0.4).
