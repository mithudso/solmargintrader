---

id: tv_profile_vo99pov0

name: "HTF Candle Volume Thermometer [ChartPrime]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "HTF Candle Volume Thermometer displays a segmented volume heatmap within each higher-timeframe candle. It seeks to show which parts of a candle’s price range contained the greatest volume and to mark that local maximum for subsequent price-reaction analysis. Bullish/bearish candle backgrounds and heat intensity supply context; the concentration of traded volume is not a direct measurement of resting liquidity."

registry_key: null

runner: null

evaluation: null

---

# HTF Candle Volume Thermometer [ChartPrime]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

HTF Candle Volume Thermometer displays a segmented volume heatmap within each higher-timeframe candle. It seeks to show which parts of a candle’s price range contained the greatest volume and to mark that local maximum for subsequent price-reaction analysis. Bullish/bearish candle backgrounds and heat intensity supply context; the concentration of traded volume is not a direct measurement of resting liquidity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Volume-to-price allocation within higher-timeframe candles is undisclosed.

- Volume-to-price allocation within higher-timeframe candles is undisclosed.

## How it works

- Divide each HTF candle range into smaller levels, distribute recorded volume across them and color the sections as a heatmap.
- Highlight the maximum-volume level while shading the candle background by direction.

## Outputs and intended use

- Compare distribution across bullish/bearish candles and inspect reactions at high-volume levels as potential support/resistance or stop/target context.

## Parameters and stated settings

- HTF interval, heatmap resolution and colors are adjustable; no numeric defaults are disclosed.

## Failure modes and caveats

- Analytical: segmentation precision depends on underlying observations and allocation assumptions; an unclosed HTF candle can change its apparent maximum.

## Missing information and implementation boundary

- Data granularity, volume-to-price allocation, maximum ties, historical coverage and confirmed/live behavior are not specified.

## Data requirements

Required inputs: price/volume observations granular enough for HTF segmentation.

Repository input-class support: unavailable or unresolved. The source does not establish the data granularity or allocation; plain HTF OHLCV cannot reconstruct exact within-candle volume distribution.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
Each HTF candle is divided into smaller levels
```

### E2: outputs_and_use, readiness

```text
Marks the level within each HTF candle where the highest volume was recorded
```

### E3: parameters, readiness

```text
adjust the HTF timeframe, color settings, and resolution
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_vo99pov0_htf_candle_volume_thermometer_chartprime](../tv_vo99pov0_htf_candle_volume_thermometer_chartprime.md)

## Source

https://www.tradingview.com/script/Vo99POv0-HTF-Candle-Volume-Thermometer-ChartPrime/

Publication ID: Vo99POv0. Source SHA-256: a5a05ec482f68e57db5452fd36887ecde5677cbf10909736583f5f5802c65c67. Raw-description SHA-256: ab281ccb2b61256fc24aa97472beca53f1a22f81ed6b4336080753f4acce3a35.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
