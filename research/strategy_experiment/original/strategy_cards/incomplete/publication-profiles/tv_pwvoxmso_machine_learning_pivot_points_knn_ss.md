---

id: tv_profile_pwvoxmso

name: "Machine Learning Pivot Points (KNN) [SS]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare the current regression slope with slope signatures collected before confirmed turning points to flag possible approaching pivots."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning Pivot Points (KNN) [SS]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare the current regression slope with slope signatures collected before confirmed turning points to flag possible approaching pivots.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The feature concept and default signature lengths are disclosed, but the classifier output and confidence cannot be reproduced from the prose.

- Exact slope/distance normalization
- Cluster confidence and signal rule
- Training memory and outcome-label rules

## How it works

- At each confirmed high/low pivot, store the regression slope of its preceding signature window. Compare current rolling slope with historical high/low classes using nearest-neighbor distances and derive a relative cluster-similarity confidence.

## Outputs and intended use

- A live table shows high/low bias and similarity; a separate proof-of-concept table reports reversal occurrence and subsequent moves. Glowing markers give way to ordinary triangles when polyline limits constrain history.

## Parameters and stated settings

- K defaults two. The described training uses ten-bar pivots and twenty-bar slope signatures, with pivot left/right and signature-window settings adjustable.

## Failure modes and caveats

- A ninety-percent similarity description is not a calibrated ninety-percent reversal probability. Pivot labels become known only after confirmation, and training/test separation is not demonstrated.

## Missing information and implementation boundary

- Slope normalization, exact distance aggregation, confidence mapping, success/reversal definition, training-window limits and signal gating are absent.

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
Every time a 10-bar pivot (High or Low) is confirmed, the script extracts the Linear Regression Slope of the 20 bars leading into that point.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
KNN Clusters (K):[/i] Set to 2 by default.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Confidence Metric:[/i] This represents the [i]Cluster Similarity[/i].
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_pwvoxmso_machine_learning_pivot_points_knn_ss](../tv_pwvoxmso_machine_learning_pivot_points_knn_ss.md)

## Source

https://www.tradingview.com/script/PwVoxMSo-Machine-Learning-Pivot-Points-KNN-SS/

Publication ID: PwVoxMSo. Source SHA-256: ee5b8abab80ea14e2f5a296e29054a236f109223a3def36cf6d77f1b083e6fb5. Raw-description SHA-256: 3992f0d1f454a578166d825114c6b2cc5d27b52dabbbe20ae857a0384e6caff5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
