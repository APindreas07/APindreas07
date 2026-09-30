"""Strategy lab round 6: L1 Asian-range breakout (5-min, HistData) and L4 weekly reversal after extreme weeks
(daily, TradeStation). See edge/lab/r6/PREREGISTRATION.md. Random numbers (seed 20261003) only pick parameter sets
and resample real returns.

Run:  python -m edge.lab.r6.research
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
from edge.lab.r3 import research as R3

OUT = Path(__file__).resolve().parent / "results"
SEED, N_MC, N_TRIALS = 20261003, 10_000, 21
PRIOR_FX = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350,
            -0.900, -0.760, -1.010, -0.840, -0.100, 0.240]
WF_YEARS = list(range(2017, 2027))
SLOT = np.arange(288)

# ---------------------------------------------------------------- L1 (5-minute, London time grid from round 3)
L1_PAIRS = [0, 1, 2]                                   # EURUSD, GBPUSD, USDJPY in R3.PAIRS
BC, BO, AO = R3.G["bc"], R3.G["bo"], R3.G["ao"]
ASIA_HI = np.nanmax(BC[:, :84, :], axis=1)             # bars 00:00-06:55 London
ASIA_LO = np.nanmin(BC[:, :84, :], axis=1)


def l1(p):
    f, end_h = float(p[0]), int(p[1])
    end = end_h * 12
    out = np.zeros((R3.ND, 7))
    for j in L1_PAIRS:
        hi, lo = ASIA_HI[:, j], ASIA_LO[:, j]
        rng_pips = (hi - lo) / R3.PIP[j]
        ok = np.isfinite(rng_pips) & (rng_pips >= 10) & (rng_pips <= 80)
        up, dn = hi + f * (hi - lo), lo - f * (hi - lo)
        win = BC[:, 84:end, j]
        cl, cs = win > up[:, None], win < dn[:, None]
        il = np.where(cl.any(1), cl.argmax(1), 10 ** 6)
        is_ = np.where(cs.any(1), cs.argmax(1), 10 ** 6)
        s = np.minimum(il, is_) + 84                           # signal slot
        d = np.where(il < is_, 1.0, -1.0)
        has = ok & (np.minimum(il, is_) < 10 ** 6)
        s = np.where(has, s, 0)
        stop = np.where(d > 0, lo, hi)
        allb = BC[:, :, j]
        breach = np.where(d[:, None] > 0, allb < stop[:, None], allb > stop[:, None])
        breach &= (SLOT[None, :] > s[:, None]) & (SLOT[None, :] < 192)
        xs = np.where(breach.any(1), breach.argmax(1) + 1, 192)  # exit at the open of the next slot, or 16:00
        e = np.minimum(s + 1, 287)
        rows = np.arange(R3.ND)
        bi, ai, bx, ax = BO[rows, e, j], AO[rows, e, j], BO[rows, xs, j], AO[rows, xs, j]
        r = np.where(d > 0, (bx - ai) / ai, (bi - ax) / bi)
        # spread is already paid via ask = bid + table spread; add 0.45 pip commission+slippage per side
        cost = (R3.EXTRA_SIDE_PIPS * R3.PIP[j]) * (1 / ((ai + bi) / 2) + 1 / ((ax + bx) / 2))
        r = np.where(has & (s + 1 < 192), r - cost, 0.0)
        out[:, j] = np.nan_to_num(r)
    return (out * R3.W)[:, L1_PAIRS].sum(axis=1) / len(L1_PAIRS)


# ---------------------------------------------------------------- L4 (daily, 7 majors + 21 crosses)
MAJ, XB = FX2.MAJ, FX2.XB
CL = np.hstack([MAJ.C, XB.C])
NI = CL.shape[1]
FRI = np.flatnonzero(FX2.IDX.dayofweek.to_numpy() == 4)
WK_RET = np.full((len(FRI), NI), np.nan)
WK_RET[1:] = CL[FRI[1:]] / CL[FRI[:-1]] - 1
WK_SD = pd.DataFrame(WK_RET).rolling(52).std().shift(1).to_numpy()


def l4(p):
    k, W = float(p[0]), int(p[1])
    with np.errstate(invalid="ignore", divide="ignore"):
        z = WK_RET / WK_SD
    pos = np.zeros((FX2.T, NI))
    for j in range(NI):
        free = 0
        for wi in np.flatnonzero(np.abs(z[:, j]) > k):
            i = FRI[wi]
            if i < free or wi + W >= len(FRI):
                continue
            d = -np.sign(WK_RET[wi, j])
            end = FRI[wi + W]
            stop = CL[i, j] * (1 - d * 3 * WK_SD[wi, j])
            win = CL[i + 1:end + 1, j]
            hit = np.flatnonzero(win < stop) if d > 0 else np.flatnonzero(win > stop)
            ex = i + 1 + int(hit[0]) if len(hit) else end
            pos[i:ex, j] = d
            free = ex
    rm, _ = MAJ.run(pos[:, :7] * MAJ.vs)
    rx, _ = XB.run(pos[:, 7:] * XB.vs)
    w = np.hstack([pos[:, :7] * MAJ.vs, pos[:, 7:] * XB.vs])
    hd = np.zeros_like(w)
    hd[1:] = w[:-1]
    swap = np.abs(hd).mean(axis=1) * 0.02 / C.ANN
    return (rm * 7 + rx * 21) / NI - swap


HYP = {"L1": ("Asian-range breakout at London (EURUSD, GBPUSD, USDJPY)", l1, R3),
       "L4": ("Weekly reversal after extreme weeks (7 majors + 21 crosses)", l4, FX2)}
GRIDS = {"L1": [(f, e) for f in (0.0, 0.1, 0.2, 0.3) for e in (9, 10, 11)],
         "L4": [(k, W) for k in (1.5, 2.0, 2.5, 3.0) for W in (1, 2, 3)]}


def draw(h, rng, n):
    if h == "L1":
        return list(zip(rng.uniform(0, 0.3, n).tolist(), rng.integers(9, 12, n).tolist()))
    return list(zip(rng.uniform(1.5, 3.0, n).tolist(), rng.integers(1, 4, n).tolist()))


def masks(mod):
    return mod.M_DEV, mod.M_OOS, mod.M_HOLD, (mod.DAYS if mod is R3 else mod.IDX).year.to_numpy()


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    for h, (name, fn, mod) in HYP.items():
        mdev, moos, mhold, years = masks(mod)
        R = np.array([fn(p) for p in GRIDS[h]])
        r_wf, chosen, dev = C.walk_forward(R, GRIDS[h], years, WF_YEARS)
        wf[h] = (r_wf, mod)
        s = np.array([[C.sharpe(x[moos]), C.sharpe(x[mhold]), C.sharpe(x[mdev])] for x in (fn(p) for p in draw(h, rng, N_MC))])
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos": C.stats(r_wf[moos]), "holdout": C.stats(r_wf[mhold]), "dev": C.stats(dev[mdev]),
                  "target": C.target_check(r_wf[moos]),
                  "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                               "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean()), "frac_dev_sharpe_pos": float((s[:, 2] > 0).mean())}}
        a, tot = C.block_boot(r_wf[moos], rng)
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}
        print(f"{h} done ({time.time()-t0:.0f}s): OOS {res[h]['oos']['sharpe']:.2f}", flush=True)
    sharpes = PRIOR_FX + [res[h]["oos"]["sharpe"] for h in HYP]
    for h in HYP:
        r_wf, mod = wf[h]
        res[h]["deflated_sharpe"] = deflated_sharpe(r_wf[masks(mod)[1]], N_TRIALS, sharpes)
        res[h]["criteria"], res[h]["validated"] = C.criteria(res[h], res[h]["deflated_sharpe"]["dsr"] >= 0.95)
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "hypotheses": res,
                                                  "validated": [h for h in HYP if res[h]["validated"]]}, indent=2, default=float))
    print(json.dumps({h: {"validated": res[h]["validated"], **res[h]["criteria"]} for h in HYP}, indent=1))
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
