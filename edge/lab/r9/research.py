"""Strategy lab round 9: P1 pooled ridge-regression model over 18 instruments (FX majors, Scandi/CEE, gold, silver).

See edge/lab/r9/PREREGISTRATION.md. Real HistData bars + TradeStation SPY closes in. Each year's model is trained
only on the trailing 5 years. Fills at the first bar >= 18:30 New York (rollover rule). Random numbers (seed
20261006) only draw hyperparameters and resample real returns.

Run:  python -m edge.lab.r9.research
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
CACHE = DATA / "_cache" / "daily_r9.pkl"
LAST = pd.Timestamp("2026-09-25")
SEED, N_MC, N_TRIALS = 20261006, 10_000, 27
PRIOR = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350,
         -0.900, -0.760, -1.010, -0.840, -0.100, 0.240, -1.370, -0.140, 0.703, -0.260, -0.310, 0.510, -0.360]
MAJ = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
MIN = ["USDNOK", "USDSEK", "USDPLN", "USDHUF", "USDCZK", "EURNOK", "EURSEK", "EURPLN", "EURHUF"]
MET = ["XAUUSD", "XAGUSD"]
INST = MAJ + MIN + MET
NI = len(INST)
TABLE = {"EURUSD": 1.0, "GBPUSD": 1.5, "USDJPY": 1.2, "AUDUSD": 1.3, "USDCAD": 1.8, "USDCHF": 1.8, "NZDUSD": 2.0}


def load():
    if CACHE.exists():
        return pd.read_pickle(CACHE)
    out = {}
    for p in INST:
        df = pd.concat([pd.read_csv(f) for f in sorted((DATA / p).glob("*.csv.gz"))], ignore_index=True)
        ny = pd.to_datetime(df.ts, utc=True).dt.tz_convert("America/New_York")
        df["tday"] = (ny + pd.Timedelta(hours=7)).dt.tz_localize(None).dt.normalize()
        hm = ny.dt.hour * 60 + ny.dt.minute
        # position of the bar within the trading day: minutes since 17:00 NY
        df["since"] = (hm - 17 * 60) % (24 * 60)
        g = df.groupby("tday")
        c = g.bc.last()
        o = df[df.since >= 90].groupby("tday").bo.first()               # first bar at/after 18:30 NY
        d = pd.DataFrame({"o": o, "c": c}).dropna()
        out[p] = d[(d.index.dayofweek < 5) & (d.index <= LAST)]
    pd.to_pickle(out, CACHE)
    return out


RAW = load()
IDX = RAW[INST[0]].index
for p in INST:
    IDX = IDX.intersection(RAW[p].index)
T = len(IDX)
O = np.column_stack([RAW[p].o.reindex(IDX).to_numpy() for p in INST])
CL = np.column_stack([RAW[p].c.reindex(IDX).to_numpy() for p in INST])
YEAR = IDX.year.to_numpy()
spy = pd.read_csv(ROOT / "data" / "tradestation" / "SPY_daily.csv", parse_dates=["date"]).set_index("date").close
SPY = spy.reindex(IDX.union(spy.index)).ffill().reindex(IDX).to_numpy()

# costs per unit |change in weight| per side
cost = np.zeros(NI)
for j, p in enumerate(INST):
    if p in TABLE:
        pip = 0.01 if p.endswith("JPY") else 1e-4
        cost[j] = (TABLE[p] + 0.9) * pip / 2 / np.nanmedian(CL[:, j])
    elif p in MIN:
        cost[j] = 3e-4
    else:
        cost[j] = 1e-4 if p == "XAUUSD" else 2e-4
SWAP = np.array([0.02] * 7 + [0.04] * 9 + [0.03] * 2)

LOGC = np.log(CL)
R1 = np.zeros_like(CL)
R1[1:] = np.diff(LOGC, axis=0)
SD60 = pd.DataFrame(R1).rolling(60).std().to_numpy()
SD10 = pd.DataFrame(R1).rolling(10).std().to_numpy()
with np.errstate(divide="ignore", invalid="ignore"):
    VS = np.nan_to_num(0.10 / (SD60 * np.sqrt(C.ANN)), nan=0.0, posinf=0.0)


def lagret(n):
    out = np.full_like(CL, np.nan)
    out[n:] = LOGC[n:] - LOGC[:-n]
    return out


def feats():
    F = []
    for n in (1, 5, 20, 60, 120, 250):
        F.append(lagret(n) / (SD60 * np.sqrt(n)))
    for n in (20, 60, 200):
        m = pd.DataFrame(CL).rolling(n).mean().to_numpy()
        F.append((CL / m - 1) / SD60)
    F.append(SD10 / SD60)
    usd = lagret(5)
    eurusd5 = usd[:, [0]]
    leg = usd.copy()
    for j, p in enumerate(INST):
        if p.startswith("EUR") and p != "EURUSD":
            leg[:, j] = eurusd5[:, 0]
    F.append(leg / (SD60 * np.sqrt(5)))
    spy5 = np.full(T, np.nan)
    spy5[5:] = np.log(SPY[5:] / SPY[:-5])
    F.append(np.repeat(spy5[:, None], NI, axis=1) / np.nanstd(spy5))
    dow = IDX.dayofweek.to_numpy()
    for d in range(5):
        F.append(np.repeat((dow == d).astype(float)[:, None], NI, axis=1))
    return np.stack(F, axis=2)                                           # T x NI x 17


FE = feats()
NF = FE.shape[2]
_TGT = {}


def target(H):
    if H not in _TGT:
        y = np.full_like(CL, np.nan)
        y[:-H] = (LOGC[H:] - np.log(O[1:T - H + 1])) / SD60[:-H] if H >= 1 else np.nan
        _TGT[H] = y
    return _TGT[H]


def fit_predict(H, lam, q, test_years, train_len=5):
    """Return (T x NI) predictions, NaN outside test years, and per-year thresholds."""
    y = target(H)
    pred = np.full((T, NI), np.nan)
    for ty in test_years:
        start = pd.Timestamp(f"{ty}-01-01")
        tr = (YEAR >= ty - train_len) & (YEAR <= ty - 1)
        tr_idx = np.flatnonzero(tr)
        tr_idx = tr_idx[tr_idx + H < np.searchsorted(IDX, start)]        # target fully known before the test year
        X = FE[tr_idx].reshape(-1, NF)
        Y = y[tr_idx].reshape(-1)
        ok = np.isfinite(X).all(1) & np.isfinite(Y)
        X, Y = X[ok], Y[ok]
        mu, sd = X.mean(0), X.std(0) + 1e-12
        Xs = (X - mu) / sd
        beta = np.linalg.solve(Xs.T @ Xs + lam * np.eye(NF), Xs.T @ (Y - Y.mean()))
        thr = np.quantile(np.abs(Xs @ beta + Y.mean()), q) if q > 0 else 0.0
        te = np.flatnonzero(YEAR == ty)
        Xt = (FE[te] - mu) / sd
        p = Xt @ beta + Y.mean()
        p = np.where(np.abs(p) > thr, p, 0.0)
        pred[te] = p
    return pred


def run(pred, H):
    """Rebalance every H days at the close to sign(pred) x vol size; fills at the next 18:30 open."""
    reb = np.zeros(T, bool)
    first = np.flatnonzero(np.isfinite(pred).any(1))
    if len(first) == 0:
        return np.zeros(T)
    reb[first[0]::H] = True
    last = np.maximum.accumulate(np.where(reb, np.arange(T), 0))
    sig = np.nan_to_num(np.sign(pred))[last] * (np.arange(T) >= first[0])[:, None]
    w = sig * VS
    gap = np.zeros_like(CL)
    gap[1:] = O[1:] / CL[:-1] - 1
    day = CL / O - 1
    hg, hd = np.zeros_like(w), np.zeros_like(w)
    hg[2:], hd[1:] = w[:-2], w[:-1]
    r = hg * gap + hd * day - np.abs(hd - hg) * cost - np.abs(hd) * SWAP / C.ANN
    return np.nan_to_num(r).sum(1) / NI


WF_YEARS = list(range(2017, 2027))


def strat(p, years=WF_YEARS, train_len=5):
    H, lam, q = int(p[0]), float(p[1]), float(p[2])
    return run(fit_predict(H, lam, q, years, train_len), H)


GRID = [(H, lam, q) for H in (1, 5, 10, 20) for lam in (1.0, 10.0, 100.0) for q in (0.0, 0.5, 0.8)]


def mask(a, b):
    return (IDX >= pd.Timestamp(a)) & (IDX <= pd.Timestamp(b))


M_DEV, M_OOS, M_HOLD = mask("2014-01-01", "2016-12-31"), mask("2017-01-01", "2023-12-31"), mask("2024-01-01", LAST)


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    print(f"{T} days {IDX[0].date()}..{IDX[-1].date()}, {NI} instruments, {NF} features", flush=True)
    R = np.array([strat(p) for p in GRID])
    r_wf, chosen, _ = C.walk_forward(R, GRID, YEAR, WF_YEARS)
    dev = np.mean([strat(p, years=[2014, 2015, 2016], train_len=2) for p in set(chosen.values())], axis=0)
    print(f"WF done ({time.time()-t0:.0f}s): OOS {C.sharpe(r_wf[M_OOS]):.2f}", flush=True)
    draws = list(zip(rng.integers(1, 21, N_MC).tolist(), np.exp(rng.uniform(np.log(0.1), np.log(1000), N_MC)).tolist(),
                     rng.uniform(0, 0.8, N_MC).tolist()))
    s = []
    for i, p in enumerate(draws):
        x = strat(p)
        s.append((C.sharpe(x[M_OOS]), C.sharpe(x[M_HOLD])))
        if i % 1000 == 0:
            print(f"  MC {i} ({time.time()-t0:.0f}s)", flush=True)
    s = np.array(s)
    a, tot = C.block_boot(r_wf[M_OOS], rng)
    o = {"name": "Pooled ridge ML, 18 instruments", "chosen_params": {str(y): list(p) for y, p in chosen.items()},
         "oos": C.stats(r_wf[M_OOS]), "holdout": C.stats(r_wf[M_HOLD]), "dev": C.stats(dev[M_DEV]),
         "target": C.target_check(r_wf[M_OOS]),
         "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                      "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean())},
         "return_mc": {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}}
    o["deflated_sharpe"] = deflated_sharpe(r_wf[M_OOS], N_TRIALS, PRIOR + [o["oos"]["sharpe"]])
    o["criteria"], o["validated"] = C.criteria(o, o["deflated_sharpe"]["dsr"] >= 0.95)
    pd.DataFrame({"P1": r_wf}, index=IDX)[M_OOS | M_HOLD].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "P1": o}, indent=2, default=float))
    t = o["target"]
    print("P1 OOS sh %.2f ann %+.1f%% dd %.0f%% | hold sh %.2f ann %+.1f%% | dev %.2f | pMC %.0f%% med %.2f | Ploss %.0f%% | DSR %.3f | within limits %s/mo | fails %s" % (
        o["oos"]["sharpe"], o["oos"]["ann_return"] * 100, o["oos"]["max_dd"] * 100, o["holdout"]["sharpe"],
        o["holdout"]["ann_return"] * 100, o["dev"]["sharpe"], o["param_mc"]["frac_oos_sharpe_pos"] * 100,
        o["param_mc"]["median_oos_sharpe"], o["return_mc"]["prob_loss_over_oos"] * 100, o["deflated_sharpe"]["dsr"],
        None if t["monthly_return_within_limits"] is None else round(t["monthly_return_within_limits"] * 100, 2),
        ",".join(k.split("_")[0] for k, v in o["criteria"].items() if not v)))
    print("chosen:", o["chosen_params"], f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
