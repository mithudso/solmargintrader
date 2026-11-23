---

id: tv_profile_hcokncdk

name: "Percent Rank Histogram"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Percent Rank Histogram compares where each selected instrument currently sits within its own historical distribution. It uses percentile position rather than directly comparing raw price levels across assets, then colors columns and adds arrows for rising/falling rank. The author suggests midpoint readings as trend context, but percentile rank is relative position within a window rather than a forecast probability or a cross-sectional capitalization rank."

registry_key: null

runner: null

evaluation: null

---

# Percent Rank Histogram

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Percent Rank Histogram compares where each selected instrument currently sits within its own historical distribution. It uses percentile position rather than directly comparing raw price levels across assets, then colors columns and adds arrows for rising/falling rank. The author suggests midpoint readings as trend context, but percentile rank is relative position within a window rather than a forecast probability or a cross-sectional capitalization rank.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines percentile ranking and its caller-selectable window; unspecified display defaults do not block that computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For each selected series, calculate the share of historical observations less than or equal to its current value over the chosen rank window.
- Display ranked percentages as gradient columns and label whether the percentile increased or decreased.

## Outputs and intended use

- Compare assets’ relative historical positions; above/below midpoint is proposed as bullish/bearish context.

## Parameters and stated settings

- Supports ten instruments; example defaults include TOTAL and crypto names described as top-nine coins, without establishing a historical universe. Midpoint guide is 50. Rank length and column width are adjustable.

## Failure modes and caveats

- Analytical: high percentile can persist in a trend, and the chosen window changes interpretation; default top-coin wording does not establish current constituents.

## Missing information and implementation boundary

- Exact series selection, full default symbol list/window, tie implementation and display scaling are not provided.

## Data requirements

Required inputs: caller-selected instrument price histories.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source. Optional TOTAL aggregate market series has separate unverified feed coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
percentage of historical data points that are less than or equal to the current value
```

### E2: parameters, readiness

```text
up to 10 financial instruments
```

### E3: parameters, readiness

```text
middle scale line (50)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hcokncdk_percent_rank_histogram](../tv_hcokncdk_percent_rank_histogram.md)

## Source

https://www.tradingview.com/script/hcOKNCdK-Percent-Rank-Histogram/

Publication ID: hcOKNCdK. Source SHA-256: 1a1023818255b85fc3ab45aedc07230df729b42e27b834609bafff02541eea8f. Raw-description SHA-256: e6a9b5b44091d5a5d508041a937e9b1c8adb44a4e88601dfb77142a6f4a8ecaf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
