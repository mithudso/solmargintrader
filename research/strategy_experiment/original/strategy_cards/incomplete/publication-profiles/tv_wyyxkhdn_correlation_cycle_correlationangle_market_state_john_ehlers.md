---

id: tv_profile_wyyxkhdn

name: "Correlation Cycle, CorrelationAngle, Market State - John Ehlers"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "This publication combines Ehlers Correlation Cycle, CorrelationAngle and Market State into one indicator. Its financial purpose is to present cycle and state information in a unified view, while also demonstrating an optimized Pine implementation. The author attributes the original concepts to a Traders Tips article and says the implementation is heavily modified. The description devotes most of its space to development commentary, so neither the original reference nor the named outputs should be substituted for undisclosed calculation rules."

registry_key: null

runner: null

evaluation: null

---

# Correlation Cycle, CorrelationAngle, Market State - John Ehlers

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

This publication combines Ehlers Correlation Cycle, CorrelationAngle and Market State into one indicator. Its financial purpose is to present cycle and state information in a unified view, while also demonstrating an optimized Pine implementation. The author attributes the original concepts to a Traders Tips article and says the implementation is heavily modified. The description devotes most of its space to development commentary, so neither the original reference nor the named outputs should be substituted for undisclosed calculation rules.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- All core correlation, phase and market-state equations are undisclosed.

## How it works

- Combine the three named Ehlers components in a shared implementation.
- Use a consolidated loop as an optimization relative to the source design; no correlation kernels, angle equation or state classifier are shown.

## Outputs and intended use

- Inspect cycle, angle and market-state outputs together; a dark background can be disabled.
- No numerical signal thresholds, trade management or execution policy is specified.

## Parameters and stated settings

- The source names the June 2020 reference and Pine version 4.0; analytical periods/defaults are not supplied.

## Failure modes and caveats

- Author claims of surpassing the original design are unverified.
- A named external method does not establish which modifications affect the resulting signal.

## Missing information and implementation boundary

- Input series, correlation window/basis, phase transformation, state thresholds and modification details are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Chart OHLCV supports the default data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose

```text
Correlation Cycle, CorrelationAngle, and Market State
```

### E2: parameters

```text
TASC - June 2020 Traders Tips
```

### E3: risks, missing_information

```text
heavily modified version of the original indicator
```

### E4: mechanism

```text
only used one "for" loop
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_wyyxkhdn_correlation_cycle_correlationangle_market_state_john_ehlers](../tv_wyyxkhdn_correlation_cycle_correlationangle_market_state_john_ehlers.md)

## Source

https://www.tradingview.com/script/wyyXKHDn-Correlation-Cycle-CorrelationAngle-Market-State-John-Ehlers/

Publication ID: wyyXKHDn. Source SHA-256: 6569784ff876c0794916e28d61bfe31d0d01f7240e13f389a8c0d91d3dec4dde. Raw-description SHA-256: 8def94937ea3a0196aa37ca5a2e03e356bd95d604e667e8c1bec4884e82c694f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
