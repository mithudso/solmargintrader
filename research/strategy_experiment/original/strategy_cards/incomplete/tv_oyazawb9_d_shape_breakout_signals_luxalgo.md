---
id: tv_oyazawb9_d_shape_breakout_signals_luxalgo
name: "D-Shape Breakout Signals [LuxAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of D-Shape Breakout Signals [LuxAlgo]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# D-Shape Breakout Signals [LuxAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The D-Shape Breakout Signals indicator uses a unique and novel technique to provide support/resistance curves, a trailing stop loss line, and visual breakout signals from semi-circular shapes.

> D-shape is a new concept where the distance between two Swing points is used to create a semi-circle/arc, where the width is expressed as a user-defined percentage of the radius. The resulting arc can be used as a potential support/resistance as well as a source of breakouts.

> Users can adjust this percentage (width of the D-shape) in the settings ("D-Width"), which will influence breakouts and the Stop-Loss line.

> The script includes a Trailing Stop-Loss line (TSL), which is only updated when a breakout of the D-Shape occurs. The TSL will return the midline of the D-Shape subject to a breakout.

> The TSL can be used as a stop-loss or entry-level but can also act as a potential support/resistance level or trend visualization.

> In an uptrend, with an already available green TSL, the potential new Stop-Loss value must be higher than the previous TSL value; while in a downtrend, the new TSL value must be lower.

> The Stop-Loss line won't be updated when a "Neutral Breakout" occurs.

> Swing Length: Period used for the swing detection, with higher values returning longer-term Swing Levels.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`, `tv_method_trailing_stop`.

## Data and availability

Required inputs: ohlcv.
The repository supports OHLCV history. Verify symbol, cadence, timezone and complete bars for the chosen experiment; this is not a claim that every source market is cached.

## Implementation and validation

No runner or registry key is assigned. Before implementation, freeze the numerical
formula, seeds, missing-value policy, warm-up and parameter domains. Where the source
does not disclose an algorithm or default, recover it rather than guessing. Specify
entry, exit, stop, holding horizon, exposure and costs separately from the indicator.
Record which choices come from the publication and which define a new experiment.

Compute with closed bars and trailing data only. Confirm pivots and higher-timeframe
values before use; never backdate a signal to a pivot that needed later bars. Test
prefix invariance, flat/zero inputs, unavailable data and one-bar-delayed execution.
Evaluate chronologically out of sample, deduct transaction and financing costs and compare with
buy-and-hold and simpler component rules. Record all searched configurations.

## Failure modes and caveats

An author description is not source code or independent validation. Visual styling,
retrospective drawing anchors, repainting pivots and fitted full-history models can
produce unavailable historical signals. A rule can be numerically correct and lose
after costs. Venue, session, data and asset differences limit transfer to SOL.

## Measured results

Not measured in this repository. Publication examples, advertised accuracy and
screenshots are not repository backtest results.

## Likelihood of success: low

Basis: a-priori. The mechanism has no confirming out-of-sample result here. This rating
does not promote the source author's claims into evidence of profitability.

## Sources

- https://www.tradingview.com/script/oYAzaWB9-D-Shape-Breakout-Signals-LuxAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
