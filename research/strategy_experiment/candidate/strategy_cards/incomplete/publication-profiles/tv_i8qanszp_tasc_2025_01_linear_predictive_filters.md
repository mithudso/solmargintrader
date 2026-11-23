---

id: tv_profile_i8qanszp

name: "TASC 2025.01 Linear Predictive Filters"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Estimate dominant market cycles using an adaptive linear predictive filter and expose forecasts, spectrum and cycle length as separate analytical views."

registry_key: null

runner: null

evaluation: null

---

# TASC 2025.01 Linear Predictive Filters

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate dominant market cycles using an adaptive linear predictive filter and expose forecasts, spectrum and cycle length as separate analytical views.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The processing chain and recommended bandwidths are described, but core predictive and spectrum equations are absent.

- Griffiths coefficient update and prediction equations
- Bandpass coefficients and spectrum calculation

## How it works

- Band-limit prices through second-order high/low-pass filters. Adapt Griffiths predictor coefficients to reduce latest prediction error, derive a partial frequency spectrum from those coefficients and identify its strongest component.

## Outputs and intended use

- Predictor/signal crosses are proposed as possible trade cues. A periodogram colors relative cycle power, while the dominant-cycle output can tune separate indicators.

## Parameters and stated settings

- Suggested band boundaries include an upper bound at least 125 bars for position trading, 18-40 for swing trading and minimum lower bound eight to limit aliasing. Spectrum/cycle data length should reach the upper boundary.

## Failure modes and caveats

- Adaptive frequency estimates can shift with noisy, nonstationary data. A dominant spectral component does not guarantee a persistent economically tradable cycle or reliable future price projection.

## Missing information and implementation boundary

- Filter coefficients, adaptive update rate/order, forecast horizon, spectral power estimator and exact cycle-selection implementation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
upper bound of 125 bars or higher
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
upper bound of 40 bars and a lower bound of 18 bars
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
a minimum of eight bars
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
adaptively minimizes the error between the latest data point and prediction
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_i8qanszp_tasc_2025_01_linear_predictive_filters](../tv_i8qanszp_tasc_2025_01_linear_predictive_filters.md)
- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)

## Source

https://www.tradingview.com/script/i8qanSzP-TASC-2025-01-Linear-Predictive-Filters/

Publication ID: i8qanSzP. Source SHA-256: a5db406827fe6ca3b8aa72ab79e9ead9a35f46d86e3a8d8e60e90e5f7957c028. Raw-description SHA-256: 5bc471c2c1e663d1a02a6992dc8b552c0fc6f55ccfc192490cd4a38453d04e63.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
