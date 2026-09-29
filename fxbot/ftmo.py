"""FTMO 2-Step ($10,000) rules, compounding position sizing and lifecycle simulation.

Rules modelled (FTMO 2-Step Challenge; see results/ftmo_study/REPORT.md for sources):
    Phase 1 (Challenge)     profit target 10% ($1,000), min 4 trading days, no time limit
    Phase 2 (Verification)  profit target 5% ($500),    min 4 trading days, no time limit
    Funded (FTMO Account)   no target; payouts optional (here: no withdrawals for 12 months)
    All phases              Max Loss 10%: equity (incl. open trades) may never touch $9,000
                            (static: it does not move up as the account grows)
                            Max Daily Loss 5% ($500): equity may not fall $500 below the
                            higher of balance and equity at the start of the day
    Account type            Swing (positions held overnight and over weekends are allowed;
                            forex leverage 1:30)
    Costs                   $5 per lot round-turn commission, spread, overnight swap

Daily bars here roll at 17:00 New York, FTMO's day at 00:00 Prague (one hour apart);
the daily-loss check uses each bar's worst price, which is stricter than reality.

Position sizing (compounding, rule-aware):
    risk per trade = risk_pct x current balance, but never more than
      * the distance to the $9,000 floor minus a buffer, and
      * what is left of today's $500 daily-loss budget minus a buffer,
    so a normal stop-out can never breach a rule; only a price gap through the
    stop can. Lot size is also capped by the 1:30 Swing leverage.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .systems import PIP, orders


@dataclass(frozen=True)
class FTMORules:
    initial: float = 10_000.0
    phase1_target: float = 0.10
    phase2_target: float = 0.05
    max_loss_pct: float = 0.10
    daily_loss_pct: float = 0.05
    min_trading_days: int = 4
    leverage: float = 30.0            # Swing account, forex
    commission_per_lot: float = 5.0   # USD round turn ($2.50 per side)
    spread_pips: float = 1.0          # EURUSD raw spread + slippage allowance
    swap_long: float = -6.0           # USD per lot per night (assumption; check your terminal)
    swap_short: float = 0.0           # conservative: usually slightly positive on EURUSD
    risk_usd: float = 100.0           # only used by legacy metric helpers


@dataclass(frozen=True)
class Sizing:
    risk_pct: float = 0.01
    floor_buffer_pct: float = 0.01    # keep 1% of the account between a stop-out and $9,000
    daily_buffer_pct: float = 0.01    # and 1% inside the $500 daily limit
    min_risk_pct: float = 0.001       # skip trades if the allowed risk is below this
    daily_guard: bool = True          # equity protector: close the trade before the daily limit


class FTMOSim:
    def __init__(self, feat, rules=FTMORules(), bar_model="path"):
        """bar_model: 'path' assumes open->low->high->close on up days and
        open->high->low->close on down days; 'worst' assumes the adverse extreme
        always comes first (the most pessimistic reading of a daily bar)."""
        self.f = feat.reset_index(drop=True)
        self.r = rules
        self.bar_model = bar_model
        self.dates = self.f["date"].to_numpy()
        self.o, self.h, self.l, self.c = (self.f[k].to_numpy() for k in ("open", "high", "low", "close"))
        self.atr = self.f["atr14"].to_numpy()
        self._orders = {}
        self._chan = {}

    def orders(self, sysm):
        if sysm not in self._orders:
            self._orders[sysm] = orders(self.f, sysm)
        return self._orders[sysm]

    def channel(self, n):
        if n not in self._chan:
            self._chan[n] = (self.f["low"].rolling(n).min().to_numpy(), self.f["high"].rolling(n).max().to_numpy())
        return self._chan[n]

    def idx(self, start, end):
        d = self.f["date"]
        ix = np.flatnonzero((d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end)))
        return (int(ix[0]), int(ix[-1])) if len(ix) else (None, None)

    # ------------------------------------------------------------------
    def trade(self, s, sysm, last):
        """Order decided at close s, executed on s+1. Returns trade dict or None."""
        od = self.orders(sysm)
        e = s + 1
        if e > last:
            return None
        sp = self.r.spread_pips * PIP
        if od["kind"] == "market":
            d = int(od["dir"][s])
            if d == 0:
                return None
            fill = self.o[e] + (sp if d > 0 else 0.0)
            at_open = True
        else:
            L, S = od["long_lvl"][s], od["short_lvl"][s]
            hit_l = not np.isnan(L) and self.h[e] >= L
            hit_s = not np.isnan(S) and self.l[e] <= S
            if hit_l and hit_s:
                return None                      # both sides triggered: order unknowable on daily bars
            if hit_l:
                d, fill = 1, max(self.o[e], L) + sp
            elif hit_s:
                d, fill = -1, min(self.o[e], S)
            else:
                return None
            at_open = False
        sl_dist = self.atr[s] * sysm.sl_mult
        if not sl_dist > 0:
            return None
        stop = fill - d * sl_dist
        init_stop = stop
        tp = fill + d * sysm.rr * sl_dist if sysm.rr else None
        lo_ch, hi_ch = self.channel(sysm.trail_n) if sysm.trail_n else (None, None)
        sig = od["signal"]
        hold_end = min(e + sysm.max_hold - 1, last)
        exit_i = exit_px = reason = None
        best = worst = fill
        for j in range(e, hold_end + 1):
            adj = 0.0 if d > 0 else sp          # shorts exit at the Ask
            o_, h_, l_, c_ = self.o[j] + adj, self.h[j] + adj, self.l[j] + adj, self.c[j] + adj
            if j > e:
                if sysm.flip_exit and sig[j - 1] != d:
                    exit_i, exit_px, reason = j, o_, "SIGNAL FLIP"
                    break
                if (d > 0 and o_ <= stop) or (d < 0 and o_ >= stop):
                    exit_i, exit_px, reason = j, o_, "STOP (GAP)"
                    break
                if tp is not None and ((d > 0 and o_ >= tp) or (d < 0 and o_ <= tp)):
                    exit_i, exit_px, reason = j, o_, "TARGET (GAP)"
                    break
            pts = self._after_entry(j, e, at_open, d, fill - (sp if d > 0 else 0.0), o_, h_, l_, c_)
            hit = None
            for px in pts:
                if (d > 0 and px <= stop) or (d < 0 and px >= stop):
                    hit = "STOP"
                    break
                if tp is not None and ((d > 0 and px >= tp) or (d < 0 and px <= tp)):
                    hit = "TARGET"
                    break
            adverse, favour = (l_, h_) if d > 0 else (h_, l_)
            if hit == "STOP":
                exit_i, exit_px = j, stop
                reason = "STOP" if stop == init_stop else "TRAIL"
                break
            if hit == "TARGET":
                exit_i, exit_px, reason = j, tp, "TARGET"
                best = tp
                break
            best = max(best, favour) if d > 0 else min(best, favour)
            worst = min(worst, adverse) if d > 0 else max(worst, adverse)
            if sysm.trail_n and not np.isnan(lo_ch[j]):
                stop = max(stop, lo_ch[j] - PIP) if d > 0 else min(stop, hi_ch[j] + sp + PIP)
        if exit_i is None:
            exit_i = hold_end
            exit_px = self.c[hold_end] + (0.0 if d > 0 else sp)
            reason = "TIME" if hold_end == e + sysm.max_hold - 1 else "END"
        return dict(s=s, e=e, x=exit_i, d=d, entry=fill, exit=exit_px, sl_dist=sl_dist,
                    reason=reason, at_open=at_open,
                    mfe_r=d * (best - fill) / sl_dist, mae_r=-d * (worst - fill) / sl_dist)

    def _after_entry(self, j, e, at_open, d, trigger, o_, h_, l_, c_):
        """Price points visited on bar j after the position exists, in order."""
        adverse, favour = (l_, h_) if d > 0 else (h_, l_)
        if self.bar_model == "worst":
            return [adverse, favour, c_]
        path = [o_, l_, h_, c_] if self.c[j] >= self.o[j] else [o_, h_, l_, c_]
        if j > e or at_open:
            return path[1:]
        # stop entry on bar e: find where the path first reaches the trigger
        if (d > 0 and o_ >= trigger) or (d < 0 and o_ <= trigger):
            return path[1:]
        for k in range(3):
            if (d > 0 and path[k + 1] >= trigger) or (d < 0 and path[k + 1] <= trigger):
                return path[k + 1:]
        return path[1:]

    # ------------------------------------------------------------------
    def run(self, sysm, sizing, start, end, target=None, stop_on_breach=True, initial=None):
        """Simulate one account. Returns (trades, equity, outcome)."""
        r = self.r
        init = initial or r.initial
        first, last = self.idx(start, end)
        if first is None:
            return pd.DataFrame(), pd.DataFrame(), {"result": "NO DATA"}
        first = max(first, 1)
        floor = r.initial * (1 - r.max_loss_pct)          # static, from the phase's starting size
        daily_lim = r.initial * r.daily_loss_pct
        balance, prev_eq = init, init
        pos = None
        trades, days = [], []
        trading_days = 0
        outcome = {"result": "OPEN"}
        target_bal = init * (1 + target) if target else None
        target_hit = False
        extra_days_needed = 0
        sp = r.spread_pips * PIP
        for i in range(first, last + 1):
            day_ref = max(balance, prev_eq)
            if pos is None and not target_hit:
                t = self.trade(i - 1, sysm, last)
                if t is not None:
                    risk = sizing.risk_pct * balance
                    risk = min(risk, balance - floor - sizing.floor_buffer_pct * r.initial,
                               daily_lim - (day_ref - balance) - sizing.daily_buffer_pct * r.initial)
                    units = risk / t["sl_dist"] if risk >= sizing.min_risk_pct * r.initial else 0.0
                    units = min(units, r.leverage * balance / t["entry"])
                    lots = np.floor(units / 1000) / 100          # broker lot step 0.01
                    if lots > 0:
                        t["lots"], t["units"], t["risk"] = lots, lots * 100_000, lots * 100_000 * t["sl_dist"]
                        pos = t
                        trading_days += 1
            eq_close = eq_low = balance
            if pos is not None:
                d, u, ent = pos["d"], pos["units"], pos["entry"]
                adj = 0.0 if d > 0 else sp
                adverse = (self.l[i] if d > 0 else self.h[i] + adj)
                if sizing.daily_guard and i >= pos["e"]:
                    # FTMO counts floating profit given back: exit where today's loss would
                    # reach the daily limit minus the buffer (an "equity protector").
                    allowed = daily_lim - sizing.daily_buffer_pct * r.initial - (day_ref - balance)
                    guard = ent + d * (day_ref - allowed - balance) / u
                    if (d > 0 and adverse <= guard) or (d < 0 and adverse >= guard):
                        planned = pos["exit"] if i == pos["x"] else None
                        stop_first = (planned is not None and pos["reason"].startswith(("STOP", "TRAIL"))
                                      and ((d > 0 and planned >= guard) or (d < 0 and planned <= guard)))
                        if not stop_first:
                            o_ = self.o[i] + adj
                            gapped = i > pos["e"] and ((d > 0 and o_ <= guard) or (d < 0 and o_ >= guard))
                            pos.update(x=i, exit=o_ if gapped else guard, reason="DAILY GUARD")
                if i == pos["x"]:
                    nights = int((self.dates[i] - self.dates[pos["e"]]) / np.timedelta64(1, "D"))
                    comm = r.commission_per_lot * pos["lots"]
                    swap = (r.swap_long if d > 0 else r.swap_short) * pos["lots"] * nights
                    gross = u * d * (pos["exit"] - ent)
                    worst_px = pos["exit"] if pos["reason"].startswith(("STOP", "TRAIL", "DAILY")) else adverse
                    eq_low = balance + u * d * (worst_px - ent) - comm + swap
                    net = gross - comm + swap
                    balance += net
                    eq_close = balance
                    trades.append(self._record(pos, nights, gross, comm, swap, net, balance))
                    pos = None
                else:
                    eq_close = balance + u * d * (self.c[i] + adj - ent)
                    eq_low = balance + u * d * (adverse - ent)
                eq_low = min(eq_low, eq_close)
            days.append((self.dates[i], balance, eq_close, eq_low, day_ref))
            prev_eq = eq_close
            if eq_low <= floor or day_ref - eq_low >= daily_lim:
                outcome.setdefault("breach_date", str(pd.Timestamp(self.dates[i]).date()))
                outcome["breach_rule"] = "MAX LOSS" if eq_low <= floor else "DAILY LOSS"
                if stop_on_breach:
                    outcome["result"] = "FAIL"
                    break
            if target_bal and not target_hit and pos is None and balance >= target_bal:
                target_hit = True
                extra_days_needed = max(0, r.min_trading_days - trading_days)
            if target_hit:
                if extra_days_needed == 0:               # min trading days met (micro trades if needed)
                    outcome["result"] = "PASS"
                    break
                extra_days_needed -= 1
        eq = pd.DataFrame(days, columns=["date", "balance", "equity_close", "equity_low", "day_start"])
        if not eq.empty:
            outcome["end_date"] = pd.Timestamp(eq["date"].iloc[-1])
            outcome["days"] = (outcome["end_date"] - pd.Timestamp(eq["date"].iloc[0])).days
        outcome["trading_days"] = trading_days
        return pd.DataFrame(trades), eq, outcome

    def _record(self, t, nights, gross, comm, swap, net, balance):
        return {
            "signal_date": pd.Timestamp(self.dates[t["s"]]).date(),
            "entry_date": pd.Timestamp(self.dates[t["e"]]).date(),
            "exit_date": pd.Timestamp(self.dates[t["x"]]).date(),
            "days_held": t["x"] - t["e"] + 1,
            "type": "BUY" if t["d"] > 0 else "SELL",
            "lots": t["lots"],
            "risk_usd": round(t["risk"], 2),
            "entry_price": round(t["entry"], 5),
            "stop_pips": round(t["sl_dist"] / PIP, 1),
            "exit_price": round(t["exit"], 5),
            "exit_reason": t["reason"],
            "pips": round(t["d"] * (t["exit"] - t["entry"]) / PIP, 1),
            "r_gross": round(t["d"] * (t["exit"] - t["entry"]) / t["sl_dist"], 3),
            "mfe_r": round(t["mfe_r"], 3),
            "mae_r": round(t["mae_r"], 3),
            "gross_pnl": round(gross, 2),
            "commission": round(comm, 2),
            "swap": round(swap, 2),
            "net_pnl": round(net, 2),
            "r_net": round(net / t["risk"], 3),
            "balance": round(balance, 2),
        }

    # ------------------------------------------------------------------
    def lifecycle(self, sysm, sizing, start, funded_days=365):
        """Challenge -> Verification -> 12 months funded (no withdrawals), from `start`."""
        r = self.r
        end = self.dates[-1]
        out = {"start": pd.Timestamp(start).date()}
        _, _, p1 = self.run(sysm, sizing, start, end, target=r.phase1_target)
        out["phase1"], out["phase1_days"] = p1["result"], p1.get("days")
        if p1["result"] != "PASS":
            return out
        s2 = p1["end_date"] + pd.Timedelta(days=1)
        _, _, p2 = self.run(sysm, sizing, s2, end, target=r.phase2_target)
        out["phase2"], out["phase2_days"] = p2["result"], p2.get("days")
        if p2["result"] != "PASS":
            return out
        s3 = p2["end_date"] + pd.Timedelta(days=1)
        f_end = s3 + pd.Timedelta(days=funded_days)
        out["funded_start"] = s3.date()
        if f_end > pd.Timestamp(end):
            out["funded"] = "INCOMPLETE"
            return out
        tr, eq, fo = self.run(sysm, sizing, s3, f_end)
        out["funded"] = "BREACHED" if fo["result"] == "FAIL" else "SURVIVED"
        out["funded_final"] = eq["balance"].iloc[-1] if not eq.empty else np.nan
        out["funded_return_pct"] = (out["funded_final"] / r.initial - 1) * 100
        if not eq.empty and fo["result"] != "FAIL":
            m = monthly(eq)
            out["funded_avg_month_pct"] = ((1 + m / 100).prod() ** (1 / len(m)) - 1) * 100 if len(m) else np.nan
        out["days_to_funded"] = (s3 - pd.Timestamp(start)).days
        return out


def monthly(eq):
    s = eq.set_index(pd.to_datetime(eq["date"]))["equity_close"]
    me = s.resample("ME").last()
    prev = me.shift(1)
    prev.iloc[0] = s.iloc[0]
    return (me / prev - 1) * 100
