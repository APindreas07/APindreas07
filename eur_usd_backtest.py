# -*- coding: utf-8 -*-
"""EUR/USD backtest: daily EMA/RSI trend filter + hourly RSI pullback entry.

All price data comes from yfinance (EURUSD=X). Every trade outcome is
simulated deterministically by walking forward through the real hourly bars;
no random numbers or dummy data are used.

Default test period is 2024-01-01 to 2025-12-31. Yahoo only serves hourly
bars for roughly the last 730 days, so if the requested start is older than
that, the hourly simulation starts at the earliest date Yahoo can provide and
the script prints the exact range that was actually tested.

Outputs:
    - trades log printed to the console and saved to eur_usd_trades_log.csv
    - equity / cumulative-returns chart (with EUR/USD buy-and-hold benchmark)
      saved to eur_usd_returns_chart.png

Run:
    pip install yfinance pandas numpy matplotlib
    python eur_usd_backtest.py
    python eur_usd_backtest.py --start 2025-01-01 --end 2025-12-31
"""

import argparse

import matplotlib
matplotlib.use("Agg")  # render to file; works headless and in notebooks
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

TICKER = "EURUSD=X"
PIP = 0.0001
MAX_HOLD_BARS = 120  # 5 trading days of hourly bars
DEFAULT_START = "2024-01-01"
DEFAULT_END = "2025-12-31"
HOURLY_LIMIT_DAYS = 729  # Yahoo rejects 1h requests older than 730 days
DAILY_WARMUP_DAYS = 90   # extra daily history so EMA/RSI are settled on day one


# ---------------------------------------------------------------------------
# Indicators (plain pandas, so yfinance is the only data dependency)
# ---------------------------------------------------------------------------
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length=14):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


# ---------------------------------------------------------------------------
# Data download
# ---------------------------------------------------------------------------
def _calendar_date(ts, to_utc):
    """Tz-naive midnight date. Hourly bars are compared in UTC; daily bars keep
    the calendar date Yahoo labelled them with."""
    ts = pd.to_datetime(ts)
    if ts.dt.tz is not None:
        ts = (ts.dt.tz_convert("UTC") if to_utc else ts).dt.tz_localize(None)
    return ts.dt.normalize()


def _download(interval, start, end):
    df = yf.download(TICKER, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"),
                     interval=interval, auto_adjust=True, progress=False)
    if df.empty:
        raise RuntimeError(f"yfinance returned no {interval} data for {start.date()} -> "
                           f"{end.date()}. Check your connection or the date range.")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "timestamp"})
    return df[["timestamp", "Open", "High", "Low", "Close"]].dropna()


