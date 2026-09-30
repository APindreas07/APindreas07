# Agent state (read first on every run; update last)

- **stage:** DATA (round 4); pre-registration committed
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 2 (sent 2026-09-30, round 3 results)
- **next_action:**
  1. Download HistData for the 9 Scandinavian/CEE pairs, 2012..2026-09-25: `python -m tools.histdata --pairs USDNOK USDSEK USDPLN USDHUF USDCZK EURNOK EURSEK EURPLN EURHUF --start 2012 --end 2026-09-25` (about 2 minutes).
  2. Build daily 17:00-New-York bars and the 21 crosses.
  3. Write `edge/lab/r4/research.py` (J1-J3 per the pre-registration; reuse the r3 stats, Monte Carlo and DSR code).
  4. Check the engine against an explicit loop, run the tests, report, and email report #3.
- **notes:**
  - Data: HistData 5-minute bars for the 7 majors, 2012..2026-09-25, are downloaded (`data/histdata/`,
    git-ignored; manifest committed).
  - The round-3 full run took about 65 minutes. The H4 path-dependent Monte Carlo is the slow part.
