---

id: tv_profile_ouvjr45r

name: "chartpatterns"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: financial-library

summary: "Scan zigzag pivots for chart patterns and encapsulate their geometry, drawings and presentation properties in reusable objects."

registry_key: null

runner: null

evaluation: null

---

# chartpatterns

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** financial-library. Native publication type: library. Review: independently reviewed.

## Idea and objective

Scan zigzag pivots for chart patterns and encapsulate their geometry, drawings and presentation properties in reusable objects.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Allowed-pattern encoding, classification formulas, ratio tolerances/defaults, overlap logic and dependency version compatibility are not given.

- Allowed-pattern encoding, classification formulas, ratio tolerances/defaults, overlap logic and dependency version compatibility are not given.

## How it works

- findPattern consumes a ZigzagLite object, scan properties and pattern array. Candidate patterns use trendlines through alternating pivots, compare their slope/retracement/bar ratios and optionally avoid overlap; draw/erase methods manage the resulting objects.

## Outputs and intended use

- Return a Pattern object with pivots, paired lines, names/types, ratio difference, internal zigzag and labels. It is chart-pattern infrastructure, not a standalone entry/exit system.

## Parameters and stated settings

- Search uses five or six pivots. Offset one is recommended for a non-repainting scan; error/flat ratios, optional bar-ratio limit, allowed-pattern flags, themes and drawing widths/labels are configurable.

## Failure modes and caveats

- Skipping the newest pivot can reduce dependence on developing structure but does not independently prove every upstream input never repaints. Pattern labels depend on undisclosed type rules.

## Missing information and implementation boundary

- Allowed-pattern encoding, classification formulas, ratio tolerances/defaults, overlap logic and dependency version compatibility are not given.

## Data requirements

Required inputs: zigzag pivot objects, caller scan properties and pattern array.

Repository input-class support: available. These are caller-provided financial structures derivable from OHLCV; missing algorithm details do not imply missing raw market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Set it to 1 for non repainting scan.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Can be either 5 or 6
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
First trend line joining pivots 1, 3, 5
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Second trend line joining pivots 2, 4 (, 6)
```

## Source

https://www.tradingview.com/script/OuVJr45r-chartpatterns/

Publication ID: OuVJr45r. Source SHA-256: b7fa14408fddf8712c283ac231ea50c1dfa4868ab9fb10367a903a5f6b58161c. Raw-description SHA-256: e95382e8c327560211dad0c779b63e8969ac878192c1b9703a5076a348db3574.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
