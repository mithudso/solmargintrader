---

id: tv_profile_whbzgfdu

name: "Machine Learning: Lorentzian Classification"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Classify possible price direction by comparing multi-feature historical observations through a Lorentzian-distance approximate-neighbor model with optional regime/kernel filters."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning: Lorentzian Classification

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Classify possible price direction by comparing multi-feature historical observations through a Lorentzian-distance approximate-neighbor model with optional regime/kernel filters.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The settings are extensive but the central neighbor/classification and filter/exit equations are delegated to unavailable code.

- Distance/feature/ANN algorithm
- Training target and leakage controls
- Filter/kernel/exit equations

## How it works

- Construct RSI,WaveTrend,CCI and ADX-based features, search approximate nearest historical cases with a Lorentzian metric and aggregate their directional labels. Apply volatility/regime/optional ADX filters and kernel-regression context, with optional dynamic exits.

## Outputs and intended use

- Color bars, show integer predictions/entry-exit cues,kernel estimate and an optional configuration win-rate table. The theoretical event-warping analogy does not establish that the model explicitly knows macro-event times.

## Parameters and stated settings

- Defaults include sourcehlc3,neighbors8,history2000 and five features(RSI,WT,CCI,ADX,RSI). Volatility/regime filters on,ADX off; regime threshold-0.1,ADX20. Kernel on with lookback8,weight8,start25. Exits/dynamic exits default off.
- Published bounds: neighbors 1–100 step 1 (default 8); feature count 2–5 (default 5); color compression 1–10 (default 1). Single-parameter features use second-parameter EMA smoothing default 1.
- Regime threshold defaults -0.1, range -10 to 10 step 0.1; ADX threshold defaults 20, range 0–100 step 1. Volatility/regime filters default on; ADX filter off.
- Kernel lookback defaults 8, minimum 3, recommended 3–50. Relative weighting defaults 8, step 0.25, recommended 0.25–25. Regression start defaults 25, recommended 0–25. Recommendations are not validation or additional defaults.
- Trade with kernel, show kernel estimate, bar colors, prediction integers and backtest results default on. Show exits, dynamic exits and ATR offset default off. Prediction offset defaults 0 with minimum 0.

## Failure modes and caveats

- Distance-metric results on general classification datasets do not prove financial profitability. Displayed backtest statistics need leakage-free labels,costs and execution assumptions; the source delegates ANN details to unavailable comments.

## Missing information and implementation boundary

- Lorentzian equation,feature normalization/periods,ANN sampling/order,training labels/horizon,filter equations,kernel formula and exit logic are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports local calculations; external input requirements are stated separately.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Neighbors Count - This has a default value of 8
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Max Bars Back - This has a default value of 2000.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Feature Count - This has a default value of 5
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Regime Threshold - This has a default value of -0.1
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
ADX Threshold - This has a default value of 20
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Lookback Window - This has a default value of 8
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Relative Weighting - This has a default value of 8
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Start Regression at Bar - This has a default value of 25
```

### E9: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Source - This has a default value of "hlc3"
```

### E10: mechanism, parameters, readiness

```text
a minimum value of 1, a maximum value of 100, and a step of 1
```

### E11: mechanism, parameters, readiness

```text
a minimum value of 2, and a maximum value of 5
```

### E12: mechanism, parameters, readiness

```text
Color Compression - This has a default value of 1, a minimum value of 1, and a maximum value of 10.
```

### E13: mechanism, parameters, readiness

```text
the second parameter will default to EMA-based smoothing with a default value of 1.
```

### E14: mechanism, parameters, readiness

```text
a minimum value of -10, a maximum value of 10, and a step of 0.1
```

### E15: mechanism, parameters, readiness

```text
a minimum value of 0, a maximum value of 100, and a step of 1
```

### E16: mechanism, parameters, readiness

```text
Lookback Window - This has a default value of 8 and a minimum value of 3.
```

### E17: mechanism, parameters, readiness

```text
Recommended range: 3-50
```

### E18: mechanism, parameters, readiness

```text
Relative Weighting - This has a default value of 8 and a step size of 0.25.
```

### E19: mechanism, parameters, readiness

```text
Recommended range: 0.25-25
```

### E20: mechanism, parameters, readiness

```text
Recommended range: 0-25
```

### E21: mechanism, parameters, readiness

```text
Show Backtest Results - This has a default value of true.
```

### E22: mechanism, parameters, readiness

```text
Show Bar Colors - This has a default value of true.
```

### E23: mechanism, parameters, readiness

```text
Show Bar Prediction Values - This has a default value of true.
```

### E24: mechanism, parameters, readiness

```text
Use ATR Offset - This has a default value of false.
```

### E25: mechanism, parameters, readiness

```text
Bar Prediction Offset - This has a default value of 0 and a minimum value of 0.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_whbzgfdu_machine_learning_lorentzian_classification](../tv_whbzgfdu_machine_learning_lorentzian_classification.md)

## Source

https://www.tradingview.com/script/WhBzgfDu-Machine-Learning-Lorentzian-Classification/

Publication ID: WhBzgfDu. Source SHA-256: bbfca9c0ddb904bbd2ec9da1480bd39f203e09b39b496f57a6008111e62a3a04. Raw-description SHA-256: f47b853e4f2443afa96f9c204034a8c0f4a4e1e033b168a60e2a32675662a20c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
