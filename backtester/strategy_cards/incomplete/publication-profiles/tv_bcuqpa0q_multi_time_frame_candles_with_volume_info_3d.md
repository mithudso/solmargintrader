---

id: tv_profile_bcuqpa0q

name: "Multi Time Frame Candles with Volume Info / 3D"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Multi Time Frame Candles with Volume Info overlays a configurable sequence of higher-timeframe candles and supplements it with volume information and remaining time to close. Its aim is to keep broader candle context visible without leaving the current chart. It also identifies new highs/lows or breakouts, though their exact definition is not described. The optional three-dimensional appearance is a presentation device, not an additional market measurement. Multiple configured instances can place different higher-timeframe series in the same window."

registry_key: null

runner: null

evaluation: null

---

# Multi Time Frame Candles with Volume Info / 3D

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multi Time Frame Candles with Volume Info overlays a configurable sequence of higher-timeframe candles and supplements it with volume information and remaining time to close. Its aim is to keep broader candle context visible without leaving the current chart. It also identifies new highs/lows or breakouts, though their exact definition is not described. The optional three-dimensional appearance is a presentation device, not an additional market measurement. Multiple configured instances can place different higher-timeframe series in the same window.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Higher-timeframe candle aggregation/confirmation and extreme-marking predicates are unspecified.

- Higher-timeframe candle aggregation/confirmation and extreme-marking predicates are unspecified.

## How it works

- Retrieve or construct higher-timeframe candles and draw their bodies/wicks with optional depth/shadow.
- Add higher-timeframe volume and closing-time information and mark new extremes.

## Outputs and intended use

- Higher-timeframe candle drawings, volume colors, remaining-time text and breakout indications support contextual chart reading.

## Parameters and stated settings

- Higher timeframe, candle count, starting bar, candle/wick/volume/text/shadow/background colors are configurable.
- The 3D effect defaults enabled and can be disabled.

## Failure modes and caveats

- An unfinished higher-timeframe candle changes before close, so visible breakouts may be provisional.
- Graphic offsets can obscure the temporal relationship with source candles.

## Missing information and implementation boundary

- Aggregation/confirmation behavior, breakout reference window, volume mapping, default timeframe/count and trading rules are absent.

## Data requirements

Required inputs: ohlcv, market session/calendar timing.

Repository input-class support: available. Higher-timeframe candles and volume can be derived from OHLCV with timestamps; live close countdown also depends on ordinary session timing.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, outputs_and_use, readiness

```text
volume info, remaining time to close
```

### E2: outputs_and_use

```text
new highs/lows[/b] / breakouts.
```

### E3: parameters

```text
3D effect, by default it's enables
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bcuqpa0q_multi_time_frame_candles_with_volume_info_3d](../tv_bcuqpa0q_multi_time_frame_candles_with_volume_info_3d.md)

## Source

https://www.tradingview.com/script/BcuQpa0q-Multi-Time-Frame-Candles-with-Volume-Info-3D/

Publication ID: BcuQpa0q. Source SHA-256: 772ae5453f98e5b0c6c992aca2528bc29696722902f68127f9dadb30430eb2b2. Raw-description SHA-256: 278869b545df075be0ba0d31d2936c4173616245ac586da59899132e18f6dc18.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
