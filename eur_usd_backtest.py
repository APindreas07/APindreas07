# -*- coding: utf-8 -*-
"""EUR/USD daily pullback backtest on TradeStation historical data.

Strategy (long only, one position at a time):
    - Trend filter (previous day's close): EMA1 > EMA5 > EMA9 and RSI(14) > 50
    - Pullback trigger (today's close):    RSI(3) < 40
    - Entry: next day's open + spread (buying at the Ask)
    - Stop:  entry - ATR(14) * atr_mult     Target: entry + stop distance * rr
    - Exit:  stop or target touched by the daily High/Low, otherwise at the close
             after max_hold days. If a day touches both, the stop is assumed to
             hit first (conservative). A day that opens beyond a level fills at
             the open (models weekend/overnight gaps).

Price data: data/eurusd_daily_tradestation.csv, real EURUSD daily bars pulled
from the TradeStation market-data API (get-bars, Daily). No random numbers,
no synthetic prices: every trade is replayed bar by bar from that file.

Outputs:
    - trades log printed to the console and saved to eur_usd_trades_log.csv
    - equity / cumulative-return chart (with EUR/USD buy-and-hold benchmark)
      saved to eur_usd_returns_chart.png

Run:
    pip install pandas numpy matplotlib
    python eur_usd_backtest.py
    python eur_usd_backtest.py --start 2025-01-01 --end 2025-12-31 --rr 2
"""

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # render to file; works headless and in notebooks
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

SYMBOL = "EURUSD"
PIP = 0.0001
DATA_FILE = Path(__file__).resolve().parent / "data" / "eurusd_daily_tradestation.csv"
DEFAULT_START = "2024-01-01"
DEFAULT_END = "2025-12-31"


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------
def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length):
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False, min_periods=length).mean()
    return 100 - (100 / (1 + gain / loss))


def atr(df, length):
    prev_close = df["close"].shift()
    true_range = pd.concat([df["high"] - df["low"],
                            (df["high"] - prev_close).abs(),
                            (df["low"] - prev_close).abs()], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_data(path=DATA_FILE):
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    df["ema1"] = ema(df["close"], 1)
    df["ema5"] = ema(df["close"], 5)
    df["ema9"] = ema(df["close"], 9)
    df["rsi14"] = rsi(df["close"], 14)
    df["rsi3"] = rsi(df["close"], 3)
    df["atr14"] = atr(df, 14)
    print(f"Loaded {len(df)} {SYMBOL} daily bars from {Path(path).name} "
          f"({df['date'].iloc[0]:%Y-%m-%d} -> {df['date'].iloc[-1]:%Y-%m-%d}).")
    return df


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------
def run_backtest(df, start=DEFAULT_START, end=DEFAULT_END, initial_capital=10000.0,
                 risk_pct=0.01, rr_ratio=3.0, atr_mult=1.0, rsi_entry=40, max_hold=5,
                 fee_drag=2.0, spread_pips=1.5):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    spread_val = spread_pips * PIP

    trend = ((df["ema1"] > df["ema5"]) & (df["ema5"] > df["ema9"]) & (df["rsi14"] > 50))
    # Trend from the previous day, pullback on the signal day; both are known
    # at the signal day's close, and the trade is entered at the next open.
    signal = trend.shift(1, fill_value=False) & (df["rsi3"] < rsi_entry) & df["atr14"].notna()

    in_period = (df["date"] >= start) & (df["date"] <= end)
    last_idx = int(np.flatnonzero(in_period)[-1])

    balance = initial_capital
    trades_log = []
    bars = df.to_dict("records")
    i = 0
    while i < last_idx:
        if balance < initial_capital * 0.5:  # stop at 50% drawdown
            break
        e = i + 1  # entry bar
        if not signal.iloc[i] or not in_period.iloc[e]:
            i += 1
            continue

        entry_price = bars[e]["open"] + spread_val
        sl_dist = bars[i]["atr14"] * atr_mult
        stop_loss = entry_price - sl_dist
        take_profit = entry_price + sl_dist * rr_ratio

        exit_idx, exit_price, exit_reason = None, None, None
        hold_end = min(e + max_hold - 1, last_idx)
        for j in range(e, hold_end + 1):
            bar = bars[j]
            if j > e and bar["open"] <= stop_loss:
                exit_idx, exit_price, exit_reason = j, bar["open"], "STOP (GAP)"
                break
            if j > e and bar["open"] >= take_profit:
                exit_idx, exit_price, exit_reason = j, bar["open"], "TARGET (GAP)"
                break
            if bar["low"] <= stop_loss:
                exit_idx, exit_price, exit_reason = j, stop_loss, "STOP LOSS"
                break
            if bar["high"] >= take_profit:
                exit_idx, exit_price, exit_reason = j, take_profit, "TAKE PROFIT"
                break
        if exit_idx is None:
            exit_idx, exit_price = hold_end, bars[hold_end]["close"]
            exit_reason = "TIME EXIT" if hold_end == e + max_hold - 1 else "END OF PERIOD"

        risk_amount = balance * risk_pct
        units = risk_amount / sl_dist  # EUR bought so a full stop loses risk_amount
        net_pnl = units * (exit_price - entry_price) - fee_drag
        balance += net_pnl

        trades_log.append({
            "signal_date": bars[i]["date"].date(),
            "entry_date": bars[e]["date"].date(),
            "exit_date": bars[exit_idx]["date"].date(),
            "days_held": exit_idx - e + 1,
            "type": "BUY",
            "lots": round(units / 100_000, 2),
            "entry_price": round(entry_price, 5),
            "stop_loss": round(stop_loss, 5),
            "take_profit": round(take_profit, 5),
            "exit_price": round(exit_price, 5),
            "exit_reason": exit_reason,
            "outcome": "WIN" if net_pnl > 0 else "LOSS",
            "pips": round((exit_price - entry_price) / PIP, 1),
            "r_multiple": round((exit_price - entry_price) / sl_dist, 2),
            "net_pnl": round(net_pnl, 2),
            "balance": round(balance, 2),
        })
        # One position at a time: the next signal can come from the exit day
        i = exit_idx

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
def period_bars(df, start, end):
    return df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]


