---
id: tv_jja8tyjc_redk_auto_stepping_ladder_trader
name: "RedK Auto-Stepping Ladder Trader"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Auto-Stepping Ladder Trader; not a tested trading strategy."
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
# RedK Auto-Stepping Ladder Trader

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The RedK Auto-Stepping Ladder Trader is an experimental tool to help identify trade entry and exits for various types of trades (Trend / Momentum / Breakout and Swing trades)

> - note that when stepping is enabled, the auto-stepping algo will choose the step value based on the underlying price range and the selected timeframe to move with common trader "mental values" where traders will usually gravitate

> - the signal line (hidden by default, and is what causes the ladder to change color) is based on my Compound Ratio Moving Average - since it's the moving average i found to provide best combination of speed and smoothness. It is used as a proxy to the price, to signal when the price is above or below the ladder level - while removing some of the whipsaws if we use the price value directly.

> - Entries should be as close to the ladder line as possible - a trader may decide to have a small margin above or below the ladder line where they set entry limit order

> - Also test your settings in PaperMoney - i noticed that different instruments may need different settings (for Ladder Type, Length, Rounding Technique, ATR multiplier..etc) for optimal setup that shows best signals.. Get very familiar with the Ladder Trader and it should hopefully become more helpful to you as a tradiing tool.

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

- https://www.tradingview.com/script/jja8TYjc-RedK-Auto-Stepping-Ladder-Trader/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
