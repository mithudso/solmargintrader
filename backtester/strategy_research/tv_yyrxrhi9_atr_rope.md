---
id: tv_yyrxrhi9_atr_rope
name: "ATR Rope"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of ATR Rope; not a tested trading strategy."
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
# ATR Rope

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> ATR Rope is inspired by DonovanWall's "Range Filter". It implements a similar concept of filtering out smaller market movements and adjusting only for larger moves. In addition, this indicator goes one step deeper by producing actionable zones to determine market state. (Trend vs. Consolidation)

> Since the indicator works based on an ATR range, the resulting ATR Channel does well to get reactions from price at its extremes. Naturally, when consolidating, price will remain within the channel, neither pushing the channel significantly up or down. Likewise, when trending, price will continue to push the channel in a single direction.

> With the goal of keeping it quick and simple, this indicator does not do any smoothing of data feeds, and is simply based on the deviation of price from the central rope. Adjusting the rope when price extends past the threshold created by +/- ATR from the rope.

> When reading up on the Range Filter indicator, it reminded me exactly of a Rope stabilization drawing tool in a program I use frequently. Rope stabilization essentially attaches a fixed length "rope" to your cursor and an anchor point (Brush). As you move your cursor, you are pulling the brush behind it. The cursor (of course) will not pull the brush until the rope is fully extended, this behavior filters out jittery movements and is used to produce smoother drawing curves.

> Consolidation Zones generate from "Flat" areas, and extend into subsequent trend areas. Consolidation is simply areas where price has crossed the Rope and remains inside the range. Over these periods, the upper and lower values are accumulated and averaged together to form the "Consolidation Zone" values. These zones are draw live, so values are averaged as the flat areas progress and don't repaint, so all values seen historically are as they would appear live.

> Author's Note: In each of these examples, I have outlined the start and end of each session. These examples come from 1 Min Future charts, and have specifically been framed with day trading in mind.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_atr_trailing`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/script/YYrxRhi9-ATR-Rope/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
