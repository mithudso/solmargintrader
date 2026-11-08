---

id: tv_profile_vxui7vrm

name: "Market Structure Dashboard | Flux Charts"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Market Structure Dashboard integrates trend, confirmed pivots, price zones, participation and session context across multiple timeframes. It exposes individual components and a weighted directional summary to distinguish agreement from conflict. Many components have substantive rules, but the combined publication remains incomplete because fair-value-gap indexing contradicts its introductory definition and higher-timeframe confirmation is unstated. Institutional-order language interprets price patterns rather than observing account activity."

registry_key: null

runner: null

evaluation: null

---

# Market Structure Dashboard | Flux Charts

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Structure Dashboard integrates trend, confirmed pivots, price zones, participation and session context across multiple timeframes. It exposes individual components and a weighted directional summary to distinguish agreement from conflict. Many components have substantive rules, but the combined publication remains incomplete because fair-value-gap indexing contradicts its introductory definition and higher-timeframe confirmation is unstated. Institutional-order language interprets price patterns rather than observing account activity.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for current-timeframe EMA trend and relative-volume tiers, with confirmed symmetric pivot procedure also explicit. FVG contradictions, HTF confirmation, session DST and composite parity remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow current-timeframe EMA/volume outputs: E=EMA(close,9); bullish if Close>E, bearish if Close<E, with equality not specified. V%=100×Volume/SMA(Volume,20). Apply tiers in descending order: >200 EXTREME; else >120 HIGH; else >80 NORMAL; else >50 LOW; else VERY LOW. Thus exact threshold equality falls into the next lower tier; zero mean volume remains undefined. Independently, a pivot high/low must be strictly higher/lower than five bars on each side and becomes known only after the right five bars.
- Compare close with EMA and confirm symmetric pivots; classify successive highs/lows and combine latest types into structural bias.
- After a swing break, use the intervening lowest-low or highest-high candle as an order block, invalidated by a close through. Track swing breaches and close reclaims.
- Sum enabled bullish/bearish/neutral factors by timeframe weight, then divide by the maximum possible magnitude. Add volume/SMA and ATR/average-ATR states.

## Outputs and intended use

- Read timeframe rows, nearest zones, prior-period extremes and optional overlays.
- Use session context and weighted bias to support analysis rather than automatic execution.

## Parameters and stated settings

- Up to seven timeframes; EMA defaults 9, swing length 5 and ATR 14 with averaging lookback 20.
- Volume thresholds are 200%,120%,80%,50%; volatility boundaries 130%,70%; bias boundaries ±20%,±50%.
- Use current chart timeframe, EMA9 and volume SMA20; pivot strength defaults five per side. Narrow scope excludes FVGs, HTF requests and session clocks.

## Failure modes and caveats

- Pivot confirmation is delayed.
- FVG wording alternates first/third candles with current versus three bars ago, and touch versus full-gap mitigation.

## Missing information and implementation boundary

- Resolve FVG indexing/mitigation, higher-timeframe sampling and EST versus New York daylight-saving interpretation.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default input class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
up to 7 configurable timeframes
```

### E2: parameters, mechanism, readiness

```text
9-period EMA (configurable)
```

### E3: parameters

```text
Swing Length parameter (default: 5)
```

### E4: parameters

```text
14-period ATR and compares it to its own 20-period average
```

### E5: parameters, mechanism, readiness

```text
EXTREME (over 200% of average), HIGH (over 120%), NORMAL (over 80%), LOW (over 50%), or VERY LOW (50% or less).
```

### E6: parameters

```text
HIGH (ATR over 130% of average), NORMAL (ATR between 70-130% of average), or LOW (ATR under 70% of average).
```

### E7: parameters

```text
Over 50% shows BULLISH
```

### E8: parameters

```text
Between 20% and 50%
```

### E9: parameters

```text
Between -20% and 20%
```

### E10: parameters

```text
Between -50% and -20%
```

### E11: parameters

```text
Below -50%
```

### E12: missing_information

```text
three bars ago
```

### E13: missing_information

```text
three-candle pattern
```

### E14: mechanism

```text
bias percentage equals the total score divided by the maximum possible score, multiplied by 100.
```

### E15: mechanism, parameters, readiness

```text
current volume as a percentage of its 20-period simple moving average.
```

### E16: mechanism, parameters, readiness

```text
A swing high is confirmed when a candle's high is higher than the specified number of candles on both sides.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_candlestick_patterns](../tv_method_candlestick_patterns.md)
- [tv_method_fair_value_gap](../../tv_method_fair_value_gap.md)
- [tv_method_liquidity_sweep](../../tv_method_liquidity_sweep.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_order_blocks](../tv_method_order_blocks.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_vxui7vrm_market_structure_dashboard_flux_charts](../tv_vxui7vrm_market_structure_dashboard_flux_charts.md)

## Source

https://www.tradingview.com/script/vXui7vrm-Market-Structure-Dashboard-Flux-Charts/

Publication ID: vXui7vrm. Source SHA-256: 13500d80d95818311f5e6bb1d1bc1aa16f5c62d65b9d6f5756db5c31495af2ba. Raw-description SHA-256: e48d601c4c38c7ea246bed6233cb84bfdcb540d7dea317d271f0ecd54936e6f1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
