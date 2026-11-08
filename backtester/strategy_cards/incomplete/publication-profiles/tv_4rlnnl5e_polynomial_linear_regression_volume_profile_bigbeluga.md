---

id: tv_profile_4rlnnl5e

name: "Polynomial/Linear Regression Volume Profile [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Measure historical volume concentration relative to a fitted trend path rather than fixed horizontal prices."

registry_key: null

runner: null

evaluation: null

---

# Polynomial/Linear Regression Volume Profile [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Measure historical volume concentration relative to a fitted trend path rather than fixed horizontal prices.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core regression-relative volume allocation and grid construction are not disclosed.

- Grid bounds and row assignment
- Volume weights/allocation
- Regression source/lookback and dispersion definition

## How it works

- Fit an OLS line or quadratic curve, form parallel regression-relative layers and accumulate volume weights by row. Highlight the highest-volume row as a dynamic POC and draw standard-deviation envelopes.

## Outputs and intended use

- Use the profile, density colors and dashboard to inspect trend-relative value regions and extremes. The source suggests POC pullbacks, boundary reversion and low-volume-zone breakouts, but provides no measured probabilities or complete execution rules.

## Parameters and stated settings

- Choose linear versus second-degree polynomial baseline, profile width and line styles. Envelopes are at one, two and three standard deviations; lookback, bin count and default widths are not specified.

## Failure modes and caveats

- Institutional activity and resting transaction volume are not directly observed by regression/OHLCV. Fitted curves and POC rows can move on refitting; an outer-band touch is not a guaranteed reversion.

## Missing information and implementation boundary

- Regression source/window, layer bounds, volume allocation and standard-deviation definition are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class; code parity and cached-history coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
second-degree curved path (Polynomial)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
envelopes at 1, 2, and 3 Standard Deviations.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
cumulative transaction weights across each regression row.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_4rlnnl5e_polynomial_linear_regression_volume_profile_bigbeluga](../tv_4rlnnl5e_polynomial_linear_regression_volume_profile_bigbeluga.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/4rlNNL5e-Polynomial-Linear-Regression-Volume-Profile-BigBeluga/

Publication ID: 4rlNNL5e. Source SHA-256: 2281a6bd9b770ada231d3d30944f97759b127c3ed208dbd5c1e76e60cac53bdb. Raw-description SHA-256: 8f80da612588be17e99e85d10190651f7a807f810a2c830b097db92b0fcd72e6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
