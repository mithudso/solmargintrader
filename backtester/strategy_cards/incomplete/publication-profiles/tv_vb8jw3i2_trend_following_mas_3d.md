---

id: tv_profile_vb8jw3i2

name: "Trend Following MAs 3D"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Trend Following MAs 3D combines the direction and relative arrangement of a family of moving averages into a trend-strength visualization. It aims to make agreement across horizons visible, with a shrinking display indicating little trend. The three-dimensional appearance is a visual encoding, not another data dimension. The author reports personal impressions of success but gives no measured test or signal definition. A faithful card therefore describes the multi-average concept while leaving its aggregation and geometric mapping unresolved."

registry_key: null

runner: null

evaluation: null

---

# Trend Following MAs 3D

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Trend Following MAs 3D combines the direction and relative arrangement of a family of moving averages into a trend-strength visualization. It aims to make agreement across horizons visible, with a shrinking display indicating little trend. The three-dimensional appearance is a visual encoding, not another data dimension. The author reports personal impressions of success but gives no measured test or signal definition. A faithful card therefore describes the multi-average concept while leaving its aggregation and geometric mapping unresolved.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core relation/direction aggregation and strength-to-display mapping are not defined.

## How it works

- Calculate a family of selected-type moving averages and examine their directions and relationships.
- Map inferred trend direction/strength to a three-dimensional display whose small size denotes no trend.

## Outputs and intended use

- A size/direction visualization supports discretionary regime inspection.

## Parameters and stated settings

- Twenty averages span periods 5–100; types available are EMA,SMA,RMA,WMA,VWMA.
- Exact length progression, defaults and rendering controls are not supplied.

## Failure modes and caveats

- Correlated averages do not provide independent evidence.
- Without the aggregation rule, apparent strength cannot be reproduced or calibrated.

## Missing information and implementation boundary

- Direction/relationship scoring, normalization, visual geometry, thresholds and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Named moving averages, including volume-weighted variants, use OHLCV data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism

```text
20 moving averages (5 to 100 period)
```

### E2: parameters

```text
EMA, SMA, RMA, WMA, VWMA.
```

### E3: outputs_and_use

```text
When it gets tiny it means there is no trend
```

### E4: readiness, mechanism

```text
direction of MAs and relation between
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_vb8jw3i2_trend_following_mas_3d](../tv_vb8jw3i2_trend_following_mas_3d.md)

## Source

https://www.tradingview.com/script/Vb8jW3I2-Trend-Following-MAs-3D/

Publication ID: Vb8jW3I2. Source SHA-256: 27af66cc3ccc70c21de5fb0de1a483c826d0bfc066ed2f05c88025261745c906. Raw-description SHA-256: 33c48c828c76223f59894902cc7e009ef85c23c8ca86b74f7ab7e5f38ee8cf90.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
