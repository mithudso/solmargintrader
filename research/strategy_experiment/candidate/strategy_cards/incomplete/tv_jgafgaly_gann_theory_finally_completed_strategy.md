---
id: tv_jgafgaly_gann_theory_finally_completed_strategy
name: "GANN Theory Finally Completed Strategy"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of GANN Theory Finally Completed Strategy; not a tested trading strategy."
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
# GANN Theory Finally Completed Strategy

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> I took a couple of months off to read a book i found on Amazon on Andrew Gann the inventor of GANN theory. After finishing his article i theorized that it could be transformed in these modern times. This will a Membership to perform, Alerts mean allot to people that want to automate the thought process behind this. Please note that i am not a paid person posting this, i been trading for 16 years ever since i graduated from High School, I went to college to understand Pattern Recognition. Believe it or not there is a pattern to every aspect of our Lives.

> To plot the GANN BOX (not the GANN fix Box or the GANN angles) You are taking the Gann Box Placing it on the Poor Mans Volume Profile DAILY chart. For an Uptrend you go UP 2 and right 2, you'll understand when you plot it. For Down Trend down 2 right 2. Sideways (rangebound) oddly special one. Up 1 Right 2 Down 1 Right 2. When your plotting on the charts LOCK the Gann on the chart. I use Daily Right 2 because i set it at the beginning of the MONTH and its good for until the NEXT month. you set alerts on the GANN FIB LINES. (ENTRYS) BASED... If you are having issues with plotting this LET ME KN

> I take all of my trades on the 15min timeframe with an Anchor on the Daily Chart. Anchor meaning MTF MTF MTF MTF all of them are set to the daily. I want to make thoughtful readings based on the Daily Overall proceedings of the market direction.

> Stop loss is a very touchie subject that everyone should think about doing... Personally i use 4 different methods Count 5 bars back, last Swing point, or Halfway between the two fibs of entry. if i am feeling lucky just on the other side of the Fib Entry point. * the Lucky part of this one is if it goes bad you have a very LOW LOW risk of loosing allot of hard earned capital. Generally I will use the 5 bars back method.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_gann`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/chart/AMGN/JgaFgaLY-GANN-Theory-Finally-Completed-Strategy/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
