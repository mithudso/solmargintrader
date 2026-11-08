---

id: tv_profile_yqkwbg4m

name: "Intrabar Analyzer [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Intrabar Analyzer displays lower-timeframe prices and technical calculations within a higher-timeframe chart context. It aims to make hidden intrabar structure inspectable through alternate candle constructions, overlays, volume/price graphics and technical ratings. Users can compare traditional prices with synthetic forms such as Renko or Heikin-Ashi, but those representations do not share identical execution meaning. The publication chiefly lists capabilities and screenshots rather than explaining the many underlying calculations. Its intended use is exploratory drill-down, not a defined signal combination."

registry_key: null

runner: null

evaluation: null

---

# Intrabar Analyzer [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Intrabar Analyzer displays lower-timeframe prices and technical calculations within a higher-timeframe chart context. It aims to make hidden intrabar structure inspectable through alternate candle constructions, overlays, volume/price graphics and technical ratings. Users can compare traditional prices with synthetic forms such as Renko or Heikin-Ashi, but those representations do not share identical execution meaning. The publication chiefly lists capabilities and screenshots rather than explaining the many underlying calculations. Its intended use is exploratory drill-down, not a defined signal combination.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core synthetic-chart/indicator configurations and graph/rating calculations are not disclosed.

## How it works

- Request a selected lower timeframe and render its price/volume observations.
- Offer traditional, Heikin-Ashi, Kagi, Point & Figure, Renko and line-break forms with selectable technical overlays/oscillators.
- Display TradingView-style intrabar technical ratings on either side of the price box.

## Outputs and intended use

- Intrabar price and volume graph, up to three simultaneous indicators and signed technical-rating display support detailed chart analysis.

## Parameters and stated settings

- Lower timeframe defaults one minute; six price representations.
- Technical ratings multiply by 100; negative left, positive right and zero unhighlighted. Colors/characters are configurable.

## Failure modes and caveats

- Synthetic price forms and technical consensus are not independent confirmations.
- Lower-timeframe history limits and feed differences can alter visible intrabars.

## Missing information and implementation boundary

- Indicator lengths/defaults, synthetic-chart construction, graph scaling, rating formula and causal update policy are absent.

## Data requirements

Required inputs: lower-timeframe ohlcv, synthetic-price feed/configuration when selected.

Repository input-class support: unavailable or unresolved. Requires compatible intrabar histories and synthetic-chart settings beyond ordinary chart candles.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
default = 1 minute
```

### E2: parameters

```text
6 variations of price data
```

### E3: parameters

```text
up to three indicators
```

### E4: parameters

```text
multiplied by x100
```

### E5: parameters

```text
"0" value is not shown
```

### E6: mechanism, readiness

```text
All data is sourced from a lower timeframe
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../tv_method_heikin_ashi.md)
- [tv_method_renko](../tv_method_renko.md)
- [tv_yqkwbg4m_intrabar_analyzer_kioseff_trading](../tv_yqkwbg4m_intrabar_analyzer_kioseff_trading.md)

## Source

https://www.tradingview.com/script/YqkWbG4M-Intrabar-Analyzer-Kioseff-Trading/

Publication ID: YqkWbG4M. Source SHA-256: 825635b0de0bbdaa8dc7944f878e13807d90ceef207b1e9f22087ec73e082b12. Raw-description SHA-256: 5c55bdead8b259556ca2ffa8b8d75340277742276b2e916ef7a3aaaaa1f25c73.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
