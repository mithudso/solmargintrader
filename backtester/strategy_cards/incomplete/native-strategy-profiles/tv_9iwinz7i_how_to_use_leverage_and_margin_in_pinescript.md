---
id: tv_9iwinz7i_how_to_use_leverage_and_margin_in_pinescript
name: "How to use Leverage and Margin in PineScript"
kind: research-tool
status: documentation-only
classification: leverage-example
summary: "Explain how the publication configures notional exposure and simulated margin constraints; it supplies no forecasting or entry edge."
registry_key: null
runner: null
evaluation: null
---
# How to use Leverage and Margin in PineScript

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** leverage-example. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Explain how the publication configures notional exposure and simulated margin constraints; it supplies no forecasting or entry edge.

## How it works

- The example assumes order sizing as a percentage of strategy equity. It multiplies the desired capital allocation by a leverage factor to express a larger notional order.
- It separately discusses broker-emulator margin requirements and forced partial/full closures. Exposure size and maintenance capacity are different controls.
- These are historical author examples. They must not be copied as current venue requirements or used as a live liquidation formula.

## Documented rules and trade lifecycle

- For the stated 100%-equity allocation, the source uses 100 for unlevered quantity and 3000 for a 30-times notional example.
- For a stated 10%-equity allocation at 15-times leverage, the source example gives quantity value 150.
- The source also prints margin_long = 1./30*50 and the same expression for margin_short. Its broker-specific explanation is not independently validated here.
- Entry/exit decisions must come from a separate strategy. A margin call is an unwanted failure of its risk design, not an entry/exit rule.

## Parameters and stated settings

- Historical examples: leverage 30 or 15; allocations 100% or 10%; author margin example uses 50.
- These examples are not asserted defaults, current broker policy, or recommended leverage.

## Failure modes and caveats

- A percentage-of-equity allocation multiplied by leverage can create much greater notional risk than the allocation name suggests.
- A Pine broker emulator and a real venue can have different margin, financing, gap and liquidation behavior.

## Missing information and implementation boundary

- No trading signal, stop, target, holding horizon or complete script is supplied.
- Recover and validate the applicable Pine version and actual venue margin semantics before implementing any numerical example.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> Having said that - this is purely educational stuff.

### E2: qty

> default_qty_value = 100    // which stands for 100%[/pine]
> 
> Now, if you want to trade with 30:1 leverage, you need to multipy the quantity by 30x, so you'd get 30 x 100 = 3000:
> [pine]default_qty_value = 3000    // which stands for 3000%[/pine]
> 
> And you can play around with this value as you wish, so if you want to enter each trade with 10% equity on 15:1 leverage you'd get default_qty_value = 150.
> That's easy. Of course you can modify this quantity value not only in the script, but also afterwards in Script Settings popup, "Properties" tab.

### E3: margin

> margin_long = 1./30*50, margin_short = 1./30*50[/pine]
> 
> Whereas "30" is a leverage scale as in 30:1, and "50" stands for 50% of Margin required by your broker. Personally the Required Margin number I've met most often is 50%, so I'm using value 50 here, but there are literally 1000+ brokers in this world and this is individual decision by each of them, so you'd better ask yourself.

## Sources

https://www.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
