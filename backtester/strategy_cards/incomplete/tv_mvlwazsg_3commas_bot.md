---
id: tv_mvlwazsg_3commas_bot
name: "3Commas Bot"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Provide a modifiable trading and alert-execution shell with predefined risk controls, using a moving-average crossover as the initial demonstration signal."
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
# 3Commas Bot

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** execution-template-with-demo. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Provide a modifiable trading and alert-execution shell with predefined risk controls, using a moving-average crossover as the initial demonstration signal.

## How it works

- An upward MA cross opens the long direction and a downward cross the short direction. MA types and lengths are selectable.
- Stops reference the selected swing-high/low lookback with an ATR adjustment. The entry-to-stop distance defines risk; a chosen risk/reward multiple projects the target.
- An optional ATR trail begins after a selected fraction of the entry-to-target distance is traversed. Fixed targets can be disabled to let the trail determine the exit.
- 3Commas alert compatibility is an integration capability described by the author. This card neither configures bots nor establishes that a live connector is implemented in this repository.

## Documented rules and trade lifecycle

- The documented default risk/reward relationship is 1:1. Direction comes from the MA cross.
- Select the stop/target controls, swing lookback, ATR adjustment and risk/reward factor.
- If trailing is selected, its activation fraction defaults to 0, meaning the described trail starts at entry. An activation fraction of 0.5 means halfway to the projected target.
- If the limit target is disabled, a trade may continue past that target region until its trailing stop is reached.

## Parameters and stated settings

- Author defaults disclosed: 1:1 risk/reward, 0.05% commission, trailing activation fraction 0.
- The BTCUSD 1-hour screenshot uses 50/100 MAs, ATR multiplier 1.3, risk adjustment 1.2, reward/risk 0.6 and trail activation 60%; these are an illustration, not all defaults.

## Failure modes and caveats

- A webhook fill can differ from the broker-emulator fill; reconciliation, slippage and partial fills matter.
- ATR/swing parameters materially change risk distance and turnover. A good crossover illustration is not validation of the shell or a customized signal.

## Missing information and implementation boundary

- The full source, stop-anchor formula, position-size formula, all defaults and order sequencing need recovery.
- The historical commission discussion is an author setting, not a current exchange fee quote.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: rules

> The default settings have a basic 1:1 risk to reward ratio, which sets a limit and a stop equal distance from the entry. The entry is a simple MA cross (up for long, down for short). There a variety of MA's to choose from and the user can define the lengths of the averages. The ratio can be adjusted from the menu along with a volatility based adder (ATR) that helps to distance a stop from support or resistance. These values are calculated off the swing low/high of the user defined lookback period. Risk is calculated from position entry to stop, and projected upwards to the limit as a function of the desired risk to reward ratio. Of note: the default settings include 0.05% commissions. Competitive commissions of the leading cryptocurrency exchanges are .1% round trip (one buy and one sell) for market orders. There is also some slippage to allow time for alerts to be sent and orders to fill giving the back test results a more accurate representation of real time conditions. Its recommended to research the going rates for your exchange and set them to default for the strategy you use or build.

### E2: example

> settings used for the display image: 
> 
> 1hr chart on BTCUSD 
> -ATR stop
> -Risk adjustment 1.2
> -ATR multiplier 1.3
> -RnR 0.6
> -MAs HEMA/SMA
> -MA Length 50/100
> -Order size percent of equity 
> -Trail trigger 60% of target

### E3: trail

> Among the options for possible settings is a trailing stop. This stop will ratchet higher once triggered as a function of the Average True Range (ATR). There is a variable level to choose where the user would like to begin trailing the stop during the trade. The level can be assigned with a decimal between 0 and 1 (eg. 0.5 = 50% of the distance between entry and the target which must be exceeded before the trail triggers to begin). This can allow for some dips to occur during the trade possibly keeping you in the trade for longer, while potentially reducing risk of drawdown over time. The default for this setting is 0 meaning unless adjusted, the trail will trigger on entry if the trailing stop exit method is selected.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> With 3rd party API providers growing in popularity, many are turning to automating their strategies on their favorite assets. With so many options and layers of customization possible, TradingView offers a place no better for young or even experienced coders to build a platform from to meet these needs. 3Commas has offered easy access with straight forward TradingView compatibility. Before long many have their brokers hooked up and are ready to send their alerts (or perhaps they have been trying with mixed success for some time now) only they realize there might just be a little bit more to bu

> Well now there is just that. This strategy is meant for those that have begun to delve into the world of algorithmic trading providing a template that offers risk defined positions complete with stops, limit orders, and even trailing stops should one so choose to employ any of these criteria. It provides a framework that is easily manipulated (with some basic working knowledge of pine coding) to encompass ones own ideas and entry criteria, while also providing an already functioning strategy.

> The default settings have a basic 1:1 risk to reward ratio, which sets a limit and a stop equal distance from the entry. The entry is a simple MA cross (up for long, down for short). There a variety of MA's to choose from and the user can define the lengths of the averages. The ratio can be adjusted from the menu along with a volatility based adder (ATR) that helps to distance a stop from support or resistance. These values are calculated off the swing low/high of the user defined lookback period. Risk is calculated from position entry to stop, and projected upwards to the limit as a function

> Among the options for possible settings is a trailing stop. This stop will ratchet higher once triggered as a function of the Average True Range (ATR). There is a variable level to choose where the user would like to begin trailing the stop during the trade. The level can be assigned with a decimal between 0 and 1 (eg. 0.5 = 50% of the distance between entry and the target which must be exceeded before the trail triggers to begin). This can allow for some dips to occur during the trade possibly keeping you in the trade for longer, while potentially reducing risk of drawdown over time. The defa

> Although a simple strategy is implemented here, the benefits of this script allow a user a starting platform to build their strategies from with built in risk mitigation. This allows the user to sidestep some of the potential difficulties' that can arise while learning Pine and taking on the endeavor of automating their trading strategies. It is meant as an aid, a structure, and an educational piece that can be seen as a "pick-up-and-go" strategy with easy 3Commas compatibility. Additionally, this can help users become more comfortable with strategy alert messages and sending strings in the fo

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/MvlwAzSg-3Commas-Bot/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
