---

id: tv_profile_aapsyqft

name: "Gann Box (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Gann Box draws a price/time framework from the visible chart’s highest and lowest points. It aims to show possible reaction levels through percentage subdivisions, fans, angles and curves. The visible-range basis is central: scrolling or zooming can change the extrema and therefore the entire drawing. The source presents geometric forecasting claims but provides no empirical validation. A projected line is a scenario/reference, not evidence that future prices follow astrological or geometric laws."

registry_key: null

runner: null

evaluation: null

---

# Gann Box (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Gann Box draws a price/time framework from the visible chart’s highest and lowest points. It aims to show possible reaction levels through percentage subdivisions, fans, angles and curves. The visible-range basis is central: scrolling or zooming can change the extrema and therefore the entire drawing. The source presents geometric forecasting claims but provides no empirical validation. A projected line is a scenario/reference, not evidence that future prices follow astrological or geometric laws.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core fan/curve/angle geometry and scale conventions are not disclosed.

## How it works

- Locate visible-range high/low and draw a box between them.
- Subdivide price/time according to selected percentages, with optional fans, curves and angles.
- Allow reverse orientation and extension beyond the last bar.

## Outputs and intended use

- Grid, labels, fans/curves/angles and breakout alerts support discretionary support/resistance inspection.

## Parameters and stated settings

- Visible range, percentage levels, visibility, colors, Reverse and Extend govern output; no numeric defaults are supplied.

## Failure modes and caveats

- View-dependent anchors introduce hindsight and make historical comparisons unstable.
- Gann forecasting assertions do not establish predictive validity.

## Missing information and implementation boundary

- Visible-extrema tie selection, box time endpoints, fan/curve equations, scale normalization and alert predicates are absent.

## Data requirements

Required inputs: ohlcv, visible chart range.

Repository input-class support: unavailable or unresolved. OHLCV supplies extrema, but viewport anchors are user-dependent and not specified for a reproducible run.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
highest and lowest price points visible on the chart.
```

### E2: mechanism

```text
divides it according to specified percentages
```

### E3: outputs_and_use

```text
Gann Curves
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_aapsyqft_gann_box_zeiierman](../tv_aapsyqft_gann_box_zeiierman.md)
- [tv_method_gann](../tv_method_gann.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/aaPsyqft-Gann-Box-Zeiierman/

Publication ID: aaPsyqft. Source SHA-256: ea9eb73d67e207001ac7a3697296c6c29a643ecf61be962f8ce3ff730d137cf3. Raw-description SHA-256: d93c452d76cfdcfb95df4a53c6268b85a0ea8d9ed8be9705074a88c1b1cc57db.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
