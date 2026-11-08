---

id: tv_profile_yrff3z4j

name: "Financials - Comparing Companies"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Financials Comparing Companies places a small selected peer group in a sortable financial table. It is intended for same-sector comparison and supplements fundamentals with price, moving-average and volume context. The author uses objects as an implementation demonstration, but the financial purpose is peer analysis rather than a generic programming utility. No automatic ranking-to-trade or valuation cutoff follows from a sorted column."

registry_key: null

runner: null

evaluation: null

---

# Financials - Comparing Companies

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Financials Comparing Companies places a small selected peer group in a sortable financial table. It is intended for same-sector comparison and supplements fundamentals with price, moving-average and volume context. The author uses objects as an implementation demonstration, but the financial purpose is peer analysis rather than a generic programming utility. No automatic ranking-to-trade or valuation cutoff follows from a sorted column.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for chosen daily SMA/EMA values, one-bar rising/falling comparisons and volume averages in the selected peer table. Fundamental data/period mapping and sort rules remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow daily technical peer summary: for each supplied company daily-close series calculate two caller-selected SMA/EMA lengths. SMA_N is mean of the latest N closes; ordinary EMA_N uses alpha=2/(N+1). Compare each MA_t to its preceding value for rising/falling, with equal values left unclassified. Calculate mean daily volume over the selected window, initially described as20 days. This does not reproduce fundamental ratios or sorting.
- Retrieve EPS, valuation ratios, profitability, debt/equity, current ratio and market capitalization for selected companies.
- Sort the peer rows by the chosen financial field and supplement them with current price, moving averages and volume.

## Outputs and intended use

- Inspect same-sector relative fundamentals, header explanations and currency information.
- Choose SMA or EMA types and lengths; adjust table location and text size.

## Parameters and stated settings

- The comparison supports five companies and requires chart timeframe one day or higher.
- Two moving averages and an adjustable volume average initially described as 20 days are included.
- Choose up to five symbols, daily data, each MA type (SMA/EMA) and length, and volume-average period (source20-day example). EMA warmup/seed, ties and full fundamental table remain caveats.

## Failure modes and caveats

- Different currencies, report dates and accounting definitions can make apparently similar ratios incomparable.
- Selected peers do not constitute a historical point-in-time stock universe.

## Missing information and implementation boundary

- Financial feed/period mapping, derived-ratio equations, sort direction/ties and publication timing are absent.

## Data requirements

Required inputs: selected company fundamentals, selected company OHLCV.

Repository input-class support: unavailable or unresolved. Selected external series or user pivots are required beyond chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
5 companies only.
```

### E2: parameters

```text
Chart time frame must be 1Day or higher!
```

### E3: parameters

```text
2 Simple/Exponential moving average
```

### E4: parameters, mechanism, readiness

```text
Average volume (20 days), you can set the period
```

### E5: outputs_and_use

```text
companies from the same sector!
```

### E6: mechanism, parameters, readiness

```text
2 Simple/Exponential moving average, you can set the length, also it checks if it is rising/falling
```

### E7: mechanism, parameters, readiness

```text
You can set the type of Moving averages as SMA or EMA and you can also set the length for both
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_yrff3z4j_financials_comparing_companies](../tv_yrff3z4j_financials_comparing_companies.md)

## Source

https://www.tradingview.com/script/yRFF3z4J-Financials-Comparing-Companies/

Publication ID: yRFF3z4J. Source SHA-256: 43fd001d4a2a0654dde50e6554173ff6ea790e0b2f54750305b7be3c04fb44cb. Raw-description SHA-256: 253ae7bbc8dfb4cb88c5c7c611dbb7e8b5c333fa2e317ace2348bf84fa9902e8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
