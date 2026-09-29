"""Candidate EURUSD strategy families for the FTMO study (daily bars, long and/or short).

Each system turns daily features into *orders for the next day*, decided at the
close of day s and executed on day s+1, so nothing uses information from the
future:

    market   enter at the next open in direction dir[s]
    stop     buy-stop at long_lvl[s] and/or sell-stop at short_lvl[s], valid for day s+1

and fixed exit rules: stop = sl_mult x ATR(14) from the fill, then either a
fixed target (rr x stop distance), a trailing channel exit, an exit when the
signal flips, and/or a time limit.

All parameter values below are textbook defaults chosen before looking at
results (Donchian 20/55, momentum 3/6 months, RSI(3) pullback, 0.5-0.8 ATR
volatility breakout). The study picks among them on 2018-2021 only.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import atr, ema, rsi

PIP = 0.0001


@dataclass(frozen=True)
class System:
    name: str
    family: str
    direction: str = "both"          # 'long' or 'both'
    sl_mult: float = 2.0
    rr: float = 3.0                  # fixed target in R; 0 = no fixed target
    trail_n: int = 0                 # exit on an n-day channel break (0 = off)
    flip_exit: bool = False          # exit at the next open when the signal reverses
    max_hold: int = 60               # trading days
    params: tuple = field(default_factory=tuple)

    def label(self):
        exits = [f"target {self.rr:g}R"] if self.rr else []
        if self.trail_n:
            exits.append(f"trail {self.trail_n}d channel")
        if self.flip_exit:
            exits.append("exit on signal flip")
        exits.append(f"max {self.max_hold}d")
        side = "long only" if self.direction == "long" else "long + short"
        return f"{self.name} | {side} | stop {self.sl_mult:g}xATR | " + ", ".join(exits)


def features(df):
    out = df.copy()
    c = out["close"]
    out["atr14"] = atr(out, 14)
    for n in (1, 5, 9, 50):
        out[f"ema{n}"] = ema(c, n)
    out["rsi14"] = rsi(c, 14)
    out["rsi3"] = rsi(c, 3)
    for n in (10, 20, 27, 55):
        out[f"hh{n}"] = out["high"].rolling(n).max()
        out[f"ll{n}"] = out["low"].rolling(n).min()
    for n in (63, 126):
        out[f"mom{n}"] = np.sign(c / c.shift(n) - 1)
    return out


def orders(feat, sysm):
    """Return dict of arrays indexed by decision day s (for execution on s+1)."""
    n = len(feat)
    kind = "market"
    dir_ = np.zeros(n)
    long_lvl = np.full(n, np.nan)
    short_lvl = np.full(n, np.nan)
    signal = np.zeros(n)              # used by flip_exit
    allow_short = sysm.direction == "both"
    f = sysm.family
    p = dict(sysm.params)

    if f == "donchian":
        k = p["n"]
        kind = "stop"
        long_lvl = (feat[f"hh{k}"] + PIP).to_numpy()
        if allow_short:
            short_lvl = (feat[f"ll{k}"] - PIP).to_numpy()
    elif f == "momentum":
        sig = feat[f"mom{p['lookback']}"].fillna(0).to_numpy()
        if not allow_short:
            sig = np.where(sig > 0, 1.0, 0.0)
        dir_ = sig.copy()
        signal = sig
    elif f == "pullback":
        up = ((feat["ema1"] > feat["ema5"]) & (feat["ema5"] > feat["ema9"]) & (feat["rsi14"] > 50))
        dn = ((feat["ema1"] < feat["ema5"]) & (feat["ema5"] < feat["ema9"]) & (feat["rsi14"] < 50))
        longs = up.shift(1, fill_value=False) & (feat["rsi3"] < p["rsi_lo"])
        shorts = dn.shift(1, fill_value=False) & (feat["rsi3"] > 100 - p["rsi_lo"])
        dir_ = longs.to_numpy(float) - (shorts.to_numpy(float) if allow_short else 0.0)
    elif f == "volbreak":
        kind = "stop"
        nxt_open = feat["open"].shift(-1)
        off = feat["atr14"] * p["k"]
        trend_up = feat["close"] > feat["ema50"]
        long_lvl = np.where(trend_up, nxt_open + off, np.nan)
        if allow_short:
            short_lvl = np.where(~trend_up, nxt_open - off, np.nan)
    else:
        raise ValueError(f)
    ready = feat["atr14"].notna().to_numpy() & (np.arange(n) >= 130)   # indicator warm-up
    dir_ = np.where(ready, dir_, 0.0)
    long_lvl = np.where(ready, long_lvl, np.nan)
    short_lvl = np.where(ready, short_lvl, np.nan)
    return {"kind": kind, "dir": dir_, "long_lvl": long_lvl, "short_lvl": short_lvl, "signal": signal}


def candidates():
    """The pre-registered candidate list (every one is reported)."""
    out = []
    for d in ("long", "both"):
        for n in (20, 55):
            out.append(System(f"Donchian {n}", "donchian", d, 2.0, 3.0, 0, False, 60, (("n", n),)))
            out.append(System(f"Donchian {n}", "donchian", d, 2.0, 0.0, n // 2, False, 120, (("n", n),)))
        for lb in (63, 126):
            out.append(System(f"Momentum {lb}d", "momentum", d, 3.0, 3.0, 0, True, 60, (("lookback", lb),)))
            out.append(System(f"Momentum {lb}d", "momentum", d, 3.0, 0.0, 0, True, 250, (("lookback", lb),)))
        out.append(System("Pullback RSI3", "pullback", d, 1.0, 3.0, 0, False, 5, (("rsi_lo", 45),)))
        for k in (0.5, 0.8):
            out.append(System(f"Vol breakout {k:g}ATR", "volbreak", d, 1.0, 3.0, 0, False, 10, (("k", k),)))
    return out
