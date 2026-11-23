---
id: tv_43000732559_chart_pattern_inverted_cup_and_handle
name: "Chart Pattern Inverted Cup and Handle"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Chart Pattern Inverted Cup and Handle; not a tested trading strategy."
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
# Chart Pattern Inverted Cup and Handle

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> <iframe src="https://www.youtube.com/embed/MvUHkmOzmaw??si=ib5SfKHI6zCkvy0x&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>

> In the In Progress mode, the indicator searches not only for formed patterns, but also for patterns that are still being formed. The last point of such a pattern (point 4) may not be in the pivot point, in this case the handle line will be dotted. When forming the handle, the highest high values between points 3 and 4 and between point 4 and the end of the handle are taken into account. The high between points 3 and 4 should be lower than the high between point 4 and the end of the handle line. The breakout of the pattern is based on the close value of the symbol.

> Permissible Deviation - determines the maximum allowable price difference along the edges of the cup. It is calculated as a percentage of the height of the cup.

> Awaiting - the handle is not broken through, or it is broken through and at the same time the price has not gone above the threshold value (determined by the Handle Max Rollback input) and has not reached the target yet.

> Failed - the price did not reach the target and went above the threshold value, or the handle became longer than the cup.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_cup_handle`.

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

- https://www.tradingview.com/support/solutions/43000732559-chart-pattern-inverted-cup-and-handle/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
