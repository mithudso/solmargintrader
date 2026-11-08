---
id: tv_2s4bqqzq_tasc_2026_10_a_low_risk_etf_trading_strategy
name: "TASC 2026.10 A Low-Risk ETF-Trading Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2026.10 A Low-Risk ETF-Trading Strategy; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# TASC 2026.10 A Low-Risk ETF-Trading Strategy

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements concepts from a short-term ETF investment strategy outlined by Markos Katsanos in the article "Selecting Strong ETFs While Avoiding Sharp Overbought Reversals" from the October 2026 edition of TASC Traders' Tips. The strategy analyzes Katsanos' custom relative strength indicator, RSMK, alongside momentum and correlation to identify entry and exit conditions across a diverse set of ETFs. This script is an indicator designed for scanning for the strategy's conditions in the Pine Screener.

> Katsanos' strategy scans a diverse set of exchange-traded funds (ETFs) for strict entry and exit criteria based on relative strength, momentum, and correlation with a benchmark index. The objective is to achieve returns comparable to a buy-and-hold portfolio, while reducing downside risks for better risk-adjusted performance. The strategy operates on ETFs because they're well-suited for short-term investing. Their diversified holdings offer broad market exposure, and often high liquidity and relatively lower volatility.

> At its core, the strategy uses a modified relative strength indicator named RSMK, which Katsanos originally introduced in the March 2020 issue of TASC Traders' Tips. His RSMK aims to address the shortcomings of traditional relative strength (RS) analysis. While traditional RS calculates the ratio between two instruments' prices, the RSMK calculates the smoothed change in the natural logarithm of the ratio and scales it as a percentage. The formula is as follows:

> Because the strategy operates on multiple instruments rather than a single one, this script is implemented as an indicator designed to scan the entry and exit criteria with the Pine Screener. Select this indicator from the screener's menu and apply it to a selected watchlist. We've also prepared this watchlist for analyzing the same set of instruments referenced in the article.

> The author's strategy relies on the following sets of conditions to determine entry points. Users can customize these conditions, as well as the exit conditions, in the "Settings/Inputs" tab. An entry signal occurs only if all of the conditions are true:

> The following criteria determine when to close a position. An exit signal occurs if any of these conditions are true:

> When an entry signal occurs for any symbol, the "Entry" column on that symbol's row shows a value of 1. When an exit signal occurs, the "Exit" column shows a value of -1. If neither signal occurs, neither column displays a value. After an entry signal occurs, the "Entry price" and "Position performance" columns display the entry price and current percentage return until the exit signal occurs.

> When the script runs on a chart, it displays a green triangle on each entry bar and a dotted line indicating the position's entry price in the main chart pane. It also shows a green or red fill between the current price and the entry price while the position is active. When an exit condition occurs, the script displays a red "X" above the exit bar. In a separate pane, the script displays the RSMK indicator alongside its moving average:

> The 10-length RSI was below 35 at least once over the last 20 days.

> The 5-length EMA is above the 15-day SMA from five days ago.

> Risk-adjusted performance refers to a strategy's profitability relative to the risk required to achieve it. In his article, Katsanos explains that many trading strategies offer promising returns but poor risk-adjusted performance due to high volatility or drawdowns. In other words, the returns from such strategies may not justify the risk.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `xs_momentum`.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/2S4BqQzQ-TASC-2026-10-A-Low-Risk-ETF-Trading-Strategy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
