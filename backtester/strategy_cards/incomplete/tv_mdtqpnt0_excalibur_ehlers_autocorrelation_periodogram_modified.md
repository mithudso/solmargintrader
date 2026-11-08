---
id: tv_mdtqpnt0_excalibur_ehlers_autocorrelation_periodogram_modified
name: "[Excalibur] Ehlers AutoCorrelation Periodogram Modified"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of [Excalibur] Ehlers AutoCorrelation Periodogram Modified; not a tested trading strategy."
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
# [Excalibur] Ehlers AutoCorrelation Periodogram Modified

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Keep your coins folks, I don't need them, don't want them. If you wish be generous, I do hope that charitable peoples worldwide with surplus food stocks may consider stocking local food banks before stuffing monetary bank vaults, for the crusade of remedying the needs of less than fortunate children, parents, elderly, homeless veterans, and everyone else who deserves nutritional sustenance for the soul.

> This is my enhanced and heavily modified version of autocorrelation periodogram (ACP) for Pine Script v5.0. It was originally devised by the mathemagician John Ehlers for detecting dominant cycles (frequencies) in an asset's price action. I have been sitting on code similar to this for a long time, but I decided to unleash the advanced code with my [Excalibur] fashion. Originally Ehlers released this with multiple versions, one in a 2016 TASC article and the other in his last published 2013 book "Cycle Analytics for Traders", chapter 8. He wasn't joking about "concepts of advanced technical tr

> What you see is a new species of autocorrelation periodogram combining Ehlers' innovation with my fascinations of what ACP could be in a Pine package. One other intention of this script's code is to pay homage to Ehlers' lifelong works. Like Kondratiev, Ehlers is also a hardcore cycle enthusiast. I intend to carry on the fire Ehlers envisioned and I believe that is literally displayed here as a pleasant "fiery" example endowed with Pine. With that said, I tried to make the code as computationally efficient as possible, without going into dozens of more crazy lines of code to speed things up ev

> The periodogram renders the power spectrum of a signal, with the y-axis representing the periodicity (frequencies/wavelengths) and the x-axis representing time. The y-axis is divided into periods, with each elevation representing a period. In this periodogram, the y-axis ranges from 6 at the very bottom to 49 at the top, with intermediate values in between, all indicating the power of the corresponding frequency component by color. The higher the position occurs on the y-axis, the longer the period or lower the frequency. The x-axis of the periodogram represents time and is divided into equal

> Analogous to the realm of economics, aperiodic cycles/frequencies, both enduring and ephemeral, do exist in all facets of life, every second of every day. To name a few that any blind man can naturally see are: heartbeat (cardiac cycles), respiration rates, circadian rhythms of sleep, powerful magnetic solar cycles, seasonal cycles, lunar cycles, weather patterns, vegetative growth cycles, and ocean waves. Do not pretend for one second that these basic aforementioned examples do not affect business cycle fluctuations in minuscule and monumental ways hour to hour, day to day, season to season,

> Firstly, this is NOT technically speaking an indicator like most others. I would describe it as an advanced cycle period detector to obtain market data spectral estimates with low latency and moderate frequency resolution. Developers can take advantage of this detector by creating scripts that utilize a "Dominant Cycle Source" input to adaptively govern algorithms. Be forewarned, I would only recommend this for advanced developers, not novice code dabbling. Although, there is some Pine wizardry introduced here for novice Pine enthusiasts to witness and learn from. AI did describe the code into

> I am now confident Pine should have adequate overhead left over to attach various indicators to the dominant cycle via input.source(). TV, I apologize in advance if in the future a server cluster combusts into a raging inferno... Coders, be fully prepared to build entire algorithms from pure raw code, because not all of the built-in Pine functions fully support dynamic periods (e.g. length=ANYTHING). Many of them do, as this was requested and granted a while ago, but some functions are just inherently finicky due to implementation combinations and MUST be emulated via raw code. I would imagine

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_fourier_cycle`.

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

- https://www.tradingview.com/script/MdtqpNT0-Excalibur-Ehlers-AutoCorrelation-Periodogram-Modified/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
