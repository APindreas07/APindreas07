"""Pre-registered edge tests E1-E6 (see edge/PREREGISTRATION.md).

Everything here is deterministic: real TradeStation bars in, statistics out.
No random numbers, no resampling, no parameter search beyond the neighbour
grids fixed in the pre-registration.

Run:  python -m edge.research
Writes edge/results/*.csv, edge/results/equity.png and prints a summary.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "tradestation"
OUT = Path(__file__).resolve().parent / "results"

HOLDOUT_START = pd.Timestamp("2024-01-01")
POST_END = pd.Timestamp("2023-12-31")

COST_SPY = 0.0002          # per side, SPY/QQQ daily strategies
COST_MONTHLY_ETF = 0.0005  # per side, monthly strategies (also used for SPY/QQQ there: the stricter figure)
FX_PIPS_ROUND_TURN = 1.5
CFD_FINANCING = 0.03       # per year on held notional, sensitivity only

ETFS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV", "USO", "DBC"]
FX = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]


# ---------------------------------------------------------------- data

def load_daily(sym: str) -> pd.DataFrame:
    d = pd.read_csv(DATA / f"{sym}_daily.csv", parse_dates=["date"]).set_index("date")
    return d.sort_index()


def month_end_closes(sym: str) -> pd.Series:
    """Month-end close indexed by monthly Period.

    SPY: monthly file (1993-04..2001-12) spliced with daily month-ends from
    2000-01 on (the two agree on the overlap; checked in splice_check()).
    QQQ: daily month-ends. Everything else: the monthly bars.
    """
    if sym in ("SPY", "QQQ"):
        d = load_daily(sym)["close"]
        me = d.groupby(d.index.to_period("M")).last()
        if sym == "SPY":
            m = pd.read_csv(DATA / "SPY_monthly.csv", parse_dates=["date"])
            m = m.set_index(m["date"].dt.to_period("M"))["close"]
            first_full = me.index[1]  # daily data start mid-Nov 1999 -> Nov is partial
            me = pd.concat([m[m.index < first_full], me[me.index >= first_full]])
        return me.sort_index()
    m = pd.read_csv(DATA / f"{sym}_monthly.csv", parse_dates=["date"])
    return m.set_index(m["date"].dt.to_period("M"))["close"].sort_index()


def splice_check() -> float:
    d = load_daily("SPY")["close"]
    me = d.groupby(d.index.to_period("M")).last()
    m = pd.read_csv(DATA / "SPY_monthly.csv", parse_dates=["date"])
    m = m.set_index(m["date"].dt.to_period("M"))["close"]
    common = me.index[1:].intersection(m.index)
    return float((me[common] / m[common] - 1).abs().max())


# ---------------------------------------------------------------- stats

def tstat(x) -> float:
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    if len(x) < 2 or x.std(ddof=1) == 0:
        return float("nan")
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(len(x))))


def compound(x) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.prod(1 + x) - 1) if len(x) else 0.0


def block_of(ts: pd.Timestamp, pre_end_year: int) -> str:
    if ts >= HOLDOUT_START:
        return "holdout"
    if ts.year <= pre_end_year:
        return "pre"
    return "post"


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


@dataclass
class Result:
    name: str
    market: str
    rule: str
    blocks: dict = field(default_factory=dict)      # block -> dict(net, n, ...)
    full_net: float = float("nan")
    t_edge: float = float("nan")
    extra: dict = field(default_factory=dict)
    neighbours: dict = field(default_factory=dict)  # label -> full-sample net
    confirm: dict | None = None
    equity: pd.Series | None = None

    def checks(self, need_confirm: bool) -> dict:
        c = {
            "every_block_positive": all(b["net"] > 0 for b in self.blocks.values()),
            "t_ge_2": bool(self.t_edge >= 2.0),
        }
        if self.neighbours:
            c["all_neighbours_positive"] = all(v > 0 for v in self.neighbours.values())
        if need_confirm:
            c["qqq_confirms"] = bool(self.confirm and self.confirm["net"] > 0 and self.confirm["t"] >= 1.5)
        c["PASS"] = all(c.values())
        return c


# ---------------------------------------------------------------- E1

def rsi_wilder(close: pd.Series, n: int) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn
    return 100 - 100 / (1 + rs)


def e1_trades(d: pd.DataFrame, rsi_th=10, exit_sma=5, cost=COST_SPY):
    """Long when close>SMA200 and RSI(2)<th; exit when close>SMA(exit_sma).
    Signals on the close, fills at the next open."""
    c, o = d["close"].to_numpy(), d["open"].to_numpy()
    sma200 = d["close"].rolling(200).mean().to_numpy()
    smax = d["close"].rolling(exit_sma).mean().to_numpy()
    rsi = rsi_wilder(d["close"], 2).to_numpy()
    n = len(d)
    pos = np.zeros(n)  # 1 if long over the open(t)->open(t+1) interval
    trades = []
    i, entry = 0, None
    while i < n - 1:
        if entry is None:
            if not np.isnan(sma200[i]) and c[i] > sma200[i] and rsi[i] < rsi_th:
                entry = i + 1
        else:
            if c[i] > smax[i]:
                trades.append((entry, i + 1, o[i + 1]))
                entry = None
        i += 1
    if entry is not None:  # still open at the end: mark at last close
        trades.append((entry, n - 1, c[n - 1]))
    rows = []
    for a, b, exit_px in trades:
        pos[a:b] = 1
        g = exit_px / o[a] - 1
        rows.append({"entry": d.index[a], "exit": d.index[b], "days": b - a,
                     "gross": g, "net": g - 2 * cost})
    oo = pd.Series(o, index=d.index).shift(-1) / pd.Series(o, index=d.index) - 1
    return pd.DataFrame(rows), pos, oo


def e1_summary(d, rsi_th=10, exit_sma=5, cost=COST_SPY):
    tr, pos, oo = e1_trades(d, rsi_th, exit_sma, cost)
    inpos = oo[pos == 1].dropna()
    edge = inpos - oo.dropna().mean()
    return tr, float(tr["net"].pipe(compound)), tstat(edge), inpos


def run_e1(spy, qqq) -> Result:
    tr, net, t, inpos = e1_summary(spy)
    r = Result("E1", "SPY daily", "RSI(2)<10 & close>SMA200, exit close>SMA5, next-open fills")
    tr["block"] = [block_of(x, 2008) for x in tr["entry"]]
    for b in ("pre", "post", "holdout"):
        sub = tr[tr["block"] == b]
        r.blocks[b] = {"net": compound(sub["net"]), "n": len(sub),
                       "win": float((sub["net"] > 0).mean()) if len(sub) else float("nan"),
                       "avg": float(sub["net"].mean()) if len(sub) else float("nan")}
    r.full_net, r.t_edge = net, t
    r.extra = {"trades": len(tr), "days_in_market_pct": len(inpos) / len(spy),
               "avg_trade_net": float(tr["net"].mean()), "win_rate": float((tr["net"] > 0).mean())}
    for th in (5, 10, 15, 20, 25):
        for xs in (3, 5, 10):
            r.neighbours[f"RSI<{th}/SMA{xs}"] = e1_summary(spy, th, xs)[1]
    qtr, qnet, qt, _ = e1_summary(qqq)
    r.confirm = {"net": qnet, "t": qt, "n": len(qtr)}
    r.equity = trade_equity(tr, spy.index)
    tr.to_csv(OUT / "E1_trades_SPY.csv", index=False)
    return r


def trade_equity(tr: pd.DataFrame, idx) -> pd.Series:
    eq = pd.Series(np.nan, index=idx)
    v = 1.0
    eq.iloc[0] = v
    for _, row in tr.iterrows():
        v *= 1 + row["net"]
        eq[row["exit"]] = v
    return eq.ffill()


# ---------------------------------------------------------------- E2

def e2_trades(d: pd.DataFrame, entry_k=-2, exit_k=3, cost=COST_SPY):
    """entry_k: -1 = last trading day of month, -2 = second-to-last ...
    exit_k: 1 = first trading day of next month ... Positions are close->close."""
    per = d.index.to_period("M")
    months = pd.Series(np.arange(len(d)), index=d.index).groupby(per)
    idx_by_month = {m: g.to_numpy() for m, g in months}
    ms = sorted(idx_by_month)
    c = d["close"].to_numpy()
    rows = []
    for m, nxt in zip(ms[1:-1], ms[2:]):  # skip first month (partial)
        cur, nx = idx_by_month[m], idx_by_month[nxt]
        if len(nx) < exit_k or len(cur) < -entry_k:
            continue
        a, b = cur[entry_k], nx[exit_k - 1]
        g = c[b] / c[a] - 1
        rows.append({"entry": d.index[a], "exit": d.index[b], "a": a, "b": b,
                     "gross": g, "net": g - 2 * cost})
    tr = pd.DataFrame(rows)
    cc = d["close"].pct_change()
    pos = np.zeros(len(d))
    for a, b in zip(tr["a"], tr["b"]):
        pos[a + 1:b + 1] = 1
    return tr, pos, cc


def e2_summary(d, entry_k=-2, exit_k=3):
    tr, pos, cc = e2_trades(d, entry_k, exit_k)
    inpos = cc[pos == 1].dropna()
    return tr, compound(tr["net"]), tstat(inpos - cc.dropna().mean()), inpos


def run_e2(spy, qqq) -> Result:
    tr, net, t, inpos = e2_summary(spy)
    r = Result("E2", "SPY daily", "long close of day -2 to close of day +3")
    tr["block"] = [block_of(x, 2008) for x in tr["entry"]]
    for b in ("pre", "post", "holdout"):
        sub = tr[tr["block"] == b]
        r.blocks[b] = {"net": compound(sub["net"]), "n": len(sub),
                       "win": float((sub["net"] > 0).mean()), "avg": float(sub["net"].mean())}
    r.full_net, r.t_edge = net, t
    r.extra = {"trades": len(tr), "days_in_market_pct": len(inpos) / len(spy),
               "avg_trade_net": float(tr["net"].mean()), "win_rate": float((tr["net"] > 0).mean())}
    for ek in (-3, -2, -1):
        for xk in (2, 3, 4):
            r.neighbours[f"entry{ek}/exit+{xk}"] = e2_summary(spy, ek, xk)[1]
    qtr, qnet, qt, _ = e2_summary(qqq)
    r.confirm = {"net": qnet, "t": qt, "n": len(qtr)}
    r.equity = trade_equity(tr, spy.index)
    tr.drop(columns=["a", "b"]).to_csv(OUT / "E2_trades_SPY.csv", index=False)
    return r


# ---------------------------------------------------------------- E3

def e3_series(d, cost=COST_SPY):
    on = (d["open"] / d["close"].shift(1) - 1).dropna()
    cc = d["close"].pct_change().dropna()
    return on, on - 2 * cost, cc


def run_e3(spy, qqq) -> Result:
    on, net, cc = e3_series(spy)
    r = Result("E3", "SPY daily", "long close->next open every day")
    blk = pd.Series([block_of(x, 2008) for x in net.index], index=net.index)
    for b in ("pre", "post", "holdout"):
        r.blocks[b] = {"net": compound(net[blk == b]), "n": int((blk == b).sum()),
                       "gross": compound(on[blk == b])}
    r.full_net = compound(net)
    r.t_edge = tstat(on - cc.mean())
    r.extra = {"mean_overnight_gross_bp": on.mean() * 1e4, "mean_close_close_bp": cc.mean() * 1e4,
               "cost_per_day_bp": 2 * COST_SPY * 1e4, "t_gross_overnight_vs_zero": tstat(on)}
    qon, qnet, qcc = e3_series(qqq)
    r.confirm = {"net": compound(qnet), "t": tstat(qon - qcc.mean()), "n": len(qnet)}
    r.equity = (1 + net).cumprod().reindex(spy.index).ffill().fillna(1.0)
    return r


# ---------------------------------------------------------------- monthly

def monthly_block(p: pd.Period, pre_end_year: int) -> str:
    return block_of(p.to_timestamp(how="end"), pre_end_year)


def run_e4() -> Result:
    px = month_end_closes("SPY")
    sma10 = px.rolling(10).mean()
    sig = (px > sma10).astype(float)          # decided at month-end t, held over t+1
    ret = px.pct_change().shift(-1)           # return over month t+1, aligned to t
    pos = sig.where(sma10.notna())
    trades = pos.diff().abs().fillna(0)
    net = (pos * ret - trades * COST_MONTHLY_ETF).dropna()
    net.index = net.index + 1                 # label by the month the return is earned
    bh = px.pct_change().reindex(net.index)
    r = Result("E4", "SPY monthly", "long if month-end close > 10-month SMA else cash (0%)")
    blk = pd.Series([monthly_block(p, 2007) for p in net.index], index=net.index)
    for b in ("pre", "post", "holdout"):
        r.blocks[b] = {"net": compound(net[blk == b]), "n": int((blk == b).sum()),
                       "buy_hold": compound(bh[blk == b])}
    r.full_net, r.t_edge = compound(net), tstat(net)
    eq = (1 + net).cumprod()
    beq = (1 + bh).cumprod()
    r.extra = {"months": len(net), "switches": int(trades.sum()),
               "t_vs_buy_hold": tstat(net - bh), "maxdd": max_drawdown(eq), "maxdd_buy_hold": max_drawdown(beq),
               "buy_hold_full": compound(bh), "pct_months_invested": float(pos.reindex(net.index - 1).mean())}
    r.equity = eq
    return r


def fx_cost_frac(sym: str, price: pd.Series) -> pd.Series:
    pip = 0.01 if sym.endswith("JPY") else 0.0001
    return (FX_PIPS_ROUND_TURN / 2) * pip / price  # per side


def tsmom(universe, lookback=12, vol_target=0.10, min_markets=5, financing=0.0):
    px = pd.DataFrame({s: month_end_closes(s) for s in universe}).sort_index()
    rets = px.pct_change()
    lb = px / px.shift(lookback) - 1
    vol = rets.rolling(12).std() * np.sqrt(12)
    w = np.sign(lb) * (vol_target / vol)
    w = w.where(lb.notna() & vol.notna() & (vol > 0))
    nmk = w.notna().sum(axis=1)
    w = w.div(nmk, axis=0)                    # equal risk across the markets live that month
    w = w.where(nmk >= min_markets)
    fwd = rets.shift(-1)
    gross = (w * fwd).sum(axis=1, min_count=1)
    percost = pd.DataFrame({s: (fx_cost_frac(s, px[s]) if s in FX else pd.Series(COST_MONTHLY_ETF, index=px.index))
                            for s in universe})
    turnover = w.fillna(0).diff().abs()
    turnover.iloc[0] = w.fillna(0).iloc[0].abs()
    costs = (turnover * percost).sum(axis=1)
    fin = w.abs().sum(axis=1) * financing / 12
    net = (gross - costs - fin).where(w.notna().any(axis=1))
    # the last month-end has no forward return
    net = net.iloc[:-1].dropna()
    net.index = net.index + 1
    info = {"gross_exposure_avg": float(w.abs().sum(axis=1).loc[w.notna().any(axis=1)].mean()),
            "markets_avg": float(nmk[nmk >= min_markets].mean()),
            "cost_drag_ann": float(costs.loc[w.notna().any(axis=1)].mean() * 12)}
    return net, w, info


def run_tsmom(name, universe, label) -> Result:
    net, w, info = tsmom(universe)
    r = Result(name, label, "sign of 12m return, 10% vol target per market (12m of monthly returns), equal risk")
    blk = pd.Series([monthly_block(p, 2012) for p in net.index], index=net.index)
    for b in ("pre", "post", "holdout"):
        r.blocks[b] = {"net": compound(net[blk == b]), "n": int((blk == b).sum()),
                       "ann_ret": float(net[blk == b].mean() * 12), "ann_vol": float(net[blk == b].std() * np.sqrt(12))}
    r.full_net, r.t_edge = compound(net), tstat(net)
    eq = (1 + net).cumprod()
    fnet, _, _ = tsmom(universe, financing=CFD_FINANCING)
    r.extra = {**info, "start": str(net.index[0]), "end": str(net.index[-1]), "months": len(net),
               "ann_ret": float(net.mean() * 12), "ann_vol": float(net.std() * np.sqrt(12)),
               "sharpe_ann": float(net.mean() / net.std() * np.sqrt(12)), "maxdd": max_drawdown(eq),
               "with_3pct_cfd_financing_full_net": compound(fnet), "t_with_financing": tstat(fnet)}
    for lb in (3, 6, 12):
        r.neighbours[f"lookback{lb}"] = compound(tsmom(universe, lookback=lb)[0])
    r.equity = eq
    net.to_frame("net").to_csv(OUT / f"{name}_monthly_returns.csv")
    w.to_csv(OUT / f"{name}_weights.csv")
    return r


# ---------------------------------------------------------------- report

def fmt_pct(x):
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x * 100:+.1f}%"


def plot(results, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(13, 11))
    for ax, r in zip(axes.flat, results):
        eq = r.equity.copy()
        if isinstance(eq.index, pd.PeriodIndex):
            eq.index = eq.index.to_timestamp(how="end")
        ax.plot(eq.index, eq.values, lw=1.2)
        ax.set_yscale("log")
        ax.axvline(HOLDOUT_START, color="k", ls="--", lw=0.8)
        verdict = "PASS" if r.checks(r.name in ("E1", "E2", "E3"))["PASS"] else "FAIL"
        ax.set_title(f"{r.name} {r.market} - {verdict} (net of costs)", fontsize=10)
        ax.grid(alpha=0.3)
    fig.suptitle("Pre-registered edge tests on TradeStation data (dashed line = start of untouched holdout, 2024-01-01)")
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    OUT.mkdir(exist_ok=True)
    spy, qqq = load_daily("SPY"), load_daily("QQQ")
    results = [run_e1(spy, qqq), run_e2(spy, qqq), run_e3(spy, qqq), run_e4(),
               run_tsmom("E5", ETFS + FX, "18 markets monthly"), run_tsmom("E6", FX, "7 FX majors monthly")]
    summary = {"spy_splice_max_abs_diff": splice_check()}
    for r in results:
        chk = r.checks(r.name in ("E1", "E2", "E3"))
        summary[r.name] = {"market": r.market, "rule": r.rule, "blocks": r.blocks, "full_net": r.full_net,
                           "t_edge": r.t_edge, "neighbours": r.neighbours, "confirm": r.confirm,
                           "extra": r.extra, "checks": chk}
        print(f"\n== {r.name} {r.market}: {r.rule}")
        for b, v in r.blocks.items():
            print(f"   {b:8s} net {fmt_pct(v['net']):>9s}  n={v['n']}")
        print(f"   full net {fmt_pct(r.full_net)}  t_edge {r.t_edge:.2f}")
        if r.neighbours:
            neg = [k for k, v in r.neighbours.items() if v <= 0]
            print(f"   neighbours: {len(r.neighbours) - len(neg)}/{len(r.neighbours)} positive {neg}")
        if r.confirm:
            print(f"   QQQ: net {fmt_pct(r.confirm['net'])} t {r.confirm['t']:.2f}")
        print(f"   extra: { {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.extra.items()} }")
        print(f"   checks: {chk}")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    plot(results, OUT / "equity.png")
    return results


if __name__ == "__main__":
    main()
