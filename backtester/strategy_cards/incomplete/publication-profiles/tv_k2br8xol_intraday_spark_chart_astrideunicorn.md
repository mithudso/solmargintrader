---

id: tv_profile_k2br8xol

name: "Intraday Spark Chart [AstrideUnicorn]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Show intraday performance relative to the session's opening price through a compact percentage-change sparkline."

registry_key: null

runner: null

evaluation: null

---

# Intraday Spark Chart [AstrideUnicorn]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Show intraday performance relative to the session's opening price through a compact percentage-change sparkline.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for daily-open percentage change and sign coloring on supplied session-labelled prices; exact exchange-calendar and plotting parity remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For a supplied daily-session opening price O and current price P, express performance as 100*(P-O)/O. Zero marks O; color the area/line green above O and red below O. Update during the session and retain the final daily percentage at session close.
- Separate days with dotted vertical markers and label their daily opens. Asset selection defaults to the chart symbol.

## Outputs and intended use

- Green indicates above-open performance, red below-open performance and zero the daily open. Use the chart as a session-bias view; the author's opening-range-breakout use case does not itself define an opening range or trigger.

## Parameters and stated settings

- Asset defaults to the chart symbol and can be changed. The author recommends one-minute through four-hour charts and warns on higher timeframes.

## Failure modes and caveats

- Daily open depends on session conventions. Relative-to-open direction does not measure volume conviction or independently predict settlement.

## Missing information and implementation boundary

- Exact session timezone/calendar, extended-hours treatment, missing opening bars and equality coloring are unspecified. Final daily percentage is stated to update at session close, but its exact platform event timing is not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
A green area/line indicates price is above the daily open (bullish).
A red area/line signals price is below the daily open (bearish).
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Best paired with: 1m to 4H timeframes (auto-warns on higher TFs).
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Defaults to the current chart symbol.
```

### E4: mechanism, parameters, readiness

```text
Real-time % change from daily open.
```

### E5: mechanism, parameters, readiness

```text
Final daily % change (updated at session close).
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_k2br8xol_intraday_spark_chart_astrideunicorn](../../tv_k2br8xol_intraday_spark_chart_astrideunicorn.md)
- [tv_method_intermarket_correlation](../../tv_method_intermarket_correlation.md)
- [tv_method_opening_range](../tv_method_opening_range.md)

## Source

https://www.tradingview.com/script/k2bR8xoL-Intraday-Spark-Chart-AstrideUnicorn/

Publication ID: k2bR8xoL. Source SHA-256: 6258a189f261e8d7c43ee46dc1b668bd7f4c34e0bea7e932b0fb8929ab68e363. Raw-description SHA-256: bdea9a7d3ea74edf069f289eba81c6aaaf6c98be5e8cb8047814dfafd2dc9480.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
