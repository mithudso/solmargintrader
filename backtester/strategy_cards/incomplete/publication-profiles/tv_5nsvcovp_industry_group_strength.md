---

id: tv_profile_5nsvcovp

name: "Industry Group Strength"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Industry Group Strength helps a trader locate leadership among peers rather than judging a stock solely against the broad market. It recognizes the charted stock’s industry, requests the predefined peer list, and ranks the group using a selected performance measure. This can reveal whether a candidate is leading a strong cohort or lagging its immediate competitors. A benchmark-relative measure and raw-return alternatives answer different questions, so the ranking mode matters. The result is a research and screening table, with no disclosed requirement to buy the highest-ranked stock or rebalance on a particular schedule."

registry_key: null

runner: null

evaluation: null

---

# Industry Group Strength

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Industry Group Strength helps a trader locate leadership among peers rather than judging a stock solely against the broad market. It recognizes the charted stock’s industry, requests the predefined peer list, and ranks the group using a selected performance measure. This can reveal whether a candidate is leading a strong cohort or lagging its immediate competitors. A benchmark-relative measure and raw-return alternatives answer different questions, so the ranking mode matters. The result is a research and screening table, with no disclosed requirement to buy the highest-ranked stock or rebalance on a particular schedule.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Relative-strength normalization and the industry-peer selection contract are missing.

- Relative-strength normalization and the industry-peer selection contract are missing.

## How it works

- Use predefined industry lists filtered for capitalization, price and primary listing status; identify the chart symbol’s group and retrieve its peers.
- Rank peers by YTD return, a chosen-lookback percentage return, or benchmark-relative strength.
- Compute raw RS as stock close divided by benchmark close, then normalize the rating.

## Outputs and intended use

- Table text and color-coded lines show performance; a percentile gradient highlights leaders and laggards.
- Use peer ranking to focus further stock research, not as a complete execution model.

## Parameters and stated settings

- List filters are capitalization above 2B and price above $10, plus primary listing status.
- RS defaults to S&P 500 and is normalized to 1–99; RS and percentage-return modes have user-selected lookbacks.

## Failure modes and caveats

- Predefined lists can omit delisted names and create survivorship bias.
- A normalized price ratio is not necessarily a cross-sectional percentile unless the undisclosed mapping establishes that.

## Missing information and implementation boundary

- Actual peer lists, as-of date, industry taxonomy, normalization formula, corporate-action treatment and missing-symbol rules are absent.

## Data requirements

Required inputs: industry classification and predefined peer universe, peer price histories, benchmark prices, market capitalization and listing status.

Repository input-class support: unavailable or unresolved. Cross-sectional histories, classifications and eligibility metadata are required. Current prose does not establish a point-in-time peer universe.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, required_data

```text
Market capitalization over 2B
[*]Price greater than $10
[*]Primary listing status
```

### E2: mechanism, readiness

```text
automatically recognizes the industry group of the current stock
```

### E3: mechanism

```text
dividing the closing price of the stock by the closing price of the S&P 500.
```

### E4: parameters, mechanism

```text
normalizes the RS value into a range from 1 to 99
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5nsvcovp_industry_group_strength](../tv_5nsvcovp_industry_group_strength.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/5NsvcOVp-Industry-Group-Strength/

Publication ID: 5NsvcOVp. Source SHA-256: 321aa00b69872294cd53aaed1215a449f6005dd7ccdbfcccdfbadf4db569e2ac. Raw-description SHA-256: 6a3579e365b33067a3d5fa1a68e4fcd7b8041e67c2e653486a9a44411537641d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
