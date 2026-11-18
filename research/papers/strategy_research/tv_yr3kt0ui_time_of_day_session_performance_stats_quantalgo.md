---
id: tv_yr3kt0ui_time_of_day_session_performance_stats_quantalgo
name: "Time-of-Day/Session Performance Stats [QuantAlgo]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Time-of-Day/Session Performance Stats [QuantAlgo]; not a tested trading strategy."
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
# Time-of-Day/Session Performance Stats [QuantAlgo]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Time-of-Day/Session Performance Stats is a comprehensive time-based analysis tool built for traders who want clear, ranked insight into when markets actually move. It measures average range, volume, bullish bias, and drift across every hour of the day and the four major sessions, then surfaces the strongest and weakest windows so you can focus activity where the data supports it. Whether you trade crypto around the clock or equity and forex sessions on a weekday schedule, the indicator turns raw historical bars into practical rankings, session comparisons, and non-repainting chart overlays

> Six presets (Classic, Aqua, Cosmic, Cyber, Neon, Custom) apply a continuous gradient from the bullish color at rank 1 to the bearish color at the last rank across every board, panel, and overlay. Custom mode exposes individual bullish and bearish color pickers; text contrast is calculated automatically so any chosen colors remain readable.

> Markets are not uniform across the 24-hour cycle. Liquidity, volatility, and participation concentrate in specific hours and sessions. Sydney is typically the thinnest of the four major centers, Tokyo drives Asian activity, London often produces the widest ranges of the day, and the London-New York overlap is usually the busiest window. By averaging range, volume, the share of up closes, and net drift for each hour and each session over a configurable lookback, this tool converts those recurring patterns into ranked statistics instead of leaving you to rely on memory or anecdotal observation.

> The indicator walks a configurable window of past bars (limited by lookback days and a hard max-bar ceiling) in the timezone you select. Every usable bar is assigned to its hour of day and to any sessions it falls inside. Range can be measured in percent of close or in raw price units. Volume, directional closes, and drift are accumulated in parallel. Hours that do not meet a minimum bar-count threshold are dropped from every ranking so tiny samples cannot distort the boards.

> Chart overlays read a trailing window of the same length rather than the final ranking, so background shading and bar coloring never repaint. The Focus Hours panel converts the Aggregated ranking into three practical allocation plans plus the single quietest hour to avoid.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_seasonality`.

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

- https://www.tradingview.com/script/Yr3kT0uI-Time-of-Day-Session-Performance-Stats-QuantAlgo/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
