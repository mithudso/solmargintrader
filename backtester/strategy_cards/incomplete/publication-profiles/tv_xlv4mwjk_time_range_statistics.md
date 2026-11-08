---

id: tv_profile_xlv4mwjk

name: "Time Range Statistics"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Time Range Statistics summarizes a manually selected chart interval, combining familiar price statistics with volume, gaps and intermarket correlation. It lets the user study a specific episode instead of a fixed rolling window. The panel includes directional context based on higher-high versus lower-low counts, while chart lines expose the interval’s mean and extremes. These are descriptive statistics and do not establish a forecast."

registry_key: null

runner: null

evaluation: null

---

# Time Range Statistics

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Time Range Statistics summarizes a manually selected chart interval, combining familiar price statistics with volume, gaps and intermarket correlation. It lets the user study a specific episode instead of a fixed rolling window. The panel includes directional context based on higher-high versus lower-low counts, while chart lines expose the interval’s mean and extremes. These are descriptive statistics and do not establish a forecast.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Selected-range arithmetic mean, extrema, average volume and explicit gap tests are independently reproducible; normalized range and directional-count extras need further definition.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Select a bar-index range or extend from Start to the latest bar, then compute mean, normalized spread, percentage change, average volume and optional gap count.
- Detect gaps using opens beyond the prior high/low and calculate closing-price correlation with a selected instrument in the same range.

## Outputs and intended use

- Read the panel’s instrument/timeframe/date context and statistics, plus mean/high/low lines on the highlighted chart area.

## Parameters and stated settings

- Start defaults to 9000 and End to 10000; Start 0 plus evaluate-to-last-bar requests full available history. Correlation instrument defaults to GOOG and gap count is initially hidden.

## Failure modes and caveats

- Analytical: handpicked intervals create selection bias; close-level correlation can reflect common trends. The printed percentage-change denominator is End, so it differs from conventional start-based return wording.

## Missing information and implementation boundary

- Normalized-range formula, high/low counting details, data alignment, invalid-index handling and precise percentage-change sign convention need code verification.

## Data requirements

Required inputs: ohlcv, caller-selected comparison closing-price history.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
By default Start = 9000 and End = 10000
```

### E2: parameters, readiness

```text
Start = 0
```

### E3: parameters, readiness

```text
by default GOOG
```

### E4: mechanism, risks, readiness

```text
divided by the price at bar [i]End[/i]
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_xlv4mwjk_time_range_statistics](../../tv_xlv4mwjk_time_range_statistics.md)

## Source

https://www.tradingview.com/script/XLV4MwjK-Time-Range-Statistics/

Publication ID: XLV4MwjK. Source SHA-256: 1c29cb79f98978daa344b87c3bd006db0a1c021a37c7727a287a1612e20abcc7. Raw-description SHA-256: 08cf39cd61b05cbba3903d618959a4b7cd252537e4208ca89f6dec7186fe4140.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
