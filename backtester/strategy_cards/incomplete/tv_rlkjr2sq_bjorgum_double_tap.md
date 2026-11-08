---
id: tv_rlkjr2sq_bjorgum_double_tap
name: "Bjorgum Double Tap"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bjorgum Double Tap; not a tested trading strategy."
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
# Bjorgum Double Tap

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific strategy named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Double Tap is a pattern recognition script aimed at detecting Double Tops and Double Bottoms. Double Tap can be applied to the broker emulator to observe historical results, run as a trading bot for live trade alerts in real time with entry signals, take profit, and stop orders, or to simply detect patterns.

> Repainting is simply the difference in behaviour of a strategy in real time vs the results calculated on the historical dataset. The strategy, by default, will wait for confirmed signals and is thus designed to not repaint. Waiting for bar close for entires aligns results in the real time data feed to those calculated on historical bars, which contain far less data. By doing this we align the behaviour of the strategy on the 2 data types, which brings significance to the calculated results. To override this behaviour and introduce repainting one can select "Recalculate on every tick" from the

> 👉 It is possible to use this script as an indicator as opposed to a full strategy by disabling "Use Strategy" in the "Inputs" tab. Basic alerts for detection will be sent when patterns are detected as opposed to complex order syntax. For alerts mid-bar enable "Recalculate on every tick", and for confirmed signals ensure it is disabled.

> By default, the strategy will place a stop loss at the invalidation point of the pattern. This point is beyond the pattern high in the case of Double Tops, or beneath the pattern low in the case of Double Bottoms. The target or take profit point is an equal-legs measurement, or 100% of the pattern height in the direction of the pattern bias. Both the stop and the limit level can be adjusted from the user menu as a percentage of the pattern height.

> 👉 It is important to note that in the case the trailing stop is enabled, limit orders are excluded from the exit criteria. Rather, the point in time that the limit value is exceeded is the point that the trail begins. As such, this method will exit by stop loss only.

> The following are five options for delivering alerts from Double Tap to live trade execution via third party ​API solutions or chat bots to share your trades on social media. These destinations can be selected from the input menu and alert syntax will automatically configure in alerts appropriately to manage trades.

> Trading Connector is a third party fully autonomous Chrome extension designed to catch alert webhooks from TradingView and interface with MT4/MT5 to execute live trades from your machine. Alerts to Trading Connector are simple; just select the destination from the input drop down menu, set your ticker in the "TC Ticker" box in the "Alert Strings" section and enter your URL in the alert window when configuring your alert.

> Historical back testing is the most common method to test a strategy due in part to the general ease of gathering quick results. The underlying theory is that any strategy that worked well in the past is likely to work well in the future, and conversely, any strategy that performed poorly in the past is likely to perform poorly in the future. It is easy to poke holes in this theory, however, as for one to accept it as gospel, one would have to assume that future results will match what has come to pass. The randomness of markets may see to it otherwise, so it is important to scrutinize results

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_double_top_bottom`, `tv_method_support_resistance`, `tv_method_trailing_stop`.

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

- https://www.tradingview.com/script/rLkjr2sQ-Bjorgum-Double-Tap/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
