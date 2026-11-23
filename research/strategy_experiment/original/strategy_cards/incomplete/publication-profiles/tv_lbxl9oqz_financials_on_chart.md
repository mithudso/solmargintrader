---

id: tv_profile_lbxl9oqz

name: "Financials on Chart"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Financials on Chart brings selected company fundamentals into a configurable chart panel. Its purpose is convenient financial inspection without leaving the price view. Users choose fields and reporting periods, including raw statement items, ratios, growth measures and several values calculated from fundamentals. Display customization changes presentation rather than investment logic. Currency conversion is conditional on USD quote currency, and some values are dimensionless. The source warns that fields/periods differ across markets and unavailable requests can error; a blank or failed field should not be treated as zero."

registry_key: null

runner: null

evaluation: null

---

# Financials on Chart

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Financials on Chart brings selected company fundamentals into a configurable chart panel. Its purpose is convenient financial inspection without leaving the price view. Users choose fields and reporting periods, including raw statement items, ratios, growth measures and several values calculated from fundamentals. Display customization changes presentation rather than investment logic. Currency conversion is conditional on USD quote currency, and some values are dimensionless. The source warns that fields/periods differ across markets and unavailable requests can error; a blank or failed field should not be treated as zero.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for displaying selected raw financial fields at selected reporting periods. Optional locally derived valuation formulas and currency-conversion timing remain outside this narrow raw-field reporting scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Fetch selected fundamental series using Pine financial() and calculate optional valuation measures from those inputs.
- Format each field with its chosen reporting period, precision, legend and styling.
- Optionally convert USD-denominated values to another supported currency.

## Outputs and intended use

- A panel of chosen fundamentals supports company/valuation research; no screening threshold or order rule is supplied.

## Parameters and stated settings

- Up to nine displayed fundamentals from a stated catalogue of 222 plus five derived values: market cap, earnings yield, P/B, P/E and price/sales.
- Position, row size, text/background, currency labels, abbreviations and per-field period/precision are configurable.

## Failure modes and caveats

- Reported/revised financials may not equal point-in-time information available historically.
- Currency and reporting-period mismatches can invalidate comparisons.
- Unavailable fields/periods cause errors according to the source.

## Missing information and implementation boundary

- Derived formulas are linked but not reproduced; release-date handling, revision policy, conversion timing and defaults are absent.

## Data requirements

Required inputs: company fundamental histories by reporting period, prices/share data for derived valuations, FX conversion rates when selected.

Repository input-class support: unavailable or unresolved. Fundamentals and reporting metadata are external to OHLCV, and field/period coverage is not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, purpose

```text
up to 9 fundamentals
```

### E2: parameters

```text
222 financials available in Pine
```

### E3: parameters, mechanism, readiness

```text
one of five values calculated
```

### E4: parameters, mechanism

```text
only done when the symbol's quote currency is USD.
```

### E5: risks

```text
configured financials cannot be fetched, an error will occur.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lbxl9oqz_financials_on_chart](../tv_lbxl9oqz_financials_on_chart.md)
- [tv_method_value_investing](../tv_method_value_investing.md)

## Source

https://www.tradingview.com/script/Lbxl9OqZ-Financials-on-Chart/

Publication ID: Lbxl9OqZ. Source SHA-256: f3ec3a6165f4e2a3007bae19f2e3c38f8d08d2fc6c89bef747dddc1edabaf453. Raw-description SHA-256: 604b647d07ac8569bdc1aefd81d33c34e17196ee855f9ad21104b6b167c5b5d7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
