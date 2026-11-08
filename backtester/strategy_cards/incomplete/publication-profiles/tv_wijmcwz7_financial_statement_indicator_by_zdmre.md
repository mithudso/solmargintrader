---

id: tv_profile_wijmcwz7

name: "Financial Statement Indicator by zdmre"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Financial Statement Indicator summarizes a company through income-statement, balance-sheet and cash-flow/statistics tables. Its purpose is to support fundamental review directly on the chart rather than calculate a technical entry signal. The source enumerates reported and ratio fields, giving a useful inventory of what the dashboard exposes. It does not explain whether ratios come directly from a vendor or are calculated locally, and it does not supply reporting-period or publication-timing contracts."

registry_key: null

runner: null

evaluation: null

---

# Financial Statement Indicator by zdmre

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Financial Statement Indicator summarizes a company through income-statement, balance-sheet and cash-flow/statistics tables. Its purpose is to support fundamental review directly on the chart rather than calculate a technical entry signal. The source enumerates reported and ratio fields, giving a useful inventory of what the dashboard exposes. It does not explain whether ratios come directly from a vendor or are calculated locally, and it does not supply reporting-period or publication-timing contracts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed calculation or data contract is unresolved.

- The financial field/period and ratio-computation contracts are absent.

## How it works

- Populate an income view with revenue, net profit, EPS, diluted EPS and price/earnings.
- Populate a balance-sheet view with assets, equity, book value, debt and debt/equity.
- Add profitability, liquidity and cash-flow fields in a statistics view.

## Outputs and intended use

- Review corporate financial condition across the separate summaries.
- Use the tables as analysis inputs; no valuation threshold, ranking or order rule is prescribed.

## Parameters and stated settings

- Three tables are described; no numeric defaults or reporting-period settings are supplied.

## Failure modes and caveats

- Statements and ratios can refer to different reporting dates or revised figures.
- Cross-company comparison requires consistent currencies, accounting definitions and denominators.

## Missing information and implementation boundary

- Feed fields, period selection, ratio formulas, units, missing-data behavior and point-in-time release alignment are unspecified.

## Data requirements

Required inputs: company financial statements, valuation and profitability ratios.

Repository input-class support: unavailable or unresolved. Fundamental releases and their point-in-time availability are not supplied by chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
3 Tables;
```

### E2: mechanism

```text
[b]Income Statement Table:[/b]
Revenue
Net Profit
EPS
EPS-D
P/E
```

### E3: outputs_and_use

```text
Return On Equity
Return On Asset
Return On Invested Capital
Quick Ratio
Free Cash Flow
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_value_investing](../tv_method_value_investing.md)
- [tv_wijmcwz7_financial_statement_indicator_by_zdmre](../tv_wijmcwz7_financial_statement_indicator_by_zdmre.md)

## Source

https://www.tradingview.com/script/wiJMcWZ7-Financial-Statement-Indicator-by-zdmre/

Publication ID: wiJMcWZ7. Source SHA-256: 0b97ebfd0846207a9997ce719035138e50f4fa2d2aeeee8eb5bd57790f5b2aeb. Raw-description SHA-256: 5fe942f231605ef471069e0e4e757480cd0c6f0552b75992695bddea8a2cc82f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
