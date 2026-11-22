---

id: tv_profile_an7yrdfo

name: "PriceFormat"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Format prices and price changes in the instrument-appropriate notation so financial chart labels match the intended tick/pip/fraction conventions."

registry_key: null

runner: null

evaluation: null

---

# PriceFormat

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Format prices and price changes in the instrument-appropriate notation so financial chart labels match the intended tick/pip/fraction conventions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Interfaces and financial purpose are clear, but exact format/rounding algorithms and instrument metadata mappings are not reproducible.

- Format detection and tick/fraction/pip mappings
- Rounding/negative/subtick semantics
- Precision/language enum rules

## How it works

- Detect chart formatting class, convert values to decimal/pip/fraction/volume representations and expose a general string-conversion alternative. Measure a pair of prices as both formatted distance and tick count; callers can override precision/language unavailable from chart settings.

## Outputs and intended use

- Use formatted strings in labels, boxes or tables rather than mistaking generic decimal conversion for correct financial notation. Auxiliary format detectors/converters expose finer control over separators, tick parameters and scientific notation.

## Parameters and stated settings

- Inputs include price, precision/language enums, allowPips, minimum tick, price scale/minimum movement, separators and spacing. The examples default Precision.DEFAULT and English; exhaustive enum mappings are not provided.

## Failure modes and caveats

- Incorrect metadata or manually selected locale/precision can round or display prices misleadingly. Formatting is presentation only and must not replace numeric order-price validation.

## Missing information and implementation boundary

- Rounding/tie policy, negative/subtick behavior, format detection rules, pip/fraction mappings and tick-change calculation details are absent.

## Data requirements

Required inputs: caller price values, symbol tick/price-scale metadata, manual precision/language selection.

Repository input-class support: available. Prices plus public symbol metadata and caller choices are sufficient data classes; no external feed is intrinsically required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
matching the same format that TradingView uses to display open/high/low/close prices
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Measures a change in price in terms of both distance and ticks.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
PriceFormat.Precision.DEFAULT
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
PriceFormat.Language.ENGLISH
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Minimum tick size.
```

## Source

https://www.tradingview.com/script/An7YRDFo-PriceFormat/

Publication ID: An7YRDFo. Source SHA-256: d3d0730a62bc2c00952ac1b0b3d578acdaa5e3315780bf8c459cc5ca54797f1a. Raw-description SHA-256: d31ad7f663dee923d3528d438a47df4ae58bbbbfb70205b3a95b46a1a4f2caae.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
