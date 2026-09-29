"""FX round 2: pre-registered hypotheses G1-G4 (see edge/fx2/PREREGISTRATION.md).

Real TradeStation daily bars (7 USD majors + SPY) in, statistics out. The 21 crosses are computed exactly from
the real USD legs (same 17:00 NY timestamp). Random numbers (seed 20260929) are used ONLY for the parameter
Monte Carlo (picking parameter sets) and the return Monte Carlo (block-resampling REAL realised returns).

Run:  python -m edge.fx2.research
"""
from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "tradestation"
OUT = Path(__file__).resolve().parent / "results"

MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]          # same order as MAJORS
CCY_SIGN = np.array([1, 1, -1, 1, -1, -1, 1], dtype=float)         # +1: XXXUSD, -1: USDXXX
SPREAD_PIPS = {"EURUSD": 1.0, "USDJPY": 1.2, "GBPUSD": 1.5, "AUDUSD": 1.3,
               "USDCAD": 1.8, "USDCHF": 1.8, "NZDUSD": 2.0}
EXTRA_PIPS = 0.5 + 0.4

LAST_DATE = pd.Timestamp("2026-09-25")
DEV = (pd.Timestamp("2008-01-01"), pd.Timestamp("2016-12-31"))
OOS = (pd.Timestamp("2017-01-01"), pd.Timestamp("2023-12-31"))
HOLD = (pd.Timestamp("2024-01-01"), LAST_DATE)
WF_YEARS = list(range(2017, 2027))
TRAIN_YEARS = 5
TARGET_VOL, VOL_WIN, ANN = 0.10, 60, 252
SEED = 20260929
N_PARAM_MC, N_BOOT, BLOCK = 10_000, 10_000, 20
SWAP_PER_YEAR = 0.02
MAX_STRAT_SCALE = 4.0
TARGET_ANNUAL = 1.02 ** 12 - 1                                      # 2% a month = 26.8% a year
MAX_DD_AT_TARGET, MIN_SHARPE_TARGET, DD_BUDGET = -0.30, 0.8, -0.20


# ---------------------------------------------------------------- data

def _load():
    frames = []
    for p in MAJORS:
        d = pd.read_csv(DATA / f"{p}_daily.csv", parse_dates=["date"]).set_index("date")
        frames.append(d[["open", "close"]].add_prefix(p + "_"))
    df = pd.concat(frames, axis=1, join="inner").sort_index()
    df = df[df.index <= LAST_DATE]
    O = df[[p + "_open" for p in MAJORS]].to_numpy(float)
    C = df[[p + "_close" for p in MAJORS]].to_numpy(float)
    spy = pd.read_csv(DATA / "SPY_daily.csv", parse_dates=["date"]).set_index("date")["close"]
    spy = spy.reindex(df.index.union(spy.index)).ffill().reindex(df.index).to_numpy(float)
    return df.index, O, C, spy


IDX, MO, MC_, SPY = _load()
T = len(IDX)
YEAR = IDX.year.to_numpy()
TI = np.arange(T)[:, None]
PIP = np.array([0.01 if "JPY" in p else 0.0001 for p in MAJORS])
RT = np.array([SPREAD_PIPS[p] + EXTRA_PIPS for p in MAJORS])
MAJ_COST = RT * PIP / 2.0 / MO                  # per unit |change in weight|, per day
# value of 1 unit of each currency in USD
VO = np.where(CCY_SIGN > 0, MO, 1.0 / MO)
VC = np.where(CCY_SIGN > 0, MC_, 1.0 / MC_)
CROSS = list(combinations(range(7), 2))          # (a, b): price of a in units of b
CROSS_NAMES = [CCYS[a] + CCYS[b] for a, b in CROSS]
XO = np.column_stack([VO[:, a] / VO[:, b] for a, b in CROSS])
XC = np.column_stack([VC[:, a] / VC[:, b] for a, b in CROSS])
X_COST = np.column_stack([MAJ_COST[:, a] + MAJ_COST[:, b] for a, b in CROSS])  # conservative: both legs


def mask(a, b):
    return (IDX >= a) & (IDX <= b)


M_DEV, M_OOS, M_HOLD = mask(*DEV), mask(*OOS), mask(*HOLD)


