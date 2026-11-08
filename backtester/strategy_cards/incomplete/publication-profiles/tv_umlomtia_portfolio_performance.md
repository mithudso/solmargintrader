---

id: tv_profile_umlomtia

name: "Portfolio Performance"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Portfolio Performance reports the historical behavior of a user-composed multi-instrument allocation. It combines a statistics table, monthly performance chart and benchmark comparison so users can inspect both overall results and instrument contributions. The source is a concise feature announcement, not an accounting specification. Its configurable rebalancing feature matters because a periodic target-weight portfolio can behave differently from a buy-and-hold allocation even when both start with the same weights."

registry_key: null

runner: null

evaluation: null

---

# Portfolio Performance

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Portfolio Performance reports the historical behavior of a user-composed multi-instrument allocation. It combines a statistics table, monthly performance chart and benchmark comparison so users can inspect both overall results and instrument contributions. The source is a concise feature announcement, not an accounting specification. Its configurable rebalancing feature matters because a periodic target-weight portfolio can behave differently from a buy-and-hold allocation even when both start with the same weights.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The listed core definitions remain unresolved.

- Portfolio accounting, rebalancing and statistics formulas are absent.
- Symbols, allocations and synchronized histories are unspecified.

## How it works

- Compose a selected instrument portfolio and evaluate it over the chosen date range and initial capital.
- Apply a configurable rebalancing period, calculate contribution and basic statistics, and compare portfolio and benchmark monthly performance.

## Outputs and intended use

- Inspect the monthly portfolio/benchmark display and statistics table.
- Customize presentation; no broker reconciliation or order execution is described.

## Parameters and stated settings

- Up to 15 instruments are supported. Initial capital, dates and rebalance period are configurable; numeric defaults are absent.

## Failure modes and caveats

- Historical performance is not a forecast; omitted costs and allocation mechanics can materially affect results.

## Missing information and implementation boundary

- Weights, compounding, rebalance timestamp, cash/cost/dividend treatment, contribution attribution and metric definitions are not provided.

## Data requirements

Required inputs: selected instrument histories, benchmark history, portfolio allocation inputs.

Repository input-class support: unavailable or unresolved. Selected external inputs and history are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
Compose portfolio with up to 15 instruments
```

### E2: parameters, mechanism

```text
Change Initial capital / date range / rebalancing period
```

### E3: outputs_and_use

```text
Compute instruments contribution
```

### E4: outputs_and_use

```text
Display monthly performance of portfolio and benchmark
```

## Source

https://www.tradingview.com/script/umloMtiA-Portfolio-Performance/

Publication ID: umloMtiA. Source SHA-256: c5f93d1db14b00aefd424a82e302460b0ea46b52b8b805c000db734a072e8955. Raw-description SHA-256: d96b5f688632c5337a1f822255cf576a83105897b2d92344573237b9b083da0f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
