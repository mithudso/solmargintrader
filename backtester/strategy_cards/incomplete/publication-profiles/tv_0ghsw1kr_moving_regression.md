---

id: tv_profile_0ghsw1kr

name: "Moving Regression"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Moving Regression creates a rolling smooth representation of chart data while allowing the trader to tune how closely the line follows recent curvature. It combines a local polynomial fit with a moving window, so its role is broader than a fixed moving average. The author proposes using the resulting curve to judge momentum and trend direction, identify possible reversals, and locate contextual support or resistance."

registry_key: null

runner: null

evaluation: null

---

# Moving Regression

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Moving Regression creates a rolling smooth representation of chart data while allowing the trader to tune how closely the line follows recent curvature. It combines a local polynomial fit with a moving window, so its role is broader than a fixed moving average. The author proposes using the resulting curve to judge momentum and trend direction, identify possible reversals, and locate contextual support or resistance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The prose defines a rolling polynomial concept but does not resolve the fitting criterion or input series for a reproducible line.

- The prose defines a rolling polynomial concept but does not resolve the fitting criterion or input series for a reproducible line.

## How it works

- Fit a polynomial of the selected degree to the specified prior-data window and evaluate the polynomial at the final data point to form each observation of the rolling line.
- Optional direction coloring uses the fitted polynomial’s next-step direction: an upward projection produces green and the alternative produces red.
- Longer windows and lower degree favor smoothing with lag; increasing degree can reduce lag while admitting more local noise. A constant-degree fit matches the same-window simple moving average.

## Outputs and intended use

- Read the curve for trend confirmation, momentum and possible support/resistance; its short extrapolation is a directional suggestion rather than an independently validated forecast.

## Parameters and stated settings

- Length controls the moving fitting window; Local Polynomial Degree controls curvature. Predict Trend Direction enables the forecast-based coloring.
- The author explicitly compares degree 0 with SMA, degree 1 with a linear fit, and degree 2 with a squared fit; no default length is disclosed.

## Failure modes and caveats

- Analytical: high-degree fits can overreact to noisy windows and extrapolated direction can reverse as the window advances.

## Missing information and implementation boundary

- Exact input price series, numerical fitting method, default length, and executable entry/exit rules are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart prices support the described deterministic calculation class; algorithm parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Moving Regression is a generalization of moving average and polynomial regression.

The procedure approximates a specified number of prior data points with a polynomial function of a user-defined degree. Then, polynomial interpolation of the last data point is used to construct a Moving Regression time series.
```

### E2: outputs_and_use, readiness

```text
When the local polynomial is predicted to move up in the next time step, the color of the Moving Regression curve will be green.
```

### E3: parameters, mechanism, readiness

```text
When the degree of the local polynomial is set to 0 (i.e., fitting data to a constant level), the Moving Regression time series exactly matches the Simple Moving Average of the same length.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_0ghsw1kr_moving_regression](../../tv_0ghsw1kr_moving_regression.md)
- [tv_method_polynomial_regression](../tv_method_polynomial_regression.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/0GhsW1KR-Moving-Regression/

Publication ID: 0GhsW1KR. Source SHA-256: fe7aeaa6515950cb555f9ec926a11dc5fc7150549d1dd1acd50a3b6b2c908a8e. Raw-description SHA-256: ea80fc4ea69f4085bcb8d2609bc72c3ff0975e4cbad5eaa4568771655d30f605.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
