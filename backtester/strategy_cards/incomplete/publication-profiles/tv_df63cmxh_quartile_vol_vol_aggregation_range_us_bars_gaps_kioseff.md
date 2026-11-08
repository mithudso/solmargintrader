---

id: tv_profile_df63cmxh

name: "(Quartile Vol.; Vol. Aggregation; Range US Bars; Gaps) [Kioseff]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Compare volume distributions, alternative bar aggregations and persistent gaps in one price-action research tool. The publication provides descriptive statistics and chart transformations rather than a complete entry/exit strategy."

registry_key: null

runner: null

evaluation: null

---

# (Quartile Vol.; Vol. Aggregation; Range US Bars; Gaps) [Kioseff]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare volume distributions, alternative bar aggregations and persistent gaps in one price-action research tool. The publication provides descriptive statistics and chart transformations rather than a complete entry/exit strategy.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Manual cumulative-volume threshold events is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Volume quartiles and a high-percentile threshold categorize bars, display dispersions and measure subsequent returns. Successive high-volume observations can receive a regression channel, and a time anchor can start VWAP.
- Range US bars form after separate trend/reversal price thresholds, with state-dependent continuation rules. They use minute OHLC, so multiple reversals within a minute collapse into an approximation.
- Volume-aggregation bars form when cumulative chart-timeframe volume reaches a threshold, carrying excess forward. Gap tracking records partial fills, completion delays and directional statistics, sorting unfilled gaps by price distance.
- Accumulate supplied chart-bar volume against caller positive threshold Q. Mark a threshold event when cumulative volume reaches/exceeds Q;carry the remainder forward. Event timing occurs at observed chart bars,not synthetic tick fills. Multiple events/overshoot price mapping,automatic thresholds,range/gap/quartile outputs remain unqualified.

## Outputs and intended use

- Quartile colors/labels, statistics tables, synthetic bars, gap boxes/lists and anchored VWAP support discretionary analysis.
- Remote gaps can be hidden then reappear when price returns nearby; visibility is distinct from gap validity.
- Usable scope: Manual cumulative-volume threshold events. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Automatic or manual range trend/reversal thresholds and volume threshold; date segmentation, forward-return horizon and log-return option.
- Volume includes a 90th-percentile category. Gap minimum size and hide-distance percentage are user settings; warning messages flag overly fine aggregation thresholds.

## Failure modes and caveats

- OHLC approximations cannot recreate tick-level range or volume bars. Small thresholds can produce misleading synthetic structure.
- Conditional returns following high volume are descriptive and sensitive to sample overlap and regime; they do not prove a tradable edge.

## Missing information and implementation boundary

- Quantile window/interpolation, automatic threshold formulas, gap endpoint definition, intrabar sequencing and precise return-sampling rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV at chart and minute resolutions supplies the described raw data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
90th Percentile Volume Threshold
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
1-minute OHLC data is used for calculations.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Tick data isn't used; therefore, remainder values are carry over.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Partially filled gaps are displayed in the corresponding gap box
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The user defines the dollar amount price must travel up/down
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
Similar to the Range US chart type, Volume Aggregation bars aren’t bound to a time-axis; the bars form after a user-defined, cumulative amount of volume is achieved or exceeded. Consequently, once the cumulative amount of volume is achieved or exceeded - a bar is produced at the corresponding price level.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
Regardless of the current price, Volume Aggregation bars for after a requisite amount of volume is achieved/exceeded. Tick data isn't used; therefore, remainder values are carry over.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_df63cmxh_quartile_vol_vol_aggregation_range_us_bars_gaps_kioseff](../tv_df63cmxh_quartile_vol_vol_aggregation_range_us_bars_gaps_kioseff.md)
- [tv_method_linear_regression_channel](../tv_method_linear_regression_channel.md)

## Source

https://www.tradingview.com/script/DF63CmXh-Quartile-Vol-Vol-Aggregation-Range-US-Bars-Gaps-Kioseff/

Publication ID: DF63CmXh. Source SHA-256: e9882d6970f693d887d55d7df4e4fbe351a473f4c68ee531c888ffe3bf9b0d15. Raw-description SHA-256: b123e3969e140f7cac8fad8b419564abf94640f89a0e4b0c0a14ee8aad347240.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
