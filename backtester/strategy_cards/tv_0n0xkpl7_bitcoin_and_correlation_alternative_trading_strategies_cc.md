---
id: tv_0n0xkpl7_bitcoin_and_correlation_alternative_trading_strategies_cc
name: "BITCOIN and CORRELATION, alternative trading strategies (CC)"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of BITCOIN and CORRELATION, alternative trading strategies (CC); not a tested trading strategy."
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
# BITCOIN and CORRELATION, alternative trading strategies (CC)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The correlation coefficient is a statistical measure of the strength of the relationship between the relative movements of two variables. The values range between -1.0 and 1.0. A calculated number greater than 1.0 or less than -1.0 means that there was an error in the correlation measurement. A correlation of -1.0 shows a perfect negative correlation, while a correlation of 1.0 shows a perfect positive correlation. A correlation of 0.0 shows no linear relationship between the movement of the two variables.

> A high degree of correlation between the equity markets and Bitcoin has existed, particularly in the last few months. In other periods, gold and Bitcoin appear to move in tandem. However, the correlation that should be watched the most is the dollar since the global economy is based on the strength or weakness of our world reserve currency, the United States dollar. Weaker USD drove up Bitcoin prices in Q2, Q3 2020.

> The greenback is currently overvalued by 10% to 15% based on several reasons, according to Zach Pandl, co-head of global FX and EM strategy at Goldman Sachs. A drop on this scale would bring the dollar index to its lowest since late 2014. Furthermore a stimulus package and/or another lockdown will push the dollar even lower. We can use this information to plan a strategy for a correlation trade between BTC and other markets.

> In other words, investors can use negatively-correlated assets or securities to hedge their portfolio and reduce market risk due to volatility or wild price fluctuations. Many investors hedge the price risk of a portfolio, which effectively reduces any capital gains or losses because they want the dividend income or yield from the stock or security.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

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

- https://www.tradingview.com/chart/BTCUSD/0n0XkpL7-BITCOIN-and-CORRELATION-alternative-trading-strategies-CC/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
