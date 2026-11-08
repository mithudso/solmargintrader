---

id: tv_profile_3xe8qqfr

name: "Directional Volume Shapes (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Classify the recent shape of estimated directional candle pressure, then display an idealized volume-scaled template of that regime. The visible columns are synthesized representations, so they should not be mistaken for observed buy/sell volume."

registry_key: null

runner: null

evaluation: null

---

# Directional Volume Shapes (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Classify the recent shape of estimated directional candle pressure, then display an idealized volume-scaled template of that regime. The visible columns are synthesized representations, so they should not be mistaken for observed buy/sell volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The candle scorer, Gaussian smoothing/peak algorithm and complete template equations are not supplied.

- The candle scorer, Gaussian smoothing/peak algorithm and complete template equations are not supplied.

## How it works

- A triangular-distribution candle scorer returns a bounded value, transformed into signed pressure; optional raw-volume weighting affects classification. Absolute magnitudes remove direction before skewness, smoothed peaks and temporal correlation determine the shape.
- Classification priority is multiple peaks, rising/falling correlation, signed skewness, then Bell. Five successive classifications differing from the current shape trigger a switch even when those alternatives differ from each other.
- Separately, an EMA of signed pressure determines bullish/bearish polarity. A template advances through a fixed cycle, reverses phase with polarity, and scales by recent average volume.

## Outputs and intended use

- Columns and shape labels show the pressure regime; the author proposes price divergences and zero-side readings.
- Optional moving average smooths the final synthesized output, rather than the original pressure observations.

## Parameters and stated settings

- Detection window, volume weighting, polarity EMA length, template cycle, optional SMA/EMA/RMA/WMA and display transparency.
- Classifier thresholds use correlation ±0.5 and skewness ±0.1; prominence exceeds 10% of the smoothed maximum. Output amplitude uses a three-bar volume SMA multiplied by 1.8.

## Failure modes and caveats

- Triangular candle activity is an approximation without intrabar observations. Fixed thresholds have no significance test.
- Template phase and volume scaling can create apparent divergences unrelated to changes in the underlying pressure magnitudes.

## Missing information and implementation boundary

- The candle scorer, Gaussian smoothing/peak algorithm and complete template equations are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Standard historical OHLCV supplies the market-data class; this does not establish source-code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
ps = 2.0 * dm - 1.0
```

### E2: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
if peaks >= 2
    out := peaks == 2 ? "Bimodal" : "Multimodal"
```

### E3: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
• Skewness thresholds of ±0.1
• Correlation thresholds of ±0.5
• Peak prominence above 10% of the smoothed envelope’s maximum
```

### E4: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
amp = ta.sma(volume, 3) * 1.8
```

### E5: purpose, mechanism, outputs_and_use, parameters, missing_information, readiness

```text
The five classifications do not need to match each other.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_3xe8qqfr_directional_volume_shapes_zeiierman](../tv_3xe8qqfr_directional_volume_shapes_zeiierman.md)
- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)

## Source

https://www.tradingview.com/script/3XE8qqfr-Directional-Volume-Shapes-Zeiierman/

Publication ID: 3XE8qqfr. Source SHA-256: 69ab3509ac3dd092cd0676796057d1888bfe3fc366f2f87918824e17d2f9075d. Raw-description SHA-256: 14ec6d8ff3005d833180f0b6f45d9c2b06c51012a45523f3ca9f242208475a8d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
