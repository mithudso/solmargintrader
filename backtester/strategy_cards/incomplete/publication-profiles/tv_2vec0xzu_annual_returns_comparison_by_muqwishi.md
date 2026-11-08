---

id: tv_profile_2vec0xzu

name: "Annual Returns % Comparison [By MUQWISHI]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Annual Returns % Comparison provides a visual history of how two chosen instruments changed from year to year. Its purpose is comparative performance inspection: the reader can see which symbol led in a given year and how the pattern changes across the chosen date range. The output is constructed as a table-based paired column display, rather than an entry signal on the price chart. Adjusted-versus-unadjusted data selection is particularly relevant to comparison, because that choice can change the economic interpretation of the reported returns. The source does not establish whether the adjustment constitutes a full total-return calculation."

registry_key: null

runner: null

evaluation: null

---

# Annual Returns % Comparison [By MUQWISHI]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Annual Returns % Comparison provides a visual history of how two chosen instruments changed from year to year. Its purpose is comparative performance inspection: the reader can see which symbol led in a given year and how the pattern changes across the chosen date range. The output is constructed as a table-based paired column display, rather than an entry signal on the price chart. Adjusted-versus-unadjusted data selection is particularly relevant to comparison, because that choice can change the economic interpretation of the reported returns. The source does not establish whether the adjustment constitutes a full total-return calculation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Annual return endpoints and partial-year calculation are not defined.

- Annual return endpoints and partial-year calculation are not defined.

## How it works

- Compute historical annual percentage changes for the selected symbols and place each period’s results in paired columns.
- Render those columns using a Pine table and reveal individual values in hover tooltips.

## Outputs and intended use

- Paired annual-return columns support relative historical comparison; symbol colors identify each series.
- Tooltips expose the value for an individual column.

## Parameters and stated settings

- Two symbols and start/end dates are user inputs.
- Users choose adjusted or unadjusted data, table position, column dimensions and background/border/text colors.

## Failure modes and caveats

- Comparisons can be distorted by unequal histories, partial years, corporate actions or inconsistent adjustments.
- Historical leadership does not itself define an investable rotation rule.

## Missing information and implementation boundary

- Exact year-boundary prices, partial-year treatment and adjustment methodology are not specified.
- No rebalance, entry, exit, benchmark or transaction-cost rules are given.

## Data requirements

Required inputs: two symbol price histories, corporate-action adjustment series when selected.

Repository input-class support: unavailable or unresolved. The description requires independently chosen symbols and optionally adjusted histories; their availability and adjustment semantics are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, required_data, readiness

```text
compare the historical annual percentage change of any two symbols.
```

### E2: outputs_and_use

```text
each period has pair columns showing the yearly percentage change for entered symbols.
```

### E3: parameters

```text
Enter [Start - End] date range.
```

### E4: parameters

```text
Choose the output data whether adjusted or not.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_2vec0xzu_annual_returns_comparison_by_muqwishi](../../../strategy_research/tv_2vec0xzu_annual_returns_comparison_by_muqwishi.md)

## Source

https://www.tradingview.com/script/2VEC0XzU-Annual-Returns-Comparison-By-MUQWISHI/

Publication ID: 2VEC0XzU. Source SHA-256: 196a8a3b27cebdeda95eacfdf94b3a2b1497d902178a05e58434f5137401683f. Raw-description SHA-256: d488e8691810c66c92707f24e5cde35a7e164b2e0273b5eadc624288d62460ad.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
