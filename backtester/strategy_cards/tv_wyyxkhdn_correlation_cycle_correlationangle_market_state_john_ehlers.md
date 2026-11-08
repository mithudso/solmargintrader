---
id: tv_wyyxkhdn_correlation_cycle_correlationangle_market_state_john_ehlers
name: "Correlation Cycle, CorrelationAngle, Market State - John Ehlers"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Correlation Cycle, CorrelationAngle, Market State - John Ehlers; not a tested trading strategy."
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
# Correlation Cycle, CorrelationAngle, Market State - John Ehlers

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Hot off the press, I present this "Correlation Cycle, CorrelationAngle, and Market State" multicator employing PSv4.0, originally formulated by Dr. John Ehlers for TASC - June 2020 Traders Tips. Basically it's an all-in-one combination of three Ehlers' indicators. This power packed triplet indicator, being less than a 100 line implementation at initial release, is a heavily modified version of the original indicator using novel techniques that surpass John Ehlers' original intended design.

> As always, I have included advanced Pine programming techniques that conform to proper "Pine Etiquette" by example. There are so many Pine mastery techniques included, I don't have an abundance of time to elaborate on all of them. For those of you are code savvy, you may have notice I only used one "for" loop for increased server efficiency, instead of the two "for" loops in the original formulation. For those of you who are newcomers to Pine Script, this code release may also help you comprehend the immense "Power of Pine" by employing advanced programming techniques while exhibiting code uti

> I have created many of Ehlers' indicators in PE, a few of which I have published in my profile, but I wanted to show how programming with Pine Script can be an artistic form of craftsmanship and poetry. None of this would be possible without the ingeniously minded Tradingview staff revolutionizing algorithmic trading at it's finest. If you should ever encounter them by chance, ponder humbly thanking these computing wizards for their diligence and dedication. They are providing, and shall award to us members, some of the most fascinating conceptualized tech imaginable in the coming future. I ca

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

- https://www.tradingview.com/script/wyyXKHDn-Correlation-Cycle-CorrelationAngle-Market-State-John-Ehlers/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
