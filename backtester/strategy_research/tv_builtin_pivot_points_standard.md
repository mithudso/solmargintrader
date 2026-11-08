---
id: tv_builtin_pivot_points_standard
name: "Pivot Points Standard"
kind: exposure-strategy
status: spec-only
family: other
summary: "Specification of Pivot Points Standard; not a tested trading strategy."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  type: {default: "Traditional", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  number_of_pivots_back: {default: 15, type: "int", desc: "Documented TradingView input; not an optimized strategy setting"}
  pivots_timeframe: {default: "Auto", type: "str", desc: "Documented TradingView input; not an optimized strategy setting"}
  show_historical_pivots: {default: true, type: "bool", desc: "Documented TradingView input; not an optimized strategy setting"}
presets: {}
---
# Pivot Points Standard

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

For prior completed period H,L,C: P=(H+L+C)/3; R1=2*P-L; S1=2*P-H; R2=P+H-L; S2=P-H+L. Other type selections require their own formulas; do not silently use Traditional.

## Documented inputs and source details

TradingView catalog inputs: `type`=Traditional [Traditional, Fibonacci, Woodie, Classic, DeMark, Camarilla, Floor]; `number of pivots back`=15; `pivots timeframe`=Auto [Auto, Daily, Weekly, Monthly, Yearly]; `show historical pivots`=true.

Catalog notes: No plots keys in overrides; type options enumerated. (d.ts L25644).

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

https://www.tradingview.com/support/solutions/43000521824-pivot-points-standard/

These passages retain the official description and its conventions. Where they
differ from the standard reference formula above, establish the exact variant
before implementing or claiming numerical parity.

````text
<iframe src="https://www.youtube.com/embed/pnITIxt9ZTQ??si=x4VHyvSyn9NZFuAp&wmode=opaque" frameborder="0" allowfullscreen=""></iframe>
````

````text
Specifies the type of pivot point calculation. Each pivot point type uses a different calculation logic (described in the Calculation section below) and draws its own number of levels.
````

````text
The timeframe used for the pivots calculation. All available timeframes are daily or higher. For example, if "Weekly" is chosen, the indicator uses the current week's open and the previous week's open, high, low, and close (OHLC) to calculate the pivot point levels, and as a result, the levels change once a week.
````
