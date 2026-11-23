---

id: tv_profile_lg5vvckk

name: "MarketHolidays"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "MarketHolidays supplies market-closure timestamps so other indicators and strategies can account for non-trading days. It is execution/calendar infrastructure, not a directional signal. Its datasets are split across libraries for compilation and performance reasons, then combined for the requested country. Historical special closures are included according to the source, but completeness and future updates are not independently established."

registry_key: null

runner: null

evaluation: null

---

# MarketHolidays

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

MarketHolidays supplies market-closure timestamps so other indicators and strategies can account for non-trading days. It is execution/calendar infrastructure, not a directional signal. Its datasets are split across libraries for compilation and performance reasons, then combined for the requested country. Historical special closures are included according to the source, but completeness and future updates are not independently established.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The closure dataset has no disclosed country/date coverage, timezone or timestamp convention, so its core calendar contract cannot be reproduced.

- The closure dataset has no disclosed country/date coverage, timezone or timestamp convention, so its core calendar contract cannot be reproduced.

## How it works

- Generate timestamp arrays with a Python process using pandas_market_calendars, then aggregate period-specific data for a requested country.

## Outputs and intended use

- Call getHolidays to receive an array of holiday/non-trading-day timestamps for use in another financial script.

## Parameters and stated settings

- Country input accepts syminfo.country or an ISO 3166-1 alpha-2 code. No default country or date-coverage limits are supplied.

## Failure modes and caveats

- Analytical: country-level holidays can differ from a specific exchange or product calendar, and early closes or exceptional future changes may require separate handling.

## Missing information and implementation boundary

- Covered countries, date range, timezone, timestamp convention, update policy and unsupported-code behavior are not disclosed.

## Data requirements

Required inputs: country code, market-closure timestamp dataset.

Repository input-class support: unavailable or unresolved. Requires the library’s external calendar dataset and caller country; OHLCV is not a substitute for calendar coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
including historical special market closures
```

### E2: purpose, readiness

```text
account for non-trading days.
```

### E3: parameters, readiness

```text
ISO 3166-1 alpha-2 format.
```

### E4: outputs_and_use, readiness

```text
An array of timestamps of market holidays
```

## Source

https://www.tradingview.com/script/LG5VVCkK-MarketHolidays/

Publication ID: LG5VVCkK. Source SHA-256: 93fc04b409f30e6c106364e099fbab52bd504d5e265d7c2fb1c31777d824ba06. Raw-description SHA-256: aba34e708cf30e2b01288de81a8a2af080e4e7757bdece3b04b18464893750eb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
