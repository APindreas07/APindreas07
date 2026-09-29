"""Position sizing and hard risk limits for deployed strategies (owner-set, 2026-09-29: CONSERVATIVE).

These limits are non-negotiable and are checked before every order:
  * risk per trade  <= 1% of current account equity (distance to the protective stop x units)
  * total gross notional of all open positions <= 5x equity
  * kill switch: if equity falls 10% below its running peak, flatten everything and stop trading

Deployment target is the TradeStation SIM (paper) account only.

Usage (from the agent):
    from edge.lab.deploy.risk import size_trade, kill_switch
    q = size_trade(pair="EURUSD", equity=100_000, entry=1.0850, stop=1.0820, usd_rates={...}, open_notional_usd=0)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

RISK_PER_TRADE = 0.01
MAX_GROSS_LEVERAGE = 5.0
KILL_DRAWDOWN = -0.10
LOT_STEP = 1_000            # round units down to 1k (micro lot)
EQUITY_LOG = Path(__file__).resolve().parent / "EQUITY.csv"


@dataclass
class Sizing:
    units: int
    risk_usd: float
    notional_usd: float
    reason: str


def usd_per_unit_move(pair: str, price: float, usd_rates: dict) -> float:
    """USD P&L of one unit for a price move of 1.0 in `pair` (quote currency converted to USD)."""
    quote = pair[3:]
    if quote == "USD":
        return 1.0
    if pair.startswith("USD"):
        return 1.0 / price                     # USDXXX: P&L in XXX, divide by USDXXX
    # cross XXXYYY: P&L in YYY -> USD via YYYUSD or USDYYY
    if f"{quote}USD" in usd_rates:
        return usd_rates[f"{quote}USD"]
    return 1.0 / usd_rates[f"USD{quote}"]


def notional_usd_per_unit(pair: str, price: float, usd_rates: dict) -> float:
    base = pair[:3]
    if base == "USD":
        return 1.0
    if pair.endswith("USD"):
        return price
    if f"{base}USD" in usd_rates:
        return usd_rates[f"{base}USD"]
    return 1.0 / usd_rates[f"USD{base}"]


def size_trade(pair: str, equity: float, entry: float, stop: float, usd_rates: dict,
               open_notional_usd: float = 0.0) -> Sizing:
    """Largest position (in units, rounded down to 1k) that satisfies BOTH the 1% risk and the 5x leverage caps."""
    dist = abs(entry - stop)
    if dist <= 0 or equity <= 0:
        return Sizing(0, 0.0, 0.0, "invalid stop or equity")
    risk_units = RISK_PER_TRADE * equity / (dist * usd_per_unit_move(pair, entry, usd_rates))
    n_per = notional_usd_per_unit(pair, entry, usd_rates)
    room = MAX_GROSS_LEVERAGE * equity - open_notional_usd
    lev_units = max(room, 0.0) / n_per
    units = int(min(risk_units, lev_units) // LOT_STEP * LOT_STEP)
    why = "risk cap" if risk_units <= lev_units else "leverage cap"
    return Sizing(units, units * dist * usd_per_unit_move(pair, entry, usd_rates), units * n_per,
                  why if units > 0 else "no room under leverage cap")


def record_equity(timestamp: str, equity: float) -> None:
    new = not EQUITY_LOG.exists()
    with EQUITY_LOG.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "equity"])
        w.writerow([timestamp, f"{equity:.2f}"])


def kill_switch(current_equity: float) -> dict:
    """True if equity is 10% or more below its running peak (peak from EQUITY.csv plus the current value)."""
    peak = current_equity
    if EQUITY_LOG.exists():
        with EQUITY_LOG.open() as f:
            for row in csv.DictReader(f):
                peak = max(peak, float(row["equity"]))
    dd = current_equity / peak - 1
    return {"peak": peak, "drawdown": dd, "halt": dd <= KILL_DRAWDOWN}
