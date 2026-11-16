---
id: pivot_reversal_v33_source_research
name: "TradingView Pivot Reversal Strategy v33 research"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Confirmed high/low pivot stop-order adapter with unresolved tie semantics."
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
# TradingView Pivot Reversal Strategy v33

Version: 1.0.0. Delta: separate source-bound research card; frozen original
readiness record remains unchanged.

The official Pine snapshot `src:f1cf879aa1a71c9a`, SHA-256
`cd6def72548fb84e02312f302dd2799f897638d0a2c688aef04ca861b5a5628f`,
defaults to four left and two right pivot bars. Once confirmed, it arms entry
stops one symbol tick above a high pivot or below a low pivot. The source
contains no cancellation in the branches that disarm these conditions; an
adapter must not invent cancellation. This built-in is distinct from the
existing help-page prose describing discretionary pivot-point bounces.

`research/tradingview_pivot_reversal.py` emits source-level intents only after
the two right bars exist. Exact equal-high/low tie behavior of the Pine pivot
functions is still unverified. The adapter therefore exposes strict, earliest
and latest tie sensitivities; none is asserted to be TradingView parity. A
0.01 tick in the common oracle proxy is a declared TradingView scanner-derived
scenario, not an observed Jupiter tick. The 1,000-USD signal-close sizing is a
counterfactual scenario, and unverified source-default sizing is withheld.
Funding, exchange margin, liquidation and full spread are not modelled. The
required low likelihood field is an a-priori catalog label, not a measured
probability.
