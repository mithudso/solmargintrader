---

id: tv_profile_lbobwukj

name: "Sync Frame (MTF Charts) [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Show several lower-timeframe views of the current asset together so the reader can compare local price behavior without switching the main chart."

registry_key: null

runner: null

evaluation: null

---

# Sync Frame (MTF Charts) [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show several lower-timeframe views of the current asset together so the reader can compare local price behavior without switching the main chart.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Lower-timeframe aggregation, alignment, missing bars, lookahead behavior and automatic-resolution formula are not disclosed.

- Lower-timeframe aggregation, alignment, missing bars, lookahead behavior and automatic-resolution formula are not disclosed.

## How it works

- Render five lower-timeframe charts, derive timeframe choices automatically and dynamically scale the mini-charts as the main chart is zoomed or positioned.

## Outputs and intended use

- Choose candlestick, Heikin-Ashi or baseline presentation. Use these as synchronized context displays; the source defines no indicator score or trading trigger.

## Parameters and stated settings

- Timeframes are user-customizable and can be automatically calculated. The exact default resolutions and retained candle count are absent.

## Failure modes and caveats

- Heikin-Ashi prices are synthetic. Mini-chart scaling can make absolute moves hard to compare, and lower-timeframe history may have platform limits.

## Missing information and implementation boundary

- Lower-timeframe aggregation, alignment, missing bars, lookahead behavior and automatic-resolution formula are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
[*]5 lower timeframe candle charts shown
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Timeframes auto-calculated using the new timeframe.from_seconds() function
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Heikin-Ashi candles available
[*]Baseline chart type available
[*]Dynamic Scaling for ease of use
[*]User customizable timeframes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)

## Source

https://www.tradingview.com/script/LbobwUkJ-Sync-Frame-MTF-Charts-Kioseff-Trading/

Publication ID: LbobwUkJ. Source SHA-256: 915bbe91ad8dc8ba6ea7adbed6c88d4d2532ca72f58a9792c04016150056c2c3. Raw-description SHA-256: a306c96264c5b4f905a8e94679b87366783d633d99e8208622ec06b8579c2ca9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
