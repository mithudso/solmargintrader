---

id: tv_profile_cbnacnmq

name: "Volume and Price Z-Score [Multi-Asset] - By Leviathan"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume and Price Z-Score screens assets by how unusual current price and activity are relative to their own histories and, optionally, relative to the group. It distinguishes a single-bar anomaly from persistent averaged deviations and cross-sectional outliers. Multiple displays let the reader compare price-volume alignment, divergence and unusual participation without imposing one trade interpretation. The source correctly notes that financial price and volume are generally not normally distributed, so standardized distances should not be converted into normal-theory probabilities. OBV mode changes the question from activity magnitude to a cumulative directional-volume proxy."

registry_key: null

runner: null

evaluation: null

---

# Volume and Price Z-Score [Multi-Asset] - By Leviathan

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume and Price Z-Score screens assets by how unusual current price and activity are relative to their own histories and, optionally, relative to the group. It distinguishes a single-bar anomaly from persistent averaged deviations and cross-sectional outliers. Multiple displays let the reader compare price-volume alignment, divergence and unusual participation without imposing one trade interpretation. The source correctly notes that financial price and volume are generally not normally distributed, so standardized distances should not be converted into normal-theory probabilities. OBV mode changes the question from activity magnitude to a cumulative directional-volume proxy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for ordinary Current/Average price and regular-volume z-scores and price-minus-volume delta with a chosen averaging length and default 20-bar normalization window. Relative-group normalization and exact variance convention remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For ordinary Current mode, calculate each selected price or regular-volume observation minus its rolling mean, divided by the corresponding rolling standard deviation, over the chosen lookback (default 20 bars). Average mode takes the custom-length average of that z-score series. Delta equals price z-score minus volume z-score. Dispersion sample convention and zero-dispersion handling remain caveats.
- Relative mode standardizes a symbol’s z-score against group z-score behavior, although its exact denominator is not given.
- Choose regular volume or OBV and optionally subtract volume z-score from price z-score.

## Outputs and intended use

- Scatterplot maps price z-score horizontally and volume vertically; squares guide standardized distance.
- Paired columns/circles, delta columns and history heatmaps expose cross-asset anomalies and alignment.

## Parameters and stated settings

- Advertised coverage is 200 symbols; current z-score mean lookback defaults to 20 bars.
- Current, Average and Relative modes, custom averaging length, volume/OBV, display type and heatmap gradient are selectable.
- Scatter guides use ±1/2/3 SD; column/circle display range is described as -4 to 4.

## Failure modes and caveats

- Cross-sectional outliers depend on universe selection and aligned timestamps.
- OBV is a candle-direction proxy; price-volume convergence is not causal proof or a guaranteed signal.

## Missing information and implementation boundary

- Symbol universe, dispersion conventions, relative-mode formula, zero-variance handling, OBV initialization and order rules are missing.

## Data requirements

Required inputs: multi-asset OHLCV histories, selected symbol universe.

Repository input-class support: unavailable or unresolved. The multi-symbol presentation needs caller-selected aligned OHLCV histories; cache coverage is unestablished. A changing historical-membership universe is not required for the independently defined per-symbol ordinary z-scores.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, purpose

```text
for 200 symbols.
```

### E2: parameters

```text
default is 20 bars
```

### E3: risks

```text
Datasets like price and volume (in this context) are most often not normally distributed.
```

### E4: parameters

```text
between -4 and 4
```

### E5: parameters

```text
within ±1 standard deviation
```

### E6: parameters

```text
within ±2 standard deviations
```

### E7: parameters

```text
within ±3 standard deviations
```

### E8: mechanism, readiness

```text
difference between the z-score of price and the z-score of volume.
```

### E9: mechanism, readiness

```text
A Z-Score is a statistical measurement indicating the number of standard deviations a data point deviates from the dataset's mean.
```

### E10: mechanism, parameters

```text
mean (moving average with any custom length, default is 20 bars).
```

### E11: mechanism, readiness

```text
Calculates the custom-length average of symbol's z-score.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cbnacnmq_volume_and_price_z_score_multi_asset_by_leviathan](../tv_cbnacnmq_volume_and_price_z_score_multi_asset_by_leviathan.md)

## Source

https://www.tradingview.com/script/CBnACnmq-Volume-and-Price-Z-Score-Multi-Asset-By-Leviathan/

Publication ID: CBnACnmq. Source SHA-256: 27320f1da8d69e8657f7c6e850d7fa2b484817cc7f7690110af6452ebb48ed61. Raw-description SHA-256: 3ab1a74bc3fe682c5a001be10ec7bb355ed4a54b3388ab6e78026cba2ba5bb48.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
