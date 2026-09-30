# Agent state (read first on every run; update last)

- **stage:** RESEARCH round 8 (gold/silver) + FX; M1 shadow forward test running
- **halted:** false (kill switch not triggered)
- **deployed:** M1 gotobi as a SHADOW forward test (no orders; SIM accounts cannot trade spot FX). See edge/lab/deploy/M1_FORWARD.md. First trade: Tokyo 2026-10-05 (Sun Oct 4, 18:00-20:55 UTC-4); log it on Oct 5 with get-bars.
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 8 (sent 2026-09-30: replies received, M1 shadow test, questions C/D)
- **owner decisions (read from Gmail on 2026-09-30):**
  - 09:47 UTC: "Include Gold and Silver".
  - 11:05 UTC: "Go all in and start Option 2: widen to gold and silver ... keep it within usage limits, any pace".
  - 16:58 UTC: "A: yes, B: 1 and 2", which means:
    - **paper-trade M1 gotobi on SIM: YES**;
    - **continue the FX search AND add gold/silver**.
- **next_action:**
  1. **M1 SIM deployment.** Rule 5 says deploy exactly what was tested, and sizing needs a stop, so:
     - pre-register and test **M1s** = M1 + a protective stop (r7b);
     - read-only checks of the SIM accounts and the USDJPY symbol format;
     - then schedule the entry and exit orders for the next gotobi days (in the owner's time zone, UTC-4:
       entry 18:00, exit 20:55, on the evening before each gotobi Tokyo date).
     - Upcoming gotobi Tokyo dates: **Mon 2026-10-05** (trade Sun Oct 4) and **Fri 2026-10-09**, standing in
       for Sat Oct 10 (trade Thu Oct 8).
  2. **Round 8: gold and silver.** Download XAUUSD and XAGUSD with `tools/histdata.py`. Candidate: E5-style
     trend, where gold drove the only real edge found so far.
- **notes:**
  - Owner replies come from the same address (SENT label). Read the thread with `get_thread`; never use
    -in:sent.
  - The owner's PC is on UTC-4 ("Cuba Standard Time" = New York offset).
  - The TradeStation trading environment was checked on 2026-09-30 and is **sim**.
  - Data: HistData 5-minute bars for the 7 majors and the 9 Scandinavian/CEE pairs, 2012..2026-09-25. Shared
    statistics are in `edge/lab/common.py`.
