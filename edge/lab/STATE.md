# Agent state (read first on every run; update last)

- **stage:** TEST (round 5); pre-registration committed (K1 equity-regime trend, K2 post-stress rebound, K3 G1+G3 combo)
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 4 (sent 2026-09-30, round 4 results)
- **next_action:** write `edge/lab/r5/research.py` (TradeStation daily majors + SPY; 6 risk crosses; K3 reuses `edge.fx2.research` functions), check the engine against an explicit loop, run the tests in the background, then report, update the ledger and email report #5. Before round 6, check Gmail for the owner's gold answer.
- **notes:**
  - Data available: HistData 5-minute bars for the 7 majors and the 9 Scandinavian/CEE pairs, 2012..2026-09-25.
    Round 4 caches daily bars in `data/histdata/_cache/daily_r4.pkl`. Shared statistics are in
    `edge/lab/common.py`.
  - Rounds 3 and 4 showed the **gross** signals are about zero, so costs are not the main issue.
