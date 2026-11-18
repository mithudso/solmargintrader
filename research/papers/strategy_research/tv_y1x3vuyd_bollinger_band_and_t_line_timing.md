---
id: tv_y1x3vuyd_bollinger_band_and_t_line_timing
name: "Bollinger Band and T-Line Timing"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bollinger Band and T-Line Timing; not a tested trading strategy."
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
# Bollinger Band and T-Line Timing

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Here is a method to track current trends and spot reversals.

> On February 27th, price broke the Bollinger Band Support and created a Bollinger Band Snap. This could be used as an exit, since price had moved down almost 250 points from the open, resulting in a profit, and price is unlikely to stay trading below the lower Bollinger Band for long. If one exited based on the strong Bollinger Band Snap on February 27th, a re-entry can be taken on March 6th, with a confirmed close price below the T-Line at the 2973 price level and continuing down to about $2192. How would you know when this bearish trend would end? Resistance was marked by the T-Line and suppo

> This combined Bollinger Band and T-Line dynamic trend tracking is reliable and it can be used effectively in many ways. First, as shown at the beginning of the chart, it shows a long entry and provides profit opportunity as the index rises. Second, a crossover, with a confirmed second session close, is the exit point for leaving a current trend, taking profits, or for entering a new trend based on the newly revised price direction. Third, as shown in the February 24th trend, using a Bollinger Band Snap to signal a time to take profits and exit the position as price generally will retrace back

> Bollinger Bands contain three parts. First is a 20-period simple moving average, the middle band (purple line). Second is the upper band and third is the lower band (blue lines). Both of the upper and lower bands are two standard deviations away from the middle band. This sets up a powerful and visual summary of historical volatility. Thus, price is unlikely to trade above the upper band or below the lower band. When price does move outside of these ranges, it retreats back into range very quickly. So, Bollinger Bands are a great “probability matrix” to time and control both entry and exit.

> Rick Saddler coined the term “T-Line”. The T-Line (red line) is an 8-day exponential moving average of price that yields surprisingly reliable signals for changes in price direction. The general rule is that when price is above the T-Line, it remains bullish until it crosses below and closes for at least two sessions. This sets up a bearish reversal. When price is below the T-Line, the prevailing bearish trend continues until price crosses above and closes above for at least two consecutive sessions.

> In late February, price was trending lower with considerable strength and many gaps. The retracements occurring in the second week could have been viewed as reversals, except for one important signal: Close price remained below the T-Line from February 24th entry at 3226 all the way down to End-March when it traded at a low of 2192. Price did close above the T-Line toward the beginning of March, but immediately crossed back and closed below the T-Line the next day. Since price did not close above the T-Line resistance for two consecutive sessions, this bearish trend continued. This was further

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

- https://www.tradingview.com/chart/SPX/Y1X3vuyD-Bollinger-Band-and-T-Line-Timing/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
