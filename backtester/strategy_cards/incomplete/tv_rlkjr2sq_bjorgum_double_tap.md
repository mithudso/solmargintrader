---
id: tv_rlkjr2sq_bjorgum_double_tap
name: "Bjorgum Double Tap"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Recognize a failed retest of a high or low, then trade the neckline breakout as a double-top or double-bottom reversal/breakout pattern."
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
# Bjorgum Double Tap

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Recognize a failed retest of a high or low, then trade the neckline breakout as a double-top or double-bottom reversal/breakout pattern.

## How it works

- An alternating swing-high/swing-low zig-zag list is updated as extrema change. Pattern recognition searches that sequence for an M or W shape with a failed second test and a break of the intervening neckline.
- The default target projects one pattern height beyond the neckline. The stop lies beyond the invalidation extreme: above a double top or below a double bottom.
- An optional ATR trail starts at the projected target instead of executing the fixed take-profit. In that mode, the target is an activation threshold and exits occur by stops.

## Documented rules and trade lifecycle

- Confirm the double formation and neckline breakout before entry; the described default waits for bar close.
- Place the invalidation stop and a pattern-height target. Both offsets can be adjusted as percentages of pattern height.
- If the ATR trail is enabled, exclude the limit target and start trailing when the projection is reached. Trail from a chosen lookback extreme with an ATR offset.
- Track whether a pivot has already been traded to avoid duplicate detection. Per-tick recalculation is an alternate realtime mode and should not be treated as equivalent historical behavior.

## Parameters and stated settings

- Default target projection is 100% of pattern height. Stop/target percentages, swing lookback, ATR lookback/multiplier and strategy/indicator mode are configurable.
- Sizing and commission come from strategy properties; numeric size/fee defaults are not established by the description.

## Failure modes and caveats

- Zig-zag extrema and pivots can be revised while forming; never backdate a signal to the eventual turning-point bar.
- A same-bar neckline break, target trigger and stop interaction needs conservative execution sequencing.
- The author warns that historical equity growth/shrinkage affects alert quantities; replay-derived account size can produce an unexpected order size.

## Missing information and implementation boundary

- Recover pivot confirmation, double-test tolerance, spacing requirements, entry timing, duplicate keys and ATR trail recurrence.
- The author intentionally omits backtest results. No independent profit claim is made here.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: pattern

> Doubles are technical formations that are both reversal patterns and breakout patterns. These formations typically have a distinctive “M” or a “W” shape with price action breaking beyond the neckline formed by the center of the pattern. They can be recognized when a ​pivot fails to break when tested for a second time and the retracement that follows breaks beyond the key level opposite. This can trap entrants that were playing in the direction of the prior trend. Entries are made on the breakout with a target projected beyond the neckline equal to the height of the pattern.

### E2: recognition

> Patterns are recognized through the use of ​zig-zag; a method of filtering price action by connecting swing highs and lows in an alternating fashion to establish trend, ​support and resistance, or derive shapes from price action. The script looks for the highest or lowest point in a given number of bars and updates a list with the values as they form. If the levels are exceeded, the values are updated. If the direction changes and a new significant point is made, a new point is added to the list and the process starts again. Meanwhile, we scan the list of values looking for the distinctive shape to form as previously described.

### E3: exits

> By default, the strategy will place a stop loss at the invalidation point of the pattern. This point is beyond the pattern high in the case of Double Tops, or beneath the pattern low in the case of Double Bottoms. The target or take profit point is an equal-legs measurement, or 100% of the pattern height in the direction of the pattern bias. Both the stop and the limit level can be adjusted from the user menu as a percentage of the pattern height. 
> 
> Trailing Stops
> Optional from the menu is the implementation of an ATR based trailing stop. The trailing stop is designed to begin when the target projection is reached. From there, the script looks back a user-defined number of bars for the highest or lowest point +/- the ATR value. For tighter stops the user can look back a lesser number of bars, or decrease the ATR multiple. When using either Alertatron or Trading Connector, each change in the trail value will trigger an alert to update the stop order on the exchange to reflect the new trail price. This reduces latency and slippage that can occur when relying on alerts only as real exchange orders fill faster and remain in place in the event of a disruption in communication between your strategy and the exchange, which ensures a higher level of safety. 
> 
> 👉  It is important to note that in the case the trailing stop is enabled, limit orders are excluded from the exit criteria. Rather, the point in time that the limit value is exceeded is the point that the trail begins. As such, this method will exit by stop loss only.

### E4: history

> It is important to understand that the calculations on the account size take place from the beginning of the price history of the strategy. This means that if historical results have inflated or depleted the account size from the beginning of trade history until now, the values sent in alerts will reflect the calculated size based on the inputs in the "Properties" tab. To start fresh, the user must set the date in the "Inputs" tab to the current date as to remove trades from the trade history. Failure to follow this instruction can result in an unexpected order size being sent in the alert.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> Double Tap is a pattern recognition script aimed at detecting Double Tops and Double Bottoms. Double Tap can be applied to the broker emulator to observe historical results, run as a trading bot for live trade alerts in real time with entry signals, take profit, and stop orders, or to simply detect patterns.

> Repainting is simply the difference in behaviour of a strategy in real time vs the results calculated on the historical dataset. The strategy, by default, will wait for confirmed signals and is thus designed to not repaint. Waiting for bar close for entires aligns results in the real time data feed to those calculated on historical bars, which contain far less data. By doing this we align the behaviour of the strategy on the 2 data types, which brings significance to the calculated results. To override this behaviour and introduce repainting one can select "Recalculate on every tick" from the

> 👉 It is possible to use this script as an indicator as opposed to a full strategy by disabling "Use Strategy" in the "Inputs" tab. Basic alerts for detection will be sent when patterns are detected as opposed to complex order syntax. For alerts mid-bar enable "Recalculate on every tick", and for confirmed signals ensure it is disabled.

> By default, the strategy will place a stop loss at the invalidation point of the pattern. This point is beyond the pattern high in the case of Double Tops, or beneath the pattern low in the case of Double Bottoms. The target or take profit point is an equal-legs measurement, or 100% of the pattern height in the direction of the pattern bias. Both the stop and the limit level can be adjusted from the user menu as a percentage of the pattern height.

> 👉 It is important to note that in the case the trailing stop is enabled, limit orders are excluded from the exit criteria. Rather, the point in time that the limit value is exceeded is the point that the trail begins. As such, this method will exit by stop loss only.

> The following are five options for delivering alerts from Double Tap to live trade execution via third party ​API solutions or chat bots to share your trades on social media. These destinations can be selected from the input menu and alert syntax will automatically configure in alerts appropriately to manage trades.

> Trading Connector is a third party fully autonomous Chrome extension designed to catch alert webhooks from TradingView and interface with MT4/MT5 to execute live trades from your machine. Alerts to Trading Connector are simple; just select the destination from the input drop down menu, set your ticker in the "TC Ticker" box in the "Alert Strings" section and enter your URL in the alert window when configuring your alert.

> Historical back testing is the most common method to test a strategy due in part to the general ease of gathering quick results. The underlying theory is that any strategy that worked well in the past is likely to work well in the future, and conversely, any strategy that performed poorly in the past is likely to perform poorly in the future. It is easy to poke holes in this theory, however, as for one to accept it as gospel, one would have to assume that future results will match what has come to pass. The randomness of markets may see to it otherwise, so it is important to scrutinize results

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/rLkjr2sQ-Bjorgum-Double-Tap/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
