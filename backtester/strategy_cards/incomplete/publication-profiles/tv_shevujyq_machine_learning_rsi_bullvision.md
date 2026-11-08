---

id: tv_profile_shevujyq

name: " Machine Learning RSI ║ BullVision"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Contextualize RSI using historically similar feature patterns and optionally blend/filter that contextual estimate with ordinary RSI."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning RSI ║ BullVision

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Contextualize RSI using historically similar feature patterns and optionally blend/filter that contextual estimate with ordinary RSI.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core feature/distance/weighting and threshold equations remain unspecified despite the clear conceptual pipeline.

- Feature normalization and distance weights
- Neighbor weighting/blending
- Dynamic thresholds and filter settings

## How it works

- Construct normalized RSI level/momentum, volatility, regression-slope and price-momentum features. Find nearest historical matches, average their RSI by similarity weight and blend with the base oscillator; optional Kalman, ALMA or double-EMA filters smooth the result.

## Outputs and intended use

- Read the oscillator and static/dynamic overbought/oversold levels as contextual momentum, not an explicit price forecast. Trend/impulse palettes and accessibility modes change presentation.

## Parameters and stated settings

- Choose RSI length and smoothing, KNN enablement, neighbor count, one-to-five features, model weight, lookback and filtering. Actual numerical defaults, dynamic-threshold formulas and filter parameters are not listed.

## Failure modes and caveats

- Historical similarity need not persist across regimes. Normalization using future samples would leak information, and extra filtering can conceal rapid changes; the source does not establish leakage-free code or superior sensitivity.

## Missing information and implementation boundary

- Feature equations, normalization windows, distance kernel, neighbor exclusion, weighting, blend ordering and dynamic thresholds are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculations use ordinary OHLCV; missing equations are specification gaps, not missing external market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
only 1 (RSI) or up to all 5 features
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
selects the closest matches and averages their RSI values, weighted by similarity.
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Kalman Filter, ALMA, Double EMA
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_kalman_filter](../tv_method_kalman_filter.md)
- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_shevujyq_machine_learning_rsi_bullvision](../tv_shevujyq_machine_learning_rsi_bullvision.md)

## Source

https://www.tradingview.com/script/sHevuJyQ-Machine-Learning-RSI-BullVision/

Publication ID: sHevuJyQ. Source SHA-256: 8c8b3c92fdbd5b892ad03358ad401aa00d4e87015aba785857a95fa6a01c2283. Raw-description SHA-256: 0df9981a55a69577072588475d0f3245c3afc29aeaa580b125ed73c9a2512e35.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
