"""Strategy lab round 3: pre-registered intraday hypotheses H1-H4 (see edge/lab/r3/PREREGISTRATION.md).

Real Dukascopy 5-minute bid/ask bars (tools/dukascopy.py) in, statistics out. Buys fill at the ask, sells at the bid,
plus a top-up to the retail spread table and 0.45 pip commission+slippage per side. Random numbers (seed 20260930)
are used ONLY to pick parameter sets and to block-resample REAL realised daily returns.

Run:  python -m edge.lab.r3.research
"""
from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from edge.lab.dsr import deflated_sharpe

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data" / "dukascopy"
CACHE = DATA / "_cache"
OUT = Path(__file__).resolve().parent / "results"

PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
CCY_SIGN = np.array([1, 1, -1, 1, -1, -1, 1], float)          # +1 XXXUSD, -1 USDXXX
TABLE = np.array([1.0, 1.5, 1.2, 1.3, 1.8, 1.8, 2.0])          # retail spread table, pips
PIP = np.array([1e-2 if p.endswith("JPY") else 1e-4 for p in PAIRS])
EXTRA_SIDE_PIPS = 0.45                                          # (0.5 commission + 0.4 slippage) / 2
LAST = pd.Timestamp("2026-09-25")
DEV = (pd.Timestamp("2012-01-01"), pd.Timestamp("2016-12-31"))
OOS = (pd.Timestamp("2017-01-01"), pd.Timestamp("2023-12-31"))
HOLD = (pd.Timestamp("2024-01-01"), LAST)
WF_YEARS = list(range(2017, 2027))
TRAIN_YEARS = 5
TARGET_VOL, VOL_WIN, ANN = 0.10, 60, 252
SEED, N_MC, N_BOOT, BLOCK = 20260930, 10_000, 10_000, 20
TARGET_ANNUAL = 1.02 ** 12 - 1
PRIOR_FX_SHARPES = [-0.195, -0.280, -0.384, -0.480, -0.201, 0.160, -0.582, 0.201, -0.132]   # ledger F1-F5, G1-G4
N_TRIALS = 13
LONDON = "Europe/London"


# ---------------------------------------------------------------- data

