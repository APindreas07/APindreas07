"""Shared statistics for strategy-lab rounds: Sharpe, drawdown, target check, block bootstrap, walk-forward.

Everything operates on arrays of REAL realised daily net returns; random numbers are used only in block_boot
(resampling real returns) and by callers drawing parameter sets.
"""
from __future__ import annotations

import numpy as np

ANN = 252
TARGET_ANNUAL = 1.02 ** 12 - 1          # 2% a month compounded = 26.8% a year
MAX_LEV, MAX_DD = 5.0, -0.10            # owner's conservative limits (edge/lab/deploy/risk.py)


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
    a = ann_ret(r)
    return {"ann_return": a, "monthly_return": (1 + a) ** (1 / 12) - 1, "ann_vol": float(r.std(ddof=1) * np.sqrt(ANN)),
            "sharpe": sharpe(r), "max_dd": max_dd(r), "total_return": float(np.prod(1 + r) - 1)}


def _solve(f, lo=0.0, hi=50.0):
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) else (lo, mid)
    return lo, hi


def target_check(r):
    """Criterion 5: the 26.8%/yr leverage must be <= 5x with OOS max drawdown <= 10%. Also reports what fits the limits."""
    a = ann_ret(r)
    out = {"oos_sharpe": sharpe(r), "leverage_for_2pct_month": None, "max_dd_at_that_leverage": None}
    if a > 0:
        _, L = _solve(lambda x: ann_ret(r * x) < TARGET_ANNUAL)
        out.update({"leverage_for_2pct_month": L, "max_dd_at_that_leverage": max_dd(r * L)})
    lev, _ = _solve(lambda x: max_dd(r * x) > MAX_DD)
    lev = min(lev, MAX_LEV)
    out["leverage_within_limits"] = lev
    out["monthly_return_within_limits"] = (1 + ann_ret(r * lev)) ** (1 / 12) - 1 if a > 0 else None
    out["target_reachable"] = bool(a > 0 and out["leverage_for_2pct_month"] <= MAX_LEV
                                   and out["max_dd_at_that_leverage"] >= MAX_DD)
    return out


def block_boot(r, rng, n_boot=10_000, block=20):
    L = len(r)
    nb = int(np.ceil(L / block))
    starts = rng.integers(0, L - block + 1, size=(n_boot, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_boot, -1)[:, :L]
    lr = np.log1p(r)[idx].sum(axis=1)
    return np.expm1(lr * ANN / L), np.expm1(lr)


def walk_forward(R, grid, years, wf_years, train_years=5):
    """R: (n_sets x T) daily returns for each grid set. Re-choose the best trailing-Sharpe set every January."""
    r_wf, chosen = np.full(R.shape[1], np.nan), {}
    for y in wf_years:
        tr = (years >= y - train_years) & (years <= y - 1)
        best = int(np.argmax([sharpe(R[i, tr]) for i in range(len(grid))]))
        chosen[y] = grid[best]
        r_wf[years == y] = R[best, years == y]
    dev = np.mean([R[grid.index(p)] for p in chosen.values()], axis=0)
    return r_wf, chosen, dev


def criteria(o, n_trials_dsr_ok):
    c = {"c1_oos_sharpe>=0.3_and_ret>0": o["oos"]["sharpe"] >= 0.3 and o["oos"]["total_return"] > 0,
         "c2_param_mc_>=60%_pos_and_median>0": o["param_mc"]["frac_oos_sharpe_pos"] >= 0.6 and o["param_mc"]["median_oos_sharpe"] > 0,
         "c3_return_mc_prob_loss<20%": o["return_mc"]["prob_loss_over_oos"] < 0.2,
         "c4_dev_sharpe>0": o["dev"]["sharpe"] > 0,
         "c5_2pct_month_within_limits": o["target"]["target_reachable"],
         "c6_deflated_sharpe>=0.95": n_trials_dsr_ok}
    return c, all(c.values())
