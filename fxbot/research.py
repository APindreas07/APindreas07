"""Research runner: baseline -> inefficiencies -> walk-forward optimisation -> parameter drift.

    python -m fxbot.research                      # daily data only
    python -m fxbot.research --h1 path/to/EURUSD_H1.csv --h1-tz Europe/Athens

Writes results/REPORT.md, charts (PNG) and CSVs. Every number in the report is
computed from the backtests in this run; nothing is typed in by hand.
"""

import argparse
import itertools
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from . import plots
from .data import ROOT, load_daily, load_hourly
from .engine import Account, Backtester, Costs
from .metrics import cards_table, monthly_returns, scorecard
from .strategy import LEGACY, Params, TREND_CHOICES, add_features

OUT = ROOT / "results"

GRID_AXES = {
    "trend": list(TREND_CHOICES),
    "rsi_thr": [25.0, 35.0, 45.0],
    "atr_mult": [1.0, 1.5, 2.0],
    "entry": ["open", "breakout", "confirm"],
    "max_hold": [5, 10, 20],
}
ORDINAL = ("rsi_thr", "atr_mult", "max_hold")

MIN_TRADES_TRAIN = 12          # at least ~4 trades a year in a 3-year training window
DD_LIMIT_TRAIN_PCT = 8.0       # stay 2% inside the FTMO 10% max-loss limit
INVALID_SCORE = -2.0


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------
def objective(card, account):
    """Return-to-drawdown in R, with hard FTMO-style constraints.

    score = net R / max(max drawdown in R, 2). Rejected (None) if fewer than
    MIN_TRADES_TRAIN trades or the intraday drawdown reaches DD_LIMIT_TRAIN_PCT.
    """
    if card.get("trades", 0) < MIN_TRADES_TRAIN or card["max_dd_pct"] >= DD_LIMIT_TRAIN_PCT:
        return None
    net_r = card["net_profit"] / account.risk_usd
    dd_r = card["max_dd_usd"] / account.risk_usd
    return net_r / max(dd_r, 2.0)


def grid(axes=GRID_AXES):
    keys = list(axes)
    return [Params(**dict(zip(keys, vals))) for vals in itertools.product(*axes.values())]


def evaluate_grid(bt, params_list, start, end):
    rows = []
    for p in params_list:
        tr, eq = bt.run(p, start, end)
        card = scorecard(tr, eq, bt.account)
        score = objective(card, bt.account)
        rows.append({**p.as_dict(), "params": p, "score": score,
                     "net_r": card["net_profit"] / bt.account.risk_usd,
                     "trades": card["trades"], "max_dd_pct": card["max_dd_pct"],
                     "expectancy_r": card["expectancy_r"], "profit_factor": card["profit_factor"]})
    return pd.DataFrame(rows)


def smooth_scores(res, axes=GRID_AXES):
    """Plateau score: mean raw score of a parameter set and its grid neighbours.

    Neighbours share the categorical choices and sit within one grid step on
    each ordinal axis. A sharp isolated peak scores lower than a broad plateau,
    which is what survives out of sample.
    """
    pos = {k: {v: i for i, v in enumerate(axes[k])} for k in ORDINAL}
    raw = res["score"].fillna(INVALID_SCORE).to_numpy()
    keyed = {}
    for idx, row in res.iterrows():
        keyed.setdefault((row["trend"], row["entry"]), []).append(idx)
    smoothed = np.empty(len(res))
    for idx, row in res.iterrows():
        vals = []
        for j in keyed[(row["trend"], row["entry"])]:
            other = res.loc[j]
            if all(abs(pos[k][other[k]] - pos[k][row[k]]) <= 1 for k in ORDINAL):
                vals.append(raw[j])
        smoothed[idx] = np.mean(vals)
    out = res.copy()
    out["plateau_score"] = smoothed
    return out


