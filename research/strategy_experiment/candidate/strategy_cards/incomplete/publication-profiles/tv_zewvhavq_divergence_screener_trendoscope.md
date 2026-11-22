---

id: tv_profile_zewvhavq

name: "Divergence Screener [Trendoscope®]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Divergence Screener compares oscillator and price pivot directions and can expose its outputs to a watchlist screener. It supports regular reversal-style and hidden continuation-style divergences with selectable trend context. The source explains these relationships and the user workflow, but the zigzag construction and intermediate-line validation remain undisclosed. The default early-signal mode is explicitly revisable, so historical annotations should not be treated as immutable live alerts."

registry_key: null

runner: null

evaluation: null

---

# Divergence Screener [Trendoscope®]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Divergence Screener compares oscillator and price pivot directions and can expose its outputs to a watchlist screener. It supports regular reversal-style and hidden continuation-style divergences with selectable trend context. The source explains these relationships and the user workflow, but the zigzag construction and intermediate-line validation remain undisclosed. The default early-signal mode is explicitly revisable, so historical annotations should not be treated as immutable live alerts.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core rules remain unresolved.

- Pivot selection/matching and line-validation predicates are undefined.

## How it works

- Calculate a built-in oscillator or accept an external plot, then detect oscillator zigzag pivots and compare corresponding price direction.
- Regular bullish/bearish cases pair price lower lows/higher highs with opposite oscillator movement; hidden cases reverse that relationship.
- Filter by zigzag structure, moving-average change between pivots or an external signed trend; reject lines violated by intermediate bars.

## Outputs and intended use

- Draw colored lines and D/H labels, inspect pivot tooltips and configure divergence-specific close alerts.
- Scan a selected watchlist using the supported built-in paths; external oscillator/trend inputs are unavailable in the screener.

## Parameters and stated settings

- Zigzag length defaults to 13 and repainting defaults enabled. Oscillator length 14 is an example.
- The source states a screener history limit of 500 bars.

## Failure modes and caveats

- Early pivots and divergences may disappear or move.
- Screener history differs from chart history and can change the candidate set.

## Missing information and implementation boundary

- Zigzag confirmation, pivot matching/ratios, intermediate violation geometry and exact trend-context classification are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the built-in calculation path.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
zigzag length (default: 13)
```

### E2: parameters

```text
14 for RSI
```

### E3: parameters

```text
Pine screener has max 500 bars available.
```

### E4: parameters, risks

```text
Repaint option is by default enabled.
```

### E5: mechanism

```text
no intermediate bars violate the divergence condition
```

### E6: mechanism

```text
positive for uptrend, negative for downtrend
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_oscillator_divergence](../tv_method_oscillator_divergence.md)
- [tv_zewvhavq_divergence_screener_trendoscope](../tv_zewvhavq_divergence_screener_trendoscope.md)

## Source

https://www.tradingview.com/script/zewvHAvQ-Divergence-Screener-Trendoscope/

Publication ID: zewvHAvQ. Source SHA-256: 36fcbc510918aa0c0cd3a070dc573d7bbf7deb60c702df00a43ab0568e33ebf5. Raw-description SHA-256: 02091f08e7f409707347878652c13390bcac05015630c7c4c026cc812f0411a6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
