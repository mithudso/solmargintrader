---
id: grid
name: Long-Only Grid (exposure staircase)
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Staircase accumulation as price falls below a rolling anchor. NOT the extension's resting-order ladder.
registry_key: grid
runner: backtester.cli
warmup_bars: 50
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params:
  anchor_window: {default: 50, type: int, desc: "SMA window for the anchor price"}
  levels: {default: 4, type: int, desc: "number of staircase rungs"}
  step: {default: 0.05, type: float, desc: "fractional drawdown per rung"}
presets:
  short: {anchor_window: 48, levels: 4, step: 0.03}
  medium: {anchor_window: 50, levels: 4, step: 0.05}
  long: {anchor_window: 120, levels: 4, step: 0.1}
---
# Long-Only Grid (exposure staircase)

## Do not confuse this with the ladder grid
This is an **exposure staircase**: exposure rises one rung per `step` of drawdown below
a rolling SMA anchor. It is a `Strategy` filled at a bar boundary, and it **never
captures a rung width**, because it never has an order resting at a level.

The strategy the Chrome extension actually trades is a **ladder of resting limit
orders with paired exits** — see `ladder_grid.md`. The two share a name and almost
nothing else. Conflating them puts a wrong number under the live strategy.

## What it looks for
Range-bound oscillation to harvest.

## Equation
```
anchor_t   = SMA(n)_t
drawdown_t = 1 - c_t/anchor_t
rungs_t    = min(floor(drawdown_t / step) + 1, levels)   if drawdown_t > 0 else 0
target_t   = rungs_t / levels
```

## Implementation
`backtester/core/strategies/signals.py::GridLong`.

## Works when
Genuine ranges. Heavily used in crypto because it feels good in a chop.

## Fails when
**A sustained downtrend. It is short volatility and long the range assumption, so it
reaches maximum exposure exactly when it is most wrong.** This is the most instructive
failure mode in the set: the strategy's own mechanism converts a trend into a
maximum-size losing position.

## Backtest notes
Grid results are dominated by whether the test window contained a range or a trend, so
a single-window backtest of a grid is close to meaningless. It also generates enormous
trade counts — 694 short, 143 long — making it unusually cost-sensitive.

## Pairs with
A regime filter, which vetoes precisely the condition that ruins it. **This pairing was
never swept** and is the highest-value untested pair in `RANKED_LISTS.md` List 2.

## Measured on SOL
Medium: **OOS -38.9%** (Sharpe -0.590) on 100 OOS trades.
Short: **OOS Sharpe -1.510** across 694 trades. Long: OOS -26.5%, 143 trades.

The figures below come from a **single 70/30 walk-forward split**, and
`research/RANKED_LISTS.md` documents why that split is structurally hostile: its
in-sample window ends within one bar of the highest close in the entire series
($261.99 on bar 1311 of 1875). It separated a bull market from a bear leg almost
exactly, so any long-biased rule *had* to look excellent in-sample and terrible
out-of-sample. In-sample rank did not predict out-of-sample rank — the medium-horizon
Spearman correlation was **-0.419**, actively inverted.

Read these numbers as evidence about **one regime transition**, not as a performance
estimate. Across the whole sweep, 45 of 311 rankable configurations (14%) had a
positive out-of-sample Sharpe and 28 (9%) made money. The evidence floor is 10
out-of-sample trades: fewer than that and a row is listed, never ranked.

## Caveats and limitations
- 694 trades at 8 bps round trip is roughly 5.5% of notional in costs alone before any
  signal contribution.
- The single most valuable experiment for this card — gating it with `sma_regime` — has
  not been run.

## How to run
```bash
python3 -m backtester.cli --strategy grid --interval 1d
```
