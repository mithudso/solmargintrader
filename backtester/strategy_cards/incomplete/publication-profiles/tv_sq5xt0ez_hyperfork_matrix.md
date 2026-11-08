---

id: tv_profile_sq5xt0ez

name: "Hyperfork Matrix"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Build a manually anchored pitchfork and propagate action/reaction geometry into a price-time lattice for discretionary chart study."

registry_key: null

runner: null

evaluation: null

---

# Hyperfork Matrix

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Build a manually anchored pitchfork and propagate action/reaction geometry into a price-time lattice for discretionary chart study.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The source provides a stepwise parameterized construction for manual pitchforks,propagation,lattice intersections and close-cross alerts.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Select alternating high/low pivots A/B/C. Use A,price-midpoint AB at A time,or full AB midpoint as Original/Schiff/Modified anchor. Draw median to BC midpoint and parallel tines through B/C; propagate by handle-length intervals,draw BC-parallel reaction and AB-parallel action lines,and intersect them with a selected pivot-price horizontal for lattice verticals.

## Outputs and intended use

- Display pitchfork,extra parallels,action/reaction lines and clamped lattice. Alerts detect close-to-close line crossings once per bar close. The cited eighty-percent median-return idea is author theory,not measured probability.

## Parameters and stated settings

- Manual timestamps,pivot start type,variant,extra parallels,log toggle,price filter,forward/backward extent,lattice source and styling are inputs. The stated five-hundred-line budget constrains dense layouts.

## Failure modes and caveats

- Manual pivots introduce hindsight selection. Log mode must be enabled separately; odd/even parallel counts may cause minor visual drift. Geometric intersections do not guarantee market turns.

## Missing information and implementation boundary

- Auto pivot-type selection and degenerate/parallel geometry edge handling are not fully detailed; principal manual geometry and crossing behavior are explicit.

## Data requirements

Required inputs: ohlcv, three manually selected pivot timestamps/prices.

Repository input-class support: available. Chart prices and user anchors are sufficient; astronomy/external data is not required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Anchor shifts 50% toward B in price
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Anchor shifts 50% toward B in both time and price
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Points are placed along the median line at handle-length intervals
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
parallel to B-C
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
parallel to A-B
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Alerts trigger once per bar close
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Maximum 500 lines
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_pitchfork](../../tv_method_pitchfork.md)
- [tv_sq5xt0ez_hyperfork_matrix](../../tv_sq5xt0ez_hyperfork_matrix.md)

## Source

https://www.tradingview.com/script/Sq5Xt0eZ-Hyperfork-Matrix/

Publication ID: Sq5Xt0eZ. Source SHA-256: aef4f6937191a401d39831daf23d05f3baceae20987061aa16b803cbb65a7539. Raw-description SHA-256: d4573fa3ee03cb84897b7d23391aa1e8849f2ed1c5ea1aabcff56f8fed167860.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
