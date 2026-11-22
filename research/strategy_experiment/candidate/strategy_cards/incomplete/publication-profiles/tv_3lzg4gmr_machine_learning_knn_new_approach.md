---

id: tv_profile_3lzg4gmr

name: "Machine Learning: kNN (New Approach)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Explore nearest-neighbor price prediction and a moving-average-like curve using historical prices directly, without constructing a separate technical-indicator feature vector."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning: kNN (New Approach)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Explore nearest-neighbor price prediction and a moving-average-like curve using historical prices directly, without constructing a separate technical-indicator feature vector.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The modification, exact relationship of N to K, default target indexing and prevention of target leakage are unclear. Training-window size and execution rules are absent.

- The modification, exact relationship of N to K, default target indexing and prevention of target leakage are unclear. Training-window size and execution rules are absent.

## How it works

- Build training examples from consecutive prices, compare an instance with historical samples using absolute distance, rank those distances and average the selected neighbors.
- The author says the implementation modifies the original procedure and can also suggest next-bar direction. This is an explanatory prediction study, not a disclosed complete trading system.

## Outputs and intended use

- Inspect the smoothed prediction curve and proposed direction as exploratory context. Similarity to a moving average is an author observation, not evidence of forecast accuracy.

## Parameters and stated settings

- K controls neighbor count. The text gives a consecutive-price training example and says its modified curve at approximately N=17 resembles sma(20).
- The stated default uses ten predictor points and the sixth as prediction value, which conflicts with the earlier next-bar target explanation.

## Failure modes and caveats

- Nearest-neighbor forecasts can be sensitive to scale, changing regimes and the selected training window. A smooth fitted curve need not predict unseen prices.

## Missing information and implementation boundary

- The modification, exact relationship of N to K, default target indexing and prevention of target leakage are unclear. Training-window size and execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature can use ordinary chart price/volume history; this is input-class availability, not verified code or market-history coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The input data is just a long series of prices over time without any particular features.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
2. Calculate the distance between the instance and all the training samples. As we are  dealing with one-dimensional distance, we simply take absolute value from the instance to  value of x (| x – v |).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
By default, shown are only 10 initial data points as predictor values and the 6th as the prediction value.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The original logic of the algorithm was slightly modified, and as a result at approx. N=17 the resulting curve nicely approximates that of the sma(20).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_3lzg4gmr_machine_learning_knn_new_approach](../tv_3lzg4gmr_machine_learning_knn_new_approach.md)
- [tv_method_knn_prediction](../tv_method_knn_prediction.md)

## Source

https://www.tradingview.com/script/3lZg4gmr-Machine-Learning-kNN-New-Approach/

Publication ID: 3lZg4gmr. Source SHA-256: 6a16605dc3ef88d83d976588b8f51d99c525cde9b28a8f2aebcec3fa40371a25. Raw-description SHA-256: 27bd321eb1b32e7a70e9d2be99cf5db1b3b84fbc7059929ddf7beccc716980fa.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