# ---------------------------------------------------------------------------
# Walk-forward
# ---------------------------------------------------------------------------
def walk_forward(bt, params_list, oos_start, oos_end, train_months=36, test_months=6, anchored_from=None):
    """Rolling (default) or anchored walk-forward. Anchored: every training window
    starts at `anchored_from` and grows; rolling: fixed `train_months` length."""
    windows = []
    t = pd.Timestamp(oos_start)
    end = pd.Timestamp(oos_end)
    while t <= end:
        test_end = min(t + pd.DateOffset(months=test_months) - pd.Timedelta(days=1), end)
        train_start = pd.Timestamp(anchored_from) if anchored_from else t - pd.DateOffset(months=train_months)
        train_end = t - pd.Timedelta(days=1)
        res = smooth_scores(evaluate_grid(bt, params_list, train_start, train_end))
        valid = res[res["score"].notna()]
        if valid.empty:
            chosen, is_score, plateau = None, np.nan, np.nan
        else:
            best = valid.sort_values(["plateau_score", "score"], ascending=False).iloc[0]
            chosen, is_score, plateau = best["params"], best["score"], best["plateau_score"]
        row = {"train": f"{train_start:%Y-%m} .. {train_end:%Y-%m}",
               "test": f"{t:%Y-%m} .. {test_end:%Y-%m}",
               "test_start": t, "test_end": test_end, "params": chosen,
               "valid_sets": len(valid), "is_score": is_score, "plateau": plateau}
        if chosen is not None:
            is_card = scorecard(*bt.run(chosen, train_start, train_end), bt.account)
            oos_card = scorecard(*bt.run(chosen, t, test_end), bt.account)
            yrs_is = (train_end - train_start).days / 365.25
            yrs_oos = (test_end - t).days / 365.25
            row.update(is_net_r=is_card["net_profit"] / bt.account.risk_usd,
                       is_r_per_year=is_card["net_profit"] / bt.account.risk_usd / yrs_is,
                       oos_net_r=oos_card["net_profit"] / bt.account.risk_usd,
                       oos_r_per_year=oos_card["net_profit"] / bt.account.risk_usd / yrs_oos,
                       oos_trades=oos_card["trades"], oos_dd_pct=oos_card["max_dd_pct"])
        windows.append(row)
        t = t + pd.DateOffset(months=test_months)
    wf = pd.DataFrame(windows)

    def schedule(date):
        hit = wf[(wf["test_start"] <= date) & (wf["test_end"] >= date)]
        return None if hit.empty else hit["params"].iloc[0]

    return wf, schedule


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------
def inefficiencies(bt, feat, trades):
    """Where does the legacy strategy leak? Returns dict of tables and numbers."""
    out = {}
    t = trades
    out["exit_mix"] = (t.groupby("exit_reason")
                         .agg(trades=("r_net", "size"), avg_r=("r_net", "mean"),
                              avg_mfe_r=("mfe_r", "mean"), avg_days=("days_held", "mean"))
                         .sort_values("trades", ascending=False))
    out["reach"] = {f">= {k}R": (t["mfe_r"] >= k).mean() * 100 for k in (0.5, 1, 2, 3)}
    time_exits = t[t["exit_reason"] == "TIME"]
    out["time_exit_share"] = len(time_exits) / len(t) * 100
    out["time_exit_gave_back_1r"] = ((time_exits["mfe_r"] >= 1) & (time_exits["r_gross"] < 0.5)).mean() * 100 \
        if len(time_exits) else 0.0
    stops = t[t["exit_reason"].str.startswith("STOP")]
    out["stops_within_2_days"] = (stops["days_held"] <= 2).mean() * 100 if len(stops) else 0.0
    out["ambiguous_bars"] = int(t["same_bar_sl_tp"].sum())
    gross_win = t.loc[t["gross_pnl"] > 0, "gross_pnl"].sum()
    out["cost_share_of_gross_wins"] = (t["commission"].sum() - t["swap"].sum()) / gross_win * 100 if gross_win else 0
    out["swap_usd"] = t["swap"].sum()

    # How often does 'break the pullback day's high' actually trigger?
    h = feat["high"].to_numpy()
    sig = np.flatnonzero(bt.signal(LEGACY))
    sig = sig[sig + 1 < len(h)]
    out["breakout_fill_pct"] = (h[sig + 1] > h[sig] + 1e-4).mean() * 100 if len(sig) else 0.0
    out["higher_high_any_day_pct"] = (h[1:] > h[:-1]).mean() * 100

    # Indicator redundancy in the legacy trend filter
    a = feat["ema1"] > feat["ema5"]
    b = feat["ema5"] > feat["ema9"]
    c = feat["rsi14"] > 50
    valid = feat["rsi14"].notna()
    out["redundancy"] = {
        "EMA1>EMA5 vs RSI14>50 agree": (a == c)[valid].mean() * 100,
        "EMA1>EMA5 vs EMA5>EMA9 agree": (a == b)[valid].mean() * 100,
        "legacy trend flips per year": (feat["trend_legacy"].astype(int).diff().abs()[valid].sum()
                                        / (valid.sum() / 260)),
    }
    for n in (50, 100, 200):
        col = f"trend_ema{n}"
        out["redundancy"][f"EMA{n} trend flips per year"] = (
            feat[col].astype(int).diff().abs()[valid].sum() / (valid.sum() / 260))

    # Does each trend definition actually pick days that drift up? (forward 10-day move)
    fwd = (feat["close"].shift(-10) - feat["open"].shift(-1)) / 1e-4
    rows = []
    for name in TREND_CHOICES:
        on = feat[f"trend_{name}"].shift(1, fill_value=False)
        rows.append({"trend": name, "days_on_pct": on[valid].mean() * 100,
                     "fwd10_pips_on": fwd[on & valid].mean(), "fwd10_pips_off": fwd[~on & valid].mean()})
    rows.append({"trend": "all days", "days_on_pct": 100.0,
                 "fwd10_pips_on": fwd[valid].mean(), "fwd10_pips_off": np.nan})
    out["trend_edge"] = pd.DataFrame(rows).set_index("trend")
    return out


