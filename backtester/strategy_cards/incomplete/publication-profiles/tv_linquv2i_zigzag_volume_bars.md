---

id: tv_profile_linquv2i

name: "Zigzag Volume Bars"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Attach volume information to zigzag swing structure so participation can be compared across market legs."

registry_key: null

runner: null

evaluation: null

---

# Zigzag Volume Bars

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Attach volume information to zigzag swing structure so participation can be compared across market legs.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Pivot algorithm, leg-volume calculation, plus/minus classification and confirmation timing are missing.

- Pivot algorithm, leg-volume calculation, plus/minus classification and confirmation timing are missing.

## How it works

- Visualize volume at zigzag swing highs and lows. The source provides display arrangements but does not state whether volume is accumulated over legs, sampled at pivots or split by candle direction.

## Outputs and intended use

- Choose ordinary volume bars or plus/minus arrangements that stack, overlap or occupy opposite sides. The display is a structural-volume comparison rather than a complete trade signal.

## Parameters and stated settings

- Stacked layouts include alternative ordering of green and red bars. Zigzag settings, volume definitions and defaults are not listed.

## Failure modes and caveats

- Recent zigzag swings can move as new extrema develop; volume attached to them may consequently change. Color does not establish true aggressor flow.

## Missing information and implementation boundary

- Pivot algorithm, leg-volume calculation, plus/minus classification and confirmation timing are missing.

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
Here is an indicator which can help you visualise volume data on Zigzag swing highs and lows.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*] Regular
[*] Plus/Minus - Stacked
[*] Plus/Minus - Overlapping
[*] Plus/Minus - Opposite Sides
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_linquv2i_zigzag_volume_bars](../tv_linquv2i_zigzag_volume_bars.md)

## Source

https://www.tradingview.com/script/lInQUv2i-Zigzag-Volume-Bars/

Publication ID: lInQUv2i. Source SHA-256: d6711c6ec611fc1695566441d802f09da965689b6eab5ba624c8ebd83aafa71c. Raw-description SHA-256: 7eda8aa8d55f09867140b26425f4fa01da95c0c4879d7497680e29f12c1ce6cd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
