---

id: tv_profile_7qjxp2op

name: "Fundamentals Graphing [Kioseff Trading]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare company fundamental metrics across a chosen asset set using adaptable charts and sortable historical reporting-period values."

registry_key: null

runner: null

evaluation: null

---

# Fundamentals Graphing [Kioseff Trading]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare company fundamental metrics across a chosen asset set using adaptable charts and sortable historical reporting-period values.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact metric identifiers, currency/unit conversion, publication-date alignment, universe membership and missing-report treatment are unspecified.

- Exact metric identifiers, currency/unit conversion, publication-date alignment, universe membership and missing-report treatment are unspecified.

## How it works

- Retrieve quarterly/annual financial fields, optionally from earlier periods, sort observations and render scatter, histogram, bar or pie displays that resize with the chart. Reverse scales or colors when a metric's sign/value ordering requires it.

## Outputs and intended use

- Use graph shape and ranking for cross-company financial comparison. Search and industry presets assist navigation; the tool supplies no explicit valuation score or trading rule.

## Parameters and stated settings

- The text describes comparison across forty assets and ten industry presets, custom symbols, report-period lookback, graph type, sorting and reversible display. Metric/period defaults are not listed.

## Failure modes and caveats

- Accounting units, sectors, report timing and restatements can undermine comparability. A selected present-day preset is not a point-in-time historical universe, and reversed color does not prove financial quality.

## Missing information and implementation boundary

- Exact metric identifiers, currency/unit conversion, publication-date alignment, universe membership and missing-report treatment are unspecified.

## Data requirements

Required inputs: financial statement metrics for selected companies, reporting-period histories and symbol universe.

Repository input-class support: unavailable or unresolved. Fundamental feeds and a defined cross-company universe are external requirements not supplied here.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
compare almost any fundamental metric across 40 assets
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]10 industry presets
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Retrieve, graph, and compare fundamental data by quarter/year.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
All data retrieved by the indicator is sortable
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7qjxp2op_fundamentals_graphing_kioseff_trading](../tv_7qjxp2op_fundamentals_graphing_kioseff_trading.md)

## Source

https://www.tradingview.com/script/7qjXp2op-Fundamentals-Graphing-Kioseff-Trading/

Publication ID: 7qjXp2op. Source SHA-256: c4bfbe7d566621157b2c381db6db43b7b36d46f4399a0f211c884b76c6880203. Raw-description SHA-256: f83d8fcb664666f6f6c28ac5fb7334566eb73bf15296ada49df82b3a780823df.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
