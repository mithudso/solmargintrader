---

id: tv_profile_g30euydh

name: "Liquidity Thermal Map [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Liquidity Thermal Map presents historical candle-volume concentration as a horizontal heatmap rather than a bar-shaped volume profile. It aims to reveal high-interest price zones and a dominant point of control, with a separate directional-volume gauge. The term liquidity is the author’s interpretation of past traded activity, not a measurement of resting order-book depth. The tool is intended as background context for support/resistance, structural analysis and movement from dense into sparse-volume regions. Those uses remain discretionary because the source supplies no concrete trade trigger."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Thermal Map [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Liquidity Thermal Map presents historical candle-volume concentration as a horizontal heatmap rather than a bar-shaped volume profile. It aims to reveal high-interest price zones and a dominant point of control, with a separate directional-volume gauge. The term liquidity is the author’s interpretation of past traded activity, not a measurement of resting order-book depth. The tool is intended as background context for support/resistance, structural analysis and movement from dense into sparse-volume regions. Those uses remain discretionary because the source supplies no concrete trade trigger.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for the explicitly described bullish/bearish-candle volume totals, percentage shares and absolute imbalance over a chosen lookback. Doji assignment, zero totals, heatmap midpoint tolerance and conflicting price-side interpretation remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Divide the lookback high-low range into evenly spaced price bins and accumulate candle volume near bin midpoints.
- Map bin totals to a thermal gradient and highlight the maximum-volume POC.
- Independent directional summary over the chosen lookback: sum volume of candles with close > open as Buy and close < open as Sell; report each side as its share of total traded volume and report absolute imbalance |Buy−Sell|. Equal-open/close volume assignment is not stated; no above/below-current-price regrouping is implied by this narrow candle-direction calculation.

## Outputs and intended use

- Horizontal colored zones, POC label and red/green vertical gauge show concentration and directional-volume summary.

## Parameters and stated settings

- Uses 30 price levels and a user-defined lookback; numeric lookback default is absent.
- Colors/POC styling are described, without a full input list.

## Failure modes and caveats

- Close-based binning approximates actual volume by price.
- Candle direction does not identify aggressors, and past volume is not available liquidity.
- The prose conflates candle-direction grouping with above/below-current-price grouping without resolving the exact calculation.

## Missing information and implementation boundary

- Bin tolerance/allocation, doji handling, directional-versus-price-side logic, normalization and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The explicitly described candle direction, close locations and volume use OHLCV data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Uses 30 evenly spaced price levels
```

### E2: mechanism, readiness

```text
whenever price closes near its midpoint.
```

### E3: mechanism

```text
candles that closed higher than they opened.
```

### E4: mechanism, outputs_and_use, readiness

```text
absolute difference between total buy and sell liquidity.
```

### E5: mechanism, readiness

```text
Represents the total traded volume during candles that closed higher than they opened.
```

### E6: mechanism, readiness

```text
Represents the total traded volume during candles that closed lower than they opened.
```

### E7: mechanism, readiness

```text
Each side displays the percentage share of total traded volume.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_g30euydh_liquidity_thermal_map_bigbeluga](../tv_g30euydh_liquidity_thermal_map_bigbeluga.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/G30eUYdH-Liquidity-Thermal-Map-BigBeluga/

Publication ID: G30eUYdH. Source SHA-256: c0dec8caa5a4da6ff0daf8904206d429060f66e3b5a216418551c5e3d3525076. Raw-description SHA-256: 8c38de31126e2fc36ee2573ceedcbfca6106417f54ac18cc43e145497413a464.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
