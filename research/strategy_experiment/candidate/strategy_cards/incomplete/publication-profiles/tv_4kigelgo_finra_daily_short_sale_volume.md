---

id: tv_profile_4kigelgo

name: "FINRA Daily Short Sale Volume"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Display daily FINRA-reported short-sale transaction volume for a supported US stock and highlight days with unusually high activity relative to a moving average."

registry_key: null

runner: null

evaluation: null

---

# FINRA Daily Short Sale Volume

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Display daily FINRA-reported short-sale transaction volume for a supported US stock and highlight days with unusually high activity relative to a moving average.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The direct daily-column output is reproducible from the disclosed FINRA:<symbol>_SHORT_VOLUME ticker convention. This usable scope covers plotting that supplied series; exact moving-average highlighting remains a separate undisclosed detail.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Fetch the special FINRA short-volume ticker for the chart symbol or an explicitly selected alternative. Plot daily observations as columns and compare each with an average whose length is expressed in days.

## Outputs and intended use

- Brighter red columns mark observations above the average. An optional ticker-name table makes the requested source visible.
- Use the series to monitor reported short-sale transactions, not outstanding short positions; the author distinguishes it from short interest and notes incomplete exchange coverage.

## Parameters and stated settings

- An Other symbol checkbox selects another security. Average length is adjustable in days; the average and source table can be hidden. No default lookback is provided.

## Failure modes and caveats

- The author says the dataset excludes non-publicly disseminated activity and is not consolidated with exchange data. Short-sale turnover must not be interpreted directly as net bearish positioning.

## Missing information and implementation boundary

- The saved text does not establish present-day feed access, reporting lag, revision handling or a strategy linking the columns to trades.
- The moving-average family and default lookback are not disclosed, so exact average-line and brighter-column parity cannot be reconstructed from the description.

## Data requirements

Required inputs: FINRA daily short-sale-volume series, supported symbol mapping.

Repository input-class support: unavailable or unresolved. The feature requires FINRA-specific data rather than ordinary OHLCV. The saved description identifies the ticker convention but does not supply or verify the series.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Daily Short Sale ​Volume provides aggregated ​volume by security for all short trades executed and reported to FINRA during normal market hours, i.e., media-reported trades.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
It's important to note that Short Sale ​Volume is not consolidated with exchange data and excludes trading activity that is not publicly disseminated.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
The moving average's length is in days, as Short ​Volume is daily data.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
For example, NASDAQ:AAPL's Short Sale ​Volume data can be loaded on your chart via the FINRA:AAPL_SHORT_VOLUME ticker.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_4kigelgo_finra_daily_short_sale_volume](../tv_4kigelgo_finra_daily_short_sale_volume.md)

## Source

https://www.tradingview.com/script/4KIgeLGo-FINRA-Daily-Short-Sale-Volume/

Publication ID: 4KIgeLGo. Source SHA-256: 17655ae9e24efe224a9cf8ddcc2d41212cd472144f99295de08ff60157ac263d. Raw-description SHA-256: f47b4b94ecb878adc5f18eaff050e80494b4884ce872256d3a434c4ec167eff9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
