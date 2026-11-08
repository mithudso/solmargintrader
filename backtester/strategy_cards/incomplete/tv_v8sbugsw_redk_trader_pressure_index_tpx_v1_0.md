---
id: tv_v8sbugsw_redk_trader_pressure_index_tpx_v1_0
name: "RedK Trader Pressure Index (TPX v1.0) "
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of RedK Trader Pressure Index (TPX v1.0) ; not a tested trading strategy."
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
# RedK Trader Pressure Index (TPX v1.0)

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific indicator named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> The RedK Trader Pressure Index (REDK_TPX) analyzes the changes in price bars to give the trader a clear visual insight that represents the ongoing fight between the bulls (buyers) and bears (sellers) in the market - to determine who is in control of the price action, which in turn can be helpful in a trader’s decision about how the price action may be unfolding, what type of trade and positions to take (or to close) and when is the ideal time to action.

> The TPX uses a simple logic and that’s one of the things I like about it – there is no complex calculation or magic stuff - and the core idea makes sense to me, as well as being one of the ways I needed to analyze my price charts.

> So, we will use the change in high and low price, between 2 consecutive price bars, as a proxy for the bull and bear “pressures” – a (weighted) moving average of these “pressure” values are then calculated along with the “Net Pressure” – the final results are plotted.

> when the bull or bear pressure is above that threshold, they will dominate and control the price move – this level can be found around the 25 or 30. I have included the ability to plot and adjust that control level in the TPX’s settings – and I also show some examples in the chart above (weekly chart for MSFT)

> TPX is also valuable in showing when there’s “lack of interest” from the buyers or the sellers (or both) – which is great in exploring chub or no-trade zones - so basically when to avoid trading.

> As in similar price-action based indicators, there’s a certain threshold or “control level”, above which, the pressure becomes “dominant”

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

- https://www.tradingview.com/script/v8sBugsW-RedK-Trader-Pressure-Index-TPX-v1-0/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
