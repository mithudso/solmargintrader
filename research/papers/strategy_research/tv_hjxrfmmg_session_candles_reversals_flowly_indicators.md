---
id: tv_hjxrfmmg_session_candles_reversals_flowly_indicators
name: "Session candles & reversals / Flowly Indicators"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Session candles & reversals / Flowly Indicators; not a tested trading strategy."
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
# Session candles & reversals / Flowly Indicators

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Like traditional candles, session based candles are a visualization of open, high, low and close values, but based on session time periods instead of typical timeframes such as daily or weekly. Session candles are formed by fetching price at session start (open), highest price during session (high), lowest price during session (low) and price at session end (close). On top of candles, session based moving average is formed and session reversals detected. Session reversals are also backtested, using win rate and magnitude metrics to better understand what to expect from session reversals and wh

> Session reversals are always based on prior corresponding session, e.g. to qualify as a NY session engulfing up, NY session must have a higher high and lower low relative to prior NY session, not just any session that has taken place in between. Session reversals should be viewed the same way wicks/engulfing formations are viewed on traditional timeframe based candles. Essentially, wick reversals (light green/red labels) tell you most of the motion during session was reversed. Engulfing reversals (dark green/red labels) on the other hand tell you all of the motion was reversed and new directio

> Session reversals are backtested using win rate and magnitude metrics. A session reversal is considered successful when next corresponding session closes higher/lower than session reversal close. Win rate is formed by dividing successful session reversal count with total reversal count, e.g. 5 successful reversals up / 10 reversals up total = 50% win rate. Win rate tells us what are the odds (historically) of session reversal producing a clean supporting move that was persistent enough to close that way too.

> By default, following session time periods are used:

> Session time periods can be changed via input menu.

> All backtesting results are shown in the backtesting panel on top right corner, with highest win rates and magnitude metrics for both reversals up and down marked separately. Note that past performance is not a guarantee of future performance and session reversals as they are should not be viewed as a complete strategy for long/short plays. Always make sure reversal count is sufficient to draw reliable conclusions of performance.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_engulfing`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/HjXrfMMg-Session-candles-reversals-Flowly-Indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
