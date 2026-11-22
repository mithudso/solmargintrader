---
id: dca
name: Dollar-Cost Averaging (instalment ramp)
kind: exposure-strategy
status: implemented
family: baseline
summary: Deploy a fixed budget in equal instalments at a fixed bar interval; exposure ramps to 1.0. The guides' DCA, expressed as an exposure target.
registry_key: dca
runner: backtester.cli
warmup_bars: 0
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  instalments: {default: 10, type: int, desc: "number of equal instalments that fill the budget"}
  interval: {default: 7, type: int, desc: "bars between instalments"}
presets:
  short: {instalments: 10, interval: 24}
  medium: {instalments: 10, interval: 7}
  long: {instalments: 12, interval: 30}
---
# Dollar-Cost Averaging (instalment ramp)

## What it is
Invest `budget / instalments` every `interval` bars regardless of price. Source formula: amount per purchase = total budget / number of scheduled purchases.

## What it looks for
Nothing. It is a deployment schedule: no signal, no timing. The question it answers is whether averaging in beats being fully invested from the first bar.

## Equation
```
done_t   = floor((bars_seen_t - 1) / interval) + 1
target_t = min(1, done_t / instalments)
```
The engine takes exposure targets, not cash orders, so an instalment is a fixed fraction of equity. True DCA buys equal cash; the invested share here drifts with price between instalments. The difference is second order next to the ramp itself.

## Implementation
`backtester/core/strategies/textbook.py::DollarCostAveraging`. Uses `len(history.closes)` only, so it cannot read a future bar.

## Parameters
- **instalments / interval** set how fast exposure ramps. 10x7 on daily bars is fully invested after 63 days; 10x24 on hourly bars after about 9 days.

## Works when
The asset rises after the first bar but with deep early drawdowns: averaging in buys the dips of the ramp window.

## Fails when
The asset rises steadily from the start (the ramp holds cash while it climbs, so it lags buy-and-hold), or falls for the whole ramp (the average cost is still above the exit).

## Backtest notes
After the ramp completes this is exactly `buy_and_hold`. All difference is confined to the first `instalments * interval` bars, so on a long series it is mostly the baseline with a delayed start. A sweep ranks it against that baseline, not against zero.

## Pairs with
Nothing: with no signal there is nothing to diversify.

## Measured on SOL
Smoke run only, not a sweep row: `python3 -m backtester.cli --split 0.7 --interval 1d`, SOL daily 2021-06-17..2026-08-04, default parameters, 8 bps round-trip costs, one 70/30 split. The split is structurally hostile to long-biased rules (see `research/RANKED_LISTS.md`), so read it as one regime transition, not an estimate. The queue (`soltui/bgqueue.py`) will produce the evaluated numbers; this card stays `implemented` until a sweep supplies them.

Full sample: +108.96% (Sharpe 0.590, 33 trades) vs buy-and-hold +87.61% (Sharpe 0.617). 70/30 split: IS +588.5% (Sharpe 1.049) -> OOS -53.95% (Sharpe -0.456); buy-and-hold OOS -70.76% (Sharpe -0.651). The full-sample gain is the start date, not skill: both lines lose most of their value in the OOS window.

## Likelihood of success: very-low

*Basis: base-rate. A deployment schedule has no edge of its own. It changes the entry date distribution, not expected return, and after the ramp it is the baseline.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
python3 -m backtester.cli --strategy dca --interval 1d --split 0.7
```