def parameter_drift(bt, center, start, end, axes=None):
    """One-at-a-time sweeps around `center` (wider than the optimisation grid)."""
    axes = axes or {
        "trend": list(TREND_CHOICES),
        "rsi_thr": [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0],
        "atr_mult": [0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0],
        "entry": ["open", "breakout", "confirm"],
        "max_hold": [3, 5, 7, 10, 15, 20, 30],
    }
    rows = []
    for name, values in axes.items():
        for v in values:
            p = Params(**{**center.as_dict(), name: v})
            card = scorecard(*bt.run(p, start, end), bt.account)
            rows.append({"param": name, "value": v, "net_r": card["net_profit"] / bt.account.risk_usd,
                         "trades": card["trades"], "expectancy_r": card["expectancy_r"],
                         "profit_factor": card["profit_factor"], "max_dd_pct": card["max_dd_pct"],
                         "breach": card["ftmo_breach"]})
    return pd.DataFrame(rows)


def challenge_runs(bt, schedule, first, last):
    """Start a fresh $10k challenge at every month start; run until +10%, a breach, or data end."""
    rows = []
    for start in pd.date_range(first, last, freq="MS"):
        _, eq = bt.run(schedule, start, bt.feat["date"].iloc[-1], halt_on_breach=True, halt_on_target=True)
        if eq.empty:
            continue
        reason = eq.attrs.get("stop_reason") or "OPEN"
        days = (pd.Timestamp(eq["date"].iloc[-1]) - start).days
        rows.append({"start": start.date(), "outcome": {"TARGET": "PASS", "BREACH": "FAIL"}.get(reason, "OPEN"),
                     "days": days, "final_balance": eq["balance"].iloc[-1]})
    return pd.DataFrame(rows)


def challenge_summary(ch):
    if ch.empty:
        return {}
    counts = ch["outcome"].value_counts()
    done = ch[ch["outcome"] != "OPEN"]
    return {"starts": len(ch), "pass": int(counts.get("PASS", 0)), "fail": int(counts.get("FAIL", 0)),
            "open": int(counts.get("OPEN", 0)),
            "median_days_to_pass": float(ch.loc[ch["outcome"] == "PASS", "days"].median())
            if counts.get("PASS", 0) else np.nan,
            "pass_rate_decided_pct": (done["outcome"] == "PASS").mean() * 100 if len(done) else np.nan}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def md_table(df, floatfmt="{:.2f}"):
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else floatfmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


# Standards the bot must meet (from the trading plan / prop-firm rules)
STANDARDS = [
    ("no FTMO breach", lambda c: not c["ftmo_breach"]),
    ("max drawdown <= 8%", lambda c: c["max_dd_pct"] <= 8.0),
    ("expectancy > 0", lambda c: c["expectancy_r"] > 0),
    ("profit factor >= 1.3", lambda c: c["profit_factor"] >= 1.3),
    ("rising, smooth equity (K-ratio > 0, R^2 >= 0.6)", lambda c: c["k_ratio"] > 0 and c["equity_r2"] >= 0.6),
]


def wfe_text(wfe):
    if wfe != wfe:
        return "n/a"
    return "below -100%" if wfe < -100 else f"{wfe:.0f}%"


