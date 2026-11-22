---

id: tv_profile_6f7ztdvh

name: "Equity Bond Currency Dashboard"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This dashboard represents changing relative market prices as a network of apparent demand flows between currencies, equities and bond yields. It centers the diagram on the dollar and links each country’s currency to its local asset references. The arrows are a conceptual interpretation of strengthening and weakening prices, useful for intermarket context, rather than observations of actual investor transfers or a complete capital-flow accounting system."

registry_key: null

runner: null

evaluation: null

---

# Equity Bond Currency Dashboard

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This dashboard represents changing relative market prices as a network of apparent demand flows between currencies, equities and bond yields. It centers the diagram on the dollar and links each country’s currency to its local asset references. The arrows are a conceptual interpretation of strengthening and weakening prices, useful for intermarket context, rather than observations of actual investor transfers or a complete capital-flow accounting system.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Instrument references, arrow-state calculations and normalization are undisclosed.

- Instrument references, arrow-state calculations and normalization are undisclosed.

## How it works

- Infer currency-versus-dollar flow direction from currency strength and connect currencies to their country equity and bond-yield blocks.
- Draw normalized open/close side bars within the selected high-low range, with borders reflecting change versus the previous close.

## Outputs and intended use

- Follow arrows for the author’s demand-flow interpretation and compare asset-block bars across markets.

## Parameters and stated settings

- The diagram covers six countries and five dollar currency pairs; it needs at least 200 chart bars.
- Historical-flow display requires a setting; defaults favor futures so markets are live simultaneously where possible.

## Failure modes and caveats

- The source explicitly omits commodities, trade and rate/inflation channels; analytical: price movement is not direct evidence of capital flow.

## Missing information and implementation boundary

- Exact instruments, normalization equations, arrow thresholds, synchronization and historical availability are not specified.

## Data requirements

Required inputs: multi-country currency pairs, equity indices or futures, bond yields.

Repository input-class support: unavailable or unresolved. Synchronized external multi-asset histories and selected symbols are required; chart OHLCV alone is insufficient.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, purpose, readiness

```text
Equities, Bonds and Currencies of 6 countries.
```

### E2: parameters, readiness

```text
usd-currency pairs of 5 countries
```

### E3: parameters, readiness

```text
requires at least 200 bars in the chart
```

### E4: risks, readiness

```text
The flow is incomplete without commodities, import/export, interest/inflation rates of countries
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6f7ztdvh_equity_bond_currency_dashboard](../tv_6f7ztdvh_equity_bond_currency_dashboard.md)

## Source

https://www.tradingview.com/script/6F7zTDvH-Equity-Bond-Currency-Dashboard/

Publication ID: 6F7zTDvH. Source SHA-256: f8ed86669de365096d1934260e6767e570ce1b78d00c50c6eb55cf4e89502c44. Raw-description SHA-256: fe9d04dbf604ec309ede89c142c60f44f64080dc92f5a69e553b07b71e9fb550.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