def load_data(start=DEFAULT_START, end=DEFAULT_END):
    """Download real EUR/USD bars from yfinance for the requested period.

    Daily bars (used for the trend filter) are available for the whole period.
    Hourly bars (used for entries/exits) are limited by Yahoo to ~730 days
    back from today, so the hourly start is clipped to that limit if needed.
    """
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    end_excl = end + pd.Timedelta(days=1)  # yfinance's end date is exclusive

    earliest_hourly = (pd.Timestamp.now().normalize()
                       - pd.Timedelta(days=HOURLY_LIMIT_DAYS))
    hourly_start = max(start, earliest_hourly)
    if hourly_start >= end_excl:
        raise RuntimeError(f"Yahoo only provides hourly data from {earliest_hourly.date()} "
                           f"onwards; the requested period ends {end.date()}.")
    if hourly_start > start:
        print(f"WARNING: Yahoo only serves hourly data from {earliest_hourly.date()} onwards. "
              f"Requested start {start.date()} -> hourly simulation starts {hourly_start.date()}.")

    print(f"Downloading {TICKER} daily data {start.date()} -> {end.date()} "
          f"(+{DAILY_WARMUP_DAYS}d indicator warm-up) ...")
    df_1d = _download("1d", start - pd.Timedelta(days=DAILY_WARMUP_DAYS), end_excl)
    df_1d["ema1"] = ema(df_1d["Close"], 1)
    df_1d["ema5"] = ema(df_1d["Close"], 5)
    df_1d["ema9"] = ema(df_1d["Close"], 9)
    df_1d["rsi14"] = rsi(df_1d["Close"], 14)

    print(f"Downloading {TICKER} hourly data {hourly_start.date()} -> {end.date()} ...")
    df_1h = _download("1h", hourly_start, end_excl)
    df_1h["rsi14"] = rsi(df_1h["Close"], 14)

    first, last = df_1h["timestamp"].iloc[0], df_1h["timestamp"].iloc[-1]
    print(f"Loaded {len(df_1d)} daily bars and {len(df_1h)} hourly bars "
          f"({first:%Y-%m-%d %H:%M} -> {last:%Y-%m-%d %H:%M}).")
    return df_1d, df_1h


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def run_backtest(df_1d, df_1h, initial_capital=10000.0, risk_pct=0.01, rr_ratio=3.0,
                 sl_pips=20, rsi_entry=40, fee_drag=2.0, spread_pips=1.5):
    df_1d = df_1d.copy()
    df_1h = df_1h.copy()

    spread_val = spread_pips * PIP
    sl_dist = sl_pips * PIP

    # Macro trend from the last *completed* daily bar before each hourly bar's
    # date, so an hourly bar never sees a daily close that hasn't happened yet.
    df_1d["macro_bull"] = ((df_1d["ema1"] > df_1d["ema5"]) &
                           (df_1d["ema5"] > df_1d["ema9"]) &
                           (df_1d["rsi14"] > 50))
    daily = pd.DataFrame({
        "date": _calendar_date(df_1d["timestamp"], to_utc=False),
        "macro_bull": df_1d["macro_bull"].values,
    }).sort_values("date")
    df_1h["date"] = _calendar_date(df_1h["timestamp"], to_utc=True)
    df_1h = pd.merge_asof(df_1h.sort_values("timestamp"), daily, on="date",
                          direction="backward", allow_exact_matches=False)
    df_1h["macro_bull"] = df_1h["macro_bull"].fillna(False).astype(bool)

    balance = initial_capital
    trades_log = []
    traded_days = set()

    h = df_1h.to_dict("records")
    n = len(h)
    i = 0
    while i < n - 1:
        row = h[i]
        if balance < initial_capital * 0.5:  # stop at 50% drawdown
            break

        if (row["date"] in traded_days or not row["macro_bull"]
                or pd.isna(row["rsi14"]) or row["rsi14"] >= rsi_entry):
            i += 1
            continue

        # BUY at the Ask (Close + spread)
        entry_price = row["Close"] + spread_val
        stop_loss = entry_price - sl_dist
        take_profit = entry_price + sl_dist * rr_ratio

        exit_idx, exit_price, exit_reason = None, None, None
        last_idx = min(i + MAX_HOLD_BARS, n - 1)
        for j in range(i + 1, last_idx + 1):
            bar = h[j]
            # Check SL before TP inside the same bar (conservative)
            if bar["Low"] <= stop_loss:
                exit_idx, exit_price, exit_reason = j, stop_loss, "STOP LOSS"
                break
            if bar["High"] >= take_profit:
                exit_idx, exit_price, exit_reason = j, take_profit, "TAKE PROFIT"
                break
        if exit_idx is None:
            # Neither level hit: close at market (Bid = Close) at the time limit
            exit_idx, exit_price = last_idx, h[last_idx]["Close"]
            exit_reason = "TIME EXIT" if last_idx == i + MAX_HOLD_BARS else "END OF DATA"

        # P&L scaled by how far price actually moved relative to the stop
        risk_amount = balance * risk_pct
        r_multiple = (exit_price - entry_price) / sl_dist
        net_pnl = risk_amount * r_multiple - fee_drag
        balance += net_pnl

        trades_log.append({
            "entry_time": row["timestamp"],
            "exit_time": h[exit_idx]["timestamp"],
            "type": "BUY",
            "entry_price": round(entry_price, 5),
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "exit_price": round(exit_price, 5),
            "exit_reason": exit_reason,
            "outcome": "WIN" if net_pnl > 0 else "LOSS",
            "pips": round((exit_price - entry_price) / PIP, 1),
            "r_multiple": round(r_multiple, 2),
            "net_pnl": round(net_pnl, 2),
            "balance": round(balance, 2),
        })
        traded_days.add(row["date"])
        # One position at a time: resume scanning after this trade closes
        i = exit_idx + 1

    trades_df = pd.DataFrame(trades_log)
    if not trades_df.empty:
        trades_df["return_pct"] = (trades_df["net_pnl"] /
                                   (trades_df["balance"] - trades_df["net_pnl"]) * 100).round(3)
        trades_df["cumulative_return_pct"] = ((trades_df["balance"] - initial_capital) /
                                              initial_capital * 100).round(3)
    return trades_df, balance


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def buy_and_hold(df_1h):
    """EUR/USD buy-and-hold cumulative return (%) over the tested hourly bars."""
    close = df_1h.set_index("timestamp")["Close"]
    return (close / close.iloc[0] - 1) * 100


def summarize(trades_df, df_1h, initial_capital, final_balance):
    total_return = (final_balance - initial_capital) / initial_capital * 100
    first, last = df_1h["timestamp"].iloc[0], df_1h["timestamp"].iloc[-1]
    print("\n=== SUMMARY ===")
    print(f"Tested period   : {first:%Y-%m-%d} -> {last:%Y-%m-%d} (real {TICKER} bars from yfinance)")
    print(f"Initial Capital : ${initial_capital:,.2f}")
    print(f"Final Balance   : ${final_balance:,.2f}")
    print(f"Total Return    : {total_return:,.2f}%")
    print(f"Buy & Hold      : {buy_and_hold(df_1h).iloc[-1]:,.2f}% (EUR/USD spot, same period)")
    if final_balance < initial_capital * 0.5:
        print("NOTE: trading stopped early after the 50% drawdown limit was hit.")
    if trades_df.empty:
        print("No trades were triggered during the backtest period.")
        return
    wins = (trades_df["outcome"] == "WIN").sum()
    equity = pd.concat([pd.Series([initial_capital]), trades_df["balance"]], ignore_index=True)
    max_dd = ((equity - equity.cummax()) / equity.cummax()).min() * 100
    gross_win = trades_df.loc[trades_df["net_pnl"] > 0, "net_pnl"].sum()
    gross_loss = -trades_df.loc[trades_df["net_pnl"] <= 0, "net_pnl"].sum()
    profit_factor = gross_win / gross_loss if gross_loss > 0 else np.inf
    print(f"Total Trades    : {len(trades_df)}")
    print(f"Win Rate        : {wins / len(trades_df) * 100:.1f}%")
    print(f"Profit Factor   : {profit_factor:.2f}")
    print(f"Max Drawdown    : {max_dd:.2f}%")
    print("Exit reasons    : " + ", ".join(f"{k}={v}" for k, v in
                                           trades_df["exit_reason"].value_counts().items()))


