"""Strategy lab round 4: pre-registered multi-day hypotheses J1-J3 (see edge/lab/r4/PREREGISTRATION.md).

Real HistData bid bars -> daily bars closing 17:00 New York. Signals on the close, fills at the next open, costs per
unit |change in weight| per side, swap on held notional. Random numbers (seed 20261001) only pick parameter sets
and resample real returns.

Run:  python -m edge.lab.r4.research
"""
from __future__ import annotations

import json
import time
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "histdata"
OUT = Path(__file__).resolve().parent / "results"
CACHE = DATA / "_cache" / "daily_r4.pkl"

MAJORS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
CCYS = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]
CCY_SIGN = np.array([1, 1, -1, 1, -1, -1, 1], float)
TABLE = np.array([1.0, 1.5, 1.2, 1.3, 1.8, 1.8, 2.0])
PIP = np.array([1e-2 if p.endswith("JPY") else 1e-4 for p in MAJORS])
MINORS = ["USDNOK", "USDSEK", "USDPLN", "USDHUF", "USDCZK", "EURNOK", "EURSEK", "EURPLN", "EURHUF"]
MINOR_SIDE_COST = 3e-4                      # 6 bp round turn
SWAP = {"A": 0.02, "B": 0.04}
LAST = pd.Timestamp("2026-09-25")
DEV = (pd.Timestamp("2012-01-01"), pd.Timestamp("2016-12-31"))
OOS = (pd.Timestamp("2017-01-01"), pd.Timestamp("2023-12-31"))
HOLD = (pd.Timestamp("2024-01-01"), LAST)
WF_YEARS = list(range(2017, 2027))
SEED, N_MC = 20261001, 10_000
N_TRIALS = 16
PRIOR_FX = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350]


# ---------------------------------------------------------------- data

