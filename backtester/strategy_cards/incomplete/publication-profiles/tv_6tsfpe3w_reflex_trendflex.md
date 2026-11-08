---

id: tv_profile_6tsfpe3w

name: "Reflex & Trendflex"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Separate smoothed price behavior into cycle-like and trend-like deviation oscillators with adaptable extreme bands."

registry_key: null

runner: null

evaluation: null

---

# Reflex & Trendflex

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Separate smoothed price behavior into cycle-like and trend-like deviation oscillators with adaptable extreme bands.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Important normalization/defaults are given, but the core filter and Reflex slope/deviation contract are not fully specified.

- SuperSmoother recurrence and initialization
- Reflex slope versus regression definition
- Threshold centering/normalization equations

## How it works

- Filter prices with SuperSmoother, compare its history against a fitted/end-to-end slope for Reflex and against the current filtered value for Trendflex. Normalize raw deviations using an exponentially weighted squared-deviation state, then optionally form MAD, standard-deviation or percentile thresholds.

## Outputs and intended use

- Use zero/sign changes for cycle/trend context and disagreements for caution. Six alerts are described as bar-close only. The source later clarifies near-zero rather than literally zero lag and warns of normalization artifacts.

## Parameters and stated settings

- Both oscillator periods default twenty within5-50. Threshold period defaults fifty within2-200, multiplier1.5, percentile90 and MAD mode default. Normalization state weights are0.04/0.96.

## Failure modes and caveats

- Quiet data can amplify noise and gaps disrupt filter continuity. The text calls Reflex comparison linear regression while also describing a slope over lookback; those are not necessarily the same computation.

## Missing information and implementation boundary

- Exact SuperSmoother recurrence, Reflex slope/sum normalization, initialization and detailed threshold equations are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV, including selected lower-timeframe history, supports the described data class. Missing computation details are separate specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
rms = 0.04 * deviation² + 0.96 * rms[1]
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Reflex Period[/b] (5-50)
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default 20.
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Default 50.
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
default 1.5
```

### E6: purpose, mechanism, outputs_and_use, parameters, readiness

```text
default 90%
```

### E7: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Near-zero lag, not zero-lag
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6tsfpe3w_reflex_trendflex](../tv_6tsfpe3w_reflex_trendflex.md)
- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)

## Source

https://www.tradingview.com/script/6tSfPE3W-Reflex-Trendflex/

Publication ID: 6tSfPE3W. Source SHA-256: 9d3ca3bf5c6050284586d02628c542fa3c26ad253237d22de4a93346584eb83f. Raw-description SHA-256: 6716ec8b294ba380e1fa2490109c40a02db9e92f7372510533b70d2641e91219.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
