"""FTMO 2-Step ($10k) strategy study for EURUSD: research -> selection -> sizing -> lifecycle.

    python -m fxbot.ftmo_study

Method (all deterministic, real TradeStation daily bars, no random numbers):
  1. Screen 22 textbook strategy families on 2018-2021 (in-sample) and 2022-2025
     (out-of-sample), under two readings of daily bars.
  2. Scan simple daily effects for anything significant in *both* halves.
  3. Select one system with a rule fixed in advance, using 2018-2021 only.
  4. Risk frontier: compounding risk-per-trade from 0.5% to 10% with FTMO-aware
     caps; monthly return vs breaches.
  5. Lifecycle: start a Challenge every month, then Verification, then 12 funded
     months with no withdrawals; count passes, breaches and funded growth.
Writes results/ftmo_study/REPORT.md, charts and CSVs.
"""

import numpy as np
import pandas as pd

from . import plots
from .data import ROOT, load_daily
from .ftmo import FTMORules, FTMOSim, Sizing, monthly
from .indicators import atr, rsi
from .systems import System, candidates, features

OUT = ROOT / "results" / "ftmo_study"
IS_START, IS_END = "2018-01-01", "2021-12-31"
OOS_START, OOS_END = "2022-01-01", "2025-12-31"
RAW = Sizing(risk_pct=0.01, floor_buffer_pct=-10, daily_buffer_pct=-10, daily_guard=False)   # no FTMO caps: pure edge measurement
RISKS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]

SOURCES = [
    ("FTMO Trading Objectives", "https://ftmo.com/en/trading-objectives/"),
    ("FTMO Academy: Maximum Daily Loss", "https://academy.ftmo.com/lesson/maximum-daily-loss/"),
    ("FTMO FAQ: Swing account type", "https://ftmo.com/en/faq/ftmo-swing-account-type/"),
    ("FTMO FAQ: closing positions overnight / weekend",
     "https://ftmo.com/en/faq/do-i-have-to-close-my-positions-overnight-or-before-the-weekend/"),
    ("FTMO Forbidden Trading Practices", "https://ftmo.com/en/forbidden-trading-practices/"),
    ("FTMO Scaling and Reward Growth Plan", "https://ftmo.com/en/reward-growth-and-scaling-plan/"),
    ("FTMO FAQ: how do I withdraw my reward", "https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/"),
    ("FTMO Academy: Minimum Trading Days", "https://academy.ftmo.com/lesson/minimum-trading-days/"),
    ("Propvator: FTMO commissions, spreads and swaps", "https://propvator.com/blog/ftmo-trading-conditions/"),
    ("PropNavi: FTMO scaling plan explained", "https://propnavi.io/en/blog/ftmo-scaling-plan-explained/"),
]


def r_stats(trades):
    if trades.empty:
        return dict(trades=0, total_r=0.0, max_dd_r=0.0, pf=np.nan, win_pct=np.nan, exp_r=np.nan)
    r = trades["r_net"]
    cum = r.cumsum()
    dd = (cum.cummax().clip(lower=0) - cum).max()
    gl = -r[r <= 0].sum()
    return dict(trades=len(r), total_r=r.sum(), max_dd_r=dd, pf=r[r > 0].sum() / gl if gl else np.inf,
                win_pct=(r > 0).mean() * 100, exp_r=r.mean())


def screen(feat):
    rows = []
    for model in ("path", "worst"):
        sim = FTMOSim(feat, bar_model=model)
        for s in candidates():
            row = {"system": s.label(), "bar model": model, "_sys": s}
            for tag, (a, b) in (("IS", (IS_START, IS_END)), ("OOS", (OOS_START, OOS_END))):
                st = r_stats(sim.run(s, RAW, a, b, stop_on_breach=False)[0])
                row.update({f"{tag} trades": st["trades"], f"{tag} R": st["total_r"],
                            f"{tag} DD R": st["max_dd_r"], f"{tag} PF": st["pf"]})
            rows.append(row)
    return pd.DataFrame(rows)


