---

id: tv_profile_12ferxal

name: "HarmonicPattern"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide callable ratio and tolerance helpers for recognizing named harmonic and repeated-top/bottom patterns from supplied pivot values."

registry_key: null

runner: null

evaluation: null

---

# HarmonicPattern

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Provide callable ratio and tolerance helpers for recognizing named harmonic and repeated-top/bottom patterns from supplied pivot values.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The function signatures and tolerance default do not disclose the core pattern acceptance tables.

- Named-pattern ratio thresholds
- Tolerance/sign/boundary conventions
- Zero-leg handling

## How it works

- Compute AB-to-BC price or time ratios, test a value against a range and return boolean checks for harmonic triangle, two/three/four taps, ABCD,Bat,Butterfly,Gartley,Shark,5-0,Wolfe,Three Drives,triangles and head/shoulders. Inputs are ratios rather than an automatic pivot scanner.

## Outputs and intended use

- Importers can use these predicates inside a larger pattern detector. No detection timing, pivot selection or trading execution is defined by the library overview.

## Parameters and stated settings

- Most pattern checks expect negative triangle rates and default margin_of_error0.05,five percent. More complex patterns accept several ratios, including six for head/shoulders.

## Failure modes and caveats

- Sign conventions and inverse leg-ratio choices matter; assuming textbook positive-ratio tables could silently produce different results. A boolean named-pattern match does not establish reversal efficacy.

## Missing information and implementation boundary

- Actual numerical ratio ranges for each predicate, tolerance expansion/equality, zero-length-leg handling and output direction semantics are missing.

## Data requirements

Required inputs: caller pivot prices/times or leg ratios.

Repository input-class support: available. Callers can derive the required pivots/ratios from price history; missing pattern rules are algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Compute the price rate of the line AB divided by the the line BC
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
expects a negative rate.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
default 0.05(5%).
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
isHnS(rate_fed, rate_feb, rate_edc, rate_dcb, rate_cba, rate_eda, margin_of_error)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_double_top_bottom](../tv_method_double_top_bottom.md)
- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_method_head_shoulders](../../../strategy_research/tv_method_head_shoulders.md)
- [tv_method_triple_top_bottom](../../../strategy_research/tv_method_triple_top_bottom.md)

## Source

https://www.tradingview.com/script/12FErxAl-HarmonicPattern/

Publication ID: 12FErxAl. Source SHA-256: 2ee8b9156d12efc6de68e25603c57ffb96ce3fde5a409c86aea488cc92119ec1. Raw-description SHA-256: b9dfb4f3eadcac6f462c525ab83965f529e556ecb8f986f0f845a055644285a0.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
