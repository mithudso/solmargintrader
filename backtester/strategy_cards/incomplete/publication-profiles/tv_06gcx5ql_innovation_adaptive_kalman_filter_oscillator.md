---

id: tv_profile_06gcx5ql

name: "Innovation Adaptive Kalman Filter Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Identify unusual price innovations and show when an adaptive Kalman filter deliberately reduces its response to those observations."

registry_key: null

runner: null

evaluation: null

---

# Innovation Adaptive Kalman Filter Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Identify unusual price innovations and show when an adaptive Kalman filter deliberately reduces its response to those observations.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Detection/display boundaries are detailed,but the core adaptive Kalman/noise and meter equations are not reproducible.

- Kalman prediction/covariance/update equations
- Noise baseline/adaptation and meter mappings
- Smoothness parameter mapping

## How it works

- Compare source with the prior prediction,optionally remove mean trend error,learn a normal error baseline and gate unusually large innovations by adding error-dependent measurement noise. Show recent error-variance Surprise and relative-response Damping along with filtered price direction.

## Outputs and intended use

- Blue Surprise and downward gray Damping distinguish ordinary noise,single outliers and clustered changes. Halos/dots flag unusual observations,not buy/sell cues. State/readout/shading explain filter behavior; combined alerts occur at bar close.

## Parameters and stated settings

- Source defaults close,trend centering on,unusual threshold2.05,added-noise scale0.05 and color hold0.25. Shift starts with both meters30,settles when either below20 and ends when both below10. Surprise50means2×variance,75means4×. Halos retain100events.
- Major Unusual Move >= twice Unusual-Move Threshold; Moves Clustering at three unusual moves within Noise Lookback before volatility shift. Halo defaults on, price dots off, pane dots on. Halos retain 100 moves; dots and halo-hover labels share 500-label budget, about 250 events under defaults; price dots consume another label per move.

## Failure modes and caveats

- Damping can slow adaptation to a genuine structural price change. Surprise multiples concern variance,not single-price movement. Engineering analogy/research does not establish financial forecast quality; drawing/label limits restrict history.

## Missing information and implementation boundary

- Prediction/state/covariance recurrences,noise-baseline estimator,meter transforms,fade/reset policy and period-like smoothness mapping are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supports the local-input class; missing formulas are specification gaps rather than missing market history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default value of 2.05
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
adds 0.05 times the squared error
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The default is 0.25.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
both meters reach 30
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
both meters fall below 10
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
either meter falls below 20
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
50 corresponds to twice the normal level, and 75 corresponds to four times
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Only the most recent 100 halos are retained.
```

### E9: mechanism, parameters, readiness

```text
A Major Unusual Move reaches at least twice the Unusual-Move Threshold. Moves Clustering identifies when the count reaches three unusual moves within Noise Lookback, before a volatility shift has started.
```

### E10: mechanism, parameters, readiness

```text
Dots and the invisible labels used for halo hover information share TradingView’s 500-label limit. With the default settings, approximately the most recent 250 unusual moves retain their dots and hover information.
```

### E11: mechanism, parameters, readiness

```text
Enabled by default, with halos retained for the most recent 100 unusual moves.
```

### E12: mechanism, parameters, readiness

```text
Disabled by default. The dots and halos can be enabled independently.
```

### E13: mechanism, parameters, readiness

```text
Enabled by default. These provide the same hover information
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator](../tv_06gcx5ql_innovation_adaptive_kalman_filter_oscillator.md)
- [tv_method_kalman_filter](../tv_method_kalman_filter.md)

## Source

https://www.tradingview.com/script/06GCx5qL-Innovation-Adaptive-Kalman-Filter-Oscillator/

Publication ID: 06GCx5qL. Source SHA-256: cf69046fe2097f836a62f3dea9396358ea2d520e4241db9012e9a27332cfbb05. Raw-description SHA-256: 0beb4a1265a76087f23e5a8d62933ae7f9fa09b06dd99b512f08aa12468260fe.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
