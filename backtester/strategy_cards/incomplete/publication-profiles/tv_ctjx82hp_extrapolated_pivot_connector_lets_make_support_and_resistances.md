---

id: tv_profile_ctjx82hp

name: "Extrapolated Pivot Connector - Lets Make Support And Resistances"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Extrapolate support and resistance lines from selected pairs of historical pivots, including pivots in another indicator series."

registry_key: null

runner: null

evaluation: null

---

# Extrapolated Pivot Connector - Lets Make Support And Resistances

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Extrapolate support and resistance lines from selected pairs of historical pivots, including pivots in another indicator series.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The line interpolation is clear, but the pivot-detection contract and endpoint indexing are not sufficiently specified for reproducible output.

- Pivot high/low detection and confirmation rule
- Anchor-index semantics/defaults

## How it works

- Detect high/low pivots at a chosen sensitivity and connect selected older/newer highs for resistance and lows for support. Extend each connection linearly; a custom-source mode applies the same process to an oscillator or average.

## Outputs and intended use

- Labels identify chosen anchor positions. Use the projections as linear structure references, with source scaling considered when transferring the tool to indicator panes.

## Parameters and stated settings

- Length sets pivot sensitivity; A-High/B-High and A-Low/B-Low select endpoints. Length five and a fifty-period average are examples, not confirmed defaults. Custom-source mode must be explicitly enabled for another indicator.

## Failure modes and caveats

- Pivot confirmation is delayed, and linear extrapolation assumes a locally linear structure. Log display advice does not establish that calculations themselves use log prices.

## Missing information and implementation boundary

- Exact pivot test/confirmation, endpoint indexing defaults, invalidation and alert rules are not specified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the disclosed input class; source-code parity and cached historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
made by connecting past pivot high's/low's to more recent ones and extrapolating the resulting connection.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The A-High parameter determine the position of the pivot high to be used as first point
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The B-High parameter determine the last pivot high.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The figure above use length = 5.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ctjx82hp_extrapolated_pivot_connector_lets_make_support_and_resistances](../tv_ctjx82hp_extrapolated_pivot_connector_lets_make_support_and_resistances.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/CtjX82Hp-Extrapolated-Pivot-Connector-Lets-Make-Support-And-Resistances/

Publication ID: CtjX82Hp. Source SHA-256: 946b708d5e548ebef35416a9d5c4288067fa8bbbebeef51e053a616e1cdb24bb. Raw-description SHA-256: 6b1403fa0b34f16c567ee1ec4d2b53b6d90c5f40d9983d8b0c1d694dbfd8f1bc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
