---

id: tv_profile_gpct4m6t

name: "Machine Learning: kNN-based Strategy"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This kNN publication classifies the current market state by comparing two current indicator values with historical pairs. Its purpose is to explore whether indicator-state similarity contains information about the next market move. Historical observations and their direction labels provide the reference examples, and nearby examples determine the current class. The author calls kNN unsupervised, but the described use of direction labels is a supervised classification setup; that terminology conflict does not change the disclosed mechanism. The source explicitly warns that signals repaint, so the historical display cannot be accepted as a causal backtest."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning: kNN-based Strategy

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This kNN publication classifies the current market state by comparing two current indicator values with historical pairs. Its purpose is to explore whether indicator-state similarity contains information about the next market move. Historical observations and their direction labels provide the reference examples, and nearby examples determine the current class. The author calls kNN unsupervised, but the described use of direction labels is a supervised classification setup; that terminology conflict does not change the disclosed mechanism. The source explicitly warns that signals repaint, so the historical display cannot be accepted as a causal backtest.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Nearest-neighbor distance, feature normalization, k, target horizon and voting are absent.

- Nearest-neighbor distance, feature normalization, k, target horizon and voting are absent.

## How it works

- Store feature1, feature2 and directions in arrays.
- Find nearest historical two-feature states and classify the current observation from their states.
- Permit experimenting with different indicator pairs.

## Outputs and intended use

- Directional predictions support trend-analysis experimentation; playback is suggested for observing behavior.

## Parameters and stated settings

- Neighbor count k and feature indicators are implied; no numeric defaults, distance metric or training-window settings are supplied.

## Failure modes and caveats

- Signals explicitly repaint.
- Feature scaling, overlapping labels and neighbor selection can produce leakage or misleading similarity.
- The source’s unsupervised label conflicts with its labeled-array mechanism.

## Missing information and implementation boundary

- Feature formulas, normalization, distance, k, target horizon, voting, causal exclusions and complete order rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed historical indicator-state framework is compatible with chart-derived features; exact feature rules remain unspecified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
feature1, feature2 and directions
```

### E2: mechanism

```text
two dimensional kNN
```

### E3: risks

```text
Being an unsupervised machine learning algorithm
```

### E4: risks

```text
Warning: Signals ARE repainting.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_gpct4m6t_machine_learning_knn_based_strategy](../tv_gpct4m6t_machine_learning_knn_based_strategy.md)
- [tv_method_knn_prediction](../tv_method_knn_prediction.md)

## Source

https://www.tradingview.com/script/GpcT4M6T-Machine-Learning-kNN-based-Strategy/

Publication ID: GpcT4M6T. Source SHA-256: 325e00ffece93a60659b70cffdb896be64198cd81d99a4877197c3af1bdea3b2. Raw-description SHA-256: a2acb82324274eaa1ad911fc88e2e7803b1695899093f40e572e11942a41aee6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
