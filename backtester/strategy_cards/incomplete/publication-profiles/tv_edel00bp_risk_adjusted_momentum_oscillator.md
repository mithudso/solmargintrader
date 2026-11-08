---

id: tv_profile_edel00bp

name: "Risk-Adjusted Momentum Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dampen momentum according to a drawdown-based risk context, then combine normalization, adaptive smoothing and leading-style components. RAMO aims to make momentum signals risk-aware; its broad literature claims do not establish the indicator’s own empirical advantages."

registry_key: null

runner: null

evaluation: null

---

# Risk-Adjusted Momentum Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dampen momentum according to a drawdown-based risk context, then combine normalization, adaptive smoothing and leading-style components. RAMO aims to make momentum signals risk-aware; its broad literature claims do not establish the indicator’s own empirical advantages.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Drawdown source/window, normalization order, volatility definition, parameter defaults and exact layered signal conditions are unspecified.

- Drawdown source/window, normalization order, volatility definition, parameter defaults and exact layered signal conditions are unspecified.

## How it works

- Raw momentum may be rate of change, absolute difference or log return. A factor equal to one minus scaled current/max drawdown multiplies momentum, floored to retain a small fraction.
- Z-score normalization clips extreme values. Volatility percentile interpolates EMA alpha, while mean/standard-deviation bands create adaptive thresholds.
- Auxiliary components include EMA-smoothed lagged momentum difference, forward linear-regression extrapolation and an exhaustion flag combining extreme momentum with below-average volume. Crossovers, risk regime and these components inform signal interpretation.

## Outputs and intended use

- Oscillator/signal crosses, risk state, divergence and exhaustion context are described for discretionary confirmation.
- The prose claims automatic position reduction but provides only signal damping equations; an actual portfolio sizing rule cannot be inferred.

## Parameters and stated settings

- Risk factor floor 0.05; normalized scores clipped at ±3.5. Exhaustion volume reference uses 20 bars and volatility percentile 100 observations.
- Risk regimes divide current/max drawdown at 30% and 70%; scaling, lengths, thresholds and alpha bounds are not given concrete defaults.

## Failure modes and caveats

- Zero maximum drawdown requires a guard. Clipping and damping alter amplitude and can delay or suppress valid momentum.
- The stated acceleration is a lagged first difference of momentum, despite the prose calling it a second derivative. Prediction extrapolation does not guarantee leading accuracy.

## Missing information and implementation boundary

- Drawdown source/window, normalization order, volatility definition, parameter defaults and exact layered signal conditions are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supplies the described price/volume data class; unidentified drawdown or algorithm semantics remain specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Risk_Factor = 1 - (Current_Drawdown / Maximum_Drawdown × Scaling_Factor)
Risk_Adjusted_Momentum = Raw_Momentum × max(Risk_Factor, 0.05)
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Normalized_Value = max(-3.5, min(3.5, Z_Score))
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Exhaustion = |Momentum| > Threshold AND Volume < SMA(Volume, 20)
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Volatility_Percentile = Percentrank(Volatility, 100)
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
- Low Risk: Current_DD < 30% × Max_DD
```

### E6: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
- High Risk: Current_DD ≥ 70% × Max_DD
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_edel00bp_risk_adjusted_momentum_oscillator](../tv_edel00bp_risk_adjusted_momentum_oscillator.md)
- [tv_method_elliott_wave](../tv_method_elliott_wave.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/EdEL00bP-Risk-Adjusted-Momentum-Oscillator/

Publication ID: EdEL00bP. Source SHA-256: 58e194438018ef44eb569a46ffef759d2ddd6c50dd50dc9980c65a2f3c510190. Raw-description SHA-256: 3d29d0bbea165ad56908c472f92bb53334bbd94fd47690b747f082aba79f9ff3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
