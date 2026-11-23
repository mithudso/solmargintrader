---

id: tv_profile_u0r2gpti

name: "Fourier Extrapolator of Price w/ Projection Forecast [Loxx]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Fit a sum of oscillating components to historical prices and extend that fitted mathematical model into a future projection."

registry_key: null

runner: null

evaluation: null

---

# Fourier Extrapolator of Price w/ Projection Forecast [Loxx]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fit a sum of oscillating components to historical prices and extend that fitted mathematical model into a future projection.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Initialization, coefficient estimation, tolerance stopping logic, refit schedule and forecast-validation evidence are missing.

- Initialization, coefficient estimation, tolerance stopping logic, refit schedule and forecast-validation evidence are missing.

## How it works

- Estimate bias, amplitude coefficients and harmonic frequencies using Quinn-Fernandes frequency estimation. Fit harmonics sequentially to the remaining residual until the chosen harmonic count is reached, rather than fixing ordinary Fourier frequencies that simply repeat the sample.

## Outputs and intended use

- A green/red curve shows fitted history and a yellow/fuchsia curve modeled future values. The stated purpose is to demonstrate an extrapolation method for later indicators.

## Parameters and stated settings

- Inputs are price source, number of past bars, future bars, harmonics and frequency tolerance. The saved prose supplies no numerical defaults.

## Failure modes and caveats

- Good in-sample fit does not establish that market cycles persist out of sample. Increasing harmonic count can fit noise and projections may change when refitted.

## Missing information and implementation boundary

- Initialization, coefficient estimation, tolerance stopping logic, refit schedule and forecast-validation evidence are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
xi = m + Sum( a*Cos(w*i) + b*Sin(w*i), h=1..H )
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
This indicator uses the Quinn-Fernandes algorithm to find the harmonic frequencies.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
After fitting a new harmonic , the coded algorithm computes the residue between the updated model and the real values and fits a new harmonic to the residue.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_u0r2gpti_fourier_extrapolator_of_price_w_projection_forecast_loxx](../tv_u0r2gpti_fourier_extrapolator_of_price_w_projection_forecast_loxx.md)

## Source

https://www.tradingview.com/script/u0r2gpti-Fourier-Extrapolator-of-Price-w-Projection-Forecast-Loxx/

Publication ID: u0r2gpti. Source SHA-256: 79a91b8d7444de4f974060c915c544ff0c47811046b3ad067d03ac37223ab1b4. Raw-description SHA-256: 4376183c12da5e9a716c1dda5bbb078c552beae1167f0b28dd0ae0182c86db40.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
