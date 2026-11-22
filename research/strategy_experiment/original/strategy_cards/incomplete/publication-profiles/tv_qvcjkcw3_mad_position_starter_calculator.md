---

id: tv_profile_qvcjkcw3

name: "[MAD] Position starter & calculator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Position Starter & Calculator is an interactive trade ruler for planning entries, staged exits and loss limits. The user selects price/time points and quantities, then the indicator estimates prospective profit/loss, ratio and leveraged liquidation context. It is a planning graphic rather than an order executor, and the source expressly warns that liquidation assumptions vary by exchange."

registry_key: null

runner: null

evaluation: null

---

# [MAD] Position starter & calculator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Position Starter & Calculator is an interactive trade ruler for planning entries, staged exits and loss limits. The user selects price/time points and quantities, then the indicator estimates prospective profit/loss, ratio and leveraged liquidation context. It is a planning graphic rather than an order executor, and the source expressly warns that liquidation assumptions vary by exchange.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Entry-price definition, partial-target weighting, fees, liquidation formula and exchange maintenance contract are unspecified.

- Entry-price definition, partial-target weighting, fees, liquidation formula and exchange maintenance contract are unspecified.

## How it works

- Accept interactive SL, box bounds and take-profit points in long/short directional order, then calculate planned profit/loss for partial target volumes.
- Estimate stop loss and liquidation under selected leverage/maintenance assumptions; allow manual movement of time bounds in settings.

## Outputs and intended use

- Use the ruler to compare staged outcomes and risk/reward before a trade; no alerts are offered in this release.

## Parameters and stated settings

- Supports up to five targets, individually disabled with 0% volume. Five color schemes and adjustable leverage/maintenance are mentioned without numeric defaults.

## Failure modes and caveats

- Analytical: planned fills and liquidation estimates can diverge from venue execution, fees, funding and margin rules.

## Missing information and implementation boundary

- Entry-price definition, partial-target weighting, fees, liquidation formula and exchange maintenance contract are unspecified.

## Data requirements

Required inputs: user entry/stop/target prices and allocations, leverage and venue margin rules.

Repository input-class support: unavailable or unresolved. Requires caller trade configuration and verified venue liquidation inputs; OHLCV alone cannot define them.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to five target closing prices
```

### E2: parameters, readiness

```text
volume set to 0%
```

### E3: parameters, readiness

```text
five adjustable color schemes
```

### E4: risks, readiness

```text
subject to exchange variation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_qvcjkcw3_mad_position_starter_calculator](../tv_qvcjkcw3_mad_position_starter_calculator.md)

## Source

https://www.tradingview.com/script/qvCJKcW3-MAD-Position-starter-calculator/

Publication ID: qvCJKcW3. Source SHA-256: 9643d203b2e2ad8e845d22c230446e1d46cff0455e6e757299df5b28ac0bda23. Raw-description SHA-256: c674be3483eb4fd21eeabc897ab696f73fbaff5e6f2f762232f726b630315a5b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
