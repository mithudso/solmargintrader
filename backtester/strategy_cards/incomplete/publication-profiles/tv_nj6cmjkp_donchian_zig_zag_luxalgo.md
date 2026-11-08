---

id: tv_profile_nj6cmjkp

name: "Donchian Zig-Zag [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Donchian Zig-Zag creates a line that repeatedly moves toward channel extremes, producing an experimental zigzag-like view. It aims to describe directional swings and extend relationships among successive peaks/troughs as potential support/resistance. The author discusses price crosses at a slow bounce setting and apparent projection at faster settings, while acknowledging that uses are hypothetical and accuracy limited. The introductory phrase lagging or lagging is internally uninformative, so it does not establish a leading mode or forecast guarantee."

registry_key: null

runner: null

evaluation: null

---

# Donchian Zig-Zag [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Donchian Zig-Zag creates a line that repeatedly moves toward channel extremes, producing an experimental zigzag-like view. It aims to describe directional swings and extend relationships among successive peaks/troughs as potential support/resistance. The author discusses price crosses at a slow bounce setting and apparent projection at faster settings, while acknowledging that uses are hypothetical and accuracy limited. The introductory phrase lagging or lagging is internally uninformative, so it does not establish a leading mode or forecast guarantee.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Donchian bounce recurrence and turning-point confirmation are unspecified.

- Donchian bounce recurrence and turning-point confirmation are unspecified.

## How it works

- Compute Donchian extremes over a selected length and move the zigzag line between them at a configurable bounce speed.
- Connect successive peaks/troughs into extended reference lines.

## Outputs and intended use

- Zigzag, channel gradient and extended swing lines support experimental trend/level reading.

## Parameters and stated settings

- Length controls channel horizon; Bounce Speed controls convergence.
- Speed 1 is described as lagging; above 1 is presented as having predictive-looking behavior. Gradient defaults on; transparency is adjustable.

## Failure modes and caveats

- Faster geometric projection does not establish predictive information.
- Potential price-cross entries lack explicit direction, confirmation and risk controls.

## Missing information and implementation boundary

- Exact recurrence, bounce/reversal trigger, peak confirmation, defaults and order rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Donchian extrema and projected line geometry derive from OHLCV prices.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
bounce speed value of 1
```

### E2: parameters

```text
bounce speed superior to 1
```

### E3: parameters

```text
"On" by default
```

### E4: risks

```text
usages can be limited and very hypothetical.
```

### E5: mechanism, readiness

```text
converge faster toward the extremities
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_nj6cmjkp_donchian_zig_zag_luxalgo](../tv_nj6cmjkp_donchian_zig_zag_luxalgo.md)

## Source

https://www.tradingview.com/script/Nj6CMJkP-Donchian-Zig-Zag-LuxAlgo/

Publication ID: Nj6CMJkP. Source SHA-256: 9ba0519c90365dbc318006c3eb87e8ef9b86763bbd9f59f7943e83b9923273c6. Raw-description SHA-256: aa088250ac184a413aed6200732254da748976cd7666971cfc7851de88b886dd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
