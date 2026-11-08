---

id: tv_profile_sgfm0bj3

name: "Elastic Volume-Weighted Student-T Tension"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Elastic Volume-Weighted Student-T Tension builds adaptive location/dispersion bands and a relative-position oscillator. It aims to account for heavy tails and changing participation rather than assume fixed normal volatility. Volume influences the elastic mean and variance; true range substitutes when volume is unavailable. A higher-timeframe normalization option changes the weighting scale. The source proposes breakout, momentum and mean-reversion interpretations, but these alternatives do not constitute one defined trading rule. The author explicitly labels the included function as testing material."

registry_key: null

runner: null

evaluation: null

---

# Elastic Volume-Weighted Student-T Tension

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Elastic Volume-Weighted Student-T Tension builds adaptive location/dispersion bands and a relative-position oscillator. It aims to account for heavy tails and changing participation rather than assume fixed normal volatility. Volume influences the elastic mean and variance; true range substitutes when volume is unavailable. A higher-timeframe normalization option changes the weighting scale. The source proposes breakout, momentum and mean-reversion interpretations, but these alternatives do not constitute one defined trading rule. The author explicitly labels the included function as testing material.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Elastic weighting and kurtosis-to-degrees-of-freedom/dispersion equations are unspecified.

## How it works

- Update weighted mean and variance incrementally, using volume or fallback true range.
- Estimate Student-t degrees of freedom from kurtosis and adjust dispersion zones.
- Normalize price within the band structure into a percent-B-like oscillator.

## Outputs and intended use

- Bands/clouds and oscillator position show central versus stretched price behavior.

## Parameters and stated settings

- Two custom dispersion zones; example oscillator maps lower -2σ to 0, mean to 0.5 and upper +2σ to 1.
- Fixed alpha decay, HTF volume smoothing, sigma multipliers and fills are configurable. HTF denominator uses the last two closed HTF candles.
- Example HTF choices include 200-day, weekly and monthly.

## Failure modes and caveats

- Estimated tail parameters can be unstable and distributional fitting does not guarantee mean reversion.
- Volume fallback changes the weighting meaning across symbols.
- Developing HTF/session behavior and modified models require validation.

## Missing information and implementation boundary

- Exact elastic-weight recursion, kurtosis/df mapping, Student-t scaling, parameter defaults and fallback normalization are absent.

## Data requirements

Required inputs: ohlcv, higher-timeframe ohlcv when selected.

Repository input-class support: available. Prices, volume and true range are OHLCV-derived; higher-timeframe aggregation is the same data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
0.00 → Price is at the lower band (-2σ).
```

### E2: parameters

```text
0.50 → Price is at the volume-weighted mean
```

### E3: parameters

```text
1.00 → Price is at the upper band (+2σ).
```

### E4: parameters

```text
last 2 higher timeframe closed candles
```

### E5: parameters

```text
200-day timeframe
```

### E6: risks

```text
THE INCLUDED FUNCTION MUST BE CONSIDERED FOR TESTING.
```

### E7: mechanism, readiness

```text
kurtosis-driven degrees of freedom.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_sgfm0bj3_elastic_volume_weighted_student_t_tension](../tv_sgfm0bj3_elastic_volume_weighted_student_t_tension.md)

## Source

https://www.tradingview.com/script/Sgfm0BJ3-Elastic-Volume-Weighted-Student-T-Tension/

Publication ID: Sgfm0BJ3. Source SHA-256: 2afc65256e82c5f46d03d72a8bd01a7ee0cfa86c4a2fced20649616ad1a63e18. Raw-description SHA-256: f0f67318acd37e2be8d3eaa114ebfed5491d3a8194fe77fe516c2f77d2e1312b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