def plot_returns(trades_df, df_1h, initial_capital, path="eur_usd_returns_chart.png"):
    first = df_1h["timestamp"].iloc[0]
    # Start every curve at the beginning of the tested period
    times = pd.concat([pd.Series([first]), pd.to_datetime(trades_df["exit_time"])],
                      ignore_index=True)
    balance = pd.concat([pd.Series([initial_capital]), trades_df["balance"]], ignore_index=True)
    cum = pd.concat([pd.Series([0.0]), trades_df["cumulative_return_pct"]], ignore_index=True)
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True,
                             gridspec_kw={"height_ratios": [2, 2, 1]})

    axes[0].plot(times, balance, marker="o", markersize=3,
                 color="dodgerblue", linewidth=1.8)
    axes[0].axhline(initial_capital, color="grey", linestyle="--", alpha=0.6)
    axes[0].set_title("Equity Curve (USD)", fontweight="bold")
    axes[0].set_ylabel("Balance ($)")

    bh = buy_and_hold(df_1h)
    axes[1].plot(times, cum, color="forestgreen", linewidth=1.8, label="Strategy")
    axes[1].plot(bh.index, bh.values, color="slategrey", linewidth=1.0, alpha=0.8,
                 label="EUR/USD buy & hold")
    axes[1].fill_between(times, cum, 0, where=cum >= 0, color="forestgreen", alpha=0.15)
    axes[1].fill_between(times, cum, 0, where=cum < 0, color="crimson", alpha=0.15)
    axes[1].axhline(0, color="red", linestyle="--", alpha=0.5, label="Break even (0%)")
    axes[1].set_title("Cumulative Return (%)", fontweight="bold")
    axes[1].set_ylabel("Return (%)")
    axes[1].legend()

    colors = np.where(trades_df["return_pct"] >= 0, "forestgreen", "crimson")
    axes[2].bar(pd.to_datetime(trades_df["exit_time"]), trades_df["return_pct"],
                color=colors, width=1.0)
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_title("Per-Trade Return (%)", fontweight="bold")
    axes[2].set_ylabel("Return (%)")
    axes[2].set_xlabel("Exit time")

    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.5)
    last = df_1h["timestamp"].iloc[-1]
    fig.suptitle(f"{TICKER} strategy backtest, {first:%Y-%m-%d} to {last:%Y-%m-%d} "
                 f"(real yfinance hourly data)", fontsize=14)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"Returns chart saved to {path}")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default=DEFAULT_START, help="first date (YYYY-MM-DD)")
    ap.add_argument("--end", default=DEFAULT_END, help="last date, inclusive (YYYY-MM-DD)")
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--risk-pct", type=float, default=0.01, help="fraction of balance risked per trade")
    ap.add_argument("--rr", type=float, default=3.0, help="reward:risk ratio")
    ap.add_argument("--sl-pips", type=float, default=20)
    ap.add_argument("--rsi-entry", type=float, default=40, help="enter when hourly RSI is below this")
    ap.add_argument("--spread-pips", type=float, default=1.5)
    ap.add_argument("--fee", type=float, default=2.0, help="fixed cost per trade in USD")
    return ap.parse_args()


def main():
    args = parse_args()
    df_1d, df_1h = load_data(args.start, args.end)

    trades_df, final_balance = run_backtest(
        df_1d, df_1h,
        initial_capital=args.capital,
        risk_pct=args.risk_pct,
        rr_ratio=args.rr,
        sl_pips=args.sl_pips,
        rsi_entry=args.rsi_entry,
        fee_drag=args.fee,
        spread_pips=args.spread_pips,
    )

    print(f"\n=== TRADES LOG ({len(trades_df)} trades) ===")
    if not trades_df.empty:
        with pd.option_context("display.max_rows", None, "display.width", 220,
                               "display.max_columns", None):
            print(trades_df.to_string(index=False))
        trades_df.to_csv("eur_usd_trades_log.csv", index=False)
        print("Trades log saved to eur_usd_trades_log.csv")

    summarize(trades_df, df_1h, args.capital, final_balance)

    if not trades_df.empty:
        plot_returns(trades_df, df_1h, args.capital)

    return trades_df, final_balance


if __name__ == "__main__":
    main()
