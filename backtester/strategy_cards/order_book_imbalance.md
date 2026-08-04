---
id: order_book_imbalance
name: Order-Book Imbalance
kind: exposure-strategy
status: spec-only
family: microstructure
summary: The highest-frequency edge available, and completely out of reach here.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [l2-order-book]
data_available: false
params:
  depth: {default: 5, type: int, desc: "levels of book depth to aggregate"}
  threshold: {default: 0.3, type: float, desc: "imbalance magnitude required to act"}
presets: {}
---
# Order-Book Imbalance

> **Spec-only — never implemented, never run.** No performance figures appear on this
> card, deliberately. `research/STRATEGIES.md` mechanism #39.

## Equation
```
imbalance_t = (bid_vol - ask_vol) / (bid_vol + ask_vol)   at depth k
```

## Why it might work
It is the most direct observation of supply and demand that exists.

## What implementing it would take
L2 snapshots at high frequency, and a fill model that accounts for queue position. This
harness has no order book and models fills at bar prices.

## Caveats
The signal decays in milliseconds to seconds. Anything a bar-resolution backtest
concludes about it is noise.

## Data gap
**No L2 depth data.**
