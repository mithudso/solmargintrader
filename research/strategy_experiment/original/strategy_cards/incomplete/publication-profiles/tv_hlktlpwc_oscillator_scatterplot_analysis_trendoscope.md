---

id: tv_profile_hlktlpwc

name: "Oscillator Scatterplot Analysis [Trendoscope®]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Oscillator Scatterplot Analysis measures price displacement and elapsed bars between dynamic oversold and overbought transitions. It aims to show whether oscillator excursions correspond to favorable or contrary price moves, rather than assume every extreme has the same meaning. Signed duration separates oversold-to-overbought from the opposite journey, while horizontal position captures price direction. Scatter/heatmap density and quadrant counts support research into the chosen oscillator. No trade rule follows automatically from a dense quadrant."

registry_key: null

runner: null

evaluation: null

---

# Oscillator Scatterplot Analysis [Trendoscope®]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Oscillator Scatterplot Analysis measures price displacement and elapsed bars between dynamic oversold and overbought transitions. It aims to show whether oscillator excursions correspond to favorable or contrary price moves, rather than assume every extreme has the same meaning. Signed duration separates oversold-to-overbought from the opposite journey, while horizontal position captures price direction. Scatter/heatmap density and quadrant counts support research into the chosen oscillator. No trade rule follows automatically from a dense quadrant.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Exact transition pairing and price-displacement/boundary conventions are unspecified.

## How it works

- Select oscillator and derive dynamic extremes using Bollinger, Keltner or Donchian boundaries.
- Measure price movement and bar count between opposite extreme states.
- Bucket samples for scatter/heatmap, signed by journey direction and optionally compress outliers into border cells.

## Outputs and intended use

- Four-quadrant distribution of displacement versus signed duration supports oscillator evaluation.

## Parameters and stated settings

- Oscillator/length, boundary method/length/multiplier, grid rows/columns and outlier percentage are configurable.
- Source says table maximum10000 cells;20% outlier example trims both20% tails for bounds while retaining border data.

## Failure modes and caveats

- Boundary method and event pairing materially change the sample.
- Trimming chart bounds can conceal tail detail; overlapping journeys may not be independent.

## Missing information and implementation boundary

- Oscillator defaults, transition/recross pairing, price displacement unit/source and exact boundary formulas are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Named oscillator/band and price-duration inputs use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
x-axis represents price movement.
```

### E2: mechanism

```text
number of bars it took
```

### E3: parameters

```text
max 10000 cells
```

### E4: parameters

```text
20% outlier means
```

### E5: parameters

```text
bottom 20% and top 20%
```

### E6: parameters, readiness

```text
Bollinger Bands, Keltener Channel and Donchian channel
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hlktlpwc_oscillator_scatterplot_analysis_trendoscope](../tv_hlktlpwc_oscillator_scatterplot_analysis_trendoscope.md)

## Source

https://www.tradingview.com/script/hLKTlpwc-Oscillator-Scatterplot-Analysis-Trendoscope/

Publication ID: hLKTlpwc. Source SHA-256: d15b924d8e6ed15ecdc1efd0ed88b6bc68ac9c42042fd034115bf850606273d7. Raw-description SHA-256: b2d1bf9ade708e4b0efe6eb9bc3af1c9248652a985b5fa12ab2e661da74bbfdf.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
