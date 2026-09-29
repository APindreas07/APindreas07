# Agent state (read first on every run; update last)

- **stage:** DATA (round 3)
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **email_thread_id:** 1a0eec446c2c9ba9
- **last_report_number:** 1 (sent 2026-09-29)
- **next_action:**
  1. When the HistData download has finished (log: `%TEMP%\claude\histdata.log`, last line "DONE"), check
     coverage and commit `data/histdata_MANIFEST.csv`.
  2. Run `python -m edge.lab.r3.research` in the background.
  3. Check the engine against an explicit loop on one pair.
  4. Write `edge/lab/r3/REPORT.md`, add the ledger rows, and email report #2.
- **notes:**
  - Dukascopy was abandoned for bulk data (throttled to about 2 files per 10 minutes). The owner chose HistData
    (option 1, 2026-09-29).
  - HistData timestamps are New York time **with** DST (verified against Dukascopy). `tools/histdata.py`
    handles it.
