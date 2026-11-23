---

id: tv_profile_hjjizrog

name: "Manual Harmonic Patterns - With interactive inputs"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Validate harmonic relationships in a manually selected XABCD drawing instead of automatically scanning historical prices."

registry_key: null

runner: null

evaluation: null

---

# Manual Harmonic Patterns - With interactive inputs

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Validate harmonic relationships in a manually selected XABCD drawing instead of automatically scanning historical prices.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Harmonic ratio tables, PRZ construction, tolerance defaults and the unexplained additional F point in the ordering note are missing.

- Harmonic ratio tables, PRZ construction, tolerance defaults and the unexplained additional F point in the ordering note are missing.

## How it works

- The user selects ordered pivot points through interactive inputs. The tool checks harmonic-pattern validity and draws filled triangles and a named potential-reversal-zone box when its ratio tests pass.

## Outputs and intended use

- Valid patterns receive lines, labels, fills and PRZ identification; invalid drawings retain plain XABCD lines. The user remains responsible for choosing genuine pivots and a permissible price path.

## Parameters and stated settings

- Point selection is interactive. The source describes bullish and bearish pivot alternation, but does not disclose ratio tolerances or the supported pattern set.

## Failure modes and caveats

- The tool does not verify pivot correctness, overflow across XB/BD lines or chronological point ordering. A displayed valid ratio pattern can therefore still violate broader harmonic rules.

## Missing information and implementation boundary

- Harmonic ratio tables, PRZ construction, tolerance defaults and the unexplained additional F point in the ordering note are missing.

## Data requirements

Required inputs: ohlcv, user-selected ordered XABCD points.

Repository input-class support: available. Price history is sufficient for the market-data class, but interactive pivot choices are required; no automatic pattern reconstruction is implied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
This is not a scanner and it will not scan historical bars for harmonic patterns.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Script will not check if selected pivots are correct.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Script will not check for overflow conditions.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*] Show PRZ box which shoes the name of valid patterns.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hjjizrog_manual_harmonic_patterns_with_interactive_inputs](../tv_hjjizrog_manual_harmonic_patterns_with_interactive_inputs.md)
- [tv_method_harmonic_xabcd](../tv_method_harmonic_xabcd.md)

## Source

https://www.tradingview.com/script/hjjizROg-Manual-Harmonic-Patterns-With-interactive-inputs/

Publication ID: hjjizROg. Source SHA-256: a8551711daad8d546d98e3803209587cca80fa4913f225144200ff95ffa09b17. Raw-description SHA-256: e80eacfa0e113a8879fe9d51d7741cd4fd359675f684993726838634d0b6b256.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
