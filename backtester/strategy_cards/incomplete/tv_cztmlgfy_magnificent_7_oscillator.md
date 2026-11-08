---
id: tv_cztmlgfy_magnificent_7_oscillator
name: "Magnificent 7 Oscillator"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Magnificent 7 Oscillator; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Magnificent 7 Oscillator

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The Magnificent 7 Oscillator is a sophisticated momentum-based technical indicator designed to analyze the collective performance of the seven largest technology companies in the U.S. stock market (Apple, Microsoft, Alphabet, Amazon, NVIDIA, Tesla, and Meta). This indicator incorporates established momentum factor research and provides three distinct analytical modes: absolute momentum tracking, equal-weighted market comparison, and relative performance analysis. The tool integrates five different oscillator methodologies and includes advanced breadth analysis capabilities.

> The momentum calculation methodology follows the academic standard:

> The indicator employs robust data collection with error handling for missing or invalid security data. Each stock's momentum is calculated independently using the specified lookback period (default: 14 periods).

> - Entry/Exit Timing: Utilize threshold crossovers for position sizing decisions

> The indicator's foundation rests on seminal momentum research in financial markets. Jegadeesh and Titman (1993) demonstrated that stocks with strong price performance over 3-12 month periods tend to continue outperforming in subsequent periods¹. This momentum effect was later incorporated into formal factor models by Carhart (1997), who extended the Fama-French three-factor model to include a momentum factor (UMD - Up Minus Down)².

> Where P(t) is the current price and n is the lookback period.

> - Market Cap Weight: Reserved for future enhancement

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_risk_based_sizing`, `xs_momentum`.

## Data and availability

Required inputs: ohlcv, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/CztMLgfY-Magnificent-7-Oscillator/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
