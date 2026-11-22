---

id: tv_profile_iipj0kjz

name: "TimeSeriesBenchmarkMeasures"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Benchmark forecast errors, temporal dependence, stationarity and interval behavior for model or strategy research. The library evaluates caller-generated predictions and observations; it provides neither forecasts nor trading decisions."

registry_key: null

runner: null

evaluation: null

---

# TimeSeriesBenchmarkMeasures

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Benchmark forecast errors, temporal dependence, stationarity and interval behavior for model or strategy research. The library evaluates caller-generated predictions and observations; it provides neither forecasts nor trading decisions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Explicit complete-data forecast metrics is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Point-error APIs offer absolute/squared/root errors, normalized and percentage variants, including target offsets. Interval RMSE uses the midpoint of each lower/upper bound pair.
- Temporal diagnostics compute autocorrelation at selected lags and an ADF unit-root statistic with critical value and observation count.
- Interval sharpness is average width; resolution is width deviation; coverage is the fraction of targets inside intervals. Pinball loss uses quantile-weighted asymmetric errors; the matrix mean selects the lower bound at or below the median quantile and upper bound above it.
- For paired actual a and forecast f,MAE=mean(abs(a-f)),MSE=mean((a-f)^2),RMSE=sqrt(MSE). Interval RMSE replaces f with(lower+upper)/2. Sharpness=mean(upper-lower);resolution=mean(abs(width-sharpness));coverage=count(lower<=a<=upper)/N. Theil=sqrt(sum((a-f)^2))/(sqrt(sum(a^2))+sqrt(sum(f^2))). Pinball=tau*(a-f) if a>=f else(1-tau)*(f-a);mean pinball uses lower column for tau<=0.5,upper otherwise. NRMSE/ADF and missing/degenerate handling remain excluded.
- Disclosed SMAPE modes are0:sum(abs(f-a))/sum(f+a);1:mean(abs(f-a)/((f+a)/2));2:100*mean(abs(f-a)/(abs(f)+abs(a))). Preserve their different scaling and restrict to nonzero denominators.

## Outputs and intended use

- Returns scalar metrics, lag-value arrays or the ADF statistic/critical-value/count tuple for comparative model assessment.
- Theil’s expression normalizes error norm by observed and forecast norms; metric scale and calibration should be interpreted alongside forecast horizon and nominal coverage.
- Usable scope: Explicit complete-data forecast metrics. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Aligned arrays, lower/upper interval matrices, RMSE order/offset defaulting to zero, ACF lags, ADF maximum lag/confidence and quantile level.
- SMAPE offers three distinct formulas; their scales differ, so scores must retain the selected mode.

## Failure modes and caveats

- Source claims Theil’s supplied normalized expression ranges to infinity, although triangle inequality bounds that expression. It also reverses the intuitive descriptions of width and deviation scores.
- Percentage errors can fail at zero/negative denominators; stationarity rejection is conditional on the unspecified regression specification.

## Missing information and implementation boundary

- NRMSE normalization, ADF regression/critical-value implementation, missing-value behavior and several percentage/error conventions are undisclosed.

## Data requirements

Required inputs: caller historical forecasts and aligned realized observations, forecast interval matrices and nominal quantile/confidence metadata.

Repository input-class support: unavailable or unresolved. The caller must supply aligned model outputs/observations or state/event contracts; these are not provided by OHLCV alone.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
evaluate the accuracy, stability, and risk characteristics of various models or strategies
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
converting interval forecasts (with min/max bounds) into point forecasts using the mean of the interval bounds
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
default=0`
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
sqrt(Sum((y_i - f_i)^2)) / (sqrt(Sum(y_i^2)) + sqrt(Sum(f_i^2)))
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
For τ ≤ 0.5: Uses the first column (min) of forecasts
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
For τ > 0.5: Uses the second column (max) of forecasts
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
  In statistics, mean absolute error (MAE) is a measure of errors between paired observations expressing the same phenomenon. Examples of Y versus X include comparisons of predicted versus observed, subsequent time versus initial time, and one technique of measurement versus an alternative technique of measurement.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
  The Mean Squared Error (MSE) is a measure of the quality of an estimator. As it is derived from the square of Euclidean distance, it is always a positive value that decreases as the error approaches zero.
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
  Root Mean Squared Error for a set of interval windows. Computes RMSE by converting interval forecasts (with min/max bounds) into point forecasts using the mean of the interval bounds, then compares against actual target values.
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
The sharpness metric is calculated as the mean of the interval widths across all observations, where
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
The resolution is calculated as the mean absolute deviation of individual interval widths from the
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
  Calculates the coverage probability, which is the percentage of target values that fall within the corresponding forecasted prediction intervals.
```

### E13: mechanism, parameters, outputs_and_use, readiness

```text
Theil's Inequality Coefficient is calculated as: `sqrt(Sum((y_i - f_i)^2)) / (sqrt(Sum(y_i^2)) + sqrt(Sum(f_i^2)))`
```

### E14: mechanism, parameters, outputs_and_use, readiness

```text
- If target >= forecast: (target - forecast) * τ
```

### E15: mechanism, parameters, outputs_and_use, readiness

```text
- If target < forecast: (forecast - target) * (1 - τ)
```

### E16: mechanism, parameters, outputs_and_use, readiness

```text
    [b]mode (int)[/b]: Type of method: default=0:`sum(abs(Fi-Ti)) / sum(Fi+Ti)` , 1:`mean(abs(Fi-Ti) / ((Fi + Ti) / 2))` , 2:`mean(abs(Fi-Ti) / (abs(Fi) + abs(Ti))) * 100`
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)

## Source

https://www.tradingview.com/script/IiPJ0Kjz-TimeSeriesBenchmarkMeasures/

Publication ID: IiPJ0Kjz. Source SHA-256: 8a8ea4d2949fbd107e65a935e24ea0a19beac3530ea75f27f3cbfe5c680132ec. Raw-description SHA-256: bf4726815985b3494c2e7e2801865acf92187896a0cef201839baf8261f87683.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
