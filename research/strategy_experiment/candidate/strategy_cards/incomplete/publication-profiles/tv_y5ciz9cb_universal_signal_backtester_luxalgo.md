---

id: tv_profile_y5ciz9cb

name: "Universal Signal Backtester [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: reporting-tool

summary: "Universal Signal Backtester simulates trades from selectable built-in or external signals and summarizes their historical outcomes on-chart. It aims to let users compare entry logic, exits and cost assumptions within a common display. Dynamic target suggestions are optimization context, not established out-of-sample recommendations, and its cost presets are historical software assumptions rather than verified broker fees."

registry_key: null

runner: null

evaluation: null

---

# Universal Signal Backtester [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** reporting-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Universal Signal Backtester simulates trades from selectable built-in or external signals and summarizes their historical outcomes on-chart. It aims to let users compare entry logic, exits and cost assumptions within a common display. Dynamic target suggestions are optimization context, not established out-of-sample recommendations, and its cost presets are historical software assumptions rather than verified broker fees.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Trade fill ordering, partial-size allocation and cost-unit conventions are undisclosed.

- Trade fill ordering, partial-size allocation and cost-unit conventions are undisclosed.

## How it works

- Choose MA crossover, external-source crossover or discrete trigger interpretation, optionally filter direction and low-volatility signals, then simulate target/stop outcomes.
- Track trade metrics, an equity sparkline, hourly performance and weekday/monthly profitability heatmaps.
- Apply selected spread/commission presets or manual values and rank TP choices by a selected metric.

## Outputs and intended use

- Inspect entry signposts, active exit lines/hit marks, dashboard metrics and session patterns to research the chosen signal.

## Parameters and stated settings

- Supports up to three TP and three SL levels; built-in examples are EMA 9/21, EMA 12/26 and SMA 50/200.
- Target distances can use ATR, ticks or points; trigger semantics, direction, cost profile, suggested-TP metric and visuals are configurable.

## Failure modes and caveats

- Analytical: selecting the best TP on the same sample risks overfitting; simultaneous stop/target hits, external repainting and assumed costs can distort results.

## Missing information and implementation boundary

- Fill ordering, partial-size allocation, commission units, Sharpe convention, choppiness formula and lookahead safeguards are not disclosed.

## Data requirements

Required inputs: ohlcv, caller-selected external signals for external modes, user cost/exit assumptions.

Repository input-class support: unavailable or unresolved. Built-in MA mode is OHLCV-derived, but the full configurable backtester requires signal and execution assumptions not supplied by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
up to three Take Profit (TP) and three Stop Loss (SL) levels.
```

### E2: parameters, readiness

```text
9/21 EMA, 12/26 EMA, or the Golden/Death Cross (50/200 SMA)
```

### E3: parameters, readiness

```text
Value Changes, Crosses 0, or Not NA
```

## Source

https://www.tradingview.com/script/Y5CIZ9CB-Universal-Signal-Backtester-LuxAlgo/

Publication ID: Y5CIZ9CB. Source SHA-256: f83cb23ccece827f9c9150b7445fcd2e46d1883f021f9b6c53bec657d8179e2c. Raw-description SHA-256: 4e68ba7a1d01fbc19245e9903adc333cce29e869992692badc1f5c6556484059.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
