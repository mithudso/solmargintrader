---
id: tv_gy4ilk5n_momentum_based_zigzag_incl_qqe_non_repainting
name: "Momentum-based ZigZag (incl. QQE) NON-REPAINTING"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Momentum-based ZigZag (incl. QQE) NON-REPAINTING; not a tested trading strategy."
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
# Momentum-based ZigZag (incl. QQE) NON-REPAINTING

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I spent a lot of time searching for the best ZigZag indicator. Difficulty with all of them is that they are always betting on some pre-defined rules which identify or confirm pivot points. Usually it is time factor - pivot point gets confirmed after a particular number of candles. This methodology is probably the best when market is moving relatively slow, but when price starts chopping up and down, there is no way the ZigZag follows accurately. On the other hand if you set it too tight (for example pivot confirmation after only 2 or even 1 candle), you will get hundreds of zigzag lines and th

> My point of view is to follow the market. If it has reversed, then it has reversed, and there is no need to wait pre-defined number of candles for the confirmation. Such reversals will always be visible on momentum indicators, such as the most popular MACD. But a single-line moving average can be also good enough to notice reversals. Or my favourite one - QQE, which I borrowed (and improved) from JustUncleL, who borrowed it from Glaz, who borrowed it from... I don't even know where Quantitative Qualitative Estimation originates from. Thanks to all these guys for their input and code.

> I'm about to publish some more scripts based on this ZigZag algo, so follow me on TradingView to get notified.

> One thing I need to emphasize. This indicator DOES NOT REPAINT. It might look like the lines are a bit delayed, especially when compared to all the other ZigZag indicators on TradingView, but they are actually TRUE. There is a value in this - my indicator prints pivot points and Zigzag exactly on the moment they have been noticed, not earlier faking to be faster than they could be.

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

- https://www.tradingview.com/script/gY4ilk5N-Momentum-based-ZigZag-incl-QQE-NON-REPAINTING/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
