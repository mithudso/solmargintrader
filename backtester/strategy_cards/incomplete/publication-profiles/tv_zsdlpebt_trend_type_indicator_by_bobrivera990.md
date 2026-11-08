---

id: tv_profile_zsdlpebt

name: "Trend Type Indicator by BobRivera990"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trend Type Indicator categorizes price behavior as sideways, upward or downward using volatility and directional-movement tools. It is intended for comparing trend context across chart timeframes before applying a separate trend-trading method. The publication distinguishes strength/range detection from direction, which avoids assuming that high volatility alone means an uptrend. Its displayed status is lagged and smoothed, so the raw classification rules do not fully reproduce the published output."

registry_key: null

runner: null

evaluation: null

---

# Trend Type Indicator by BobRivera990

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trend Type Indicator categorizes price behavior as sideways, upward or downward using volatility and directional-movement tools. It is intended for comparing trend context across chart timeframes before applying a separate trend-trading method. The publication distinguishes strength/range detection from direction, which avoids assuming that high volatility alone means an uptrend. Its displayed status is lagged and smoothed, so the raw classification rules do not fully reproduce the published output.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for raw ADX-only sideways/up/down classification with chosen DI/ADX lengths and explicit25 threshold. Full combined-filter and smoothed/lagged output parity remain incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow raw ADX-only classifier: disable the ATR sideways filter, enable ADX with chosen DI length and ADX smoothing. ADX≤25 means sideways; otherwise +DI>−DI means uptrend and −DI>+DI means downtrend. Equal DI above the threshold remains unspecified. This is the pre-display classification, not the published smoothed/lagged oscillator.
- Classify sideways conditions when ATR is below its moving average or ADX indicates insufficient trend strength, according to enabled filters.
- For non-sideways conditions compare positive and negative directional indicators for upward versus downward direction.
- Apply configurable smoothing and lag to the displayed oscillator/status.

## Outputs and intended use

- Check agreement across higher and lower chart timeframes as contextual confirmation.
- No entry fill, position size or exit policy is supplied.

## Parameters and stated settings

- ATR average is described as 20 periods and ADX strength threshold as 25. Default status refers to eight periods before the latest close.
- ATR/DI lengths, average type, smoothing factor and lag are configurable.
- Use ADX threshold25 with caller-selected DI and ADX smoothing lengths; do not infer numeric defaults for these. Both-filter combination, output smoothing and default eight-bar lag are outside narrow scope.

## Failure modes and caveats

- A lagged status is not a current-bar trend reading.
- Low ATR and low ADX measure different properties and may disagree.

## Missing information and implementation boundary

- Enabled-filter combination, smoothing equation, ATR/DI defaults and equal-DI handling are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the built-in calculation path.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
8 periods before the latest closing price.
```

### E2: parameters

```text
20-period moving average of the ATR.
```

### E3: parameters, mechanism, readiness

```text
ADX is less than or equal to 25
```

### E4: mechanism

```text
when +DI is higher than -DI, it is an uptrend.
```

### E5: missing_information

```text
Factor used for smoothing the oscillator
```

### E6: mechanism, parameters, readiness

```text
when +DI is higher than -DI, it is an uptrend. When -DI is higher than +DI, it is a downtrend.
```

### E7: mechanism, parameters, readiness

```text
"Use ATR …"
```

### E8: mechanism, parameters, readiness

```text
"Use ADX ..."
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zsdlpebt_trend_type_indicator_by_bobrivera990](../tv_zsdlpebt_trend_type_indicator_by_bobrivera990.md)

## Source

https://www.tradingview.com/script/zsDLpeBT-Trend-Type-Indicator-by-BobRivera990/

Publication ID: zsDLpeBT. Source SHA-256: beac28d0ea88d054f4305607325dea74a8ecf1d4a0d89ccf0ce989279a3ef533. Raw-description SHA-256: 08116783face30720a38a4b4dc5f237256fdc6799fd3b6d4a7b32b7bec1feeaf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
