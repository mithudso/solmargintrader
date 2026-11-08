---
id: tv_i9tjotjl_lube
name: "LUBE"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Look for price entering a recently under-visited zone where it may move with less congestion, then trade the near-term trend until congestion returns."
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
# LUBE

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Look for price entering a recently under-visited zone where it may move with less congestion, then trade the near-term trend until congestion returns.

## How it works

- A friction series measures how many recent bars contained the current price level. More past visits imply congestion; fewer visits identify a relatively unfamiliar price zone.
- The entry trigger seeks a new low in normalized friction relative to an older baseline. Direction comes from a fast weighted moving average named fir.
- Exit when friction recovers to the configured threshold, rather than from a separately stated profit-price target.

## Documented rules and trade lifecycle

- For the described BTCUSD 30-minute setup, inspect the preceding 500 bars for visits to the current price level.
- The entry threshold is -10 on a scale whose recent low/high are described as 0/100. The author relates the baseline to 100 bars with a five-bar offset.
- Use the fast weighted average to choose long or short; its exact directional condition is not disclosed.
- Close when friction reaches the selected exit level, described as 50 by default.

## Parameters and stated settings

- Described example/defaults: 500-bar visit window, 100-bar friction baseline, five-bar offset, entry -10, exit 50, BTCUSD 30-minute bars.
- The exact weighted-average length and normalization equations are missing.

## Failure modes and caveats

- A new low in observed congestion can precede a failed breakout or a violent reversal, not just a clean trend.
- The author notes missed large moves and whipsaws, and warns that direct long-to-short alerts can mishandle an old open position.

## Missing information and implementation boundary

- Recover visit-count inclusion rules, normalization/zero-range behavior, fir direction logic, and exact trigger crossings.
- No leverage or drawdown figure from the source is independently validated here.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: intent

> I decided on the strange title "LUBE" because I was measuring how many of the previous 500 bars had the current price level already been in. I wanted to discover when the price was in a new zone or an area that it hadn't spent much time in recently... the LUBE zone.
> 
> Think of the blue line as showing you the current level friction. If the blue line is high, price is quagmired and not moving quickly. Price could trend sideways for a while before breaking out.  A high blue line is a high traffic zone for trading. When the blue line dips low, it's encountering a price zone the asset has not been observed in recently, and this could mean price could break out and move more freely and quickly when it does. We get a trade entry signal if the blue line dips below the bottom white line. The bottom white line is currently set to -10. Think about the lowest the blue line has been recently as 0, and the highest as 100. It is set by default (for BTCUSD 30m chart) to -10 meaning the blue line has to dip a little (-10%) below the lowest it has experienced recently to initiate a trade. This is the LUBE zone. The bottom white line shows that level. Again this is a level lower than the lowest amount of friction experienced in price action for the last 100 bars, but offset by 5 bars showing where that level was at 5 bars ago. We want to dip below that to initiate a trade.

### E2: exit

> The direction to trade in is determined by a very quick moving weighted moving average (variable name is "fir") to see if the recent trend is up or down. To end a trade, an arbitrary number between 0 and 100 is picked telling us when we are experiencing enough friction again to end the trade. I have it preset to 50 (think of it as 50/100 or half way between the white bars. At a 50% friction level it's time to get out of the trade.

### E3: alerts

> Bot traders using alerts: beware the alert conditions. If a trade goes directly from long to short (which happens rarely), without closing a trade first, it might not act properly. If you use bots to trade, for "LONG" please close any old trades first before putting in instructions to open a leveraged long. To go "SHORT" please remember to close any old trade first as well, and things *should* work out just fine.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This is a chart meant for 30m BTCUSD but could be used for many other assets, and there are inputs to play with.

> Think of the blue line as showing you the current level friction. If the blue line is high, price is quagmired and not moving quickly. Price could trend sideways for a while before breaking out. A high blue line is a high traffic zone for trading. When the blue line dips low, it's encountering a price zone the asset has not been observed in recently, and this could mean price could break out and move more freely and quickly when it does. We get a trade entry signal if the blue line dips below the bottom white line. The bottom white line is currently set to -10. Think about the lowest the blue

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/i9tJOtjl-LUBE/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
