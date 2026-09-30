# M1 gotobi: forward (shadow) paper test

**Owner approval:** paper-trade M1 on SIM ("A: yes", 2026-09-30).

**Constraint found (2026-09-30).** The TradeStation SIM accounts cannot trade spot FX.
- `confirm-order` for USDJPY on SIM3101536M returned "Invalid account for the asset type".
- The only available proxy is CME micro yen futures (MJYZ26, in SIM futures account SIM3101537F). Its spread
  (~0.0002 on 0.639, about 5 USDJPY pips) is larger than M1's whole gross edge (about 3.6 pips), so a futures
  SIM test would measure the instrument's cost rather than the strategy.

**Therefore, until the owner decides otherwise:** a **shadow forward test**, with no orders.
- **Signal:** for every gotobi Tokyo date from 2026-10-05 onward, the frozen M1 rule, unchanged:
  - buy at the open of the 07:00 Tokyo bar (18:00 UTC-4, the evening before);
  - sell at the open of the 09:55 Tokyo bar.
- **Prices:** real **TradeStation** USDJPY 5-minute bars, fetched afterwards with `get-bars` (100 bars around
  the window).
- **Costs:** the same as the backtest: 1.2 pips spread + 0.9 pip commission and slippage.
- **Sizing:** the same 10% volatility sizing; also reported at the owner's 5x leverage cap.
- **Logging:** each trade is appended to the table below. After at least 18 trades (about 3 months), the
  forward result is compared with the backtest's expectation of +1.5 pips net per trade.

**Frozen rule parameters:** E = 07:00 Tokyo; exit at the 09:55 Tokyo open; long only; gotobi calendar as in
`edge/lab/r7/research.py` (`gotobi_flags`). Japanese holidays are not excluded.

| gotobi Tokyo date | entry (Tokyo 07:00) bid open | exit (09:55) bid open | gross pips | net pips (after 2.1) |
|-------------------|------------------------------|-----------------------|------------|----------------------|
