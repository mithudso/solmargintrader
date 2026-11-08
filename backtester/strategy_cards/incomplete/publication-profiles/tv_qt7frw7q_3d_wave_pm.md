---

id: tv_profile_qt7frw7q

name: "3D Wave-PM"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "3D Wave-PM visualizes volatility cycles through a heatmap across timeframes. It is intended to distinguish quieter, potentially compressed conditions from more active phases, using a color-plume analogy. The author connects blue/green plumes to pent-up volatility and orange/red plumes to large moves, but those expectations remain interpretation rather than a demonstrated forecast guarantee."

registry_key: null

runner: null

evaluation: null

---

# 3D Wave-PM

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

3D Wave-PM visualizes volatility cycles through a heatmap across timeframes. It is intended to distinguish quieter, potentially compressed conditions from more active phases, using a color-plume analogy. The author connects blue/green plumes to pent-up volatility and orange/red plumes to large moves, but those expectations remain interpretation rather than a demonstrated forecast guarantee.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The Wave-PM volatility calculation and multi-timeframe heatmap thresholds are absent.

- The Wave-PM volatility calculation and multi-timeframe heatmap thresholds are absent.

## How it works

- Use the Wave-PM volatility oscillator described in Mark Whistler’s book and render its multi-timeframe values as a heatmap.
- Provide simpler and line-based visualizations as alternatives to the more demanding display.

## Outputs and intended use

- Inspect volatility phases and potential expansion context; the source does not assign trade direction to the colors.

## Parameters and stated settings

- Visualization style is selectable; no oscillator formula, timeframe list, lengths or color thresholds are disclosed.

## Failure modes and caveats

- The author warns the display can be GPU intensive; analytical: volatility expansion does not specify the direction of a move, and compression may persist.

## Missing information and implementation boundary

- Wave-PM equations, precise color boundaries, synchronization across timeframes and execution rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, readiness

```text
designed to help read cycles of volatility.
```

### E2: outputs_and_use, readiness

```text
blue and green plumes which invariably give way to big moves signaled by the orange and red plumes.
```

### E3: risks, readiness

```text
This indicator can be quite GPU intensive
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qt7frw7q_3d_wave_pm](../tv_qt7frw7q_3d_wave_pm.md)

## Source

https://www.tradingview.com/script/qT7frw7Q-3D-Wave-PM/

Publication ID: qT7frw7Q. Source SHA-256: 7998898d1d8feaa035d81efdc83f32a6d4c3bcc0a219a8ea282222092f400808. Raw-description SHA-256: dbfb2dbc268e1dcd9c61c94f474850fe0a1c203c0a9165cbf624ac0989ba2bd1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
