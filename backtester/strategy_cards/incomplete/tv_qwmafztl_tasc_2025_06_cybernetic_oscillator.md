---
id: tv_qwmafztl_tasc_2025_06_cybernetic_oscillator
name: "TASC 2025.06 Cybernetic Oscillator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of TASC 2025.06 Cybernetic Oscillator; not a tested trading strategy."
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
# TASC 2025.06 Cybernetic Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> This script implements the Cybernetic Oscillator introduced by John F. Ehlers in his article "The Cybernetic Oscillator For More Flexibility, Making A Better Oscillator" from the June 2025 edition of the TASC Traders' Tips. It cascades two-pole highpass and lowpass filters, then scales the result by its root mean square (RMS) to create a flexible normalized oscillator that responds to a customizable frequency range for different trading styles.

> Oscillators are indicators widely used by technical traders. These indicators swing above and below a center value, emphasizing cyclic movements within a frequency range. In his article, Ehlers explains that all oscillators share a common characteristic: their calculations involve computing differences. The reliance on differences is what causes these indicators to oscillate about a central point.

> The difference between two data points in a series acts as a highpass filter — it allows high frequencies (short wavelengths) to pass through while significantly attenuating low frequencies (long wavelengths). Ehlers demonstrates that a simple difference calculation attenuates lower-frequency cycles at a rate of 6 dB per octave. However, the difference also significantly amplifies cycles near the shortest observable wavelength, making the result appear noisier than the original series. To mitigate the effects of noise in a differenced series, oscillators typically smooth the series with a lowp

> Ehlers highlights an underlying issue with smoothing differenced data to create oscillators. He postulates that market data statistically follows a pink spectrum, where the amplitudes of cyclic components in the data are approximately directly proportional to the underlying periods. Specifically, he suggests that cyclic amplitude increases by 6 dB per octave of wavelength.

> Because some conventional oscillators, such as RSI, use differencing calculations that attenuate cycles by only 6 dB per octave, and market cycles increase in amplitude by 6 dB per octave, such calculations do not have a tangible net effect on larger wavelengths in the analyzed data. The influence of larger wavelengths can be especially problematic when using these oscillators for mean reversion or swing signals. For instance, an expected reversion to the mean might be erroneous because oscillator's mean might significantly deviate from its center over time.

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

- https://www.tradingview.com/script/QwMaFZTL-TASC-2025-06-Cybernetic-Oscillator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
