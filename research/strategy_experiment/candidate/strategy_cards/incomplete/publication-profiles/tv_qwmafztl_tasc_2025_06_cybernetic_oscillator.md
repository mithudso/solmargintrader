---

id: tv_profile_qwmafztl

name: "TASC 2025.06 Cybernetic Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Isolate a configurable band of cyclical price behavior and normalize its amplitude for trend or threshold-oriented viewing."

registry_key: null

runner: null

evaluation: null

---

# TASC 2025.06 Cybernetic Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Isolate a configurable band of cyclical price behavior and normalize its amplitude for trend or threshold-oriented viewing.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The filter topology and bandwidth choices are given, but exact recurrences and normalization details are absent.

- Two-pole high-pass/SuperSmoother coefficients
- RMS initialization/window and threshold defaults

## How it works

- Cascade a two-pole high-pass filter with a two-pole SuperSmoother low-pass filter, then divide the result by RMS. High-pass critical period limits longest waves and low-pass period limits shortest waves.

## Outputs and intended use

- Trend display colors by zero sign; Threshold display uses a gray line and highlights user-defined extremes. This is a filtered market representation, not direct evidence of stable future cycles.

## Parameters and stated settings

- Default passband spans twenty-to-thirty bars; an example longer high-pass setting is 250. RMS length is configurable, minimum low-pass above eight is recommended and high-pass must not be below low-pass.

## Failure modes and caveats

- RMS-scaled amplitudes are standard-deviation-like only under suitable distribution/mean assumptions. Filter choices alter phase/lag, and invalid bandwidth produces a runtime error.

## Missing information and implementation boundary

- Filter coefficient recurrences, initialization, RMS window default, zero-RMS handling and threshold defaults are not in the description.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; code parity and complete market coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
cascades two-pole highpass and lowpass filters
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default settings to pass cycles between 20 and 30 bars
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
larger highpass period of 250 bars
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
smallest period to a value above 8
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qwmafztl_tasc_2025_06_cybernetic_oscillator](../tv_qwmafztl_tasc_2025_06_cybernetic_oscillator.md)

## Source

https://www.tradingview.com/script/QwMaFZTL-TASC-2025-06-Cybernetic-Oscillator/

Publication ID: QwMaFZTL. Source SHA-256: cb4a94725a12820ae777c21d0ead5d9eb1b1bd44e89f965e1d007917046df47f. Raw-description SHA-256: 610712fbbea081b57123a5fe9e9623176615e0628b2f1fe36f661e5ece2ab65b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
