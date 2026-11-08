---

id: tv_profile_lu0mtsud

name: "Earnings Snapshot [Trendoscope]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Earnings Snapshot organizes historical stock EPS releases, future estimates and associated price growth into a chart table and release-date labels. It replaces manual comparisons of quarterly reports with a compact view of growth and price reaction. Revenue is expressly excluded because the author had not resolved its data presentation. This is fundamental-event visualization rather than an alerting or backtesting system; a favorable color should not be treated as an independently verified earnings beat or trading recommendation."

registry_key: null

runner: null

evaluation: null

---

# Earnings Snapshot [Trendoscope]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Earnings Snapshot organizes historical stock EPS releases, future estimates and associated price growth into a chart table and release-date labels. It replaces manual comparisons of quarterly reports with a compact view of growth and price reaction. Revenue is expressly excluded because the author had not resolved its data presentation. This is fundamental-event visualization rather than an alerting or backtesting system; a favorable color should not be treated as an independently verified earnings beat or trading recommendation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for positive-base actual-EPS quarter-over-quarter and four-quarter growth. Event-price sampling, future estimates and the complete seven-factor score remain outside scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow historical actual-EPS growth: given ordered quarterly actual EPS E_q, calculate Q2Q=100×(E_q/E_(q−1)−1) and Y2Y=100×(E_q/E_(q−4)−1), restricted to positive comparison bases. Use four reported quarterly observations back, not inferred calendar-year alignment. Price-growth and future-estimate score components are separate.
- Retrieve actual, estimated and standardized EPS and compare earnings and prices with the preceding quarter and four quarters earlier.
- For each comparison add or subtract one for positive earnings growth, positive price growth and earnings growth exceeding price growth; repeat for year-over-year and add the future-estimate direction.

## Outputs and intended use

- Show complete text or compact score labels with hover details, plus an optional growth table.
- Review slowing growth, price/earnings divergence and upcoming estimate direction around earnings dates.

## Parameters and stated settings

- Seven factors produce scores from -7 to +7. Historical lookback reaches 24 quarters.
- Display mode, label size and table visibility are configurable.
- Use supplied ordered actual quarterly EPS; quarter lags are one and four, with strictly positive bases for this narrow standard percentage-change calculation. Zero/negative EPS, irregular reporting and release/revision timing remain caveats.

## Failure modes and caveats

- Quarter-based indexing assumes regular reporting and may misalign irregular issuers.
- Negative or zero EPS bases complicate percentage-growth interpretation.

## Missing information and implementation boundary

- Price sampling at earnings events, zero/negative-denominator handling and future-estimate feed timing are not specified.

## Data requirements

Required inputs: ohlcv, actual and estimated quarterly EPS, earnings release calendar.

Repository input-class support: unavailable or unresolved. The required external event or detailed feed is not established by chart OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism

```text
Since there are 7 factors, the score can vary from -7 to +7.
```

### E2: mechanism

```text
Y2Y, based on 4 quarters back
```

### E3: parameters

```text
Configurable history lookback (up to 24 quarters)
```

### E4: outputs_and_use

```text
No alerts or backtesting integration; this is purely a visualization tool.
```

### E5: purpose

```text
revenue details are not included
```

### E6: mechanism, parameters, readiness

```text
Computes percentage changes in earnings and price compared to the previous quarter (Last), year-over-year (Y2Y, based on 4 quarters back)
```

### E7: mechanism, parameters, readiness

```text
Assumes quarterly earnings; irregular reporting schedules may affect Y2Y accuracy.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_lu0mtsud_earnings_snapshot_trendoscope](../../tv_lu0mtsud_earnings_snapshot_trendoscope.md)
- [tv_method_value_investing](../tv_method_value_investing.md)

## Source

https://www.tradingview.com/script/lu0MTsuD-Earnings-Snapshot-Trendoscope/

Publication ID: lu0MTsuD. Source SHA-256: f08c3b3e8c613e7f7e3563492633b1448f8a0ede5b77256d402305188b997dbb. Raw-description SHA-256: 31ff18e3fc99c279f393e696ac834bcb879cfcf03aa0f8d9a62b160b9406632b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
