# AXS Trading - Windows Desktop App

## To Run:

1. Install dependencies:
```
npm install
```

2. Start the app:
```
npm start
```

3. Build .exe installer:
```
npm run build
```

The installer will be in `dist/` folder.

## EURUSD strategy research (Python)

Buy-only EURUSD swing strategy tested against an FTMO-style $10k account
($100 risk per trade, 1:3 R:R, 10% max loss, 5% daily loss). Uses real
TradeStation daily bars in `data/eurusd_daily_tradestation.csv`; no random data.

```
pip install pandas numpy matplotlib
python eur_usd_backtest.py --throttle-below 9500 --out results   # one backtest: trades log, chart, scorecard
python -m fxbot.research                                         # full study -> results/REPORT.md
python -m fxbot.research --h1 EURUSD_H1.csv --h1-tz Europe/Athens  # add the 1H confirmation (MT5 export)
python tests/test_engine.py                                      # engine checks
```

See `results/REPORT.md` for the latest findings.
