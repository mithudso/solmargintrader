---
id: tv_cjx3k6l2_stop_loss_cascades_breakouts_kioseff_trading
name: "Stop Loss Cascades (Breakouts) [Kioseff Trading]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Stop Loss Cascades (Breakouts) [Kioseff Trading]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Stop Loss Cascades (Breakouts) [Kioseff Trading]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This indicator "Stop-Loss Clustering (Breakouts)" attempts to model trader stop-loss placement logic and identify price areas where a large amount of stop losses might cluster.

> Because the true distribution of stop placement is unobservable, the model assumes that positions entered are structurally invalidated at the closest swing level based on their classified direction.

> It then identifies historical observations whose sizes are most similar to the current value, either by selecting all observations within a tolerance range around that value (where the range is based on the typical spacing between historical observations), or by selecting the single closest match.

> The idea is, if stop losses are indeed highly concentrated in a specific area, price extending through that area may produce high-velocity breakout conditions via forced order flow.

> I'll cover this topic more thoroughly throughout the description. For now, just know that stop loss location & size data is not publicly available. Any model of their concentration locations is highly assumptive.

> A trader entering a long position may place their stop-loss below a recent swing low, reasoning that if price breaks that level, the trade idea is invalidated.

> A trader entering a short position may place their stop-loss above a recent swing high for the same reason.

> This is where ”Stop-Loss Clustering (Breakouts)” becomes important - we’re almost done!

> Pink-shaded regions indicate a price area with greater opportunity for stop loss clustering. Volume was significant around these regions or price has traded within proximity for extended periods.

> Market structure traders frequently reference prior swing highs and swing lows when making decisions about entries, exits, and risk.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_market_structure`, `tv_method_round_number_levels`, `tv_method_support_resistance`, `tv_method_volume_footprint`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements, classified-tick-or-lower-timeframe-history, level2-orderbook-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/CJX3k6l2-Stop-Loss-Cascades-Breakouts-Kioseff-Trading/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
