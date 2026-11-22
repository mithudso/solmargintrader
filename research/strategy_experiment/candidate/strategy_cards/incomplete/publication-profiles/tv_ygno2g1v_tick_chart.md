---

id: tv_profile_ygno2g1v

name: "Tick Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Build a live candle chart organized by count of price updates rather than fixed elapsed time."

registry_key: null

runner: null

evaluation: null

---

# Tick Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build a live candle chart organized by count of price updates rather than fixed elapsed time.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Grouping an ordered live price-update stream into consecutive blocks of the selected tick count defines the principal tick-candle construction. This usable scope excludes exact volume reporting, persistence and platform-feed parity.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Aggregate each configured number of consecutive ticks into a candle. The author defines ticks in terms of platform updates, so the resulting chart follows the observed update stream.

## Outputs and intended use

- Display tick candles with volume information, current/minimum/maximum/average volume and OHLC for the last candle. Use it to inspect activity-scaled price movement while the feed is live.

## Parameters and stated settings

- Number of ticks per candle and number of candles are configurable, along with body, wick and volume-bar colors. The example uses 100 ticks per candle.

## Failure modes and caveats

- The author says it works only on real-time bars. Platform updates need not correspond one-for-one with exchange trades, and missed updates cannot be recovered from ordinary historical candles.

## Missing information and implementation boundary

- Tick deduplication, volume allocation, candle reset and persisted-history handling are not described.

## Data requirements

Required inputs: live price and volume update stream.

Repository input-class support: unavailable or unresolved. Historical OHLCV cannot reproduce the ordered live update stream required to construct these tick candles.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
for example if you set Number of Ticks Per Candle = 100 then each candlestick is created using 100 ticks.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Tick Chart only works on realtime bars.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The script shows current, minimum, maximum and average volumes. it also shows OHLC values on the last candle.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_renko](../tv_method_renko.md)
- [tv_ygno2g1v_tick_chart](../../../strategy_research/tv_ygno2g1v_tick_chart.md)

## Source

https://www.tradingview.com/script/ygNO2G1V-Tick-Chart/

Publication ID: ygNO2G1V. Source SHA-256: f4570cb79a34e12d1dfcfd7495d84df1c653a1c4dbfd7a3b8fdab0a41539d5e6. Raw-description SHA-256: 455e1d7df206e034affb1a0362d5aea22a283592911f8da4038e959810559423.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
