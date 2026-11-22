---
id: tv_195p3ylk_commitment_of_traders_legacy_metrics
name: "Commitment of Traders: Legacy Metrics"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Commitment of Traders: Legacy Metrics; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-cot-reports, venue-open-interest-and-liquidation-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Commitment of Traders: Legacy Metrics

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator displays the Commitment of Traders (​COT) legacy data for futures markets.

> Possible values are: All, Old, Other. When commodities have a well-defined marketing season or crop year (e.g. Wheat or Lean Hogs futures), this determines how the data is aggregated. Detailed explanation can be found in the "Old and Other Futures" section of the CTFC Explanatory Notes linked above. The "Major Markets for Which the COT Data Is Shown by Crop Year" table in the Explanatory Notes specifies the commodities that this distinction applies to; selecting "Old" for any of the commodities not in that list will return the same data as in "All", while selecting "Other" will return 0.

> By default, the indicator uses the chart's symbol to derive the COT data it displays. You can also specify a CFTC code in the "CFTC code" field of the script's inputs to display COT data from a symbol different than the chart's.

> The rest of this section documents the script's input fields.

> Commitment of Traders ​(​COT) data is tallied by the Commodity ​Futures Trading Commission (CFTC), a US federal agency that oversees the trading of derivative markets such as futures in the US. It is weekly data that provides traders with information about open interest for an asset. The CFTC oversees derivative markets traded on different exchanges, so ​COT data is available for assets that can be traded on CBOT, ​CME, NYMEX, COMEX, and ICEUS.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-cot-reports, venue-open-interest-and-liquidation-history.
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

- https://www.tradingview.com/script/195p3YlK-Commitment-of-Traders-Legacy-Metrics/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
