"""Pre-registered FX strategy research F1-F5 (see edge/fx/PREREGISTRATION.md).

Real TradeStation daily bars for the 7 USD majors in, statistics out.
Random numbers (seed 20260928) are used ONLY for the two pre-registered Monte Carlo tests:
  * parameter Monte Carlo: 10,000 parameter sets drawn uniformly from each family's range;
  * return Monte Carlo: 10,000 block-bootstrap resamples of REAL realised daily net returns.
No prices or returns are ever generated.

Run:  python -m edge.fx.research
Writes edge/fx/results/*.csv, *.png and summary.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "tradestation"
OUT = Path(__file__).resolve().parent / "results"

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
SPREAD_PIPS = {"EURUSD": 1.0, "USDJPY": 1.2, "GBPUSD": 1.5, "AUDUSD": 1.3,
               "USDCAD": 1.8, "USDCHF": 1.8, "NZDUSD": 2.0}
EXTRA_PIPS = 0.5 + 0.4                      # commission + slippage, per round turn
CCY_SIGN = np.array([1, 1, -1, 1, -1, -1, 1], dtype=float)  # +1: XXXUSD, -1: USDXXX

LAST_DATE = pd.Timestamp("2026-09-25")      # later bars are partial / after the cut-off
DEV = (pd.Timestamp("2008-01-01"), pd.Timestamp("2016-12-31"))   # 2007 = warm-up only
OOS = (pd.Timestamp("2017-01-01"), pd.Timestamp("2023-12-31"))
HOLD = (pd.Timestamp("2024-01-01"), LAST_DATE)
WF_YEARS = list(range(2017, 2027))          # 2017-2023 validation, 2024-2026 holdout
TRAIN_YEARS = 5

TARGET_VOL = 0.10
VOL_WIN = 60
SEED = 20260928
N_PARAM_MC = 10_000
N_BOOT = 10_000
BLOCK = 20
SWAP_PER_YEAR = 0.02                        # sensitivity only
ANN = 252
MAX_STRAT_SCALE = 4.0                      # cap on the strategy-level vol multiplier (see scale_to_vol)


# ---------------------------------------------------------------- data

def load() -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    frames = []
    for p in PAIRS:
        d = pd.read_csv(DATA / f"{p}_daily.csv", parse_dates=["date"]).set_index("date")
        frames.append(d[["open", "close"]].add_prefix(p + "_"))
    df = pd.concat(frames, axis=1, join="inner").sort_index()
    df = df[df.index <= LAST_DATE]
    O = df[[p + "_open" for p in PAIRS]].to_numpy(float)
    C = df[[p + "_close" for p in PAIRS]].to_numpy(float)
    return df.index, O, C


IDX, O, C = load()
T = len(IDX)
PIP = np.array([0.01 if "JPY" in p else 0.0001 for p in PAIRS])
RT_PIPS = np.array([SPREAD_PIPS[p] + EXTRA_PIPS for p in PAIRS])
COST_FRAC = RT_PIPS * PIP / 2.0 / O          # cost per unit of |change in weight| (half a round turn)
GAP_RET = np.zeros_like(C)                   # close(t-1) -> open(t)
GAP_RET[1:] = O[1:] / C[:-1] - 1
DAY_RET = C / O - 1                          # open(t) -> close(t)
CC_RET = np.zeros_like(C)
CC_RET[1:] = C[1:] / C[:-1] - 1
_sd = pd.DataFrame(CC_RET).rolling(VOL_WIN).std().to_numpy()
VOL_SCALE = np.nan_to_num(TARGET_VOL / (_sd * np.sqrt(ANN)), nan=0.0, posinf=0.0)  # known at close t
CSUM = np.vstack([np.zeros((1, 7)), np.cumsum(C, axis=0)])
CSUM2 = np.vstack([np.zeros((1, 7)), np.cumsum(C * C, axis=0)])
TI = np.arange(T)[:, None]


def mask(a, b):
    return ((IDX >= a) & (IDX <= b))


M_DEV, M_OOS, M_HOLD = mask(*DEV), mask(*OOS), mask(*HOLD)


def sma(n: int) -> np.ndarray:
    out = np.full_like(C, np.nan)
    out[n - 1:] = (CSUM[n:] - CSUM[:-n]) / n
    return out


def rstd(n: int) -> np.ndarray:
    out = np.full_like(C, np.nan)
    s, s2 = CSUM[n:] - CSUM[:-n], CSUM2[n:] - CSUM2[:-n]
    var = (s2 - s * s / n) / (n - 1)
    out[n - 1:] = np.sqrt(np.maximum(var, 0))
    return out


def nret(n: int) -> np.ndarray:
    out = np.full_like(C, np.nan)
    out[n:] = C[n:] / C[:-n] - 1
    return out


_ROLL = {}


def roll_ext(n: int) -> tuple[np.ndarray, np.ndarray]:
    """max / min of the n closes BEFORE t (so a breakout compares today with the prior window)."""
    if n not in _ROLL:
        df = pd.DataFrame(C)
        _ROLL[n] = (df.rolling(n).max().shift(1).to_numpy(), df.rolling(n).min().shift(1).to_numpy())
    return _ROLL[n]


# ---------------------------------------------------------------- engine

def state_machine(long_in, short_in, exit_long, exit_short) -> np.ndarray:
    """Vectorised position state from entry/exit events (entries of opposite sides never coincide)."""
    ent = long_in | short_in
    le = np.maximum.accumulate(np.where(ent, TI, -1), axis=0)
    d = np.where(long_in, 1, -1)
    d_last = np.take_along_axis(d, np.maximum(le, 0), axis=0)
    xl = np.maximum.accumulate(np.where(exit_long, TI, -1), axis=0)
    xs = np.maximum.accumulate(np.where(exit_short, TI, -1), axis=0)
    pos = np.where((le >= 0) & (d_last == 1) & (le > xl), 1.0, 0.0)
    pos = np.where((le >= 0) & (d_last == -1) & (le > xs), -1.0, pos)
    return pos


def hold_every(w: np.ndarray, rebal: np.ndarray) -> np.ndarray:
    """Keep weights fixed between rebalance days (rebal: bool per row)."""
    last = np.maximum.accumulate(np.where(rebal, np.arange(T), 0))
    return w[last]


WEEK_END = np.r_[IDX[1:].isocalendar().week.to_numpy() != IDX[:-1].isocalendar().week.to_numpy(), True]


def signal(fam: str, p: tuple) -> np.ndarray:
    """Target weights decided at the close of each day (T x 7), vol-scaled."""
    if fam == "F1":
        f, s = p
        a, b = sma(f), sma(s)
        sig = np.where(np.isnan(b), 0.0, np.where(a > b, 1.0, -1.0))
        return sig * VOL_SCALE
    if fam == "F2":
        (n,) = p
        r = nret(n)
        w = np.nan_to_num(np.sign(r)) * VOL_SCALE
        return hold_every(w, WEEK_END)
    if fam == "F3":
        n, m = p
        hi_n, lo_n = roll_ext(n)
        hi_m, lo_m = roll_ext(m)
        sig = state_machine(C > hi_n, C < lo_n, C < lo_m, C > hi_m)
        return sig * VOL_SCALE
    if fam == "F4":
        n, h = p
        strength = nret(n) * CCY_SIGN
        ok = ~np.isnan(strength).any(axis=1)
        rank = np.argsort(np.argsort(np.nan_to_num(strength), axis=1), axis=1)  # 0 = weakest
        ccy = np.where(rank >= 5, 1.0, np.where(rank <= 1, -1.0, 0.0)) * ok[:, None]
        w = ccy * CCY_SIGN * VOL_SCALE
        first = int(np.argmax(ok))
        rebal = np.zeros(T, bool)
        rebal[first::h] = True
        return hold_every(w, rebal)
    if fam == "F5":
        n, k = p
        z = (C - sma(n)) / rstd(n)
        sig = state_machine(z < -k, z > k, z >= 0, z <= 0)
        return sig * VOL_SCALE
    raise ValueError(fam)


def run(w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Daily net return of the equal-risk pair average, and gross exposure. Signal at close t, fill at open t+1."""
    held_gap = np.zeros_like(w)    # position over close(t-1)->open(t): decided at close t-2
    held_day = np.zeros_like(w)    # position over open(t)->close(t):  decided at close t-1
    held_gap[2:] = w[:-2]
    held_day[1:] = w[:-1]
    r = held_gap * GAP_RET + held_day * DAY_RET - np.abs(held_day - held_gap) * COST_FRAC
    return r.mean(axis=1), np.abs(held_day).sum(axis=1) / 7


