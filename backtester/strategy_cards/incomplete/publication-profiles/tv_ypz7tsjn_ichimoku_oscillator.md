---

id: tv_profile_ypz7tsjn

name: "Ichimoku Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Ichimoku Oscillator translates several Ichimoku relationships into stacked oscillator layers so the user can inspect directional agreement. Its entry interpretation requires all layers to align with the main trend, rather than entering immediately when the trend changes. It also proposes partial-profit events and optional ATR protection, but the full adjusted equations are not provided."

registry_key: null

runner: null

evaluation: null

---

# Ichimoku Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Ichimoku Oscillator translates several Ichimoku relationships into stacked oscillator layers so the user can inspect directional agreement. Its entry interpretation requires all layers to align with the main trend, rather than entering immediately when the trend changes. It also proposes partial-profit events and optional ATR protection, but the full adjusted equations are not provided.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Main-trend formula, cloud boundary selection, Ichimoku lengths/displacement defaults, ATR adaptation and bounce definition are missing.

- Main-trend formula, cloud boundary selection, Ichimoku lengths/displacement defaults, ATR adaptation and bounce definition are missing.

## How it works

- Construct layer distances from close/cloud, displaced lagging/cloud, conversion/base and leading-span separation.
- Evaluate all-layer agreement under a main trend, optionally alter conversion/base with ATR and add EMA-based partial-profit context.

## Outputs and intended use

- Enter in the main direction only after all layers agree; close on main-trend change and optionally take partial profits on conversion/base or EMA/fourth-layer crosses.

## Parameters and stated settings

- Four layers are described; ATR option, EMA partial-profit option, bounce markers and customizable alerts/messages are configurable without default lengths.

## Failure modes and caveats

- Analytical: displaced components require careful time alignment and multiple crosses can whipsaw; partial-profit instructions omit quantity.

## Missing information and implementation boundary

- Main-trend formula, cloud boundary selection, Ichimoku lengths/displacement defaults, ATR adaptation and bounce definition are missing.

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
There are four layer:
```

### E2: mechanism, readiness

```text
distance between Conversion and Base lines
```

### E3: outputs_and_use, readiness

```text
you need to wait for all other conditions met
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_ypz7tsjn_ichimoku_oscillator](../tv_ypz7tsjn_ichimoku_oscillator.md)

## Source

https://www.tradingview.com/script/ypZ7TSjN-Ichimoku-Oscillator/

Publication ID: ypZ7TSjN. Source SHA-256: d884df83e0bb80767ca32266c58328acd10ed8414094df082f919995e469bb38. Raw-description SHA-256: 00b28ba83e7dd3e5dfe6a033d239fb7799e5ece6cc28d92e7d05a7c188540a2f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
