---
id: tv_method_value_investing
name: "Financial ratio value screening"
kind: exposure-strategy
status: spec-only
family: research-method
summary: "Specification of Financial ratio value screening; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Financial ratio value screening

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Rank a point-in-time investable universe by declared valuation/profitability measures, with fiscal release timestamps and corporate-action adjustments. Freeze rebalancing and exclusion rules. Today's restated accounts must not enter historical decisions.

## Documented inputs and source details

This is a conventional reference specification of the named mechanism. Source
articles may use different thresholds or subjective annotations. Their names identify
the concept; they do not establish a unique source algorithm.

No numeric trading defaults are invented. Freeze any missing choices before testing.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: point-in-time-financial-statements.
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

- https://www.tradingview.com/script/HjgCUw6g-Dynamic-Equity-Allocation-Model/
- https://www.tradingview.com/script/Lbxl9OqZ-Financials-on-Chart/
- https://www.tradingview.com/script/Mb0faMoT-Advanced-Fed-Decision-Forecast-Model-AFDFM/
- https://www.tradingview.com/script/Tlz0MxsJ-Sticky-Notes-Checklist-To-do-Journal-algoat/
- https://www.tradingview.com/script/lu0MTsuD-Earnings-Snapshot-Trendoscope/
- https://www.tradingview.com/script/wiJMcWZ7-Financial-Statement-Indicator-by-zdmre/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
