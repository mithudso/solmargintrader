---

id: tv_profile_oqttrc35

name: "TASC 2025.02 Autocorrelation Indicator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Map lag-by-lag correlation in a smoothed price series to inspect evolving cycle and trend structure."

registry_key: null

runner: null

evaluation: null

---

# TASC 2025.02 Autocorrelation Indicator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Map lag-by-lag correlation in a smoothed price series to inspect evolving cycle and trend structure.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The source describes the display and ACF concept but omits the filter and lag/estimator contract needed for exact reproduction.

- UltimateSmoother definition and period
- Lag ranges and ACF estimator

## How it works

- Smooth a selected source with UltimateSmoother, correlate it with delayed copies over a selected data length and color separate lag lines. Three lag-range modes partition the display to fit plot limits.

## Outputs and intended use

- Green indicates positive, red negative and orange/yellow near-zero correlation. Repeated shapes suggest cycles; broadening correlation from short to long lags is interpreted as trend, and abrupt vertical shifts with short samples as possible turns.

## Parameters and stated settings

- The source illustrates autocorrelation length twenty on daily data and recommends length two for turning-point inspection. Add three instances with different Lag range settings for the full display. Actual range boundaries/default smoothing period are absent.

## Failure modes and caveats

- An autocorrelation heatmap is not itself a calibrated power spectrum or proof of forecastable market structure. Extremely short windows can produce unstable estimates.

## Missing information and implementation boundary

- UltimateSmoother coefficients, exact lag ranges, ACF estimator, normalization/variance handling and live confirmation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; source-code parity and complete history remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
smoothed by Ehlers' [i]UltimateSmoother[/i] filter
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
three[/i] distinct ranges
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
such as 20 on a "1D" chart
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
such as 2.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_oqttrc35_tasc_2025_02_autocorrelation_indicator](../tv_oqttrc35_tasc_2025_02_autocorrelation_indicator.md)

## Source

https://www.tradingview.com/script/OQtTRc35-TASC-2025-02-Autocorrelation-Indicator/

Publication ID: OQtTRc35. Source SHA-256: fea1cb70e929766d43c8333a00e5ba2bc716238ddf2e38e26357bcc26e035c39. Raw-description SHA-256: 56948a4c85e03d2961d08e0518e2ccfee32ddd440c5d7e62ac29de611c89ecca.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
