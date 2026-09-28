# Data fetch progress (TradeStation get-bars, 100 bars per call)
Rebuild CSVs any time with: python tools/extract_bars.py
ALL DONE. 0 duplicate conflicts, 0 OHLC violations, 0 missing months.
SPY daily: 6750 bars, 1999-11-23 .. 2026-09-25 (only gaps are real closures 2001-09-11..14, 2007-01-02, 2012-10-29/30).
QQQ daily: 5981 bars, 2002-12-16 .. 2026-09-25.
Monthly (unit Monthly, barsback 100, lastdates 2026-09-30, 2018-05-31, 2010-01-31), all to 2026-09 (partial, through 09-25):
  IWM EFA 2001-10 | EEM 2003-04 | TLT IEF 2002-07 | GLD 2004-11 | SLV USO 2006-04 | DBC 2006-02
  EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD 2001-10
SPY month-ends: monthly file 1993-04..1999-11, daily month-ends after (identical on the overlap).
