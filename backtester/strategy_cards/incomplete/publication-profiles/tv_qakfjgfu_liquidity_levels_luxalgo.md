---

id: tv_profile_qakfjgfu

name: "Liquidity Levels [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Mark prices associated with volume peaks and summarize how later closing prices occupy the intervals between those levels."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Levels [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Mark prices associated with volume peaks and summarize how later closing prices occupy the intervals between those levels.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: Peak test, associated-price choice, level replacement, histogram boundary ties and actual bounce conditions are omitted.

- Peak test, associated-price choice, level replacement, histogram boundary ties and actual bounce conditions are omitted.

## How it works

- Detect significant-volume peaks over a lookback and use their associated prices as horizontal levels. Count closes and bullish candles between neighboring levels in an optional histogram.

## Outputs and intended use

- Use levels as hypotheses for support/resistance and bins as occupancy context. Previously tested levels may merit review, but the author asks for additional volume analysis rather than guaranteeing a bounce.

## Parameters and stated settings

- Configure detection length, retained level count, relative/random/fixed colors, line style, histogram window and bin colors. The illustrative histogram uses 200 bars with 68 closes and 27 bullish bars in an interval.

## Failure modes and caveats

- Volume peaks do not directly reveal resting liquidity. Histogram occupancy is historical, and short transit through a wide interval is not a complete volatility model.

## Missing information and implementation boundary

- Peak test, associated-price choice, level replacement, histogram boundary ties and actual bounce conditions are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart OHLCV supports the described input class. Code parity, complete history and forward performance remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
When a peak occurs, we take the price where this peak occurred and use it as the value for our level.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
over the most recent 200 bars (determined by Histogram Window) 68 closing prices fall between levels A and B, with 27 bars being bullish.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_qakfjgfu_liquidity_levels_luxalgo](../tv_qakfjgfu_liquidity_levels_luxalgo.md)

## Source

https://www.tradingview.com/script/qAkfJgFu-Liquidity-Levels-LuxAlgo/

Publication ID: qAkfJgFu. Source SHA-256: 1c100ab9f670a46a1d5b3e421e3292b7a3d82f39e8808df1fda6682c6ad8a19f. Raw-description SHA-256: 836b28dbf9d46c220f60eb78ab95adfb94a42e42012839b693d1a946d20f3ae8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
