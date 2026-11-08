---
id: tv_yln2bnaa_auto_fibonacci_and_gann_fan_retracements_combo
name: "Auto Fibonacci and Gann Fan/Retracements Combo"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Auto Fibonacci and Gann Fan/Retracements Combo; not a tested trading strategy."
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
# Auto Fibonacci and Gann Fan/Retracements Combo

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This is a combination of Fibonacci and Gann fan/retracements.

> as the user requires on the chart. Each level set or fan consists of 7 lines based on the most important ratios of Fibonacci/Gann.

> In this new script I tried to find the exact highest and lowest prices based on this idea that: if a high point is formed lower than previous high which was after a lowest point, then that previous one was the local highest point, and vice versa if a low point is formed higher than previous low which was after a highest point, then that previous one was the local lowest point. So logically an extremum price on the chart won't be found until the next high/low point is formed.

> In order to draw Fibonacci and Gann fan/retracements, it's necessary to find local highest and lowest price points (Extrema) on the chart. As this could be so challenging, most traders and coders draw the lines covering the low and high prices over a given period of time or a limited number of bars back instead. I already wrote an indicator using this approach (Auto Fibonacci Combo).

> A Gann fan consists of a series of lines called Gann angles. These angles are superimposed over a price chart to show potential support and resistance levels. The resulting image is supposed to help technical analysts predict price changes. Gann believed the 45-degree angle to be most important, but the Gann fan also draws angles at degrees like 75, 63.75, 26.25 and 15. The Gann fan originates at a low or high point. The resulting lines show areas of potential future support and resistance. The 45-degree line is known as the 1:1 line because the price will rise or fall at a 45-degree angle whe

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_gann`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/YLn2bNaa-Auto-Fibonacci-and-Gann-Fan-Retracements-Combo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
