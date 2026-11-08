---

id: tv_profile_5a8qkpsh

name: "Point of Control V2 "

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Organize volume-profile points of control by reset period and identify historical concentrations relevant to the current price without extending every old level across the chart."

registry_key: null

runner: null

evaluation: null

---

# Point of Control V2

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Organize volume-profile points of control by reset period and identify historical concentrations relevant to the current price without extending every old level across the chart.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The described computation retains a blocking specification gap: The volume-at-price allocation method, increment formula, definition of Grand POC and ranking/tie rules are not disclosed.

- The volume-at-price allocation method, increment formula, definition of Grand POC and ranking/tie rules are not disclosed.

## How it works

- Reset profiles by day, week or a fixed bar count and automatically determine price increments. Bar-count periods start at the beginning of the dataset rather than counting backward from its end.
- Search completed-period points of control around current price and identify a Grand POC plus the next three runners-up across periods.

## Outputs and intended use

- Display nearby historical POCs and the cross-period leaders as potential reference levels. The publication is an indicator counterpart to a reusable POC library, not an order-generation strategy.

## Parameters and stated settings

- Reset mode is selectable. Price increment is automatic; users cannot specify row count to derive that increment.

## Failure modes and caveats

- Changing available history can shift bar-count period boundaries. A high-volume historical level does not guarantee support or resistance on a later revisit.

## Missing information and implementation boundary

- The volume-at-price allocation method, increment formula, definition of Grand POC and ranking/tie rules are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described feature can use ordinary chart price/volume history; this is input-class availability, not verified code or market-history coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
- Bar count resets starting from the beginning of the data set (bar index =0) vs bars back from the end of the data set
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- Automates the determination of the increment level rather than the user specifying ticks or price brackets
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
- This script also looks across all the period POCs and identifies the master POC or what I call the Grand POC, and also the next 3 runner up POCs
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_5a8qkpsh_point_of_control_v2](../tv_5a8qkpsh_point_of_control_v2.md)

## Source

https://www.tradingview.com/script/5a8QKPSH-Point-of-Control-V2/

Publication ID: 5a8QKPSH. Source SHA-256: 591c5a94dff1b26acc7b354218cc7870415c1ebfd8d1d1fcab63a82cd205141b. Raw-description SHA-256: 89f721130fa37a7b79ed9ba83e475b1d2fc5666f8602dc268bd13874720fb5cd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
