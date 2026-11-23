---

id: tv_profile_o8trzczt

name: "Intrabar Efficiency Ratio"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Gauge the directional efficiency of each chart bar relative to movement observed in its lower-timeframe components. Unlike unsigned Kaufman efficiency, this variant retains direction and smooths the result into a momentum-style display."

registry_key: null

runner: null

evaluation: null

---

# Intrabar Efficiency Ratio

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Gauge the directional efficiency of each chart bar relative to movement observed in its lower-timeframe components. Unlike unsigned Kaufman efficiency, this variant retains direction and smooths the result into a momentum-style display.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Chart/intrabar change boundary conventions, zero-denominator handling, precise weighting formula and default lengths are not given.

- Chart/intrabar change boundary conventions, zero-denominator handling, precise weighting formula and default lengths are not given.

## How it works

- Divide signed chart-bar change by the sum of absolute intrabar changes, then apply moving-average smoothing. Optional percent-rank weighting reduces contributions from relatively small chart-price changes.
- The line view shows the middle-length average. Synthetic candles use long/short averages as open/close and extrema across those plus raw efficiency as high/low. Circles show three averages colored by their rolling ranks.
- Lower-timeframe selection trades intrabar precision against historical coverage, using stepped, fixed-minute or approximate target-count modes. An information box reports actual coverage.

## Outputs and intended use

- Line, candles or circle displays expose directional efficiency; the author also suggests absolute efficiency as an adaptive-average input, without supplying that downstream system.
- Coverage statistics help distinguish a recent high-resolution sample from a longer coarser history.

## Parameters and stated settings

- Seven average families; ALMA offset 0.85 and sigma 6. Circle ranks use 100 bars with thresholds 10%, 50% and 90%.
- Target intrabar options 12,24,50,100,250; relative-change weighting period and MA lengths are configurable.

## Failure modes and caveats

- Intrabar bars still omit within-bar tick paths. The historical platform intrabar limit in the prose should not be assumed current.
- Different session coverage and selected precision can change apparent efficiency; absent/flat intrabars require defined handling.

## Missing information and implementation boundary

- Chart/intrabar change boundary conventions, zero-denominator handling, precise weighting formula and default lengths are not given.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical OHLCV at the chosen chart and lower/higher timeframes supplies the disclosed raw data class, subject to coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
IER compares single bar changes for the current chart's timeframe to the sum of absolute intrabar changes
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
offset` and `sigma` set to 0.85 and 6 respectively.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
over the previous 100 bars.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
below 10%, between 10% and 50%, between 50% and 90%, and above 90%.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The available choices are 12, 24, 50, 100, and 250.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_o8trzczt_intrabar_efficiency_ratio](../tv_o8trzczt_intrabar_efficiency_ratio.md)

## Source

https://www.tradingview.com/script/o8tRZCzT-Intrabar-Efficiency-Ratio/

Publication ID: o8tRZCzT. Source SHA-256: ea926b9ed753bd4aabc3079d5670824820bfa91dbad03630e08abf1458869bfb. Raw-description SHA-256: 00deab211d34574985f96da17c0936934336c12ce4ec7b47977f24f2ea696859.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
