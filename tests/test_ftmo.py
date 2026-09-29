"""FTMO simulator checks on hand-built daily bars (test fixtures, not market data).

Run:  python tests/test_ftmo.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fxbot.ftmo import FTMORules, FTMOSim, Sizing  # noqa: E402
from fxbot.systems import System  # noqa: E402

NO_COST = FTMORules(commission_per_lot=0.0, spread_pips=0.0, swap_long=0.0, swap_short=0.0)


def feat(rows, atr=0.0050):
    df = pd.DataFrame(rows, columns=["open", "high", "low", "close"])
    df.insert(0, "date", pd.bdate_range("2024-01-01", periods=len(df)))
    df["atr14"] = atr
    return df


class Always(System):
    """Market order in a fixed direction every day (fixture only)."""


def sim_with_orders(df, direction, rules=NO_COST, model="path"):
    sim = FTMOSim(df, rules, model)
    s = System("fixture", "fixture", "both", 1.0, 3.0, 0, False, 60)
    n = len(df)
    sim._orders[s] = {"kind": "market", "dir": np.full(n, float(direction)), "long_lvl": np.full(n, np.nan),
                      "short_lvl": np.full(n, np.nan), "signal": np.full(n, float(direction))}
    return sim, s


def test_short_trade_profits_when_price_falls():
    df = feat([(1.10, 1.1005, 1.0995, 1.10), (1.10, 1.1005, 1.0840, 1.0850), (1.085, 1.086, 1.084, 1.085)])
    sim, s = sim_with_orders(df, -1)
    t = sim.trade(0, s, len(df) - 1)
    assert t["d"] == -1 and t["reason"] == "TARGET" and abs(t["exit"] - (1.10 - 0.015)) < 1e-9


def test_daily_guard_closes_before_giving_back_profit():
    # long entered at 1.1000, closes +150 pips (+$600 floating), next day falls 200 pips
    df = feat([(1.1000, 1.1005, 1.0995, 1.1000),
               (1.1000, 1.1010, 1.0990, 1.1005),
               (1.1005, 1.1155, 1.1000, 1.1150),
               (1.1150, 1.1152, 1.0950, 1.0960),
               (1.0960, 1.0965, 1.0955, 1.0960)], atr=0.0100)
    sim, s = sim_with_orders(df, 1)
    trades, eq, oc = sim.run(s, Sizing(risk_pct=0.04), "2024-01-02", "2024-01-05", stop_on_breach=True)
    assert oc["result"] != "FAIL"
    assert trades.iloc[0]["exit_reason"] == "DAILY GUARD"
    worst_day_loss = (eq["day_start"] - eq["equity_low"]).max()
    assert worst_day_loss <= 500.0 - 100.0 + 1e-6


def test_without_guard_the_same_path_breaches_daily_loss():
    df = feat([(1.1000, 1.1005, 1.0995, 1.1000),
               (1.1000, 1.1010, 1.0990, 1.1005),
               (1.1005, 1.1155, 1.1000, 1.1150),
               (1.1150, 1.1152, 1.0950, 1.0960),
               (1.0960, 1.0965, 1.0955, 1.0960)], atr=0.0100)
    sim, s = sim_with_orders(df, 1)
    _, _, oc = sim.run(s, Sizing(risk_pct=0.04, daily_guard=False), "2024-01-02", "2024-01-05")
    assert oc["result"] == "FAIL" and oc["breach_rule"] == "DAILY LOSS"


def test_risk_never_exceeds_distance_to_floor():
    df = feat([(1.10, 1.1005, 1.0995, 1.10)] * 4, atr=0.0050)
    sim, s = sim_with_orders(df, 1)
    trades, _, _ = sim.run(s, Sizing(risk_pct=0.05), "2024-01-02", "2024-01-04", initial=9_300.0)
    # balance 9,300: floor 9,000 minus 1% buffer leaves $200 of risk at most
    assert trades.empty or (trades["risk_usd"] <= 200.0 + 1e-6).all()


def test_target_needs_four_trading_days():
    rows = [(1.10, 1.1005, 1.0995, 1.10), (1.10, 1.1160, 1.0995, 1.115)] + [(1.115, 1.1155, 1.1145, 1.115)] * 8
    df = feat(rows, atr=0.0050)
    sim, s = sim_with_orders(df, 1)
    sim._orders[s]["dir"][2:] = 0.0          # only one real trade
    _, eq, oc = sim.run(s, Sizing(risk_pct=0.04), "2024-01-02", "2024-01-12", target=0.10)
    assert oc["result"] == "PASS"
    assert len(eq) >= 4                      # waited for the remaining trading days


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
