---
id: tv_qtkfi42t_macd_x_overlay_more_than_macd_by_dgt
name: "MACD-X Overlay, More Than MACD by DGT"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of MACD-X Overlay, More Than MACD by DGT; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# MACD-X Overlay, More Than MACD by DGT

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The most popular indicator used in technical analysis , the moving average convergence divergence ( MACD ), created by Gerald Appel. MACD is a trend-following momentum indicator , designed to reveal changes in the strength, direction, momentum, and duration of a trend in a financial instrument’s price

> In its simples form, MACD-X implements variety of different calculation techniques applied to obtain MACD Line. Different calculation techniques lead to different values for MACD Line, as will further discuss below, and as a consequence the signal line and the histogram values will differentiate accordingly.

> 2- Introduces different proven techniques applied on MACD calculation, such as MACD-AS (Histogram), MACD-Leader and MACD-Source, besides the traditional MACD (MACD-TRADITIONAL)

> MACD employs two Moving Averages of varying lengths (which are lagging indicators) to identify trend direction and duration. Then, MACD takes the difference in values between those two Moving Averages (MACD Line) and an EMA of those Moving Averages (Signal Line) and plots that difference between the two lines as a histogram which oscillates above and below a center Zero Line. The histogram is used as a good indication of a security's momentum.

> 1- Plotting of the Oscillator presented on top of the price chart (main chart) and applicable on both log and linear scale. Maximum plotting length is limited to 250 bars

> The MACD-Histogram measures the distance between MACD and its signal line (the 9-day EMA of MACD ). Aspray developed the MACD-Histogram to anticipate signal line crossovers in MACD . Because MACD uses moving averages and moving averages lag price, signal line crossovers can come late and affect the reward-to-risk ratio of a trade. Bullish or bearish divergences in the MACD-Histogram can alert chartists to an imminent signal line crossover in MACD

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/qtkFi42t-MACD-X-Overlay-More-Than-MACD-by-DGT/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
