---
id: tv_ppjps450_neglected_volume_by_dgt
name: "Neglected Volume by DGT"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Neglected Volume by DGT; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-financial-statements]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Neglected Volume by DGT

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Volume is one piece of information that is often neglected, however, learning to interpret volume brings many advantages and could be of tremendous help when it comes to analyzing the markets. In addition to technicians, fundamental investors also take notice of the numbers of shares traded for a given security.

> Within this study, Relative Volume, Volume Weighted Bars and Volume Moving Average are presented, where Relative Volume relates current trading volume to past trading volume over long period, Volume Weighted Bars presents price bars colored based on short period past trading volume average, and Volume Moving Average is average of volume over shot period

> Volume Weighted Bars, a study of Kıvanç Özbilgiç, aims to present if price movements are supported by Volume. Volume Weighted Bars are calculated based on shot period volume moving average which will reflect more recent changes in volume. Price actions with high volume will be displayed with darker colors, average volume values will remain as they are and low volume values will be indicated with lighter colors.

> Relative Volume is presented as color-coded bars similar to regular Volume indicator but uses four color codes instead two. Notable increases of volume are presented in green and red while average values with back and gray, hence adding ability to emphasis notable increases in the volume. It is kind of a like a radar for how "in-play" a security is. Users are allowed to change the threshold, default value is set to Fibonacci golden ration standard deviation away from its moving average.

> Volume Moving Average, Is short period volume moving average, aims to display visually the volume changes. Please not that Relative Volume bars are calculated based on standard deviation of long volume moving average.

> The script is for informational and educational purposes only. Use of the script does not constitute professional and/or financial advice. You alone have the sole responsibility of evaluating the script output and risks associated with the use of the script. In exchange for using the script, you agree not to hold dgtrd TradingView user liable for any possible claim for damages arising from any decision you make based on use of the script

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_oscillator_divergence`, `tv_method_support_resistance`.

## Data and availability

Required inputs: ohlcv, point-in-time-financial-statements.
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

- https://www.tradingview.com/script/PpjPs450-Neglected-Volume-by-DGT/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
