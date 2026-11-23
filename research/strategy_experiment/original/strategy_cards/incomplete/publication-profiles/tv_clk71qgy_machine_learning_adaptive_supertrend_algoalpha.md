---

id: tv_profile_clk71qgy

name: "Machine Learning Adaptive SuperTrend [AlgoAlpha]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Machine Learning Adaptive SuperTrend replaces a single fixed volatility assumption with a clustered ATR regime. It groups historical ATR observations into low, medium and high volatility and feeds the selected regime level into SuperTrend. The purpose is an adaptive trend display with separate information about current volatility, rather than a supervised model trained to predict returns."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning Adaptive SuperTrend [AlgoAlpha]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Machine Learning Adaptive SuperTrend replaces a single fixed volatility assumption with a clustered ATR regime. It groups historical ATR observations into low, medium and high volatility and feeds the selected regime level into SuperTrend. The purpose is an adaptive trend display with separate information about current volatility, rather than a supervised model trained to predict returns.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** K-means initialization/iteration details and centroid substitution into SuperTrend are not sufficiently defined.

- K-means initialization/iteration details and centroid substitution into SuperTrend are not sufficiently defined.

## How it works

- Calculate ATR over a training interval, initialize volatility cluster guesses and iterate k-means centroids.
- Assign current volatility to one of the clusters and use the classified level in the SuperTrend calculation.

## Outputs and intended use

- Read trend-line color changes for possible trend shifts and use the table for centroids, cluster sizes and current volatility; alerts cover trend and volatility changes.

## Parameters and stated settings

- There are three volatility clusters. Inputs include ATR length, SuperTrend factor, initial volatility percentiles, training interval and bullish/bearish colors; no numeric defaults are supplied.

## Failure modes and caveats

- Analytical: clustering describes the training distribution and may lag abrupt shifts; adaptation does not demonstrate better trade outcomes.

## Missing information and implementation boundary

- Cluster stopping criteria, empty-cluster behavior, precise centroid substitution, training defaults and close confirmation are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
classify volatility into three clusters: high, medium, and low.
```

### E2: parameters, readiness

```text
Configure ATR length, SuperTrend factor, and initial volatility guesses.
```

### E3: outputs_and_use, readiness

```text
data table displaying cluster centroids, sizes, and the current volatility level
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_clk71qgy_machine_learning_adaptive_supertrend_algoalpha](../tv_clk71qgy_machine_learning_adaptive_supertrend_algoalpha.md)

## Source

https://www.tradingview.com/script/CLk71Qgy-Machine-Learning-Adaptive-SuperTrend-AlgoAlpha/

Publication ID: CLk71Qgy. Source SHA-256: a7592b5ba00d37be217dd37e5c5a5b8678593f3165d62506d5ed99e1028a0894. Raw-description SHA-256: cfc3b08e81589cc818024f3e59108d6c3b1a67be33cadc1d32956d4467a8a1f5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
