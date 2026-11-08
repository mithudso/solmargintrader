---

id: tv_profile_5wxlrdaq

name: "TASC 2022.06 Ehlers Loops"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Ehlers Loops visualizes the relationship between filtered price and filtered volume. It offers a way to inspect familiar claims about whether rising or falling volume confirms a price move, rather than accepting those claims without examining the joint trajectory. A conventional pane shows both streams over time, while a scatterplot turns their paired observations into a loop. The latter highlights curvature and direction of travel through price-volume space. The intended interpretation is discretionary market-condition analysis; the source does not prescribe orders at particular loop quadrants."

registry_key: null

runner: null

evaluation: null

---

# TASC 2022.06 Ehlers Loops

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Ehlers Loops visualizes the relationship between filtered price and filtered volume. It offers a way to inspect familiar claims about whether rising or falling volume confirms a price move, rather than accepting those claims without examining the joint trajectory. A conventional pane shows both streams over time, while a scatterplot turns their paired observations into a loop. The latter highlights curvature and direction of travel through price-volume space. The intended interpretation is discretionary market-condition analysis; the source does not prescribe orders at particular loop quadrants.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Filter coefficients and RMS normalization window are not supplied.

- Filter coefficients and RMS normalization window are not supplied.

## How it works

- Band-limit both streams with a high-pass Butterworth filter followed by a low-pass SuperSmooth filter.
- Divide each filtered stream by its root-mean-square scale.
- Plot the resulting zero-mean series together or map volume to the scatterplot x-axis and price to its y-axis.

## Outputs and intended use

- Default oscillator view supports comparison of price/volume directions.
- Scatterplot view exposes path curvature and standardized departures over a selected timespan.

## Parameters and stated settings

- HPPeriod and LPPeriod select filter cutoff wavelengths; timespan and display mode govern visualization.
- The prose associates one/two/three standard deviations with 68%, 95% and 99.7%, but these are author assertions rather than established reversal probabilities.

## Failure modes and caveats

- A normal-distribution coverage rule does not imply the claimed probability of a future financial reversal.
- Filtering and scaling can create lag and make loop appearance sensitive to chosen periods.

## Missing information and implementation boundary

- Filter coefficients, RMS window, warmup behavior, default lengths and explicit trading predicates are not provided.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Price and volume streams are standard OHLCV inputs; the exact filtering implementation remains unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
high-pass[/url] Butterworth filter
```

### E2: mechanism

```text
low-pass[/url] SuperSmooth filter.
```

### E3: mechanism

```text
dividing each by their root-mean-square values.
```

### E4: parameters, risks

```text
68%, 95% and 99.7% at one, two and three standard deviations
```

### E5: parameters

```text
HPPeriod[/b] and [b]LPPeriod
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5wxlrdaq_tasc_2022_06_ehlers_loops](../tv_5wxlrdaq_tasc_2022_06_ehlers_loops.md)

## Source

https://www.tradingview.com/script/5WXLRdaQ-TASC-2022-06-Ehlers-Loops/

Publication ID: 5WXLRdaQ. Source SHA-256: d74d73db8b05c8e5a8f70d438d5f9de82ec0f9ad0fcf0ff751af1c992dc8a6bc. Raw-description SHA-256: 88b53a019f6fc623e93d077abeed8d8c4c6c3d6bf231f74e72ad0a20d48c59c8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
