# Agent state (read first on every run; update last)

- **stage:** RESEARCH (round 5)
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 4 (sent 2026-09-30, round 4 results)
- **next_action:** research round 5, at most 3 hypotheses. Ideas not yet tested:
  - calendar flows beyond month-end: quarter-end and year-end rebalancing, pre-holiday behaviour;
  - trend or mean reversion **conditioned on a risk regime** read from price data only (for example SPY
    volatility or drawdown as the filter);
  - a combined, equal-risk portfolio of the two round-2 near-misses (G1 cross mean reversion, G3 month-end flow)
    as a **new trial**; its deflated Sharpe will be very demanding;
  - **only if the owner agrees:** gold (XAUUSD), which trades on FX platforms and drove E5's gains. Asked in
    report #4; wait for the owner's answer before using it.

  Each hypothesis must state its expected gross edge per trade against cost before testing.
- **notes:**
  - Data available: HistData 5-minute bars for the 7 majors and the 9 Scandinavian/CEE pairs, 2012..2026-09-25.
    Round 4 caches daily bars in `data/histdata/_cache/daily_r4.pkl`. Shared statistics are in
    `edge/lab/common.py`.
  - Rounds 3 and 4 showed the **gross** signals are about zero, so costs are not the main issue.
