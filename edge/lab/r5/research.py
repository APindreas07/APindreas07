"""Strategy lab round 5: K1 equity-regime risk-currency trend, K2 rebound after equity stress, K3 G1+G3 combination.

See edge/lab/r5/PREREGISTRATION.md. Real TradeStation daily bars (7 majors + SPY, via edge.fx2.research) in.
Random numbers (seed 20261002) only pick parameter sets and resample real returns.

Run:  python -m edge.lab.r5.research
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from edge.fx2 import research as FX2
from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe

OUT = Path(__file__).resolve().parent / "results"
SEED, N_MC, N_TRIALS = 20261002, 10_000, 19
PRIOR_FX = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350,
            -0.900, -0.760, -1.010]
SWAP = 0.02
IDX, T, YEAR = FX2.IDX, FX2.T, FX2.YEAR
M_DEV, M_OOS, M_HOLD = FX2.M_DEV, FX2.M_OOS, FX2.M_HOLD
WF_YEARS = list(range(2017, 2027))

# risk basket: long risk currency vs safe haven, expressed on fx2's cross columns
BASKET = {"JPYAUD": -1, "JPYCAD": -1, "JPYNZD": -1, "AUDCHF": 1, "CADCHF": 1, "CHFNZD": -1}
COLS = [FX2.CROSS_NAMES.index(k) for k in BASKET]
DIRS = np.array(list(BASKET.values()), float)
XB = FX2.XB
X_C = XB.C[:, COLS]
GAP, DAY, COST, VS = XB.gap[:, COLS], XB.day[:, COLS], XB.cost[:, COLS], XB.vs[:, COLS]
RET60 = pd.DataFrame(np.r_[np.zeros((1, 6)), X_C[1:] / X_C[:-1] - 1]).rolling(60).std().to_numpy()
SPY = FX2.SPY
FRIDAY = IDX.dayofweek.to_numpy() == 4


def run(pos):
    """pos (T x 6) of +1/0/-1 in 'risk-on' units at each close -> equal-risk daily net return of the basket."""
    w = pos * DIRS * VS
    hg, hd = np.zeros_like(w), np.zeros_like(w)
    hg[2:], hd[1:] = w[:-2], w[:-1]
    r = hg * GAP + hd * DAY - np.abs(hd - hg) * COST - np.abs(hd) * SWAP / C.ANN
    return np.nan_to_num(r).sum(axis=1) / 6


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def k1(p):
    n, b, s = int(p[0]), float(p[1]), int(p[2])
    m = sma(SPY, n)
    state, st = np.zeros(T), 0.0
    for t in range(T):
        if FRIDAY[t] and np.isfinite(m[t]):
            if SPY[t] > m[t] * (1 + b):
                st = 1.0
            elif SPY[t] < m[t] * (1 - b):
                st = -1.0 if s == 1 else 0.0
        state[t] = st
    return run(np.repeat(state[:, None], 6, axis=1))


def k2(p):
    N, x, H = int(p[0]), float(p[1]), int(p[2])
    rN = np.full(T, np.nan)
    rN[N:] = SPY[N:] / SPY[:-N] - 1
    ev = np.flatnonzero(rN < -x)
    pos = np.zeros((T, 6))
    free = 0
    for i in ev:
        if i < free or i >= T - 1:
            continue
        end = min(i + H, T - 1)
        last = i
        for j in range(6):
            cl = X_C[:, j] ** DIRS[j]                          # price of the risk-on leg
            stop = cl[i] - 3 * RET60[i, j] * cl[i]
            win = cl[i + 1:end + 1]
            k = np.flatnonzero(win < stop)
            ex = i + 1 + int(k[0]) if len(k) else end
            pos[i:ex, j] = 1.0
            last = max(last, ex)
        free = last
    return run(pos)


HYP = {"K1": ("Equity-regime risk-currency trend (SPY SMA filter)", k1),
       "K2": ("Rebound after equity stress (risk basket)", k2)}
GRIDS = {"K1": [(n, b, s) for n in (50, 100, 150, 200, 250) for b in (0.0, 0.01, 0.02) for s in (0, 1)],
         "K2": [(N, x, H) for N in (3, 5, 10) for x in (0.03, 0.05, 0.08) for H in (10, 20, 40)]}


def draw(h, rng, n):
    if h == "K1":
        return list(zip(rng.integers(50, 251, n).tolist(), rng.uniform(0, 0.02, n).tolist(), rng.integers(0, 2, n).tolist()))
    return list(zip(rng.integers(3, 11, n).tolist(), rng.uniform(0.03, 0.10, n).tolist(), rng.integers(5, 41, n).tolist()))


def trip(x):
    return C.sharpe(x[M_OOS]), C.sharpe(x[M_HOLD]), C.sharpe(x[M_DEV])


def k3_combo(r1, r3):
    return np.mean([FX2.scale_to_vol(np.nan_to_num(r1))[0], FX2.scale_to_vol(np.nan_to_num(r3))[0]], axis=0)


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res, wf, mcs = {}, {}, {}
    for h, (name, fn) in HYP.items():
        R = np.array([fn(p) for p in GRIDS[h]])
        r_wf, chosen, dev = C.walk_forward(R, GRIDS[h], YEAR, WF_YEARS)
        wf[h] = r_wf
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()}, "dev": C.stats(dev[M_DEV])}
        print(f"{h} WF done ({time.time()-t0:.0f}s)", flush=True)
        mcs[h] = np.array([trip(fn(p)) for p in draw(h, rng, N_MC)])
        print(f"{h} MC done ({time.time()-t0:.0f}s)", flush=True)
    # K3: combination of round-2 G1 and G3 walk-forward streams
    g1, _, _, g1dev = FX2.walk_forward("G1")
    g3, _, _, g3dev = FX2.walk_forward("G3")
    wf["K3"] = k3_combo(g1, g3)
    wf["K3"][YEAR < 2017] = np.nan
    res["K3"] = {"name": "Combination of round-2 near-misses G1 + G3", "chosen_params": "as edge/fx2 walk-forward",
                 "dev": C.stats(k3_combo(g1dev, g3dev)[M_DEV])}
    p1, p3 = FX2.draw_params("G1", rng, N_MC), FX2.draw_params("G3", rng, N_MC)
    mcs["K3"] = np.array([trip(k3_combo(FX2.strat("G1", a)[0], FX2.strat("G3", b)[0])) for a, b in zip(p1, p3)])
    print(f"K3 done ({time.time()-t0:.0f}s)", flush=True)
    sharpes = PRIOR_FX + [C.sharpe(wf[h][M_OOS]) for h in ("K1", "K2", "K3")]
    for h in ("K1", "K2", "K3"):
        r = wf[h]
        o = res[h]
        o.update({"oos": C.stats(r[M_OOS]), "holdout": C.stats(r[M_HOLD]), "target": C.target_check(r[M_OOS])})
        s = mcs[h]
        o["param_mc"] = {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                         "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean()), "frac_dev_sharpe_pos": float((s[:, 2] > 0).mean())}
        a, tot = C.block_boot(r[M_OOS], rng)
        o["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "median_ann_return": float(np.median(a)),
                          "prob_loss_over_oos": float((tot < 0).mean())}
        o["deflated_sharpe"] = deflated_sharpe(r[M_OOS], N_TRIALS, sharpes)
        o["criteria"], o["validated"] = C.criteria(o, o["deflated_sharpe"]["dsr"] >= 0.95)
    live = M_OOS | M_HOLD
    df = pd.DataFrame(wf, index=IDX)
    df[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    summary = {"first": str(IDX[0].date()), "last": str(IDX[-1].date()), "n_trials_for_dsr": N_TRIALS,
               "hypotheses": res, "validated": [h for h in res if res[h]["validated"]]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 6))
    d = df[live]
    for h in ("K1", "K2", "K3"):
        ax.plot(d.index, np.cumprod(1 + d[h].fillna(0)), lw=1.3, label=f"{h} {res[h]['name']}")
    ax.plot(d.index, (1 + C.TARGET_ANNUAL) ** (np.arange(len(d)) / C.ANN), "g--", lw=1, label="2% a month target")
    ax.set_yscale("log")
    ax.axvspan(FX2.HOLD[0], FX2.HOLD[1], color="orange", alpha=0.12)
    ax.set_title("Lab round 5: walk-forward equity, net of costs and swap, 2017-2026")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "equity.png", dpi=120)
    print(json.dumps({h: {"validated": res[h]["validated"], **res[h]["criteria"]} for h in res}, indent=1))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
