---
id: tv_o52gurxf_redk_momentum_bars_redk_mo_bars
name: "RedK Momentum Bars (RedK Mo_Bars)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Momentum Bars (RedK Mo_Bars); not a tested trading strategy."
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
# RedK Momentum Bars (RedK Mo_Bars)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Momentum Bars (Mo_Bars) offers a different way to visualize (relative) momentum - and uses some simple TA concepts to provide a different perspective into how we read momentum changes and incorporate that in our trading.

> at a very broad level, we can use Mo_Bars similar to how we use a MACD - both are centered and unrestricted oscillators - note the difference that Mo_Bars is based on 3 MA's rather than 2.

> Here's the detailed (top chart) setup that Mo_Bars is based on -- The settings for the MA's on the price charts have been matched / sync'ed with the Mo_Bars settings on the lower panel to demonstrate how the script works and how it translate the MA action on the price chart to what we see below.

> -- in simple terms, if the main MA is below the signal MA, the bar is red - and when the main MA is above the signal MA, the bar is green - a white bar usually shows up when there's a detected change of relative momentum direction (note that this is not the same as the trend direction - and that's what helps show and exploit convergence and divergence - similar to a MACD)

> the first line is a relatively fast MA with a short length - acts as the main price tracking line

> the second line is slightly slower than the main line - 2 to 3 bars longer length - and will by default use the open value as source - this works better to identify when the closing price starts to move faster than the open (as in, bars more frequently close higher than they open) - this line acts as the signal line - there's an added setting for an additional delay that utilizes regular WMA smoothing - the delay acts to magnify the relative displacement between the 2 MAs

> (I choose to use WMA as the MA type for the filter line .. and there's a good reason for that - which i'll skip for now - but in future versions, we can add other selectable MA types. )

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

- https://www.tradingview.com/script/O52gURXf-RedK-Momentum-Bars-RedK-Mo-Bars/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
