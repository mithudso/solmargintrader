---

id: tv_profile_gewgoj30

name: "NeuraLib: A Native AI and Deep Learning Runtime"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide a native neural-network research runtime for financial indicators and strategies. NeuraLib packages tensor operations, automatic differentiation, training, validation and scaling, leaving the caller to define a model, target and trading interpretation."

registry_key: null

runner: null

evaluation: null

---

# NeuraLib: A Native AI and Deep Learning Runtime

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Provide a native neural-network research runtime for financial indicators and strategies. NeuraLib packages tensor operations, automatic differentiation, training, validation and scaling, leaving the caller to define a model, target and trading interpretation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The financial runtime API and example workflow are extensive, but core tensor/training and custom-loss behavior remains undisclosed for an independent reproduction.

- Tensor/gradient kernels, initializer defaults, optimizer constants, custom finance-loss equations and scaler/split edge rules are not reproduced in the description.

## How it works

- A sequential builder assembles input, dense, activation, dropout and normalization blocks; custom computational graphs extend it with matrix, sequence and attention primitives. Forward evaluation produces tensors; backward propagation accumulates gradients and optimizer steps update parameters.
- Window/rolling datasets validate row widths and missing values, preserve chronology, separate training and holdout batches, and scale validation using a training-side profile. Prediction outputs can be inverse-scaled into target units.
- Training may run only at the confirmed historical edge or on every explicit call. Optimizer schedules, clipping, accumulation and early stopping control updates. Dropout Monte Carlo prediction returns mean/variance, not a calibrated financial risk distribution.

## Outputs and intended use

- APIs return tensors, predictions, loss/metric history and serialized weights. The first example explicitly plots an untrained model; the return example pairs previous-bar RSI/EMA-relative price/ATR fraction/momentum with a matured next return.
- Companion model extensions add recurrent/convolutional/attention blocks and replay utilities. These capabilities do not establish profitable forecasts or implementation parity.

## Parameters and stated settings

- The return example uses four features, eight hidden units, dropout0.10, AdamW learning rate0.003, a500-row dataset, readiness64 and a16-row validation holdout; trainBatch(16) returns the training side of that split, not a16-row training batch.
- Model dimensions, RNG seed, loss/metrics, scaler kinds, optimizer constants, training gate/cadence and schedules are caller choices.

## Failure modes and caveats

- Claimed external-runtime parity and leakage guards are author assertions without supporting tests in this description. Full-history repeated fitting can still contaminate model-selection judgments if validation is reused.
- Training cost, stochastic initialization and state persistence affect reproducibility. Neural output and dropout dispersion require independent out-of-sample assessment.

## Missing information and implementation boundary

- Tensor/gradient kernels, initializer defaults, optimizer constants, custom finance-loss equations and scaler/split edge rules are not reproduced in the description.

## Data requirements

Required inputs: caller financial feature and matured target arrays, OHLCV for the included return-feature example, caller model training configuration and random seed.

Repository input-class support: unavailable or unresolved. OHLCV supports the example feature class, but arbitrary caller targets, feature definitions and model configuration are additional inputs not established as supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
custom indicators, strategies, regime detection, directional prediction
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The plot in this first example is the untrained forward output
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
nl.windowDataset(4, 1, 500
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
nl.adamW(0.003)
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
dropout(0.10
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
dense(8, nl.ActivationKind.relu
```

### E7: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
if dataset.ready(64)
```

### E8: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
dataset.trainBatch(16)
```

### E9: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
dataset.validationBatch(16)
```

### E10: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
This example trains from completed historical pairs.
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
[*][b]trainBatch(validationRows or validationWindows, targetOffset)[/b]: Returns the training side of the split.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_kalman_filter](../tv_method_kalman_filter.md)
- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_method_logistic_prediction](../../tv_method_logistic_prediction.md)
- [tv_method_neural_prediction](../tv_method_neural_prediction.md)

## Source

https://www.tradingview.com/script/GewgOj30-NeuraLib-A-Native-AI-and-Deep-Learning-Runtime/

Publication ID: GewgOj30. Source SHA-256: 81af1e73eeb5da32b40160c358903ab31c0367579374022e221987c1ea6e37b1. Raw-description SHA-256: 1afcaa9a0be8d403c596bd37259217bf9555b50b70838e0d8be157c42be72152.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
