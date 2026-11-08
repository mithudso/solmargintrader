---

id: tv_profile_bfu1hmks

name: "Neural Weight Oscillator (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Neural Weight Oscillator blends trend, mean-reversion and momentum features using trader preference weights and an optional adaptive layer. Its Best-Worst Method converts relative importance judgments into normalized weights, while historical feature/return pairs adjust feature amplification. The result aims to adapt the oscillator’s emphasis across market conditions, rather than treat every factor equally or demonstrate that a neural label creates predictive accuracy."

registry_key: null

runner: null

evaluation: null

---

# Neural Weight Oscillator (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Neural Weight Oscillator blends trend, mean-reversion and momentum features using trader preference weights and an optional adaptive layer. Its Best-Worst Method converts relative importance judgments into normalized weights, while historical feature/return pairs adjust feature amplification. The result aims to adapt the oscillator’s emphasis across market conditions, rather than treat every factor equally or demonstrate that a neural label creates predictive accuracy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Normalize function, feature lengths, EMA velocity, sample storage/ranking, weight-update learning rate and final blending/clipping are not fully defined.

- Normalize function, feature lengths, EMA velocity, sample storage/ranking, weight-update learning rate and final blending/clipping are not fully defined.

## How it works

- Build ATR-normalized EMA spread/slope for trend, inverted RSI plus negative price Z-score for reversion, and a ROC/RSI/EMA-velocity mixture for momentum.
- Derive relative weights from best/worst comparison inputs using a square-root relationship and normalization.
- Rank delayed feature samples by volatility-adjusted move strength, compare a weighted prediction with observed direction and learn feature amplifiers.

## Outputs and intended use

- Read the bounded oscillator for directional pressure, expansion or possible exhaustion and choose BWM preferences to fit an explicit regime hypothesis.

## Parameters and stated settings

- Output is 0–100 with midpoint 50, expansion examples above 70/below 30 and exhaustion above 80/below 20.
- Controls include fast/slow EMA, smoothing, best/worst relationships, training toggle, Influence and Line Impact; no full default set is supplied.

## Failure modes and caveats

- Analytical: selective high-quality training samples and flexible preferences can overfit; correct delayed-label alignment is essential to avoid future leakage.

## Missing information and implementation boundary

- Normalize function, feature lengths, EMA velocity, sample storage/ranking, weight-update learning rate and final blending/clipping are not fully defined.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
operates between 0 and 100.
```

### E2: parameters, readiness

```text
Values above 50
```

### E3: parameters, readiness

```text
above 70
```

### E4: parameters, readiness

```text
below 30
```

### E5: parameters, readiness

```text
above 80 or below 20
```

### E6: mechanism, readiness

```text
relWeight = math.sqrt((aBW / boVal) * owVal)
```

### E7: mechanism, readiness

```text
pred = twTrend * s.trend + twMean * s.mean + twMomentum * s.momentum + tbias
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bfu1hmks_neural_weight_oscillator_zeiierman](../tv_bfu1hmks_neural_weight_oscillator_zeiierman.md)
- [tv_method_market_structure](../tv_method_market_structure.md)

## Source

https://www.tradingview.com/script/bfu1hmkS-Neural-Weight-Oscillator-Zeiierman/

Publication ID: bfu1hmkS. Source SHA-256: b7b802855b7b9ebd025c8322c0f597983515bf61a64490dd9685318b9124dbb6. Raw-description SHA-256: a839d71d3aeb0ba18b3ac6c528c514c4904384084ea24cd67223b06126b816d7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
