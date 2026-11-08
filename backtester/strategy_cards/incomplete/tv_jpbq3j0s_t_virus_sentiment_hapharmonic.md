---
id: tv_jpbq3j0s_t_virus_sentiment_hapharmonic
name: "T-Virus Sentiment [hapharmonic]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of T-Virus Sentiment [hapharmonic]; not a tested trading strategy."
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
# T-Virus Sentiment [hapharmonic]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> 🧬 T-Virus Sentiment: Visualize the Market's DNA

> The primary output of the indicator is the "Active %" gauge you see on the right side of the vial. This percentage represents the overall sentiment score, calculated as an average from 7 different technical analysis tools. Each tool is analyzed on every bar and assigned a score from 1 (strong bearish pressure) to 5 (strong bullish potential).

> The bubbles visualize the battle between buyers and sellers. There are two modes to control how this is calculated:

> This default mode is best for getting a broad, contextual understanding of the current session. It dynamically analyzes the volume of every single candlestick currently visible on the screen to calculate the buy/sell pressure ratio. It answers the question: "Over the entire period I'm looking at, who is in control?" As you zoom in or out, the calculation adapts.

> Simply hover the mouse over any indicator label (like EMA, OBV, etc.) to get a detailed tooltip. It will explain the specific data points and thresholds that signal met to be placed in its current zone. This helps build trust in the signals and allows users to fine-tune the indicator settings to better match their own trading style.

> Red & Angry: A warning sign. This appears if either the sentiment is weak, or a bullish sentiment is not being confirmed by buying volume. The latter could indicate a potential "bull trap" or an exhaustive move.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/jpbq3J0S-T-Virus-Sentiment-hapharmonic/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
