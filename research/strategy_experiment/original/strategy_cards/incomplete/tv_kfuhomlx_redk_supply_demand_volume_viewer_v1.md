---
id: tv_kfuhomlx_redk_supply_demand_volume_viewer_v1
name: "RedK_Supply/Demand Volume Viewer v1"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK_Supply/Demand Volume Viewer v1; not a tested trading strategy."
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
# RedK_Supply/Demand Volume Viewer v1

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> VolumeViewer is a volume indicator, that offers a simple way to estimate the movement and balance (or lack of) of supply & demand volume based on the shape of the price bar. i put this together few years ago and i have a version of this published for another platform under different names (Directional Volume, BetterVolume) in case you come across them

> - to achieve that, we depend on a simple assumption, that the volume associated with an up move is "demand" and the volume associated with a down move is "Supply". so we basically extrapolate these supply and demand values based on how the bar looks like - a full "green" price bar / candle will be considered 100% demand, and a full "red" price bar will be considered 100% supply - a bar that opens and closes at the same level will be 50/50 split between supply & demand.

> 1. first we calculate a score % for the volume portion that is considered demand based on the bar shape

> - the premise is, at spots where there's big lack of balance, that's where to expect to find key price levels (support / resistance) and these price levels will come into play in future so can be used to set entry / exit targets for our trades - see the example in the AAPL chart where you can easily locate these "balance or reversal levels" using the tops/bottoms/zero-crossings from the Net Volume line

> 2. after calculating the Bull vs Bears portion of volume, we take a moving average of both for the length you set, to come up with what we consider to be the Demand vs Supply - as usual, i use a weighted moving average (WMA) here.

> - we can also use this simple indicator to gain more insights (at a high level) of the price in terms of accumulation vs distribution and if the sellers or buyers are in control - for example, in the above AAPL chart, V.Viewer tells us that buyers have been in control since October 19 - even during the recent drop, demand continued to be in play - compare that to DIS chart below for the same period, where it shows that the market was dumping DIS thru the weakness. DIS was bleeding red most of the time

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`, `tv_method_volume_footprint`.

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

- https://www.tradingview.com/script/kfUHOMlX-RedK-Supply-Demand-Volume-Viewer-v1/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
