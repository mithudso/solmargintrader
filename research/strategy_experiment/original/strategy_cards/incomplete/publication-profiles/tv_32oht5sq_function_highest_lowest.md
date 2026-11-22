---

id: tv_profile_32oht5sq

name: "Function Highest/Lowest"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Provide a reusable highest/lowest calculation building block for chart analysis, while leaving its exact interface and trading interpretation unspecified."

registry_key: null

runner: null

evaluation: null

---

# Function Highest/Lowest

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: study. Review: independently reviewed.

## Idea and objective

Provide a reusable highest/lowest calculation building block for chart analysis, while leaving its exact interface and trading interpretation unspecified.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: Function signatures, return types, missing-value behavior, initialization and example usage require the unavailable code.

- Function signatures, return types, missing-value behavior, initialization and example usage require the unavailable code.

## How it works

- The entire available description identifies a function for highest() and lowest(). It supplies no algorithm, argument list or demonstration, so no particular rolling-extreme formula can be reconstructed.

## Outputs and intended use

- A caller would use the named extreme-value functionality inside a larger calculation. The publication does not disclose a plotted indicator, signal or trading rule.

## Parameters and stated settings

- No source series, window length, default or tie-handling option is disclosed.

## Failure modes and caveats

- Assuming a particular lookback or pivot definition from the function name would create unsupported behavior.

## Missing information and implementation boundary

- Function signatures, return types, missing-value behavior, initialization and example usage require the unavailable code.

## Data requirements

Required inputs: caller-supplied numerical series.

Repository input-class support: unavailable or unresolved. The description names extreme-value functions but does not specify the required series or interface.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Function for highest() and lowest()
```

## Source

https://www.tradingview.com/script/32ohT5SQ-Function-Highest-Lowest/

Publication ID: 32ohT5SQ. Source SHA-256: bc7a80b4d11b1ad2d34b24f1327d0bae2cf1502af124145f4a2a8814eee0cc7d. Raw-description SHA-256: e5cc32f4f9bff7c6cbd5bc982f4a336a7a4d8081a821c2be4be03d4bacb4b29f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
