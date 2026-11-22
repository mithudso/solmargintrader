---

id: tv_profile_rs3xqwyx

name: "Support and Resistance Logistic Regression | Flux Charts"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Learn which historical pivot conditions tend to produce repeatedly respected levels, then score and monitor new support/resistance candidates."

registry_key: null

runner: null

evaluation: null

---

# Support and Resistance Logistic Regression | Flux Charts

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Learn which historical pivot conditions tend to produce repeatedly respected levels, then score and monitor new support/resistance candidates.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The model features and purpose are disclosed, but training, outcome labeling and level-interaction rules are not defined enough to reproduce the classifier.

- Logistic training/feature-scaling equations
- Respect/break tolerance and label maturation
- Model window and default parameters

## How it works

- Detect pivots, extract RSI and absolute candle-body size, and continuously fit logistic regression using subsequent respect behavior as labels. Plot new pivots whose model score exceeds a probability threshold and track retests or closes beyond them.

## Outputs and intended use

- Probability labels, R retest markers, B break markers and corresponding alerts provide level-monitoring context. The fitted score is a model output, not a demonstrated calibrated success probability.

## Parameters and stated settings

- Pivot Length, Target Respects and Probability Threshold are inputs. Display and line styling are configurable; exact numerical defaults are not given.

## Failure modes and caveats

- Training labels depend on future price behavior, making label maturation and leakage controls essential. Multiple retests of one level are dependent observations, and model calibration may drift.

## Missing information and implementation boundary

- RSI period, feature scaling, optimization/regularization, training window, respect tolerance and timing of label updates are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
including the RSI (Relative Strength Index) and the Body Size (the absolute difference between the open and close price of the candle).
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
continuously trained on past pivot data and their subsequent behavior
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Body Size (the absolute difference between the open and close price of the candle)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_logistic_prediction](../../../strategy_research/tv_method_logistic_prediction.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_rs3xqwyx_support_and_resistance_logistic_regression_flux_charts](../tv_rs3xqwyx_support_and_resistance_logistic_regression_flux_charts.md)

## Source

https://www.tradingview.com/script/rS3xqWYx-Support-and-Resistance-Logistic-Regression-Flux-Charts/

Publication ID: rS3xqWYx. Source SHA-256: 6c607ea05445194cf6b26dda5a7ba6d8c516601bb9b41664d99bd9b753cecdc7. Raw-description SHA-256: 145f6c2bbfbf9000171a4545f12c8fd40a49cefb6c6f946d3a69b7eeb675ddb8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
