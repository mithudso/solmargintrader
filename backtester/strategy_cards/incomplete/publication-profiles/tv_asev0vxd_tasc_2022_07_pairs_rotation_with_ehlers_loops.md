---

id: tv_profile_asev0vxd

name: "TASC 2022.07 Pairs Rotation With Ehlers Loops"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Visualize relative cyclical strength of two securities to guide a long-only rotation between them."

registry_key: null

runner: null

evaluation: null

---

# TASC 2022.07 Pairs Rotation With Ehlers Loops

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Visualize relative cyclical strength of two securities to guide a long-only rotation between them.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Filter coefficients, RMS window, rotation detection, turnover costs, switching confirmation and cash-state rules are missing.

- Filter coefficients, RMS window, rotation detection, turnover costs, switching confirmation and cash-state rules are missing.

## How it works

- Apply identical high-pass and SuperSmoother filters to both prices, divide each band-limited stream by its RMS and plot one against the other as a loop. Chart-symbol values occupy the vertical axis and reference values the horizontal axis.

## Outputs and intended use

- Thicker segments indicate recent observations. The author associates clockwise upward motion with owning the chart asset and counterclockwise rightward motion with owning the reference; only one security is held at a time.

## Parameters and stated settings

- Low-pass and high-pass periods control bandwidth, and Loop Segments sets the displayed interval. Numerical defaults and symbol choices are absent.

## Failure modes and caveats

- Rotation direction can change with filter settings and lag. The stated reversal expectation beyond one or two deviations is a heuristic, not validated probability or executable switching logic.

## Missing information and implementation boundary

- Filter coefficients, RMS window, rotation detection, turnover costs, switching confirmation and cash-state rules are missing.

## Data requirements

Required inputs: aligned prices for two selected securities.

Repository input-class support: unavailable or unresolved. A selected reference security and aligned two-asset history are required but not supplied in the saved source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This strategy works by having a long position in only one of two securities
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
individually filtered using identical high-pass and SuperSmoother filters.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
dividing each of them by their
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
root-mean-square
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data

```text
the thicker line corresponds to the later data points.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_asev0vxd_tasc_2022_07_pairs_rotation_with_ehlers_loops](../tv_asev0vxd_tasc_2022_07_pairs_rotation_with_ehlers_loops.md)

## Source

https://www.tradingview.com/script/AsEv0Vxd-TASC-2022-07-Pairs-Rotation-With-Ehlers-Loops/

Publication ID: AsEv0Vxd. Source SHA-256: d92fa3f1855598132a12ba2961fbdcc82bd2bd363b4ec210d938092127f140e0. Raw-description SHA-256: 4e686b32913dcb579b790f10897db51a8ce0cab86a5f3deab96d1549232ac7b6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
