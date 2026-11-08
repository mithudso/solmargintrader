---
id: tv_8owcuqfq_multi_distribution_volume_profile_zeiierman
name: "Multi-Distribution Volume Profile (Zeiierman)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Multi-Distribution Volume Profile (Zeiierman); not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Multi-Distribution Volume Profile (Zeiierman)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Multi-Distribution Volume Profile (Zeiierman) is a flexible, structure-first volume profile tool that lets you reshape how volume is distributed across price, from classic uniform profiles to advanced statistical curves like Gaussian, Lognormal, Student-t, and more.

> The script scans a user-defined Bars Included window and finds the full high–low span of that zone. It then divides this range into a user-controlled number of Price Levels (rows).

> It measures the candle’s price range, body, and wicks.

> When Apply Gradient is enabled, the row’s bullish/bearish colors are tinted from faint to strong based on this chosen metric, effectively turning the profile into a heatmap of your chosen structural property.

> Instead of forcing every market into a single "one-size-fits-all" profile, this tool lets you model how volume is likely concentrated inside each bar (body vs wicks, midpoint, tails, center bias, right-skew, heavy tails, etc.) and then stacks that behavior across a whole lookback window to build a rich, multi-distribution map of traded activity.

> Profile Thickness – Relative thickness of the profile along the time axis, as a % of the lookback window.

> The content provided in my scripts, indicators, ideas, algorithms, and systems is for educational and informational purposes only. It does not constitute financial advice, investment recommendations, or a solicitation to buy or sell any financial instruments. I will not accept liability for any loss or damage, including without limitation any loss of profit, which may arise directly or indirectly from the use of or reliance on such information.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/8owCUqFq-Multi-Distribution-Volume-Profile-Zeiierman/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
