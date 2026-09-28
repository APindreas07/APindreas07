# Data fetch progress (TradeStation get-bars, 100 bars per call)
Rebuild CSVs any time with: python tools/extract_bars.py
ALL DONE. 0 duplicate conflicts, 0 OHLC violations, 0 missing months.
SPY daily: 6750 bars, 1999-11-23 .. 2026-09-25 (only gaps are real closures 2001-09-11..14, 2007-01-02, 2012-10-29/30).
QQQ daily: 5981 bars, 2002-12-16 .. 2026-09-25.
Monthly (unit Monthly, barsback 100, lastdates 2026-09-30, 2018-05-31, 2010-01-31), all to 2026-09 (partial, through 09-25):
  IWM EFA 2001-10 | EEM 2003-04 | TLT IEF 2002-07 | GLD 2004-11 | SLV USO 2006-04 | DBC 2006-02
  EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD 2001-10
SPY month-ends: monthly file 1993-04..1999-11, daily month-ends after (identical on the overlap).

## FX daily fetch (for edge/fx, pre-registered in edge/fx/PREREGISTRATION.md)
unit Daily, barsback 100. lastdates (135-day steps): 2026-09-30 2026-05-18 2026-01-03 2025-08-21 2025-04-08 2024-11-24 2024-07-12 2024-02-28 2023-10-16 2023-06-03 2023-01-19 2022-09-06 2022-04-24 2021-12-10 2021-07-28 2021-03-15 2020-10-31 2020-06-18 2020-02-04 2019-09-22 2019-05-10 2018-12-26 2018-08-13 2018-03-31 2017-11-16 2017-07-04 2017-02-19 2016-10-07 2016-05-25 2016-01-11 2015-08-29 2015-04-16 2014-12-02 2014-07-20 2014-03-07 2013-10-23 2013-06-10 2013-01-26 2012-09-13 2012-05-01 2011-12-18 2011-08-05 2011-03-23 2010-11-08 2010-06-26 2010-02-11 2009-09-29 2009-05-17 2009-01-02 2008-08-20 2008-04-07 2007-11-24 2007-07-12 2007-02-27
ALL 7 PAIRS COMPLETE (EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD), 2006-10..2026-09, ~5185 bars each, no gaps >5 days.
Resume: run `python3 tools/extract_bars.py >/dev/null && python3 tools/fx_coverage.py` -> it lists the lastdates still missing per pair. Fetch those, repeat until all "none".
