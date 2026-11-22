---

id: tv_profile_fnlmn99w

name: "TASC 2026.09 Adaptive SuperSmoother"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Adaptive SuperSmoother adjusts a filter’s critical period according to movement in a fixed-period companion filter. It aims to retain high-frequency noise suppression while responding faster to changing market direction. The adaptive line is compared with the fixed line, and their difference is displayed separately. Ehlers’s suggested directional interpretation is long when adaptive is above fixed and short otherwise, with difference peaks/valleys as possible turning-point clues. Those suggestions are signal concepts rather than a full executable strategy with fills and risk controls."

registry_key: null

runner: null

evaluation: null

---

# TASC 2026.09 Adaptive SuperSmoother

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Adaptive SuperSmoother adjusts a filter’s critical period according to movement in a fixed-period companion filter. It aims to retain high-frequency noise suppression while responding faster to changing market direction. The adaptive line is compared with the fixed line, and their difference is displayed separately. Ehlers’s suggested directional interpretation is long when adaptive is above fixed and short otherwise, with difference peaks/valleys as possible turning-point clues. Those suggestions are signal concepts rather than a full executable strategy with fills and risk controls.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The complete filter recurrence and adaptive-period normalization are not supplied.

- The complete filter recurrence and adaptive-period normalization are not supplied.

## How it works

- Filter the source with a fixed-period SuperSmoother, then compute its one-bar change and rolling RMS.
- Scale change by RMS and cap the scaled value; square one minus half that value to derive a period factor.
- Multiply the base period by the factor, enforce a minimum, and run a second SuperSmoother with that adaptive period.

## Outputs and intended use

- Red fixed and blue adaptive lines plus a difference oscillator support directional comparison.

## Parameters and stated settings

- Defaults: Close source, base period 20 and RMS length 81.
- Scaled ROC is capped at 2 and adaptive period floored at 2.

## Failure modes and caveats

- The source does not clarify signed-versus-absolute ROC treatment, materially affecting the period factor.
- Filter crossings can whipsaw and do not establish profitable execution.

## Missing information and implementation boundary

- Exact SuperSmoother coefficients, ROC definition, RMS initialization/zero handling, turning-point confirmation and trade management are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Source prices, changes and RMS are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
one-bar ROC
```

### E2: parameters, mechanism

```text
limit the maximum scaled value to 2.
```

### E3: parameters

```text
minimum value of 2
```

### E4: parameters

```text
default is 20.
```

### E5: parameters

```text
default is 81.
```

### E6: parameters

```text
default is "Close".
```

### E7: outputs_and_use

```text
long when the Adaptive SuperSmoother is above the fixed-period SuperSmoother
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fnlmn99w_tasc_2026_09_adaptive_supersmoother](../tv_fnlmn99w_tasc_2026_09_adaptive_supersmoother.md)

## Source

https://www.tradingview.com/script/FnlMn99W-TASC-2026-09-Adaptive-SuperSmoother/

Publication ID: FnlMn99W. Source SHA-256: 85d94ae0db5903deb06e46fb1fa03f2bef951ddeee17c042bdda1b676ea1d4c6. Raw-description SHA-256: cbb2a6700cdf4baaa60dcf4106a15faf8622506dd747ec72ab19c245d40e78f4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
