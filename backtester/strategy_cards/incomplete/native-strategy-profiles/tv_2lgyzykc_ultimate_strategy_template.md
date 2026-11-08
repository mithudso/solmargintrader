---
id: tv_2lgyzykc_ultimate_strategy_template
name: "Ultimate Strategy Template"
kind: research-tool
status: documentation-only
classification: strategy-template
summary: "Separate a trading signal from its execution and risk-management shell, so different indicators can be evaluated through the same strategy template."
registry_key: null
runner: null
evaluation: null
---
# Ultimate Strategy Template

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** strategy-template. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Separate a trading signal from its execution and risk-management shell, so different indicators can be evaluated through the same strategy template.

## How it works

- An external indicator emits exactly +1 for a bullish event, -1 for a bearish event, and 0 otherwise. The template consumes its plotted connector series.
- The included illustration uses a moving-average crossover: a fast average crossing above a slow average emits a buy event, and a cross below emits a sell event. This illustration is replaceable; it is not a universal entry rule of the framework.
- Session/date filters and selectable stop/target methods wrap the supplied signal. They let the experiment change execution and risk rules while holding the indicator constant.

## Documented rules and trade lifecycle

- Select the external connector as the template data source. The documented signal contract requires exact +1/-1 values.
- Choose the permitted trading sessions and dates, direction/closure settings, and whether positions close at session end.
- Select stops from none, percentage, percentage trailing, or ATR; select targets from none, percentage, or ATR. ATR risk/reward settings define a separate execution configuration.
- Optional controls limit streaks, losing days, drawdown, intraday loss, and trades per day/week. The description does not enumerate the enabled defaults.

## Parameters and stated settings

- Example connector only: fast/slow lengths 10/100 and SMA defaults; RMA and EMA are alternatives.
- Framework choices include session/date windows, risk limits, stop/target modes, and alert settings. Numeric defaults for these controls are not disclosed.

## Failure modes and caveats

- Changing the external indicator changes the hypothesis being tested; performance cannot be attributed to the shell alone.
- A repainting connector or inconsistent alert/fill timing can make a clean-looking wrapper reproduce unavailable historical signals.

## Missing information and implementation boundary

- The complete template source is absent. The excerpt supplies a connector example, not the full order state machine.
- Close/reversal semantics, exact risk-limit enforcement, fills and all numerical defaults need recovery before a parity implementation.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: connect

> The Strategy Template expects the value to be exactly 1 for the bullish signal, and -1 for the bearish signal

### E2: example

> type_ma1 = input(title="MA1 type", defval="SMA", options=["RMA", "SMA", "EMA"])
> length_ma1 = input(10, title = "  [ALL but VWAP] MA1 length", type=input.integer)
> type_ma2 = input(title="MA2 type", defval="SMA", options=["RMA", "SMA", "EMA"])
> length_ma2 = input(100, title = "  [ALL but VWAP] MA2 length", type=input.integer)

### E3: risk

> - Set the maximum losing streak length with an input
> - Set the maximum winning streak length with an input
> - Set the maximum consecutive days with a loss
> - Set the maximum drawdown (in % of strategy equity)
> - Set the maximum intraday loss in percentage
> - Limit the number of trades per day
> - Limit the number of trades per week
> - Stop-loss: None or Percentage or Trailing Stop Percentage or ATR
> - Take-Profit: None or Percentage or ATR
> - Risk-Reward based on ATR multiple for the Stop-Loss and Take-Profit

## Sources

https://www.tradingview.com/script/2lGyzYkC-Ultimate-Strategy-Template/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
