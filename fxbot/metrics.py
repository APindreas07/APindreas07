"""Equity-curve scorecard and prop-firm (FTMO) rule checks.

Every backtest is re-scored on the same card, so runs are comparable:

    Growth       net profit, return, CAGR, expectancy (R), profit factor
    Risk         max drawdown from peak (worst intraday), lowest equity vs the
                 $9,000 FTMO floor, worst daily loss vs the $500 limit,
                 max losing streak, Ulcer index, longest time under water
    Smoothness   R^2 of the equity curve vs a straight line, K-ratio,
                 Sharpe / Sortino of daily mark-to-market returns, % positive months
"""

import numpy as np
import pandas as pd


def _streak(mask):
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def scorecard(trades, eq, account):
    init = account.initial
    out = {}
    if eq.empty:
        return out
    dates = pd.to_datetime(eq["date"])
    years = max((dates.iloc[-1] - dates.iloc[0]).days / 365.25, 1e-9)
    final = eq["balance"].iloc[-1]
    out["period"] = f"{dates.iloc[0]:%Y-%m-%d} -> {dates.iloc[-1]:%Y-%m-%d}"
    out["net_profit"] = final - init
    out["return_pct"] = (final / init - 1) * 100
    out["cagr_pct"] = ((final / init) ** (1 / years) - 1) * 100 if final > 0 else -100.0

    n = len(trades)
    out["trades"] = n
    out["trades_per_year"] = n / years
    if n:
        r = trades["r_net"]
        wins, losses = r[r > 0], r[r <= 0]
        out["win_rate_pct"] = len(wins) / n * 100
        out["avg_win_r"] = wins.mean() if len(wins) else 0.0
        out["avg_loss_r"] = losses.mean() if len(losses) else 0.0
        out["expectancy_r"] = r.mean()
        gl = -trades.loc[trades["net_pnl"] <= 0, "net_pnl"].sum()
        gw = trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum()
        out["profit_factor"] = gw / gl if gl > 0 else np.inf
        out["max_losing_streak"] = _streak(r <= 0)
        out["costs_usd"] = trades["commission"].sum() - trades["swap"].sum()
        out["swap_usd"] = trades["swap"].sum()
    else:
        for k in ("win_rate_pct", "avg_win_r", "avg_loss_r", "expectancy_r", "profit_factor",
                  "max_losing_streak", "costs_usd", "swap_usd"):
            out[k] = 0.0

    # Drawdown: running peak of close equity vs the worst intraday equity
    peak = eq["equity_close"].cummax().clip(lower=init)
    dd = eq["equity_low"] - peak
    out["max_dd_usd"] = -dd.min()
    out["max_dd_pct"] = -dd.min() / init * 100
    out["lowest_equity"] = eq["equity_low"].min()
    floor = init * (1 - account.max_loss_pct)
    out["ftmo_floor_buffer_usd"] = out["lowest_equity"] - floor
    daily_loss = (eq["day_start"] - eq["equity_low"]).clip(lower=0)
    out["worst_daily_loss_usd"] = daily_loss.max()
    breach = (eq["equity_low"] <= floor) | (daily_loss >= init * account.daily_loss_pct)
    out["ftmo_breach"] = bool(breach.any())
    out["ftmo_breach_date"] = str(pd.Timestamp(eq.loc[breach, "date"].iloc[0]).date()) if breach.any() else ""

    dd_close_pct = (eq["equity_close"] / eq["equity_close"].cummax() - 1) * 100
    out["ulcer_index"] = float(np.sqrt((dd_close_pct ** 2).mean()))
    under = eq["equity_close"] < eq["equity_close"].cummax() - 1e-9
    longest = cur = 0
    start = None
    for d, u in zip(dates, under):
        if u:
            start = start or d
            longest = max(longest, (d - start).days)
        else:
            start = None
    out["longest_underwater_days"] = longest

    y = eq["equity_close"].to_numpy()
    x = np.arange(len(y))
    if len(y) > 2 and np.ptp(y) > 0:
        slope, icpt = np.polyfit(x, y, 1)
        resid = y - (slope * x + icpt)
        out["equity_r2"] = 1 - resid.var() / y.var()
        se = np.sqrt((resid ** 2).sum() / (len(y) - 2) / ((x - x.mean()) ** 2).sum())
        out["k_ratio"] = slope / se / np.sqrt(len(y)) if se > 0 else 0.0
    else:
        out["equity_r2"] = out["k_ratio"] = 0.0
    ret = eq["equity_close"].pct_change().dropna()
    out["sharpe"] = ret.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0.0
    downside = ret[ret < 0].std()
    out["sortino"] = ret.mean() / downside * np.sqrt(252) if downside and downside > 0 else 0.0
    monthly = monthly_returns(eq)
    out["positive_months_pct"] = (monthly > 0).mean() * 100 if len(monthly) else 0.0
    out["exposure_pct"] = 0.0 if not n else trades["days_held"].sum() / len(eq) * 100
    return out


def monthly_returns(eq):
    s = eq.set_index(pd.to_datetime(eq["date"]))["equity_close"]
    month_end = s.resample("ME").last()
    prev = month_end.shift(1)
    prev.iloc[0] = s.iloc[0]
    return (month_end / prev - 1) * 100


FORMAT = [
    ("period", "Period", "{}"),
    ("net_profit", "Net profit", "${:,.0f}"),
    ("return_pct", "Return", "{:+.1f}%"),
    ("cagr_pct", "CAGR", "{:+.2f}%"),
    ("trades", "Trades", "{:d}"),
    ("trades_per_year", "Trades / year", "{:.1f}"),
    ("win_rate_pct", "Win rate", "{:.1f}%"),
    ("expectancy_r", "Expectancy / trade", "{:+.3f} R"),
    ("profit_factor", "Profit factor", "{:.2f}"),
    ("max_dd_pct", "Max drawdown (intraday, from peak)", "{:.2f}%"),
    ("lowest_equity", "Lowest equity (FTMO floor $9,000)", "${:,.0f}"),
    ("worst_daily_loss_usd", "Worst daily loss (limit $500)", "${:,.0f}"),
    ("ftmo_breach", "FTMO limit breached", "{}"),
    ("max_losing_streak", "Max losing streak", "{:d}"),
    ("ulcer_index", "Ulcer index", "{:.2f}"),
    ("longest_underwater_days", "Longest time under water", "{:d} days"),
    ("equity_r2", "Equity curve R^2 (smoothness)", "{:.2f}"),
    ("k_ratio", "K-ratio", "{:.3f}"),
    ("sharpe", "Sharpe (daily MTM)", "{:.2f}"),
    ("sortino", "Sortino", "{:.2f}"),
    ("positive_months_pct", "Positive months", "{:.0f}%"),
    ("exposure_pct", "Time in market", "{:.0f}%"),
    ("costs_usd", "Commission + swap paid", "${:,.0f}"),
]


def fmt(card, key):
    for k, _, f in FORMAT:
        if k == key:
            v = card.get(k, "")
            try:
                return f.format(int(v) if f.endswith(":d}") or "{:d}" in f else v)
            except (ValueError, TypeError):
                return str(v)
    return str(card.get(key, ""))


def cards_table(named_cards):
    """Markdown table: one column per named scorecard."""
    names = list(named_cards)
    lines = ["| Metric | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for k, label, _ in FORMAT:
        lines.append(f"| {label} | " + " | ".join(fmt(named_cards[n], k) for n in names) + " |")
    return "\n".join(lines)
