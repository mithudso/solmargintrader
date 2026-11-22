---

id: tv_profile_qypmcjka

name: "Lowest / Highest From Widget"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Lowest / Highest From Widget contextualizes the current price by finding when the market was last beyond it. It helps answer how far back one must look for a higher or lower observation, giving a temporal reference for a notable present value. It is descriptive market-history analysis rather than a forecast of what happens after a new extreme."

registry_key: null

runner: null

evaluation: null

---

# Lowest / Highest From Widget

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Lowest / Highest From Widget contextualizes the current price by finding when the market was last beyond it. It helps answer how far back one must look for a higher or lower observation, giving a temporal reference for a notable present value. It is descriptive market-history analysis rather than a forecast of what happens after a new extreme.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Most-recent prior daily scalar search is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Search for the most recent day when price was higher or lower than the current value, then connect that reference with a line.
- For caller-selected daily x[t], search backward independently for first x[t-j]>x[t] and first x[t-j]<x[t]. Report matching dates/values and connect each to current. Strict comparisons follow higher/lower; caller handles no-match initialization.

## Outputs and intended use

- Read a table of previous high/low information and the connecting line to understand the historical recency of the current level.
- Usable scope: Most-recent prior daily scalar search. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- No price-source selection, search horizon, timeframe rule or defaults are supplied.

## Failure modes and caveats

- Analytical: the current value can change intrabar and the returned historical comparison does not measure future return likelihood.

## Missing information and implementation boundary

- Strict versus inclusive comparison, high/low versus close source, search exhaustion and daily mapping are not documented.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
compute most recent day when price was higher / lower than current
```

### E2: outputs_and_use, readiness

```text
Line coming from that value to the current one
```

### E3: outputs_and_use, readiness

```text
A table with previous low/high information
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
Just add it to chart and script will compute most recent day when price was higher / lower than current and it will display:
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qypmcjka_lowest_highest_from_widget](../tv_qypmcjka_lowest_highest_from_widget.md)

## Source

https://www.tradingview.com/script/QyPmcjKa-Lowest-Highest-From-Widget/

Publication ID: QyPmcjKa. Source SHA-256: 018f8ae661606156252615492748b0c7b8cf63dd424a7da90c43b67727799a32. Raw-description SHA-256: 4f4a735e3bd57c382a6583bd33c0a04cf2f4a15c6fd50cd12c127d610fb77c3a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
