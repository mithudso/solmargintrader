---

id: tv_profile_n8flt7gc

name: "Penrose Diagram"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Translate session-relative historical price excursions into repeated triangle geometry inspired by Penrose diagrams."

registry_key: null

runner: null

evaluation: null

---

# Penrose Diagram

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Translate session-relative historical price excursions into repeated triangle geometry inspired by Penrose diagrams.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact vertex formula, averaging basis, session timezone, line timing and actionable interpretation are not disclosed.

- Exact vertex formula, averaging basis, session timezone, line timing and actionable interpretation are not disclosed.

## How it works

- Measure average and maximum/minimum distances from session open over a selected day sample. Use those data-dependent points to construct a triangle, then rotate copies and translate them above/below the current open; start new geometry each session.

## Outputs and intended use

- Extend the diagram to inspect price/time geometry. It is an analogy to a physics diagram, not an established causal or forecasting model. Overlap of copies is explicitly intentional.

## Parameters and stated settings

- The author prefers twenty-day averages for forex/futures and thirty for crypto; these are adjustable preferences. Extension and period controls are mentioned without exhaustive defaults.

## Failure modes and caveats

- Overlapping triangles reflect asymmetric high/low excursions, not necessarily market signals. Flexible geometry can invite hindsight pattern fitting and depends on session-open conventions.

## Missing information and implementation boundary

- Exact vertex formula, averaging basis, session timezone, line timing and actionable interpretation are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculation uses ordinary chart history; this establishes input class, not verified code, full history or profitability.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The data points for each triangle are variable upon the average highest/lowest point from Open Price and the Max/Min highest/lowest point from Open Price over a variable amount of days.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
I prefer to use a 20-Day Average Period for Forex and Futures Products, for Crypto a 30 Day Average Period
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
all triangles are exactly the same, just rotated 180°and translated above and below the current Session Open Price.
```

## Source

https://www.tradingview.com/script/N8flt7gC-Penrose-Diagram/

Publication ID: N8flt7gC. Source SHA-256: baed28ffe058cb5b1b5498ad614942f48b6f7fac83eca6b2254700ebdc0ba84b. Raw-description SHA-256: 60e81b9c8d6ca0b46ade8d7a1c48c98f02760b2d9031921e0ed685e450734ffd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
