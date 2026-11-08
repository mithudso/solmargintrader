---
id: tv_muxarne5_audcad_day_trade_signal_by_keltner_channel
name: "AUDCAD - Day trade signal by Keltner channel"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of AUDCAD - Day trade signal by Keltner channel; not a tested trading strategy."
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
# AUDCAD - Day trade signal by Keltner channel

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

The source defines three Keltner pullback-entry choices. Method 1 first requires a close beyond the upper or lower channel and then waits for a pullback to the basis. Method 2 first requires a close beyond a second outer band and then waits for a pullback to the first upper or lower band. Method 3 combines both and gives Method 1 priority. An optional pivot filter checks higher-high/higher-low or lower-low/lower-high structure. Stops and targets are distances of ATR(20) times separate risk and reward ratios from entry, with signs determined by trade direction. The source states 1% risk, but does not fully specify the channel settings, second-band construction, pivot confirmation or risk/reward ratios. Its advertised win rate is an unverified author claim.

## Documented inputs and source details

> * The signal are tested in 3,5 years. Winrate stability over 52% every year.

> - Stoploss: Calculated from the entry point + - actual fluctuation by the formula ATR (20) * risk ratio (risk).

> - Profit: Calculated from the entry point of the command + - actual oscillation using ATR formula (20) * reward ratio (reward).

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

- https://www.tradingview.com/chart/AUDCAD/MUxArNe5-AUDCAD-Day-trade-signal-by-Keltner-channel/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Additional bound source rules

The following source passages support the mechanism above. They are author
descriptions, not repository performance evidence.

````text
Risk: 1%.
````

````text
+ Keltner channel: the price closed above or below Upper / Lower Keltner for signal 1. Wait for the price to adjust to the Basis line, then enter the order.
````

````text
+ Keltner channel: price closes above or below Upper 2 / Lower 2 Keltner gives signal 1. Wait for the price to adjust to Upper / Lower line, then enter the order.
````

````text
Method 3: combine both, priority 1 if satisfied conditions
````

````text
+ Pivot option: appear rising signal: Higher High / Higher Low. Decline signal: Lower Low / Lower High for signal 2.
````

````text
- When the above conditions are met, the Indicator shows a Buy / Sell signal according to the trend.
````
