"""Strategy lab round 10: Q1 = round-9 model P1 with REAL daily financing (OECD 3-month rates) instead of the
flat swap charge. See edge/lab/r10/PREREGISTRATION.md. Everything else is imported unchanged from edge.lab.r9.

Run:  python -m edge.lab.r10.research
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe
from edge.lab.r9 import research as R9

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results"
SEED, N_MC, N_TRIALS = 20261007, 10_000, 28
MARKUP = 0.01

rates = pd.read_csv(ROOT / "data" / "rates" / "ir3m_monthly.csv", index_col=0)
rates.index = pd.PeriodIndex(rates.index, freq="M")
prev_month = (R9.IDX.to_period("M") - 1)
RT = rates.reindex(prev_month).ffill().to_numpy()                 # T x currencies, % a year, previous month
CCY = list(rates.columns)


def pair_ccys(p):
    return (p[:3], p[3:]) if not p.startswith("XA") else ("METAL", "USD")


days = np.r_[1, np.diff(R9.IDX.values).astype("timedelta64[D]").astype(int)]
CARRY = np.zeros((R9.T, R9.NI))                                   # daily carry of a LONG unit, fraction
for j, p in enumerate(R9.INST):
    b, q = pair_ccys(p)
    rb = np.zeros(R9.T) if b == "METAL" else RT[:, CCY.index(b)]
    rq = RT[:, CCY.index(q)]
    CARRY[:, j] = (rb - rq) / 100 / 360 * days
CARRY = np.nan_to_num(CARRY)
MK = MARKUP / 360 * days


def run_real(pred, H):
    reb = np.zeros(R9.T, bool)
    first = np.flatnonzero(np.isfinite(pred).any(1))
    if len(first) == 0:
        return np.zeros(R9.T)
    reb[first[0]::H] = True
    last = np.maximum.accumulate(np.where(reb, np.arange(R9.T), 0))
    sig = np.nan_to_num(np.sign(pred))[last] * (np.arange(R9.T) >= first[0])[:, None]
    w = sig * R9.VS
    gap = np.zeros_like(R9.CL)
    gap[1:] = R9.O[1:] / R9.CL[:-1] - 1
    day = R9.CL / R9.O - 1
    hg, hd = np.zeros_like(w), np.zeros_like(w)
    hg[2:], hd[1:] = w[:-2], w[:-1]
    fin = hd * CARRY - np.abs(hd) * MK[:, None]
    r = hg * gap + hd * day - np.abs(hd - hg) * R9.cost + fin
    return np.nan_to_num(r).sum(1) / R9.NI


R9.run = run_real                                                  # the only change vs round 9


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    R = np.array([R9.strat(p) for p in R9.GRID])
    r_wf, chosen, _ = C.walk_forward(R, R9.GRID, R9.YEAR, R9.WF_YEARS)
    dev = np.mean([R9.strat(p, years=[2014, 2015, 2016], train_len=2) for p in set(chosen.values())], axis=0)
    print(f"WF done ({time.time()-t0:.0f}s): OOS {C.sharpe(r_wf[R9.M_OOS]):.2f}", flush=True)
    draws = list(zip(rng.integers(1, 21, N_MC).tolist(), np.exp(rng.uniform(np.log(0.1), np.log(1000), N_MC)).tolist(),
                     rng.uniform(0, 0.8, N_MC).tolist()))
    s = []
    for i, p in enumerate(draws):
        x = R9.strat(p)
        s.append((C.sharpe(x[R9.M_OOS]), C.sharpe(x[R9.M_HOLD])))
        if i % 2000 == 0:
            print(f"  MC {i} ({time.time()-t0:.0f}s)", flush=True)
    s = np.array(s)
    a, tot = C.block_boot(r_wf[R9.M_OOS], rng)
    o = {"name": "P1 with real financing (OECD 3M rates)", "chosen_params": {str(y): list(p) for y, p in chosen.items()},
         "oos": C.stats(r_wf[R9.M_OOS]), "holdout": C.stats(r_wf[R9.M_HOLD]), "dev": C.stats(dev[R9.M_DEV]),
         "target": C.target_check(r_wf[R9.M_OOS]),
         "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                      "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean())},
         "return_mc": {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}}
    o["deflated_sharpe"] = deflated_sharpe(r_wf[R9.M_OOS], N_TRIALS, R9.PRIOR + [-0.88, o["oos"]["sharpe"]])
    o["criteria"], o["validated"] = C.criteria(o, o["deflated_sharpe"]["dsr"] >= 0.95)
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "Q1": o}, indent=2, default=float))
    t = o["target"]
    print("Q1 OOS sh %.2f ann %+.1f%% dd %.0f%% | hold sh %.2f ann %+.1f%% | dev %.2f | pMC %.0f%% med %.2f | Ploss %.0f%% | DSR %.3f | within limits %s/mo | fails %s" % (
        o["oos"]["sharpe"], o["oos"]["ann_return"] * 100, o["oos"]["max_dd"] * 100, o["holdout"]["sharpe"],
        o["holdout"]["ann_return"] * 100, o["dev"]["sharpe"], o["param_mc"]["frac_oos_sharpe_pos"] * 100,
        o["param_mc"]["median_oos_sharpe"], o["return_mc"]["prob_loss_over_oos"] * 100, o["deflated_sharpe"]["dsr"],
        None if t["monthly_return_within_limits"] is None else round(t["monthly_return_within_limits"] * 100, 2),
        ",".join(k.split("_")[0] for k, v in o["criteria"].items() if not v)))
    print("chosen:", o["chosen_params"], f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
