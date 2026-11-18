---
id: tv_t1v41bl5_session_edge_profiler_flux_charts
name: "Session Edge Profiler | Flux Charts"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Session Edge Profiler | Flux Charts; not a tested trading strategy."
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
# Session Edge Profiler | Flux Charts

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Session Edge Profiler is a statistical dashboard indicator that profiles up to five configurable trading sessions (Asia, London, NY AM, NY Lunch, NY PM by default) across the available completed trading days loaded on the chart. The indicator records each session's range, volume, directional outcome, and smart money structure (Fair Value Gaps, swing breaks, higher highs, lower lows) on every completed day, then surfaces the resulting statistics in a configurable on-chart dashboard with progress bars and best value markers.

> For every metric, the indicator filters history by the selected weekdays. Range-based metrics are normalized against the previous daily ATR for cross-volatility comparison, while volume, directional, extreme, and structure metrics are calculated directly from completed session records. The indicator also computes percentile rankings of the current session range against its historical distribution. Session boxes can be plotted for visual reference, and a live label tracks the active session's running range against its historical average and percentile rank in real time. The indicator is statist

> 🔹How is Session Tracking detected and calculated?

> For each completed session, Bull is true when the session's close (the chart close at the bar where the session ended) exceeds its open. Continuation is true when the previous occurrence of the same session was bullish in the same direction (both bullish or both bearish). The very first occurrence in history has no previous reference and is excluded from the continuation calculation. The dashboard divides the bullish session count by the total session count for Bull %, and the matched continuation count by the continuation eligible count for Continuation %.

> Markets do not move uniformly across the day. Each trading session carries different participant types, different volume profiles, and different structural behaviors. The Asia session tends to be range bound and accumulative. The London session frequently sweeps overnight liquidity. NY AM often produces the largest expansions of the day. NY Lunch is typically the lowest volume window. NY PM frequently reverses or extends NY AM moves into the close.

> These tendencies are widely cited but rarely measured per instrument. The Session Edge Profiler quantifies them. By recording per session statistics across the historical window available on the chart, and by filtering by selected weekdays, the indicator builds an empirical profile of how each session has actually behaved on a specific symbol rather than relying on generalized assumptions. The result is a session level statistical profile that can be compared against the current session in real time, identifying when a given session is behaving unusually large, unusually quiet, or consistent w

> For each completed session, the raw range (session high minus session low) is divided by the daily ATR value of the previous completed day. The daily ATR uses a configurable length (default 14) and is always read from the previous daily bar, which means the value is fixed for the entire current trading day and never repaints. The session's normalized range is stored alongside its weekday in the history. When the dashboard renders, the indicator averages all normalized ranges from sessions whose weekday passes the filter, then multiplies by 100 to produce the displayed percentage.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fair_value_gap`, `tv_method_liquidity_sweep`.

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

- https://www.tradingview.com/script/T1V41Bl5-Session-Edge-Profiler-Flux-Charts/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
