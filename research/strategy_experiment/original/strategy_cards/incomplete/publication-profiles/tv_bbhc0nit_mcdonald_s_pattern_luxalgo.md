---

id: tv_profile_bbhc0nit

name: "McDonald's Pattern [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Fit a deliberately humorous market-pattern drawing to observed price tops and bottoms and score its resemblance to a familiar logo."

registry_key: null

runner: null

evaluation: null

---

# McDonald's Pattern [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fit a deliberately humorous market-pattern drawing to observed price tops and bottoms and score its resemblance to a familiar logo.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Bezier fitting, score normalization, extrema timing, vertex-option semantics and actionable rules are missing.

- Bezier fitting, score normalization, extrema timing, vertex-option semantics and actionable rules are missing.

## How it works

- Use tops/bottoms as cubic Bezier control points to approximate an M-shaped pattern with a deep retracement. Rolling maxima/minima, rather than pivot points, determine extrema.

## Outputs and intended use

- A chart score reports logo similarity; normal and inverted forms receive red and green backgrounds. The author explicitly frames this as entertainment, with some components non-real-time. It remains a price-pattern drawing, not a serious trading method.

## Parameters and stated settings

- Length changes extrema sensitivity. A vertex option is described using the last bar even though its name says first bar, an unresolved author inconsistency. Traditional retracement is described as greater than 50%.

## Failure modes and caveats

- Pattern flexibility and non-real-time fitting invite retrospective pattern recognition. Background colors are descriptive shapes, not validated directional forecasts.

## Missing information and implementation boundary

- Bezier fitting, score normalization, extrema timing, vertex-option semantics and actionable rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the disclosed calculation class; this is not a verified implementation or historical-feed coverage claim.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Traditionally the McDonalds pattern is described by an M pattern with deep retracement (> 50%)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Some aspects of this indicator are not real-time
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Length: Sensitivity of tops/bottoms detection. The method does not make use of pivot points, using rolling maximums/minimums instead.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Use First Bar As Vertex: Use the price and bar index of the last bar as vertex.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bbhc0nit_mcdonald_s_pattern_luxalgo](../tv_bbhc0nit_mcdonald_s_pattern_luxalgo.md)

## Source

https://www.tradingview.com/script/BbHc0nIt-McDonald-s-Pattern-LuxAlgo/

Publication ID: BbHc0nIt. Source SHA-256: eaa60b2f46a4ddfa9879f004faa1386e38f9c703328d0caf3d16548422f89070. Raw-description SHA-256: cf273f4d8cc5b92eac93e9fa267c86ad1232dcbc31ae7c63000c2ac0631403fd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
