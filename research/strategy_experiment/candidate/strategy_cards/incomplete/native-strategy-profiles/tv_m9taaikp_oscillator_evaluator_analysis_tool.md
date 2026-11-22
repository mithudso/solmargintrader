---
id: tv_m9taaikp_oscillator_evaluator_analysis_tool
name: "Oscillator Evaluator (Analysis tool)"
kind: research-tool
status: documentation-only
classification: evaluation-tool
summary: "Compare how different oscillators behave under several common signal interpretations, holding the evaluation framework conceptually constant."
registry_key: null
runner: null
evaluation: null
---
# Oscillator Evaluator (Analysis tool)

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** evaluation-tool. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Compare how different oscillators behave under several common signal interpretations, holding the evaluation framework conceptually constant.

## How it works

- One selected oscillator is compared with two alternatives. Six test modes probe trend correlation, crossover behavior, zero crossings, extremes, short-horizon mean reversion, and trend profit-taking.
- The tool asks what information an oscillator provides; it is explicitly not presented as a complete strategy. Its modes are alternative experiments, not six confirmations to combine into one entry.

## Documented rules and trade lifecycle

- Mode 1 uses moving-average increase/decrease; mode 2 uses a two-moving-average crossover.
- Mode 3 enters long on a zero crossover and short on a zero crossunder.
- Mode 4 buys/sells at oscillator extremes. Modes 5 and 6 evaluate mean-reversion filtering/small changes and profit-taking within trends, respectively.
- The description does not give the exact thresholds, lengths, position handling or exit conditions for most modes.

## Parameters and stated settings

- Oscillator selection, two comparison oscillators and one of six evaluation modes are described. Complete defaults are not provided.

## Failure modes and caveats

- Choosing the best oscillator and mode on the same history is a selection experiment, not independent evidence of predictive value.
- Modes can favor different oscillator scales; direct comparison needs consistent signal normalization, execution and costs.

## Missing information and implementation boundary

- Recover each mode's exact equations, settings, exits and performance calculation before comparing results.
- No source code or independently reproduced test results are available in the capture.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: compare

> The oscillator evaluator is a tool that will help you analyse and compare the oscillator of your choice to another 2 oscillators.

### E2: modes

> First there is a moving average increase or decrease strategy, that will give you a good idea of the correlation of the oscillator with the price.
> 
> The second is a commom 2 MA crossover strategy, that will give you and idea of the validaty of that oscillator as a strategy or as a trend filter.
> 
> The third strategy is a cross over 0 signal, that will go long on a crossover of 0 and short on a crossunder 0. This helps you see how good is the oscillator at evaluating suport and resistance areas and give you an idea of its balance.
> 
> The forth strategy is a Buy/Sell on extremes of the oscillator and will let you know how good is your strategy at spotting good places to buy and sell.
> 
> The fith strategy is to evaluate how goood the oscillator is as a mean reversion filter or how good it is at spotting small price changes.
> 
> The sixth strategy is similar to the last but is focused on how good is the oscillator spotting good places to take profits on trending strategies.

### E3: scope

> This script is not intended to be used as a full strategy but as a tool.

## Sources

https://www.tradingview.com/script/M9taaIkp-Oscillator-Evaluator-Analysis-tool/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
