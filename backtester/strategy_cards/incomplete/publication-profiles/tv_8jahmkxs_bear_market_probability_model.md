---

id: tv_profile_8jahmkxs

name: "Bear Market Probability Model"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Combine macroeconomic,technical,sentiment and breadth stress proxies into a weighted systemic-risk score labeled bear-market probability."

registry_key: null

runner: null

evaluation: null

---

# Bear Market Probability Model

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine macroeconomic,technical,sentiment and breadth stress proxies into a weighted systemic-risk score labeled bear-market probability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The composite skeleton lacks factor scoring/weights and its required external-series contracts; probability calibration is not defined.

- Factor equations/normalization and category weights
- External market/macro/breadth histories with release timing
- Threshold and bear-event calibration

## How it works

- Normalize category scores and average by category weight. Inputs include Treasury curve spreads,high-yield credit stress,DXY/gold-oil,price averages/MACD/RSI/drawdown,VIX/put-call and advance-decline/new-high-low measures; adapt warning/danger thresholds with volatility.

## Outputs and intended use

- Use component/table risk context for discretionary exposure or hedging review. A weighted score is not a calibrated probability without outcome definition and validation; cited research on individual factors does not validate this composite.

## Parameters and stated settings

- Thirteen factors/four categories are claimed. Credit references350/500 basis points,VIX20/25/30,MA50/200 and McClellan EMA19-minus39 are disclosed. Dynamic warning/danger scales1/1.5 with stated10-20point bounds; actual weights/defaults are absent.

## Failure modes and caveats

- US bias,lagged/revised economic releases,correlated stress inputs,false positives and regime changes limit interpretation. The bibliography includes broad claims not independently verified here.

## Missing information and implementation boundary

- Factor normalization/weights,data tickers/lag alignment,base thresholds,volatility estimator,bear-event/horizon definition and probability calibration are missing.

## Data requirements

Required inputs: Treasury yields and high-yield OAS, DXY/gold/oil/VIX/put-call data, point-in-time breadth and market price histories.

Repository input-class support: unavailable or unresolved. The model requires multiple macro/sentiment/breadth feeds and a historical constituent/release contract absent from the saved source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
13 distinct risk factors across four analytical categories
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bear Market Probability = Σ(Wi × Ci) / ΣWi × 100
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Normal conditions: < 350 basis points
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Severe stress: > 500 basis points
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
McClellan Oscillator (Ema19 - Ema39 of A-D difference)
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Warning Level: Base threshold ± (Volatility × 1.0)
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Danger Level: Base threshold ± (Volatility × 1.5)
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bounds: ±10-20 points
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8jahmkxs_bear_market_probability_model](../tv_8jahmkxs_bear_market_probability_model.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/8jAHmKXS-Bear-Market-Probability-Model/

Publication ID: 8jAHmKXS. Source SHA-256: e6528f75df2ad9693c096dd7e4641a5101268f9316b66484e958a8745bef559a. Raw-description SHA-256: 8a5a6c22585bcd8ee38c9f39e2ef3facd3345e68c7a2dad5f52537c5b498674a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