class Book:
    """Price arrays + precomputed return pieces for one instrument set."""

    def __init__(self, O, C, cost):
        self.O, self.C, self.cost = O, C, cost
        self.n = C.shape[1]
        self.gap = np.zeros_like(C)
        self.gap[1:] = O[1:] / C[:-1] - 1
        self.day = C / O - 1
        cc = np.zeros_like(C)
        cc[1:] = C[1:] / C[:-1] - 1
        sd = pd.DataFrame(cc).rolling(VOL_WIN).std().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            self.vs = np.nan_to_num(TARGET_VOL / (sd * np.sqrt(ANN)), nan=0.0, posinf=0.0)
        self.L = np.log(C)
        self.cs = np.vstack([np.zeros((1, self.n)), np.cumsum(self.L, axis=0)])
        self.cs2 = np.vstack([np.zeros((1, self.n)), np.cumsum(self.L ** 2, axis=0)])
        self.ccs = np.vstack([np.zeros((1, self.n)), np.cumsum(C, axis=0)])

    def sma_price(self, n):
        out = np.full_like(self.C, np.nan)
        out[n - 1:] = (self.ccs[n:] - self.ccs[:-n]) / n
        return out

    def zlog(self, n):
        s, s2 = self.cs[n:] - self.cs[:-n], self.cs2[n:] - self.cs2[:-n]
        m = s / n
        sd = np.sqrt(np.maximum((s2 - s * s / n) / (n - 1), 0))
        z = np.full_like(self.C, np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            z[n - 1:] = (self.L[n - 1:] - m) / sd
        return z

    def run(self, w):
        """Signal at close t -> filled at open t+1. Returns (equal-risk average daily net return, gross exposure)."""
        hg, hd = np.zeros_like(w), np.zeros_like(w)
        hg[2:], hd[1:] = w[:-2], w[:-1]
        r = hg * self.gap + hd * self.day - np.abs(hd - hg) * self.cost
        return r.mean(axis=1), np.abs(hd).sum(axis=1) / self.n


MAJ = Book(MO, MC_, MAJ_COST)
XB = Book(XO, XC, X_COST)


def state_machine(long_in, short_in, exit_long, exit_short):
    ent = long_in | short_in
    le = np.maximum.accumulate(np.where(ent, TI, -1), axis=0)
    d_last = np.take_along_axis(np.where(long_in, 1, -1), np.maximum(le, 0), axis=0)
    xl = np.maximum.accumulate(np.where(exit_long, TI, -1), axis=0)
    xs = np.maximum.accumulate(np.where(exit_short, TI, -1), axis=0)
    pos = np.where((le >= 0) & (d_last == 1) & (le > xl), 1.0, 0.0)
    return np.where((le >= 0) & (d_last == -1) & (le > xs), -1.0, pos)


def hold_every(w, rebal):
    return w[np.maximum.accumulate(np.where(rebal, np.arange(T), 0))]


# month-end bookkeeping for G3
_mo = IDX.to_period("M")
MONTH_END = np.r_[_mo[1:] != _mo[:-1], False]      # last trading day of each month (current month incomplete)
_pos_in_month = pd.Series(np.arange(T)).groupby(np.asarray(_mo)).transform(lambda s: s.max() - s).to_numpy()
DAYS_TO_ME = np.where(pd.Series(_mo).groupby(np.asarray(_mo)).transform("size").to_numpy() > 0, _pos_in_month, 0)
_prev_me_close = pd.Series(np.where(MONTH_END, SPY, np.nan)).shift(1).ffill().to_numpy()
SPY_MTD = SPY / _prev_me_close - 1
_last_month = _mo == _mo[-1]                          # the final (partial) month has no known month-end


def signal(h, p):
    if h == "G1":
        n, k = p
        z = XB.zlog(int(n))
        return state_machine(z < -k, z > k, z >= 0, z <= 0) * XB.vs
    if h == "G2":
        n, hd = int(p[0]), int(p[1])
        r = np.full_like(MC_, np.nan)
        r[n:] = MC_[n:] / MC_[:-n] - 1
        strength = r * CCY_SIGN
        ok = ~np.isnan(strength).any(axis=1)
        rank = np.argsort(np.argsort(np.nan_to_num(strength), axis=1), axis=1)   # 0 = weakest
        ccy = np.where(rank <= 1, 1.0, np.where(rank >= 5, -1.0, 0.0)) * ok[:, None]  # long weakest
        w = ccy * CCY_SIGN * MAJ.vs
        rebal = np.zeros(T, bool)
        rebal[int(np.argmax(ok))::hd] = True
        return hold_every(w, rebal)
    if h == "G3":
        d, x = int(p[0]), float(p[1])
        active = (DAYS_TO_ME >= 1) & (DAYS_TO_ME <= d) & ~_last_month
        # decided at close of day (month-end - d) and held while active; direction fixed from that day's SPY MTD
        start = (DAYS_TO_ME == d) & ~_last_month
        dir_at_start = np.where(SPY_MTD > x, 1.0, np.where(SPY_MTD < -x, -1.0, 0.0))   # +1 = short USD
        last_start = np.maximum.accumulate(np.where(start, np.arange(T), 0))
        usd_short = np.where(active, dir_at_start[last_start], 0.0)
        return usd_short[:, None] * CCY_SIGN[None, :] * MAJ.vs
    if h == "G4":
        f, s = int(p[0]), int(p[1])
        a, b = XB.sma_price(f), XB.sma_price(s)
        return np.where(np.isnan(b), 0.0, np.where(a > b, 1.0, -1.0)) * XB.vs
    raise ValueError(h)


BOOK = {"G1": XB, "G2": MAJ, "G3": MAJ, "G4": XB}


def strat(h, p):
    return BOOK[h].run(signal(h, p))


# ---------------------------------------------------------------- stats

def sharpe(r):
    r = r[np.isfinite(r)]
    s = r.std(ddof=1)
    return float(r.mean() / s * np.sqrt(ANN)) if s > 0 else 0.0


def ann_ret(r):
    g = np.prod(1 + r)
    return float(g ** (ANN / len(r)) - 1) if g > 0 else -1.0


def max_dd(r):
    eq = np.cumprod(1 + r)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def stats(r):
    return {"ann_return": ann_ret(r), "monthly_return": (1 + ann_ret(r)) ** (1 / 12) - 1,
            "ann_vol": float(r.std(ddof=1) * np.sqrt(ANN)), "sharpe": sharpe(r), "max_dd": max_dd(r),
            "total_return": float(np.prod(1 + r) - 1)}


def target_check(r):
    """Criterion 5 on out-of-sample returns r (daily)."""
    a = ann_ret(r)
    out = {"oos_sharpe": sharpe(r)}
    if a > 0:
        lo, hi = 0.0, 50.0                      # leverage that makes the annual return 26.8%
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if ann_ret(r * mid) < TARGET_ANNUAL else (lo, mid)
        L = hi
        out.update({"leverage_for_2pct_month": L, "max_dd_at_that_leverage": max_dd(r * L)})
    else:
        out.update({"leverage_for_2pct_month": None, "max_dd_at_that_leverage": None})
    lo, hi = 0.0, 50.0                          # leverage that keeps max drawdown at 20%
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if max_dd(r * mid) > DD_BUDGET else (lo, mid)
    out["leverage_at_20pct_dd"] = lo
    out["monthly_return_at_20pct_dd"] = (1 + ann_ret(r * lo)) ** (1 / 12) - 1 if a > 0 else None
    out["target_reachable"] = bool(a > 0 and out["oos_sharpe"] >= MIN_SHARPE_TARGET
                                   and out["max_dd_at_that_leverage"] >= MAX_DD_AT_TARGET)
    return out


# ---------------------------------------------------------------- walk-forward, Monte Carlo

GRIDS = {
    "G1": [(n, k) for n in (5, 10, 20, 40, 60) for k in (1.0, 1.5, 2.0, 2.5, 3.0)],
    "G2": [(n, h) for n in (1, 2, 3, 5, 10) for h in (1, 2, 3, 5)],
    "G3": [(d, x) for d in (1, 2, 3, 4, 5) for x in (0.0, 0.005, 0.01, 0.02, 0.03)],
    "G4": [(f, s) for f in (5, 10, 20, 30, 50, 75, 100) for s in (50, 75, 100, 150, 200, 250, 300) if f < s / 1.5],
}
HYP = list(GRIDS)
NAMES = {"G1": "Cross-pair mean reversion (21 crosses)", "G2": "Short-term cross-sectional reversal",
         "G3": "Month-end equity-hedge flow (USD)", "G4": "Trend on crosses (21 crosses)"}


def walk_forward(h):
    grid = GRIDS[h]
    res = [strat(h, p) for p in grid]
    R, G = np.array([x[0] for x in res]), np.array([x[1] for x in res])
    r_wf, g_wf, chosen = np.full(T, np.nan), np.full(T, np.nan), {}
    for y in WF_YEARS:
        tr = (YEAR >= y - TRAIN_YEARS) & (YEAR <= y - 1)
        best = int(np.argmax([sharpe(R[i, tr]) for i in range(len(grid))]))
        chosen[y] = grid[best]
        te = YEAR == y
        r_wf[te], g_wf[te] = R[best, te], G[best, te]
        if y == WF_YEARS[0]:        # 2016 with the 2017 choice: only to warm up portfolio vol scaling
            pre = YEAR == y - 1
            r_wf[pre], g_wf[pre] = R[best, pre], G[best, pre]
    dev_blend = np.mean([R[grid.index(p)] for p in chosen.values()], axis=0)
    return r_wf, g_wf, chosen, dev_blend


def draw_params(h, rng, n):
    if h == "G1":
        return list(zip(rng.integers(5, 61, n).tolist(), rng.uniform(1.0, 3.0, n).tolist()))
    if h == "G2":
        return list(zip(rng.integers(1, 11, n).tolist(), rng.integers(1, 6, n).tolist()))
    if h == "G3":
        return list(zip(rng.integers(1, 6, n).tolist(), rng.uniform(0.0, 0.03, n).tolist()))
    out = []
    while len(out) < n:
        f, s = int(rng.integers(5, 101)), int(rng.integers(50, 301))
        if f < s / 1.5:
            out.append((f, s))
    return out


def block_boot(r, rng):
    L = len(r)
    nb = int(np.ceil(L / BLOCK))
    starts = rng.integers(0, L - BLOCK + 1, size=(N_BOOT, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(N_BOOT, -1)[:, :L]
    lr = np.log1p(r)[idx].sum(axis=1)
    return np.expm1(lr * ANN / L), np.expm1(lr), idx


def scale_to_vol(r):
    sd = pd.Series(r).rolling(VOL_WIN).std().shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        k = np.nan_to_num(TARGET_VOL / (sd * np.sqrt(ANN)), nan=0.0, posinf=0.0)
    k = np.minimum(k, MAX_STRAT_SCALE)
    return r * k, k


# ---------------------------------------------------------------- main

def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    for h in HYP:
        r_wf, g_wf, chosen, dev = walk_forward(h)
        wf[h] = (r_wf, g_wf)
        res[h] = {"name": NAMES[h], "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos_2017_2023": stats(r_wf[M_OOS]),
                  "oos_swap_adjusted_ann_return": ann_ret(r_wf[M_OOS]) - SWAP_PER_YEAR * float(np.mean(g_wf[M_OOS])),
                  "holdout_2024_2026_seen_adjacent": stats(r_wf[M_HOLD]),
                  "dev_2008_2016_chosen_blend": stats(dev[M_DEV]),
                  "target_2pct_month": target_check(r_wf[M_OOS])}
        print(f"{h} WF ({time.time()-t0:.0f}s): OOS Sharpe {res[h]['oos_2017_2023']['sharpe']:.2f}, "
              f"hold {res[h]['holdout_2024_2026_seen_adjacent']['sharpe']:.2f}, dev {res[h]['dev_2008_2016_chosen_blend']['sharpe']:.2f}")

    rows = []
    for h in HYP:
        for i, p in enumerate(draw_params(h, rng, N_PARAM_MC)):
            r, _ = strat(h, p)
            rows.append({"hyp": h, "i": i, "p1": p[0], "p2": p[1], "oos_sharpe": sharpe(r[M_OOS]),
                         "oos_ann_return": ann_ret(r[M_OOS]), "hold_sharpe": sharpe(r[M_HOLD]),
                         "dev_sharpe": sharpe(r[M_DEV])})
        print(f"{h} param MC ({time.time()-t0:.0f}s)")
    mc = pd.DataFrame(rows)
    mc.to_csv(OUT / "param_mc.csv", index=False, float_format="%.5f")

    boots = {}
    for h in HYP:
        s = mc[mc.hyp == h]
        res[h]["param_mc"] = {"n": len(s), "frac_oos_sharpe_pos": float((s.oos_sharpe > 0).mean()),
                              "median_oos_sharpe": float(s.oos_sharpe.median()),
                              "p05_oos_sharpe": float(s.oos_sharpe.quantile(.05)),
                              "p95_oos_sharpe": float(s.oos_sharpe.quantile(.95)),
                              "frac_hold_sharpe_pos": float((s.hold_sharpe > 0).mean()),
                              "frac_dev_sharpe_pos": float((s.dev_sharpe > 0).mean())}
        a, tot, _ = block_boot(wf[h][0][M_OOS], rng)
        boots[h] = a
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "median_ann_return": float(np.median(a)),
                               "p95_ann_return": float(np.percentile(a, 95)), "prob_loss_over_oos": float((tot < 0).mean())}
        o = res[h]
        c = {"c1_wf_oos_sharpe>=0.3_and_ret>0": o["oos_2017_2023"]["sharpe"] >= 0.3 and o["oos_2017_2023"]["total_return"] > 0,
             "c2_param_mc_>=60%_pos_and_median>0": o["param_mc"]["frac_oos_sharpe_pos"] >= 0.6 and o["param_mc"]["median_oos_sharpe"] > 0,
             "c3_return_mc_prob_loss<20%": o["return_mc"]["prob_loss_over_oos"] < 0.2,
             "c4_dev_sharpe>0": o["dev_2008_2016_chosen_blend"]["sharpe"] > 0}
        o["criteria"], o["validated"] = c, all(c.values())
        o["meets_2pct_month"] = o["validated"] and o["target_2pct_month"]["target_reachable"]

    validated = [h for h in HYP if res[h]["validated"]]
    port_h = validated or HYP
    live = M_OOS | M_HOLD
    sc = {h: scale_to_vol(np.nan_to_num(wf[h][0])) for h in port_h}
    port = np.mean([sc[h][0] for h in port_h], axis=0)
    pr = port[live]
    summary = {"data": {"first": str(IDX[0].date()), "last": str(IDX[-1].date()), "days": T,
                        "instruments": {"majors": MAJORS, "crosses": CROSS_NAMES}},
               "hypotheses": res, "validated": validated,
               "portfolio": {"members": port_h, "tradable": bool(validated),
                             "oos_2017_2023": stats(port[M_OOS]), "holdout_2024_2026_seen_adjacent": stats(port[M_HOLD]),
                             "full_2017_2026": stats(pr), "target_2pct_month": target_check(port[M_OOS]),
                             "calendar_years": {str(y): float(np.prod(1 + port[live & (YEAR == y)]) - 1) for y in WF_YEARS}}}
    a, tot, idx = block_boot(pr, rng)
    summary["portfolio"]["return_mc_full"] = {"p05_ann_return": float(np.percentile(a, 5)),
                                              "median_ann_return": float(np.median(a)),
                                              "p95_ann_return": float(np.percentile(a, 95)),
                                              "prob_loss": float((tot < 0).mean())}
    # portfolio parameter MC: portfolio i uses random set i of each member
    pm = []
    sub = {h: mc[mc.hyp == h][["p1", "p2"]].to_numpy() for h in port_h}
    for i in range(N_PARAM_MC):
        rp = np.mean([scale_to_vol(strat(h, tuple(sub[h][i]))[0])[0] for h in port_h], axis=0)
        pm.append((sharpe(rp[M_OOS]), sharpe(rp[M_HOLD]), ann_ret(rp[live])))
    pm = np.array(pm)
    pd.DataFrame(pm, columns=["oos_sharpe", "hold_sharpe", "ann_return_2017_2026"]).to_csv(
        OUT / "portfolio_param_mc.csv", index=False, float_format="%.5f")
    summary["portfolio"]["param_mc"] = {"frac_oos_sharpe_pos": float((pm[:, 0] > 0).mean()),
                                        "median_oos_sharpe": float(np.median(pm[:, 0])),
                                        "frac_hold_sharpe_pos": float((pm[:, 1] > 0).mean()),
                                        "median_ann_return": float(np.median(pm[:, 2])),
                                        "p05_ann_return": float(np.percentile(pm[:, 2], 5)),
                                        "p95_ann_return": float(np.percentile(pm[:, 2], 95))}
    df = pd.DataFrame({h: wf[h][0] for h in HYP}, index=IDX)
    df["portfolio"] = port
    df[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    charts(df[live], mc, pm, pr, idx, boots, summary)
    print(json.dumps({h: {"validated": res[h]["validated"], "meets_2pct": res[h]["meets_2pct_month"], **res[h]["criteria"]} for h in HYP}, indent=1))
    print(json.dumps(summary["portfolio"], indent=1, default=float))
    print(f"done in {time.time()-t0:.0f}s")


def charts(df, mc, pm, pr, idx, boots, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    port = summary["portfolio"]
    tag = "validated" if port["tradable"] else "NOT validated - information only"
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for h in HYP:
        ax[0].plot(df.index, np.cumprod(1 + df[h].fillna(0)), lw=0.8, alpha=0.7, label=f"{h} {NAMES[h]}")
    eq = np.cumprod(1 + df["portfolio"])
    ax[0].plot(df.index, eq, color="k", lw=2, label=f"Portfolio ({'+'.join(port['members'])})")
    tgt = (1 + TARGET_ANNUAL) ** (np.arange(len(df)) / ANN)
    ax[0].plot(df.index, tgt, color="green", ls="--", lw=1, label="2% a month target")
    ax[0].set_yscale("log")
    for a in ax:
        a.axvspan(HOLD[0], HOLD[1], color="orange", alpha=0.12)
    ax[0].set_title(f"FX round 2 walk-forward equity, net of costs (2017-2026) - portfolio {tag}")
    ax[0].legend(fontsize=8, loc="upper left")
    ax[0].grid(alpha=0.3)
    ax[1].fill_between(df.index, eq / np.maximum.accumulate(eq) - 1, 0, color="firebrick", alpha=0.5)
    ax[1].set_ylabel("drawdown")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "portfolio_curve.png", dpi=120)
    plt.close(fig)

    fig, axs = plt.subplots(1, 5, figsize=(22, 4.5))
    for a, h in zip(axs, HYP):
        s = mc[mc.hyp == h]
        a.hist(s.oos_sharpe, bins=60, color="steelblue", alpha=0.8, label="OOS 2017-23")
        a.hist(s.hold_sharpe, bins=60, color="orange", alpha=0.5, label="holdout 24-26")
        a.axvline(0, color="k")
        p = summary["hypotheses"][h]["param_mc"]
        a.set_title(f"{h} {NAMES[h]}\n{p['frac_oos_sharpe_pos']:.0%} of 10,000 sets >0, median {p['median_oos_sharpe']:.2f}", fontsize=8)
        a.legend(fontsize=7)
    axs[4].hist(pm[:, 0], bins=60, color="k", alpha=0.7, label="OOS 2017-23")
    axs[4].hist(pm[:, 1], bins=60, color="orange", alpha=0.5, label="holdout 24-26")
    axs[4].axvline(0, color="r")
    axs[4].set_title(f"Portfolio, 10,000 random parameter sets\n{(pm[:,0]>0).mean():.0%} >0, median {np.median(pm[:,0]):.2f}", fontsize=8)
    axs[4].legend(fontsize=7)
    fig.suptitle("Parameter Monte Carlo: net Sharpe of 10,000 random parameter sets (seed 20260929)")
    fig.tight_layout()
    fig.savefig(OUT / "param_mc.png", dpi=110)
    plt.close(fig)

    paths = np.cumprod(1 + pr[idx], axis=1)
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
    x = np.arange(paths.shape[1]) / ANN
    for q, al in ((5, .15), (25, .3)):
        ax[0].fill_between(x, np.percentile(paths, q, axis=0), np.percentile(paths, 100 - q, axis=0),
                           color="steelblue", alpha=al, label=f"{q}-{100-q}th pct")
    ax[0].plot(x, np.median(paths, axis=0), color="steelblue", label="median resample")
    ax[0].plot(x, np.cumprod(1 + pr), color="k", lw=1.5, label="actual")
    ax[0].plot(x, (1 + TARGET_ANNUAL) ** x, color="green", ls="--", label="2% a month")
    ax[0].set_yscale("log")
    ax[0].set_title("Portfolio: 10,000 block-bootstraps of real 2017-2026 daily returns")
    ax[0].legend(fontsize=8)
    for h in HYP:
        ax[1].hist(boots[h], bins=80, histtype="step", lw=1.2, label=f"{h} {NAMES[h]}")
    ax[1].axvline(0, color="k")
    ax[1].axvline(TARGET_ANNUAL, color="green", ls="--", label="2% a month")
    ax[1].set_title("Return MC per hypothesis: annualised return, resampled OOS 2017-2023")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "return_mc.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
