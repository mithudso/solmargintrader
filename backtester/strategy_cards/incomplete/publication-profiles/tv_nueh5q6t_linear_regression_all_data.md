---

id: tv_profile_nueh5q6t

name: "Linear Regression (All Data)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Show a single broad price trend by fitting a regression line across the instrument history available on the chart."

registry_key: null

runner: null

evaluation: null

---

# Linear Regression (All Data)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show a single broad price trend by fitting a regression line across the instrument history available on the chart.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Regression coordinates, treatment of gaps, fit residuals, extension behavior and any actionable thresholds are unspecified.

- Regression coordinates, treatment of gaps, fit residuals, extension behavior and any actionable thresholds are unspecified.

## How it works

- Calculate and plot linear regression using the entire accessible dataset instead of a rolling fixed-length window.

## Outputs and intended use

- Use the fitted line as long-history directional context. The author suggests scrolling to its beginning and returning to the latest bar if a long line is not visible.

## Parameters and stated settings

- The whole-history fitting span is disclosed. No source-price selector, regression default or channel parameter is listed.

## Failure modes and caveats

- The author reports problems below one-hour intraday timeframes and visibility issues for many datapoints. A whole-history fit changes when the accessible sample changes.

## Missing information and implementation boundary

- Regression coordinates, treatment of gaps, fit residuals, extension behavior and any actionable thresholds are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The tool plots a linear regression line using the entire history of an instrument on chart. There are may be issues on intraday timeframes less then 1h.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_nueh5q6t_linear_regression_all_data](../../tv_nueh5q6t_linear_regression_all_data.md)

## Source

https://www.tradingview.com/script/NUeh5q6T-Linear-Regression-All-Data/

Publication ID: NUeh5q6T. Source SHA-256: a128ba6a97afce4c4a8d6becc41cc9287184b08096cb24c291879f898f789705. Raw-description SHA-256: 081067e2e6ed27ccbd6fe5b92f96315bfcab2c6eefdecc6a735356028f6f6719.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
