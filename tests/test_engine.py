"""Engine checks on small hand-built price bars (test fixtures, not market data).

Run:  python tests/test_engine.py      (or: python -m pytest tests)
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fxbot.data import load_daily, trading_day  # noqa: E402
from fxbot.engine import PIP, Account, Backtester, Costs  # noqa: E402
from fxbot.strategy import LEGACY, Params, add_features, signals  # noqa: E402

NO_COSTS = Costs(spread_pips=0.0, commission_per_lot=0.0, swap_per_lot_night=0.0)


def bars(rows, atr=0.0050):
    """rows: list of (open, high, low, close) on consecutive weekdays."""
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "date", pd.bdate_range("2024-01-01", periods=len(df)))
    df["atr14"] = atr
    return df


def test_signals_do_not_look_ahead():
    feat = add_features(load_daily())
    cut = 1500
    base = signals(feat, LEGACY)[:cut]
    altered = load_daily()
    altered.loc[cut:, ["open", "high", "low", "close"]] *= 1.2   # change only the future
    again = signals(add_features(altered), LEGACY)[:cut]
    assert (base == again).all()


def test_gap_through_stop_fills_at_open():
    # signal on bar 0; enter bar 1 open 1.1000; stop 50 pips; bar 2 gaps down to 1.0900
    df = bars([(1.1000, 1.1010, 1.0990, 1.1000),
               (1.1000, 1.1020, 1.0960, 1.1010),
               (1.0900, 1.0920, 1.0880, 1.0910)])
    bt = Backtester(df, costs=NO_COSTS)
    t = bt._daily_trade(0, Params(entry="open", atr_mult=1.0, max_hold=5), len(df) - 1)
    assert t["reason"] == "STOP (GAP)" and abs(t["exit"] - 1.0900) < 1e-9


def test_same_bar_stop_and_target_counts_as_stop():
    df = bars([(1.1000, 1.1010, 1.0990, 1.1000),
               (1.1000, 1.1200, 1.0900, 1.1000)])      # bar 1 spans both levels
    bt = Backtester(df, costs=NO_COSTS)
    t = bt._daily_trade(0, Params(entry="open", atr_mult=1.0, rr=3.0, max_hold=5), len(df) - 1)
    assert t["reason"] == "STOP" and t["ambiguous"]


def test_target_and_costs():
    df = bars([(1.1000, 1.1010, 1.0990, 1.1000),
               (1.1000, 1.1010, 1.0990, 1.1000),
               (1.1000, 1.1160, 1.0995, 1.1150)])      # target = entry + 3 x 50 pips
    costs = Costs(spread_pips=0.0, commission_per_lot=7.0, swap_per_lot_night=-6.0)
    bt = Backtester(df, costs=costs)
    t = bt._daily_trade(0, Params(entry="open", atr_mult=1.0, max_hold=5), len(df) - 1)
    t["risk"] = 100.0
    units, lots, nights, gross, comm, swap = bt._costs(t)
    assert t["reason"] == "TARGET"
    assert abs(gross - 300.0) < 1e-6                      # 3R on $100 risk
    assert abs(lots - 0.2) < 1e-9                         # $100 / 50 pips = 0.2 lots
    assert abs(comm - 1.4) < 1e-9 and nights == 1 and abs(swap + 1.2) < 1e-9


def test_confirm_entry_waits_for_up_close():
    df = bars([(1.1000, 1.1010, 1.0950, 1.0960),       # pullback day
               (1.0960, 1.0990, 1.0940, 1.0950),       # down close: no entry
               (1.0950, 1.0990, 1.0940, 1.0980)])
    bt = Backtester(df, costs=NO_COSTS)
    assert bt._daily_trade(0, Params(entry="confirm"), len(df) - 1) is None
    t = bt._daily_trade(1, Params(entry="confirm"), len(df) - 1)
    assert t["at_close"] and abs(t["entry"] - 1.0980) < 1e-9


def test_throttle_halves_risk_below_line():
    feat = add_features(load_daily())
    acct = Account(throttle_below=20_000.0)            # always below -> always throttled
    trades, _ = Backtester(feat, acct).run(LEGACY, "2018-01-01", "2019-12-31")
    assert len(trades) and (trades["risk_usd"] == 50.0).all()


def test_trading_day_rolls_at_5pm_new_york():
    ts = pd.Series(pd.to_datetime(["2024-01-02 21:00", "2024-01-02 22:00"]).tz_localize("UTC"))
    d = trading_day(ts)
    assert d.iloc[0] == pd.Timestamp("2024-01-02") and d.iloc[1] == pd.Timestamp("2024-01-03")


def test_h1_entry_uses_next_bar_open():
    daily = bars([(1.1000, 1.1010, 1.0990, 1.1000)] * 3)
    daily["date"] = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
    # 1H bars for trade day 2024-01-03 (22:00 UTC Jan 2 .. 21:00 UTC Jan 3): a dip then a rally
    ts = pd.date_range("2024-01-01 22:00", "2024-01-04 21:00", freq="h", tz="UTC")
    close = np.full(len(ts), 1.1000)
    day3 = (ts >= "2024-01-02 22:00") & (ts < "2024-01-03 22:00")
    k = np.flatnonzero(day3)
    close[k[:8]] = 1.1000 - np.arange(1, 9) * 2 * PIP
    close[k[8:]] = close[k[7]] + np.arange(1, len(k) - 7) * 4 * PIP
    h1 = pd.DataFrame({"timestamp": ts, "open": close, "high": close + PIP, "low": close - PIP, "close": close})
    h1["trade_date"] = trading_day(h1["timestamp"])
    bt = Backtester(daily, costs=NO_COSTS, h1=h1)
    t = bt._h1_trade(0, Params(entry="h1", atr_mult=1.0, max_hold=2), len(daily) - 1)
    assert t is not None
    conf = bt.h1.index[bt.h1["confirm"] & (bt.h1["trade_date"] == "2024-01-03")][0]
    assert abs(t["entry"] - bt.h1["open"].iloc[conf + 1]) < 1e-12


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
