---
id: tv_nlygzrmb_short_volume_stamper
name: "Short Volume Stamper"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Short Volume Stamper; not a tested trading strategy."
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
# Short Volume Stamper

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> BE SURE TO RUN THE SCRIPT WITH BAR REPLAY TO SEE WHAT IT DOES! I hope you like it!

> This script calculates the total short volume, total volume, and the short volume / total volume ratio since the 2-year high price. In addition, the approximate dollar value of all short volume since the 2-year high, and the approximate dollar value of all non-short sell volume since the 2-year high is calculated using VWAP. A red line (short interest ratio >= 20%) connects the 2-year high to current session’s high price; a green line (short interest ratio < 20%) connects the 2-year high to the current session’s high.

> The script also “stamps” sessions in which a NEW 1-year high in SHORT volume is achieved, and when a PIVOT POINT high is achieved (highest high over 51 sessions). When a new high in short volume is achieved the script aggregates the total volume and short volume for the 5 sessions prior to the new high, the session of the new high, and the 4 sessions after the new high (10 sessions). Additional volume calculations are performed for the 10 session period!

> When a pivot point high is achieved the script aggregates the total volume and short volume for the 3 sessions prior to the pivot high, the session of the pivot high, and the 2 sessions after the new high (6 sessions). Additional volume calculations are performed for the 6 session period!

> Red labels, red boxes, and red lines indicate a short volume ratio greater than or equal to 20% over the corresponding period!

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

- https://www.tradingview.com/script/nLYgzrMB-Short-Volume-Stamper/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
