---

id: tv_profile_cy6rizcl

name: "Probability Distribution Histogram"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Probability Distribution Histogram describes the empirical distribution of an input series so a trader or researcher can examine shape, tails and model residuals. It explicitly provides no trading signals. Optional transformations and trimming let the user choose which representation of the data to study, while a normal-distribution overlay offers a visual comparison rather than a formal normality test."

registry_key: null

runner: null

evaluation: null

---

# Probability Distribution Histogram

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Probability Distribution Histogram describes the empirical distribution of an input series so a trader or researcher can examine shape, tails and model residuals. It explicitly provides no trading signals. Optional transformations and trimming let the user choose which representation of the data to study, while a normal-distribution overlay offers a visual comparison rather than a formal normality test.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Sample extrema, equal-width bins and count/sample normalization define the independent empirical histogram; optional trimming/normal overlay may remain unspecified.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Find the input sample’s minimum and maximum, divide the span into bins, count observations in each bin and normalize counts by sample size.
- Optionally transform with natural log, percentage change or differencing; optionally trim observations before estimating the distribution.

## Outputs and intended use

- Read bin probability mass and compare shape with an optional normal curve, including for residual diagnostics.

## Parameters and stated settings

- Bin count, transformations, trimming and normal overlay are configurable; no defaults or statistical test thresholds are supplied.

## Failure modes and caveats

- Analytical: binning and trimming can hide tails or make a distribution look more normal; logs require appropriate positive inputs. Historical mass is not a forecast probability.

## Missing information and implementation boundary

- Sample window, bin-edge conventions, trim criteria, normal-curve fitting and invalid-input handling are not documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
compare the count in each bin to the total number of data points, to get a percentage of the total for each bin.
```

### E2: purpose, readiness

```text
This is not an indicator that will give you any trading signals.
```

### E3: parameters, readiness

```text
natural logarithmic function
```

### E4: outputs_and_use, readiness

```text
option to plot the normal distribution as well, for comparison.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cy6rizcl_probability_distribution_histogram](../tv_cy6rizcl_probability_distribution_histogram.md)

## Source

https://www.tradingview.com/script/Cy6RiZcL-Probability-Distribution-Histogram/

Publication ID: Cy6RiZcL. Source SHA-256: b4a6814556cc2a2751933dc881fe80ccff373e0518668f91f9dd639d8664d7ea. Raw-description SHA-256: 36987cff53d0e020eb4437877b330f3f2a9f8b097a39077d97e3a6393a22748a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
