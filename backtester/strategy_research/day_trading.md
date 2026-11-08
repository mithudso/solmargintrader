---
id: day_trading
name: Day Trading (flat at session close)
kind: exposure-strategy
status: spec-only
family: intraday
summary: A holding-period rule, not a signal: open and close within one UTC day. Spec-only until a session-flat wrapper exists.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: a-priori
params:
  session_hours: {default: 24, type: int, desc: "bars after which a position is forced flat (24 on hourly bars is one UTC day)"}
presets: {}
---
# Day Trading (flat at session close)

## What it is
The guides define day trading as opening and closing positions inside one trading day on chart-based entries. Source P&L formula: position size x (exit - entry) - fees - funding/slippage.

## What it looks for
Nothing of its own. It constrains WHEN a position may be held; the entry rule comes from any other card.

## Equation
```
target_t = base_signal_t if hour_of_day_t not in the close window else 0
P&L      = size * (exit - entry) - fees - funding - slippage
```

## Implementation
None. A session-flat wrapper would sit beside `core/strategies/tiers.py` (a wrapper, not a signal) and need `BarWindow` timestamps. Hourly SOL bars already exist (`--interval 1h`). It is not built because its only effect is to multiply turnover, and every measured fast configuration in the sweep lost to costs.

## Works when
Liquid markets, tight execution and a rule set that was tested net of costs.

## Fails when
Fees and slippage exceed the edge. At 8 bps round trip, a position taken and closed daily pays about 29% of capital a year in costs before any signal.

## Pairs with
Any entry card at the `short` horizon preset.

## Measured on SOL
Not measured. No code exists for this card.

## Likelihood of success: very-low

*Basis: a-priori. Pure turnover constraint; the measured short-horizon rows (e.g. `macd` at -4.621 OOS Sharpe) are the best evidence about it.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
No runner. Use any entry card with `--interval 1h` to approximate it.
```
