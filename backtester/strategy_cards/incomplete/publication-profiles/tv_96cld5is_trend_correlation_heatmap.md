---

id: tv_profile_96cld5is

name: "Trend Correlation Heatmap"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare price-to-time correlation across horizons and chart resolutions to describe the direction and consistency of fitted market trends."

registry_key: null

runner: null

evaluation: null

---

# Trend Correlation Heatmap

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare price-to-time correlation across horizons and chart resolutions to describe the direction and consistency of fitted market trends.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The basic correlation statistic is clear, but the source-specific grid and extremum/change aggregation are not reproducible.

- Timeframe/lookback grid and alignment
- Extreme aggregation and change formula

## How it works

- Calculate Pearson correlation between price and advancing time for multiple lookback/timeframe combinations. Track the strongest positive and negative correlations and changes in those extremes over a recent interval.

## Outputs and intended use

- Read positive values as rising and negative as falling fitted trends, inspect multi-horizon agreement and optionally use the best-fitting horizon to select another indicator's length. A legend explains the distinct colors.

## Parameters and stated settings

- Timeframes, legend and extreme-change displays can be toggled. Max/Min change uses fourteen prior candles; worked examples span fifty to five-hundred bars, not a fully specified default grid.

## Failure modes and caveats

- High price/time correlation is in-sample trend fit, not a probability of continuation or breakout. Searching many lookbacks and then tuning averages to the winner creates selection bias.

## Missing information and implementation boundary

- The complete horizon/timeframe grid, correlation source, time alignment, extreme selection and precise change formula are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described model uses ordinary market history; missing algorithms remain specification gaps, not missing raw price data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
traditional Pearson Correlation Coefficient or R value
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
change in correlation over the previous 14 candles.
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
tracks the correlation of a ticker to time on multiple timeframes.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_96cld5is_trend_correlation_heatmap](../tv_96cld5is_trend_correlation_heatmap.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/96Cld5iS-Trend-Correlation-Heatmap/

Publication ID: 96Cld5iS. Source SHA-256: 41138c6ce0ca9263bd9e60741e9f24414db0d9b459c2bb23e13f123962eed5da. Raw-description SHA-256: 687dfdbc82a358ff4003cd64e63fd4f39ac43a06442ebaa2fddb6e6b6fc7311d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