def strat(fam, p):
    return run(signal(fam, p))


# ---------------------------------------------------------------- stats

def sharpe(r):
    r = r[np.isfinite(r)]
    s = r.std(ddof=1)
    return float(r.mean() / s * np.sqrt(ANN)) if s > 0 else 0.0


def ann_ret(r):
    return float(np.prod(1 + r) ** (ANN / len(r)) - 1)


def max_dd(r):
    eq = np.cumprod(1 + r)
    return float((eq / np.maximum.accumulate(eq) - 1).min())


def stats(r):
    return {"ann_return": ann_ret(r), "ann_vol": float(r.std(ddof=1) * np.sqrt(ANN)),
            "sharpe": sharpe(r), "max_dd": max_dd(r), "total_return": float(np.prod(1 + r) - 1)}


# ---------------------------------------------------------------- walk-forward

GRIDS = {
    "F1": [(f, s) for f in (5, 10, 20, 30, 50, 75, 100) for s in (50, 75, 100, 150, 200, 250, 300) if f < s / 1.5],
    "F2": [(n,) for n in (20, 40, 60, 90, 120, 180, 260)],
    "F3": [(n, m) for n in (20, 40, 55, 80, 100, 120) for m in sorted({max(10, n // 4), max(10, n // 2), n})],
    "F4": [(n, h) for n in (20, 60, 120, 180, 260) for h in (5, 10, 21)],
    "F5": [(n, k) for n in (5, 10, 20, 30, 40) for k in (1.0, 1.5, 2.0, 2.5)],
}
FAMS = list(GRIDS)
NAMES = {"F1": "MA trend", "F2": "TS momentum", "F3": "Donchian breakout",
         "F4": "Cross-sectional momentum", "F5": "Mean reversion (z-score)"}
YEAR = IDX.year.to_numpy()


def walk_forward(fam):
    grid = GRIDS[fam]
    res = [strat(fam, p) for p in grid]
    R = np.array([x[0] for x in res])
    G = np.array([x[1] for x in res])
    r_wf, g_wf = np.full(T, np.nan), np.full(T, np.nan)
    chosen = {}
    for y in WF_YEARS:
        tr = (YEAR >= y - TRAIN_YEARS) & (YEAR <= y - 1)
        best = int(np.argmax([sharpe(R[i, tr]) for i in range(len(grid))]))
        chosen[y] = grid[best]
        te = YEAR == y
        r_wf[te], g_wf[te] = R[best, te], G[best, te]
        if y == WF_YEARS[0]:     # 2016 filled with the 2017 choice: used ONLY to warm up portfolio vol scaling
            pre = YEAR == y - 1
            r_wf[pre], g_wf[pre] = R[best, pre], G[best, pre]
    # criterion 4: the chosen parameter sets, blended equally, over the development period
    dev_blend = np.mean([R[grid.index(p)] for p in chosen.values()], axis=0)
    return r_wf, g_wf, chosen, dev_blend


# ---------------------------------------------------------------- Monte Carlo

def draw_params(fam, rng, n):
    out = []
    if fam == "F1":
        while len(out) < n:
            f, s = int(rng.integers(5, 101)), int(rng.integers(50, 301))
            if f < s / 1.5:
                out.append((f, s))
    elif fam == "F2":
        out = [(int(x),) for x in rng.integers(20, 261, n)]
    elif fam == "F3":
        for _ in range(n):
            N = int(rng.integers(20, 121))
            out.append((N, int(rng.integers(10, N + 1))))
    elif fam == "F4":
        out = list(zip(rng.integers(20, 261, n).tolist(), rng.integers(5, 22, n).tolist()))
    elif fam == "F5":
        out = list(zip(rng.integers(5, 41, n).tolist(), rng.uniform(1.0, 2.5, n).tolist()))
    return out


def block_boot(r, rng, n_boot=N_BOOT, block=BLOCK):
    """Moving-block bootstrap of real returns: annualised return and total return of each resample."""
    L = len(r)
    nb = int(np.ceil(L / block))
    starts = rng.integers(0, L - block + 1, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :L]
    lr = np.log1p(r)[idx].sum(axis=1)
    return np.expm1(lr * ANN / L), np.expm1(lr), idx


def scale_to_vol(r):
    """Scale a daily return stream to 10% vol using trailing 60-day stdev known the day before.

    Implementation choice (not in the pre-registration): the multiplier is capped at MAX_STRAT_SCALE, because a
    strategy that was nearly flat for 60 days (e.g. F5 with a high k) otherwise gets an unbounded multiplier.
    """
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
    summary = {"data": {"pairs": PAIRS, "first": str(IDX[0].date()), "last": str(IDX[-1].date()), "bars": T}}
    wf, fam_res = {}, {}

    # 1) walk-forward + criteria 1 and 4
    for fam in FAMS:
        r_wf, g_wf, chosen, dev_blend = walk_forward(fam)
        wf[fam] = (r_wf, g_wf)
        oos, hold = r_wf[M_OOS], r_wf[M_HOLD]
        fam_res[fam] = {
            "name": NAMES[fam],
            "chosen_params": {str(y): list(p) for y, p in chosen.items()},
            "oos_2017_2023": stats(oos),
            "oos_swap_adjusted_ann_return": ann_ret(oos) - SWAP_PER_YEAR * float(np.mean(g_wf[M_OOS])),
            "avg_gross_exposure_oos": float(np.mean(g_wf[M_OOS])),
            "holdout_2024_2026": stats(hold),
            "dev_2008_2016_chosen_blend": stats(dev_blend[M_DEV]),
        }
        print(f"{fam} walk-forward done ({time.time()-t0:.0f}s): OOS Sharpe {fam_res[fam]['oos_2017_2023']['sharpe']:.2f}")

    # 2) parameter Monte Carlo, 10,000 sets per family
    mc_rows = []
    for fam in FAMS:
        sets = draw_params(fam, rng, N_PARAM_MC)
        for i, p in enumerate(sets):
            r, _ = strat(fam, p)
            mc_rows.append({"family": fam, "i": i, "p1": p[0], "p2": p[1] if len(p) > 1 else np.nan,
                            "oos_sharpe": sharpe(r[M_OOS]), "oos_ann_return": ann_ret(r[M_OOS]),
                            "hold_sharpe": sharpe(r[M_HOLD]), "dev_sharpe": sharpe(r[M_DEV])})
        print(f"{fam} param MC done ({time.time()-t0:.0f}s)")
    mc = pd.DataFrame(mc_rows)
    mc.to_csv(OUT / "param_mc.csv", index=False, float_format="%.5f")
    for fam in FAMS:
        s = mc[mc.family == fam]
        fam_res[fam]["param_mc"] = {
            "n": len(s), "frac_oos_sharpe_pos": float((s.oos_sharpe > 0).mean()),
            "median_oos_sharpe": float(s.oos_sharpe.median()),
            "p05_oos_sharpe": float(s.oos_sharpe.quantile(.05)), "p95_oos_sharpe": float(s.oos_sharpe.quantile(.95)),
            "frac_hold_sharpe_pos": float((s.hold_sharpe > 0).mean()),
            "median_hold_sharpe": float(s.hold_sharpe.median()),
            "frac_dev_sharpe_pos": float((s.dev_sharpe > 0).mean()),
        }

    # 3) return Monte Carlo on the real walk-forward OOS returns
    boots = {}
    for fam in FAMS:
        a, tot, _ = block_boot(wf[fam][0][M_OOS], rng)
        boots[fam] = a
        fam_res[fam]["return_mc"] = {"n": N_BOOT, "block": BLOCK, "p05_ann_return": float(np.percentile(a, 5)),
                                     "median_ann_return": float(np.median(a)),
                                     "p95_ann_return": float(np.percentile(a, 95)),
                                     "prob_loss_over_oos": float((tot < 0).mean())}

    # verdicts
    for fam in FAMS:
        f = fam_res[fam]
        c = {"c1_wf_oos_sharpe>=0.3_and_ret>0": f["oos_2017_2023"]["sharpe"] >= 0.3 and f["oos_2017_2023"]["total_return"] > 0,
             "c2_param_mc_>=60%_pos_and_median>0": f["param_mc"]["frac_oos_sharpe_pos"] >= 0.6 and f["param_mc"]["median_oos_sharpe"] > 0,
             "c3_return_mc_prob_loss<20%": f["return_mc"]["prob_loss_over_oos"] < 0.2,
             "c4_dev_sharpe>0": f["dev_2008_2016_chosen_blend"]["sharpe"] > 0}
        f["criteria"] = c
        f["validated"] = all(c.values())
    validated = [f for f in FAMS if fam_res[f]["validated"]]
    summary["families"] = fam_res
    summary["validated"] = validated

    # 4) portfolio: equal risk across validated families (all 5 shown too, labelled non-tradable if none validate)
    port_fams = validated if validated else FAMS
    live = M_OOS | M_HOLD
    scaled = {}
    for fam in port_fams:
        s, k = scale_to_vol(np.nan_to_num(wf[fam][0]))
        scaled[fam] = (s, k)
    port = np.mean([scaled[f][0] for f in port_fams], axis=0)
    port_gross = np.mean([scaled[f][1] * np.nan_to_num(wf[f][1]) for f in port_fams], axis=0)
    pr = port[live]
    summary["portfolio"] = {
        "families": port_fams, "tradable": bool(validated),
        "oos_2017_2023": stats(port[M_OOS]), "holdout_2024_2026": stats(port[M_HOLD]),
        "full_2017_2026": stats(pr),
        "swap_adjusted_ann_return_full": ann_ret(pr) - SWAP_PER_YEAR * float(np.mean(port_gross[live])),
        "avg_gross_exposure": float(np.mean(port_gross[live])),
        "calendar_years": {str(y): float(np.prod(1 + port[live & (YEAR == y)]) - 1) for y in WF_YEARS},
    }
    a, tot, idx = block_boot(pr, rng)
    summary["portfolio"]["return_mc_full"] = {
        "n": N_BOOT, "p05_ann_return": float(np.percentile(a, 5)), "median_ann_return": float(np.median(a)),
        "p95_ann_return": float(np.percentile(a, 95)), "prob_loss": float((tot < 0).mean())}
    boot_paths = np.cumprod(1 + pr[idx], axis=1)  # resampled REAL returns

    # portfolio parameter MC: portfolio built from the i-th random set of each included family
    pm = []
    draws = {f: mc[mc.family == f] for f in port_fams}
    for i in range(N_PARAM_MC):
        rs = []
        for f in port_fams:
            row = draws[f].iloc[i]
            p = (int(row.p1),) if f == "F2" else ((int(row.p1), float(row.p2)) if f == "F5" else (int(row.p1), int(row.p2)))
            rs.append(scale_to_vol(strat(f, p)[0])[0])
        rp = np.mean(rs, axis=0)
        pm.append((sharpe(rp[M_OOS]), sharpe(rp[M_HOLD]), ann_ret(rp[live])))
        if i % 2000 == 0:
            print(f"portfolio param MC {i} ({time.time()-t0:.0f}s)")
    pm = np.array(pm)
    pd.DataFrame(pm, columns=["oos_sharpe", "hold_sharpe", "ann_return_2017_2026"]).to_csv(
        OUT / "portfolio_param_mc.csv", index=False, float_format="%.5f")
    summary["portfolio"]["param_mc"] = {
        "n": N_PARAM_MC, "frac_oos_sharpe_pos": float((pm[:, 0] > 0).mean()), "median_oos_sharpe": float(np.median(pm[:, 0])),
        "frac_hold_sharpe_pos": float((pm[:, 1] > 0).mean()), "median_hold_sharpe": float(np.median(pm[:, 1])),
        "p05_ann_return": float(np.percentile(pm[:, 2], 5)), "median_ann_return": float(np.median(pm[:, 2])),
        "p95_ann_return": float(np.percentile(pm[:, 2], 95))}

    # outputs
    df = pd.DataFrame({f: wf[f][0] for f in FAMS}, index=IDX)
    df["portfolio"] = port
    df[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    charts(df[live], mc, pm, boot_paths, boots, summary)
    print(json.dumps({f: {"validated": fam_res[f]["validated"], **fam_res[f]["criteria"]} for f in FAMS}, indent=1))
    print(json.dumps(summary["portfolio"], indent=1, default=float))
    print(f"done in {time.time()-t0:.0f}s")


def charts(df, mc, pm, boot_paths, boots, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    port = summary["portfolio"]
    tag = "validated" if port["tradable"] else "NOT validated - shown for information"
    # 1) portfolio curve
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for f in FAMS:
        ax[0].plot(df.index, np.cumprod(1 + df[f].fillna(0)), lw=0.8, alpha=0.6, label=f"{f} {NAMES[f]}")
    eq = np.cumprod(1 + df["portfolio"])
    ax[0].plot(df.index, eq, color="k", lw=2, label=f"Portfolio ({'+'.join(port['families'])})")
    for a in ax:
        a.axvspan(HOLD[0], HOLD[1], color="orange", alpha=0.12)
    ax[0].text(HOLD[0], ax[0].get_ylim()[1] * 0.97, " holdout", va="top")
    ax[0].set_title(f"FX walk-forward equity (net of costs, out-of-sample 2017-2026) - portfolio {tag}")
    ax[0].set_ylabel("growth of 1")
    ax[0].legend(fontsize=8, loc="upper left")
    ax[0].grid(alpha=0.3)
    ax[1].fill_between(df.index, eq / np.maximum.accumulate(eq) - 1, 0, color="firebrick", alpha=0.5)
    ax[1].set_ylabel("drawdown")
    ax[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "portfolio_curve.png", dpi=120)
    plt.close(fig)

    # 2) parameter Monte Carlo
    fig, axs = plt.subplots(2, 3, figsize=(15, 8))
    for a, f in zip(axs.flat, FAMS):
        s = mc[mc.family == f]
        a.hist(s.oos_sharpe, bins=60, color="steelblue", alpha=0.8, label="OOS 2017-23")
        a.hist(s.hold_sharpe, bins=60, color="orange", alpha=0.5, label="holdout 24-26")
        a.axvline(0, color="k", lw=1)
        pm_ = summary["families"][f]["param_mc"]
        a.set_title(f"{f} {NAMES[f]}\n{pm_['frac_oos_sharpe_pos']:.0%} of 10,000 sets OOS Sharpe>0, median {pm_['median_oos_sharpe']:.2f}", fontsize=9)
        a.legend(fontsize=7)
    a = axs.flat[5]
    a.hist(pm[:, 0], bins=60, color="k", alpha=0.7, label="OOS 2017-23")
    a.hist(pm[:, 1], bins=60, color="orange", alpha=0.5, label="holdout 24-26")
    a.axvline(0, color="r", lw=1)
    a.set_title(f"Portfolio, 10,000 random parameter sets\n{(pm[:,0]>0).mean():.0%} OOS Sharpe>0, median {np.median(pm[:,0]):.2f}", fontsize=9)
    a.legend(fontsize=7)
    fig.suptitle("Parameter Monte Carlo: net Sharpe of 10,000 random parameter sets per family (seed 20260928)")
    fig.tight_layout()
    fig.savefig(OUT / "param_mc.png", dpi=120)
    plt.close(fig)

    # 3) return Monte Carlo (block bootstrap of the real portfolio returns)
    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
    x = np.arange(boot_paths.shape[1]) / ANN
    for q, al in ((5, .15), (25, .3)):
        ax[0].fill_between(x, np.percentile(boot_paths, q, axis=0), np.percentile(boot_paths, 100 - q, axis=0),
                           color="steelblue", alpha=al, label=f"{q}-{100-q}th pct")
    ax[0].plot(x, np.median(boot_paths, axis=0), color="steelblue", label="median resample")
    ax[0].plot(x, np.cumprod(1 + df["portfolio"].to_numpy()), color="k", lw=1.5, label="actual")
    ax[0].axhline(1, color="grey", lw=0.8)
    ax[0].set_xlabel("years")
    ax[0].set_ylabel("growth of 1")
    ax[0].set_title("Portfolio: 10,000 block-bootstrap resamples (20-day blocks) of real 2017-2026 daily returns")
    ax[0].legend(fontsize=8)
    for f in FAMS:
        ax[1].hist(boots[f], bins=80, histtype="step", lw=1.2, label=f"{f} {NAMES[f]}")
    ax[1].axvline(0, color="k")
    ax[1].set_title("Return MC per family: annualised return of resampled OOS 2017-2023")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "return_mc.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
