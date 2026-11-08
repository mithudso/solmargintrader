---
id: tv_method_dominance_rotation
name: "Bitcoin dominance and altcoin rotation"
kind: exposure-strategy
status: spec-only
family: research-method
summary: "Specification of Bitcoin dominance and altcoin rotation; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [point-in-time-crypto-market-cap-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Bitcoin dominance and altcoin rotation

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Track point-in-time BTC market cap divided by a fixed cryptocurrency-universe market cap. Define dominance/momentum thresholds and rotation legs using past data. Universe survivorship, stablecoin inclusion and fees can dominate the result.

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

Required inputs: point-in-time-crypto-market-cap-universe.
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

- https://www.tradingview.com/script/C8RarGoe-Relative-Crypto-Dominance-Polar-Chart-LuxAlgo/
- https://www.tradingview.com/chart/BTC.D/G3y6ZjUi-Can-BTC-Reversals-Be-Predicted-Using-BTC-D-and-LTC/
- https://www.tradingview.com/chart/BTC.D/NY48h7T7-How-to-Use-the-Bitcoin-Dominance-Chart-to-Maximize-Profits/
- https://www.tradingview.com/chart/BTC.D/NzsdHbcS-Bitcoin-Dominance-BTC-D-Approaching-ATH/
- https://www.tradingview.com/chart/BTC.D/S2j92IRy-BTC-Dominance-Where-next/
- https://www.tradingview.com/chart/BTC.D/VPh8gNg7-BTC-D-vs-ETH-D-ARE-WE-ABOUT-TO-SHIFT-GEARS/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
