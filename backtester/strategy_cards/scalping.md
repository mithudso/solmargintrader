---
id: scalping
name: Scalping
kind: exposure-strategy
status: spec-only
family: microstructure
summary: Many very small gains from tiny price moves on a tick or order-book edge. Spec-only: needs tick and book data the repo does not have.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [l2-order-book, tick-trade-prints]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  target_ticks: {default: 2, type: int, desc: "profit target in ticks"}
presets: {}
---
# Scalping

## What it is
The guides describe scalping as seeking small profits from small moves, many times a day, relying on tight spreads and fast execution.

## What it looks for
A short-lived imbalance: order-book pressure, trade-flow direction or a spread to capture.

## Equation
```
net_per_trade = ticks_captured * tick_value - spread_cost - 2 * fee - slippage
edge exists only if E[net_per_trade] > 0 after maker/taker fees
```

## Implementation
None. The mechanisms that could carry it already have their own spec-only cards: `order_book_imbalance`, `trade_flow_imbalance` and `avellaneda_stoikov_mm`. This card exists so the guide's category maps to them explicitly rather than being absent.

## Works when
A maker-rebate venue, sub-second execution and queue position. A retail wallet on a swap aggregator has none of these.

## Fails when
Round-trip cost exceeds the captured move. At 6 bps fee plus 2 bps slippage per side the cost is 16 bps, larger than most one-minute moves.

## Pairs with
Nothing in this repo: it needs data the engine cannot run.

## Measured on SOL
Not measured. No code exists for this card.

## Likelihood of success: very-low

*Basis: a-priori. Costs dominate at retail venues and the data needed to even test it is missing.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
No runner. See `order_book_imbalance` for the data gap.
```
