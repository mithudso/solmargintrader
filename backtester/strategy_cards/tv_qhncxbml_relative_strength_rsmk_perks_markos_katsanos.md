---
id: tv_qhncxbml_relative_strength_rsmk_perks_markos_katsanos
name: "Relative Strength(RSMK) + Perks - Markos Katsanos"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Relative Strength(RSMK) + Perks - Markos Katsanos; not a tested trading strategy."
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
# Relative Strength(RSMK) + Perks - Markos Katsanos

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> If you are desperately looking for a novel RSI, this isn't that. This is another lesser known novel species of indicator. Hot off the press, in multiple stunning color schemes, I present my version of "Relative Strength (RSMK)" employing PSv4.0, originally formulated by Markos Katsanos for TASC - March 2020 Traders Tips. This indicator is used to compare performance of an asset to a market index of your choosing. I included the S&P 500 index along side the Dow Jones and the NASDAQ indices selectively by an input() in "Settings". You may comparatively analyze other global market indices by adap

> With this contribution to the Tradingview community, also included is MY twin algorithmic formulation of "Comparative Relative Strength" as a supplementary companion indicator. They are eerily similar, so I decided to include it. You may easily disable my algorithm within the indicator "Settings". I do hope you may find both of them useful. Configurations are displayed above in multiple scenarios that should be suitable for most traders.

> Unfortunately, there are so many Pine mastery techniques included, I don't have time to write about all of them. I will have to let you discover them for yourself, excluding the following Pine "Tricks and Tips" described next. Of notable mention with this release, I have "overwritten" the Pine built-in function ema(). You may overwrite other built-in functions too. If you weren't aware of this Pine capability, you now know! Just heed caution when doing so to ensure your replacement algorithms are 100% sound. My ema() will also accept a floating point number for the period having ultimate adjus

> The comments section below is solely just for commenting and other remarks, ideas, compliments, etc... regarding only this indicator, not others. When available time provides itself, I will consider your inquiries, thoughts, and concepts presented below in the comments section, should you have any questions or comments regarding this indicator. When my indicators achieve more prevalent use by TV members, I may implement more ideas when they present themselves as worthy additions. As always, "Like" it if you simply just like it with a proper thumbs up, and also return to my scripts list occasio

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `xs_momentum`.

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

- https://www.tradingview.com/script/qhNCXBmL-Relative-Strength-RSMK-Perks-Markos-Katsanos/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
