---

id: tv_profile_s2clgbm5

name: "Volume-based Support & Resistance Zones"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Volume-based Support & Resistance Zones marks high-volume swing extremes across several timeframes. It aims to highlight structural prices that may matter for reversal or for breakout-and-retest analysis. A zone extends from the fractal extreme to its candle close, combining a turning-point reference with the size of the rejection region. The author says larger zones are more significant, but that is a qualitative interpretation rather than a tested ranking. The indicator offers extensive history, drawing and alert controls without supplying a complete trading setup."

registry_key: null

runner: null

evaluation: null

---

# Volume-based Support & Resistance Zones

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume-based Support & Resistance Zones marks high-volume swing extremes across several timeframes. It aims to highlight structural prices that may matter for reversal or for breakout-and-retest analysis. A zone extends from the fractal extreme to its candle close, combining a turning-point reference with the size of the rejection region. The author says larger zones are more significant, but that is a qualitative interpretation rather than a tested ranking. The indicator offers extensive history, drawing and alert controls without supplying a complete trading setup.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Volume-average calculation/timing and equal-extreme/zone lifecycle rules are not fully defined.

## How it works

- Require fractal highs with three successive higher highs followed by two lower highs, with inverse logic for lows.
- Gate fractals by volume above its configurable moving average.
- Draw extreme-to-close zones per timeframe, retain bounded history and suppress lower-timeframe zones on higher charts.

## Outputs and intended use

- Up to four timeframe zone sets, lines/labels/extensions and configurable alerts support level monitoring.

## Parameters and stated settings

- Four timeframes; per-timeframe volume-average value, zone count and alert types plus styling/visibility are configurable.
- Fractal sequence uses three rising and two falling highs; defaults for MA/timeframes are absent.

## Failure modes and caveats

- Fractals confirm after the turning point; historical zone origins can appear earlier than availability.
- Older higher-timeframe origins may fall back to a bounded history position, especially on stocks.

## Missing information and implementation boundary

- Volume MA type/length defaults, exact volume comparison timing, equal-extreme treatment, invalidation and alert predicates are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Fractal extrema, closes, volume averages and higher-timeframe aggregation use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
4 time frames
```

### E2: mechanism, parameters, readiness

```text
3 successive higher highs followed by 2 successive lower highs
```

### E3: mechanism, readiness

```text
volume that pierces above the volume's Moving Average.
```

### E4: mechanism

```text
fractal high/low and the close of the candle
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_s2clgbm5_volume_based_support_resistance_zones](../tv_s2clgbm5_volume_based_support_resistance_zones.md)

## Source

https://www.tradingview.com/script/S2ClgBm5-Volume-based-Support-Resistance-Zones/

Publication ID: S2ClgBm5. Source SHA-256: f43e8a36fd5b310dcd72fd56af38544a356ed0abfd3a87599e4064352baf6027. Raw-description SHA-256: 226caf5acb64b458e6dc09b1f6f86019379e7936182384ccaa4fcdd1d2f1ab00.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
