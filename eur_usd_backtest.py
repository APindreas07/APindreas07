# -*- coding: utf-8 -*-
"""Single EUR/USD backtest on the FTMO-style account: trades log, equity chart, scorecard.

Uses real TradeStation daily bars (data/eurusd_daily_tradestation.csv) and the
fxbot engine; nothing is random. For the full study (inefficiencies, walk-forward
optimisation, parameter drift, FTMO challenge simulation) run:

    python -m fxbot.research

Examples:
    python eur_usd_backtest.py                                # legacy rules, 2018-2025
    python eur_usd_backtest.py --throttle-below 9500          # half risk below $9,500
    python eur_usd_backtest.py --trend ema100 --entry confirm --rsi-thr 35 --atr-mult 1.5 --max-hold 10
    python eur_usd_backtest.py --h1 EURUSD_H1.csv --h1-tz Europe/Athens --entry h1
"""

import argparse
from dataclasses import replace
from pathlib import Path

import pandas as pd

from fxbot import plots
from fxbot.data import load_daily, load_hourly
from fxbot.engine import Account, Backtester, Costs
from fxbot.metrics import cards_table, scorecard
from fxbot.strategy import ENTRY_CHOICES, LEGACY, TREND_CHOICES, Params, add_features


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--trend", choices=TREND_CHOICES, default=LEGACY.trend)
    ap.add_argument("--rsi-thr", type=float, default=LEGACY.rsi_thr, help="RSI(3) must close below this")
    ap.add_argument("--atr-mult", type=float, default=LEGACY.atr_mult, help="stop distance in ATR(14)s")
    ap.add_argument("--entry", choices=ENTRY_CHOICES, default=LEGACY.entry)
    ap.add_argument("--max-hold", type=int, default=LEGACY.max_hold, help="max trading days in a trade")
    ap.add_argument("--risk", type=float, default=Account.risk_usd, help="USD risked per trade")
    ap.add_argument("--throttle-below", type=float, default=0.0,
                    help="halve risk while the balance is below this (0 = off)")
    ap.add_argument("--spread-pips", type=float, default=Costs.spread_pips)
    ap.add_argument("--commission", type=float, default=Costs.commission_per_lot)
    ap.add_argument("--swap", type=float, default=Costs.swap_per_lot_night)
    ap.add_argument("--h1", type=Path, help="1H bars CSV for --entry h1")
    ap.add_argument("--h1-tz", default="UTC")
    ap.add_argument("--out", type=Path, default=Path("."), help="folder for the CSV and chart")
    return ap.parse_args()


def main():
    args = parse_args()
    params = Params(trend=args.trend, rsi_thr=args.rsi_thr, atr_mult=args.atr_mult,
                    entry=args.entry, max_hold=args.max_hold)
    account = replace(Account(), risk_usd=args.risk, throttle_below=args.throttle_below)
    costs = Costs(args.spread_pips, args.commission, args.swap)
    h1 = load_hourly(args.h1, args.h1_tz) if args.h1 else None
    if params.entry == "h1" and h1 is None:
        raise SystemExit("--entry h1 needs --h1 <file>")

    bt = Backtester(add_features(load_daily()), account, costs, h1)
    trades, eq = bt.run(params, args.start, args.end)
    card = scorecard(trades, eq, account)

    print(f"Setup: {params.label()}")
    print(f"\n=== TRADES LOG ({len(trades)} trades) ===")
    if not trades.empty:
        with pd.option_context("display.max_rows", None, "display.width", 250, "display.max_columns", None):
            print(trades.drop(columns=["setup"]).to_string(index=False))
    print("\n=== EQUITY SCORECARD ===")
    print(cards_table({"This run": card}))

    args.out.mkdir(parents=True, exist_ok=True)
    trades.to_csv(args.out / "eur_usd_trades_log.csv", index=False)
    plots.equity_chart({"Strategy": eq}, account, args.out / "eur_usd_returns_chart.png",
                       f"EURUSD {params.label()}, {args.start[:4]}-{args.end[:4]}")
    print(f"\nSaved {args.out / 'eur_usd_trades_log.csv'} and {args.out / 'eur_usd_returns_chart.png'}")


if __name__ == "__main__":
    main()
