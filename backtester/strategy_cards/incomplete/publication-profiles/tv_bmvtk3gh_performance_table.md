---

id: tv_profile_bmvtk3gh

name: "Performance Table"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Display continuously updated percentage performance over several familiar horizons in a compact on-chart table."

registry_key: null

runner: null

evaluation: null

---

# Performance Table

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display continuously updated percentage performance over several familiar horizons in a compact on-chart table.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The return equation and each daily lookback horizon are explicit, defining the table computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Calculate percentage change as current minus past value, multiplied by 100 and divided by past value. Horizon labels use daily-bar offsets rather than exact calendar-month durations.

## Outputs and intended use

- Use the table to monitor current performance. The author notes that its real-time updates can differ from the less frequently updated sidebar.

## Parameters and stated settings

- Week/month/quarter/half-year/year references use closes 5,21,63,126 and 251 daily bars back; YTD uses the previous year's close.

## Failure modes and caveats

- Fixed trading-bar approximations can differ from calendar periods. Intrabar current prices make displayed returns move during a live bar.

## Missing information and implementation boundary

- Price adjustments, missing daily history, zero denominators and exact year-boundary selection are not described.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history. Availability refers to input class, not code validation or cached history.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
(Current value - Past value) * 100 / Past value
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*][b]1W[/b] - close 5 daily bars ago
[*][b]1M[/b] - close 21 daily bars ago
[*][b]3M[/b] - close 63 daily bars ago
[*][b]6M[/b] - close 126 daily bars ago
[*][b]YTD[/b] - close of the past year
[*][b]1Y[/b] - close 251 daily bars ago
```

## Source

https://www.tradingview.com/script/BmvtK3GH-Performance-Table/

Publication ID: BmvtK3GH. Source SHA-256: 399e3ef3591be6805dd86baf4f5a2a89a2acf2add4b5b2b42efb9266624f17ba. Raw-description SHA-256: ded7008ebb3a274cbdfb7d3919682f59d62d40f5179699a18b587523a07a5520.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