def select(scr):
    """Rule fixed in advance: on 2018-2021 only (path model), highest R / max-DD-R among
    systems with >= 30 trades and profit factor >= 1.2. Returns (system, reason)."""
    is_ = scr[scr["bar model"] == "path"].copy()
    ok = is_[(is_["IS trades"] >= 30) & (is_["IS PF"] >= 1.2)]
    if ok.empty:
        return None, "no system met the in-sample bar"
    ok = ok.assign(score=ok["IS R"] / ok["IS DD R"].clip(lower=1))
    best = ok.sort_values("score", ascending=False).iloc[0]
    return best["_sys"], f"in-sample R/DD {best['score']:.2f}, PF {best['IS PF']:.2f}, {best['IS trades']} trades"


def effect_scan(df0):
    df = df0.copy()
    c = df["close"]
    df["next1"] = (c.shift(-1) - c) / 1e-4
    df["next3"] = (c.shift(-3) - c) / 1e-4
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    df["ibs"] = (c - df["low"]) / rng
    df["rsi2"] = rsi(c, 2)
    up, dn = (c > c.shift()).astype(int), (c < c.shift()).astype(int)
    df["up_streak"] = up.groupby((up != up.shift()).cumsum()).cumsum() * up
    df["dn_streak"] = dn.groupby((dn != dn.shift()).cumsum()).cumsum() * dn
    a = atr(df, 14).shift()
    move = c - c.shift()
    conds = {
        "closed in bottom 20% of range": df["ibs"] < 0.2, "closed in top 20% of range": df["ibs"] > 0.8,
        "RSI(2) < 10": df["rsi2"] < 10, "RSI(2) > 90": df["rsi2"] > 90,
        "3+ down closes": df["dn_streak"] >= 3, "3+ up closes": df["up_streak"] >= 3,
        "down > 1 ATR": move < -a, "up > 1 ATR": move > a,
        "Friday (next = Monday)": df["date"].dt.dayofweek == 4,
        "last day of month": df["date"].shift(-1).dt.month != df["date"].dt.month,
        "all days": pd.Series(True, index=df.index),
    }
    halves = {"IS": (df["date"] >= IS_START) & (df["date"] <= IS_END),
              "OOS": (df["date"] >= OOS_START) & (df["date"] <= OOS_END)}
    rows = []
    for name, m in conds.items():
        row = {"condition": name}
        for tag, h in halves.items():
            for col in ("next1", "next3"):
                x = df.loc[m & h, col].dropna()
                t = x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else np.nan
                row[f"{tag} {col} pips"] = x.mean()
                row[f"{tag} {col} t"] = t
            row[f"{tag} n"] = int((m & h).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def frontier(sim, sysm, start, end):
    rows = []
    for rp in RISKS:
        tr, eq, oc = sim.run(sysm, Sizing(risk_pct=rp), start, end)
        m = monthly(eq) if not eq.empty else pd.Series(dtype=float)
        final = eq["balance"].iloc[-1] if not eq.empty else np.nan
        months = max(len(m), 1)
        peak = eq["equity_close"].cummax()
        rows.append({
            "risk per trade": f"{rp * 100:g}%",
            "_risk": rp,
            "breached": oc.get("breach_date", "no"),
            "months traded": len(m),
            "final balance": final,
            "avg month (compounded)": ((final / 10_000) ** (1 / months) - 1) * 100 if final > 0 else np.nan,
            "best month": m.max() if len(m) else np.nan,
            "worst month": m.min() if len(m) else np.nan,
            "months >= 7%": int((m >= 7).sum()),
            "max drawdown %": ((peak - eq["equity_low"]) / peak).max() * 100 if not eq.empty else np.nan,
            "trades": len(tr),
        })
    return pd.DataFrame(rows)


def lifecycles(sim, sysm, first="2018-01-01", last="2025-11-01"):
    rows = []
    for rp in RISKS:
        for st in pd.date_range(first, last, freq="MS"):
            lc = sim.lifecycle(sysm, Sizing(risk_pct=rp), st)
            lc["risk"] = rp
            rows.append(lc)
    return pd.DataFrame(rows)


def lifecycle_summary(lc):
    rows = []
    for rp, g in lc.groupby("risk"):
        n = len(g)
        p1 = (g["phase1"] == "PASS").sum()
        p1f = (g["phase1"] == "FAIL").sum()
        p2 = (g.get("phase2") == "PASS").sum() if "phase2" in g else 0
        p2f = (g.get("phase2") == "FAIL").sum() if "phase2" in g else 0
        fd = g[g.get("funded").isin(["SURVIVED", "BREACHED"])] if "funded" in g else g.iloc[0:0]
        surv = (fd["funded"] == "SURVIVED").sum() if len(fd) else 0
        rows.append({
            "risk per trade": f"{rp * 100:g}%",
            "challenge starts": n,
            "phase 1 passed": int(p1), "phase 1 failed": int(p1f),
            "phase 2 passed": int(p2), "phase 2 failed": int(p2f),
            "funded years completed": len(fd),
            "funded year survived": int(surv),
            "median funded 12m return %": fd.loc[fd["funded"] == "SURVIVED", "funded_return_pct"].median()
            if surv else np.nan,
            "median avg month (funded) %": fd["funded_avg_month_pct"].median() if surv else np.nan,
            "median days to funded": g["days_to_funded"].median() if "days_to_funded" in g else np.nan,
        })
    return pd.DataFrame(rows)


def requirement_table():
    """What a strategy needs to average X% a month at 1:3 reward:risk."""
    rows = []
    for target in (10.0, 7.5):
        for risk in (1.0, 2.0):
            r_needed = np.log1p(target / 100) / np.log1p(risk / 100)   # R per month, compounding
            for trades in (5, 10, 20):
                exp = r_needed / trades
                win = (exp + 1) / 4 * 100                               # E = 3w - (1-w) at 1:3
                rows.append({"target / month": f"{target:g}%", "risk / trade": f"{risk:g}%",
                             "R needed / month": r_needed, "trades / month": trades,
                             "expectancy needed (R)": exp, "win rate needed at 1:3": win})
    return pd.DataFrame(rows)


def md(df, fmt="{:.2f}"):
    cols = [c for c in df.columns if not str(c).startswith("_")]
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append("" if np.isnan(v) else fmt.format(v))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    daily = load_daily()
    feat = features(daily)
    rules = FTMORules()
    sim = FTMOSim(feat, rules, "path")

    scr = screen(feat)
    scan = effect_scan(daily)
    chosen, why = select(scr)
    oos_best = scr[scr["bar model"] == "path"].sort_values("OOS R", ascending=False).iloc[0]["_sys"]
    legacy = next(s for s in candidates() if s.family == "pullback" and s.direction == "long")
    named = []
    if chosen is not None:
        named.append(("Selected (in-sample rule)", chosen))
    named.append(("Best out-of-sample (hindsight)", oos_best))
    named.append(("Original pullback, long only", legacy))
    systems = {}
    for name, s in named:                      # merge names when two roles are the same system
        prev = next((k for k, v in systems.items() if v == s), None)
        if prev:
            systems[f"{prev} = {name}"] = systems.pop(prev)
        else:
            systems[name] = s

    fronts, lcs, curves = {}, {}, {}
    for name, s in systems.items():
        fronts[name] = frontier(sim, s, IS_START, OOS_END)
        lc = lifecycles(sim, s)
        lcs[name] = (lc, lifecycle_summary(lc))
    main_sys = chosen if chosen is not None else oos_best

    # equity curves at 1% and 5% risk for the selected system, full period
    for rp in (0.01, 0.05):
        _, eq, _ = sim.run(main_sys, Sizing(risk_pct=rp), IS_START, OOS_END)
        curves[f"{rp * 100:g}% risk per trade"] = eq
    tr_main, _, _ = sim.run(main_sys, Sizing(risk_pct=0.01), IS_START, OOS_END)
    tr_main.to_csv(OUT / "trades_selected_1pct.csv", index=False)
    scr.drop(columns=["_sys"]).to_csv(OUT / "screen.csv", index=False)
    scan.to_csv(OUT / "effect_scan.csv", index=False)
    for name, f in fronts.items():
        f.drop(columns=["_risk"]).assign(system=name).to_csv(
            OUT / f"frontier_{systems[name].family}_{systems[name].direction}.csv", index=False)
    for name, (lc, _) in lcs.items():
        lc.to_csv(OUT / f"lifecycles_{systems[name].family}_{systems[name].direction}.csv", index=False)

    rules_eq = FTMORules()
    plots.equity_chart(curves, type("A", (), {"initial": rules_eq.initial, "max_loss_pct": rules_eq.max_loss_pct,
                                             "target_pct": rules_eq.phase1_target})(),
                       OUT / "equity_selected.png",
                       f"{main_sys.name}, FTMO-aware compounding, 2018-2025 (stops at a rule breach)")
    frontier_chart(fronts, OUT / "risk_frontier.png")
    write_report(rules, scr, scan, chosen, why, oos_best, systems, fronts, lcs, main_sys)
    print(f"Report written to {OUT / 'REPORT.md'}")


def frontier_chart(fronts, path):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plots._fig(1, 2, figsize=(12, 4.2))
    for k, (name, f) in enumerate(fronts.items()):
        x = f["_risk"] * 100
        a1.plot(x, f["avg month (compounded)"], color=plots.SERIES[k], linewidth=2, marker="o",
                markersize=5, label=plots._t(name))
        breached = f["breached"] != "no"
        a2.plot(x, f["max drawdown %"], color=plots.SERIES[k], linewidth=2, marker="o", markersize=5,
                label=plots._t(name))
        a1.plot(x[breached], f.loc[breached, "avg month (compounded)"], linestyle="none", marker="x",
                markersize=9, color=plots.TEXT)
    for y, lab in ((10, "10%/month goal"), (7.5, "7.5%/month")):
        a1.axhline(y, color=plots.LIMIT, linewidth=0.9, linestyle=(0, (4, 3)))
        a1.annotate(lab, (0.01, y), xycoords=("axes fraction", "data"), xytext=(0, 3),
                    textcoords="offset points", fontsize=8, color=plots.TEXT_2)
    a2.axhline(10, color=plots.LIMIT, linewidth=0.9, linestyle=(0, (4, 3)))
    a2.annotate("FTMO 10% max loss", (0.01, 10), xycoords=("axes fraction", "data"), xytext=(0, 3),
                textcoords="offset points", fontsize=8, color=plots.TEXT_2)
    a1.set_title("Average month, compounded (x = FTMO breach)", loc="left", fontsize=10)
    a2.set_title("Worst drawdown from peak, %", loc="left", fontsize=10)
    for a in (a1, a2):
        a.set_xlabel("Risk per trade, % of balance", color=plots.TEXT_2)
        plots._style(a)
    a1.set_ylabel("% per month", color=plots.TEXT_2)
    a1.legend(frameon=False, fontsize=8, loc="upper left")
    fig.suptitle("EURUSD 2018-2025, FTMO 2-Step rules, compounding", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=plots.SURFACE)
    plt.close(fig)


def write_report(rules, scr, scan, chosen, why, oos_best, systems, fronts, lcs, main_sys):
    L = []
    add = L.append
    add("# EURUSD strategy for the FTMO 2-Step $10,000 Challenge: research report\n")
    add("*Generated by `python -m fxbot.ftmo_study` from real TradeStation EURUSD daily bars "
        "(2017-11 to 2025-12). No random numbers. Every table is recomputed on each run.*\n")

    add("## 1. FTMO rules implemented\n")
    add("| Rule | Value used | How it is simulated |\n|---|---|---|")
    add(f"| Phase 1 (Challenge) target | 10% ($1,000) | pass when flat with balance >= $11,000 and >= {rules.min_trading_days} trading days |")
    add(f"| Phase 2 (Verification) target | 5% ($500) | fresh $10,000; pass at $10,500 and >= {rules.min_trading_days} trading days |")
    add("| Time limit | none | phases run until pass, breach or end of data |")
    add("| Max Loss | 10%, static | equity including open trades, at each day's worst price, must stay above $9,000 |")
    add("| Max Daily Loss | 5% ($500) | from the higher of balance and equity at the start of the day, incl. open losses, commission and swap |")
    add("| Minimum trading days | 4 per phase | a day with a new position; if the target is hit earlier the bot places micro trades on the remaining days |")
    add("| Account type | Swing | overnight and weekend holding allowed; forex leverage 1:30 (lot size capped) |")
    add(f"| Commission | ${rules.commission_per_lot:g}/lot round turn | charged per trade |")
    add(f"| Spread + slippage | {rules.spread_pips:g} pip | buys at the Ask, sells at the Bid |")
    add(f"| Swap | long {rules.swap_long:+g}, short {rules.swap_short:+g} USD/lot/night | assumption: check the terminal's swap tab |")
    add("| Funded account | 80% split, payouts optional (first after 14 days), fee refunded with first payout | per your plan: **no withdrawals for 12 months**, profits compound |")
    add("| Scaling plan | +25% balance every 4 months | needs 10% growth **and 2 payouts** in 4 months, so it cannot trigger while not withdrawing |")
    add("| Forbidden practices | no latency/price-feed exploits, no hedging across accounts, no >2,000 server requests/day | a daily-bar swing bot is far from all of these |")
    add("\nSources (FTMO's site is not reachable from the research environment, so the rules were cross-checked "
        "across these pages via search):\n")
    for t, u in SOURCES:
        add(f"- [{t}]({u})")
    add("")

    add("## 2. Compounding and rule-aware position sizing\n")
    add("- Risk per trade = X% of the **current balance** (compounding; no withdrawals).")
    add("- Capped so a normal stop-out can never break a rule: never more than (balance - $9,000 - 1% buffer), and never "
        "more than what is left of today's $500 daily budget minus a 1% buffer. Only a price gap through the stop can breach.")
    add("- **Equity protector:** FTMO's daily loss counts floating profit given back (it is measured from the higher of "
        "balance and equity at the day's start). A swing trade that is +$800 in the morning and then stops out has lost "
        "$1,200 'today'. So every open trade is closed if today's loss reaches the $500 limit minus the 1% buffer.")
    add("- Lot size is also capped by the Swing account's 1:30 leverage and rounded down to 0.01 lot.")
    add("- The floor stays at $9,000 as the balance grows, so compounding widens the cushion: at $12,000 the account "
        "can absorb a $3,000 drawdown before touching the floor.\n")

    add("## 3. Can a daily EURUSD strategy earn 7-10% a month? What it would take\n")
    add("Required edge to average the target per month at 1:3 reward:risk (compounding):\n")
    add(md(requirement_table()) + "\n")

    add("## 4. Strategy research\n")
    add("### 4a. Screen of 22 textbook systems\n")
    add(f"In-sample {IS_START[:4]}-{IS_END[:4]}, out-of-sample {OOS_START[:4]}-{OOS_END[:4]}. Results in R "
        "(multiples of the amount risked), before any FTMO caps. `path` assumes open-low-high-close on up days and "
        "open-high-low-close on down days; `worst` assumes the adverse extreme always comes first.\n")
    add(md(scr[scr["bar model"] == "path"].drop(columns=["bar model"]), "{:.2f}") + "\n")
    both = scr[scr["bar model"] == "path"]
    n_both = int(((both["IS R"] > 0) & (both["OOS R"] > 0)).sum())
    add(f"**Systems profitable in both halves: {n_both} of {len(both)}.**\n")
    add("<details><summary>Same screen with the worst-case bar reading</summary>\n")
    add(md(scr[scr["bar model"] == "worst"].drop(columns=["bar model"]), "{:.2f}") + "\n")
    add("</details>\n")

    add("### 4b. Effect scan (average next-day and next-3-day move, pips, with t-statistics)\n")
    cols = ["condition", "IS n", "IS next1 pips", "IS next1 t", "OOS n", "OOS next1 pips", "OOS next1 t",
            "IS next3 t", "OOS next3 t"]
    add(md(scan[cols], "{:.1f}") + "\n")
    sig = scan[(scan["IS next1 t"].abs() >= 2) & (scan["OOS next1 t"].abs() >= 2) &
               (np.sign(scan["IS next1 t"]) == np.sign(scan["OOS next1 t"]))]
    add(f"Effects significant (|t| >= 2) with the same sign in both halves: "
        f"**{', '.join(sig['condition']) if len(sig) else 'none'}**.\n")

    add("### 4c. Selection (rule fixed in advance, in-sample only)\n")
    add("Rule: highest in-sample R / max drawdown R among systems with at least 30 trades and profit factor >= 1.2.\n")
    if chosen is not None:
        row = both[both["system"] == chosen.label()].iloc[0]
        add(f"Selected: **{chosen.label()}** ({why}). Out of sample it made **{row['OOS R']:+.1f}R** "
            f"(profit factor {row['OOS PF']:.2f}).\n")
    else:
        add(f"No system passed the in-sample rule ({why}).\n")
    add(f"For comparison the best out-of-sample system, picked with hindsight, was **{oos_best.label()}**.\n")

    add("## 5. Risk frontier: monthly return vs FTMO breaches (2018-2025, compounding)\n")
    add("One continuous account from January 2018, run until a rule breach (then it stops, as FTMO would close it).\n")
    add("![Risk frontier](risk_frontier.png)\n")
    for name, f in fronts.items():
        add(f"**{name}: {systems[name].label()}**\n")
        add(md(f, "{:.2f}") + "\n")

    add("## 6. Full FTMO lifecycle simulation\n")
    add("A new Challenge started on the first trading day of every month (Jan 2018 to Nov 2025). "
        "Pass Phase 1 -> Phase 2 on a fresh $10,000 -> 12 funded months, no withdrawals.\n")
    for name, (_, summ) in lcs.items():
        add(f"**{name}**\n")
        add(md(summ, "{:.1f}") + "\n")
    add("![Equity](equity_selected.png)\n")

    add("## 7. Conclusions\n")
    best_month = max(f["avg month (compounded)"].max() for f in fronts.values())
    safe = []
    for name, f in fronts.items():
        ok = f[f["breached"] == "no"]
        if len(ok):
            safe.append((name, ok["avg month (compounded)"].max(), ok["risk per trade"].iloc[ok["avg month (compounded)"].argmax()]))
    add(f"- Highest average month achieved by any system at any risk level: **{best_month:.2f}%**.")
    for name, v, rp in safe:
        add(f"- {name}: best average month without an FTMO breach over 2018-2025: **{v:.2f}%** (at {rp} risk).")
    cap = (rules.daily_loss_pct - 0.01) * 100
    add(f"- FTMO's 5% daily loss limit caps a single trade at about {cap:g}% risk (keeping a 1% buffer), so "
        f"settings above {cap:g}% behave identically: the rules themselves stop you from sizing up further.")
    n_breach = sum(int((f["breached"] != "no").sum()) for f in fronts.values())
    lc_best = max((summ["median avg month (funded) %"].max() for _, summ in lcs.values()), default=np.nan)
    add(f"- Best median month in a funded year (lifecycle, any system, any risk): **{lc_best:.2f}%**.")
    add("- 10% or 7-8% a month is **not supported by EURUSD daily data**: it needs roughly 10x the edge any tested "
        "system showed. " + (f"Raising risk to chase it breached the 10% max loss in {n_breach} of the frontier runs "
        "(x marks)." if n_breach else "With the caps and the equity protector no frontier run breached, but raising "
        "risk stops adding return once the daily-loss cap binds: the edge, not the sizing, is the limit."))
    add("- What would have to change to aim higher: intraday data (1H/5M entries and exits, many more trades), "
        "several uncorrelated pairs/instruments, and an edge validated out of sample before sizing up.\n")

    add("## 8. Limitations\n")
    add("- Daily bars: the order of highs and lows inside a day is assumed (see 4a for the worst-case reading).")
    add("- FTMO's day resets at midnight Prague; the data's day at 17:00 New York (1 hour apart).")
    add("- Swap is a fixed assumption; spread 1 pip; commission $5/lot. Real fills vary.")
    add("- Challenge starts overlap in time, so the lifecycle counts are not independent trials.")
    (OUT / "REPORT.md").write_text("\n".join(L))


if __name__ == "__main__":
    main()
