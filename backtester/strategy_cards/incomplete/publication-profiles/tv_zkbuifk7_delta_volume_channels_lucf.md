---

id: tv_profile_zkbuifk7

name: "Delta Volume Channels [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Translate lower-timeframe directional-volume estimates into price-chart channels and configurable condition markers. The design emphasizes visual pressure and consolidation context rather than raw flow values or verified exchange aggressor volume."

registry_key: null

runner: null

evaluation: null

---

# Delta Volume Channels [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Translate lower-timeframe directional-volume estimates into price-chart channels and configurable condition markers. The design emphasizes visual pressure and consolidation context rather than raw flow values or verified exchange aggressor volume.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Intrabar DV/DVpercent is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Classify intrabar volume by open/close direction, then prior-close change for flat bars, then last polarity. Summed up minus down volume forms delta; dividing by total intrabar volume gives delta percentage.
- A reference average and an average of a delta/relative-volume-weighted source define a channel. Their ordering sets bull/bear state; source-close position and both slopes strengthen that state.
- A divergence means disagreement of the two average slopes. Save divergence-bar levels, expand them on later divergences until breached, and reset with a new divergence after breach. Channel breakout direction combines with pressure strength for stronger states.
- Sign intrabar volume by close-open;flat body uses close-previous_intrabar_close;unchanged price carries last polarity. Sum U,D;DV=U-D;DV%=100*(U-D)/(U+D) for positive total. Caller supplies LTF/initial polarity and adequate observations. Weighted source/channels and marker filters remain outside scope.

## Outputs and intended use

- Filled channels, bar colors, divergence marks and optional raw-value tooltips support discretionary stop tightening or confirmation.
- Markers/alerts use caller-selected state transitions and filters at bar close. The author’s non-repaint claim is limited to that timing and is not independently verified.
- Usable scope: Intrabar DV/DVpercent. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Default reference is close ALMA length20, weighted line capped at five reference standard deviations.
- Divergence defaults use high/low boundaries; upside breach requires low above top and downside high below bottom. Precision, MA type/source/length, cap, volume weighting and marker filters are configurable.

## Failure modes and caveats

- Lower-timeframe polarity is a flow proxy; data coverage and volume-reporting quality constrain interpretation.
- Channel colors do not encode a complete trade policy; a weakened strong state need not predict reversal.

## Missing information and implementation boundary

- Exact relative-volume normalization, weighted-price transformation, cap lookback and complete marker-filter definitions are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Lower-timeframe OHLCV supports the disclosed proxy model; it does not supply actual stop orders or aggressor flags.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The default settings use an Arnaud-Legoux moving average
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
a length of 20 bars
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
capped to 5 standard deviations
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the last known polarity is used.
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
a divergence is any bar where the slope of the reference line does not match that of the DV%-weighted line.
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
 • As a last resort, when there is no movement during an intrabar and it closes at the same price as the previous intrabar, the last known polarity is used.
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
Once all intrabars making up a chart bar have been analyzed and the up or down property of each intrabar's ​volume determined, the up volumes are added and the down volumes subtracted. The resulting value is ​volume delta for that chart bar, which can be used as an estimate of the buying/selling pressure on an instrument.
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
This value is the proportion that delta ​volume represents of the total intrabar ​volume in the chart bar. Note that on some symbols/timeframes, the total intrabar ​volume may differ from the chart's ​volume for a bar, but that will not affect our calculations since we use the total intrabar ​volume.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)
- [tv_zkbuifk7_delta_volume_channels_lucf](../tv_zkbuifk7_delta_volume_channels_lucf.md)

## Source

https://www.tradingview.com/script/zkBuiFk7-Delta-Volume-Channels-LucF/

Publication ID: zkBuiFk7. Source SHA-256: 9c6fe36a22558ab2f4da7135073ab19e8956306f4cb7296d849f66879b506abe. Raw-description SHA-256: 8e65514eda561ea8c3c4aaae44da754077a11a005059f4493dd2eded4fb8a235.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
