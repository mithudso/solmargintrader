---
id: tv_8mvftxpg_tape_lucf
name: "Tape [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Tape [LucF]; not a tested trading strategy."
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
# Tape [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script prints an ersatz of a trading console's "tape" section to the right of your chart. It displays the time, price and volume​ of each update of the chart's feed. It also calculates volume​ delta for the bar. As it calculates from realtime information, it will not display information on historical bars.

> The script first determines if price has moved up or down since the last update. The polarity of the price change, in turn, determines the polarity of the volume​​ for that specific update. If price does not move between consecutive updates, then the last known polarity is used. Using this method, we can calculate a running volume​ delta accumulation for the bar, which becomes the bar's final volume​ delta value when the bar closes (you can inspect values of elapsed realtime bars in the Data Window or the indicator's values). Note that these values will all reset if the script re-executes beca

> While this method of calculating volume​ delta is not perfect, it is currently the most precise way of calculating volume​ delta available on TradingView at the moment. Calculating more precise results would require scripts to have access to bid/ask levels from any chart timeframe. Charts at seconds timeframes do use exchange/broker ticks when the feeds you are using allow for it, and this indicator will run on them, but tick data is not yet available from higher timeframes, for now. Also note that the method used in this script is far superior to the intrabar inspection technique used on hist

> You can use the script's inputs to configure:

> • Marker 3 on tape lines with volume​ exceeding a threshold. These trigger in realtime. Be sure to set a threshold high enough so that it doesn't generate too many alerts.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_volume_delta`.

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

- https://www.tradingview.com/script/8mVFTxPg-Tape-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
