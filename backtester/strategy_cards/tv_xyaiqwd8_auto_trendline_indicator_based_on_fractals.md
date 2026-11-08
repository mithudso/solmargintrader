---
id: tv_xyaiqwd8_auto_trendline_indicator_based_on_fractals
name: "Auto Trendline Indicator (based on fractals)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Auto Trendline Indicator (based on fractals); not a tested trading strategy."
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
# Auto Trendline Indicator (based on fractals)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> A tool that automatically draws out trend lines by connecting the most recent fractals.

> The process of manual drawing out trend lines is highly subjective. Many times, we don’t trade what we see, but what we “want to see”. As a result, we draw lines pointing to the direction that we wishfully want price to move towards. While there are no right/wrong ways to draw trend lines, there are, however, systematic/unsystematic ways to draw trend lines. This tool will systematically draw out trend lines based on fractals.

> The purpose of this exercise is to take a tool that is readily available (ie. in this case, TradingView’s built-in fractals tool), and to create a newer tool based on it.

> Fractal period (denoted as ‘n’ in code): It is the number of bars bounding a high/low point that must be lower/higher than it, respectively, in order for fractal to be considered valid. Period ‘n’ can be adjusted in this tool. Traditionally, chartists pick the value of 5. The longer it is, the less noise seen on the chart, and the pivot point may also be exhibited in higher timeframes. The drawback is that it will increase the period of lag, and it will take more bars to confirm the printed fractal.

> Others: Intuitive parameters such as whether to draw historical trend lines, what color to use, which way to extend the lines, and whether or not to show points of crossings.

> Here is an interesting observation on the price actions of NASDAQ futures on a 5 second chart during regular trading hours on July 14, 2022.

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

- https://www.tradingview.com/script/xYaiqwD8-Auto-Trendline-Indicator-based-on-fractals/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