def standards_row(card):
    passed = [name for name, test in STANDARDS if card and test(card)]
    return len(passed), [name for name, _ in STANDARDS if name not in passed]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="2018-01-01", help="first date the strategy may trade")
    ap.add_argument("--oos-start", default="2021-01-01", help="first out-of-sample date")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--train-months", type=int, default=36)
    ap.add_argument("--test-months", type=int, default=6)
    ap.add_argument("--h1", type=Path, help="optional 1H bars CSV (adds entry='h1' to the grid)")
    ap.add_argument("--h1-tz", default="UTC", help="timezone of the 1H file's timestamps")
    ap.add_argument("--spread-pips", type=float, default=Costs.spread_pips)
    ap.add_argument("--commission", type=float, default=Costs.commission_per_lot)
    ap.add_argument("--swap", type=float, default=Costs.swap_per_lot_night)
    ap.add_argument("--throttle-below", type=float, default=9500.0,
                    help="balance below which risk is halved in the throttled runs")
    args = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    account = Account()
    throttled = replace(account, throttle_below=args.throttle_below)
    costs = Costs(args.spread_pips, args.commission, args.swap)
    feat = add_features(load_daily())
    h1 = load_hourly(args.h1, args.h1_tz) if args.h1 else None
    bt = Backtester(feat, account, costs, h1)
    btt = Backtester(feat, throttled, costs, h1)
    axes = dict(GRID_AXES)
    if h1 is not None:
        axes["entry"] = axes["entry"] + ["h1"]
    params_list = grid(axes)

    # 1. Baseline: the previous script's strategy on the prop-firm account
    lt, le = bt.run(LEGACY, args.start, args.end)
    legacy_full = scorecard(lt, le, account)
    ltt, let_ = btt.run(LEGACY, args.start, args.end)
    legacy_full_thr = scorecard(ltt, let_, throttled)
    diag = inefficiencies(bt, feat, lt)

    # 2. Walk-forward optimisation: rolling (primary) and anchored
    wf_roll, sched_roll = walk_forward(bt, params_list, args.oos_start, args.end,
                                       args.train_months, args.test_months)
    wf_anch, sched_anch = walk_forward(bt, params_list, args.oos_start, args.end,
                                       args.train_months, args.test_months, anchored_from=args.start)
    variants = {"Legacy (fixed rules)": LEGACY,
                f"Walk-forward, rolling {args.train_months}m": sched_roll,
                "Walk-forward, anchored": sched_anch}
    runs = {}
    for name, sched in variants.items():
        for tag, b in (("", bt), (" + throttle", btt)):
            tr, eq = b.run(sched, args.oos_start, args.end)
            runs[name + tag] = (tr, eq, scorecard(tr, eq, b.account))

    # 3. Parameter drift around the set the rolling walk-forward chose most often
    chosen = [p for p in wf_roll["params"] if p is not None]
    center = max(set(chosen), key=chosen.count) if chosen else Params()
    drift_is = parameter_drift(bt, center, args.start, args.oos_start)
    drift_oos = parameter_drift(bt, center, args.oos_start, args.end)
    heat = {}
    for rt in [15.0, 25.0, 35.0, 45.0, 55.0]:
        for am in [1.0, 1.5, 2.0, 2.5, 3.0]:
            p = Params(**{**center.as_dict(), "rsi_thr": rt, "atr_mult": am})
            heat[(rt, am)] = scorecard(*bt.run(p, args.start, args.end), account)["net_profit"] / account.risk_usd
    heat_df = pd.Series(heat).unstack()

    # 4. FTMO challenge simulations
    challenges = {name: challenge_runs(bt, sched, args.oos_start, args.end) for name, sched in variants.items()}
    challenges[f"Legacy (fixed rules), starts from {args.start[:4]}"] = challenge_runs(bt, LEGACY, args.start, args.end)
    challenges[f"Legacy + throttle, starts from {args.start[:4]}"] = challenge_runs(btt, LEGACY, args.start, args.end)

    # 5. Outputs
    names = list(variants)
    plots.equity_chart({names[1]: runs[names[1]][1], names[2]: runs[names[2]][1], names[0]: runs[names[0]][1]},
                       account, OUT / "equity_walkforward.png",
                       f"EURUSD buy-only, $10k FTMO-style account, $100 risk/trade, out-of-sample "
                       f"{args.oos_start[:4]}-{args.end[:4]}")
    plots.equity_chart({"Legacy": le, "Legacy + throttle": let_}, account, OUT / "equity_legacy_full.png",
                       f"Legacy strategy (previous script) on the prop-firm account, {args.start[:4]}-{args.end[:4]}")
    plots.drift_chart(drift_oos, center.as_dict(), OUT / "parameter_drift_oos.png",
                      f"Parameter drift, out-of-sample {args.oos_start[:4]}-{args.end[:4]} "
                      f"(one parameter changed at a time; ring = chosen)")
    plots.heatmap(heat_df, OUT / "heatmap_rsi_atr.png",
                  f"Net R {args.start[:4]}-{args.end[:4]} by RSI(3) threshold and stop size\n"
                  f"(other settings: {center.trend}, {center.entry}, hold {center.max_hold}d)",
                  "Stop distance (x ATR14)", "RSI(3) entry threshold")
    for name, (tr, eq, _) in runs.items():
        slug = name.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("+_", "")
        tr.to_csv(OUT / f"trades_oos_{slug}.csv", index=False)
    lt.to_csv(OUT / "trades_legacy_full.csv", index=False)
    wf_tables = {}
    for name, wf in ((names[1], wf_roll), (names[2], wf_anch)):
        wf_tables[name] = wf.assign(params=wf["params"].map(lambda p: p.label() if p else "stay flat"))
        slug = "rolling" if "rolling" in name else "anchored"
        wf_tables[name].drop(columns=["test_start", "test_end"]).to_csv(OUT / f"walkforward_{slug}.csv", index=False)
    pd.concat([drift_is.assign(sample="in-sample"), drift_oos.assign(sample="out-of-sample")]) \
        .to_csv(OUT / "parameter_drift.csv", index=False)
    for name, ch in challenges.items():
        slug = name.lower().replace(" ", "_").replace(",", "").replace("(", "").replace(")", "").replace("+_", "")
        ch.to_csv(OUT / f"challenges_{slug}.csv", index=False)
    for stale in ("equity_walkforward.csv", "trades_walkforward.csv", "trades_legacy.csv",
                  "walkforward_windows.csv", "ftmo_challenges_walkforward.csv"):
        (OUT / stale).unlink(missing_ok=True)

    write_report(args, account, throttled, costs, feat, legacy_full, legacy_full_thr, diag, wf_tables, runs,
                 center, drift_is, drift_oos, heat_df, challenges, h1 is not None, len(params_list))
    print(f"Report written to {OUT / 'REPORT.md'}")