def load_pair(pair: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    c = CACHE / f"{pair}.pkl"
    files = sorted((DATA / pair).glob("*.csv.gz"))
    if c.exists() and c.stat().st_mtime > max(f.stat().st_mtime for f in files):
        return pd.read_pickle(c)
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df[df.ts < LAST + pd.Timedelta(days=1)].drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    df.to_pickle(c)
    return df


def build():
    """Per pair: a (day x 288 five-minute London-local slots) grid of bid/ask open/close, and 15-minute bars for H4."""
    raw = {p: load_pair(p) for p in PAIRS}
    loc = {p: raw[p].ts.dt.tz_convert(LONDON) for p in PAIRS}
    all_days = sorted(set().union(*[set(loc[p].dt.normalize().dt.tz_localize(None).unique()) for p in PAIRS]))
    days = pd.DatetimeIndex([d for d in all_days if d.weekday() < 5 and d <= LAST])
    dpos = pd.Series(np.arange(len(days)), index=days)
    G = {k: np.full((len(days), 288, 7), np.nan, np.float32) for k in ("bo", "ao", "bc", "ac")}
    for j, p in enumerate(PAIRS):
        L = loc[p]
        d = L.dt.normalize().dt.tz_localize(None)
        ok = d.isin(days).to_numpy()
        di = dpos.reindex(d[ok]).to_numpy()
        si = ((L.dt.hour * 60 + L.dt.minute) // 5).to_numpy()[ok]
        for k in G:
            G[k][di, si, j] = raw[p][k].to_numpy()[ok]
    # daily vol scale from the last available mid close of each London day
    mid_c = (G["bc"] + G["ac"]) / 2
    last_close = pd.DataFrame(np.array([pd.DataFrame(mid_c[:, :, j]).ffill(axis=1).iloc[:, -1].to_numpy() for j in range(7)]).T,
                              index=days)
    r = last_close.pct_change(fill_method=None)
    sd = r.rolling(VOL_WIN, min_periods=VOL_WIN).std().shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        W = np.nan_to_num(TARGET_VOL / (sd * np.sqrt(ANN)), nan=0.0, posinf=0.0)
    # 15-minute bars for H4
    B15 = {}
    for j, p in enumerate(PAIRS):
        g = raw[p].set_index("ts").resample("15min", label="left", closed="left")
        b = pd.DataFrame({"bo": g.bo.first(), "ao": g.ao.first(), "bc": g.bc.last(), "ac": g.ac.last()}).dropna()
        lt = b.index.tz_convert(LONDON)
        b["lmin"] = lt.hour * 60 + lt.minute
        b["lday"] = lt.normalize().tz_localize(None)
        b = b[b.lday.isin(days)]
        B15[p] = {"bo": b.bo.to_numpy(), "ao": b.ao.to_numpy(), "mid": ((b.bc + b.ac) / 2).to_numpy(),
                  "lmin": b.lmin.to_numpy(), "dpos": dpos.reindex(b.lday).to_numpy()}
    return days, G, W, B15


t_load = time.time()
DAYS, G, W, B15 = build()
ND = len(DAYS)
YEAR = DAYS.year.to_numpy()


def mask(a, b):
    return (DAYS >= a) & (DAYS <= b)


M_DEV, M_OOS, M_HOLD = mask(*DEV), mask(*OOS), mask(*HOLD)


def extra_frac(bo, ao):
    """Per-side cost beyond the real bid/ask, as a fraction of price: top-up to the retail table + 0.45 pip."""
    real = ao - bo
    top = np.maximum(0.0, TABLE * PIP - real) / 2
    return (top + EXTRA_SIDE_PIPS * PIP) / ((ao + bo) / 2)


def trade(slot_in, slot_out, direction):
    """Return (days x 7) of a same-day trade entered at the open of slot_in and exited at the open of slot_out.

    direction: (days x 7) array of +1 / -1 / 0. Long buys the ask and sells the bid; short the reverse.
    """
    bi, ai, bx, ax = G["bo"][:, slot_in], G["ao"][:, slot_in], G["bo"][:, slot_out], G["ao"][:, slot_out]
    long_r = (bx - ai) / ai
    short_r = (bi - ax) / bi
    r = np.where(direction > 0, long_r, np.where(direction < 0, short_r, 0.0))
    cost = (extra_frac(bi, ai) + extra_frac(bx, ax)) * (direction != 0)
    r = r - cost
    return np.where(np.isfinite(r), r, 0.0)


def mid_close(slot):
    return (G["bc"][:, slot] + G["ac"][:, slot]) / 2


def h1_pair_returns(p):
    w, x = int(p[0]), float(p[1])
    s_end = 96 + w // 5 - 1                      # bar ending at 08:00+W
    s = np.sign(mid_close(s_end) - mid_close(95))  # bar 07:55-08:00 ends at 08:00
    s = np.where(np.isfinite(s), s, 0.0)
    return trade(96 + w // 5, int(round(x * 12)), s)


def h3_pair_returns(p):
    P, Q = int(p[0]), int(p[1])
    usd = np.broadcast_to(-CCY_SIGN, (ND, 7))     # +1 = long the pair = long USD for USDXXX
    ok = np.isfinite(G["bo"][:, 192]) & np.isfinite(G["bo"][:, 193])
    r1 = trade(192 - P // 5, 192, usd * ok)
    r2 = trade(193, 193 + Q // 5, -usd * ok)
    return r1 + r2


def h4_pair_returns(p):
    n, k, e = int(p[0]), float(p[1]), float(p[2])
    out = np.zeros((ND, 7))
    for j, pr in enumerate(PAIRS):
        b = B15[pr]
        m = b["mid"]
        T = len(m)
        cs, cs2 = np.r_[0, np.cumsum(m)], np.r_[0, np.cumsum(m * m)]
        mu = np.full(T, np.nan)
        sd = np.full(T, np.nan)
        mu[n - 1:] = (cs[n:] - cs[:-n]) / n
        sd[n - 1:] = np.sqrt(np.maximum((cs2[n:] - cs2[:-n] - n * mu[n - 1:] ** 2) / (n - 1), 0))
        with np.errstate(divide="ignore", invalid="ignore"):
            z = (m - mu) / sd
        er = ER[pr]
        lm = b["lmin"]
        can = (lm >= 7 * 60) & (lm <= 19 * 60) & (er < e) & np.isfinite(z)
        ent_l = np.flatnonzero(can & (z < -k))
        ent_s = np.flatnonzero(can & (z > k))
        late = lm >= 20 * 60
        BIG = T + 10
        nl = np.minimum.accumulate(np.where((z >= 0) | late, np.arange(T), BIG)[::-1])[::-1]
        ns = np.minimum.accumulate(np.where((z <= 0) | late, np.arange(T), BIG)[::-1])[::-1]
        ents = np.r_[ent_l, ent_s]
        dirs = np.r_[np.ones(len(ent_l)), -np.ones(len(ent_s))]
        o = np.argsort(ents, kind="stable")
        ents, dirs = ents[o], dirs[o]
        free = 0
        bo, ao, dp = b["bo"], b["ao"], b["dpos"]
        for i, d in zip(ents.tolist(), dirs.tolist()):
            if i < free or i + 1 >= T:
                continue
            nxt = (nl if d > 0 else ns)[i + 1] if i + 1 < T else BIG
            jx = min(nxt, i + 16, T - 2)
            fi, fx = i + 1, jx + 1
            if d > 0:
                r = (bo[fx] - ao[fi]) / ao[fi]
            else:
                r = (bo[fi] - ao[fx]) / bo[fi]
            r -= _xf(bo[fi], ao[fi], j) + _xf(bo[fx], ao[fx], j)
            out[int(dp[fx]), j] += r
            free = fx
    return out


def _xf(bo, ao, j):
    top = max(0.0, TABLE[j] * PIP[j] - (ao - bo)) / 2
    return (top + EXTRA_SIDE_PIPS * PIP[j]) / ((ao + bo) / 2)


ER = {}
for _p in PAIRS:
    _m = B15[_p]["mid"]
    _d = np.abs(np.diff(_m, prepend=_m[0]))
    _cs = np.cumsum(_d)
    _er = np.full(len(_m), np.nan)
    _er[32:] = np.abs(_m[32:] - _m[:-32]) / np.maximum(_cs[32:] - _cs[:-32], 1e-12)
    ER[_p] = _er

HYP = {
    "H1": {"name": "London-open momentum (7 majors)", "fn": h1_pair_returns, "pairs": slice(None)},
    "H2": {"name": "London-open momentum (USDJPY only)", "fn": h1_pair_returns, "pairs": [2]},
    "H3": {"name": "London 4pm fix reversal (USD)", "fn": h3_pair_returns, "pairs": slice(None)},
    "H4": {"name": "Regime-filtered intraday mean reversion (15m)", "fn": h4_pair_returns, "pairs": slice(None)},
}
GRIDS = {
    "H1": [(w, x) for w in (15, 30, 45, 60) for x in (10, 12, 14, 16)],
    "H2": [(w, x) for w in (15, 30, 45, 60) for x in (10, 12, 14, 16)],
    "H3": [(P, Q) for P in (15, 30, 60, 120) for Q in (15, 60, 120, 240)],
    "H4": [(n, k, e) for n in (12, 24, 48, 96) for k in (1.5, 2.0, 2.5, 3.0) for e in (0.15, 0.25, 0.35)],
}
_CACHE_R: dict = {}


def strat(h, p):
    key = (h, tuple(p))
    if key in _CACHE_R:
        return _CACHE_R[key]
    fn, sel = HYP[h]["fn"], HYP[h]["pairs"]
    scaled = fn(p) * W
    r = scaled[:, sel].sum(axis=1) / 7 if isinstance(sel, slice) else scaled[:, sel[0]]
    _CACHE_R[key] = r
    return r


# ---------------------------------------------------------------- stats (as in edge/fx2)

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


def target_check(r):
    a = ann_ret(r)
    out = {"oos_sharpe": sharpe(r), "leverage_for_2pct_month": None, "max_dd_at_that_leverage": None}
    if a > 0:
        lo, hi = 0.0, 50.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if ann_ret(r * mid) < TARGET_ANNUAL else (lo, mid)
        out.update({"leverage_for_2pct_month": hi, "max_dd_at_that_leverage": max_dd(r * hi)})
    lo, hi = 0.0, 50.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if max_dd(r * mid) > -0.20 else (lo, mid)
    out["leverage_at_20pct_dd"] = lo
    out["monthly_return_at_20pct_dd"] = (1 + ann_ret(r * lo)) ** (1 / 12) - 1 if a > 0 else None
    out["target_reachable"] = bool(a > 0 and out["oos_sharpe"] >= 0.8 and out["max_dd_at_that_leverage"] >= -0.30)
    return out


def block_boot(r, rng):
    L = len(r)
    nb = int(np.ceil(L / BLOCK))
    starts = rng.integers(0, L - BLOCK + 1, size=(N_BOOT, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)).reshape(N_BOOT, -1)[:, :L]
    lr = np.log1p(r)[idx].sum(axis=1)
    return np.expm1(lr * ANN / L), np.expm1(lr), idx


def walk_forward(h):
    grid = GRIDS[h]
    R = np.array([strat(h, p) for p in grid])
    r_wf, chosen = np.full(ND, np.nan), {}
    for y in WF_YEARS:
        tr = (YEAR >= y - TRAIN_YEARS) & (YEAR <= y - 1)
        best = int(np.argmax([sharpe(R[i, tr]) for i in range(len(grid))]))
        chosen[y] = grid[best]
        r_wf[YEAR == y] = R[best, YEAR == y]
    dev = np.mean([R[grid.index(p)] for p in chosen.values()], axis=0)
    return r_wf, chosen, dev


def draw(h, rng, n):
    if h in ("H1", "H2"):
        return list(zip((rng.integers(3, 13, n) * 5).tolist(), (10 + rng.integers(0, 14, n) * 0.5).tolist()))
    if h == "H3":
        return list(zip((rng.integers(3, 25, n) * 5).tolist(), (rng.integers(1, 17, n) * 15).tolist()))
    return list(zip(rng.integers(12, 97, n).tolist(), rng.uniform(1.5, 3.0, n).tolist(), rng.uniform(0.10, 0.40, n).tolist()))


def main():
    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    print(f"data built in {t0 - t_load:.0f}s: {ND} London days {DAYS[0].date()}..{DAYS[-1].date()}", flush=True)
    rng = np.random.default_rng(SEED)
    res, wf = {}, {}
    for h in HYP:
        r_wf, chosen, dev = walk_forward(h)
        wf[h] = r_wf
        res[h] = {"name": HYP[h]["name"], "chosen_params": {str(y): list(p) for y, p in chosen.items()},
                  "oos_2017_2023": stats(r_wf[M_OOS]), "holdout_2024_2026": stats(r_wf[M_HOLD]),
                  "dev_2012_2016_chosen_blend": stats(dev[M_DEV]), "target_2pct_month": target_check(r_wf[M_OOS])}
        print(f"{h} WF ({time.time()-t0:.0f}s): OOS {res[h]['oos_2017_2023']['sharpe']:.2f} "
              f"hold {res[h]['holdout_2024_2026']['sharpe']:.2f} dev {res[h]['dev_2012_2016_chosen_blend']['sharpe']:.2f}", flush=True)

    rows = []
    for h in HYP:
        for i, p in enumerate(draw(h, rng, N_MC)):
            r = strat(h, p)
            rows.append({"hyp": h, "i": i, "params": json.dumps(list(p)), "oos_sharpe": sharpe(r[M_OOS]),
                         "hold_sharpe": sharpe(r[M_HOLD]), "dev_sharpe": sharpe(r[M_DEV])})
            if h == "H4" and i % 500 == 0:
                print(f"  H4 MC {i} ({time.time()-t0:.0f}s)", flush=True)
            if h == "H4" and len(_CACHE_R) > 400:
                _CACHE_R.clear()
        print(f"{h} param MC ({time.time()-t0:.0f}s)", flush=True)
    mc = pd.DataFrame(rows)
    mc.to_csv(OUT / "param_mc.csv", index=False, float_format="%.5f")

    oos_sharpes = PRIOR_FX_SHARPES + [res[h]["oos_2017_2023"]["sharpe"] for h in HYP]
    boots = {}
    for h in HYP:
        s = mc[mc.hyp == h]
        res[h]["param_mc"] = {"n": len(s), "frac_oos_sharpe_pos": float((s.oos_sharpe > 0).mean()),
                              "median_oos_sharpe": float(s.oos_sharpe.median()),
                              "p05_oos_sharpe": float(s.oos_sharpe.quantile(.05)), "p95_oos_sharpe": float(s.oos_sharpe.quantile(.95)),
                              "frac_hold_sharpe_pos": float((s.hold_sharpe > 0).mean()),
                              "frac_dev_sharpe_pos": float((s.dev_sharpe > 0).mean())}
        a, tot, _ = block_boot(wf[h][M_OOS], rng)
        boots[h] = a
        res[h]["return_mc"] = {"p05_ann_return": float(np.percentile(a, 5)), "median_ann_return": float(np.median(a)),
                               "p95_ann_return": float(np.percentile(a, 95)), "prob_loss_over_oos": float((tot < 0).mean())}
        res[h]["deflated_sharpe"] = deflated_sharpe(wf[h][M_OOS], N_TRIALS, oos_sharpes)
        o = res[h]
        c = {"c1_oos_sharpe>=0.3_and_ret>0": o["oos_2017_2023"]["sharpe"] >= 0.3 and o["oos_2017_2023"]["total_return"] > 0,
             "c2_param_mc_>=60%_pos_and_median>0": o["param_mc"]["frac_oos_sharpe_pos"] >= 0.6 and o["param_mc"]["median_oos_sharpe"] > 0,
             "c3_return_mc_prob_loss<20%": o["return_mc"]["prob_loss_over_oos"] < 0.2,
             "c4_dev_sharpe>0": o["dev_2012_2016_chosen_blend"]["sharpe"] > 0,
             "c5_2pct_month_reachable": o["target_2pct_month"]["target_reachable"],
             "c6_deflated_sharpe>=0.95": o["deflated_sharpe"]["dsr"] >= 0.95}
        o["criteria"], o["validated"] = c, all(c.values())

    live = M_OOS | M_HOLD
    df = pd.DataFrame(wf, index=DAYS)
    df[live].to_csv(OUT / "wf_daily_returns.csv", float_format="%.7f")
    summary = {"data": {"source": "Dukascopy 5-minute bid/ask (tools/dukascopy.py)", "first_day": str(DAYS[0].date()),
                        "last_day": str(DAYS[-1].date()), "days": ND, "pairs": PAIRS},
               "n_trials_for_dsr": N_TRIALS, "hypotheses": res,
               "validated": [h for h in HYP if res[h]["validated"]]}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    charts(df[live], mc, boots, res)
    print(json.dumps({h: {"validated": res[h]["validated"], **res[h]["criteria"]} for h in HYP}, indent=1))
    print(f"done in {time.time()-t0:.0f}s")


def charts(df, mc, boots, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 6))
    for h in HYP:
        ax.plot(df.index, np.cumprod(1 + df[h].fillna(0)), lw=1.2, label=f"{h} {HYP[h]['name']}")
    x = np.arange(len(df))
    ax.plot(df.index, (1 + TARGET_ANNUAL) ** (x / ANN), "g--", lw=1, label="2% a month target")
    ax.set_yscale("log")
    ax.axvspan(HOLD[0], HOLD[1], color="orange", alpha=0.12)
    ax.set_title("Lab round 3 (intraday, Dukascopy bid/ask): walk-forward equity, net of costs, 2017-2026")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "equity.png", dpi=120)
    plt.close(fig)
    fig, axs = plt.subplots(1, 4, figsize=(20, 4.5))
    for a, h in zip(axs, HYP):
        s = mc[mc.hyp == h]
        a.hist(s.oos_sharpe, bins=50, color="steelblue", alpha=0.8, label="OOS 2017-23")
        a.hist(s.hold_sharpe, bins=50, color="orange", alpha=0.5, label="holdout 24-26")
        a.axvline(0, color="k")
        p = res[h]["param_mc"]
        a.set_title(f"{h} {HYP[h]['name']}\n{p['frac_oos_sharpe_pos']:.0%} of 10,000 sets >0, median {p['median_oos_sharpe']:.2f}", fontsize=8)
        a.legend(fontsize=7)
    fig.suptitle("Parameter Monte Carlo (seed 20260930)")
    fig.tight_layout()
    fig.savefig(OUT / "param_mc.png", dpi=110)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    for h in HYP:
        ax.hist(boots[h], bins=80, histtype="step", lw=1.2, label=f"{h}")
    ax.axvline(0, color="k")
    ax.axvline(TARGET_ANNUAL, color="g", ls="--", label="2% a month")
    ax.set_title("Return Monte Carlo: annualised return of 10,000 block-bootstraps of real OOS 2017-2023")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "return_mc.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    main()
