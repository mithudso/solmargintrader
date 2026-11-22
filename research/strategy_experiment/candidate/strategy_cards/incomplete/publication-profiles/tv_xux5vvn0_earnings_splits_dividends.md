---

id: tv_profile_xux5vvn0

name: "Earnings, Splits, Dividends"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Demonstrate access to corporate-event series by explaining how event attributes are encoded in a TradingView internal representation."

registry_key: null

runner: null

evaluation: null

---

# Earnings, Splits, Dividends

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Demonstrate access to corporate-event series by explaining how event attributes are encoded in a TradingView internal representation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Given event-series records in the disclosed historical representation, the earnings, split and dividend field mappings define a reproducible decoding procedure. This scope does not establish current feed access or compatibility.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Map earnings report timestamps, estimates, reported/actual values and fiscal periods onto named series fields. Similar mappings expose split dates and ratios, and dividend ex-dates and amounts.

## Outputs and intended use

- Use the example to retrieve and decode event data. It is an ingestion demonstration rather than an earnings or corporate-action trading rule.

## Parameters and stated settings

- No default ticker or date range is provided. Field mappings are disclosed rather than configurable strategy thresholds.

## Failure modes and caveats

- The author explicitly warns that the internal data representation can change at any time. Misreading the field mappings could confuse estimates, actual values or split ratios.

## Missing information and implementation boundary

- Request syntax, present-day compatibility, timestamp alignment, adjustments and revision handling require code and current documentation.

## Data requirements

Required inputs: earnings event series, split event series, dividend event series.

Repository input-class support: unavailable or unresolved. Corporate-event feeds are external to OHLCV. The saved example supplies mappings, not the event histories or verified current access.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
That way is inner representation of data in TradingView, so it can be changed any time.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
time:   report date (unix time stamp)
open:  estimate value
low:    reported value
close:  actual value
high:   fiscal period (unix time stamp)
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
time:  split date (unix time stamp)
close: split denominator
open: split numerator
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
time:  ex-dividend date (unix time stamp)
close: amount
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xux5vvn0_earnings_splits_dividends](../tv_xux5vvn0_earnings_splits_dividends.md)

## Source

https://www.tradingview.com/script/XUX5VVN0-Earnings-Splits-Dividends/

Publication ID: XUX5VVN0. Source SHA-256: 9a2ebda9cd40f0bcf9682bcaa091958c5a5e5f08505ed42c194a18107a89c30e. Raw-description SHA-256: be83dd48e602553f2447c8b8e3161ae669d02530d5020fc69aa5648a5c05bdd0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
