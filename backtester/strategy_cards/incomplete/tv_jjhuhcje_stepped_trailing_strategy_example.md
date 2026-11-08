---
id: tv_jjhuhcje_stepped_trailing_strategy_example
name: "Stepped trailing strategy example"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Protect progressively more of a favorable move by advancing a stop at three profit milestones, without defining the entry signal."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# Stepped trailing strategy example

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** exit-example. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Protect progressively more of a favorable move by advancing a stop at three profit milestones, without defining the entry signal.

## How it works

- The strategy describes one initial stop and three profit levels. The first two milestones change the protective stop; only the third explicitly closes the position for profit.
- This is a stepped state machine, not a continuously moving trail and not evidence that one-third of the position is sold at each milestone.

## Documented rules and trade lifecycle

- Start with the selected initial stop-loss.
- When the first profit level is reached, move the stop to break-even.
- When the second profit level is reached, move the stop to the first profit level.
- When the third profit level is reached, exit for profit.

## Parameters and stated settings

- One stop and three profit levels are described. Their numerical distances, sizing and long/short defaults are not supplied.

## Failure modes and caveats

- A bar can cross multiple milestones and a stop; assuming a favorable intrabar order can overstate results.
- A stop at the entry price is price break-even, not necessarily net break-even after costs.

## Missing information and implementation boundary

- Recover entry conditions, long/short handling, same-bar precedence, quantity handling and level definitions.
- The saved description does not establish partial profit-taking at the first two levels.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: steps

> There are 1 stop loss and 3 profit levels.
> 
> When first tp is reached we move stop loss to break-even.
> When second tp is reached we move stop loss to first tp.
> When third tp is reached we exit by profit.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This is a stepped trailing exit example for educational purpose.

> When first tp is reached we move stop loss to break-even.

> When second tp is reached we move stop loss to first tp.

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/jjhUHcje-Stepped-trailing-strategy-example/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
