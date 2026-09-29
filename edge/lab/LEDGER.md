# Strategy lab ledger

**Append-only.** Every hypothesis ever tested is listed here, whether it passed or failed. Its trial count feeds the
Deflated Sharpe Ratio (`edge/lab/dsr.py`). Never delete or edit a past row.

## Status
- rounds_completed: 2 (round 1 = edge/fx, round 2 = edge/fx2; the pre-lab study in edge/ is listed below too)
- max_rounds: 30
- candidate_in_forward_test: none
- final_outcome: none yet

## Trials so far (one row per hypothesis family; OOS = walk-forward 2017-2023 net Sharpe unless noted)
| id | round | market | hypothesis | OOS Sharpe | validated | report |
|----|-------|--------|------------|-----------|-----------|--------|
| E1 | pre | SPY | RSI(2) pullback | n/a (block test) | no | edge/REPORT.md |
| E2 | pre | SPY | Turn of month | n/a | no | edge/REPORT.md |
| E3 | pre | SPY | Overnight drift | n/a | no | edge/REPORT.md |
| E4 | pre | SPY | 10-month SMA filter | n/a | yes (overlay only) | edge/REPORT.md |
| E5 | pre | 18 markets | Multi-asset TS momentum | n/a | yes (~2.5%/yr) | edge/REPORT.md |
| E6 | pre | FX monthly | FX TS momentum | n/a | no | edge/REPORT.md |
| F1 | 1 | 7 FX majors daily | MA trend | -0.195 | no | edge/fx/REPORT.md |
| F2 | 1 | 7 FX majors daily | TS momentum | -0.280 | no | edge/fx/REPORT.md |
| F3 | 1 | 7 FX majors daily | Donchian breakout | -0.384 | no | edge/fx/REPORT.md |
| F4 | 1 | 7 FX majors daily | Cross-sectional momentum | -0.480 | no | edge/fx/REPORT.md |
| F5 | 1 | 7 FX majors daily | z-score mean reversion | -0.201 | no | edge/fx/REPORT.md |
| G1 | 2 | 21 FX crosses daily | Cross-pair mean reversion | 0.160 | no | edge/fx2/REPORT.md |
| G2 | 2 | 7 FX majors daily | Short-term cross-sectional reversal | -0.582 | no | edge/fx2/REPORT.md |
| G3 | 2 | 7 FX majors daily | Month-end equity-hedge flow | 0.201 | no | edge/fx2/REPORT.md |
| G4 | 2 | 21 FX crosses daily | Trend on crosses | -0.132 | no | edge/fx2/REPORT.md |

FX trial count for the DSR = the number of FX rows (F*, G* and every later FX row). Currently: 9.
