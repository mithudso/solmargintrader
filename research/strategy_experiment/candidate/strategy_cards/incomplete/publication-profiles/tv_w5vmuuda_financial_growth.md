---

id: tv_profile_w5vmuuda

name: "Financial Growth"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Financial Growth compares selected corporate financial series across reporting periods and presents their growth as plots, labels or a table. It is designed to make fundamental trends visible without manually transferring reports into another tool. The publication lists multiple measures but does not define growth formulas, release timing or denominator conventions. It therefore describes a financial reporting workflow rather than a reproducible stock-selection signal."

registry_key: null

runner: null

evaluation: null

---

# Financial Growth

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Financial Growth compares selected corporate financial series across reporting periods and presents their growth as plots, labels or a table. It is designed to make fundamental trends visible without manually transferring reports into another tool. The publication lists multiple measures but does not define growth formulas, release timing or denominator conventions. It therefore describes a financial reporting workflow rather than a reproducible stock-selection signal.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for positive-base percent growth on a supplied selected financial period series and comparison lag. CAGR, minimum4 semantics, zero/negative bases and feed/release parity remain incomplete.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow positive-base financial percentage growth: for a selected financial field observed in an ordered quarterly, annual or TTM series F, and caller-selected comparison lag k, compute 100×(F_t/F_(t−k)−1) when the comparison base is positive. The lag refers to supplied reporting observations. This standard percentage-growth interpretation does not resolve CAGR, the ambiguous minimum4 or source release alignment.
- Retrieve the selected platform financial series and compare quarterly, annual or trailing-twelve-month observations.
- Offer year-over-year, quarter-over-quarter and compound annual growth views for the selected comparison size.

## Outputs and intended use

- Choose revenue, net income, EBITDA, EPS, dividend per share, free cash flow or forward P/E.
- Toggle line, label and table displays independently to inspect growth history.

## Parameters and stated settings

- A minimum of 4 is mentioned for the growth comparison, but the unit and applicable calculation are ambiguous.
- Financial field, period and comparison size are selectable; defaults are absent.
- Choose field, reporting period and comparison size/lag k. Restrict this narrow output to positive bases and aligned observations; no period/default lag is invented.

## Failure modes and caveats

- Revisions, negative bases and missing reports can distort growth percentages.
- Forward P/E contains expectations and should not be treated as realized historical earnings.

## Missing information and implementation boundary

- Growth/CAGR equations, minimum-size meaning, negative/zero handling, feed identifiers and release alignment are absent.

## Data requirements

Required inputs: financial statements, forward valuation estimates.

Repository input-class support: unavailable or unresolved. Fundamental releases and their point-in-time availability are not supplied by chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, missing_information

```text
YoY, QoQ and CAGR is also available by this script (The minimum is 4).
```

### E2: required_data

```text
Revenue,  Net Income, EBITDA,  EPS,  DVPS,  Free Cash Flow and Forward PE
```

### E3: mechanism

```text
compare between Quarter, Annual and TTM
```

### E4: mechanism, parameters, readiness

```text
compare between Quarter, Annual and TTM in term of percent of growth.
```

### E5: mechanism, parameters, readiness

```text
just select the financial data, period and size of data to compare.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_w5vmuuda_financial_growth](../tv_w5vmuuda_financial_growth.md)

## Source

https://www.tradingview.com/script/w5VmuuDA-Financial-Growth/

Publication ID: w5VmuuDA. Source SHA-256: 287aee27597a625fc748e38ef288c780a9ed98ae5f54a746505fd2548fa679c8. Raw-description SHA-256: 627c78c0591ee9f31e722522433b8c2f7e4f342a76fea759439b1c4bb60b3b52.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
