---
id: tv_sg7vk6uh_iq_trend_beams_tradingiq
name: "IQ Trend Beams [TradingIQ]"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of IQ Trend Beams [TradingIQ]; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, classified-tick-or-lower-timeframe-history]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# IQ Trend Beams [TradingIQ]

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> IQ Trend Beams is a trend assistant that draws your trendlines the way a disciplined chartist would - and then holds them accountable. It maintains two channels, support and resistance, each always showing one working line. A line is born forming: it moves and re-shapes freely, polished every bar by a perceptual score toward the line a skilled trader would actually draw. When its geometry settles and it has earned enough tangency credit, it locks - and from that moment the ink is frozen forever; it never moves again. Locked ink extends until break evidence fires, then it is broken: restyled bu

> This is an honest visualization and modeling tool, not a signal service. It draws structure clearly and states its own confidence out loud; it is not a validated edge or a promise of profit. Read the limitations section - it is not window dressing.

> • Reach profile - a smooth filled contour fanning into the future margin, where each level's forward extent is its density times the trend's estimated remaining length. It answers, at a glance: if this trend keeps going, how far - and around which prices - does its own volume say it reaches?

> • Locked and broken lines do not repaint - once a line locks, its geometry is frozen. Forming lines move by design (they are the live sketch, and are dotted to say so), and each beam's forecast (band, profile, ghost levels) refreshes at the live edge as new volume arrives and attaches only to the current live element. These are live reads, on purpose; none of them rewrites confirmed history.

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

Required inputs: ohlcv, classified-tick-or-lower-timeframe-history.
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

- https://www.tradingview.com/script/SG7Vk6uH-IQ-Trend-Beams-TradingIQ/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
