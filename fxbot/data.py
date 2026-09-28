"""Price data loading.

Daily bars: data/eurusd_daily_tradestation.csv (date,open,high,low,close), real
EURUSD daily bars from the TradeStation market-data API. A TradeStation FX day
closes at 17:00 New York time, so bar "D" covers 17:00 NY on D-1 to 17:00 NY on D.

Hourly bars (optional, for the 1H confirmation): any CSV with a timestamp column
and open/high/low/close, e.g. an MT5 "Export bars" file from the FTMO terminal.
Timestamps are converted to the same 17:00-New-York trading day as the daily bars.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DAILY_FILE = ROOT / "data" / "eurusd_daily_tradestation.csv"


def load_daily(path=DAILY_FILE):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    return df[["date", "open", "high", "low", "close"]].astype(
        {"open": float, "high": float, "low": float, "close": float})


def load_hourly(path, tz="UTC"):
    """Load 1H bars and tag each with its 17:00-NY trading day.

    Accepts common layouts: a 'timestamp'/'datetime'/'time' column, or MT5's
    separate '<DATE>' and '<TIME>' columns. `tz` is the timezone the file's
    timestamps are written in (MT5 exports use the broker server time, which
    for FTMO is UTC+2/UTC+3, i.e. 'Europe/Athens'-like; pass it explicitly).
    """
    raw = pd.read_csv(path, sep=None, engine="python")
    cols = {c.lower().strip("<>"): c for c in raw.columns}
    if "date" in cols and "time" in cols:
        ts = pd.to_datetime(raw[cols["date"]].astype(str) + " " + raw[cols["time"]].astype(str))
    else:
        key = next(k for k in ("timestamp", "datetime", "time", "date") if k in cols)
        ts = pd.to_datetime(raw[cols[key]])
    ts = ts.dt.tz_localize(tz) if ts.dt.tz is None else ts
    out = pd.DataFrame({
        "timestamp": ts.dt.tz_convert("UTC"),
        "open": raw[cols["open"]].astype(float),
        "high": raw[cols["high"]].astype(float),
        "low": raw[cols["low"]].astype(float),
        "close": raw[cols["close"]].astype(float),
    }).sort_values("timestamp").reset_index(drop=True)
    out["trade_date"] = trading_day(out["timestamp"])
    return out


def trading_day(ts_utc):
    """Map UTC timestamps (bar open times) to the 17:00-NY FX trading day."""
    ny = ts_utc.dt.tz_convert("America/New_York")
    return (ny + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()
