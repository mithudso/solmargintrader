---
id: tv_method_volume_spread_analysis
name: "Volume spread analysis"
kind: exposure-strategy
status: spec-only
family: research-method
summary: "Specification of Volume spread analysis; not a tested trading strategy."
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
# Volume spread analysis

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Compare volume with candle spread and close location in a declared trend context. Freeze thresholds for high effort/low result, test/stopping volume and confirmation. Do not infer aggressor flow or hidden orders from candle volume.

## Documented inputs and source details

This is a conventional reference specification of the named mechanism. Source
articles may use different thresholds or subjective annotations. Their names identify
the concept; they do not establish a unique source algorithm.

No numeric trading defaults are invented. Freeze any missing choices before testing.

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

- https://www.tradingview.com/script/9BKOIhdl-Numbers-Renko/
- https://www.tradingview.com/script/9MpC4ifP-Volume-Spread-Analysis-IQ-TradingIQ/
- https://www.tradingview.com/script/I5qJDPxT-RedK-EVEREX-Effort-Versus-Results-Explorer/
- https://www.tradingview.com/chart/BTCUSD/GV54T8ZJ-What-is-the-Wyckoff-Method/
- https://www.tradingview.com/chart/ES1!/taFAbnWh-S-P-500-review-Turning-losses-to-profit-by-detecting-changes/
- https://www.tradingview.com/script/WBQdFanB-MBoxAlgos/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
