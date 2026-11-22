---

id: tv_profile_iznark90

name: "Time & Sales (Tape) [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Display a tape-style view of observed price and volume events with a summary of directional dominance over the retained rows."

registry_key: null

runner: null

evaluation: null

---

# Time & Sales (Tape) [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display a tape-style view of observed price and volume events with a summary of directional dominance over the retained rows.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Aggressor/direction rules, event deduplication, volume calculation, row ordering and current feed access are not documented.

- Aggressor/direction rules, event deduplication, volume calculation, row ordering and current feed access are not documented.

## How it works

- Populate a table from either lower-timeframe observations or live ticks. Show event time, direction, price and size, and compute a dynamic dominance bar over the selected row length.

## Outputs and intended use

- Use the tape as supplementary order-flow context. The author explicitly warns against treating the table as a major basis for trading decisions.

## Parameters and stated settings

- Choose lower-timeframe or live-tick implementation, row count and size expressed as volume or price-times-volume. Table styling settings exist but their values appear only in images.

## Failure modes and caveats

- Lower-timeframe candles are aggregated observations, not necessarily individual executed trades. Live platform ticks may aggregate executions, and direction classification is unspecified.

## Missing information and implementation boundary

- Aggressor/direction rules, event deduplication, volume calculation, row ordering and current feed access are not documented.

## Data requirements

Required inputs: lower-timeframe observations or live tick stream.

Repository input-class support: unavailable or unresolved. The selected mode requires fine-grained events beyond ordinary saved OHLCV. No event stream is supplied or verified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
(1A) Lower Timeframe: Fetch data from the selected lower timeframe.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
(1B) Live Tick: Fetch data in real-time on a tick-by-tick basis, capturing data as soon as it's observed by the system.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
(3) Size Type: Volume OR Price Volume.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The values in a table should not be taken as a major concept to build a trading decision.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_iznark90_time_sales_tape_by_muqwishi](../tv_iznark90_time_sales_tape_by_muqwishi.md)

## Source

https://www.tradingview.com/script/IZnarK90-Time-Sales-Tape-By-MUQWISHI/

Publication ID: IZnarK90. Source SHA-256: 589b68b6c225f48d0b643b289fe2f1058029ed93a0f5303977255c7367e13bc0. Raw-description SHA-256: e89c383b07666ddba8ba3916dacc2da01deae7896870fb36735348837b908dd5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
