---
id: tv_y3pnzg2q_correlation_heatmap
name: "Correlation Heatmap"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Correlation Heatmap; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Correlation Heatmap

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator creates a correlation matrix for a user-specified list of symbols based on their time-aligned weekly or monthly price returns. It calculates the Pearson correlation coefficient for each possible symbol pair, and it displays the results in a symmetric table with heatmap-colored cells. This format provides an intuitive view of the linear relationships between various symbols' price movements over a specific time range.

> The Pearson correlation coefficient quantifies the strength and direction of the linear relationship between two variables. In other words, it indicates how consistently variables' values move together or in opposite directions in a proportional, linear manner. Its formula is as follows:

> In essence, the correlation coefficient measures the covariance between two variables, normalized by the product of their standard deviations. The coefficient's value ranges from -1 to 1, allowing a more straightforward interpretation of the relationship between two datasets than what covariance alone provides:

> In a financial time series, each data point (i.e., bar) in a sample represents information collected in periodic intervals. For instance, on a "1D" chart, bars form at specific times as successive days elapse.

> It's crucial to note that because this process retrieves prices for a symbol at times consistent with periodic points on the current chart, the values can represent prices from before or after the closing time of the symbol's usual session.

> Traders frequently analyze asset correlations to help optimize portfolios, assess market behaviors, identify potential risks, and support trading decisions. For instance, correlation often plays a key role in diversification. When two instruments exhibit a strong correlation in their returns, it might indicate that buying or selling both carries elevated unsystematic risk. Therefore, traders often aim to create balanced portfolios of relatively uncorrelated or anticorrelated assets to help promote investment diversity and potentially offset some of the risks.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_seasonality`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/Y3PnzG2q-Correlation-Heatmap/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
