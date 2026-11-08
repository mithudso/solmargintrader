---

id: tv_profile_we9amcve

name: "TASC 2026.04 A Synthetic Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Synthetic Oscillator estimates a changing cycle phase and outputs a sine wave synchronized to filtered price. It aims to avoid rapid direction flips by following broader cyclic structure rather than every price movement. A separate filter resets phase on sign crossings to reduce accumulated drift. The author warns the smooth synthetic peaks may arrive too early and suggests extra smoothing when needed."

registry_key: null

runner: null

evaluation: null

---

# TASC 2026.04 A Synthetic Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Synthetic Oscillator estimates a changing cycle phase and outputs a sine wave synchronized to filtered price. It aims to avoid rapid direction flips by following broader cyclic structure rather than every price movement. A separate filter resets phase on sign crossings to reduce accumulated drift. The author warns the smooth synthetic peaks may arrive too early and suggests extra smoothing when needed.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Filter coefficients, I/Q cycle-estimation equation, bounds/clamping, initialization and hardcoded settings beyond those listed are missing.

- Filter coefficients, I/Q cycle-estimation equation, bounds/clamping, initialization and hardcoded settings beyond those listed are missing.

## How it works

- Smooth source with Hann window, band-limit via highpass/SuperSmoother, normalize by RMS and derive a normalized rate-of-change quadrature component.
- Estimate instantaneous cycle from real/imaginary components, accumulate reciprocal cycle into phase and reset phase with a secondary highpass/UltimateSmoother signal.
- Return sine of final phase.

## Outputs and intended use

- Inspect zero crossings and ±1 turns as potential cyclic cues, adjusting timing in another script if appropriate.

## Parameters and stated settings

- Hann stage uses twelve bars, both RMS normalizations use one hundred bars, derivative lag is one bar and phase resets to 0/180 degrees. Source and cycle lower/upper bounds are configurable.

## Failure modes and caveats

- Analytical: cycle estimates are unstable in noncyclic markets; phase resets can shift interpretation and a smooth sine is not proof of predictive timing.

## Missing information and implementation boundary

- Filter coefficients, I/Q cycle-estimation equation, bounds/clamping, initialization and hardcoded settings beyond those listed are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
12-bar Hann Window filter
```

### E2: parameters, readiness

```text
100-bar root mean square
```

### E3: parameters, readiness

```text
one-bar rate of change
```

### E4: parameters, readiness

```text
reset[/i] the angle to 0 or 180 degrees
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_we9amcve_tasc_2026_04_a_synthetic_oscillator](../tv_we9amcve_tasc_2026_04_a_synthetic_oscillator.md)

## Source

https://www.tradingview.com/script/we9AMcvE-TASC-2026-04-A-Synthetic-Oscillator/

Publication ID: we9AMcvE. Source SHA-256: 46416d7f92e1091a80f340eca5e7df72a1ddea8aba2b4b2fd938a8f232c5b78a. Raw-description SHA-256: 86b7b8c0d2d6f42632f03c27de2481f0bf146ee2166cfd70be044565c873c6dc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
