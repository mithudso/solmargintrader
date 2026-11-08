---

id: tv_profile_jcrhuirl

name: "Tensor Market Analysis Engine (TMAE)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Tensor Market Analysis Engine proposes a composite of multidimensional volatility jumps, Hurst-style regime detection and transfer-entropy-like information flow. It aims to choose context-dependent signals and express them through a heavily decorated dashboard and chart layers. Long/short confirmation uses momentum, while voting modes change how many components must agree. The long description includes mathematical sketches and many suggested tunings, but no complete estimator implementation. Quantum/tensor/category-theory branding and first-ever assertions do not establish mathematical validity or trading performance. Estimated win-rate labels are explicitly estimates, not demonstrated trade outcomes."

registry_key: null

runner: null

evaluation: null

---

# Tensor Market Analysis Engine (TMAE)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Tensor Market Analysis Engine proposes a composite of multidimensional volatility jumps, Hurst-style regime detection and transfer-entropy-like information flow. It aims to choose context-dependent signals and express them through a heavily decorated dashboard and chart layers. Long/short confirmation uses momentum, while voting modes change how many components must agree. The long description includes mathematical sketches and many suggested tunings, but no complete estimator implementation. Quantum/tensor/category-theory branding and first-ever assertions do not establish mathematical validity or trading performance. Estimated win-rate labels are explicitly estimates, not demonstrated trade outcomes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core multivariate/entropy/Hurst estimators and component/state predicates are not specified sufficiently to reproduce the engine.

## How it works

- Estimate volatility-state distance and jump clustering through a Hawkes approximation.
- Classify persistence from R/S-like Hurst estimates with hysteresis; estimate directional information flow across lags.
- Combine component votes with RSI/EMA confirmation and spacing; show fractal/pressure levels and optional position-size guidance.

## Outputs and intended use

- Fields, regime markers, information streams, fractal levels, long/short states, quality/estimated-performance dashboard and exit cues support experimental context analysis.

## Parameters and stated settings

- Defaults: window50, sensitivity0.7, dimensions3, jump threshold3σ, decay0.85, trend/reversion thresholds0.60/0.40, lag5 and entropy threshold0.15.
- Long confirmation RSI>50 and price>EMA9; minimum signal spacing five bars.
- Fractal periods8/13/21/34/55; position-size formula scales base by threshold/distance.

## Failure modes and caveats

- Transfer entropy is predictive dependence, not proof of economic causation.
- A short-window Hurst estimate does not establish optimal strategy class; regime labels are conflated with direction.
- Approximate estimated win rates and promotional assertions are not validated measurements.

## Missing information and implementation boundary

- Covariance stabilization, Hawkes recursion, entropy discretization, Hurst adaptation, component direction, persistence/exit rules and defaults beyond selected controls are absent.

## Data requirements

Required inputs: ohlcv, lower-timeframe/cross-timeframe data in selected modes.

Repository input-class support: unavailable or unresolved. Basic inputs are chart-derived, but optional microstructure/MTF contracts and actual coverage are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Default: 50
```

### E2: parameters

```text
Default: 0.7
```

### E3: parameters

```text
Default: 3)
```

### E4: parameters

```text
Default: 3.0σ
```

### E5: parameters

```text
Default: 0.85
```

### E6: parameters

```text
Default: 0.60
```

### E7: parameters

```text
Default: 0.40
```

### E8: parameters

```text
Default: 5)
```

### E9: parameters

```text
Default: 0.15
```

### E10: parameters

```text
RSI >50 AND price >EMA-9
```

### E11: parameters

```text
Minimum 5-bar spacing
```

### E12: parameters

```text
8-Period
```

### E13: parameters

```text
13-Period
```

### E14: parameters

```text
21-Period
```

### E15: parameters

```text
34-Period
```

### E16: parameters

```text
55-Period
```

### E17: mechanism

```text
Position Size = Base Size × (Threshold / Mahalanobis Distance)
```

### E18: mechanism, readiness

```text
H = log(R/S) / log(n)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jcrhuirl_tensor_market_analysis_engine_tmae](../tv_jcrhuirl_tensor_market_analysis_engine_tmae.md)
- [tv_method_intermarket_correlation](../../../strategy_research/tv_method_intermarket_correlation.md)
- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_trailing_stop](../../../strategy_research/tv_method_trailing_stop.md)

## Source

https://www.tradingview.com/script/jcRhuIRl-Tensor-Market-Analysis-Engine-TMAE/

Publication ID: jcRhuIRl. Source SHA-256: f4a3f6743e8d738d63df5641c3a326823b9a4dcae6589f0e9d7d52fc45b38424. Raw-description SHA-256: 558185b4f929839214692ede8a513c1557193f679a7996becce8ba7379d5e0e6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
