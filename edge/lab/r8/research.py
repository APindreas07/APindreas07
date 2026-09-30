"""Strategy lab round 8: gold and silver (N1 time-series momentum, N2 gold Asian-session drift, N3 gold/silver ratio
mean reversion). See edge/lab/r8/PREREGISTRATION.md. Real HistData bars in; random numbers (seed 20261005) only draw
parameter sets and resample real returns.

Run:  python -m edge.lab.r8.research
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "histdata"
OUT = Path(__file__).resolve().parent / "results"
CACHE = DATA / "_cache" / "metals_r8.pkl"
SEED, N_MC, N_TRIALS = 20261005, 10_000, 26
PRIOR = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350,
         -0.900, -0.760, -1.010, -0.840, -0.100, 0.240, -1.370, -0.140, 0.703, -0.260]
LAST = pd.Timestamp("2026-09-25")
SIDE_COST = np.array([1e-4, 2e-4])          # gold 2 bp, silver 4 bp per round turn
SWAP = 0.03
WF_YEARS = list(range(2017, 2027))


def load():
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    out = {}
    for p in ("XAUUSD", "XAGUSD"):
        df = pd.concat([pd.read_csv(f) for f in sorted((DATA / p).glob("*.csv.gz"))], ignore_index=True)
        ny = pd.to_datetime(df.ts, utc=True).dt.tz_convert("America/New_York")
        df["tday"] = (ny + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()
        df["nyhm"] = ny.dt.hour * 60 + ny.dt.minute
        out[p] = df[["tday", "nyhm", "bo", "bh", "bl", "bc"]]
    pd.to_pickle(out, CACHE)
    return out


RAW = load()
daily = {}
for p, df in RAW.items():
    g = df.groupby("tday")
    d = pd.DataFrame({"o": g.bo.first(), "c": g.bc.last()})
    daily[p] = d[(d.index.dayofweek < 5) & (d.index <= LAST)]
IDX = daily["XAUUSD"].index.intersection(daily["XAGUSD"].index)
T = len(IDX)
O = np.column_stack([daily[p].o.reindex(IDX).to_numpy() for p in ("XAUUSD", "XAGUSD")])
CL = np.column_stack([daily[p].c.reindex(IDX).to_numpy() for p in ("XAUUSD", "XAGUSD")])
YEAR = IDX.year.to_numpy()
GAP = np.zeros_like(CL)
GAP[1:] = O[1:] / CL[:-1] - 1
DAY = CL / O - 1
RET = np.zeros_like(CL)
RET[1:] = CL[1:] / CL[:-1] - 1
_sd = pd.DataFrame(RET).rolling(60).std().to_numpy()
with np.errstate(divide="ignore", invalid="ignore"):
    VS = np.nan_to_num(0.10 / (_sd * np.sqrt(C.ANN)), nan=0.0, posinf=0.0)
FRI = IDX.dayofweek.to_numpy() == 4


def mask(a, b):
    return (IDX >= pd.Timestamp(a)) & (IDX <= pd.Timestamp(b))


M_DEV, M_OOS, M_HOLD = mask("2012-01-01", "2016-12-31"), mask("2017-01-01", "2023-12-31"), mask("2024-01-01", LAST)


def run(pos):
    w = pos * VS
    hg, hd = np.zeros_like(w), np.zeros_like(w)
    hg[2:], hd[1:] = w[:-2], w[:-1]
    r = hg * GAP + hd * DAY - np.abs(hd - hg) * SIDE_COST - np.abs(hd) * SWAP / C.ANN
    return np.nan_to_num(r).sum(axis=1) / 2


def n1(p):
    N = int(p[0])
    sig = np.zeros_like(CL)
    sig[N:] = np.sign(CL[N:] / CL[:-N] - 1)
    last = np.maximum.accumulate(np.where(FRI & (np.arange(T) >= N), np.arange(T), 0))
    pos = np.where((last > 0)[:, None], sig[last], 0.0)
    return run(pos)


# N2: gold only, intraday within one trading day (after the 17:00 NY rollover), no swap
_g = RAW["XAUUSD"]
_g = _g[_g.tday.isin(IDX)]
PIV = {h: _g[_g.nyhm == h * 60].drop_duplicates("tday").set_index("tday").bo.reindex(IDX).to_numpy() for h in (18, 19, 20, 2, 3, 4)}


def n2(p):
    E, X = int(p[0]), int(p[1])
    r = PIV[X] / PIV[E] - 1 - 2 * SIDE_COST[0]
    r = np.nan_to_num(r) * VS[:, 0]
    return r / 2                                            # gold is one of the two equal-risk slots


LR = np.log(CL[:, 0] / CL[:, 1])


def n3(p):
    n, k, H = int(p[0]), float(p[1]), int(p[2])
    s = pd.Series(LR)
    z = ((s - s.rolling(n).mean()) / s.rolling(n).std()).to_numpy()
    pos = np.zeros_like(CL)
    i, free = 0, 0
    ev = np.flatnonzero(np.abs(z) > k)
    for i in ev:
        if i < free or i >= T - 1:
            continue
        d = -np.sign(z[i])                                  # z>k: ratio high -> short gold, long silver
        end = min(i + H, T - 1)
        wz = z[i + 1:end + 1]
        cond = (np.sign(wz) != np.sign(z[i])) | (np.abs(wz) > k + 2)
        hit = np.flatnonzero(cond)
        ex = i + 1 + int(hit[0]) if len(hit) else end
        pos[i:ex, 0], pos[i:ex, 1] = d, -d
        free = ex
    return run(pos)


HYP = {"N1": ("Time-series momentum on gold and silver (weekly)", n1),
       "N2": ("Gold Asian-session drift (no swap)", n2),
       "N3": ("Gold/silver ratio mean reversion", n3)}
GRIDS = {"N1": [(N,) for N in (20, 60, 120, 180, 260)],
         "N2": [(E, X) for E in (18, 19, 20) for X in (2, 3, 4)],
         "N3": [(n, k, H) for n in (60, 120, 250) for k in (1.5, 2.0, 2.5) for H in (20, 60, 120)]}


def draw(h, rng, n):
    if h == "N1":
        return [(int(x),) for x in rng.integers(20, 261, n)]
    if h == "N2":
        g = GRIDS["N2"]
        return [g[i] for i in rng.integers(0, len(g), n)]
    return list(zip(rng.integers(60, 251, n).tolist(), rng.uniform(1.5, 2.5, n).tolist(), rng.integers(20, 121, n).tolist()))


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print(f"{T} days {IDX[0].date()}..{IDX[-1].date()}")
    res, wf = {}, {}
    for h, (name, fn) in HYP.items():
        R = np.array([fn(p) for p in GRIDS[h]])
        r_wf, chosen, dev = C.walk_forward(R, GRIDS[h], YEAR, WF_YEARS)
        wf[h] = r_wf
        s = np.array([[C.sharpe(x[M_OOS]), C.sharpe(x[M_HOLD]), C.sharpe(x[M_DEV])] for x in (fn(p) for p in draw(h, rng, N_MC))])
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos": C.stats(r_wf[M_OOS]), "holdout": C.stats(r_wf[M_HOLD]), "dev": C.stats(dev[M_DEV]),
                  "target": C.target_check(r_wf[M_OOS]),
                  "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                               "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean()), "frac_dev_sharpe_pos": float((s[:, 2] > 0).mean())}}
        a, tot = C.block_boot(r_wf[M_OOS], rng)
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}
        print(f"{h} done ({time.time()-t0:.0f}s)", flush=True)
    sh = PRIOR + [res[h]["oos"]["sharpe"] for h in HYP]
    for h in HYP:
        res[h]["deflated_sharpe"] = deflated_sharpe(wf[h][M_OOS], N_TRIALS, sh)
        res[h]["criteria"], res[h]["validated"] = C.criteria(res[h], res[h]["deflated_sharpe"]["dsr"] >= 0.95)
    live = M_OOS | M_HOLD
    pd.DataFrame(wf, index=IDX)[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "hypotheses": res}, indent=2, default=float))
    for h, o in res.items():
        t = o["target"]
        print(h, "OOS sh %.2f ann %+.1f%% dd %.0f%% | hold sh %.2f ann %+.1f%% | dev %.2f | pMC %.0f%% med %.2f | Ploss %.0f%% | DSR %.3f | within-limits %s/mo | fails %s" % (
            o["oos"]["sharpe"], o["oos"]["ann_return"] * 100, o["oos"]["max_dd"] * 100, o["holdout"]["sharpe"],
            o["holdout"]["ann_return"] * 100, o["dev"]["sharpe"], o["param_mc"]["frac_oos_sharpe_pos"] * 100,
            o["param_mc"]["median_oos_sharpe"], o["return_mc"]["prob_loss_over_oos"] * 100, o["deflated_sharpe"]["dsr"],
            None if t["monthly_return_within_limits"] is None else round(t["monthly_return_within_limits"] * 100, 2),
            ",".join(k.split("_")[0] for k, v in o["criteria"].items() if not v)))
        print("   chosen:", o["chosen_params"])


if __name__ == "__main__":
    main()
