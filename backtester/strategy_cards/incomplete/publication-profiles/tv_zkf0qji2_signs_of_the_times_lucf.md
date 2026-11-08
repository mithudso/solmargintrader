---

id: tv_profile_zkf0qji2

name: "Signs of the Times [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Signs of the Times quantifies directional bar strength from simple current/prior-bar properties while deliberately ignoring price-move amplitude. It aims to complement momentum indicators: a small favorable gap can receive the same discrete weight as a large one, making the score less dominated by outsized candles. Bull and bear evidence are collected separately, normalized and smoothed. The author recommends it as a short-term confirmation filter rather than a forecast. A second average contextualizes the signal, with stronger states requiring agreement with the zero line."

registry_key: null

runner: null

evaluation: null

---

# Signs of the Times [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Signs of the Times quantifies directional bar strength from simple current/prior-bar properties while deliberately ignoring price-move amplitude. It aims to complement momentum indicators: a small favorable gap can receive the same discrete weight as a large one, making the score less dominated by outsized candles. Bull and bear evidence are collected separately, normalized and smoothed. The author recommends it as a short-term confirmation filter rather than a forecast. A second average contextualizes the signal, with stronger states requiring agreement with the zero line.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Efficient Work and missing-volume normalization are not defined within the source.

## How it works

- Score candle polarity, rising/falling OHLC, body expansion and body-versus-wicks at unit weight.
- Double-weight gaps, Efficient Work and increased-volume directional bars; subtract bearish from bullish totals and divide by maximum weight.
- Smooth the score, compare with a second MA and zero line for colored states.

## Outputs and intended use

- Bounded oscillator, fills, arbitrary levels and signal/average channel provide directional-strength context.

## Parameters and stated settings

- Ten properties; score range ±1. Defaults ALMA20 signal and SMA20 context, levels ±0.3.
- Alternative MA/timeframe controls; length one exposes raw score. Suggested short filter spans 3–5 bars.

## Failure modes and caveats

- Efficient Work is externally referenced and its exact formula is absent.
- Live readings change before close; discrete weights do not measure economic move size.

## Missing information and implementation boundary

- Efficient Work equation, gap definition, normalization when volume missing and full smoothing defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Disclosed candle and volume properties are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Ten elementary properties
```

### E2: parameters

```text
between +1 and -1
```

### E3: parameters

```text
Weight of 1
```

### E4: parameters

```text
Weight of 2
```

### E5: parameters

```text
length 20
```

### E6: parameters

```text
+0.3 and -0.3
```

### E7: parameters

```text
last 3 to 5 bars
```

### E8: readiness, mechanism

```text
Efficient Work weight
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_zkf0qji2_signs_of_the_times_lucf](../tv_zkf0qji2_signs_of_the_times_lucf.md)

## Source

https://www.tradingview.com/script/ZKF0qji2-Signs-of-the-Times-LucF/

Publication ID: ZKF0qji2. Source SHA-256: ea7abd62c288309492d3f21ae2c8dafa467226d5e3a92a366f69717172def754. Raw-description SHA-256: 3ba6f39930b0f32e9efbebe7b6fc618d71cb546dfcf6bfe215b2be2ee1fc4a65.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
