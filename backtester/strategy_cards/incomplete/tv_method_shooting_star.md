---
id: tv_method_shooting_star
name: "Shooting star and inverted hammer"
kind: exposure-strategy
status: spec-only
family: research-method
summary: "Specification of Shooting star and inverted hammer; not a tested trading strategy."
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
# Shooting star and inverted hammer

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

Require a small body near the low and a long upper shadow with a short lower shadow. Prior trend distinguishes a shooting star from an inverted hammer. Freeze body/shadow ratios and closed-bar confirmation.

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

- https://www.tradingview.com/script/5FQgMCiO-Adaptive-Candlestick-Pattern-Recognition-System/
- https://www.tradingview.com/chart/AAPL/H25E1j6f-How-to-instantly-find-candlestick-patterns-on-your-chart/
- https://www.tradingview.com/chart/AUDJPY/jn9xvp2B-AUD-JPY-Daily-Cross-Signals-Bearish-Momentum/
- https://www.tradingview.com/chart/BTCUSD/3eYlpg28-Candlestick-Charts-Part-3-Continuation/
- https://www.tradingview.com/chart/BTCUSD/vpMH5sfd-Bitcoin-Bulls-Drift-In-Sideways-After-Bullish-Engulfing/
- https://www.tradingview.com/chart/F/RzWKkWlz-Ford-seems-to-be-finding-a-bottom/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
