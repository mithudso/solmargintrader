---
id: sar_v33_source_research
name: "TradingView Parabolic SAR Strategy v33 research"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Source-bound SAR stop-order research adapter, not a validated TradingView replica."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# TradingView Parabolic SAR Strategy v33

Version: 1.0.0. Delta: separate source-bound research card; frozen original
readiness record remains unchanged.

The official Pine snapshot `src:260da27279d3c3e8`, SHA-256
`800f3fe7f02df408f9f144951e6e44744240a67dec2825d0953d5309b0a4bef1`,
defaults acceleration start 0.02, increment 0.02 and maximum 0.2. It maintains
trend, extreme point, SAR and acceleration state; on confirmed bars it places
an opposing-direction stop at next-bar SAR and cancels the other entry ID.

`research/tradingview_sar.py` emits this source-level intent sequence for
contiguous closed bars. Its initializer, acceleration and reversal have
focused tests. This is a research adapter, not a registered live strategy or
proof of complete Pine/TradingView fill parity. The shared comparator uses a
previously observed Jupiter oracle proxy, not the requested Coinbase market.
Its fixed 1,000-USD signal-close notional is a counterfactual research scenario,
not proof of the source tester's order size. It does not model funding,
exchange margin, liquidation or full spread. The required low likelihood field
is an a-priori catalog label, not a measured probability.
