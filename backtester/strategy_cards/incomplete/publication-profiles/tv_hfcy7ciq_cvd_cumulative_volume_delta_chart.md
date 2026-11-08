---

id: tv_profile_hfcy7ciq

name: "CVD - Cumulative Volume Delta (Chart)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "CVD Chart maps cumulative or raw intrabar volume delta onto the price pane in reset-defined zones. It preserves volume-pressure context alongside price while offering multiple reset schedules, including trend-change events. The visual scale is a display transform based on zone price ranges and delta extrema, so the plotted vertical position is not itself a tradeable price or unchanged absolute delta scale."

registry_key: null

runner: null

evaluation: null

---

# CVD - Cumulative Volume Delta (Chart)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

CVD Chart maps cumulative or raw intrabar volume delta onto the price pane in reset-defined zones. It preserves volume-pressure context alongside price while offering multiple reset schedules, including trend-change events. The visual scale is a display transform based on zone price ranges and delta extrema, so the plotted vertical position is not itself a tradeable price or unchanged absolute delta scale.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Raw delta/none-or-fixed-reset CVD is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Classify intrabar volumes by candle direction with prior-close/last-polarity fallbacks, sum up minus down and optionally accumulate until reset.
- Reset by none, fixed/stepped higher timeframe, clock time, regular-session start or selected trend-indicator change.
- Scale line/histogram zones to price ranges, offset beneath price and annotate extrema/values; color simple candle/delta polarity disagreements as divergences.
- Intrabar volume sign uses body,prior-close,last-polarity fallback. DV=U-D;CVD accumulates DV with no reset or resets at caller fixed-timeframe boundaries,including current bar after reset. Initial polarity/zero volume and trend resets/scaling remain limitations.

## Outputs and intended use

- Inspect delta progression within zones and divergence coloring, while checking the information box for actual lower-timeframe coverage.
- Usable scope: Raw delta/none-or-fixed-reset CVD. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Fixed intrabar targets are approximately 12/24/50/100/250; ten precision options and configurable Zone Height/labels/tooltips are described.
- Stepped resets map subminute to hourly, below three hours to daily, through twelve hours to weekly, below weekly to monthly and weekly-or-higher to annual.

## Failure modes and caveats

- Analytical: lower-resolution attribution is not bid/ask aggressor flow; changing coverage or viewport-based scale affects the display. Trend reset dependencies add their own settings/timing.

## Missing information and implementation boundary

- Complete reset-indicator parameters, precise zone scaling/zero handling, defaults and data-gap behavior are not fully specified.

## Data requirements

Required inputs: ohlcv, lower-timeframe OHLCV, reset/session configuration.

Repository input-class support: available. The described delta proxy uses OHLCV at selected resolutions; exact available intrabar depth and platform parity are unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
12, 24, 50, 100, and 250.
```

### E2: parameters, readiness

```text
Ten options are included
```

### E3: parameters, readiness

```text
<  1min        1H
     <  3H          1D
     <= 12H         1W
     <  1W          1M
     >= 1W          1Y
```

### E4: mechanism, readiness

```text
last known polarity is used.
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
 • As a last resort, when there is no movement during an intrabar and it closes at the same price as the previous intrabar, the last known polarity is used.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
This indicator displays cumulative ​volume delta (​CVD) as an on-chart oscillator. It uses intrabar analysis to obtain more precise ​volume delta information compared to methods that only use the chart's timeframe.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
 • [b]On a fixed higher timeframe[/b]: Calculations reset on the higher timeframe you select in the "Fixed higher timeframe" field.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hfcy7ciq_cvd_cumulative_volume_delta_chart](../tv_hfcy7ciq_cvd_cumulative_volume_delta_chart.md)
- [tv_method_volume_delta](../../tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/hFcy7CIq-CVD-Cumulative-Volume-Delta-Chart/

Publication ID: hFcy7CIq. Source SHA-256: c7f6863ef7b1ce2333ca308d048706bd9f1501a73b5baf0ad191f5559418b59b. Raw-description SHA-256: 9661d1ab4d008635eb2b029ed800e441059ff83694f312c1c2890888f458260f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
