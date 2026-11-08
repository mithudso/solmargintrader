---

id: tv_profile_cluzc70g

name: "WaveTrend 3D"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "WaveTrend 3D redesigns WaveTrend around a bounded signal transform and digital filtering, then supplies several response speeds and optional mirrored waves. It seeks to reduce unbounded extremes and offer cycle/trend-reversal context. The machine-learning comparisons in the prose describe analogies and optional kernel estimation, not a disclosed trained forecasting model or proof of reduced whipsaws."

registry_key: null

runner: null

evaluation: null

---

# WaveTrend 3D

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

WaveTrend 3D redesigns WaveTrend around a bounded signal transform and digital filtering, then supplies several response speeds and optional mirrored waves. It seeks to reduce unbounded extremes and offer cycle/trend-reversal context. The machine-learning comparisons in the prose describe analogies and optional kernel estimation, not a disclosed trained forecasting model or proof of reduced whipsaws.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** RMS window, Butterworth coefficients, kernel/bandwidth, COG definition, divergence logic, signal rules and defaults are not fully documented.

- RMS window, Butterworth coefficients, kernel/bandwidth, COG definition, divergence logic, signal rules and defaults are not fully documented.

## How it works

- Take the input’s first difference, normalize by quadratic mean, pass through tanh and apply a dual-pole Butterworth-style filter.
- Offer fast/normal/slow scales, optional source EMA or center-of-gravity transformation and kernel-regression trend confirmation.

## Outputs and intended use

- Inspect bounded waveforms, optional mirrored visualization, kernels and divergence-related triggers for discretionary pattern/cycle analysis.

## Parameters and stated settings

- Core transform targets -1 to 1. Inputs include length/smoothing scales, source transforms, mirror, offset, divergence threshold and trigger-wave size; numeric computational defaults are not supplied.

## Failure modes and caveats

- Analytical: bounded transformation compresses extremes and filter/kernels can lag; multiple scale factors are proxies and should not be assumed actual independent timeframes.

## Missing information and implementation boundary

- RMS window, Butterworth coefficients, kernel/bandwidth, COG definition, divergence logic, signal rules and defaults are not fully documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
first-order derivative of our input series and normalizing it using the quadratic mean
```

### E2: parameters, readiness

```text
desired range of -1 to 1
```

### E3: mechanism, readiness

```text
dual-pole filter such as the Butterworth Filter
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cluzc70g_wavetrend_3d](../tv_cluzc70g_wavetrend_3d.md)
- [tv_method_neural_prediction](../tv_method_neural_prediction.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)

## Source

https://www.tradingview.com/script/clUzC70G-WaveTrend-3D/

Publication ID: clUzC70G. Source SHA-256: e884a7822b53f03c437d03f4026beac7cf4fef5bd36eb2d244ee8af816f37037. Raw-description SHA-256: eafe0c635cbd659c62f520a7682613b39c609f7f8b82a42a32229534b9c4246c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
