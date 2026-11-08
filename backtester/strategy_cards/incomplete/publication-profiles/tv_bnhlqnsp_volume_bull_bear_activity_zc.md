---

id: tv_profile_bnhlqnsp

name: "Volume Bull/Bear Activity [ZC]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volume Bull/Bear Activity summarizes directional-volume readings for a selected symbol list. It aims to show where bullish or bearish activity is concentrated without switching charts. Paired green/red bars represent attributed volume, while displayed price color reflects whether the candle is up or down. The source’s wording mixes the last candle for green volume with the realtime bar for red volume, so it does not establish a consistent sampling contract. No entry rule or ranking model is supplied."

registry_key: null

runner: null

evaluation: null

---

# Volume Bull/Bear Activity [ZC]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volume Bull/Bear Activity summarizes directional-volume readings for a selected symbol list. It aims to show where bullish or bearish activity is concentrated without switching charts. Paired green/red bars represent attributed volume, while displayed price color reflects whether the candle is up or down. The source’s wording mixes the last candle for green volume with the realtime bar for red volume, so it does not establish a consistent sampling contract. No entry rule or ranking model is supplied.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core bull/bear allocation and consistent bar timing are undefined.

## How it works

- Retrieve selected-symbol data at an adjustable timeframe and compute unspecified bull/bear volume readings.
- Display paired color bars and color price by candle direction.

## Outputs and intended use

- Multi-symbol volume dashboard supports discretionary activity comparison.

## Parameters and stated settings

- Up to twenty symbols; adjustable timeframe. Other defaults absent.

## Failure modes and caveats

- Directional-volume attribution and asynchronous bar wording are unclear.
- Realtime values can change and do not directly measure aggressor-side trades.

## Missing information and implementation boundary

- Buy/sell split, green/red time alignment, normalization, reset and update rules are absent.

## Data requirements

Required inputs: selected multi-symbol ohlcv or realtime volume feeds.

Repository input-class support: unavailable or unresolved. External symbol histories/live observations and the volume-allocation contract are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
for 20 symbols.
```

### E2: readiness, risks

```text
last candle of the symbol.
```

### E3: readiness, risks

```text
within the real-time bar, continuously updated.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bnhlqnsp_volume_bull_bear_activity_zc](../tv_bnhlqnsp_volume_bull_bear_activity_zc.md)

## Source

https://www.tradingview.com/script/bNhLqnsP-Volume-Bull-Bear-Activity-ZC/

Publication ID: bNhLqnsP. Source SHA-256: e697131ed53fea22d80c002f5c9a2f813296dfa91deea0278c9b39e437d2e7d1. Raw-description SHA-256: 743c63481489efd7fa1f37ff1175b10d5d7d1639d0cead871c88ed51ac870c4c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
