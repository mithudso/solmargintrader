---
id: tv_bfxf4ixh_built_in_kelly_ratio_for_dynamic_position_sizing
name: "Built-in Kelly ratio for dynamic position sizing"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Demonstrate adapting position size from the strategy's own completed-trade performance using a Kelly ratio, with a Keltner-channel strategy as the host."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [resolved-strategy-trades-and-payoffs]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Built-in Kelly ratio for dynamic position sizing

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** sizing-overlay. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Demonstrate adapting position size from the strategy's own completed-trade performance using a Kelly ratio, with a Keltner-channel strategy as the host.

## How it works

- The publication says it starts with the default Keltner-channel strategy, then adds Kelly-based sizing and ordinary target/stop inputs.
- The sizing overlay tries to allocate more or less capital as the estimated trade distribution changes. It does not supply an independent entry edge.
- A causal reconstruction must estimate sizing inputs from completed past trades only. This is an implementation requirement; the description does not disclose the estimator.

## Documented rules and trade lifecycle

- Use the described Keltner-channel host for entries; its exact version and entry/exit definitions are not included.
- Update position sizing on a per-trade basis using the Kelly ratio described by the author.
- Optional take-profit and stop-loss parameters are mentioned without settings.

## Parameters and stated settings

- No lookback length, seed size, fractional-Kelly multiplier, cap, negative-ratio handling or target/stop defaults are disclosed.

## Failure modes and caveats

- A Kelly estimate from few, nonstationary trades can be unstable; an apparent edge can produce excessive sizing.
- A future-looking or full-sample estimator would leak outcomes into earlier position sizes.

## Missing information and implementation boundary

- Recover the exact Kelly formula/estimator, minimum history, reset policy, size bounds and Keltner host rules.
- The word built-in in the title does not establish an available library API or a runnable repository implementation.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> This is the defaut keltners channel strategy with a few additions.
> The main purpose is to show how we include the Kelly ratio into our scripts for dynamic position sizing based on the performance of the strategy on a per trade basis.
> 
> We've also included the usual take-profit and stop-loss parameters in the event you want to play a little :)

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This is the defaut keltners channel strategy with a few additions.

> The main purpose is to show how we include the Kelly ratio into our scripts for dynamic position sizing based on the performance of the strategy on a per trade basis.

> We've also included the usual take-profit and stop-loss parameters in the event you want to play a little :)

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
