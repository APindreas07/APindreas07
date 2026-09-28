"""EUR/USD buy-only swing strategy research kit (FTMO-style prop account).

Modules:
    indicators  - EMA / RSI / ATR (plain pandas)
    data        - load TradeStation daily CSV and optional 1H CSV
    strategy    - parameters and signal generation (1D trend + pullback, 1H confirmation)
    engine      - trade simulation, prop-firm account and daily mark-to-market equity
    metrics     - equity-curve scorecard and FTMO rule checks
    research    - baseline, inefficiency analysis, walk-forward optimisation, parameter drift
"""
