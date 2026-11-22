---
id: tv_xkbwnq2h_intrabar_run_count_indicator_tbiktag
name: "Intrabar Run Count Indicator [tbiktag]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Intrabar Run Count Indicator [tbiktag]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Intrabar Run Count Indicator [tbiktag]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Introducing the Intrabar Run Count Indicator, a tool designed to detect potential non-randomness in intrabar price data. It utilizes the statistical runs test to examine the number of sequences (runs) of positive and negative returns in the analyzed price series. As deviations from random-walk behavior of returns may indicate market inefficiencies, the Intrabar Run Count Indicator can help traders gain a better understanding of the price dynamics inside each chart bar and make more informed trading decisions.

> To search for potential inefficiencies, the Intrabar Run Count Indicator analyzes the distribution of the signs of returns. The central assumption underlying the indicator's logic is that if the asset price follows a random-walk pattern, then the probability of the next return being positive or negative (i.e., the next price value being larger or smaller than the current value) follows a binomial distribution. In this case, the number of runs is also a random variable, and, for a large sample, its conditional distribution is approximately normal with a well-defined mean and variance (see this

> Quantitatively, the deviation from randomness can be gauged by calculating the test statistic of the runs test (that serves as an indicator line). It is defined as the absolute difference between the observed number of runs and the expected number of runs under the null hypothesis of randomness, divided by the standard deviation of the expected number of runs. If the test statistic is negative and exceeds the negative critical value (at a given confidence level), it suggests that there are fewer runs than expected for a random-walking time series. Likewise, if the test statistic exceeds the po

> The indicator line expresses​ the deviation between the number of runs observed in the dataset and the expected number of runs under the hypothesis of randomness​. Thus, it gauges the degree of deviation from random-walk behavior. If, for a given chart bar, it crosses above the critical value or crosses below the negative critical value, this may indicate non-randomness in the underlying intrabar returns. These instances are highlighted by on-chart signals and bar coloring. The confidence level that defines the critical value, as well as the number of intrabars used for analysis, are selected

> It is important to note that the readings of the Intrabar Run Count Indicator do not convey directional information and cannot predict future asset performance. Rather, they help distinguish between random and potentially tradable price movements, such as breakouts, reversals, and gap fillings.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_gap_fill`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/XkBwnQ2h-Intrabar-Run-Count-Indicator-tbiktag/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
