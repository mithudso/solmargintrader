---
id: tv_xp9odtfm_volume_profile_volume_delta_oi_delta_kioseff_trading
name: "Volume Profile Volume Delta OI Delta [Kioseff Trading]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Volume Profile Volume Delta OI Delta [Kioseff Trading]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, venue-open-interest-and-liquidation-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Volume Profile Volume Delta OI Delta [Kioseff Trading]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script serves to distinguish volume delta for any asset and open interest delta for Binance perpetual futures.

> The image above shows the indicator calculating volume at each tick level and displaying the metric.

> The image above shows Open Interest (OI) Delta calculated - similar to how the script calculates volume delta - for a Binance Perpetual Future pair.

> The indicator assumes a 60/40 split when a tick level is traded at and only one metric - "buy volume" or "sell volume" is recorded. This means there shouldn't be any levels recorded where "buy volume" is greater than 0 and "sell volume" equals 0 and vice versa. While this assumption was performed arbitrarily, it may help better replicate volume delta and OI delta calculations seen on other charting platforms.

> Further, the script can be set to recalculate after a user-defined time threshold is exceeded. You can also define the percentage or tick distance between levels.

> This feature only works for Binance Futures pairs; the script will not load when trying to calculate OI Delta on other assets.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`.

## Data and availability

Required inputs: ohlcv, venue-open-interest-and-liquidation-history.
The complete point-in-time input set has not been verified in the repository. Do not substitute current snapshots or inferred values for historical inputs.

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

- https://www.tradingview.com/script/xp9OdTFm-Volume-Profile-Volume-Delta-OI-Delta-Kioseff-Trading/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
