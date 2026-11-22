---
id: tv_s7hgang6_intraday_intensity_modes
name: "Intraday Intensity Modes"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Intraday Intensity Modes; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Intraday Intensity Modes

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Intraday Intensity Index was created by David Bostian and its use was later featured by John Bollinger in his book "Bollinger on Bollinger Bands". It is categorically a volume indicator and considered to be a useful tool for analyzing supply and demand dynamics in the market. By measuring the level of buying and selling pressure within a given trading session it attempts to provide insights into the strength of market participants' interest and their aggressiveness in executing trades throughout the day. It can be used in conjunction with Bollinger Bands® or other envelope type indicators as a

> Intraday intensity is calculated based upon the relationship between the price change and the volume of shares traded during each daily interval. It aims to capture the level of buying or selling activity relative to the overall volume. A high intraday intensity value suggests a higher level of buying or selling pressure, indicating a more active and potentially volatile market. Conversely, a low intraday intensity value indicates less pronounced trading activity and a potentially quieter market. Overall, intraday intensity provides a concise description of the intensity of trading activity du

> While there are pre-existing versions within community scripts, none were found to have applied the calculations necessary for the various modes that are presented within this version, which are believed to be operating in the manner originally intended when first described by Bostian and again later by Bollinger. When operating in default modes on daily or lower chart timeframes the logic used within this script tracks the intraday high, low, close and volume for the day with each progressing intraday bar.

> Osc Length: Set to 1 disables oscillation, values greater than 1 enables oscillation for II% (Intraday Intensity percent) mode.

> Normalized: When enabled a rolling window of Osc Length values are summed and normalized to the rolling window's volume.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/S7HGang6-Intraday-Intensity-Modes/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
