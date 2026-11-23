---
id: tv_juwuaxdx_deltaflow_volume_profile_bigbeluga
name: "DeltaFlow Volume Profile [BigBeluga]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of DeltaFlow Volume Profile [BigBeluga]; not a tested trading strategy."
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
# DeltaFlow Volume Profile [BigBeluga]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The DeltaFlow Volume Profile [BigBeluga] builds a compact volume profile next to price and enriches every bin with flow context: bullish vs. bearish participation (%), a per-bin Delta %, an optional Delta Heat Map, and a PoC band with the bin’s absolute volume. This lets you see not just where volume clustered, but who (buyers or sellers) dominated inside each price slice.

> Binned Volume Profile: Price range over a user-defined LookBack is split into Bins; each bin aggregates traded volume.

> Delta %: The difference between Bull % and Bear % for the bin. Positive = buyer dominance; negative = seller dominance.

> Reversion risk when price enters a large bearish-Δ cluster below.

> Configurable Inputs: LookBack, number of Bins (10–100), toggles for Delta, Heat Map, Volume Bars, and PoC color.

> Readable Colors: Separate inputs for bullish (volume +) and bearish (volume –) hues.

> Manage risk around the PoC; reactions there can be sharp.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/script/JUWuAXdx-DeltaFlow-Volume-Profile-BigBeluga/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
