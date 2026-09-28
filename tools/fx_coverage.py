"""Report which pre-registered FX fetch windows (lastdates) are still missing per pair.
Run after tools/extract_bars.py. A window counts as covered if the CSV has >=60 bars
in the 140 calendar days ending at that lastdate."""
import pandas as pd, os
LAST = "2026-09-30 2026-05-18 2026-01-03 2025-08-21 2025-04-08 2024-11-24 2024-07-12 2024-02-28 2023-10-16 2023-06-03 2023-01-19 2022-09-06 2022-04-24 2021-12-10 2021-07-28 2021-03-15 2020-10-31 2020-06-18 2020-02-04 2019-09-22 2019-05-10 2018-12-26 2018-08-13 2018-03-31 2017-11-16 2017-07-04 2017-02-19 2016-10-07 2016-05-25 2016-01-11 2015-08-29 2015-04-16 2014-12-02 2014-07-20 2014-03-07 2013-10-23 2013-06-10 2013-01-26 2012-09-13 2012-05-01 2011-12-18 2011-08-05 2011-03-23 2010-11-08 2010-06-26 2010-02-11 2009-09-29 2009-05-17 2009-01-02 2008-08-20 2008-04-07 2007-11-24 2007-07-12 2007-02-27".split()
for s in "EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF NZDUSD".split():
    p = f"data/tradestation/{s}_daily.csv"
    if not os.path.exists(p):
        print(s, "missing all"); continue
    d = pd.to_datetime(pd.read_csv(p).iloc[:, 0])
    miss = [l for l in LAST if ((d > pd.Timestamp(l) - pd.Timedelta(days=140)) & (d <= pd.Timestamp(l))).sum() < 60]
    gaps = d[d.diff().dt.days > 5].dt.date.tolist()
    print(s, len(d), "missing:", " ".join(miss) if miss else "none", "| gaps>5d before:", gaps)
