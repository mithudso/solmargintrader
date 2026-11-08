---
id: tv_n8bgynwl_template_trailing_strategy_backtester
name: "Template Trailing Strategy (Backtester)"
kind: research-tool
status: documentation-only
classification: strategy-template
summary: "Keep the trading hypothesis separate from order handling, position sizing and event alerts, so the same signal can be tested with different execution mechanics."
registry_key: null
runner: null
evaluation: null
---
# Template Trailing Strategy (Backtester)

Version: 1.0.0 (2026-11-08). Delta: initial source-grounded companion card for a strategy-labelled tool.

**Classification:** strategy-template. Companion research-tool card; excluded from the executable strategy roster.

## Idea and objective

Keep the trading hypothesis separate from order handling, position sizing and event alerts, so the same signal can be tested with different execution mechanics.

## How it works

- A Signal Indicator decides when to enter, exit or cancel. TTS determines how to execute those instructions through its selected order and risk settings.
- External signals follow the tts_convention DealConditions structure, including start/end long/short and optional cancellation conditions. This differs from the simple +1/-1 connector used by another template.
- The framework supports market/limit/stop/stop-limit choices, staged profit targets, break-even movement, trailing, sizing and per-event alert messages. Its built-in Two MA logic is a demonstration.
- A moonbag is residual quantity reserved after configured profit targets; it remains until a stop or close signal. This is execution policy rather than a new entry edge.

## Documented rules and trade lifecycle

- Choose an internal demonstration or a conforming external Signal Indicator as the deal-condition source.
- Configure entry and exit order types, target distances, stops, trailing behavior and quantity/risk policy independently of the signal.
- Use the configured per-event messages for entries/exits/target/stop changes. This card documents the source capability and performs no broker integration.
- The author explicitly warns that tick-based take-profit trailing can change historical behavior after realtime data is discarded; evaluate basic signal logic without that feature first.

## Parameters and stated settings

- The publication describes modules for filters, signal choice, internal Two MA logic, volatility, entry, profit targets, stops, exit, sizing, analytics and alerts.
- No complete numeric defaults or exact signal encoding are disclosed. The author identifies the publication license as CC BY-NC-SA 4.0.

## Failure modes and caveats

- A non-repainting wrapper cannot repair a repainting external signal.
- Tick-dependent trailing and assumed intrabar paths can cause historical and realtime outcomes to disagree.
- The author says dollar-cost averaging or bespoke stop/target logic may require another implementation; do not assume arbitrary strategies fit this shell.

## Missing information and implementation boundary

- Recover the exact convention version/encoding, parameter defaults, order-priority/cancellation behavior and all sizing rules.
- The complete Pine script is absent. A 200-day SMA and 1% stop-entry example explains the interface; it is not a claimed default trading system.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: scope

> The "Template Trailing Strategy (Backtester)" (TTS) is a back-tester orchestration framework. It supercharges the implementation-test-evaluation lifecycle of new trading strategies, by making it possible to plug in your own trading idea.
> While TTS offers a vast number of configuration settings, it primarily allows the trader to:
> 
>  Test and evaluate your own trading logic that is described in terms of entry, exit, and cancellation conditions.
>  Define the entry and exit order types as well as their target prices when the limit, stop, or stop-limit order types are used.
>  Utilize a variety of options regarding the placement of the stop-loss and take-profit target(s) prices and support for well-known techniques like moving to breakeven and trailing.
>  Provide well-known quantity calculation methods to properly handle risk management and easily evaluate trading strategies and compare them.
>  Alert on each trading event or any related change through a robust and fully customizable messaging system.
> 
> All of the above makes TTS a practical toolkit: once you learn it, many repetitive tasks that strategy authors usually re-implement are eliminated. Using TradingView’s built-in backtesting engine makes testing and comparing ideas straightforward.
> By utilizing the TTS one can easily swap "trading logic" by testing, evaluating, and comparing each trading idea and/or individual component of a strategy.
> Finally, TTS, through its per-event alert management (and debugging) system, provides an automated solution that supports live trading with brokers via webhooks.
> 
> NOTE: The "Template Trailing Strategy (Backtester)" does not dictate how you can combine different indicator types. Thus, it should not be confused as a "Trading System", because it gives its user full flexibility on that end (for better or worse).

### E2: signal

> "Signal Indicator" (SI) is an indicator that can output a "signal" that follows a specific convention so that the "Template Trailing Strategy (Backtester)" can "understand" and execute the orders accordingly. The SI realizes the core trading logic signaling to the TTS when to enter, exit, or cancel an order. A SI instructs the TTS "when" to enter or exit, and the TTS determines "how" to enter and exit the position once the Signal Indicator generates a signal.
> A very simple example of a Signal Indicator might be a 200-day Simple Moving Average Signal. When the price of the security closes above the 200-day SMA, a SI would provide TTS with a "long entry signal". Once TTS receives the "long entry signal", the TTS will open a long position and send an alert or automated trade message via webhook to a broker, based on the Entry settings defined in TTS. If the TTS Entry settings specify a "Market" order type, then the open long position will be executed by TTS immediately. But if the TTS Entry settings specify a "Stop" order type with a 1% Stop Distance, then when the price of the security rises by 1% after the "long entry signal" occurs, the TTS will open a long position and the Long Entry alert or webhook to the broker will be sent.

### E3: repaint

> ⚠️ There is an exception though, when the "Enable Trail⚠️💹" checkbox is checked, the Take Profit trailing feature is enabled, and a tick-based approach is used, meaning that after a while, when the TradingView discards all the real-time data, assumptions will be made by the backtesting engine that will cause a form of repainting. To avoid making false assumptions please disable this feature in the early stages and evaluate its usefulness in your strategy later on, after first confirming the success of the logic without this feature. In this case, consider turning on the bar magnifier feature. This way you will get more accurate backtest results when the Take Profit trailing feature is enabled.

### E4: limit

> While this framework can satisfy quite a large number of trading strategies there are cases where it cannot do so. For example, if you have a custom logic for your stop-loss or take-profit placement, or if you want to dollar cost average, then it might be better to start a new strategy script from scratch.

## Sources

https://www.tradingview.com/script/n8bgynWl-Template-Trailing-Strategy-Backtester/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
