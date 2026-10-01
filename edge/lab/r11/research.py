"""Strategy lab round 11: R1 time-series and R2 cross-sectional momentum on 18 instruments with real financing.
See edge/lab/r11/PREREGISTRATION.md. Data/costs from edge.lab.r9, carry from edge.lab.r10 (both unchanged).

Run:  python -m edge.lab.r11.research
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe
from edge.lab.r10 import research as R10

R9 = R10.R9
OUT = Path(__file__).resolve().parent / "results"
SEED, N_MC, N_TRIALS = 20261008, 10_000, 30
PRIOR = R9.PRIOR + [-0.880, -0.500]
T, NI = R9.T, R9.NI
FRI = R9.IDX.dayofweek.to_numpy() == 4
GAP = np.zeros_like(R9.CL)
GAP[1:] = R9.O[1:] / R9.CL[:-1] - 1
DAY = R9.CL / R9.O - 1


def run(sig):
    """sig (T x NI): -1/0/+1 decided at Friday closes and held; returns equal-risk daily net returns."""
    last = np.maximum.accumulate(np.where(FRI, np.arange(T), 0))
    s = np.where((last > 0)[:, None], sig[last], 0.0)
    w = s * R9.VS
    hg, hd = np.zeros_like(w), np.zeros_like(w)
    hg[2:], hd[1:] = w[:-2], w[:-1]
    r = hg * GAP + hd * DAY - np.abs(hd - hg) * R9.cost + hd * R10.CARRY - np.abs(hd) * R10.MK[:, None]
    return np.nan_to_num(r).sum(1) / NI


def ret_n(n):
    out = np.full_like(R9.CL, np.nan)
    out[n:] = R9.LOGC[n:] - R9.LOGC[:-n]
    return out


def r1(p):
    return run(np.nan_to_num(np.sign(ret_n(int(p[0])))))


def r2(p):
    n, k = int(p[0]), int(p[1])
    score = ret_n(n) / R9.SD60
    ok = np.isfinite(score).all(1)
    rank = np.argsort(np.argsort(np.nan_to_num(score), axis=1), axis=1)
    sig = np.where(rank >= NI - k, 1.0, np.where(rank < k, -1.0, 0.0)) * ok[:, None]
    return run(sig)


HYP = {"R1": ("Time-series momentum, 18 instruments, real carry", r1),
       "R2": ("Cross-sectional momentum, 18 instruments, real carry", r2)}
GRIDS = {"R1": [(n,) for n in (20, 60, 120, 180, 260)],
         "R2": [(n, k) for n in (20, 60, 120, 260) for k in (2, 4, 6)]}


def draw(h, rng, n):
    if h == "R1":
        return [(int(x),) for x in rng.integers(20, 261, n)]
    return list(zip(rng.integers(20, 261, n).tolist(), rng.integers(2, 7, n).tolist()))


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    for h, (name, fn) in HYP.items():
        R = np.array([fn(p) for p in GRIDS[h]])
        r_wf, chosen, dev = C.walk_forward(R, GRIDS[h], R9.YEAR, R9.WF_YEARS)
        wf[h] = r_wf
        s = np.array([[C.sharpe(x[R9.M_OOS]), C.sharpe(x[R9.M_HOLD]), C.sharpe(x[R9.M_DEV])] for x in (fn(p) for p in draw(h, rng, N_MC))])
        a, tot = C.block_boot(r_wf[R9.M_OOS], rng)
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos": C.stats(r_wf[R9.M_OOS]), "holdout": C.stats(r_wf[R9.M_HOLD]), "dev": C.stats(dev[R9.M_DEV]),
                  "target": C.target_check(r_wf[R9.M_OOS]),
                  "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                               "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean()), "frac_dev_sharpe_pos": float((s[:, 2] > 0).mean())},
                  "return_mc": {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}}
        print(f"{h} done ({time.time()-t0:.0f}s)", flush=True)
    sh = PRIOR + [res[h]["oos"]["sharpe"] for h in HYP]
    for h in HYP:
        res[h]["deflated_sharpe"] = deflated_sharpe(wf[h][R9.M_OOS], N_TRIALS, sh)
        res[h]["criteria"], res[h]["validated"] = C.criteria(res[h], res[h]["deflated_sharpe"]["dsr"] >= 0.95)
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "hypotheses": res}, indent=2, default=float))
    for h, o in res.items():
        t = o["target"]
        print(h, "OOS sh %.2f ann %+.1f%% dd %.0f%% | hold sh %.2f ann %+.1f%% | dev %.2f | pMC %.0f%% med %.2f | Ploss %.0f%% | DSR %.3f | within limits %s/mo | fails %s" % (
            o["oos"]["sharpe"], o["oos"]["ann_return"] * 100, o["oos"]["max_dd"] * 100, o["holdout"]["sharpe"],
            o["holdout"]["ann_return"] * 100, o["dev"]["sharpe"], o["param_mc"]["frac_oos_sharpe_pos"] * 100,
            o["param_mc"]["median_oos_sharpe"], o["return_mc"]["prob_loss_over_oos"] * 100, o["deflated_sharpe"]["dsr"],
            None if t["monthly_return_within_limits"] is None else round(t["monthly_return_within_limits"] * 100, 2),
            ",".join(k.split("_")[0] for k, v in o["criteria"].items() if not v)))
        print("   chosen:", o["chosen_params"])


if __name__ == "__main__":
    main()
