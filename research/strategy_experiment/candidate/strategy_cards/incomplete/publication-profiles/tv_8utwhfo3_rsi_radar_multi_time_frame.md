---

id: tv_profile_8utwhfo3

name: "RSI Radar Multi Time Frame"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "RSI Radar Multi Time Frame turns several timeframe-specific RSI readings into a radar-shaped chart overlay. The aim is simultaneous momentum inspection across horizons, including intervals above and below the chart timeframe. Its experimental polyline presentation stays in the visible chart area as the user scrolls or zooms, making it a persistent dashboard rather than a historical signal trace. A reader can inspect broad agreement or disagreement among the RSI readings, but the source does not define a multi-timeframe consensus rule or assign trades to a particular radar shape."

registry_key: null

runner: null

evaluation: null

---

# RSI Radar Multi Time Frame

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

RSI Radar Multi Time Frame turns several timeframe-specific RSI readings into a radar-shaped chart overlay. The aim is simultaneous momentum inspection across horizons, including intervals above and below the chart timeframe. Its experimental polyline presentation stays in the visible chart area as the user scrolls or zooms, making it a persistent dashboard rather than a historical signal trace. A reader can inspect broad agreement or disagreement among the RSI readings, but the source does not define a multi-timeframe consensus rule or assign trades to a particular radar shape.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** RSI source/period and lower-timeframe sampling semantics are not specified.

- RSI source/period and lower-timeframe sampling semantics are not specified.

## How it works

- Request RSI readings from independently selected higher, lower or chart-equivalent timeframes.
- Connect the readings into a curved radar outline or hexagonal polyline and reposition it within the visible chart.

## Outputs and intended use

- A continuously visible radar shows cross-timeframe RSI with configurable overbought/oversold and line colors.

## Parameters and stated settings

- Six timeframe readings; curved/hexagon style and colors are configurable.
- The example spans seconds through one day on a 30-minute chart; it is an example rather than default values.

## Failure modes and caveats

- Developing higher-timeframe readings can change unless confirmed values are selected; confirmation behavior is not supplied.
- A radar polygon can visually emphasize shape without a corresponding calibrated signal.

## Missing information and implementation boundary

- RSI length/source, timeframe defaults, lower-timeframe sampling, lookahead/confirmation policy and trading rules are absent.

## Data requirements

Required inputs: multi-timeframe ohlcv including lower-timeframe history.

Repository input-class support: unavailable or unresolved. Lower-than-chart readings require additional intrabar histories; sufficient compatible coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
RSI values from 6 different time frames
```

### E2: required_data

```text
higher or lower time frames than chart time frame.
```

### E3: parameters, outputs_and_use

```text
Curved/Hexagon optionally.
```

### E4: parameters

```text
seconds to 1Day
```

### E5: parameters

```text
30mins here
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_8utwhfo3_rsi_radar_multi_time_frame](../tv_8utwhfo3_rsi_radar_multi_time_frame.md)

## Source

https://www.tradingview.com/script/8UtWhfo3-RSI-Radar-Multi-Time-Frame/

Publication ID: 8UtWhfo3. Source SHA-256: 44bae978890aadfee7a32ea39c5c0fcc216986961ce0476b11be2f1abf7c4f40. Raw-description SHA-256: 3a691c00d1e7fbf548b3c6a9efbed9c63c82c366c3b9807d7c7b3351754d028e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
