---

id: tv_profile_sr0scav5

name: "Wavelet-Trend ML Integration [Alpha Extract]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "The saved title says Wavelet-Trend ML Integration, but the complete description instead documents Alpha-Extract Volatility Quality. It describes signed true-range momentum smoothed with two EMAs, optional range normalization and deviation bands. The mismatch prevents confidently identifying the publication’s actual implemented algorithm, and the normalized extreme thresholds contradict the printed bounded normalization."

registry_key: null

runner: null

evaluation: null

---

# Wavelet-Trend ML Integration [Alpha Extract]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

The saved title says Wavelet-Trend ML Integration, but the complete description instead documents Alpha-Extract Volatility Quality. It describes signed true-range momentum smoothed with two EMAs, optional range normalization and deviation bands. The mismatch prevents confidently identifying the publication’s actual implemented algorithm, and the normalized extreme thresholds contradict the printed bounded normalization.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Unnormalized signed-TR double EMA and bands is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Sign true range by candle direction, apply EMA then another EMA, and optionally map the result with historical min/max to a centered scale.
- Construct deviation envelopes around smoothed VQI and flag purported extreme levels; no wavelet or trained model is explained.
- TR=max(high-low,abs(high-prevClose),abs(low-prevClose));weighted=TR*sign(close-open),with doji sign0. Raw=EMA(weighted,VQILength);smoothed=EMA(raw,SmoothingLength). For each supplied multiplier m,bands=smoothed±m*StdDev(smoothed,VQILength). Caller chooses lengths/multipliers/variance convention. Title mismatch and normalized±200 threshold contradiction remain explicit;normalized signals excluded.

## Outputs and intended use

- Read positive/negative VQI, zero crosses, colored candles and optional extreme markers as volatility-momentum context, subject to the identity contradiction.
- Usable scope: Unnormalized signed-TR double EMA and bands. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- VQI length defaults 14, smoothing 5, band multipliers 1/2/3 and normalization lookback 200 minimum 50. Source states normalized scale -100/+100 but signals at ±200.

## Failure modes and caveats

- Analytical: in-window min/max normalization as printed cannot normally reach the advertised ±200 thresholds; title/description mismatch is a core source-quality issue.

## Missing information and implementation boundary

- Actual script identity, normalization/signal mismatch, min/max sample alignment and whether any wavelet/ML behavior exists are unresolved.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, missing_information, readiness

```text
Alpha-Extract Volatility Quality Indicator
```

### E2: mechanism, risks, readiness

```text
VQI Normalized = ((VQI Smoothed - Lowest VQI) / (Highest VQI - Lowest VQI) - 0.5) × 200
```

### E3: parameters, readiness

```text
default: 14
```

### E4: parameters, readiness

```text
default: 5
```

### E5: parameters, readiness

```text
defaults: 1.0, 2.0, 3.0
```

### E6: parameters, readiness

```text
default: 200, min: 50
```

### E7: parameters, risks, readiness

```text
VQI ≥ 200 (Normalized)
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[*]Weighted Volatility = Bar Range × (Close > Open ? 1 : Close < Open ? -1 : 0)
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
[*]VQI Raw = EMA(Weighted Volatility, VQI Length)
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[*]VQI Smoothed = EMA(VQI Raw, Smoothing Length)
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
[*]Upper Band N = VQI Smoothed + (StdDev(VQI Smoothed, VQI Length) × Multiplier N)
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
[*]Lower Band N = VQI Smoothed - (StdDev(VQI Smoothed, VQI Length) × Multiplier N)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_sr0scav5_wavelet_trend_ml_integration_alpha_extract](../tv_sr0scav5_wavelet_trend_ml_integration_alpha_extract.md)

## Source

https://www.tradingview.com/script/sr0scAV5-Wavelet-Trend-ML-Integration-Alpha-Extract/

Publication ID: sr0scAV5. Source SHA-256: 09467305cf0fbe9d583803e6641713da02eeb7d8f8afb039abc06ae6a5b724bd. Raw-description SHA-256: 1a324195c96c39b8d5320a98e18db8b34da32874e2c7bfbd047b522b41418ee3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
