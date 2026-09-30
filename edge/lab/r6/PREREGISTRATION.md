# Strategy lab round 6: pre-registration

Written and pushed **before** any round-6 test is run, and never changed afterwards. Currencies only (the owner
has not yet answered the gold question).

## Hypotheses

| id | idea | data | rule | parameters | expected gross per trade vs cost |
|----|------|------|------|------------|----------------------------------|
| L1 | **Asian-range breakout** at the London session | HistData 5-min, EURUSD, GBPUSD, USDJPY, 2012-2026 | Asian range = high and low of bid closes from 00:00 to 07:00 London. Between 07:00 and 11:00 London, the first 5-min close above range high + f x range goes long (below range low - f x range goes short), filled at the next bar's open. At most one trade a day. Stop at the opposite side of the range. Exit at the stop (checked on 5-min closes, filled at the next open) or at 16:00 London. Skip the day if range < 10 pips or > 80 pips. | f 0.0..0.3, entry window end 09:00..11:00 | Typical Asian range 25-45 pips; a follow-through of ~0.5-1 range = 15-40 pips vs 2-2.4 pips cost (about 10x). |
| L4 | **Weekly reversal after extreme weeks** | TradeStation daily, 7 majors + 21 crosses, 2006-2026 | At each Friday close, z_w = that week's return / stdev of the last 52 weekly returns. If abs(z_w) > k, take the **opposite** position, filled at the next open, and hold for W weeks. Stop at 3 x weekly stdev from entry, on daily closes. | k 1.5..3.0, W 1..3 | Reversal of ~0.3-0.6 of a 2-3% extreme week = 0.6-1.8% vs about 0.05% cost (>10x). |

**Sources.** L1 is a widely used session-breakout pattern; studies of FX intraday seasonality document the jump
in volume and volatility at the London open. It has weak academic evidence, which is stated honestly. L4 follows
evidence of short-horizon overreaction and reversal in currencies after large moves. It differs from G2 (daily,
cross-sectional rank) and F5 (daily z-score) in both horizon and trigger.

## Common rules
- **Costs:** as in rounds 3-4.
  - L1: the retail table spread + 0.9 pip per round turn.
  - L4: majors at the table spread + 0.9 pip; crosses at the sum of both legs.
- **Swap:** -2% a year on positions held overnight (L4 only; L1 is flat by 16:00).
- **Sizing:** each instrument is sized to 10% volatility (60-day stdev of daily returns), averaged with equal
  risk.
- **Periods:**
  - L1: development 2012-2016, out-of-sample 2017-2023 (yearly walk-forward), holdout 2024 .. 2026-09-25.
  - L4: development 2008-2016, out-of-sample 2017-2023, holdout 2024 .. 2026-09-25.
- **Walk-forward grids:**
  - L1: f {0, 0.1, 0.2, 0.3} x window end {09:00, 10:00, 11:00}.
  - L4: k {1.5, 2.0, 2.5, 3.0} x W {1, 2, 3}.
- **Pass criteria:** as in edge/lab/AGENT.md (criteria 1-6).
  - Parameter Monte Carlo: 10,000 sets, seed 20261003.
  - Deflated Sharpe: n_trials = 21 (19 earlier FX rows + L1 + L4).

Random numbers are used only to pick parameter sets and to resample real returns.
