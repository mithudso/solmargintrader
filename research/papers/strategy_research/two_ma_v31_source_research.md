---
id: two_ma_v31_source_research
name: "TradingView Two moving averages v31 research"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Source-bound moving-average research adapter; TradingView parity remains unverified."
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
# TradingView two moving averages v31: provisional research card

Version: 0.1.0. Status: source-bound draft; independent source and outcome review pending. This is not a registered executable strategy.

The pinned built-in uses 9- and 18-period simple moving averages and crossover events. The source adapter is `research/tv_two_ma.py`; the source pin, implementation assumptions, and unresolved crossover, missing-value and order-sizing semantics are documented in `research/tv_two_ma_rabbithole.md`. The existing generic 20/50 persistent-exposure crossover is a different strategy.

The common Jupiter oracle comparison uses signal-close equal-notional sizing as a sensitivity, not as proof of TradingView default order size, perpetual-market fills, costs, or prospective performance.

The required low likelihood field is an a-priori catalog label, not a measured probability.
