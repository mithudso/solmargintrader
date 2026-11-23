---

id: tv_profile_ni17vkdu

name: "Reflex Oscillator - Dr. John Ehlers"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This Reflex Oscillator adaptation presents Ehlers’ cycle-sensitive oscillator with experimental smoothing controls. It aims to respond to reversals while retaining cyclical information, and exposes a reusable function for other scripts. The description’s near-zero-lag and bounded-range language is an author characterization rather than a verified implementation guarantee across every timeframe."

registry_key: null

runner: null

evaluation: null

---

# Reflex Oscillator - Dr. John Ehlers

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This Reflex Oscillator adaptation presents Ehlers’ cycle-sensitive oscillator with experimental smoothing controls. It aims to respond to reversals while retaining cyclical information, and exposes a reusable function for other scripts. The description’s near-zero-lag and bounded-range language is an author characterization rather than a verified implementation guarantee across every timeframe.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Reflex/filter recursions and normalization are undisclosed.

- Reflex/filter recursions and normalization are undisclosed.

## How it works

- Use the Reflex formulation with a Super Smoother stage and internal EMA, allowing an independent smoother override and post-smoothing adjustment.

## Outputs and intended use

- Inspect cyclical reversal-sensitive movement and configurable reference levels; the author suggests levels could support added alert conditions but does not give a trading rule.

## Parameters and stated settings

- The author claims a range around ±2 from second to monthly candles. Super Smoother override/period, Post Smooth and levels are adjustable without numeric defaults.

## Failure modes and caveats

- Analytical: extra smoothing changes timing and amplitude; source-stated range and lag behavior require empirical verification.

## Missing information and implementation boundary

- Reflex recursion, normalization, default lengths and actual alert/entry/exit conditions are not reproduced.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
bound range between +/-2.0
```

### E2: mechanism, readiness

```text
added an independent control for the Super Smoother.
```

### E3: parameters, mechanism, readiness

```text
"Post Smooth" input() that "tweaks" the internal Reflex EMA
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ni17vkdu_reflex_oscillator_dr_john_ehlers](../tv_ni17vkdu_reflex_oscillator_dr_john_ehlers.md)

## Source

https://www.tradingview.com/script/NI17VkdU-Reflex-Oscillator-Dr-John-Ehlers/

Publication ID: NI17VkdU. Source SHA-256: def28edf1a4c74c42599d23b18572792b6fa204ae9eedcf7459cbd94ff4fa251. Raw-description SHA-256: 00f499fac8114959095c7db3a11db4fabd813e33860e7da1e92c5378d8c9aeb6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
