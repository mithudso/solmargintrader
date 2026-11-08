---

id: tv_profile_93tde1fd

name: "Liquidity Price Depth Chart [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Rearrange visible-range bullish and bearish candle prices into a depth-chart-like visualization of historical price/volume concentration."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Price Depth Chart [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Rearrange visible-range bullish and bearish candle prices into a depth-chart-like visualization of historical price/volume concentration.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Price selection within candles, displacement accumulation, duplicate-price handling and exact sentiment denominator are unspecified.

- Price selection within candles, displacement accumulation, duplicate-price handling and exact sentiment denominator are unspecified.

## How it works

- Sort selected prices descending, place bullish observations on the left and bearish ones on the right, and use displacement to represent associated volume. Mark each side's highest-volume price and display its share of total visible-range volume.

## Outputs and intended use

- Inspect clustered shapes and voids as historical concentration/rapid-movement context. The resemblance to an order-book chart does not make it an order-book feed or direct evidence of resting liquidity.

## Parameters and stated settings

- Visible chart range defines the sample and recalculates results when changed. Toggles control highest-volume lines, percentages and percentage-box padding.

## Failure modes and caveats

- Viewport changes alter the analysis retrospectively. Candle direction is not trade aggressor classification, and historical volume does not prove open positions remain at those levels.

## Missing information and implementation boundary

- Price selection within candles, displacement accumulation, duplicate-price handling and exact sentiment denominator are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
highlighting sorted prices from bullish and bearish candles located on the chart's visible range
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
changing the chart's visible range will recalculate the indicator.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
higher displacement highlighting prices with more volume.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_93tde1fd_liquidity_price_depth_chart_luxalgo](../tv_93tde1fd_liquidity_price_depth_chart_luxalgo.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/93TdE1fd-Liquidity-Price-Depth-Chart-LuxAlgo/

Publication ID: 93TdE1fd. Source SHA-256: cf9c0053b94ae3572aad547579ae27979e10f978333dd020f7ac1698e5725cb9. Raw-description SHA-256: f468b6dbd5fa59b345761273cc4a84dd6269d8f657bc056c0bd08adb5271eac1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
