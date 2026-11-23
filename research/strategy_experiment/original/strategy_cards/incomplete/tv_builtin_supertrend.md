---
id: tv_builtin_supertrend
name: "SuperTrend"
kind: exposure-strategy
status: spec-only
family: trend
summary: "Specification of SuperTrend; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  length: {default: 10, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  factor: {default: 3, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# SuperTrend

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

candidateUpper=(H+L)/2+factor*ATR(length); candidateLower=(H+L)/2-factor*ATR(length). Ratchet active bands and flip on a closed-bar crossing. Freeze state initialization and ATR convention.

## Documented inputs and source details

TradingView catalog inputs: `length`=10; `factor`=3.

Catalog notes: (plots: `supertrend`, `up arrow`, `down arrow`; d.ts L26612).

These are documented UI inputs, not verified constructor defaults. Standard formulas
are reference definitions; the capture does not establish exact TradingView seed,
smoothing or rendering parity.

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

- docs/TRADINGVIEW-REFERENCE.md — built-in indicator catalog and standard equations.
- https://www.tradingview.com/charting-library-docs/latest/indicators/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.

## Official help clarification

https://www.tradingview.com/support/solutions/43000634738-supertrend/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/cwl88klshU8??si=aOHe3eYLx1auBt6W&wmode=opaque" frameborder="0" allowfullscreen="" class="fr-draggable"></iframe>
````

````text
Supertrend is a trend-following indicator based on Average True Range (ATR). The calculation of its single line combines trend detection and volatility. It can be used to detect changes in trend direction and to position stops.
````

````text
To calculate bands of the Supertrend, use the following formulas:
````
