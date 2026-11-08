---

id: tv_profile_vrtl3vwf

name: "Machine Learning RSI | AI Classification & Ranking (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Machine Learning RSI classifies the current momentum environment by matching a multidimensional RSI fingerprint to historical labeled analogs. It aims to replace a simple threshold interpretation with adaptive feature importance, distance-weighted votes and quality gates. The learned conviction also changes Supertrend width. The source clarifies this is an online analog classifier, not a neural network. It provides several component equations, but ranking/confidence functions and causal label maturation are not fully specified. Confirmed-bar signals alone do not prove absence of future-label leakage."

registry_key: null

runner: null

evaluation: null

---

# Machine Learning RSI | AI Classification & Ranking (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Machine Learning RSI classifies the current momentum environment by matching a multidimensional RSI fingerprint to historical labeled analogs. It aims to replace a simple threshold interpretation with adaptive feature importance, distance-weighted votes and quality gates. The learned conviction also changes Supertrend width. The source clarifies this is an online analog classifier, not a neural network. It provides several component equations, but ranking/confidence functions and causal label maturation are not fully specified. Confirmed-bar signals alone do not prove absence of future-label leakage.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core rank/confidence and normalization functions plus outcome maturation/causal exclusion rules are missing.

## How it works

- Build RSI level, slope, acceleration, neutral distance, percentile, volatility, fast/slow spread and regime features.
- Store historical features with ATR-scaled outcome classes; compare using weighted log(1+absolute difference) distances and inverse-gap votes.
- Adapt weights using squared class-mean separation over summed class variances; gate signals by rank/confidence and modulate Supertrend multiplier with conviction.

## Outputs and intended use

- ML RSI, long/short marks, adaptive Supertrend/cloud, candle colors and signal line support momentum/regime research.

## Parameters and stated settings

- Eight features; RSI output 0–100 with midpoint 50 and illustrative 70/30 strong-pressure levels.
- Feature examples include RSI dispersion 14 and regime EMA20; outcome classes range -3..3 by zero/one/two-band move thresholds.
- Source, RSI length, memory, k, ranks/confidence, filters, weighting, Supertrend and smoothing controls are configurable.

## Failure modes and caveats

- Analog relevance depends on regime and memory; fitted feature weights can overfit.
- Confidence is an internal score, not established probability.
- Future outcomes require delayed insertion, whose exact implementation is absent.

## Missing information and implementation boundary

- scale01, rank/confidence, label horizon/maturation, neighbor exclusions, defaults and full state transitions are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. RSI features, ATR outcomes and Supertrend use OHLCV; exact causal pipeline remains an algorithm gap.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
8-feature market fingerprint
```

### E2: parameters

```text
ranges from 0 to 100.
```

### E3: parameters

```text
Values above 50
```

### E4: parameters

```text
above 70
```

### E5: parameters

```text
below 30
```

### E6: parameters

```text
ta.stdev(rOsc, 14)
```

### E7: parameters

```text
ta.ema(rOsc, 20)
```

### E8: parameters, mechanism

```text
moveFwd > 2 * bandFwd ? 3 :
```

### E9: parameters

```text
moveFwd < -2 * bandFwd ? -3 :
```

### E10: readiness

```text
setup.rank := rankScore(…)
setup.conf := confScore(…)
```

### E11: mechanism

```text
float w = 1.0 / (1.0 + n.gap)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_neural_prediction](../tv_method_neural_prediction.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)
- [tv_vrtl3vwf_machine_learning_rsi_ai_classification_ranking_zeiierman](../tv_vrtl3vwf_machine_learning_rsi_ai_classification_ranking_zeiierman.md)

## Source

https://www.tradingview.com/script/VrTL3VwF-Machine-Learning-RSI-AI-Classification-Ranking-Zeiierman/

Publication ID: VrTL3VwF. Source SHA-256: 02a88162ebe4b80e1e316c7eb7d6ad8f86cf227d04737db5fd4aacdfa43f6be6. Raw-description SHA-256: 7b746cffe0e8a775747ec6a6461e6450f6368973548d229bb4239f57d5737a8c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
