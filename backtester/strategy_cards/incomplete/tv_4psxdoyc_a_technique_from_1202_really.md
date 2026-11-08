---
id: tv_4psxdoyc_a_technique_from_1202_really
name: "A technique from 1202 - Really? "
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of A technique from 1202 - Really? ; not a tested trading strategy."
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
# A technique from 1202 - Really?

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific method named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> Fibonacci (1170 – c. 1240–50), also known as Leonardo Bonacci, Leonardo of Pisa, or Leonardo Bigollo Pisano was an Italian mathematician from the Republic of Pisa, considered to be "the most talented Western mathematician of the Middle Ages".

> Fibonacci popularized the Hindu–Arabic numeral system in the Western world primarily through his composition in 1202 of Liber Abaci (Book of Calculation). He also introduced Europe to the sequence of Fibonacci numbers, which he used as an example in Liber Abaci.

> With this method you will notice in your back-testing those areas of interest will often be at the 61.8% of the A to B move. This means if A + B = 100, then the target would be around 161-2.

> This idea does not constitute as financial advice. It is for educational purposes only, our principle trader has over 20 years’ experience in stocks, ETF’s, and Forex. Hence each trade setup might have different hold times, entry or exit conditions, and will vary from the post/idea shared here. You can use the information from this post to make your own trading plan for the instrument discussed. Trading carries a risk; a high percentage of retail traders lose money. Please keep this in mind when entering any trade. Stay safe.

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_elliott_wave`, `tv_method_fib_extensions`, `tv_method_support_resistance`.

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

- https://www.tradingview.com/chart/XAUUSD/4PsxDOYc-A-technique-from-1202-Really/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
