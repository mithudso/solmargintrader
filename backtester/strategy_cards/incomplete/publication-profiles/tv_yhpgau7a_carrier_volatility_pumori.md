---

id: tv_profile_yhpgau7a

name: "Carrier Volatility [Pumori]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Explore an intentionally overreactive fractional-length recursive transform as a visual carrier of rapid changes in RSI or price."

registry_key: null

runner: null

evaluation: null

---

# Carrier Volatility [Pumori]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Explore an intentionally overreactive fractional-length recursive transform as a visual carrier of rapid changes in RSI or price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The named fractional EMA transform lacks the recurrence and stability controls needed for reproducible safe numerical behavior.

- Fractional EMA coefficient/recurrence
- Initialization and stability/overflow handling
- Envelope calculation

## How it works

- Apply two fractional EMA-like recursions at length 0.1 to a chosen source, producing overshoot/correction oscillations. Use RSI by default, its SMA for diagnostic smoothing or close for price-domain display.

## Outputs and intended use

- Interpret envelope expansion/contraction as activity context and waveform jitter as movement quality. The source describes a research component, with Kalman integration only planned for future work.

## Parameters and stated settings

- Both transform lengths default 0.1. RSI length and its SMA length default fourteen; RSI is the default mode, RSI-SMA diagnostic and close the price mode.

## Failure modes and caveats

- A conventional EMA coefficient at sub-unit length can be unstable. Bounded input alone does not prove stable recursion, so the author's controlled-instability and lag-free claims require explicit recurrence and numerical tests.

## Missing information and implementation boundary

- The actual fractional EMA coefficient, seed/reset, overflow stabilization, envelope extraction and signal thresholds are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; code parity and historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
EMA Lengths: 0.1, 0.1
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
RSI Length: 14
RSI SMA Length: 14
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
A sub-unit length (N < 1) is intentionally used to produce an anti-smoothing response
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_kalman_filter](../tv_method_kalman_filter.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_yhpgau7a_carrier_volatility_pumori](../../../strategy_research/tv_yhpgau7a_carrier_volatility_pumori.md)

## Source

https://www.tradingview.com/script/yHpgAu7A-Carrier-Volatility-Pumori/

Publication ID: yHpgAu7A. Source SHA-256: 058b7199a1aa6ee641308309291b41caefb78d16aa55fc0eca9b12cbca55c94d. Raw-description SHA-256: 27e950b2a05ed5230e4d52d93f74ce650dc2efb16591e72f1da421d1a97c227e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
