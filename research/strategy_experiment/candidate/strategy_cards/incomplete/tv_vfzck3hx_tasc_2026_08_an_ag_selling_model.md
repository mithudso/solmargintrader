---
id: tv_vfzck3hx_tasc_2026_08_an_ag_selling_model
name: "TASC 2026.08 An Ag Selling Model"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Help an agricultural producer obtain an above-average selling price by staging short futures sales into seasonal strength, then covering at harvest."
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
# TASC 2026.08 An Ag Selling Model

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Help an agricultural producer obtain an above-average selling price by staging short futures sales into seasonal strength, then covering at harvest.

## How it works

- The hypothesis is crop seasonality: a single annual crop can produce weaker harvest prices and stronger growing-season prices.
- A selling level combines a seasonal simple moving average with an ATR volatility premium. Conceptually the described level is SMA(source, length) + factor × ATR.
- Sales are spaced to avoid placing every order into the same rally. This is a crop-specific seasonal selling model, not a generic cryptocurrency short signal.

## Documented rules and trade lifecycle

- Sell short when the specified selling level is reached, in one-contract increments up to three sales per year.
- Wait the chosen number of days between sales.
- Avoid the selected post-harvest downtime, then allow sales during the eligible seasonal period.
- Cover the shorts at harvest. The stated objective is to beat the average selling price, not a demonstrated portfolio return.

## Parameters and stated settings

- MA length: recommended range 20–60 days, with 40 offered as a starting point; these recommendations are not asserted complete script defaults.
- ATR length/factor, harvest month, post-harvest delay and days between trades are inputs. The author suggests ATR factors 2.5–3.5 and a two-month post-harvest delay for tuning.
- Corn illustration: capital 15,000,000 cents ($150,000), commission 300 cents ($3) per order, one-tick slippage, and up to three one-contract sales.

## Failure modes and caveats

- A failed crop, supply shock or altered seasonal pattern can keep prices high against a short hedge.
- A cents-versus-dollars or contract-multiplier error overwhelms any purported edge. Futures rolls and calendar alignment also affect the experiment.

## Missing information and implementation boundary

- Recover the exact ATR definition, harvest scheduling, annual reset, trigger/fill semantics and contract selection.
- Crop calendars and corn contract economics are not supplied by generic SOL OHLCV. No measured result is reproduced here.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: intent

> The core idea is that if there is only one crop per year, crop prices will be lowest around harvest and highest around peak growing season. Based on this timing, the strategy spaces out its sell orders up to three times throughout the year, and covers its position at harvest.
> 
> The goal of this strategy is simply to beat the average price. Since selling at harvest should typically provide a lower-than-average price exit, success for this strategy means having the average of its entries above the average price.

### E2: rules

> █ THE RULES
> 
> 
> Sell short at the selling level. 
> Delay these sells to ensure two sells are not in the same rally.
> Avoid selling immediately after harvest, as a long period of low prices typically follows.
> Exit positions (cover shorts) at harvest.

### E3: props

> Initial Capital: 15,000,000¢ == $150,000; see note above.
> Position Sizing: This strategy sells in one-contract increments up to three times per year.
> Commissions: Commission value is set to 300¢ ($3) per order, which is a generous estimate.
> Slippage: Slippage is set to one tick to simulate reasonable execution conditions.

### E4: inputs

> MA length: Moving Average length (Simple Moving Average). A 20 to 60 day range is recommended; with 40 as a starting point.
> ATR length: Average True Range length.
> ATR factor: Factor by which to multiply ATR when calculating selling level. 2.5 to 3.5 is generally recommended but higher has been seen for more volatile grains.
> Month of Harvest: Set the month of harvest for the crop being traded, which changes depending on the seasonality of the commodity.
> Delay in months after harvest: Set this to the typical downtime after harvest where prices are typically lowest. This can vary per instrument but 2 months is the suggested point for tuning.
> Days between trades: Days to wait between sales.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This strategy implements the "Ag Selling Model" as presented by Perry J. Kaufman in the August 2026 edition of the TASC Traders' Tips "Identifying The Best Price Levels For Selling Commodity Futures". The article describes a long-hold selling strategy for agricultural commodity futures based around the seasonal harvest timing of crops, mainly US grains traded on the CBOT and KCBOT, both which have been acquired by CME.

> The core idea is that if there is only one crop per year, crop prices will be lowest around harvest and highest around peak growing season. Based on this timing, the strategy spaces out its sell orders up to three times throughout the year, and covers its position at harvest.

> With these two figures, the volatility is added to the average based on a multiplication factor.

> ATR factor: Factor by which to multiply ATR when calculating selling level. 2.5 to 3.5 is generally recommended but higher has been seen for more volatile grains.

> Avoid selling immediately after harvest, as a long period of low prices typically follows.

> IMPORTANT NOTE: The strategy parameters have been adjusted specifically for Corn Futures (ZC1!). This ticker operates in Cents (USX) rather than Dollars (USD); all the strategy values have been translated to account for this. To apply this strategy to other markets it is important to properly adjust the strategy parameters to simulate realistic conditions.

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
