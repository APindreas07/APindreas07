"""Buy-only swing strategy: 1D chart for trend, 1D pullback for timing, 1H for confirmation.

Each indicator has one job, so none of them double-count the same information:

    1D trend      close above a rising EMA(N)            -> are we allowed to buy at all?
    1D pullback   RSI(3) closes below a threshold        -> is price temporarily cheap?
    1D volatility ATR(14) sizes the stop; target = 3R     -> how far can it move?
    Confirmation  price turns back up before we buy       -> has the dip stopped?

The trend is read from the day *before* the pullback day, because a pullback
often closes below short EMAs by definition. Everything a signal uses is known
at the signal day's close; entries happen on the next day.

Confirmation modes:
    open      buy the next day's open (no confirmation; the old behaviour)
    breakout  buy-stop 1 pip above the pullback day's high, valid next day only
              (strict: after these sharp down days it fills only ~9% of the time)
    confirm   buy at the next day's close only if that day closed up (above its
              open and above the pullback day's close): the daily-bar proxy for
              "the 1H chart turned up"
    h1        on the next day, buy the open of the first 1H bar after a 1H close
              above the 1H EMA(20) with 1H RSI(14) crossing up through 50
              (needs 1H data; see data.load_hourly)

The 'legacy' trend reproduces the previous script's filter (EMA1 > EMA5 > EMA9
and RSI(14) > 50) so its weaknesses can be measured against the new design.
"""

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from .indicators import atr, ema, rsi

TREND_CHOICES = ("legacy", "ema50", "ema100", "ema200")
ENTRY_CHOICES = ("open", "breakout", "confirm", "h1")


@dataclass(frozen=True)
class Params:
    trend: str = "ema100"
    rsi_thr: float = 35.0      # RSI(3) must close below this
    atr_mult: float = 1.5      # stop distance in ATR(14)s
    entry: str = "confirm"
    max_hold: int = 10         # trading days in the trade (entry day counts unless entering at its close)
    rr: float = 3.0            # fixed by the trading plan (1:3)

    def label(self):
        return (f"{self.trend} | RSI3<{self.rsi_thr:g} | SL {self.atr_mult:g}xATR | "
                f"{self.entry} | hold {self.max_hold}d | 1:{self.rr:g}")

    def as_dict(self):
        return asdict(self)


# The previous script's strategy, on the new account/cost model.
LEGACY = Params(trend="legacy", rsi_thr=40, atr_mult=1.0, entry="open", max_hold=5)


def add_features(df):
    """Daily indicator columns used by every parameter set."""
    out = df.copy()
    c = out["close"]
    for n in (1, 5, 9, 50, 100, 200):
        out[f"ema{n}"] = ema(c, n)
    out["rsi14"] = rsi(c, 14)
    out["rsi3"] = rsi(c, 3)
    out["atr14"] = atr(out, 14)
    out["trend_legacy"] = (out["ema1"] > out["ema5"]) & (out["ema5"] > out["ema9"]) & (out["rsi14"] > 50)
    for n in (50, 100, 200):
        rising = out[f"ema{n}"] > out[f"ema{n}"].shift(5)
        warm = np.arange(len(out)) >= n  # EMA needs ~n bars before it means anything
        out[f"trend_ema{n}"] = (c > out[f"ema{n}"]) & rising & warm
    return out


def signals(feat, p):
    """Boolean array: True at bar i means 'buy setup confirmed at the close of i'."""
    trend_prev = feat[f"trend_{p.trend}"].shift(1, fill_value=False).to_numpy(bool)
    pullback = (feat["rsi3"] < p.rsi_thr).to_numpy(bool)
    ready = feat["atr14"].notna().to_numpy(bool)
    return trend_prev & pullback & ready


# ---------------------------------------------------------------------------
# 1H confirmation
# ---------------------------------------------------------------------------
def add_hourly_features(h1):
    out = h1.copy()
    out["ema20"] = ema(out["close"], 20)
    out["rsi14"] = rsi(out["close"], 14)
    cross_up = (out["rsi14"] >= 50) & (out["rsi14"].shift(1) < 50)
    out["confirm"] = (out["close"] > out["ema20"]) & cross_up
    return out


def h1_entry(h1f, day_index, trade_date):
    """First 1H confirmation on `trade_date`; returns (bar position to enter at) or None.

    The confirmation is read at a 1H close, so the fill is the *next* 1H bar's open.
    `day_index` maps trade_date -> array of 1H row positions for that day.
    """
    rows = day_index.get(pd.Timestamp(trade_date))
    if rows is None:
        return None
    confirm = h1f["confirm"].to_numpy()
    for k in rows[:-1]:
        if confirm[k]:
            return k + 1
    return None
