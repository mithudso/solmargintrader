---

id: tv_profile_x4xoo9ax

name: "Fibonacci Sequence Circles [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Fibonacci Sequence Circles draws expanding geometric references around selected market anchors. The author proposes them as support/resistance and expansion context, with anchors chosen from pivots or calendar transitions. The sequence recurrence is explicitly shown, but a circle on a time-price chart also needs a price-versus-time scale. That mapping is not supplied, so the numerical sequence alone is insufficient to reproduce the published drawing."

registry_key: null

runner: null

evaluation: null

---

# Fibonacci Sequence Circles [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fibonacci Sequence Circles draws expanding geometric references around selected market anchors. The author proposes them as support/resistance and expansion context, with anchors chosen from pivots or calendar transitions. The sequence recurrence is explicitly shown, but a circle on a time-price chart also needs a price-versus-time scale. That mapping is not supplied, so the numerical sequence alone is insufficient to reproduce the published drawing.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- Anchor selection and time-to-price geometry are unspecified.

## How it works

- Set the first diameter to start_val and the next to start_val plus integer half of start_val.
- Generate later diameters by summing the preceding pair and center the resulting circles on the chosen anchor.

## Outputs and intended use

- Display diameter labels in bars and customize visibility/color per circle.
- Use a linear chart, as the source expressly warns against logarithmic visualization.

## Parameters and stated settings

- The code builds ten sequence terms. Anchor options are pivot high, pivot low, daily, weekly or monthly; start value is adjustable.

## Failure modes and caveats

- Chart aspect ratio and scaling can change apparent intersections.
- Geometric proximity does not establish future price reaction.

## Missing information and implementation boundary

- Pivot confirmation, timeframe anchor price, price/time radius conversion and circle sampling are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
secon   = start_val + int(start_val/2)
```

### E2: mechanism

```text
three   = first + secon
```

### E3: parameters

```text
ten     = eight + nine
```

### E4: outputs_and_use

```text
use simple not logarithmic chart
```

### E5: outputs_and_use

```text
diameter of each circle (in bars)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_x4xoo9ax_fibonacci_sequence_circles_bigbeluga](../tv_x4xoo9ax_fibonacci_sequence_circles_bigbeluga.md)

## Source

https://www.tradingview.com/script/x4xoO9ax-Fibonacci-Sequence-Circles-BigBeluga/

Publication ID: x4xoO9ax. Source SHA-256: 9aff4e6d522c694850b3e39e8329d301ade831e061f6d350c4855746bb84990a. Raw-description SHA-256: 538c3201c46774205546b8266de553b293813d38f060e898547dfc3939ffe0b1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