def summary_lines(args, account, legacy_full, legacy_full_thr, wf_tables, runs, center, heat_df, challenges):
    """Headline findings, each computed from this run's results."""
    out = []
    account_risk = account.risk_usd
    ok = {n: standards_row(c)[0] for n, (_, _, c) in runs.items()}
    best = [n for n, k in ok.items() if k == len(STANDARDS)]
    out.append(f"- **Out of sample ({args.oos_start[:4]}-{args.end[:4]}), runs meeting all {len(STANDARDS)} standards:** "
               + (", ".join(best) if best else "none") + ".")
    for name, wf in wf_tables.items():
        c = runs[name][2]
        wfe = (wf["oos_r_per_year"].sum() / wf["is_r_per_year"].sum() * 100
               if "is_r_per_year" in wf and wf["is_r_per_year"].sum() > 0 else float("nan"))
        verdict = ("the optimised settings did not carry forward" if not wfe > 50 else "the edge carried forward")
        out.append(f"- **{name}:** {c['return_pct']:+.1f}% out of sample, walk-forward efficiency {wfe_text(wfe)}, "
                   f"{wf['params'].nunique()} different parameter sets in {len(wf)} windows: {verdict}.")
    for name, ch in challenges.items():
        if "from" in name:
            sm = challenge_summary(ch)
            out.append(f"- **{name}:** {sm['pass']} passed, {sm['fail']} failed, {sm['open']} still running of "
                       f"{sm['starts']} monthly challenge starts; median {sm['median_days_to_pass']:.0f} days to +10%.")
    rt, am = center.rsi_thr, center.atr_mult
    if rt in heat_df.index and am in heat_df.columns:
        r_i, c_i = heat_df.index.get_loc(rt), heat_df.columns.get_loc(am)
        block = heat_df.iloc[max(r_i - 1, 0):r_i + 2, max(c_i - 1, 0):c_i + 2].to_numpy().ravel()
        centre_v = heat_df.iloc[r_i, c_i]
        neigh = (block.sum() - centre_v) / (len(block) - 1)
        shape = "an isolated peak (fragile)" if centre_v > 2 * max(neigh, 0.1) else "a plateau (robust)"
        out.append(f"- **Robustness:** the most-chosen settings make {centre_v:+.1f}R over "
                   f"{args.start[:4]}-{args.end[:4]} while their neighbours average {neigh:+.1f}R: {shape}.")
    out.append(f"- **Pace:** at ${account_risk:,.0f} risk per trade even the best run grows "
               f"about {max(c['cagr_pct'] for _, _, c in runs.values()):.1f}% a year, so a +10% phase takes years, not weeks.")
    return out


