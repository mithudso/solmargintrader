---

id: tv_profile_mykmv8br

name: "Linear Regression Oscillator [ChartPrime]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Turn a close-price regression calculation into an oscillator for observing trend shifts and possible mean-reversion extremes."

registry_key: null

runner: null

evaluation: null

---

# Linear Regression Oscillator [ChartPrime]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Turn a close-price regression calculation into an oscillator for observing trend shifts and possible mean-reversion extremes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Regression-to-oscillator transformation, event tests, invalidation selection, confirmation timing and full risk controls are missing.

- Regression-to-oscillator transformation, event tests, invalidation selection, confirmation timing and full risk controls are missing.

## How it works

- Regress closes over a lookback, derive the oscillator and compare it with upper/lower thresholds. Track recent price extremes as invalidation levels and optionally color candles by oscillator sign.

## Outputs and intended use

- Positive/negative values can color bars cyan/blue. Markers identify proposed trend or reversion events, while invalidation lines are suggested as discretionary stop references.

## Parameters and stated settings

- Length defaults twenty, thresholds +1.5/-1.5 and candle coloring defaults false. The source does not specify the invalidation lookback or normalization.

## Failure modes and caveats

- Threshold extremes can persist in trends. The author's suggestion that wider thresholds improve reliability is not measured here, and a plotted invalidation line does not ensure an executable stop fill.

## Missing information and implementation boundary

- Regression-to-oscillator transformation, event tests, invalidation selection, confirmation timing and full risk controls are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed feature class; this does not establish implementation parity or complete data coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default: 20
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Default: 1.5 and -1.5 respectively
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Default: false
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Tracks the highest and lowest prices over a recent period to set levels where the current trend signal would be considered invalidated.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mykmv8br_linear_regression_oscillator_chartprime](../tv_mykmv8br_linear_regression_oscillator_chartprime.md)

## Source

https://www.tradingview.com/script/MyKmv8br-Linear-Regression-Oscillator-ChartPrime/

Publication ID: MyKmv8br. Source SHA-256: a65e5cda297fc825acb876046f2a8d3070c2f38d93c7028a5c9fc53e6f8b6356. Raw-description SHA-256: eb6cb0b45fdc19f6c10aa4401a642119a160b006a10af8d4aa96ddfc1835f39a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
