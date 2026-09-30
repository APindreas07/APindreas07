"""Strategy lab round 7: gotobi Tokyo-fix effect on USDJPY (M1 buy before the 09:55 fix, M2 fade after it).

See edge/lab/r7/PREREGISTRATION.md. Real HistData USDJPY 5-minute bars (round-3 cache) in. Random numbers
(seed 20261004) only draw parameter settings and resample real returns.

Run:  python -m edge.lab.r7.research
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from edge.lab import common as C
from edge.lab.dsr import deflated_sharpe

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results"
SEED, N_MC, N_TRIALS = 20261004, 10_000, 23
PRIOR_FX = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132, -2.140, -0.940, -3.360, -0.350,
            -0.900, -0.760, -1.010, -0.840, -0.100, 0.240, -1.370, -0.140]
PIP, TABLE, EXTRA = 0.01, 1.2, 0.45
LAST = pd.Timestamp("2026-09-25")
WF_YEARS = list(range(2017, 2027))

df = pd.read_pickle(ROOT / "data" / "histdata" / "_cache" / "USDJPY.pkl")
tk = df.ts.dt.tz_convert("Asia/Tokyo")
df["day"] = tk.dt.tz_localize(None).dt.normalize()
df["slot"] = (tk.dt.hour * 60 + tk.dt.minute) // 5
df = df[(df.day.dt.dayofweek < 5) & (df.day <= LAST)]
DAYS = pd.DatetimeIndex(sorted(df.day.unique()))
ND = len(DAYS)
di = pd.Series(np.arange(ND), index=DAYS).reindex(df.day).to_numpy()
G = {k: np.full((ND, 288), np.nan) for k in ("bo", "bc")}
for k in G:
    G[k][di, df.slot.to_numpy()] = df[k].to_numpy()
G["ao"] = G["bo"] + TABLE * PIP
YEAR = DAYS.year.to_numpy()

# vol scale from the last close of each Tokyo day, known the day before
close = pd.Series(pd.DataFrame(G["bc"]).ffill(axis=1).iloc[:, -1].to_numpy(), index=DAYS)
sd = close.pct_change(fill_method=None).rolling(60).std().shift(1).to_numpy()
with np.errstate(divide="ignore", invalid="ignore"):
    W = np.nan_to_num(0.10 / (sd * np.sqrt(C.ANN)), nan=0.0, posinf=0.0)


def gotobi_flags():
    cal = pd.date_range(DAYS[0], DAYS[-1])
    last_dom = cal + pd.offsets.MonthEnd(0)
    hit = cal.day.isin([5, 10, 15, 20, 25, 30]) | ((cal == last_dom) & (last_dom.day < 30))
    g = set()
    for d in cal[hit]:
        while d.dayofweek >= 5:
            d -= pd.Timedelta(days=1)
        g.add(d)
    return np.array([d in g for d in DAYS])


GOTOBI = gotobi_flags()


def slot(h, m):
    return (h * 60 + m) // 5


def trade(s_in, s_out, direction):
    bi, ai, bx, ax = G["bo"][:, s_in], G["ao"][:, s_in], G["bo"][:, s_out], G["ao"][:, s_out]
    r = (bx - ai) / ai if direction > 0 else (bi - ax) / bi
    r = r - EXTRA * PIP * (2 / ((ai + bi) / 2))
    return np.nan_to_num(r)


def m1(p, days=None):
    e = float(p[0])
    r = trade(slot(int(e), int(round((e % 1) * 60))), slot(9, 55), +1)
    return np.where(GOTOBI if days is None else days, r * W, 0.0)


def m2(p, days=None):
    x = float(p[0])
    r = trade(slot(10, 0), slot(int(x), int(round((x % 1) * 60))), -1)
    return np.where(GOTOBI if days is None else days, r * W, 0.0)


HYP = {"M1": ("Gotobi: buy USDJPY before the 09:55 Tokyo fix", m1, [7.0, 7.5, 8.0, 8.5, 9.0, 9.5]),
       "M2": ("Gotobi: fade USDJPY after the fix", m2, [10.5 + 0.5 * i for i in range(10)])}


def mask(a, b):
    return (DAYS >= pd.Timestamp(a)) & (DAYS <= pd.Timestamp(b))


M_DEV, M_OOS, M_HOLD = mask("2012-01-01", "2016-12-31"), mask("2017-01-01", "2023-12-31"), mask("2024-01-01", LAST)


def main():
    OUT.mkdir(exist_ok=True)
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    print(f"{ND} Tokyo days {DAYS[0].date()}..{DAYS[-1].date()}, gotobi days {int(GOTOBI.sum())}")
    for h, (name, fn, vals) in HYP.items():
        grid = [(v,) for v in vals]
        R = np.array([fn(p) for p in grid])
        r_wf, chosen, dev = C.walk_forward(R, grid, YEAR, WF_YEARS)
        wf[h] = r_wf
        draws = rng.choice(len(grid), N_MC)
        s = np.array([[C.sharpe(R[i][M_OOS]), C.sharpe(R[i][M_HOLD]), C.sharpe(R[i][M_DEV])] for i in draws])
        def gross(v):
            vs = slot(int(v), int(round((v % 1) * 60)))
            s_in, s_out, d = (vs, slot(9, 55), 1) if h == "M1" else (slot(10, 0), vs, -1)
            mv = d * (G["bo"][:, s_out] - G["bo"][:, s_in]) / PIP           # mid-to-mid move, spread excluded
            return float(np.nanmean(mv[GOTOBI & M_OOS]))
        gross_pips = [gross(v) for v in vals]
        ctrl = C.sharpe(fn(grid[len(grid) // 2], ~GOTOBI)[M_OOS])
        res[h] = {"name": name, "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos": C.stats(r_wf[M_OOS]), "holdout": C.stats(r_wf[M_HOLD]), "dev": C.stats(dev[M_DEV]),
                  "target": C.target_check(r_wf[M_OOS]),
                  "param_mc": {"frac_oos_sharpe_pos": float((s[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(s[:, 0])),
                               "frac_hold_sharpe_pos": float((s[:, 1] > 0).mean())},
                  "approx_gross_pips_per_trade_oos_by_setting": dict(zip(map(str, vals), gross_pips)),
                  "control_non_gotobi_oos_sharpe": ctrl}
        a, tot = C.block_boot(r_wf[M_OOS], rng)
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "prob_loss_over_oos": float((tot < 0).mean())}
    sharpes = PRIOR_FX + [res[h]["oos"]["sharpe"] for h in HYP]
    for h in HYP:
        res[h]["deflated_sharpe"] = deflated_sharpe(wf[h][M_OOS], N_TRIALS, sharpes)
        res[h]["criteria"], res[h]["validated"] = C.criteria(res[h], res[h]["deflated_sharpe"]["dsr"] >= 0.95)
    (OUT / "summary.json").write_text(json.dumps({"n_trials_for_dsr": N_TRIALS, "hypotheses": res}, indent=2, default=float))
    for h, o in res.items():
        print(h, "OOS sh %.2f ann %+.2f%% | hold %.2f | dev %.2f | pMC %.0f%% | Ploss %.0f%% | DSR %.3f | ctrl %.2f | fails %s" % (
            o["oos"]["sharpe"], o["oos"]["ann_return"] * 100, o["holdout"]["sharpe"], o["dev"]["sharpe"],
            o["param_mc"]["frac_oos_sharpe_pos"] * 100, o["return_mc"]["prob_loss_over_oos"] * 100,
            o["deflated_sharpe"]["dsr"], o["control_non_gotobi_oos_sharpe"],
            ",".join(k.split("_")[0] for k, v in o["criteria"].items() if not v)))
        print("   gross pips/trade OOS:", {k: round(v, 2) for k, v in o["approx_gross_pips_per_trade_oos_by_setting"].items()})


if __name__ == "__main__":
    main()
