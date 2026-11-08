---

id: tv_profile_cq5x2ame

name: "AR Forecast Scatterplot [SS]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Demonstrate an autoregressive forecast with a scatterplot and model-fit diagnostics using the author's statistical library."

registry_key: null

runner: null

evaluation: null

---

# AR Forecast Scatterplot [SS]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Demonstrate an autoregressive forecast with a scatterplot and model-fit diagnostics using the author's statistical library.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: The fitted variable, coefficient estimator, interval formula, residual assumptions, recursive projection and validation procedure are missing.

- The fitted variable, coefficient estimator, interval formula, residual assumptions, recursive projection and validation procedure are missing.

## How it works

- Fit a lag-one autoregressive relationship over a user-selected training period, then project likely outcomes from the estimated coefficients. The author recommends choosing a span aligned with the current trend using a separate regression tool.

## Outputs and intended use

- Green shows an upper-confidence scenario, blue the central forecast and red a lower-confidence scenario. An optional model table reports correlation and R-squared for inspecting in-sample fit.

## Parameters and stated settings

- Training duration is user-selected and can be counted in bars. Forecast horizon, confidence cutoffs and numerical defaults are not supplied.

## Failure modes and caveats

- Manually choosing the strongest trend and preferring high fit statistics can overfit. Selected prediction/actual screenshots are illustrations, not systematic out-of-sample validation.

## Missing information and implementation boundary

- The fitted variable, coefficient estimator, interval formula, residual assumptions, recursive projection and validation procedure are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed feature uses ordinary price/volume history; this is input-class support rather than verified implementation or data-cache parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
it tags a lag of 1, performs an autoregressive assessment over the desired training time
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
You want to see both a high correlation and a high R2 value.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Green = represents the upper confidence predictions (best case scenario)
Blue = represents the most likely result
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cq5x2ame_ar_forecast_scatterplot_ss](../tv_cq5x2ame_ar_forecast_scatterplot_ss.md)

## Source

https://www.tradingview.com/script/CQ5x2amE-AR-Forecast-Scatterplot-SS/

Publication ID: CQ5x2amE. Source SHA-256: 713fbd0d46499780495d115457d19a67f8b0935475fec781c9da5a252f347ac2. Raw-description SHA-256: fec30eb97b540d2f9ab3b6a8660f3572f8edf8afdd4c7c7dac9ee1dabd91a674.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
