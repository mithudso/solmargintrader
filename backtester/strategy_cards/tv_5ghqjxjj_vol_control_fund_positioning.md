---
id: tv_5ghqjxjj_vol_control_fund_positioning
name: "Vol-Control Fund Positioning"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of Vol-Control Fund Positioning; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv, point-in-time-macro-and-derivatives-history, synchronized-point-in-time-universe]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Vol-Control Fund Positioning

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The investors who sell because nothing happened

> A volatility control portfolio sets itself a target, typically a level of annual volatility such as ten per cent, and then sizes its equity position so that the portfolio as a whole moves roughly that much. The arithmetic is disarmingly simple. If the market has recently been moving at an annualised twenty per cent, a ten per cent target means holding half the capital in equities and the rest in cash, and if the market calms down to eight per cent, the same target calls for 125 per cent, which is achieved with futures or borrowed money, usually up to a ceiling of 150 per cent. Exposure is ther

> exposure = min(max_leverage, target_vol / realised_vol)

> Mid Range Entry fires when it returns to the middle.

> A plain average of squared returns over one month, since S&P permits equally weighted estimates as an alternative to exponential weighting (Cheng et al., 2021), with a window of my choosing, as S&P does not publish one.

> The same over three months, again a window of my choosing.

> Such rules are not a fringe product. S&P Dow Jones Indices publishes a whole family of risk control indices built on exactly this formula, and its own research describes how pension plans with defined benefits and insurers selling variable annuities use them to obtain a smoother path of returns that fits their liabilities better (Cheng et al., 2021). There is academic support for the idea as well. Moreira and Muir (2017) showed that portfolios which take less risk when volatility is high earned higher returns relative to their risk across a range of equity factors, and Harvey et al. (2018), te

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

## Data and availability

Required inputs: ohlcv, point-in-time-macro-and-derivatives-history, synchronized-point-in-time-universe.
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

- https://www.tradingview.com/script/5gHQJXjj-Vol-Control-Fund-Positioning/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
