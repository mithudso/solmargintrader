---

id: tv_profile_llaoploy

name: "Liquidation Ranges + Volume/OI Dots [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This crypto analysis overlay maps possible liquidation regions around detected price ranges and highlights unusual volume or open-interest activity. Its purpose is to connect price consolidation with estimated leveraged exposure and activity concentrations. These are modelled liquidation areas and inferred activity, not observed account liquidations or verified iceberg orders. The author also offers fixed and visible range views, persistent levels and counts of later violations to help compare where activity accumulated with subsequent price movement."

registry_key: null

runner: null

evaluation: null

---

# Liquidation Ranges + Volume/OI Dots [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This crypto analysis overlay maps possible liquidation regions around detected price ranges and highlights unusual volume or open-interest activity. Its purpose is to connect price consolidation with estimated leveraged exposure and activity concentrations. These are modelled liquidation areas and inferred activity, not observed account liquidations or verified iceberg orders. The author also offers fixed and visible range views, persistent levels and counts of later violations to help compare where activity accumulated with subsequent price movement.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The range detector, exchange liquidation equation and activity inference rules are unspecified.
- Required open-interest and lower-timeframe feed contracts are unspecified.

## How it works

- A range filter attributed to DonovanWall identifies ranges; the average range price anchors leverage liquidation projections.
- Open-interest or volume delta colors a heatmap between ranges. Net-long and net-short summaries and level tables accompany the display.
- Percent-rank detection on the last chart bar produces activity dots, while lower-timeframe data supplies a separate estimate of concentrated orders.

## Outputs and intended use

- Inspect liquidation zones, dots, heatmaps and naked activity levels as contextual chart evidence.
- Select a number of prominent levels or use a maximum-per-bar view; the description does not define automatic entries.

## Parameters and stated settings

- Liquidation leverage spans 10x to 100x.
- The iceberg estimate uses 1-minute data; 20 selected levels is an illustrative setting.

## Failure modes and caveats

- Exchange-specific margin and liquidation conventions can materially change projected zones.
- Open-interest changes do not directly reveal every participant position or order intent.

## Missing information and implementation boundary

- Range-filter settings, liquidation equation, percentile window, open-interest symbols and long/short inference rules are absent.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV, open interest.

Repository input-class support: unavailable or unresolved. The analysis requires lower-timeframe data and exchange open-interest feeds beyond the available chart OHLCV class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, parameters

```text
Liquidation ranges for crypto assets (10x - 100x)
```

### E2: parameters, risks, required_data

```text
Lower timeframe data used to discover iceberg orders (estimated using 1-minute data)
```

### E3: mechanism

```text
average price of the range is calculated to project liquidation zones.
```

### E4: mechanism, required_data

```text
Heatmap is calculated using OI (or volume) delta.
```

### E5: mechanism

```text
detection method uses percent rank and calculates on the last bar of the chart.
```

### E6: parameters

```text
if I select to show 20 levels
```

### E7: missing_information

```text
popular crypto exchange's calculation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_llaoploy_liquidation_ranges_volume_oi_dots_kioseff_trading](../tv_llaoploy_liquidation_ranges_volume_oi_dots_kioseff_trading.md)

## Source

https://www.tradingview.com/script/lLaopLoy-Liquidation-Ranges-Volume-OI-Dots-Kioseff-Trading/

Publication ID: lLaopLoy. Source SHA-256: d7420a5e0fa4ec55590302063e307f977b70651753bb8f1418f0f3db9a54725e. Raw-description SHA-256: 92bdc0d820b128df54796ab399eb420e797d966047224d721b687983ac0ebc80.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