def daily(pair):
    df = pd.concat([pd.read_csv(f) for f in sorted((DATA / pair).glob("*.csv.gz"))], ignore_index=True)
    ts = pd.to_datetime(df.ts, utc=True).dt.tz_convert("America/New_York")
    day = (ts + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()     # 17:00 NY -> next trading date
    g = df.groupby(day.values)
    d = pd.DataFrame({"o": g.bo.first(), "h": g.bh.max(), "l": g.bl.min(), "c": g.bc.last()})
    d = d[(d.index.dayofweek < 5) & (d.index <= LAST)]
    return d


def load():
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out = {p: daily(p) for p in MAJORS + MINORS}
    pd.to_pickle(out, CACHE)
    return out


RAW = load()
IDX = RAW[MAJORS[0]].index
for p in MAJORS + MINORS:
    IDX = IDX.intersection(RAW[p].index)
T = len(IDX)
YEAR = IDX.year.to_numpy()


def arr(pairs, k):
    return np.column_stack([RAW[p][k].reindex(IDX).to_numpy(float) for p in pairs])


MO, MC_ = arr(MAJORS, "o"), arr(MAJORS, "c")
VO = np.where(CCY_SIGN > 0, MO, 1 / MO)
VC = np.where(CCY_SIGN > 0, MC_, 1 / MC_)
CROSS = list(combinations(range(7), 2))
A_NAMES = MAJORS + [CCYS[a] + CCYS[b] for a, b in CROSS]
A_O = np.column_stack([MO] + [VO[:, a:a + 1] / VO[:, b:b + 1] for a, b in CROSS])
A_C = np.column_stack([MC_] + [VC[:, a:a + 1] / VC[:, b:b + 1] for a, b in CROSS])
MAJ_COST = (TABLE + 0.9) * PIP / 2 / MO
A_COST = np.column_stack([MAJ_COST] + [MAJ_COST[:, a:a + 1] + MAJ_COST[:, b:b + 1] for a, b in CROSS])
B_O, B_C = arr(MINORS, "o"), arr(MINORS, "c")
B_COST = np.full_like(B_C, MINOR_SIDE_COST)


class Book:
    def __init__(self, O, Cl, cost, swap):
        self.O, self.C, self.cost, self.swap = O, Cl, cost, swap
        self.n = Cl.shape[1]
        self.gap = np.zeros_like(Cl)
        self.gap[1:] = O[1:] / Cl[:-1] - 1
        self.day = Cl / O - 1
        self.ret = np.zeros_like(Cl)
        self.ret[1:] = Cl[1:] / Cl[:-1] - 1
        self.vs = self._vs()
        self.cs = np.vstack([np.zeros((1, self.n)), np.cumsum(self.ret, axis=0)])
        self.cs2 = np.vstack([np.zeros((1, self.n)), np.cumsum(self.ret ** 2, axis=0)])
        self.pcs = np.vstack([np.zeros((1, self.n)), np.cumsum(Cl, axis=0)])
        self.pcs2 = np.vstack([np.zeros((1, self.n)), np.cumsum(Cl ** 2, axis=0)])

    def _vs(self):
        sd = pd.DataFrame(self.ret).rolling(60).std().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.nan_to_num(0.10 / (sd * np.sqrt(C.ANN)), nan=0.0, posinf=0.0)

    def rstd(self, n, cs, cs2):
        out = np.full_like(self.C, np.nan)
        s, s2 = cs[n:] - cs[:-n], cs2[n:] - cs2[:-n]
        out[n - 1:] = np.sqrt(np.maximum((s2 - s * s / n) / (n - 1), 0))
        return out

    def ret_sd(self, n):
        return self.rstd(n, self.cs, self.cs2)

    def price_sma_sd(self, n):
        m = np.full_like(self.C, np.nan)
        m[n - 1:] = (self.pcs[n:] - self.pcs[:-n]) / n
        return m, self.rstd(n, self.pcs, self.pcs2)

    def run(self, pos):
        """pos: (T x n) of -1/0/+1 decided at each close. Returns equal-risk daily net return."""
        w = pos * self.vs
        hg, hd = np.zeros_like(w), np.zeros_like(w)
        hg[2:], hd[1:] = w[:-2], w[:-1]
        r = hg * self.gap + hd * self.day - np.abs(hd - hg) * self.cost - np.abs(hd) * self.swap / C.ANN
        return np.nan_to_num(r).sum(axis=1) / self.n


A = Book(A_O, A_C, A_COST, SWAP["A"])
B = Book(B_O, B_C, B_COST, SWAP["B"])


def fill_trades(n_rows, entries, exit_fn):
    """Sequential trades for one instrument: entries = [(i, dir)], exit_fn(i, dir) -> exit close index j.
    Position is dir from close i up to close j-1, flat from close j."""
    pos = np.zeros(n_rows)
    free = 0
    for i, d in entries:
        if i < free:
            continue
        j = exit_fn(i, d)
        pos[i:j] = d
        free = j
    return pos


def first_true(mask_slice):
    k = np.flatnonzero(mask_slice)
    return int(k[0]) if len(k) else None


# ---------------------------------------------------------------- hypotheses

def j1(p):
    s, L, c, N, m, H = int(p[0]), int(p[1]), float(p[2]), int(p[3]), float(p[4]), int(p[5])
    bk = A
    ss, sl = bk.ret_sd(s), bk.ret_sd(L)
    df = pd.DataFrame(bk.C)
    hi, lo = df.rolling(N).max().shift(1).to_numpy(), df.rolling(N).min().shift(1).to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        sq = (ss / sl) < c
    pos = np.zeros_like(bk.C)
    for j in range(bk.n):
        cl, sdl = bk.C[:, j], sl[:, j]
        ent = [(i, 1) for i in np.flatnonzero(sq[:, j] & (cl > hi[:, j]))] + \
              [(i, -1) for i in np.flatnonzero(sq[:, j] & (cl < lo[:, j]))]
        ent.sort()

        def ex(i, d, cl=cl, sdl=sdl):
            end = min(i + H, T - 1)
            win = cl[i + 1:end + 1]
            dist = m * sdl[i] * cl[i]
            best = np.maximum.accumulate(np.r_[cl[i], win])[1:] if d > 0 else np.minimum.accumulate(np.r_[cl[i], win])[1:]
            hit = first_true((win < best - dist) if d > 0 else (win > best + dist))
            return i + 1 + hit if hit is not None else end
        pos[:, j] = fill_trades(T, ent, ex)
    return bk.run(pos)


def j2(p):
    n, k, H = int(p[0]), float(p[1]), int(p[2])
    bk = B
    mu, sd = bk.price_sma_sd(n)
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (bk.C - mu) / sd
    pos = np.zeros_like(bk.C)
    for j in range(bk.n):
        cl, zz, sdd = bk.C[:, j], z[:, j], sd[:, j]
        ent = [(i, 1) for i in np.flatnonzero(zz < -k)] + [(i, -1) for i in np.flatnonzero(zz > k)]
        ent.sort()

        def ex(i, d, cl=cl, zz=zz, sdd=sdd):
            end = min(i + H, T - 1)
            win_c, win_z = cl[i + 1:end + 1], zz[i + 1:end + 1]
            stop = cl[i] - d * 3 * sdd[i]
            cond = ((win_z >= 0) | (win_c < stop)) if d > 0 else ((win_z <= 0) | (win_c > stop))
            hit = first_true(cond)
            return i + 1 + hit if hit is not None else end
        pos[:, j] = fill_trades(T, ent, ex)
    return bk.run(pos)


def j3(p):
    f, s = int(p[0]), int(p[1])
    bk = B
    mf, _ = bk.price_sma_sd(f)
    ms, _ = bk.price_sma_sd(s)
    s60 = bk.ret_sd(60)
    sig = np.where(np.isnan(ms), 0, np.sign(mf - ms))
    pos = np.zeros_like(bk.C)
    for j in range(bk.n):
        sg, cl = sig[:, j], bk.C[:, j]
        cross = np.flatnonzero((sg != 0) & (sg != np.r_[0, sg[:-1]]))
        for a, i in enumerate(cross):
            d = sg[i]
            nxt = cross[a + 1] if a + 1 < len(cross) else T
            win = cl[i + 1:nxt]
            stop = cl[i] - d * 3 * s60[i, j] * cl[i]
            hit = first_true((win < stop) if d > 0 else (win > stop))
            end = i + 1 + hit if hit is not None else nxt
            pos[i:end, j] = d
    return bk.run(pos)


HYP = {"J1": ("Volatility-squeeze breakout (7 majors + 21 crosses)", j1),
       "J2": ("Bollinger mean reversion (9 Scandi/CEE)", j2),
       "J3": ("Moving-average trend (9 Scandi/CEE)", j3)}
GRIDS = {"J1": [(s, L, c, N, m, H) for s in (5, 10) for L in (50, 100) for c in (0.6, 0.8) for N in (20, 40)
                for m in (2, 3) for H in (20, 40)],
         "J2": [(n, k, H) for n in (10, 20, 40) for k in (1.5, 2.0, 2.5) for H in (5, 10, 20)],
         "J3": [(10, 50), (20, 100), (50, 200), (5, 50), (20, 200)]}


def draw(h, rng, n):
    if h == "J1":
        return list(zip(rng.integers(5, 11, n).tolist(), rng.integers(50, 101, n).tolist(), rng.uniform(.5, .9, n).tolist(),
                        rng.integers(10, 41, n).tolist(), rng.uniform(1.5, 3.0, n).tolist(), rng.integers(10, 41, n).tolist()))
    if h == "J2":
        return list(zip(rng.integers(10, 41, n).tolist(), rng.uniform(1.5, 2.5, n).tolist(), rng.integers(5, 21, n).tolist()))
    out = []
    while len(out) < n:
        f, s = int(rng.integers(5, 51)), int(rng.integers(50, 201))
        if f < s / 2:
            out.append((f, s))
    return out


def mask(a, b):
    return (IDX >= a) & (IDX <= b)


M_DEV, M_OOS, M_HOLD = mask(*DEV), mask(*OOS), mask(*HOLD)


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    print(f"data: {T} days {IDX[0].date()}..{IDX[-1].date()}, book A {A.n}, book B {B.n}", flush=True)
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    for h, (name, fn) in HYP.items():
        R = np.array([fn(p) for p in GRIDS[h]])
        r_wf, chosen, dev = C.walk_forward(R, GRIDS[h], YEAR, WF_YEARS)
        wf[h] = r_wf
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos": C.stats(r_wf[M_OOS]), "holdout": C.stats(r_wf[M_HOLD]), "dev": C.stats(dev[M_DEV]),
                  "target": C.target_check(r_wf[M_OOS])}
        print(f"{h} WF ({time.time()-t0:.0f}s): OOS {res[h]['oos']['sharpe']:.2f} hold {res[h]['holdout']['sharpe']:.2f} "
              f"dev {res[h]['dev']['sharpe']:.2f}", flush=True)
    rows = []
    for h, (name, fn) in HYP.items():
        for i, p in enumerate(draw(h, rng, N_MC)):
            r = fn(p)
            rows.append({"hyp": h, "params": json.dumps(list(p)), "oos_sharpe": C.sharpe(r[M_OOS]),
                         "hold_sharpe": C.sharpe(r[M_HOLD]), "dev_sharpe": C.sharpe(r[M_DEV])})
            if i % 1000 == 0:
                print(f"  {h} MC {i} ({time.time()-t0:.0f}s)", flush=True)
    mc = pd.DataFrame(rows)
    mc.to_csv(OUT / "param_mc.csv", index=False, float_format="%.5f")
    sharpes = PRIOR_FX + [res[h]["oos"]["sharpe"] for h in HYP]
    for h in HYP:
        s = mc[mc.hyp == h]
        res[h]["param_mc"] = {"frac_oos_sharpe_pos": float((s.oos_sharpe > 0).mean()), "median_oos_sharpe": float(s.oos_sharpe.median()),
                              "frac_hold_sharpe_pos": float((s.hold_sharpe > 0).mean()), "frac_dev_sharpe_pos": float((s.dev_sharpe > 0).mean())}
        a, tot = C.block_boot(wf[h][M_OOS], rng)
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "median_ann_return": float(np.median(a)),
                               "prob_loss_over_oos": float((tot < 0).mean())}
        res[h]["deflated_sharpe"] = deflated_sharpe(wf[h][M_OOS], N_TRIALS, sharpes)
        res[h]["criteria"], res[h]["validated"] = C.criteria(res[h], res[h]["deflated_sharpe"]["dsr"] >= 0.95)
    live = M_OOS | M_HOLD
    pd.DataFrame(wf, index=IDX)[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    summary = {"days": T, "first": str(IDX[0].date()), "last": str(IDX[-1].date()), "n_trials_for_dsr": N_TRIALS,
               "hypotheses": res, "validated": [h for h in HYP if res[h]["validated"]]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    charts(pd.DataFrame(wf, index=IDX)[live], mc, res)
    print(json.dumps({h: {"validated": res[h]["validated"], **res[h]["criteria"]} for h in HYP}, indent=1))
    print(f"done in {time.time()-t0:.0f}s")


def charts(df, mc, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 6))
    for h in HYP:
        ax.plot(df.index, np.cumprod(1 + df[h].fillna(0)), lw=1.3, label=f"{h} {HYP[h][0]}")
    ax.plot(df.index, (1 + C.TARGET_ANNUAL) ** (np.arange(len(df)) / C.ANN), "g--", lw=1, label="2% a month target")
    ax.set_yscale("log")
    ax.axvspan(HOLD[0], HOLD[1], color="orange", alpha=0.12)
    ax.set_title("Lab round 4 (multi-day holds): walk-forward equity, net of costs and swap, 2017-2026")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "equity.png", dpi=120)
    plt.close(fig)
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.5))
    for a, h in zip(axs, HYP):
        s = mc[mc.hyp == h]
        a.hist(s.oos_sharpe, bins=50, color="steelblue", alpha=0.8, label="OOS 2017-23")
        a.hist(s.hold_sharpe, bins=50, color="orange", alpha=0.5, label="holdout 24-26")
        a.axvline(0, color="k")
        p = res[h]["param_mc"]
        a.set_title(f"{h}: {p['frac_oos_sharpe_pos']:.0%} of 10,000 sets >0, median {p['median_oos_sharpe']:.2f}", fontsize=9)
        a.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "param_mc.png", dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