def buy_and_hold(df, start, end):
    """EUR/USD buy-and-hold cumulative return (%) over the tested period."""
    p = period_bars(df, start, end).set_index("date")
    return (p["close"] / p["open"].iloc[0] - 1) * 100


def summarize(trades_df, df, start, end, initial_capital, final_balance):
    p = period_bars(df, start, end)
    total_return = (final_balance - initial_capital) / initial_capital * 100
    print("\n=== SUMMARY ===")
    print(f"Tested period   : {p['date'].iloc[0]:%Y-%m-%d} -> {p['date'].iloc[-1]:%Y-%m-%d} "
          f"({len(p)} real {SYMBOL} daily bars, TradeStation)")
    print(f"Initial Capital : ${initial_capital:,.2f}")
    print(f"Final Balance   : ${final_balance:,.2f}")
    print(f"Total Return    : {total_return:,.2f}%")
    print(f"Buy & Hold      : {buy_and_hold(df, start, end).iloc[-1]:,.2f}% (EUR/USD spot, same period)")
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
    print(f"Avg R per trade : {trades_df['r_multiple'].mean():.2f}")
    print(f"Profit Factor   : {profit_factor:.2f}")
    print(f"Max Drawdown    : {max_dd:.2f}% (closed-trade equity)")
    print("Exit reasons    : " + ", ".join(f"{k}={v}" for k, v in
                                           trades_df["exit_reason"].value_counts().items()))


def plot_returns(trades_df, df, start, end, initial_capital, path="eur_usd_returns_chart.png"):
    p = period_bars(df, start, end)
    first, last = p["date"].iloc[0], p["date"].iloc[-1]
    # Start every curve at the beginning of the tested period
    times = pd.concat([pd.Series([first]), pd.to_datetime(trades_df["exit_date"])],
                      ignore_index=True)
    balance = pd.concat([pd.Series([initial_capital]), trades_df["balance"]], ignore_index=True)
    cum = pd.concat([pd.Series([0.0]), trades_df["cumulative_return_pct"]], ignore_index=True)

    fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True,
                             gridspec_kw={"height_ratios": [2, 2, 1]})

    axes[0].plot(times, balance, marker="o", markersize=3, color="dodgerblue", linewidth=1.8)
    axes[0].axhline(initial_capital, color="grey", linestyle="--", alpha=0.6)
    axes[0].set_title("Equity Curve (USD)", fontweight="bold")
    axes[0].set_ylabel("Balance ($)")

    bh = buy_and_hold(df, start, end)
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
    axes[2].bar(pd.to_datetime(trades_df["exit_date"]), trades_df["return_pct"],
                color=colors, width=2.0)
    axes[2].axhline(0, color="black", linewidth=0.8)
    axes[2].set_title("Per-Trade Return (%)", fontweight="bold")
    axes[2].set_ylabel("Return (%)")
    axes[2].set_xlabel("Exit date")

    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.5)
    fig.suptitle(f"{SYMBOL} daily pullback backtest, {first:%Y-%m-%d} to {last:%Y-%m-%d} "
                 f"(TradeStation daily data)", fontsize=14)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"Returns chart saved to {path}")


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=DATA_FILE, help="daily OHLC CSV")
    ap.add_argument("--start", default=DEFAULT_START, help="first entry date (YYYY-MM-DD)")
    ap.add_argument("--end", default=DEFAULT_END, help="last date, inclusive (YYYY-MM-DD)")
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--risk-pct", type=float, default=0.01, help="fraction of balance risked per trade")
    ap.add_argument("--rr", type=float, default=3.0, help="reward:risk ratio")
    ap.add_argument("--atr-mult", type=float, default=1.0, help="stop distance in ATR(14)s")
    ap.add_argument("--rsi-entry", type=float, default=40, help="enter when RSI(3) closes below this")
    ap.add_argument("--max-hold", type=int, default=5, help="max trading days in a trade")
    ap.add_argument("--spread-pips", type=float, default=1.5)
    ap.add_argument("--fee", type=float, default=2.0, help="fixed cost per trade in USD")
    return ap.parse_args()


def main():
    args = parse_args()
    df = load_data(args.data)

    trades_df, final_balance = run_backtest(
        df, start=args.start, end=args.end,
        initial_capital=args.capital,
        risk_pct=args.risk_pct,
        rr_ratio=args.rr,
        atr_mult=args.atr_mult,
        rsi_entry=args.rsi_entry,
        max_hold=args.max_hold,
        fee_drag=args.fee,
        spread_pips=args.spread_pips,
    )

    print(f"\n=== TRADES LOG ({len(trades_df)} trades) ===")
    if not trades_df.empty:
        with pd.option_context("display.max_rows", None, "display.width", 250,
                               "display.max_columns", None):
            print(trades_df.to_string(index=False))
        trades_df.to_csv("eur_usd_trades_log.csv", index=False)
        print("Trades log saved to eur_usd_trades_log.csv")

    summarize(trades_df, df, args.start, args.end, args.capital, final_balance)

    if not trades_df.empty:
        plot_returns(trades_df, df, args.start, args.end, args.capital)

    return trades_df, final_balance


if __name__ == "__main__":
    main()
