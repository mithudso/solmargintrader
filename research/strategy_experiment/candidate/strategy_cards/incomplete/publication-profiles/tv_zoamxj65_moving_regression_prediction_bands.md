---

id: tv_profile_zoamxj65

name: "Moving Regression Prediction Bands"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare current price with a prior-bar polynomial forecast and an error-scaled envelope to identify movements outside the recently fitted trend."

registry_key: null

runner: null

evaluation: null

---

# Moving Regression Prediction Bands

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare current price with a prior-bar polynomial forecast and an error-scaled envelope to identify movements outside the recently fitted trend.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Polynomial degree, fitting weights, RMSE degrees of freedom, crossing confirmation and complete risk controls are absent.

- Polynomial degree, fitting weights, RMSE degrees of freedom, crossing confirmation and complete risk controls are absent.

## How it works

- Fit local polynomial regression over a lookback, extrapolate one step and estimate fit RMSE. Use the preceding bar's forecast plus/minus multiplier times preceding RMSE for current bands, avoiding a current-fit center for that forecast comparison.

## Outputs and intended use

- Choose previous prediction, current regression or a colored ribbon as center display. The author suggests upper-band breaks as bullish momentum cues and lower-band or centerline crossings as possible exits.

## Parameters and stated settings

- Length and band multiplier are configurable. Multiplier defaults two, which the author roughly equates with a ninety-five-percent normal interval.

## Failure modes and caveats

- In-sample residual RMSE alone is not a calibrated forecast-error interval. Polynomial extrapolation and heavy-tailed market returns can invalidate nominal normal coverage.

## Missing information and implementation boundary

- Polynomial degree, fitting weights, RMSE degrees of freedom, crossing confirmation and complete risk controls are absent.

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
Upper Band[/i] = [i]MRPrediction_prev[/i] + [i]Multiplier[/i]*([i]RMSE_prev[/i])
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Lower Band[/i] = [i]MRPrediction_prev[/i] - [i]Multiplier[/i]*([i]RMSE_prev[/i])
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the default value of 2.0 roughly corresponds to the 95% prediction interval
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
crossing above the upper band
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_polynomial_regression](../tv_method_polynomial_regression.md)
- [tv_zoamxj65_moving_regression_prediction_bands](../tv_zoamxj65_moving_regression_prediction_bands.md)

## Source

https://www.tradingview.com/script/zOaMXJ65-Moving-Regression-Prediction-Bands/

Publication ID: zOaMXJ65. Source SHA-256: 77dbb47460e909e758763ddb9a5514c3a2f070eb703e78b6a21f7e71eee48121. Raw-description SHA-256: 4737843b9dce9be2176f368cdd5b1fc5ed8a3346c8fda2888e55372c250b3b2d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
