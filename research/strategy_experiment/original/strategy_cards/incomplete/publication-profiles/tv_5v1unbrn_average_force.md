---

id: tv_profile_5v1unbrn

name: "Average Force"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Average Force is presented as a trend-identification oscillator built from a sentiment calculation followed by smoothing. The intended distinction is between an underlying sentiment estimate and a more readable trend-oriented output. The complete description is only a sentence, so the financial purpose is clear but the actual meaning of sentiment is not. It could refer to a price-derived proxy or another input; neither is established. A usable interpretation must therefore stop at the disclosed two-stage idea rather than substitute a familiar force-index formula or infer directional thresholds from the title."

registry_key: null

runner: null

evaluation: null

---

# Average Force

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Average Force is presented as a trend-identification oscillator built from a sentiment calculation followed by smoothing. The intended distinction is between an underlying sentiment estimate and a more readable trend-oriented output. The complete description is only a sentence, so the financial purpose is clear but the actual meaning of sentiment is not. It could refer to a price-derived proxy or another input; neither is established. A usable interpretation must therefore stop at the disclosed two-stage idea rather than substitute a familiar force-index formula or infer directional thresholds from the title.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Neither the sentiment equation nor its smoothing computation is disclosed.

- Neither the sentiment equation nor its smoothing computation is disclosed.

## How it works

- Calculate an unspecified sentiment measure.
- Smooth that measure to form a trend-oriented oscillator.

## Outputs and intended use

- An oscillator is intended to help determine trend; plotting conventions and actionable states are not disclosed.

## Parameters and stated settings

- No source parameters or defaults are specified.

## Failure modes and caveats

- An undefined sentiment proxy may not measure participant sentiment.
- Smoothing generally trades responsiveness against noise, but the undisclosed algorithm prevents quantifying that tradeoff.

## Missing information and implementation boundary

- Sentiment inputs/formula, smoothing type/length, scale, zero-line meaning, signals and trade rules are all absent.

## Data requirements

Required inputs: unspecified sentiment inputs.

Repository input-class support: unavailable or unresolved. The source never identifies the raw inputs used to calculate sentiment, so OHLCV sufficiency cannot be established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, readiness

```text
Average Force is an oscillator that calculates sentiment, then smooths the result
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5v1unbrn_average_force](../tv_5v1unbrn_average_force.md)

## Source

https://www.tradingview.com/script/5v1UnBrN-Average-Force/

Publication ID: 5v1UnBrN. Source SHA-256: 42bc223a357a6f123be9848986e099f924e0f6d9303756d195ff7380b0bdb074. Raw-description SHA-256: 40a0d737e81c419043fc3d3a15f613b9b2df2d37201152972c7db36f49aaf0a7.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
