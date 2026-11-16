# TradingView seven-strategy source contract

Version: 1.2.0. Delta: distinguish screenshot Channel Breakout from Price Channel and record the observed interval.

This is a working research record, not a completed rabbithole, executable card,
TradingView parity proof, or backtest. The owner identified the chart as
`COINBASE:ZECUSDC.P` and said that strategy inputs were defaults. The owner confirmed a 10-minute chart interval. Tester properties, exact endpoint
time, timezone and the historical script revision remain unconfirmed. The connected browser listed no existing TradingView tab; a fresh
visit to the supplied saved-chart URL returned “Chart Not Found”.

| Strategy | Existing record | Official Pine defaults and orders |
| --- | --- | --- |
| Momentum | `tv_43000599883_momentum_strategy`, research-only | Version 29.0: length 12; period momentum and its one-bar change must have the same strict sign; submit a stop one tick above the high or below the low; cancel that side when its condition fails. |
| Moving average crossover | No exact source card established | Version 31.0: SMA length 9, confirm bars 1. Count consecutive closes strictly above or below the SMA; issue a market entry when its count equals one. |
| Parabolic SAR | `tv_43000645065_parabolic_sar_strategy`, incomplete | Version 33.0: start 0.02, increment 0.02, maximum 0.2. The source defines a stateful SAR, extreme point, acceleration and bounded prior-bar values, then submits the opposing stop at next-bar SAR on confirmed bars. |
| Pivot reversal | `tv_43000594526_pivot_reversal_strategy`, incomplete | Version 33.0: pivot left 4, right 2; confirmed high/low pivots drive stop entries one tick beyond the pivot. This differs materially from the discretionary pivot-point help description. |
| Price channel | `tv_43000601862_price_channel_strategy`, research-only | Version 29.0: length 20; submit both stop orders at the current trailing highest high and lowest low after the source's `close[length]` check. |
| Two moving averages crossover | No exact source card established | Version 31.0: SMA 9 and SMA 18 of close; `ta.crossover` and `ta.crossunder` submit market entries. |
| Volatility expansion-close | `tv_43000599890_volty_expan_close_strategy`, research-only; separate existing `backtester/core/volty.py` | Version 30.0: length 5 and multiplier 0.75; simple average of `ta.tr`, then stops at close plus/minus that product after the `close[length]` check. Verify existing runner against each source edge case and fill. |

## Exact built-in source snapshots

The standard catalog and Pine Editor's **Create new → Built-in** flow exposed
public source without signing in. The editor requested each source through its
normal Pine facade endpoint. `last` is mutable; the listed version and immutable
Mongo snapshot SHA-256 bind what was read. The returned source has no explicit
license notice, so do not redistribute the source without checking terms.

| Strategy | Source ID | Version | Source snapshot SHA-256 |
| --- | --- | --- | --- |
| Momentum | `src:226ef9fa1b185243` | 29.0 | `c1ffb758acd11d4a6c98142e370b8059f23ca4e0281f06d4eeb34062651f80f8` |
| Moving average crossover | `src:d009b1e195649778` | 31.0 | `3f4d5ec22e85d0fb70797001140574a78b73779c50852545f0b76eee7b2f5e68` |
| Parabolic SAR | `src:260da27279d3c3e8` | 33.0 | `800f3fe7f02df408f9f144951e6e44744240a67dec2825d0953d5309b0a4bef1` |
| Pivot reversal | `src:f1cf879aa1a71c9a` | 33.0 | `cd6def72548fb84e02312f302dd2799f897638d0a2c688aef04ca861b5a5628f` |
| Price channel | `src:32ea2fc6e5c00b2c` | 29.0 | `67b77dac93c82a93f708993f1f56be7a7558fbce94ec024c999780c20f9adb43` |
| Two moving averages | `src:bcf0c7a7cb59abb1` | 31.0 | `811195bd717c8c71ca341240884bdcc367f7a5d59f2c652270cffe24538aa678` |
| Volatility expansion-close | `src:9fa8ed6b7e7c1466` | 30.0 | `52780b01f1b03db834600fca839d0bbc66fecd4916ea5de1a1adda325a831b04` |

