---

id: tv_profile_6qwqyut8

name: "TASC 2025.07 Laguerre Filters"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Smooth market prices with a modified Laguerre filter and show a related normalized oscillator for trend and swing analysis."

registry_key: null

runner: null

evaluation: null

---

# TASC 2025.07 Laguerre Filters

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Smooth market prices with a modified Laguerre filter and show a related normalized oscillator for trend and swing analysis.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact coefficients, filter order, initialization, zero-RMS handling and operational signal/exit definitions are absent.

- Exact coefficients, filter order, initialization, zero-RMS handling and operational signal/exit definitions are absent.

## How it works

- Use a transversal Laguerre structure with UltimateSmoother replacing the initial EMA term. Subsequent all-pass stages supply delayed components; difference the first two terms and normalize by RMS to form the oscillator.

## Outputs and intended use

- Display the filter on price and oscillator in a separate pane. Suggested research signals include crossings with UltimateSmoother or between differently ordered Laguerre filters, plus oscillator swing/mean-reversion cues.

## Parameters and stated settings

- UltimateSmoother critical period defaults thirty, gamma defaults 0.5 within the positive zero-to-one range, and oscillator RMS length defaults one hundred bars. Lower gamma is described as faster and higher gamma as more trend-oriented.

## Failure modes and caveats

- Reduced-lag claims concern filter design, not measured trading performance. RMS normalization can become unstable in flat data, and crossover signals can whipsaw.

## Missing information and implementation boundary

- Exact coefficients, filter order, initialization, zero-RMS handling and operational signal/exit definitions are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
replacing the EMA term with his UltimateSmoother filter.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
difference between the first and second terms in the modified filter structure, scaled by the root mean square (RMS).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Its default value is 30.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The default value is 0.5.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The default value is 100 bars.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6qwqyut8_tasc_2025_07_laguerre_filters](../tv_6qwqyut8_tasc_2025_07_laguerre_filters.md)

## Source

https://www.tradingview.com/script/6QWQYUT8-TASC-2025-07-Laguerre-Filters/

Publication ID: 6QWQYUT8. Source SHA-256: f3a5abdaae5fc4c7de687a10705e85f299e64ae7c6f9ac980e30530ca69a8113. Raw-description SHA-256: ba02d01d2a06068be979ac01865f42c0d10e116af3139719a8abf5f37eaa8ca0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
