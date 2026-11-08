---
id: tv_ghocsiv7_gap_filling_strategy
name: "Gap Filling Strategy "
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Trade the return to a significant opening gap's prior reference level, while offering an inverted mode that instead trades gap continuation."
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
# Gap Filling Strategy 

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Trade the return to a significant opening gap's prior reference level, while offering an inverted mode that instead trades gap continuation.

## How it works

- A significant upward opening gap opens beyond the prior high; a significant downward gap opens below the prior low. The description requires that the "bar following the gap" does not fill it; whether this is the opening/gap bar or a later bar is not disclosed.
- With invert=false, an up gap is treated as exhaustion and sold, while a down gap is bought. With invert=true, the directions reverse to follow a presumed breakout/runaway gap.
- The gap-fill level is a profit destination in the fading mode but an adverse exit in continuation mode. These are different hypotheses, not merely cosmetic parameter choices.

## Documented rules and trade lifecycle

- Apply the source's non-fill confirmation before entering. Without the source code, the phrase "bar following the gap" does not establish whether confirmation uses the gap-opening bar or a subsequent bar.
- Fade up/down gaps with short/long positions in normal mode; trade long/short respectively in inverted mode.
- Exit at the gap-fill reference level. Also choose a closure policy: next session, next gap, or an opposite position.
- The exact reference-level calculation and bar/order timing need source-code recovery; prior-close language alone is not enough to infer every boundary.

## Parameters and stated settings

- Documented controls: invert and close-when mode.
- Author examples use 15-minute technology-stock bars with no spread or commission. No net-of-cost result is established.

## Failure modes and caveats

- A high gap-fill win rate can coexist with negative P&L if the non-filling tail losses are larger.
- Fading a genuine information-driven breakaway gap can lose persistently. Gap continuation has a different failure mode: rapid reversion to the reference level.
- A 24/7 crypto market needs an explicitly defined session boundary; equity-session behavior does not automatically transfer.

## Missing information and implementation boundary

- Recover exact gap detection, fill equality rules, target anchor, incomplete-session handling and exit priority.
- Test the confirmation bar causally and include spread, commission, gap-through stops and slippage.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: significance

> Significant up gaps will have an opening price greater than the previous high, while significant down gap will have an opening price lower than the previous low with both high volume accompanying them.

### E2: logic

> In this strategy, the significance of a gap is determined by the position of the opening price relative to the previous high/low and make sure the bar following the gap don't fill it.
> 
> When the setting invert is set to false the strategy interpret the detected gaps as being exhaustion gaps, therefore when an up gap occur a short position is opened, when a down gap occur a long position is opened. When invert is set to true gaps are considered to be runaway or break away gaps, therefore the contrary positions are opened. Positions are exited when the gap has been filled, which in the chart is show'n when the price cross the red level who act as either a take profit (invert = false) or as a stop loss (invert = true).
> 
> There are various closing conditions available that the user can select from the "close when" setting. 
> 
> 
>  New Session : This option close all previous positions when the market is in a new session.
>  New Gap : This option close all previous position when a new gap has been detected.
>  Reverse Position : This option close all previous position when a contrary position to the current one is opened. This option would reduce the number of trades.

### E3: sample

> The analysis will be tested in different tech stocks with a main TF of 15 minutes with no spread and commissions applied. Default settings will be used. We'll be making our first analysis using AMD, who has recently formed a full reverse HS pattern, where the neckline has been crossed by the price. (by the way i have a bad feeling about it, hey ! feeling filling ! Lame jokes!)

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> Gaps are market prices structures that appear frequently in the stock market, and can be detected when the opening price is different from the previous closing price, this is why gaps are also called "opening price jumps". While gaps can occur frequently, some of them are more significant than others, and can be observed when looking at a long term chart.

> The following strategy is based on the exploitation of significant gaps occurring during a new session, and posses various options that can return a wide variety of results.

> When the setting invert is set to false the strategy interpret the detected gaps as being exhaustion gaps, therefore when an up gap occur a short position is opened, when a down gap occur a long position is opened. When invert is set to true gaps are considered to be runaway or break away gaps, therefore the contrary positions are opened. Positions are exited when the gap has been filled, which in the chart is show'n when the price cross the red level who act as either a take profit (invert = false) or as a stop loss (invert = true).

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
