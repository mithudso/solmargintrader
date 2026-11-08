---

id: tv_profile_wixmhdwt

name: "Seasonality [TFO]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Seasonality TFO estimates typical daily, monthly and quarterly performance by trading-day position within the year. It deliberately uses a fixed trading-day calendar rather than actual calendar month boundaries. This makes it an approximate seasonal alignment model particularly intended for US stocks and indices. Its seasonal pivots and histograms describe historical tendencies, not known future high/low dates or a complete trading strategy."

registry_key: null

runner: null

evaluation: null

---

# Seasonality [TFO]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Seasonality TFO estimates typical daily, monthly and quarterly performance by trading-day position within the year. It deliberately uses a fixed trading-day calendar rather than actual calendar month boundaries. This makes it an approximate seasonal alignment model particularly intended for US stocks and indices. Its seasonal pivots and histograms describe historical tendencies, not known future high/low dates or a complete trading strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed calculation or data contract is unresolved.

- Return aggregation and seasonal-pivot computation are undisclosed.

## How it works

- Index observations by the nth trading day of each year and aggregate historical percentage performance at matching positions.
- Approximate months and quarters as fixed groups of trading days rather than actual report/calendar intervals.
- Build seasonal high/low references from aggregated daily performance and anchor the display to the current year.

## Outputs and intended use

- Read mean performance histograms and a table comparing current actual change with the historical tendency.
- Manually offset the seasonal trace to compare previous years, recognizing alignment is approximate.

## Parameters and stated settings

- The model assumes 252 trading days annually, 21 per month and 63 per quarter; manual comparison offsets are about 252.

## Failure modes and caveats

- Years with different session counts drift relative to the fixed calendar; non-US markets may fit poorly.
- Historical seasonal tendencies can be sample-specific.

## Missing information and implementation boundary

- Daily return base, period compounding, year weighting, missing-day handling and seasonal-pivot extraction are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV provides the analysis data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism

```text
252 trading day calendar, not a 365 day calendar.
```

### E2: parameters

```text
every Month to be 21 trading days, and every Quarter to be 63 trading days.
```

### E3: mechanism

```text
"nth" trading day of the year
```

### E4: parameters, outputs_and_use

```text
manually offset it by ~252
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_wixmhdwt_seasonality_tfo](../../../strategy_research/tv_wixmhdwt_seasonality_tfo.md)

## Source

https://www.tradingview.com/script/wiXmhDwT-Seasonality-TFO/

Publication ID: wiXmhDwT. Source SHA-256: afd3135f73dff33dd7cf4209f75b16ed38bb438578950f8d6032ac5156f6ca78. Raw-description SHA-256: 85aff37f29908131f858628c6b3bdcff0ff84a562dfcf30de4f668de635a5b1e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
