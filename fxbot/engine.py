"""Trade simulation and prop-firm account.

Every trade is replayed bar by bar from real prices; nothing is random.

Fill rules (conservative where daily bars cannot tell the order of events):
    - Buys fill at the Ask (price + spread); exits at the Bid (the bar prices).
    - A bar that opens beyond the stop or target fills at that open (weekend gaps).
    - If one daily bar touches both stop and target, the stop is assumed first.
    - On a breakout entry day, a low under the stop counts as a stop even if it
      may have happened before the entry (daily bars can't tell). 1H data removes
      both ambiguities.

Account (FTMO-style 2-step challenge, all configurable):
    - $10,000 balance, fixed $100 risk per trade ($1k position budget x 10% max loss)
    - Max loss 10% of the initial balance: equity may never touch $9,000
    - Max daily loss 5%: equity may not fall more than $500 below the day's start balance
    - One position at a time, so at most one new trade per day
    - Optional drawdown throttle: risk a smaller amount while the balance is
      below a line (e.g. half risk below $9,500), to protect the max-loss floor

Equity is marked to market daily: at the close (equity_close) and at the day's
worst price (equity_low), which is what the prop-firm limits are checked against.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .strategy import Params, add_hourly_features, h1_entry, signals

PIP = 0.0001


@dataclass(frozen=True)
class Account:
    initial: float = 10_000.0
    risk_usd: float = 100.0
    max_loss_pct: float = 0.10
    daily_loss_pct: float = 0.05
    target_pct: float = 0.10
    throttle_below: float = 0.0     # e.g. 9500: while the balance is below this...
    throttle_factor: float = 0.5    # ...risk this fraction of risk_usd per trade (0 = off)


@dataclass(frozen=True)
class Costs:
    spread_pips: float = 1.5            # includes slippage allowance
    commission_per_lot: float = 7.0     # USD per 100k, round turn
    swap_per_lot_night: float = -6.0    # USD per 100k per night held, long EURUSD


class Backtester:
    def __init__(self, feat, account=Account(), costs=Costs(), h1=None):
        self.feat = feat.reset_index(drop=True)
        self.account = account
        self.costs = costs
        self.dates = self.feat["date"].to_numpy()
        self.o = self.feat["open"].to_numpy()
        self.h = self.feat["high"].to_numpy()
        self.l = self.feat["low"].to_numpy()
        self.c = self.feat["close"].to_numpy()
        self.atr = self.feat["atr14"].to_numpy()
        self._signals = {}
        self.h1 = None
        if h1 is not None:
            self.h1 = add_hourly_features(h1.reset_index(drop=True))
            self.h1_day_rows = {pd.Timestamp(d): np.asarray(v)
                                for d, v in self.h1.groupby("trade_date").indices.items()}
            self.date_pos = {pd.Timestamp(d): i for i, d in enumerate(self.dates)}

    def signal(self, p):
        if p not in self._signals:
            self._signals[p] = signals(self.feat, p)
        return self._signals[p]

    def index_range(self, start, end):
        d = self.feat["date"]
        idx = np.flatnonzero((d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end)))
        return (int(idx[0]), int(idx[-1])) if len(idx) else (None, None)

    # ------------------------------------------------------------------
    # Single trade
    # ------------------------------------------------------------------
    def _daily_trade(self, s, p, last_idx):
        """Signal at bar s, entry attempt on bar s+1. Returns a trade dict or None."""
        e = s + 1
        spread = self.costs.spread_pips * PIP
        at_close = False
        if p.entry == "open":
            fill = self.o[e]
        elif p.entry == "breakout":
            trigger = self.h[s] + PIP
            if self.h[e] < trigger:
                return None
            fill = max(self.o[e], trigger)
        elif p.entry == "confirm":
            if not (self.c[e] > self.o[e] and self.c[e] > self.c[s]):
                return None
            fill, at_close = self.c[e], True
        else:
            raise ValueError(p.entry)
        entry = fill + spread
        sl_dist = self.atr[s] * p.atr_mult
        sl, tp = entry - sl_dist, entry + sl_dist * p.rr
        first_j = e + 1 if at_close else e
        hold_end = min(first_j + p.max_hold - 1, last_idx)
        exit_i = exit_px = reason = None
        ambiguous = False
        hi = lo = entry
        for j in range(first_j, hold_end + 1):
            if j > e and self.o[j] <= sl:
                exit_i, exit_px, reason = j, self.o[j], "STOP (GAP)"
                lo = min(lo, self.o[j])
                break
            if j > e and self.o[j] >= tp:
                exit_i, exit_px, reason = j, self.o[j], "TARGET (GAP)"
                hi = max(hi, self.o[j])
                break
            hit_sl, hit_tp = self.l[j] <= sl, self.h[j] >= tp
            if hit_sl:
                ambiguous = hit_tp
                exit_i, exit_px, reason = j, sl, "STOP"
                lo = min(lo, sl)
                hi = max(hi, min(self.h[j], tp) if hit_tp else self.h[j])
                break
            if hit_tp:
                exit_i, exit_px, reason = j, tp, "TARGET"
                hi = max(hi, tp)
                lo = min(lo, self.l[j])
                break
            hi, lo = max(hi, self.h[j]), min(lo, self.l[j])
        if exit_i is None:
            exit_i, exit_px = hold_end, self.c[hold_end]
            reason = "TIME" if hold_end == first_j + p.max_hold - 1 else "END"
        return dict(signal_i=s, entry_i=e, exit_i=exit_i, entry=entry, exit=exit_px, sl=sl, tp=tp,
                    sl_dist=sl_dist, reason=reason, ambiguous=ambiguous, at_close=at_close,
                    mfe_r=(hi - entry) / sl_dist, mae_r=(entry - lo) / sl_dist)

    def _h1_trade(self, s, p, last_idx):
        """Entry on day s+1 only after a 1H confirmation; exits managed on 1H bars."""
        h1 = self.h1
        e = s + 1
        k = h1_entry(h1, self.h1_day_rows, self.dates[e])
        if k is None or k >= len(h1):
            return None
        o, hh, ll, cc = (h1[col].to_numpy() for col in ("open", "high", "low", "close"))
        tdate = h1["trade_date"].to_numpy()
        spread = self.costs.spread_pips * PIP
        entry = o[k] + spread
        sl_dist = self.atr[s] * p.atr_mult
        sl, tp = entry - sl_dist, entry + sl_dist * p.rr
        hold_end = min(e + p.max_hold - 1, last_idx)
        last_date = pd.Timestamp(self.dates[hold_end])
        exit_k = exit_px = reason = None
        hi = lo = entry
        r = k
        while r < len(h1) and pd.Timestamp(tdate[r]) <= last_date:
            if r > k and o[r] <= sl:
                exit_k, exit_px, reason = r, o[r], "STOP (GAP)"
                lo = min(lo, o[r])
                break
            if r > k and o[r] >= tp:
                exit_k, exit_px, reason = r, o[r], "TARGET (GAP)"
                hi = max(hi, o[r])
                break
            if ll[r] <= sl:
                exit_k, exit_px, reason = r, sl, "STOP"
                lo = min(lo, sl)
                break
            if hh[r] >= tp:
                exit_k, exit_px, reason = r, tp, "TARGET"
                hi = max(hi, tp)
                break
            hi, lo = max(hi, hh[r]), min(lo, ll[r])
            r += 1
        if exit_k is None:
            exit_k = r - 1
            exit_px = cc[exit_k]
            reason = "TIME" if hold_end == e + p.max_hold - 1 else "END"
        exit_i = self.date_pos.get(pd.Timestamp(tdate[exit_k]), hold_end)
        return dict(signal_i=s, entry_i=e, exit_i=exit_i, entry=entry, exit=exit_px, sl=sl, tp=tp,
                    sl_dist=sl_dist, reason=reason, ambiguous=False,
                    mfe_r=(hi - entry) / sl_dist, mae_r=(entry - lo) / sl_dist)

    def _costs(self, t):
        units = t["risk"] / t["sl_dist"]
        lots = units / 100_000
        nights = int((self.dates[t["exit_i"]] - self.dates[t["entry_i"]]) / np.timedelta64(1, "D"))
        gross = units * (t["exit"] - t["entry"])
        commission = self.costs.commission_per_lot * lots
        swap = self.costs.swap_per_lot_night * lots * nights
        return units, lots, nights, gross, commission, swap

    # ------------------------------------------------------------------
    # Account run
    # ------------------------------------------------------------------
    def run(self, schedule, start, end, halt_on_breach=False, halt_on_target=False):
        """Simulate the account from `start` to `end` (inclusive).

        schedule: a Params (fixed) or a callable date -> Params/None (walk-forward;
        None means stay flat). Params are looked up on the entry day, so a switch
        never touches an open trade.
        """
        acct = self.account
        first, last = self.index_range(start, end)
        if first is None:
            return pd.DataFrame(), pd.DataFrame()
        first = max(first, 1)
        fixed = schedule if isinstance(schedule, Params) else None
        balance = acct.initial
        trades, days = [], []
        pos = None
        max_loss_floor = acct.initial * (1 - acct.max_loss_pct)
        stop_reason = None
        for i in range(first, last + 1):
            day_start = balance
            if pos is None and i <= last:
                p = fixed or schedule(pd.Timestamp(self.dates[i]))
                s = i - 1
                if p is not None and self.signal(p)[s]:
                    trade = (self._h1_trade if p.entry == "h1" else self._daily_trade)(s, p, last)
                    if trade is not None and trade["entry_i"] == i:
                        throttled = acct.throttle_below and balance < acct.throttle_below
                        trade["risk"] = acct.risk_usd * (acct.throttle_factor if throttled else 1.0)
                        trade["params"] = p
                        pos = trade
            eq_close = eq_low = balance
            if pos is not None:
                units = pos["risk"] / pos["sl_dist"]
                if i == pos["exit_i"]:
                    units, lots, nights, gross, comm, swap = self._costs(pos)
                    net = gross - comm + swap
                    worst = pos["exit"] if pos["reason"].startswith("STOP") else self.l[i]
                    eq_low = balance + units * (worst - pos["entry"]) - comm + swap
                    balance += net
                    eq_close = balance
                    trades.append(self._record(pos, units, lots, nights, gross, comm, swap, net, balance))
                    pos = None
                else:
                    eq_close = balance + units * (self.c[i] - pos["entry"])
                    entered_at_close = pos.get("at_close") and i == pos["entry_i"]
                    eq_low = eq_close if entered_at_close else balance + units * (self.l[i] - pos["entry"])
            days.append((self.dates[i], balance, eq_close, min(eq_low, eq_close), day_start))
            if halt_on_breach and (eq_low <= max_loss_floor or
                                   day_start - eq_low >= acct.initial * acct.daily_loss_pct):
                stop_reason = "BREACH"
                break
            if halt_on_target and pos is None and balance >= acct.initial * (1 + acct.target_pct):
                stop_reason = "TARGET"
                break
        eq = pd.DataFrame(days, columns=["date", "balance", "equity_close", "equity_low", "day_start"])
        eq.attrs["stop_reason"] = stop_reason
        return pd.DataFrame(trades), eq

    def _record(self, t, units, lots, nights, gross, comm, swap, net, balance):
        p = t["params"]
        return {
            "signal_date": pd.Timestamp(self.dates[t["signal_i"]]).date(),
            "entry_date": pd.Timestamp(self.dates[t["entry_i"]]).date(),
            "exit_date": pd.Timestamp(self.dates[t["exit_i"]]).date(),
            "days_held": t["exit_i"] - t["entry_i"] + 1,
            "type": "BUY",
            "setup": p.label(),
            "risk_usd": round(t["risk"], 2),
            "lots": round(lots, 2),
            "entry_price": round(t["entry"], 5),
            "stop_loss": round(t["sl"], 5),
            "take_profit": round(t["tp"], 5),
            "exit_price": round(t["exit"], 5),
            "exit_reason": t["reason"],
            "stop_pips": round(t["sl_dist"] / PIP, 1),
            "pips": round((t["exit"] - t["entry"]) / PIP, 1),
            "r_gross": round((t["exit"] - t["entry"]) / t["sl_dist"], 3),
            "mfe_r": round(t["mfe_r"], 3),
            "mae_r": round(t["mae_r"], 3),
            "same_bar_sl_tp": t["ambiguous"],
            "gross_pnl": round(gross, 2),
            "commission": round(comm, 2),
            "swap": round(swap, 2),
            "net_pnl": round(net, 2),
            "r_net": round(net / t["risk"], 3),
            "balance": round(balance, 2),
        }
