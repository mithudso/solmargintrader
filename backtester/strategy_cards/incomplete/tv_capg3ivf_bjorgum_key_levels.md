---
id: tv_capg3ivf_bjorgum_key_levels
name: "Bjorgum Key Levels"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Bjorgum Key Levels; not a tested trading strategy."
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
# Bjorgum Key Levels

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Key Levels Aims to capture 3 of the most significant points in price action

> Back checks are pull backs in trend that find middle ground to the 2 areas already described. Both momentum and entry price are decent, but risk is defined as a key level has flipped offering entry with stops below demand, or above supply.

> Breakouts can bring significant rallies as the market swings one sided after key levels are breached. This entry type can bring large trending runs to follow. Momentum is on your side, but the trade off is a higher entry.

> Also known as a bull trap or a bear trap, false breaks can lead to swift and significant reversals and potential for a large and sudden move to the opposite side. When a key level breakout fails to hold, parties entering to capitalize on the "epic breakout" can get left holding the bag forcing them to exit at a loss, which can double the force of pressure. Traps can bring swift gains from good entry prices. However, price is still in a larger trend against you so momentum is weak, so price action is susceptible to roll over.

> Combining these 3 methods helps to diversify risk, understand trend development, and bring steady gains. This script helps to identify these points to traders with analysis of key levels, price structure, and trend direction, while providing visual signals and alerts for when they occur.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_liquidity_sweep`.

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

- https://www.tradingview.com/script/CapG3ivf-Bjorgum-Key-Levels/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
