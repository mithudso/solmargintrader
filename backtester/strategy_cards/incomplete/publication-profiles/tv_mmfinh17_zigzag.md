---

id: tv_profile_mmfinh17

name: "Zigzag"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Represent calculated zigzag structure, attached indicators and multilevel drawing state in reusable objects."

registry_key: null

runner: null

evaluation: null

---

# Zigzag

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Represent calculated zigzag structure, attached indicators and multilevel drawing state in reusable objects.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The API/data model is documented, but the central pivot and recursive-level algorithms are not.

- Pivot detection/replacement equations
- Next-level reduction and ratios
- Initialization/custom-input validation

## How it works

- Calculate pivots from regular/custom OHLC with optional indicator matrices; retain pivot coordinates, direction, level, ratios and subcomponents. Build higher zigzag levels and expose fresh/plain/continuous drawing methods plus serialization and price/bar getters.

## Outputs and intended use

- Use pivot arrays/flags as financial structure inputs for pattern or divergence tools. newPivot,doublePivot and updateLastPivot flags distinguish state changes; the last flag explicitly supports replacement of the newest pivot.

## Parameters and stated settings

- Zigzag length defaults5, retained pivots20 and offset0 for the latest bar. Drawing defaults are blue solid width1, labels off, maximum300 objects and time-based x coordinates.

## Failure modes and caveats

- Latest-bar calculation and last-pivot replacement mean downstream consumers must decide when a pivot is confirmed. Object interfaces and labels alone do not prove non-repainting behavior.

## Missing information and implementation boundary

- Pivot detection/replacement, next-level reduction, ratio definitions, custom-OHLC validation and initialization are absent despite detailed API documentation.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV or caller-derived financial objects support the input class; algorithm gaps are separate from raw data availability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Zigzag length. Default value is 5
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default value is 20
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Default is 0 - which means calculation is done based on the latest bar.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Max number of zigzag lines to display. Default is 300
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
true if new pivot calculated replaces the old one.
```

## Source

https://www.tradingview.com/script/MmfInH17-Zigzag/

Publication ID: MmfInH17. Source SHA-256: 065d3df779a4339da5c7e7893d016c3595eabdbb2c28e404c6887eafbc69d78b. Raw-description SHA-256: ec643b0864703fc03b398ea90ad1c68dde1c2ce457e13ee7bf47866be2c9d9a6.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
