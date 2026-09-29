# Agent state (read first on every run; update last)

- **stage:** DATA (round 3)
- **halted:** false (kill switch not triggered)
- **deployed:** none
- **next_action:**
  1. Download the 7 majors, 2012 .. 2026-09-25, with `tools/dukascopy.py` at the gentle pace (2 threads). It
     resumes automatically.
  2. Then run `python -m edge.lab.r3.research`.
  3. Check the engine against an explicit loop.
  4. Write `edge/lab/r3/REPORT.md` and add the ledger rows.
- **notes:**
  - Dukascopy throttled an 8-thread burst on 2026-09-29 (HTTP 503). Keep it at 2 threads with the built-in
    pacing.
  - Git on the owner's PC needs a one-time GitHub sign-in before pushes work (see LOCAL.md). Until then, commit
    locally.
