---
id: tv_nvecqiqx_tasc_2026_03_one_percent_a_week
name: "TASC 2026.03 One Percent A Week"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Seek a small weekly snapback in TQQQ after a dip from Monday's open, with limited trade frequency and a Friday deadline."
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
# TASC 2026.03 One Percent A Week

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Seek a small weekly snapback in TQQQ after a dip from Monday's open, with limited trade frequency and a Friday deadline.

## How it works

- This is a long-only weekly mean-reversion hypothesis tailored by the author to a leveraged equity ETF, not a generic crypto trend rule.
- A resting buy limit below the weekly opening reference attempts to enter on a pullback. A target is delayed until the next day, and the holding window ends before the weekend.
- A 1% move in the position is not a 1% account gain when the position uses 10% of equity. Before costs and other effects, that isolated target corresponds to roughly 0.1% of equity. This arithmetic is interpretation, not a measured return.

## Documented rules and trade lifecycle

- Record Monday's open and set the buy limit 1% below it.
- Allow only one trade per week and use the described 10%-of-equity position size.
- After a fill, set a sell limit 1% above the fill price at the start of the following day.
- If price draws down 0.5% or more while the position is open, set a sell limit at entry. This waits for a recovery; it is not a stop that guarantees a 0.5% loss cap.
- Close any remaining position at Friday end-of-day using a market-on-close order.

## Parameters and stated settings

- Article rules: 1% dip, 1% position target, 0.5% adverse threshold, one trade/week, 10% equity sizing.
- Author simulation properties use zero commission and zero slippage. Calculation levels have no customizable inputs in the described script.

## Failure modes and caveats

- The break-even limit can remain unfilled through a continuing decline, leaving substantial risk until the forced exit.
- A limit order does not make all execution costs disappear; spreads, gaps and the Friday market order still matter.
- Holiday Mondays/Fridays and market sessions must be defined explicitly. TQQQ behavior is not evidence of transfer to SOL.

## Missing information and implementation boundary

- Recover holiday-week handling, order cancellation, intrabar priority and exact drawdown-reference semantics.
- No repository backtest validates the advertised weekly objective.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: purpose

> Simply put, the goal of this strategy is to trade TQQQ using an objective system with simple rules and no weekend holds, targeting 1% weekly returns while controlling drawdowns and preventing overtrading.
> 
> This strategy was created to exploit short-term pullbacks during strong uptrends on TQQQ. With this in mind, the strategy is naturally long-only. Additionally, the strategy executes only one trade per week, which naturally limits trade activity and makes for a more robust system.
> 
> While this strategy may not outperform buy-and-hold returns, it can offer more consistent behavior with relatively modest drawdowns and gains over time. The resulting equity curve is typically smoother overall than that of a typical buy-and-hold position, and therefore potentially more favorable from a long-term performance perspective.

### E2: props

> Position Sizing: Sizing is 10% of equity, the same as in the article.
> 
> Commissions: Commission value is set to $0. Most major US brokers charge $0 commission on stocks and ETF trades, including leveraged ETFs such as TQQQ. 
> 
> Slippage:  Slippage is set to 0. This strategy uses only limit orders, with the exception of a market-on-close order for the end of the week as a hard exit. For this reason slippage is not a consideration for this script.

### E3: rules

> █ THE RULES
> 
>  Track Monday's Opening Price: Each week, Monday's open is noted.
> 
> 
>  Enter on a 1% dip from the Open: On the open, a limit buy order is set at -1% from the open.
> 
> 
>  Set a 1% profit target: If the buy order is filled, a limit sell (take-profit) order is set at the start of the following day for +1% from the fill price. By waiting until the start of the following day, this allows for occasional profits greater than 1% each week.
> 
> 
>  Breakeven if 0.5% drawdown occurs: While in a position, if a drawdown of 0.5% or greater is observed, we immediately set a limit sell order at the entry price (breakeven).
> 
> 
>  Hard stop at Friday close: A market-on-close order is set for EOD Friday to exit us from any position which has not met the target or breakeven limits.

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> This script implements "A High-Probability Weekly Trading Strategy For TQQQ" as dictated in the March 2026 edition of the TASC Traders' Tips, "Trading Snapbacks In A Leveraged ETF”. In this article the author creates a mean reversion strategy intended for systematic and discretionary traders with the goal of having a minimal number of rules, low time commitment, and a consistent weekly profit target.

> TQQQ is a 3x leveraged fund based on the Nasdaq-100 index. The article focuses specifically on this instrument because of its key characteristics that are suitable for this type of strategy:

> The strategy aims to educate users about the specific trading approach outlined in the article. Therefore, it does not include customizable inputs to adjust calculations or levels. However, users can still adjust strategy parameters such as trade sizes, commissions, margin, etc. in the "Properties" tab.

> Set a 1% profit target: If the buy order is filled, a limit sell (take-profit) order is set at the start of the following day for +1% from the fill price. By waiting until the start of the following day, this allows for occasional profits greater than 1% each week.

> Breakeven if 0.5% drawdown occurs: While in a position, if a drawdown of 0.5% or greater is observed, we immediately set a limit sell order at the entry price (breakeven).

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
