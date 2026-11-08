---

id: tv_profile_tstsp9sk

name: "Peak Trading Activity Graphs [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Peak Trading Activity Graphs groups volume or volatility by calendar periods to reveal when activity has historically been relatively high or low. It is intended for choosing execution times and adjusting exposure to recurring conditions, rather than predicting the next price direction. Raw group medians and normalized median differences offer alternative visual contrast, while exchange time anchors the hourly examples."

registry_key: null

runner: null

evaluation: null

---

# Peak Trading Activity Graphs [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Peak Trading Activity Graphs groups volume or volatility by calendar periods to reveal when activity has historically been relatively high or low. It is intended for choosing execution times and adjusting exposure to recurring conditions, rather than predicting the next price direction. Raw group medians and normalized median differences offer alternative visual contrast, while exchange time anchors the hourly examples.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Calendar-group median volume and its min-to-max rescaling define an independent principal output; unspecified volatility mode remains outside this usable scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Group observations by month, day-of-month, weekday or hour and calculate median volume/volatility.
- Optionally rescale median differences so the smallest group is the low endpoint and the largest the high endpoint; render customizable graphs.

## Outputs and intended use

- Inspect seasonality in participation or movement and compare assets’ activity profiles before choosing session exposure.

## Parameters and stated settings

- Supports up to four graphs and 16 configurations. Median delta scales the smallest to 0 and largest to 100; volume/volatility, period, graph size and color maps are selectable.

## Failure modes and caveats

- Analytical: small calendar groups, changing session schedules and regime shifts can make apparent seasonal rankings unstable; normalized contrast can exaggerate small absolute differences.

## Missing information and implementation boundary

- Volatility formula, historical window, group counts, incomplete-period handling and minimum-sample rules are not stated.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to four different graphs and up to 16 different configurations.
```

### E2: parameters, mechanism, readiness

```text
The smaller median is 0 and the larger median is 100.
```

### E3: parameters, readiness

```text
All times are in exchange time.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_tstsp9sk_peak_trading_activity_graphs_luxalgo](../../tv_tstsp9sk_peak_trading_activity_graphs_luxalgo.md)

## Source

https://www.tradingview.com/script/TsTSP9sk-Peak-Trading-Activity-Graphs-LuxAlgo/

Publication ID: TsTSP9sk. Source SHA-256: 295ed9a3d2c47ff728bd2b33fa4ce7643418bb339242eed5a6b6373b8b25075c. Raw-description SHA-256: fced2e445c12219a23225ff6515bd3c875fe613094fe372d2f2b56739d2ed5a9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
