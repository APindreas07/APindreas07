# Strategy lab ledger

**Append-only.** Every hypothesis ever tested is listed here, whether it passed or failed. Its trial count feeds the
Deflated Sharpe Ratio (`edge/lab/dsr.py`). Never delete or edit a past row.

## Status
- rounds_completed: 7 (round 7 = edge/lab/r7; round 6 = edge/lab/r6; round 5 = edge/lab/r5; round 1 = edge/fx, round 2 = edge/fx2, round 3 = edge/lab/r3, round 4 = edge/lab/r4; the pre-lab study in edge/ is listed below too)
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
| H1 | 3 | 7 FX majors 5-min | London-open momentum | -2.140 | no | edge/lab/r3/REPORT.md |
| H2 | 3 | USDJPY 5-min | London-open momentum, USDJPY only | -0.940 | no | edge/lab/r3/REPORT.md |
| H3 | 3 | 7 FX majors 5-min | London 4pm fix reversal | -3.360 | no | edge/lab/r3/REPORT.md |
| H4 | 3 | 7 FX majors 15-min | Regime-filtered intraday mean reversion | -0.350 | no | edge/lab/r3/REPORT.md |
| J1 | 4 | 7 majors + 21 crosses daily | Volatility-squeeze breakout, multi-day | -0.900 | no | edge/lab/r4/REPORT.md |
| J2 | 4 | 9 Scandi/CEE daily | Bollinger mean reversion, multi-day | -0.760 | no | edge/lab/r4/REPORT.md |
| J3 | 4 | 9 Scandi/CEE daily | Moving-average trend with stop | -1.010 | no | edge/lab/r4/REPORT.md |
| K1 | 5 | 6 risk crosses daily + SPY | SPY-regime risk-currency trend | -0.840 | no | edge/lab/r5/REPORT.md |
| K2 | 5 | 6 risk crosses daily + SPY | Rebound after equity stress | -0.100 | no | edge/lab/r5/REPORT.md |
| K3 | 5 | G1 + G3 streams | Combination of round-2 near-misses | 0.240 | no (closest so far) | edge/lab/r5/REPORT.md |
| L1 | 6 | EURUSD GBPUSD USDJPY 5-min | Asian-range breakout at London | -1.370 | no | edge/lab/r6/REPORT.md |
| L4 | 6 | 7 majors + 21 crosses daily | Weekly reversal after extreme weeks | -0.140 | no | edge/lab/r6/REPORT.md |
| M1 | 7 | USDJPY 5-min | Gotobi: buy before the 09:55 Tokyo fix | 0.703 | no (real but small; best so far) | edge/lab/r7/REPORT.md |
| M2 | 7 | USDJPY 5-min | Gotobi: fade after the fix | -0.260 | no | edge/lab/r7/REPORT.md |

FX trial count for the DSR = the number of FX rows (F*, G* and every later FX row). Currently: 23.
