---

id: tv_profile_bluvjpa3

name: "Aggregate BTC Candles"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Build a composite Bitcoin candle history that reduces reliance on one exchange and moderates exchange-specific wicks or gaps."

registry_key: null

runner: null

evaluation: null

---

# Aggregate BTC Candles

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build a composite Bitcoin candle history that reduces reliance on one exchange and moderates exchange-specific wicks or gaps.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact OHLC construction, symbol universe, outlier handling, normalization and historical constituent policy are missing.

- Exact OHLC construction, symbol universe, outlier handling, normalization and historical constituent policy are missing.

## How it works

- Aggregate price information from several BTC exchange tickers using arrays to obtain medians and averages. The aim is cleaner historical candles despite flash-crash wicks, missing observations and erratic early exchange data.

## Outputs and intended use

- Use composite candles for trendlines, support/resistance, algorithms or downstream indicators. They represent a synthetic index, not necessarily a price executable on any venue.

## Parameters and stated settings

- The description supplies no constituent list, weighting method, aggregation choice or default coverage window.

## Failure modes and caveats

- Changing constituents and missing-history availability can introduce discontinuities and retrospective selection bias. A median price can suppress a real venue-specific event.

## Missing information and implementation boundary

- Exact OHLC construction, symbol universe, outlier handling, normalization and historical constituent policy are missing.

## Data requirements

Required inputs: multiple BTC exchange price histories, constituent and missing-data rules.

Repository input-class support: unavailable or unresolved. The composite requires a multi-exchange universe and aligned histories that the description does not identify or supply.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This script creates candles based on an aggregated Index price from various BTC exchange tickers.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It uses the new Array functionality to generate median and averages, and is entirely original work.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bluvjpa3_aggregate_btc_candles](../tv_bluvjpa3_aggregate_btc_candles.md)

## Source

https://www.tradingview.com/script/bLUVjPa3-Aggregate-BTC-Candles/

Publication ID: bLUVjPa3. Source SHA-256: b3f154f9ea61d7b471e29d772d00552a7315cf0373c30e54e75ffbcd408784b5. Raw-description SHA-256: 4e8aeb4f71033d5a86daa01cfc81bc9a427177a246b32f102585cb7170fe0d77.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
