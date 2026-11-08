---

id: tv_profile_ucux0rjl

name: "Tops & Bottoms - Time of Day Report"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Describe when daily highs and lows have historically occurred to help readers understand intraday timing tendencies for a market."

registry_key: null

runner: null

evaluation: null

---

# Tops & Bottoms - Time of Day Report

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Describe when daily highs and lows have historically occurred to help readers understand intraday timing tendencies for a market.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Day boundary, ties between equal extremes, sample denominators and treatment of partial sessions are not specified.

- Day boundary, ties between equal extremes, sample denominators and treatment of partial sessions are not specified.

## How it works

- Identify daily extremes and aggregate their occurrence percentages by time of day. Allow the sample to include all days or only days finishing up or down.

## Outputs and intended use

- Display a column report in a selected timezone over a filtered date range. Treat frequencies as historical context, not real-time knowledge of today's eventual high or low.

## Parameters and stated settings

- The source recommends one-hour or thirty-minute charts, with thirty minutes preferred for markets opening at 9:30. Timezone, date range and day-type filters are configurable.

## Failure modes and caveats

- Completed-day extrema and up/down classification are retrospective. The author notes that geographic/exchange zones may observe daylight saving while UTC+0 does not.

## Missing information and implementation boundary

- Day boundary, ties between equal extremes, sample denominators and treatment of partial sessions are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The indicator tracks and reports the percentage of occurrence of daily tops and bottoms by the time of the day.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Analyze all days, or filter only up days or down days.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Prefer the usage of the 30-minute timeframe when your market starts at 9:30 AM.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_ucux0rjl_tops_bottoms_time_of_day_report](../../tv_ucux0rjl_tops_bottoms_time_of_day_report.md)

## Source

https://www.tradingview.com/script/ucux0RJL-Tops-Bottoms-Time-of-Day-Report/

Publication ID: ucux0RJL. Source SHA-256: ad5ee2f9d9ede064c95b18d2576ffa66334734256a923ad6664b569affd9046d. Raw-description SHA-256: 40003b03972d7af42da4fa7377a7bb0821a9e749f1835f27665d7a29802db21c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