Frozen readiness records and their checksum-bound cards are not amended by this
record. Any new implementation must have a versioned source contract, a card
with defaults matching the runner in both directions, causal warmup and fill
fixtures, and Mongo schema parity when a new card kind is introduced. A pivot
must not signal before the confirming bars exist. Distinguish a filled resting
stop from a close-confirmed signal, and test both intrabar ordering and gaps.

Apply the same explicit tester initial capital, sizing, margin, commissions,
slippage, order-processing behavior and date range to every comparison once
known. A perp study additionally requires matched market bars and a documented
funding/liquidation model. Missing funding or spread is a limitation, never zero
by implication. Report return, trade count, drawdown, cost sensitivity and
buy-and-hold, with no claim that a separate backtest reproduces the owner's
observed TradingView return. Protect existing holdout reservations.

## Pinned official descriptions

Complete `solution.description` text was extracted from the official help page
application data, normalized into readable text, and stored as immutable Mongo
snapshots. These sources are one organization, and they do not establish Pine
source, default values or trading profitability.

| Source | URL | Snapshot SHA-256 |
| --- | --- | --- |
| Momentum | https://www.tradingview.com/support/solutions/43000599883-momentum-strategy/ | `3fb96afba6f5271e08e5eb9a15762c1c3935741577304682ac3d0e4d83240549` |
| Price Channel | https://www.tradingview.com/support/solutions/43000601862-price-channel-strategy/ | `e673d6e06f277a3e4a51cb6f32ffbf3aa6a55a706bba224e497a7e0bce99ac87` |
| Pivot Reversal | https://www.tradingview.com/support/solutions/43000594526-pivot-reversal-strategy/ | `f65d44609fe7ef807fceba97b97bfb9687e5b3285c0fc09c2e7cf649c3bc08a9` |
| Parabolic SAR | https://www.tradingview.com/support/solutions/43000645065-parabolic-sar-strategy/ | `907d41dcdea78da71ba3755ce7442c4fc15860165dd2e90c0c69158c69ecfa12` |
| Volty Expan Close | https://www.tradingview.com/support/solutions/43000599890-volty-expan-close-strategy/ | `59b4e6b017632de761f1057a82492d15cb57f73fe8ba03a19a57538fa7b77e13` |

Next: finish full inventory and four-mode scoped dedup, read and check each pinned Pine source against implementation, inspect data and tester properties, record
atomic claims and source spans under owned concept leases, then complete the
six-question depth passes and trusted gate. The seven Mongo runs remain
unqualified until that process and actual publication receipts succeed.

## User-supplied reports and a distinct channel strategy

The owner supplied two TradingView report screenshots and identified the chart
interval as ten minutes. Each report displays Coinbase Advanced, 100,000 USDC
initial capital and June 21 through November 16, 2026. The visible report
figures are user-supplied simulator observations; the tester properties, exact
time cutoff, intrabar assumptions and independent reproduction remain unknown.

- Volatility expansion-close: total P&L +619,225.79 USDC (+619.23%), maximum
  drawdown 74,520.91 USDC (13.87%), 988 profitable of 2,396 trades, profit
  factor 1.313 and three margin calls.
- The second screenshot says `Channel break str`, the short title of **Channel
  breakout strategy**, not **Price channel strategy**. It displays +413,226.04
  USDC (+413.23%), maximum drawdown 120,257.81 USDC (20.05%), 410 profitable
  of 1,101 trades, profit factor 1.34 and four margin calls. The chart legend
  values at its visible crosshair are hovered intermediate values, not final
  performance or final buy-and-hold.

The public TradingView catalog identifies `STD;Channel%1BreakOut%1Strategy`
version 29.0 separately from `STD;Price%1Channel%1Strategy` version 29.0.
Its pinned source is `src:76a6738dbe0a2319`, SHA-256
`f438bd98aefb5ed835939a63678dd707740f2265459bd19923ce12c9b056cf30`.
It defaults to length 5 and places stops one tick beyond the trailing extrema.
The source guards only the long order with `not na(close[length])`; the short
order lies outside that guard. Price Channel defaults to length 20, places
stops at the trailing extrema, and guards both orders. The screenshot does not
prove which historical source version or settings generated its report. Test
both separately and do not ascribe Channel Breakout's results to Price Channel.
