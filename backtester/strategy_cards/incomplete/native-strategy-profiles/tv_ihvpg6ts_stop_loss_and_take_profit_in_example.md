---
id: tv_ihvpg6ts_stop_loss_and_take_profit_in_example
name: "Stop loss and Take Profit in $$ example"
kind: research-tool
status: documentation-only
classification: exit-example
summary: "Illustrate expressing stop-loss and take-profit amounts in the traded symbol's currency, rather than establish a trading signal."
registry_key: null
runner: null
evaluation: null
---
# Stop loss and Take Profit in $$ example

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** exit-example. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Illustrate expressing stop-loss and take-profit amounts in the traded symbol's currency, rather than establish a trading signal.

## How it works

- The entire saved description is a one-sentence declaration of a currency-denominated exit example. It does not show the conversion from money to price distance or specify whether the amount applies to a position or a unit.

## Documented rules and trade lifecycle

- Documented behavior: an educational stop-loss/take-profit example in the symbol currency.
- Entry conditions, stop and target amounts, order types, quantities and long/short behavior are not disclosed.

## Parameters and stated settings

- No parameter values or defaults are present in the saved description.

## Failure modes and caveats

- A cash stop amount cannot be converted to price distance without position quantity and instrument point/contract value.
- Treating a total-position amount as a per-unit amount would change the intended risk. These are implementation concerns, not recovered source rules.

## Missing information and implementation boundary

- The saved script object contains no source code. The available sentence is insufficient to reconstruct an executable method.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> This is a simple exit example in $$ (symbol's currency) for educational purpose.

## Sources

https://www.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
