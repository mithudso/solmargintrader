---
id: tv_7tsb40pn_magic_change_of_bill_williams_s_awesome_oscillator
name: "\"Magic Change\" of Bill Williams's Awesome Oscillator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of \"Magic Change\" of Bill Williams's Awesome Oscillator; not a tested trading strategy."
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
# "Magic Change" of Bill Williams's Awesome Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> According to Bill Williams' definition, the Awesome indicator is an oscillator, abbreviated as AO. Unlike the KDJ indicator (range from 0 to +100), the output range of the awesome indicator is unlimited. Literally, many people might think that the awesome oscillator indicator is composed of a complex algorithm developed by MIT’s prodigy, but you may be surprised to find that the indicator was originally a basic calculation of two simple moving averages, or even NO EMA is used inside. In Tradingivew Built-in functions, tt is a red and green column composed of the difference between the simple m

> Using EAO to observe the twin peaks divergence is a classic method. Deviation means that the price keeps breaking new lows, but the second peak of EAO's unilateral double peak is closer to the zero axis than the first peak. This kind of divergence appears above the zero axis and is the top divergence. The bottom deviation is the opposite, appearing on the lower side of the zero axis. It’s important to note that don’t think that deviations from 100% will cause prices to fall or rise. The market is a complex system, and there will be situations where the deviation is completed and then deviated,

> 2. If EAO crosses zero strongly, you need to wait for the column to change color and take profit. If it is consolidating near the zero axis, take the consolidating price high and low points as the price range to wait for a breakthrough, and use the EAO column expansion as a confirmation signal.

> If you are familiar with Bill Williams’ theory, you may know that he has five "magic bullets", one of which is the usage of MACD with 5/34/5 as the parameter. Coincidentally, he really likes Fibonacci numbers 5 and 34, and he also chooses these two magic numbers as parameters in AO.

> The one-sided carbine means that after EAO runs in the trend for a period of time on the zero axis side, the corresponding column begins to shrink; however, after shrinking to a certain extent, the original trend column color reverses suddenly. This corresponds to a pause on the way up or down in price. For example, during the ascent process, this is the performance of the banker force shaking off or washing out individuals. In this process, you can lighten up your position appropriately, or you can lie down and wait. Because the overall trend is still continuing, because they are all on the s

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

- https://www.tradingview.com/chart/BTCUSD/7tSB40Pn-Magic-Change-of-Bill-Williams-s-Awesome-Oscillator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
