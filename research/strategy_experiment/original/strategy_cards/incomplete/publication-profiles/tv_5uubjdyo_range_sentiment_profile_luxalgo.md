---

id: tv_profile_5uubjdyo

name: "Range Sentiment Profile [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Range Sentiment Profile organizes signed candle-body movement by price area to show where bullish or bearish changes accumulated within a recent range. It resembles a volume profile visually but measures close-minus-open variation rather than volume. The resulting bins and highlighted extremes provide contextual zones; a short or empty bin can mean cancellation between opposing movements rather than absence of activity."

registry_key: null

runner: null

evaluation: null

---

# Range Sentiment Profile [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Range Sentiment Profile organizes signed candle-body movement by price area to show where bullish or bearish changes accumulated within a recent range. It resembles a volume profile visually but measures close-minus-open variation rather than volume. The resulting bins and highlighted extremes provide contextual zones; a short or empty bin can mean cancellation between opposing movements rather than absence of activity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Assignment of standard candle body changes to overlapping price rows is unspecified.

- Assignment of standard candle body changes to overlapping price rows is unspecified.

## How it works

- Find the recent range maximum/minimum and divide that span into equally spaced price rows. Accumulate signed close-open differences for candles associated with each row.
- Normalize bin length by the largest absolute row accumulation and express each row’s percentage against total absolute body movement.
- Optional intrabar mode assigns lower-timeframe candle changes to rows for a finer allocation.

## Outputs and intended use

- Blue/orange background conveys prevailing bullish/bearish variation. Highlighted maximum rows and cancellation zones are proposed as possible support/resistance.

## Parameters and stated settings

- Length selects recent bars, Rows selects price-bin count, Use Intrabar enables finer data and Timeframe selects the intrabar interval. Width affects drawing scale; no defaults are stated.

## Failure modes and caveats

- Analytical: positive/negative candle bodies are not actual order-flow sentiment, and cancellation can hide substantial two-sided activity. Intrabar mode costs more computation.

## Missing information and implementation boundary

- Exact overlap allocation for standard bars, zero-denominator handling, available intrabar history and reversal confirmation are not given.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV for optional intrabar mode.

Repository input-class support: available. OHLCV at the selected chart/intrabar resolutions supports this calculation class; actual lower-timeframe history coverage is unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
accumulate the difference between the closing and opening price for that specific area.
```

### E2: mechanism, readiness

```text
length = Width / 100 * Area / Max
```

### E3: mechanism, readiness

```text
the accumulated close to open difference is accumulated only if the intrabar candle of the user selected timeframe lies within the area.
```

### E4: risks, readiness

```text
at the cost of a higher computation time.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5uubjdyo_range_sentiment_profile_luxalgo](../tv_5uubjdyo_range_sentiment_profile_luxalgo.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/5UuBjDYO-Range-Sentiment-Profile-LuxAlgo/

Publication ID: 5UuBjDYO. Source SHA-256: c57efff8cf64789e96ae35f0baf7d7a1faab34176a9eea6c1df09635eb860f2f. Raw-description SHA-256: 4a49cc94e1143383bd2322c08257b8f2c0b2d5cf124d957e8fe37d3b9b4e86a0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
