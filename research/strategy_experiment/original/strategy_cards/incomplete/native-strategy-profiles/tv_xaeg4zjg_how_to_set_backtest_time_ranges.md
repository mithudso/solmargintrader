---
id: tv_xaeg4zjg_how_to_set_backtest_time_ranges
name: "How To Set Backtest Time Ranges"
kind: research-tool
status: documentation-only
classification: backtest-utility
summary: "Restrict an existing strategy's experiment to chosen time/date windows, including entry and exit eligibility, without supplying its trading hypothesis."
registry_key: null
runner: null
evaluation: null
---
# How To Set Backtest Time Ranges

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** backtest-utility. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Restrict an existing strategy's experiment to chosen time/date windows, including entry and exit eligibility, without supplying its trading hypothesis.

## How it works

- A configurable window controls which periods the host strategy evaluates or trades. Additional examples toggle date windows and plot visibility.
- This is an experiment-boundary tool. The description explicitly says it is not intended as an actual trading strategy.

## Documented rules and trade lifecycle

- Apply the selected time range to entries and exits in the host strategy.
- The description mentions weekend day codes, date-range examples and plot-visibility controls, but does not give the complete inclusion logic.

## Parameters and stated settings

- Time window, date range and plot-visibility controls are described without complete defaults.

## Failure modes and caveats

- Selecting a favorable historical window after inspecting returns creates selection bias.
- Simply disabling exits outside a window could leave a position open; forced-close and pending-order policies must be specified separately.

## Missing information and implementation boundary

- Recover boundary inclusivity, timezone/day rules, cross-midnight sessions, open-position treatment and order cancellation.
- No entry signal, sizing rule, stop or target is specified.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> Example how to set the time range window to be backtested for both entries and exits. Additional examples are also included showing how to set the date range and toggle plot visibility. 
> 
> By incorporating this code with your own strategy's logic, it will allow you to backtest various time windows. 
> 
> Much gratitude to @LucF and @a.tesla2018 for help with including ':1234567' for time ranges on weekends. Thank you both!
>  
> 
> NOTICE: This is an example script and not meant to be used as an actual strategy. By using this script or any portion thereof, you acknowledge that you have read and understood that this is for research purposes only and I am not responsible for any financial losses you may incur by using this script!

## Sources

https://www.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
