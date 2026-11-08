---

id: tv_profile_kjpmckbt

name: "Bitcoin Power Law Clock [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Bitcoin Power Law Clock transforms a Bitcoin price history and average references into spirals on a cycle-clock display. It aims to contextualize the asset within a proposed power-law/cycle theory. The description’s statement about the current cycle is a publication-era interpretation, not a current market assessment. Its financial purpose is real despite clock-like artwork: price, average and halving references are explicitly plotted. However, no transformation equation or model parameters are provided, so neither the clock time nor the average path can be reproduced from this source alone."

registry_key: null

runner: null

evaluation: null

---

# Bitcoin Power Law Clock [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Bitcoin Power Law Clock transforms a Bitcoin price history and average references into spirals on a cycle-clock display. It aims to contextualize the asset within a proposed power-law/cycle theory. The description’s statement about the current cycle is a publication-era interpretation, not a current market assessment. Its financial purpose is real despite clock-like artwork: price, average and halving references are explicitly plotted. However, no transformation equation or model parameters are provided, so neither the clock time nor the average path can be reproduced from this source alone.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- Core power-law/spiral/cycle mapping is unspecified.

## How it works

- Map Bitcoin prices and an unspecified average/model into spirals and cycle-clock coordinates.
- Annotate key cycle points and optionally halvings/time-price dashboard.

## Outputs and intended use

- Price/average spirals, clock handle, scales and dashboard support cycle-theory visualization.

## Parameters and stated settings

- Requires exact1D INDEX:BTCUSD. Key hour marks12/3/6/9; auto-scale defaults on.
- Curves, colors, sizes and element visibility configurable.

## Failure modes and caveats

- Power-law fit and cycle mapping are model assumptions, not predictive guarantees.
- Publication-era bull-market language can become stale.

## Missing information and implementation boundary

- Power-law coefficients, time origin, spiral transformation, average definition and cycle phase rules absent.

## Data requirements

Required inputs: INDEX:BTCUSD daily history, halving/model calendar parameters.

Repository input-class support: unavailable or unresolved. Requires exact external series/model timing and parameters; coverage and equations are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, required_data

```text
1D INDEX:BTCUSD
```

### E2: parameters

```text
12, 3, 6, and 9
```

### E3: parameters

```text
enabled by default
```

### E4: mechanism, readiness

```text
price and average lines as spirals
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_kjpmckbt_bitcoin_power_law_clock_luxalgo](../tv_kjpmckbt_bitcoin_power_law_clock_luxalgo.md)

## Source

https://www.tradingview.com/script/kjPMckBt-Bitcoin-Power-Law-Clock-LuxAlgo/

Publication ID: kjPMckBt. Source SHA-256: bcbe72a138b4bc8e72204cdf617413f3ef85a33394d093cc98e218e2623e133e. Raw-description SHA-256: 8887fedcc093ba16d0e28afcd7707c382eb93d6fc53ced76cc7e6d3ed173d132.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
