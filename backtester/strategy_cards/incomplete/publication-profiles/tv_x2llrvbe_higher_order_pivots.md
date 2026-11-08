---

id: tv_profile_x2llrvbe

name: "Higher Order Pivots"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Higher Order Pivots recursively identifies turning points among already confirmed turning points. It is intended for retrospective market-structure analysis, where broader inflections can be distinguished from local candle noise. The author strongly warns that higher levels require variable and potentially substantial future confirmation, so their historical positions must not be mistaken for live entry availability."

registry_key: null

runner: null

evaluation: null

---

# Higher Order Pivots

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Higher Order Pivots recursively identifies turning points among already confirmed turning points. It is intended for retrospective market-structure analysis, where broader inflections can be distinguished from local candle noise. The author strongly warns that higher levels require variable and potentially substantial future confirmation, so their historical positions must not be mistaken for live entry availability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source defines local pivot geometry and recursive higher-order construction with explicit availability caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Detect a first-order high as a central high above adjacent highs in a three- or five-bar pattern, with symmetric low construction.
- Apply the same local-extreme pattern to first-order pivots for second order, then to second-order pivots for third order.

## Outputs and intended use

- Use hierarchical markers to delineate major historical structure and market inflections; source discourages live trading from higher-order points.

## Parameters and stated settings

- First-order alternatives use three or five bars; higher orders are built from triples of lower-order pivots. Examples show second order from three-bar pivots and third from five-bar pivots.

## Failure modes and caveats

- Confirmation delay is variable and significant; analytical: back-positioned markers contain later information unavailable at the pivot itself.

## Missing information and implementation boundary

- Equal-high/low tie handling, specific plotted orders/default selection and marker rendering are not detailed, but these do not obscure the recursive core definition.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
3 or 5 bar "V" shaped patterns.
```

### E2: mechanism, readiness

```text
Second order pivot points are defined by three first order pivots
```

### E3: risks, readiness

```text
generally inadvisable to use higher order pivots for live trading!
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_x2llrvbe_higher_order_pivots](../../tv_x2llrvbe_higher_order_pivots.md)

## Source

https://www.tradingview.com/script/x2LlRvBe-Higher-Order-Pivots/

Publication ID: x2LlRvBe. Source SHA-256: 828e09dcceb9431e88baf11954868d78809c18a6d531d6ee26828c652a1f0606. Raw-description SHA-256: 9a452e792164cac143e7cae0c06d1a3e81d8418cc7fb15cf8293209afe1b053d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
