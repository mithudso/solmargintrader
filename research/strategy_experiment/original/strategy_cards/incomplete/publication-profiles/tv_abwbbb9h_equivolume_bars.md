---

id: tv_profile_abwbbb9h

name: "Equivolume Bars"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Redraw market bars with widths that represent traded volume so participation becomes part of the candle geometry."

registry_key: null

runner: null

evaluation: null

---

# Equivolume Bars

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Redraw market bars with widths that represent traded volume so participation becomes part of the candle geometry.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: The width formula, zero-volume handling, price-axis drawing logic and exact history limit are absent.

- The width formula, zero-volume handling, price-axis drawing logic and exact history limit are absent.

## How it works

- Render equivolume bars independently of the ordinary time scale, using volume to determine width. Restrict computation to recent bars to avoid timeouts.

## Outputs and intended use

- Compare relative candle widths as a volume cue. The transformed layout must not be read as ordinary elapsed-time spacing.

## Parameters and stated settings

- A recent-bar starting mechanism is used, but the default count and width normalization are not stated.

## Failure modes and caveats

- The author says older bars and replay beyond the retained range are unavailable. A changed horizontal scale can distort timing comparisons with conventional overlays.

## Missing information and implementation boundary

- The width formula, zero-volume handling, price-axis drawing logic and exact history limit are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; this does not establish implementation parity or complete historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Equivolume bars. Width is determined by volume. Please note that equivolume bars are rendered independently of the time scale.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
As such you are only able to view the most recent bars and no bar replay beyond that range.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_abwbbb9h_equivolume_bars](../tv_abwbbb9h_equivolume_bars.md)

## Source

https://www.tradingview.com/script/abwBbB9h-Equivolume-Bars/

Publication ID: abwBbB9h. Source SHA-256: 587808ed4282735a7b403a5366e74a3c75e5b14e6ca09d086328a7d6682a1748. Raw-description SHA-256: f823bc7562cb90f656d2feac18a24c33d16b8f31047c44537e09921b37b4b448.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
