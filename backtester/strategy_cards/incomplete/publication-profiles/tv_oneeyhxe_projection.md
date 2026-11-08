---

id: tv_profile_oneeyhxe

name: "Projection"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Projection draws potential future price paths using line objects and a choice of predefined shapes. Its financial purpose is scenario visualization: a trader can display an anticipated parabola, triangle or zigzag rather than manually assembling all segments. The author links related scripts but does not disclose the price-projection model here. As a result, the available description supports a drawing framework, not a statistical forecast or evidence that a preset path is likely. A reader must supply the market thesis and verify any anchoring behavior before treating the projection as analysis."

registry_key: null

runner: null

evaluation: null

---

# Projection

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Projection draws potential future price paths using line objects and a choice of predefined shapes. Its financial purpose is scenario visualization: a trader can display an anticipated parabola, triangle or zigzag rather than manually assembling all segments. The author links related scripts but does not disclose the price-projection model here. As a result, the available description supports a drawing framework, not a statistical forecast or evidence that a preset path is likely. A reader must supply the market thesis and verify any anchoring behavior before treating the projection as analysis.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Projection presets lack anchor and price/time path equations.

- Projection presets lack anchor and price/time path equations.

## How it works

- Use line.new() to construct potential price-projection paths from selected presets.
- Include a tick-rounding helper, though its role and application are not described.

## Outputs and intended use

- Projected scenario drawings provide discretionary planning visuals.

## Parameters and stated settings

- Presets named Wide Parabola, Skinny Parabola, Straight Triangle, ZigZag1 and ZigZag2.
- No anchor, scale, horizon or numeric default settings are disclosed.

## Failure modes and caveats

- Preset geometry can encourage unwarranted confidence in a future path.
- No probability, uncertainty band or measured forecast evidence is supplied.

## Missing information and implementation boundary

- Projection equations, anchor selection, price/time scaling, update rules and actionable trade rules are absent.

## Data requirements

Required inputs: ohlcv, user projection/anchor settings.

Repository input-class support: unavailable or unresolved. Price data may supply references, but the source does not define the required anchoring/scaling inputs or a reproducible run.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, purpose, readiness

```text
line.new() to define some potential Price Projections.
```

### E2: parameters

```text
Wide Parabola:
```

### E3: parameters

```text
Skinny Parabola:
```

### E4: parameters

```text
Straight Triangle:
```

### E5: parameters

```text
ZigZag1:
```

### E6: parameters

```text
ZigZag2:
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_oneeyhxe_projection](../tv_oneeyhxe_projection.md)

## Source

https://www.tradingview.com/script/ONEeyHXe-Projection/

Publication ID: ONEeyHXe. Source SHA-256: da013544a81ac5157c899f9c0b9b315d315a701e83289a5a61caa40e30f6e352. Raw-description SHA-256: bc4eb3aec9fe5dc542604995d6226c0fae85b4ee2712f24c02ac08509e50a079.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
