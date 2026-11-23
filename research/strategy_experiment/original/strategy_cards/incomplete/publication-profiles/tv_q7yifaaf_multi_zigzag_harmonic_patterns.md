---

id: tv_profile_q7yifaaf

name: "Multi ZigZag Harmonic Patterns"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Search harmonic price structures across multiple zigzag depths to reveal patterns visible at different swing scales."

registry_key: null

runner: null

evaluation: null

---

# Multi ZigZag Harmonic Patterns

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Search harmonic price structures across multiple zigzag depths to reveal patterns visible at different swing scales.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Ratio tolerance for equality, pivot confirmation, overlap suppression, PRZ calculation and trade-management rules are missing.

- Ratio tolerance for equality, pivot confirmation, overlap suppression, PRZ calculation and trade-management rules are missing.

## How it works

- Build several depth-specific zigzags and compare their XABCD-style leg ratios with named pattern tables. The description lists Gartley, Crab, Deep Crab, Bat, Butterfly, Shark, Cypher, Three Drives and 5-0 tests.

## Outputs and intended use

- Use the resulting pattern annotations as candidate structural setups. Multiple depth matches are related observations, not independent proof of a reversal.

## Parameters and stated settings

- Select included zigzags and set each length, color, width and style. For example Gartley requires xab=0.618 and abc between 0.382 and 0.886, with bcd between 1.272 and 1.618 OR xad=0.786.

## Failure modes and caveats

- The tables explicitly use OR clauses; replacing them with stricter AND conditions would change the source. Developing zigzag legs can revise recent matches.

## Missing information and implementation boundary

- Ratio tolerance for equality, pivot confirmation, overlap suppression, PRZ calculation and trade-management rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price history supports the disclosed input class; source code and historical data parity have not been validated.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
this script generates harmonic patterns based on multiple deapth zigzags.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]xab = 0.618
[*]0.382 <= abc <= 0.886
[*]1.272 <= bcd <= 1.618 OR xad = 0.786
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Input parameter allows to chose which Zigzag to be included in pattern identification
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)
- [tv_q7yifaaf_multi_zigzag_harmonic_patterns](../tv_q7yifaaf_multi_zigzag_harmonic_patterns.md)

## Source

https://www.tradingview.com/script/Q7YifAAf-Multi-ZigZag-Harmonic-Patterns/

Publication ID: Q7YifAAf. Source SHA-256: d451a4f937840ca90ef2da8a2e5754a5dc85e7ba2777e90ba716f4c7e987220c. Raw-description SHA-256: 506a2a4b483fffcc199ca18ecdb2c009b5cf21e1e9cc177e7dd0b569d9bdcd8c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
