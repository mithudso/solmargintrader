---
id: tv_lcgcwwwi_bar_balance_lucf
name: "Bar Balance [LucF]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bar Balance [LucF]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Bar Balance [LucF]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> [I]Bar Balance extracts the number of up, down and neutral intrabars contained in each chart bar, revealing information on the strength of price movement. It can display stacked columns representing raw up/down/neutral intrabar counts, or an up/down balance line which can be calculated and visualized in many different ways.

> WARNING: This is an analysis tool that works on historical bars only. It does not show any realtime information, and thus cannot be used to issue alerts or for automated trading. When realtime bars elapse, the indicator will require a browser refresh, a change to its Inputs or to the chart's timeframe/symbol to recalculate and display information on those elapsed bars. Once a trader understands this, the indicator can be used advantageously to make discretionary trading decisions.

> • The "Up" section represents the count of intrabars where `close > open`, "Down" where `close < open` and "Neutral" where `close = open`.

> • While the size of the Up/Down columns always represents their respective importance on the bar, their coloring mode is independent. The default setup uses a standard coloring mode where the Up/Down columns over/under the zero line are always in the bull/bear color with a higher intensity for the winning side. Six other coloring modes allow you to pack more information in the columns. When choosing to color the top columns using a bull/bear gradient on Balance Averages, for example, you will end up with bull/bear colored tops. In order for the color of the bottom columns to continue to show t

> • In "Dual Solid Colors (All Bull/All Bear Only)" a dot only appears when all three balances are either bullish or bearish. The resulting pattern is identical to that of Marker 1.

> • Divergences are displayed as a small circle at the top of the scale. Four different types of divergence events can be detected. Divergences occur whenever the bull/bear bias of the method used diverges with the bar's price direction.

> Traders used to work with my Delta Volume Columns Pro will feel right at home in this indicator's Inputs. It has lots of options, allowing it to be used in many different ways. If you value the bar balance information this indicator mines, I hope you will find the time required to master the use of [I]Bar Balance well worth the investment.

> 3. [I]Balance Momentum: Starts by calculating, separately for both Up and Down counts, the difference between the same EMAs used in Balance Averages and an SMA of double the period used for the EMAs. These differences are then aggregated and finally, a bounded momentum of that aggregate is calculated using RSI.

> By the same token that an up bar does not guarantee that more up bars will follow, future price movements cannot be inferred from the mere count of up/down/neutral intrabars. Price movement during any chart bar for which, let's say, 12 intrabars are analyzed, could be due to only one of those intrabars. One can thus easily see how only relying on bar balance information could be very misleading. The rationale behind Bar Balance is that when the information mined for multiple chart bars is aggregated, it can provide insight into the history behind chart bars, and thus some bias as to the streng

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`.

## Data and availability

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/lcgCwWwI-Bar-Balance-LucF/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
