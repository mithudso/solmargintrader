---
id: tv_ejmwjmdf_dynamic_gap_probability_tool
name: "Dynamic Gap Probability Tool"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Dynamic Gap Probability Tool; not a tested trading strategy."
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
# Dynamic Gap Probability Tool

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Dynamic Gap Probability Tool measures the percentage gap between price and a chosen moving average, then analyzes your chart history to estimate the likelihood of the next candle moving up or down. It dynamically adjusts its sample size to ensure statistical robustness while focusing on the exact deviation level.

> • Provides real “next-candle” probabilities based on historical occurrences rather than fixed thresholds or untested heuristics.

> 1. Calculate gap = (close – moving average) / moving average * 100.

> • Automatically extends the sample when exact matches are scarce, avoiding misleading signals on rare extreme moves.

> 4. If exact X% count is below the minimum occurrences threshold, include gaps at X+1%, X+2%, etc., until threshold is reached.

> • If price is 3% above the 200-period SMA and 120 occurrences ≥3% are found, with 84 green next candles (70%) and 36 red (30%), the script displays “3% | 120 | 70% green | 30% red.”

> • Risk managers gauge reliability by inspecting sample size before acting on any signal.

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

- https://www.tradingview.com/script/EJMwjmDF-Dynamic-Gap-Probability-Tool/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
