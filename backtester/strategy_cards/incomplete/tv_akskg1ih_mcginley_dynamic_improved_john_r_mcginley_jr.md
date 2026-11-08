---
id: tv_akskg1ih_mcginley_dynamic_improved_john_r_mcginley_jr
name: "McGinley Dynamic (Improved) - John R. McGinley, Jr."
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of McGinley Dynamic (Improved) - John R. McGinley, Jr.; not a tested trading strategy."
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
# McGinley Dynamic (Improved) - John R. McGinley, Jr.

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> For all the McGinley enthusiasts out there, this is my improved version of the "McGinley Dynamic", originally formulated and publicized in 1990 by John R. McGinley, Jr. Prior to this release, I recently had an encounter with a member request regarding the reliability and stability of the general algorithm. Years ago, I attempted to discover the root of it's inconsistency, but success was not possible until now. Being no stranger to a good old fashioned computational crisis, I revisited it with considerable contemplation.

> I discovered a lack of constraints in the formulation that either caused the algorithm to implode to near zero and zero OR it could explosively enlarge to near infinite values during unusual price action volatility conditions, occurring on different time frames. A numeric E-notation in a moving average doesn't mean a stock just shot up in excess of a few quintillion in value from just "10ish" moments ago. Anyone experienced with the usual McGinley Dynamic, has probably encountered this with dynamically dramatic surprises in their chart, destroying it's usability.

> Well, I believe I have found an answer to this dilemma of 'susceptibility to miscalculation', to provide what is most likely McGinley's whole hearted intention. It required upgrading the formulation with two constraints applied to it using min/max() functions. Let me explain why below.

> The ephemeral presence of one OR both of those potentials now has a combined satisfactory remedy, AND you as TV members now have it, endowed with the ever evolving "Power of Pine". Oh yeah, this one plots from bar_index==0 too. It also has experimental settings tweaks to play with, that may reveal untapped potential of this formulation. This function now has gain of function capabilities, NOT to be confused with viral gain of function enhancements from reckless BSL-4 leaking laboratories that need to be eternally abolished from this planet. Although, I do have hopes this imd() function has the

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

- https://www.tradingview.com/script/AKsKg1ih-McGinley-Dynamic-Improved-John-R-McGinley-Jr/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
