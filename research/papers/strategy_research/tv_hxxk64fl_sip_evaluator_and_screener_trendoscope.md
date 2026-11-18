---
id: tv_hxxk64fl_sip_evaluator_and_screener_trendoscope
name: "SIP Evaluator and Screener [Trendoscope®]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of SIP Evaluator and Screener [Trendoscope®]; not a tested trading strategy."
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
# SIP Evaluator and Screener [Trendoscope®]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The SIP Evaluator and Screener [Trendoscope®] is a Pine Script indicator designed for TradingView to calculate and visualize Systematic Investment Plan (SIP) returns across multiple investment instruments. It is tailored for use in TradingView's screener, enabling users to evaluate SIP performance for various assets efficiently.

> Regular Investments: In an SIP, an investor commits to investing a fixed sum at predefined intervals, regardless of market conditions. This consistency helps inculcate a habit of saving and investing.

> In the context of the SIP Evaluator and Screener [Trendoscope®], the script simulates an SIP by calculating the number of units purchased with each fixed investment, factoring in commissions, dividends, taxes and the chosen price reference (e.g., open, close, or average prices). It tracks the cumulative investment, equity value, and dividends over time, providing a clear picture of how an SIP would perform for a given instrument. This helps users understand the impact of regular investing and make informed decisions when comparing different assets in TradingView’s screener. It offers insights

> Customizable Investment Parameters: Users can define the recurring investment amount, price reference (e.g., open, close, HL2, HLC3, OHLC4), and whether fractional quantities are allowed.

> Dividend Reinvestment: Optionally reinvests dividends after a user-specified period, with the ability to apply tax on dividends.

> Cost Averaging: By investing a fixed amount regularly, investors purchase more units when prices are low and fewer units when prices are high. This approach, known as dollar-cost averaging, reduces the average cost per unit over time and mitigates the risk of investing a large amount at a peak price.

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

- https://www.tradingview.com/script/Hxxk64fl-SIP-Evaluator-and-Screener-Trendoscope/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
