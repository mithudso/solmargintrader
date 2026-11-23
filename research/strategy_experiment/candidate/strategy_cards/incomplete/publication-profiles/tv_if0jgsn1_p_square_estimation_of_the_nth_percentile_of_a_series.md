---

id: tv_profile_if0jgsn1

name: "P-Square - Estimation of the Nth percentile of a series"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "P-Square estimates a streaming percentile over available history to avoid repeatedly sorting or retaining an expensive full series. Its financial example compares return observations, mean/dispersion and exact-versus-estimated percentile curves. The aim is computationally efficient long-history distribution research, not a directional signal. The source points to an implementation and paper but does not reproduce marker-update equations. Its normality example also conflates the mean-plus-one-standard-deviation location with a raw standard deviation value, which should not be read as a rigorous normality test."

registry_key: null

runner: null

evaluation: null

---

# P-Square - Estimation of the Nth percentile of a series

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

P-Square estimates a streaming percentile over available history to avoid repeatedly sorting or retaining an expensive full series. Its financial example compares return observations, mean/dispersion and exact-versus-estimated percentile curves. The aim is computationally efficient long-history distribution research, not a directional signal. The source points to an implementation and paper but does not reproduce marker-update equations. Its normality example also conflates the mean-plus-one-standard-deviation location with a raw standard deviation value, which should not be read as a rigorous normality test.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core P-Square update/initialization and return construction are only externally referenced.

## How it works

- Update an unspecified P-Square streaming quantile estimator as observations arrive.
- Compare estimated percentile against actual percentile and return mean/dispersion in the example.

## Outputs and intended use

- Return scatter and reference curves support estimator/financial-distribution inspection.

## Parameters and stated settings

- Example quantile84.1%; source-era built-in length limit4999 is cited as motivation, not verified current capacity.

## Failure modes and caveats

- Approximate quantiles can depend on initialization/order and need not track a rolling window.
- Visual percentile/dispersion comparison is not a complete normality test.

## Missing information and implementation boundary

- P-Square marker equations, initialization, return definition, exact-reference window and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The example uses financial returns derived from prices.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
max 4999
```

### E2: parameters

```text
84.1th percentile
```

### E3: mechanism, readiness

```text
P-Square is a fast algorithm
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_if0jgsn1_p_square_estimation_of_the_nth_percentile_of_a_series](../tv_if0jgsn1_p_square_estimation_of_the_nth_percentile_of_a_series.md)

## Source

https://www.tradingview.com/script/iF0JGsN1-P-Square-Estimation-of-the-Nth-percentile-of-a-series/

Publication ID: iF0JGsN1. Source SHA-256: d48a56f8ad612affd658c48105074454a7bcb044ca337d842473ad761a9cf60b. Raw-description SHA-256: 6901ed7dcc2354cc3805e1284bff9311688b69bf4539ea89025344814321df79.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
