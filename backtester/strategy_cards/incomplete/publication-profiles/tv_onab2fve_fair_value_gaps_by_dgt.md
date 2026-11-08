---

id: tv_profile_onab2fve

name: "Fair Value Gaps by DGT"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Track price-gap regions across chart, higher and lower timeframes and show how subsequent price movement interacts with each region."

registry_key: null

runner: null

evaluation: null

---

# Fair Value Gaps by DGT

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Track price-gap regions across chart, higher and lower timeframes and show how subsequent price movement interacts with each region.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The core computation or input contract is not completely specified: The exact gap candle test, size filters, fill-percentage formula, state retirement and auto-timeframe mapping are omitted.

- The exact gap candle test, size filters, fill-percentage formula, state retirement and auto-timeframe mapping are omitted.

## How it works

- Detect fair-value-gap candidates, maintain unfilled/partially filled/resolved states and update fill percentages. Allow alternative fill definitions based on touch, midpoint, wick sweep or body beyond.

## Outputs and intended use

- Use zones, overlap and tooltips as a structural chart map. The description's institutional-footprint language is an interpretation; a price gap does not itself identify an institution or true order-book imbalance.

## Parameters and stated settings

- Choose timeframe mode, automatic lower-timeframe selection, fill logic and label visibility. Tooltips remain available at the midpoint when labels are hidden.

## Failure modes and caveats

- Timeframe-dependent detection and developing higher-timeframe bars can alter zones. Different fill definitions produce different histories and should not be mixed in validation.

## Missing information and implementation boundary

- The exact gap candle test, size filters, fill-percentage formula, state retirement and auto-timeframe mapping are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature uses ordinary OHLCV, including lower-timeframe history where selected. This establishes data class only, not a verified implementation or cache.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Automatic real-time monitoring of each FVG’s fill progress with live percentage updates
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
[*]Any Touch
[*]Midpoint Reached
[*]Wick Sweep
[*]Body Beyond
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
When set to “Auto,” the script intelligently selects the optimal lower timeframe based on the chart resolution.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fair_value_gap](../../tv_method_fair_value_gap.md)
- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_onab2fve_fair_value_gaps_by_dgt](../tv_onab2fve_fair_value_gaps_by_dgt.md)

## Source

https://www.tradingview.com/script/Onab2fvE-Fair-Value-Gaps-by-DGT/

Publication ID: Onab2fvE. Source SHA-256: e37258e21e53737c0aae53ad8f87bd2670d0652b032fbbfe661f58e955105a22. Raw-description SHA-256: a91362927ed4c298142c21c0a9f39114a374034afbccca4edb09383c5291fd93.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
