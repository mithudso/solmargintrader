---

id: tv_profile_v8sbugsw

name: "RedK Trader Pressure Index (TPX v1.0) "

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trader Pressure Index interprets changes in consecutive bar highs and lows as a proxy for bullish and bearish pressure. Its aim is to show which side appears to control the price range and when neither side shows sufficient activity to justify a trade. This is price-derived pressure, not a direct count of buyers and sellers. The author recommends combining the display with broader trend and momentum context rather than treating it as a standalone trade instruction."

registry_key: null

runner: null

evaluation: null

---

# RedK Trader Pressure Index (TPX v1.0)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trader Pressure Index interprets changes in consecutive bar highs and lows as a proxy for bullish and bearish pressure. Its aim is to show which side appears to control the price range and when neither side shows sufficient activity to justify a trade. This is price-derived pressure, not a direct count of buyers and sellers. The author recommends combining the display with broader trend and momentum context rather than treating it as a standalone trade instruction.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- Pressure normalization, clipping and smoothing definitions are missing.

## How it works

- Measure changes in highs and lows between adjacent bars as directional-pressure proxies.
- Calculate weighted moving averages of the pressure measures and a net-pressure result.
- Compare each side with a configurable control threshold to indicate stronger dominance.

## Outputs and intended use

- Read plotted bull, bear and net pressure for supported directional movement or low-interest/no-trade conditions.
- Use with moving averages or MACD for additional contextual confirmation.

## Parameters and stated settings

- A control level around 25 or 30 is suggested; the exact default and averaging period are absent.

## Failure modes and caveats

- High/low movement cannot reveal the number of actual buyers or sellers.
- Range expansion, gaps and smoothing can affect a pressure interpretation independently of durable trend.

## Missing information and implementation boundary

- Positive/negative clipping, normalization, weighted-average length and net-pressure formula are not fully specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
change in high and low price, between 2 consecutive price bars, as a proxy
```

### E2: mechanism

```text
(weighted) moving average of these “pressure” values
```

### E3: parameters

```text
around the 25 or 30
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_v8sbugsw_redk_trader_pressure_index_tpx_v1_0](../tv_v8sbugsw_redk_trader_pressure_index_tpx_v1_0.md)

## Source

https://www.tradingview.com/script/v8sBugsW-RedK-Trader-Pressure-Index-TPX-v1-0/

Publication ID: v8sBugsW. Source SHA-256: b3791605c6fcd3824329e9e19b521a7d4ad1ce2656d89f1285a861f31e9cfa29. Raw-description SHA-256: 45e23f9569dd59d6cd47aceaa61f44747990ccb41054f933e1fcf128c2641592.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
