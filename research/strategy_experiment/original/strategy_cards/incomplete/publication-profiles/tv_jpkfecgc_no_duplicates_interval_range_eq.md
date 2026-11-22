---

id: tv_profile_jpkfecgc

name: "No Duplicates Interval Range & EQ"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "This level-display utility reduces chart clutter when range or equilibrium references from different intervals coincide. It prefers the higher-timeframe representation instead of drawing duplicate labels or levels at the same place. That is useful for viewing hierarchical market references without mistaking overlapping drawings for multiple independent levels."

registry_key: null

runner: null

evaluation: null

---

# No Duplicates Interval Range & EQ

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This level-display utility reduces chart clutter when range or equilibrium references from different intervals coincide. It prefers the higher-timeframe representation instead of drawing duplicate labels or levels at the same place. That is useful for viewing hierarchical market references without mistaking overlapping drawings for multiple independent levels.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Range/EQ level construction and duplicate comparison rules are undisclosed.

- Range/EQ level construction and duplicate comparison rules are undisclosed.

## How it works

- Generate Range and EQ levels, detect duplicates, and retain the higher-timeframe version.

## Outputs and intended use

- View a cleaned set of interval references; the author’s example shows weekly open while hiding daily open when they coincide on Monday.

## Parameters and stated settings

- The example is Monday’s open; no duplicate tolerance, selectable intervals or default settings are specified.

## Failure modes and caveats

- Analytical: suppressing a duplicate can hide its lower-timeframe provenance, and identical displayed levels are not independent evidence.

## Missing information and implementation boundary

- Range and EQ formulas, numerical equality tolerance, timeframe set and display confirmation timing are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
Generates Range & EQ levels and removes duplicates. Prioritizes by higher timeframe for duplicates.
```

### E2: parameters, outputs_and_use, readiness

```text
on Monday's open, weekly open is displayed while daily open is hidden automatically.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_jpkfecgc_no_duplicates_interval_range_eq](../tv_jpkfecgc_no_duplicates_interval_range_eq.md)

## Source

https://www.tradingview.com/script/JpKfECGC-No-Duplicates-Interval-Range-EQ/

Publication ID: JpKfECGC. Source SHA-256: ea67ff2938ccdd7abbb77d3f51e2ad787c3761f10cd9f4bf409e3eed68b859fb. Raw-description SHA-256: ba25ab201a10be30f553be68fed7dd4eb1c1c308e2e9639068434dbad4718a94.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
