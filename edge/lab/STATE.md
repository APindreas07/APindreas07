# Agent state (read first on every run; update last)

- **stage:** RESEARCH round 12 (slow pace); M1/M1b shadow test running
- **halted:** false (kill switch not triggered)
- **deployed:** M1 gotobi as a SHADOW forward test (no orders; SIM accounts cannot trade spot FX). See edge/lab/deploy/M1_FORWARD.md. First trade: Tokyo 2026-10-05 (Sun Oct 4, 18:00-20:55 UTC-4); log it on Oct 5 with get-bars.
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 12 (sent 2026-10-01: round 11 momentum)
- **owner decisions (read from Gmail on 2026-09-30):**
  - 20:45 UTC: "craft, develop, test and validate new strategies ... go over again all the currencies + gold & silver ... use every technology possibly ... let me know how it goes" -> round 9 = machine learning.
  - 09:47 UTC: "Include Gold and Silver".
  - 11:05 UTC: "Go all in and start Option 2: widen to gold and silver ... keep it within usage limits, any pace".
  - 16:58 UTC: "A: yes, B: 1 and 2", which means:
    - **paper-trade M1 gotobi on SIM: YES**;
    - **continue the FX search AND add gold/silver**.
- **next_action:**
  1. On 2026-10-05 (after 21:00 UTC-4 on Oct 4): log the M1/M1b shadow trade (get-bars USDJPY 5-min, lastdate 2026-10-05) in `edge/lab/deploy/M1_FORWARD.md`.
  2. Round 12, slow pace (not before 2026-10-01 14:00 local). Idea space for technical FX/metals is close to exhausted; consider proposing FINAL.md to the owner.
- **notes:**
  - Owner replies come from the same address (SENT label). Read the thread with `get_thread`; never use
    -in:sent.
  - The owner's PC is on UTC-4 ("Cuba Standard Time" = New York offset).
  - The TradeStation trading environment was checked on 2026-09-30 and is **sim**.
  - Data: HistData 5-minute bars for the 7 majors and the 9 Scandinavian/CEE pairs, 2012..2026-09-25. Shared
    statistics are in `edge/lab/common.py`.
