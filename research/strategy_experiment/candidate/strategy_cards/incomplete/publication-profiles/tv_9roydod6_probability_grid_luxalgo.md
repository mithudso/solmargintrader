---

id: tv_profile_9roydod6

name: "Probability Grid [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Probability Grid maps historical swing reversals into a joint price-and-time grid anchored at the latest reversal. It aims to show how far away and how late a next reversal might occur relative to past swings. The user can view values as probability beyond a cell or within that cell. Normalized mode uses returns rather than raw price distances so earlier low-price history is more comparable with later history. The probabilities should be understood as the tool’s historical-distribution estimates, not calibrated guarantees about the next market turning point."

registry_key: null

runner: null

evaluation: null

---

# Probability Grid [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Probability Grid maps historical swing reversals into a joint price-and-time grid anchored at the latest reversal. It aims to show how far away and how late a next reversal might occur relative to past swings. The user can view values as probability beyond a cell or within that cell. Normalized mode uses returns rather than raw price distances so earlier low-price history is more comparable with later history. The probabilities should be understood as the tool’s historical-distribution estimates, not calibrated guarantees about the next market turning point.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Swing confirmation and the joint reversal-probability estimator are missing.

- Swing confirmation and the joint reversal-probability estimator are missing.

## How it works

- Identify swings using Swing Length and retain up to Maximum Reversals.
- Collect price distances or normalized returns between reversals, then construct percentile-based grid boundaries.
- Display beyond-area or within-cell probability estimates from the last reversal.

## Outputs and intended use

- Grid and/or dashboard visualize price/time reversal distribution; optional marks show detected reversals.

## Parameters and stated settings

- Grid is 10×10; default deciles span percentiles 0–90, with at least two enabled.
- Normalized data and beyond-cell mode are defaults; swing length, sample count, percentiles and display placement/styles are adjustable.
- The source says each default within-cell decile cell has 1% probability; this is its model description.

## Failure modes and caveats

- Joint reversal timing and distance need not be independent; equal cell probabilities require a justified construction absent here.
- Swing identification can lag and market regimes can invalidate historical frequencies.

## Missing information and implementation boundary

- Exact swing confirmation, joint-distribution formula, dependence treatment, sample defaults and trade-management rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Swing highs/lows, elapsed bars and returns are OHLCV-derived; probability methodology is an algorithm gap.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, outputs_and_use, readiness

```text
10x10 grid
```

### E2: parameters

```text
percentiles from 0 to 90
```

### E3: parameters

```text
two of them must always be enabled
```

### E4: parameters, risks

```text
each cell has the same 1% probability
```

### E5: parameters

```text
By default the tool displays the normalized data
```

### E6: parameters

```text
default mode is Probability Beyond Each Cell
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_9roydod6_probability_grid_luxalgo](../tv_9roydod6_probability_grid_luxalgo.md)

## Source

https://www.tradingview.com/script/9royDOd6-Probability-Grid-LuxAlgo/

Publication ID: 9royDOd6. Source SHA-256: 4800888a6025d79c3bccf2c07841b35982ff01c56ff3e42e3f63810b6ab30a2b. Raw-description SHA-256: f4052c28aadabdc654ca2f90ac650981ace62ec195795d41b2b31896523a2324.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
