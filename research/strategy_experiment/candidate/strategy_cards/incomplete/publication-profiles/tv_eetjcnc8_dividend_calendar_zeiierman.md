---

id: tv_profile_eetjcnc8

name: "Dividend Calendar (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Dividend Calendar organizes dividend events and estimated future payments into portfolio-oriented tables. It supports payout timing, dividend growth and monthly/yearly income planning, with separate ex-date and pay-date views. Historical-pattern estimates are not declared dividends, and a calendar around ex-dates does not by itself establish a profitable dividend-capture strategy."

registry_key: null

runner: null

evaluation: null

---

# Dividend Calendar (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dividend Calendar organizes dividend events and estimated future payments into portfolio-oriented tables. It supports payout timing, dividend growth and monthly/yearly income planning, with separate ex-date and pay-date views. Historical-pattern estimates are not declared dividends, and a calendar around ex-dates does not by itself establish a profitable dividend-capture strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Same-currency dividend calendar/totals is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Retrieve stock dividend dates/amounts, compute average payment growth and aggregate monthly/yearly totals.
- Optionally extrapolate future payments from historical data and combine custom holdings/share counts, amounts or payout months.
- For supplied dividend dates/per-share amounts and shares,cash=amount*shares. Assign selected ex-date or payout date and sum by calendar month/year in one currency. Forward estimates,growth,FX,tax/split and feed timing excluded.

## Outputs and intended use

- View full calendar, cumulative-month or summary income tables and configure upcoming/current payout alerts.
- Usable scope: Same-currency dividend calendar/totals. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Currency defaults to USD. Ex-date versus pay-date, forward estimates, growth years, holdings/share counts, amounts/months and table design are configurable without other numeric defaults.

## Failure modes and caveats

- Analytical: dividends can be changed or canceled, forecasts can be mistaken for announced cash flows and ex-date price adjustment matters for capture strategies.

## Missing information and implementation boundary

- Feed semantics, forward-estimation equation, growth estimator, FX conversion timing, split/tax treatment and alert timing are not disclosed.

## Data requirements

Required inputs: dividend event/amount histories, selected holdings/share counts, optional FX histories.

Repository input-class support: unavailable or unresolved. Requires external corporate-action data and caller portfolio configuration, absent from price OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
By default, it's set to USD
```

### E2: mechanism, readiness

```text
estimates future values based on historical data.
```

### E3: parameters, readiness

```text
Ex-dividend day or the Actual Payout day.
```

### E4: parameters, readiness

```text
number of shares they hold
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
[*] This setting allows users to customize the stocks they track, the number of shares they hold, the dividend payout amount, and the payout months.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
For those who follow a dividend capture strategy, this indicator can be invaluable. It can help in timing the buying and selling of stocks around their ex-dividend dates to maximize dividend income.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
This script is a comprehensive tool for tracking and analyzing stock dividend data. It calculates growth rates, monthly and yearly totals, and allows for custom date handling. Structured to be visually informative, it provides tables and alerts for the easy monitoring of dividend-paying stocks.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eetjcnc8_dividend_calendar_zeiierman](../tv_eetjcnc8_dividend_calendar_zeiierman.md)

## Source

https://www.tradingview.com/script/eETJcnc8-Dividend-Calendar-Zeiierman/

Publication ID: eETJcnc8. Source SHA-256: 8288cec59250b8b92623906843be82b2ff37319cae668c20460c6ce961537131. Raw-description SHA-256: 17de4327b7b7babaef87560c04ec2c89458aad2bec880815d4d258c40dd9d573.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
