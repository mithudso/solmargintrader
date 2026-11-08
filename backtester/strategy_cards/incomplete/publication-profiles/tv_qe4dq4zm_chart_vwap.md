---

id: tv_profile_qe4dq4zm

name: "Chart VWAP"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Calculate viewport-anchored averages and extremes so the displayed chart segment becomes the explicit analysis interval."

registry_key: null

runner: null

evaluation: null

---

# Chart VWAP

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Calculate viewport-anchored averages and extremes so the displayed chart segment becomes the explicit analysis interval.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for visible-close arithmetic mean and visible-range OHLC/extrema with caller viewport boundaries; exact VWAP source and plotting parity remain outside this narrow scope.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- For caller-specified left/right visible-bar timestamps, select the visible observations. Calculate their arithmetic close mean as sum(close)/visible-bar count, visible high as maximum(high), visible low as minimum(low), beginning open and final close. These separately reproducible companion outputs do not require a VWAP price-source assumption.
- The principal branded VWAP resets at the leftmost visible bar and recalculates when scrolling/zooming changes the viewport. Its exact weighted price source and zero-volume policy are not disclosed. Optional distance labels relate visible extrema to the latest visible close.

## Outputs and intended use

- Orange VWAP and gray mean compare volume-weighted versus simple visible-window value. Optional levels show start/end prices and extremes; scrolling or zooming intentionally changes the study.

## Parameters and stated settings

- Mean defaults visible and can be hidden. OHLC/high-low values and distance labels are optional. The left/right visible opening timestamps define the sample.

## Failure modes and caveats

- Viewport dependence makes historical readings unstable under user navigation. Values should be bound to recorded visible boundaries before comparing outputs or using them in tests.

## Missing information and implementation boundary

- The VWAP source/default, zero-volume behavior and detailed label positioning are delegated to a library rather than fully shown.

## Data requirements

Required inputs: ohlcv, visible chart start/end timestamps.

Repository input-class support: available. OHLCV plus user viewport timestamps supports the described financial computations; viewport selection is an explicit extra input.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
anchored to the leftmost visible bar of the chart.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
a simple average of the chart's visible
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
close[/url] values in gray
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
reset the ​VWAP at the leftmost visible bar.
```

### E5: mechanism, parameters, readiness

```text
PCvc.​avg()` calculates the average of a source value for visible bars only.
```

### E6: mechanism, parameters, readiness

```text
You may also use the script's settings to enable the display of the chart's OHLC (open, high, low, close) levels and the values of the high and low. These are also calculated from the range of visible bars.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qe4dq4zm_chart_vwap](../../tv_qe4dq4zm_chart_vwap.md)

## Source

https://www.tradingview.com/script/QE4dq4ZM-Chart-VWAP/

Publication ID: QE4dq4ZM. Source SHA-256: d175c4f5b729f98d516e89d369a4cc5978acfaf5980cad51dddeefb0c1b2d8e8. Raw-description SHA-256: 757af377550f615fc5bcc0b1d75e28d59dd8b12ce9cdb698f680dd4639ae0ab3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
