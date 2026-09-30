# Agent state (read first on every run; update last)

- **stage:** RESEARCH (round 4)
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 2 (sent 2026-09-30, round 3 results)
- **next_action:**
  1. Research round 4. The lesson from round 3 is that retail costs (2-6 pips per trade) swamp intraday FX
     edges, so focus on **multi-day holds where the expected gross move is many times the cost**. Candidates:
     - weekly or multi-week trend on the most trending **crosses** and non-major pairs, if HistData has them;
     - volatility-breakout entries with trailing stops held for days;
     - swing mean reversion on pairs that range (for example EURCHF, AUDNZD), with multi-day holds.

     Each hypothesis must state its expected gross pips per trade relative to its cost before testing.
  2. Pre-register (`edge/lab/r4/PREREGISTRATION.md`), commit and push.
  3. Download any extra pairs with `tools/histdata.py`.
- **notes:**
  - Data: HistData 5-minute bars for the 7 majors, 2012..2026-09-25, are downloaded (`data/histdata/`,
    git-ignored; manifest committed).
  - The round-3 full run took about 65 minutes. The H4 path-dependent Monte Carlo is the slow part.
