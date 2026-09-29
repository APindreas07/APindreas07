"""Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014) - corrects a Sharpe ratio for the number of trials.

Every strategy the lab has ever tested counts as a trial (see edge/lab/LEDGER.md). The more trials, the higher the
Sharpe a winner needs before it is believed. Stdlib only.

    from edge.lab.dsr import deflated_sharpe
    dsr = deflated_sharpe(daily_returns, n_trials=..., trial_sharpes_annual=[...])
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

_N = NormalDist()
EULER_GAMMA = 0.5772156649015329
ANN = 252


def expected_max_sharpe(n_trials: int, var_sharpe: float) -> float:
    """Expected maximum of n_trials Sharpe estimates under the null (per-period units)."""
    if n_trials < 2:
        return 0.0
    a = _N.inv_cdf(1 - 1 / n_trials)
    b = _N.inv_cdf(1 - 1 / (n_trials * math.e))
    return math.sqrt(var_sharpe) * ((1 - EULER_GAMMA) * a + EULER_GAMMA * b)


def deflated_sharpe(returns, n_trials: int, trial_sharpes_annual) -> dict:
    """Probability that the true Sharpe is > 0 after correcting for n_trials. Pass criterion: dsr >= 0.95."""
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    T = len(r)
    sr = r.mean() / r.std(ddof=1)                       # per-period
    skew = float(((r - r.mean()) ** 3).mean() / r.std() ** 3)
    kurt = float(((r - r.mean()) ** 4).mean() / r.std() ** 4)
    per = np.asarray(trial_sharpes_annual, float) / math.sqrt(ANN)
    var_sr = float(per.var(ddof=1)) if len(per) > 1 else 0.0
    sr0 = expected_max_sharpe(n_trials, var_sr)
    denom = math.sqrt(max(1 - skew * sr + (kurt - 1) / 4 * sr ** 2, 1e-12))
    z = (sr - sr0) * math.sqrt(T - 1) / denom
    return {"sharpe_annual": sr * math.sqrt(ANN), "sr0_annual": sr0 * math.sqrt(ANN),
            "n_trials": n_trials, "dsr": _N.cdf(z)}
