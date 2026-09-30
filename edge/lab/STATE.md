# Agent state (read first on every run; update last)

- **stage:** AWAITING OWNER DIRECTION (after round 6); summary sent
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 6 (sent 2026-09-30, round 6 results + SUMMARY.md)
- **next_round_not_before:** 2026-09-30 12:45 local (slow pace: one round every ~6 hours while awaiting the owner)
- **next_action:** check Gmail for the owner's answer to report #6 (options 1-4 in SUMMARY.md, plus the gold question). If there is no answer, continue FX-only research at a slow pace (one round every ~6 hours) to save usage.
- **notes:**
  - Data available: HistData 5-minute bars for the 7 majors and the 9 Scandinavian/CEE pairs, 2012..2026-09-25.
    Round 4 caches daily bars in `data/histdata/_cache/daily_r4.pkl`. Shared statistics are in
    `edge/lab/common.py`.
  - Rounds 3 and 4 showed the **gross** signals are about zero, so costs are not the main issue.
