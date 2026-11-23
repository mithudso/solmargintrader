---
id: tv_szvbr1vq_kcgmut
name: "KCGmut"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of KCGmut; not a tested trading strategy."
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
# KCGmut

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> “KCGmut” stands for “Mutations Of Keltner Center Of Gravity Channel”.

> I tweeked the script of the KeltCOG (published) to calculate the columns and of REVE (also published) to calculate the volume spikes. Because the KeltCOG script had the default option to let the script chose lookback and adapt the width, I decided to not provide inputs to tweek lookback or channel width. Thus, if you use a KeltCOG in default setting, REVE and KCGmut together in the same chart, these will provide consistent complementary information about the candle. This layout has this combination:

> After adding the ‘KeltCOG Width’ label to the KeltCOG, I got the idea of creating a subpanel indicator to show the development of the width-percent in previous periods. After some more thinking, I decided that the development of the COG-width-percent should also be reported and somehow the indicator should report whether the close is over (momentum is up), in (momentum is sideways) or under (momentum is down) the COG ( This is the gray area in the channel).

> When nothing much happens, i.e. the channels keep the same width of shrink a bit, the columns get an unobtrusive color, black for the small COG patches and bluish gray for the channel columns pointing up or sideways, reddish gray when pointing down. If the COG increases (drama) the patches get colored lime (up), red (down) or orange (sideways, very seldom). If the channel increases, the columns get colored gold (up), maroon (down) or orange (sideways). Because the COG is derived from a Donchian channel, drama means a new high or low in the lookback period. Drama in the KeltCOG channel just mea

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

- https://www.tradingview.com/script/sZvBR1Vq-KCGmut/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
