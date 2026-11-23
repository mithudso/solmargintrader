---

id: tv_profile_cgbtzxz3

name: "Zigzag Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Zigzag Candles compresses a sequence of zigzag pivots into synthetic candlesticks. It aims to visualize swing structure in a familiar OHLC-like form and explore a possible foundation for future trend-following calculations. The body represents the first and last pivot in a group, while wicks represent its extremes. Each completed group retains its final pivot as the next group’s opening anchor, creating continuity. Proposed future moving averages, ATR and Supertrend are not described as implemented features."

registry_key: null

runner: null

evaluation: null

---

# Zigzag Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Zigzag Candles compresses a sequence of zigzag pivots into synthetic candlesticks. It aims to visualize swing structure in a familiar OHLC-like form and explore a possible foundation for future trend-following calculations. The body represents the first and last pivot in a group, while wicks represent its extremes. Each completed group retains its final pivot as the next group’s opening anchor, creating continuity. Proposed future moving averages, ATR and Supertrend are not described as implemented features.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core zigzag pivot-generation/confirmation algorithm is not supplied.

## How it works

- Calculate zigzag pivots using ZigzagLength.
- Once CandleSize pivots are collected, use first/last as open/close and group maximum/minimum as high/low.
- Discard all grouped pivots except the last, which seeds the next candle.

## Outputs and intended use

- Box-based synthetic swing candles show pivot-sequence direction and extremes.

## Parameters and stated settings

- CandleSize is at least three; ZigzagLength and CandleSize are inputs without defaults.

## Failure modes and caveats

- Zigzag confirmation/revision affects when synthetic candles are knowable.
- Synthetic wicks at separate pivot times do not represent ordinary time-bar execution paths.

## Missing information and implementation boundary

- Underlying zigzag algorithm, pivot confirmation, in-progress group behavior and defaults are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price pivots and their aggregation are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
CandleSize can be 3 or more.
```

### E2: mechanism

```text
last pivot acts as open to the next bar
```

### E3: mechanism, readiness

```text
start and end zigzag pivot
```

### E4: mechanism

```text
highest and lowest pivots
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cgbtzxz3_zigzag_candles](../tv_cgbtzxz3_zigzag_candles.md)

## Source

https://www.tradingview.com/script/cgbTZXz3-Zigzag-Candles/

Publication ID: cgbTZXz3. Source SHA-256: 763469101eb0dd3c42827d7a3710488da67a0d08a51dbc2101751da416a5e894. Raw-description SHA-256: 8d3cd6705c3f36b02cfa9a8ec2e3d5da3b90e6897e5bb0786d49cb46d93f8e08.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
