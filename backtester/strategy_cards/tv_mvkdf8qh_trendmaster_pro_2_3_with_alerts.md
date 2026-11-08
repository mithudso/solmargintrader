---
id: tv_mvkdf8qh_trendmaster_pro_2_3_with_alerts
name: "TrendMaster Pro 2.3 with Alerts"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Trade moving-average trend changes only when configurable momentum, trend-strength, volatility and session constraints also agree, with a defined risk budget."
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
# TrendMaster Pro 2.3 with Alerts

Version: 1.1.0 (2026-11-08). Delta: v1.0.0 to v1.1.0; explain the complete publication mechanism, objective and source gaps.

**Classification:** trading-strategy. Spec-only; no runnable repository implementation or measured performance.

## Idea and objective

Trade moving-average trend changes only when configurable momentum, trend-strength, volatility and session constraints also agree, with a defined risk budget.

## How it works

- A short/long moving-average crossover is the primary signal. An optional higher-timeframe moving-average condition aligns direction with a broader trend.
- Bollinger width, RSI, MACD, stochastic and ADX layers gate candidate signals. Requiring agreement reduces activity but does not establish that the filters provide independent information.
- Session trade counts, daily outcome limits, stop selection and dollar-risk sizing form a separate risk-management layer. Support/resistance pivots are also displayed; the description does not explicitly make every displayed pivot an entry gate.

## Documented rules and trade lifecycle

- Generate direction from the configured fast/slow MA crossover, then require the enabled filter layers to pass.
- The description gives RSI long/short thresholds 55/45, ADX above 25, and alignment of MACD with its signal line; Bollinger-width and stochastic numeric rules are not fully supplied.
- Observe the configured session limits and daily take-profit/stop-loss counts, and close at the configured market-close time.
- Choose percentage, MA-cross or band-based stop handling, then derive the profit target from stop distance and the configured reward/risk ratio.

## Parameters and stated settings

- Stated settings include MA periods 9/21, optional higher-timeframe MA 50, five trades per session, reward/risk 2 and a described $150–$250 risk range.
- Sessions are listed as Asia 18:00–00:00, London 00:00–08:00, NY AM 08:00–13:00, NY PM 13:00–18:00; the applicable timezone is not disclosed.

## Failure modes and caveats

- Many filters and session/risk settings create a large tuning space and can overfit the same price information.
- Using an unconfirmed higher-timeframe value or misinterpreting the session timezone can change historical signal availability.

## Missing information and implementation boundary

- Recover exact filter enablement/defaults, Boolean combinations, widths, stochastic thresholds, stop formulas, dollar-risk calculation and reset timing.
- No complete source code or repository performance result is available.

## Evidence and interpretation

The explanation above synthesizes the complete saved author description. Rules and numerical settings are attributed to that description; failure-mode analysis is our interpretation. The saved `script.content` field is empty. A public/open-source label does not supply the missing code. No order, bot or live integration is created by this card.

### E1: core

> Core Strategy Components
> 
> Multi-Moving Average System - Uses configurable MA types (EMA, SMA, SMMA) with short-term (9) and long-term (21) periods for primary signal generation through crossovers
> Higher Timeframe Trend Filter - Optional trend confirmation using a separate MA (default 50-period) to ensure trades align with broader market direction
> Band Power Indicator - Dynamic high/low bands calculated using different MA types to identify price channels and volatility zones

### E2: filters

> Advanced Signal Filtering
> 
> Bollinger Bands Volatility Filter - Prevents trading during low-volatility ranging markets by requiring sufficient band width
> RSI Momentum Filter - Uses customizable thresholds (55 for longs, 45 for shorts) to confirm momentum direction
> MACD Trend Confirmation - Ensures MACD line position relative to signal line aligns with trade direction
> Stochastic Oscillator - Adds momentum confirmation with overbought/oversold levels
> ADX Strength Filter - Only allows trades when trend strength exceeds 25 threshold

### E3: risk

> Session-Based Trading Management
> 
> Four Trading Sessions - Asia (18:00-00:00), London (00:00-08:00), NY AM (08:00-13:00), NY PM (13:00-18:00)
> Individual Session Limits - Separate maximum trade counts for each session (default 5 per session)
> Automatic Session Closure - All positions close at specified market close time
> 
> 
> Risk Management Features
> 
> Multiple Stop Loss Options - Percentage-based, MA cross, or band-based SL methods
> Risk/Reward Ratio - Configurable TP levels based on SL distance (default 1:2)
> Auto-Risk Calculation - Dynamic position sizing based on dollar risk limits ($150-$250 range)
> Daily Limits - Stop trading after reaching specified TP or SL counts per day

### Retained coverage passages

These normalized passages retain the earlier coverage ledger's source bindings.

> A member of the community approached me and asked me how to write an indicator that would achieve a particular set of goals involving comprehensive trend analysis, risk management, and session-based trading controls. Here is one example method of how to create such a system:

> Band Power Indicator - Dynamic high/low bands calculated using different MA types to identify price channels and volatility zones

> Risk/Reward Ratio - Configurable TP levels based on SL distance (default 1:2)

> Multiple Stop Loss Options - Percentage-based, MA cross, or band-based SL methods

> Visual Trade Management - Color-coded entry, SL, and TP levels with fill areas

> Multi-Moving Average System - Uses configurable MA types (EMA, SMA, SMMA) with short-term (9) and long-term (21) periods for primary signal generation through crossovers

> Higher Timeframe Trend Filter - Optional trend confirmation using a separate MA (default 50-period) to ensure trades align with broader market direction

> Auto-Risk Calculation - Dynamic position sizing based on dollar risk limits ($150-$250 range)

## Data and availability

The machine-readable input requirements state the source-reviewed data prerequisites. Availability means only that the named data class is supported; it does not establish a cached instrument, complete session calendar, futures contract metadata or execution parity. Source-specific requirements and gaps above still apply.

## Measured results

Not measured in this repository. Author examples and advertised objectives are not independent net-of-cost or out-of-sample results.

## Likelihood of success: low

Basis: a-priori. No confirming out-of-sample evidence exists here. For templates and overlays this rates an untested trading use, not the usefulness of the software example.

## Sources

https://www.tradingview.com/script/mVkDf8qh-TrendMaster-Pro-2-3-with-Alerts/

Source and raw-description SHA-256 values, exact passage offsets, classification and card mapping are recorded in `research/tradingview-strategy-understanding.json`. The complete source capture remains local.
