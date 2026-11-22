---

id: tv_profile_iini8ml2

name: "Weighted Harrell-Davis Quantile Estimator with AbsoluteDeviation"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Weighted Harrell-Davis Quantile Estimator explores weighted distribution-location estimates and absolute-deviation fences as alternatives to mean-based price envelopes. The author’s goal is a more robust view of non-normal financial data, based on adapted statistical research. The publication warns that the included function is for testing and may fail in different data/compiler environments, so this is a research implementation rather than an established production specification."

registry_key: null

runner: null

evaluation: null

---

# Weighted Harrell-Davis Quantile Estimator with AbsoluteDeviation

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Weighted Harrell-Davis Quantile Estimator explores weighted distribution-location estimates and absolute-deviation fences as alternatives to mean-based price envelopes. The author’s goal is a more robust view of non-normal financial data, based on adapted statistical research. The publication warns that the included function is for testing and may fail in different data/compiler environments, so this is a research implementation rather than an established production specification.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Quantile weights, effective sample size, bias correction, fence construction and numeric special-function details are absent.

- Quantile weights, effective sample size, bias correction, fence construction and numeric special-function details are absent.

## How it works

- Use a weighted Harrell-Davis quantile approach and absolute-deviation-based fences, drawing on beta/gamma and incomplete-beta implementations cited in the source.

## Outputs and intended use

- Inspect robust location/deviation estimates for price-distribution analysis; no explicit trading thresholds or entries are prescribed.

## Parameters and stated settings

- No quantile target, weighting schedule, sample length, fence multiplier or defaults are provided in the saved prose.

## Failure modes and caveats

- The author warns of modifications and possible failures; analytical: weighted quantile efficiency/robustness depends on weights and tails, and blanket claims against normal-based statistics are not universal.

## Missing information and implementation boundary

- Quantile weights, effective sample size, bias correction, fence construction and numeric special-function details are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
Weighted Harrell-Davis Quantile Estimator with Absolute Deviation Fences.
```

### E2: risks, readiness

```text
THE INCLUDED FUNCTION MUST BE CONSIDERED FOR TESTING.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_iini8ml2_weighted_harrell_davis_quantile_estimator_with_absolutedeviation](../tv_iini8ml2_weighted_harrell_davis_quantile_estimator_with_absolutedeviation.md)

## Source

https://www.tradingview.com/script/iiNI8Ml2-Weighted-Harrell-Davis-Quantile-Estimator-with-AbsoluteDeviation/

Publication ID: iiNI8Ml2. Source SHA-256: 16ab9d94b9eea15b9badb51594da897a04ab63f6303338d48be671bb63df2f40. Raw-description SHA-256: f37544bec93480f17970e9af27a237ef3989fe7204b7a76f984a38649f208779.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