def write_report(args, account, throttled, costs, feat, legacy_full, legacy_full_thr, diag, wf_tables, runs,
                 center, drift_is, drift_oos, heat_df, challenges, has_h1, n_grid):
    L = []
    add = L.append
    d0, d1 = feat["date"].iloc[0], feat["date"].iloc[-1]
    add("# EURUSD buy-only swing strategy: research report\n")
    add("*Generated by `python -m fxbot.research`. Every number below is computed from real "
        f"TradeStation EURUSD daily bars ({len(feat)} bars, {d0:%Y-%m-%d} to {d1:%Y-%m-%d}); "
        "no random numbers, no synthetic prices. Re-running regenerates the whole report.*\n")

    add("## Trading plan and standards\n")
    add(f"- Account: ${account.initial:,.0f} FTMO-style (or similar prop firm). Risk per trade "
        f"${account.risk_usd:,.0f} (a $1,000 position budget with a 10% max loss = 1% of the account).")
    add(f"- Prop-firm limits: equity may never touch ${account.initial * (1 - account.max_loss_pct):,.0f} "
        f"(10% max loss) or fall ${account.initial * account.daily_loss_pct:,.0f} below the day's starting balance "
        "(5% daily loss). Checked against the worst intraday price every day, including open trades.")
    add("- Buy only, 1:3 risk:reward on every trade, one position at a time (never more than one new trade a day).")
    add(f"- Costs: {costs.spread_pips:g} pip spread+slippage, ${costs.commission_per_lot:g}/lot round-turn commission, "
        f"{costs.swap_per_lot_night:+g} USD/lot per night held (long EURUSD swap is negative; set yours with `--swap`).")
    add("- Timeframes: 1D for trend and setup, 1H for confirmation. " + (
        "1H bars supplied: the 1H confirmation entry was included in the optimisation." if has_h1 else
        "**No 1H data was available** (TradeStation's API serves intraday data only as 5-minute bars, 100 per "
        "call, and other data vendors are blocked here). The 1H confirmation is implemented (`entry='h1'`) and "
        "joins the optimisation as soon as an H1 file is passed with `--h1`; until then the daily `confirm` "
        "entry (buy the close of an up day after the pullback) stands in for it."))
    add("- Standards every run is checked against: " + "; ".join(n for n, _ in STANDARDS) + ".\n")
    add("## Summary\n")
    for line in summary_lines(args, account, legacy_full, legacy_full_thr, wf_tables, runs, center, heat_df, challenges):
        add(line)
    add("")

    add("## 1. Baseline: the previous strategy on this account\n")
    add("Legacy rules: trend = EMA1 > EMA5 > EMA9 and RSI(14) > 50 on the prior day; buy the next open "
        "when RSI(3) < 40; stop 1x ATR(14), target 3R, exit after 5 days.\n")
    add(cards_table({f"Legacy {args.start[:4]}-{args.end[:4]}": legacy_full,
                     f"Legacy + throttle (half risk below ${throttled.throttle_below:,.0f})": legacy_full_thr}) + "\n")
    add("![Legacy equity](equity_legacy_full.png)\n")
    if legacy_full["ftmo_breach"]:
        add(f"**The legacy strategy would have lost an FTMO account started in {args.start[:4]}** "
            f"(equity touched the floor on {legacy_full['ftmo_breach_date']}). "
            + ("With the throttle it survived." if not legacy_full_thr["ftmo_breach"] else
               "Even with the throttle it breached.") + "\n")

    add("## 2. Inefficiencies found\n")
    ex = diag["exit_mix"].reset_index()
    add(md_table(ex.rename(columns={"exit_reason": "exit", "avg_r": "avg R", "avg_mfe_r": "avg best R reached",
                                    "avg_days": "avg days"})) + "\n")
    reach = diag["reach"]
    red = diag["redundancy"]
    add(f"1. **The 3R target does not fit a 5-day hold.** {diag['time_exit_share']:.0f}% of trades end on the "
        f"time limit; only {reach['>= 3R']:.0f}% ever reach +3R while {reach['>= 1R']:.0f}% reach +1R. "
        f"{diag['time_exit_gave_back_1r']:.0f}% of time-exited trades were up 1R+ and gave most of it back.")
    add(f"2. **Buying the falling knife.** {diag['stops_within_2_days']:.0f}% of stopped trades were stopped within "
        "2 days: the entry is the next open after a weak close, with no sign the dip has ended.")
    add(f"3. **Redundant trend filter.** EMA1>EMA5 and RSI(14)>50 agree on {red['EMA1>EMA5 vs RSI14>50 agree']:.0f}% "
        f"of days, EMA1>EMA5 and EMA5>EMA9 on {red['EMA1>EMA5 vs EMA5>EMA9 agree']:.0f}%: three indicators, mostly one "
        f"signal. It flips {red['legacy trend flips per year']:.0f} times a year (vs "
        f"{red['EMA100 trend flips per year']:.0f}/year for 'close above a rising EMA100'), so it is really a short-term "
        "momentum filter, not a trend filter. Note that out of sample it beat the slower EMA filters (section 6): the "
        "redundancy is a simplification opportunity, not proof the filter is bad.")
    add(f"4. **A confirmation that almost never fires.** Buying a break of the pullback day's high sounds sensible, "
        f"but the pullback days are sharp down days that close near their lows: after a legacy signal EURUSD traded "
        f"above that high the next day only {diag['breakout_fill_pct']:.0f}% of the time (vs "
        f"{diag['higher_high_any_day_pct']:.0f}% on an average day). The daily `confirm` entry (buy the close of the "
        "next up day) was added so the optimiser has a working confirmation option.")
    add(f"5. **Costs.** Commission and swap equal {diag['cost_share_of_gross_wins']:.0f}% of gross winning P&L "
        f"(swap ${diag['swap_usd']:,.0f}); longer holds pay more swap.")
    add(f"6. **Daily-bar blind spot.** {diag['ambiguous_bars']} legacy trades hit stop and target on the same day "
        "(scored as losses); 1H data resolves these.\n")
    te = diag["trend_edge"].reset_index()
    add("Does each trend filter pick days when EURUSD drifts up? (average move over the next 10 days, pips):\n")
    add(md_table(te.rename(columns={"days_on_pct": "% of days on", "fwd10_pips_on": "next 10d when on",
                                    "fwd10_pips_off": "next 10d when off"}), "{:.1f}") + "\n")

    add("## 3. Walk-forward optimisation\n")
    add(f"- {n_grid} parameter sets: trend filter x RSI(3) threshold x stop size x entry confirmation x max hold "
        "(risk:reward fixed at 1:3).")
    add(f"- Train on past data, trade the next {args.test_months} months untouched, roll forward. Rolling = fixed "
        f"{args.train_months}-month training window; anchored = training always starts {args.start[:7]} and grows. "
        f"Out-of-sample period {args.oos_start} to {args.end}.")
    add(f"- Objective: net R / max drawdown R; sets with < {MIN_TRADES_TRAIN} trades or a {DD_LIMIT_TRAIN_PCT:g}%+ "
        "drawdown in training are rejected. Selection uses a **plateau score** (the set averaged with its grid "
        "neighbours), so a lucky isolated peak loses to a stable region. If nothing passes, the bot stays flat.\n")
    for name, wf in wf_tables.items():
        add(f"### {name}\n")
        cols = ["train", "test", "params", "valid_sets", "is_r_per_year", "oos_net_r", "oos_trades"]
        add(md_table(wf[[c for c in cols if c in wf]].rename(columns={
            "params": "chosen parameters", "valid_sets": "sets passing", "is_r_per_year": "train R/yr",
            "oos_net_r": "test R", "oos_trades": "test trades"}), "{:.1f}") + "\n")
        if "is_r_per_year" in wf and wf["is_r_per_year"].sum() > 0:
            wfe = wf["oos_r_per_year"].sum() / wf["is_r_per_year"].sum() * 100
            add(f"Walk-forward efficiency (out-of-sample R/yr vs training R/yr): {wfe_text(wfe)}. "
                "Above ~50% suggests a real edge; near or below 0% means the training results did not carry forward.\n")
        n_unique = wf["params"].nunique()
        add(f"Distinct parameter sets chosen across {len(wf)} windows: {n_unique}.\n")

    add("## 4. Out-of-sample comparison against the standards\n")
    rows = []
    for name, (_, _, c) in runs.items():
        n_ok, missed = standards_row(c)
        rows.append({"run": name, "return": f"{c['return_pct']:+.1f}%", "trades": c["trades"],
                     "expectancy R": c["expectancy_r"], "profit factor": c["profit_factor"],
                     "max DD": f"{c['max_dd_pct']:.1f}%", "lowest equity": f"${c['lowest_equity']:,.0f}",
                     "K-ratio": c["k_ratio"], "R^2": c["equity_r2"],
                     "standards met": f"{n_ok}/{len(STANDARDS)}",
                     "missed": "; ".join(missed) or "none"})
    add(md_table(pd.DataFrame(rows)) + "\n")
    add("![Out-of-sample equity](equity_walkforward.png)\n")
    primary = next(n for n in runs if "rolling" in n and "throttle" not in n)
    legacy_name = next(n for n in runs if n.startswith("Legacy") and "throttle" not in n)
    add(cards_table({primary: runs[primary][2], legacy_name: runs[legacy_name][2]}) + "\n")
    for name in (primary, legacy_name):
        m = monthly_returns(runs[name][1])
        if len(m):
            yearly = m.groupby(m.index.year).apply(lambda s: ((1 + s / 100).prod() - 1) * 100)
            add(f"{name}, return by year: " + ", ".join(f"{y}: {v:+.1f}%" for y, v in yearly.items()) + "\n")

    add("## 5. FTMO challenge simulation\n")
    add("A fresh $10,000 challenge started on the first trading day of every month, run until the +10% phase-1 "
        "target (pass), a limit breach (fail), or the end of the data (still running):\n")
    rows = []
    for name, ch in challenges.items():
        s = challenge_summary(ch)
        if s:
            rows.append({"strategy": name, "starts": s["starts"], "passed": s["pass"], "failed": s["fail"],
                         "still running": s["open"], "pass rate (decided)": s["pass_rate_decided_pct"],
                         "median days to pass": s["median_days_to_pass"]})
    if rows:
        add(md_table(pd.DataFrame(rows), "{:.0f}") + "\n")

    add("## 6. Parameter drift (robustness)\n")
    add(f"Centre = the set the rolling walk-forward chose most often: `{center.label()}`. Each panel changes one "
        "parameter, keeping the rest fixed. Robust settings sit on a broad plateau; a spike means luck.\n")
    add("![Parameter drift](parameter_drift_oos.png)\n")
    add("![Heatmap](heatmap_rsi_atr.png)\n")
    for label, dr in (("In-sample (before the out-of-sample period)", drift_is), ("Out-of-sample", drift_oos)):
        add(f"<details><summary>{label} drift table</summary>\n")
        add(md_table(dr, "{:.2f}") + "\n")
        add("</details>\n")
    is_net = drift_is["net_r"]
    add(f"Regime check: before {args.oos_start[:4]}, {int((is_net > 0).sum())} of {len(is_net)} one-at-a-time "
        f"variations were profitable; out of sample, {int((drift_oos['net_r'] > 0).sum())} of {len(drift_oos)} were. "
        "Results depend heavily on whether EURUSD is trending up.\n")

    add("## 7. Limitations\n")
    add("- Daily bars only: the intraday order of highs and lows is unknown. Same-day stop/target hits count as "
        "losses and breakout-day lows count against the trade, both conservative.")
    add("- Swap and commission are fixed assumptions; real long-EURUSD swap changed with interest rates.")
    add("- One instrument, one direction, a few dozen out-of-sample trades per run: small samples. Several variants "
        "were run (all shown above); picking the best-looking one after the fact is itself in-sample.")
    add("- A buy-only EURUSD strategy has little to do in long down-trends (2018, 2021-2022). Past behaviour does "
        "not guarantee future results.\n")
    (OUT / "REPORT.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
