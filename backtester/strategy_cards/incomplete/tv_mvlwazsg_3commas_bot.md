---
id: tv_mvlwazsg_3commas_bot
name: "3Commas Bot"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Specification of 3Commas Bot; not a tested trading strategy."
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

Version: 1.0.0 (2026-11-08). Delta: first source-reconciled card.

> **Spec-only — no strategy implementation or performance result is claimed.**
> This card records a signal or research method. An indicator alone is not an order rule.

## Mechanism and equations

This publication documents the source-specific strategy named above. The
author-defined mechanism and any stated inputs are preserved in the passages below.
A similar component name does not make it equivalent to an existing strategy.
No missing equation or trading threshold has been supplied by inference.

## Documented inputs and source details

> With 3rd party API providers growing in popularity, many are turning to automating their strategies on their favorite assets. With so many options and layers of customization possible, TradingView offers a place no better for young or even experienced coders to build a platform from to meet these needs. 3Commas has offered easy access with straight forward TradingView compatibility. Before long many have their brokers hooked up and are ready to send their alerts (or perhaps they have been trying with mixed success for some time now) only they realize there might just be a little bit more to bu

> Well now there is just that. This strategy is meant for those that have begun to delve into the world of algorithmic trading providing a template that offers risk defined positions complete with stops, limit orders, and even trailing stops should one so choose to employ any of these criteria. It provides a framework that is easily manipulated (with some basic working knowledge of pine coding) to encompass ones own ideas and entry criteria, while also providing an already functioning strategy.

> The default settings have a basic 1:1 risk to reward ratio, which sets a limit and a stop equal distance from the entry. The entry is a simple MA cross (up for long, down for short). There a variety of MA's to choose from and the user can define the lengths of the averages. The ratio can be adjusted from the menu along with a volatility based adder (ATR) that helps to distance a stop from support or resistance. These values are calculated off the swing low/high of the user defined lookback period. Risk is calculated from position entry to stop, and projected upwards to the limit as a function

> Among the options for possible settings is a trailing stop. This stop will ratchet higher once triggered as a function of the Average True Range (ATR). There is a variable level to choose where the user would like to begin trailing the stop during the trade. The level can be assigned with a decimal between 0 and 1 (eg. 0.5 = 50% of the distance between entry and the target which must be exceeded before the trail triggers to begin). This can allow for some dips to occur during the trade possibly keeping you in the trade for longer, while potentially reducing risk of drawdown over time. The defa

> Although a simple strategy is implemented here, the benefits of this script allow a user a starting platform to build their strategies from with built in risk mitigation. This allows the user to sidestep some of the potential difficulties' that can arise while learning Pine and taking on the endeavor of automating their trading strategies. It is meant as an aid, a structure, and an educational piece that can be seen as a "pick-up-and-go" strategy with easy 3Commas compatibility. Additionally, this can help users become more comfortable with strategy alert messages and sending strings in the fo

These are bounded passages from the author description, not independently verified
formulas, defaults or performance. No complete repository implementation has been established for this source-specific card. Captured descriptions may include formulas and example code snippets.
Recover every missing numerical definition before implementation.

## Existence check

The coverage ledger checked the existing card names, registry, indicator functions and
Compound scorecard before this card was created. Related components do not establish
equivalence to this complete specification. Exact matches reuse their existing entry
in the ledger instead of receiving another card.

Related existing/specification cards: `tv_method_atr_trailing`, `tv_method_risk_based_sizing`, `tv_method_support_resistance`, `tv_method_trailing_stop`.

## Data and availability

Required inputs: ohlcv.
The repository supports OHLCV history. Verify symbol, cadence, timezone and complete bars for the chosen experiment; this is not a claim that every source market is cached.

## Implementation and validation

No runner or registry key is assigned. Before implementation, freeze the numerical
formula, seeds, missing-value policy, warm-up and parameter domains. Where the source
does not disclose an algorithm or default, recover it rather than guessing. Specify
entry, exit, stop, holding horizon, exposure and costs separately from the indicator.
Record which choices come from the publication and which define a new experiment.

Compute with closed bars and trailing data only. Confirm pivots and higher-timeframe
values before use; never backdate a signal to a pivot that needed later bars. Test
prefix invariance, flat/zero inputs, unavailable data and one-bar-delayed execution.
Evaluate chronologically out of sample, deduct transaction and financing costs and compare with
buy-and-hold and simpler component rules. Record all searched configurations.

## Failure modes and caveats

An author description is not source code or independent validation. Visual styling,
retrospective drawing anchors, repainting pivots and fitted full-history models can
produce unavailable historical signals. A rule can be numerically correct and lose
after costs. Venue, session, data and asset differences limit transfer to SOL.

## Measured results

Not measured in this repository. Publication examples, advertised accuracy and
screenshots are not repository backtest results.

## Likelihood of success: low

Basis: a-priori. The mechanism has no confirming out-of-sample result here. This rating
does not promote the source author's claims into evidence of profitability.

## Sources

- https://www.tradingview.com/script/MvlwAzSg-3Commas-Bot/

The coverage ledger records canonical URLs, source-file hashes, decoded-description
hashes and the excerpt offsets used for this card. Raw dumps remain outside Git.
