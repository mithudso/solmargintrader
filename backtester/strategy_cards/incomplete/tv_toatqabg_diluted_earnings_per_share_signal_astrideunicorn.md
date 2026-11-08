---
id: tv_toatqabg_diluted_earnings_per_share_signal_astrideunicorn
name: "Diluted Earnings Per Share Signal [AstrideUnicorn]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Diluted Earnings Per Share Signal [AstrideUnicorn]; not a tested trading strategy."
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
# Diluted Earnings Per Share Signal [AstrideUnicorn]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Earnings Per Share (EPS) is a financial metric closely monitored by investors. The so-called "positive earnings surprise" - a situation when EPS reading for a stock beats the value forecasted by analysts gives a bullish signal for this stock. The EPS reading lower than the analysts' estimate gives a bearish signal.

> The Diluted Earnings Per Share (Diluted EPS) metric calculates a company's potential earnings per share value in the case if all convertible securities get converted to common shares. Convertible securities include preferred shares, stock options, warrants, convertible debt, etc. Diluted EPS is a more scientific way to estimate earnings per share, and it is usually lower than the ordinary EPS.

> The Diluted EPS Signal indicator (DEPSS) is a fundamental indicator that calculates trading signals by comparing the Diluted EPS to the EPS Estimate. In many cases, Diluted EPS gives better insight into how a reported EPS reading may impact the stock price.

> Diluted Earnings Surprise higher than the specified threshold value is a bullish signal. In this case, the indicator displays a green triangle pointing up.

> Diluted Earnings Surprise lower than the specified threshold value is a bearish signal displayed as a red triangle pointing down.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/script/ToaTQAbG-Diluted-Earnings-Per-Share-Signal-AstrideUnicorn/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
