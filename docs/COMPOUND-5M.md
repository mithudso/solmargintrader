# Compound five-minute scorecard

A tester for one question: **will the next 5-minute bar close up or down?** Every metric in
`5minleveragestrategies.json` (and the ones it was missing) scores that bar from -1 (down) to +1
(up). The scores are combined into one call (UP, DOWN or FLAT), which you can backtest and
forward test, metric by metric and combined. Nothing here places an order.

| Piece | Where |
| --- | --- |
| Scoring and aggregation (pure, no I/O) | `backtester/core/scorecard.py` |
| Historical evaluation through the engine | `backtester/core/compound.py` |
| Saved config, live reads, forward ledger, sweeps, CLI | `soltui/compound.py` |
| The tab | soltui → **Compound 5m** |
| Registry commands (TUI, CLI, API, extension host) | `compound.catalog`, `compound.config`, `compound.save`, `compound.reset`, `compound.signal`, `compound.backtest`, `compound.results`, `compound.forward_tick`, `compound.forward_status` |
| Agent skill | `skills/five-minute-signal/SKILL.md` (live copy in `~/.claude/skills/`) |
| One command for everything | `research/full_suite.py` |

## How a call is made

1. **Score.** Each enabled metric returns a score in [-1, 1] for the latest *closed* bar, or
   "undefined" (warming up, or a live input missing). Undefined is never treated as zero.
2. **De-duplicate families.** RSI, Stochastic and CCI measure one thing; MACD and an EMA cross
   share two EMAs. With `dedupe_families=1` each family votes once, at its heaviest member's
   weight, so the family with the most indicators does not win by count.
3. **Weight by regime.** Each bar is classified trend (ADX ≥ 25), range (ADX ≤ 18), squeeze
   (Bollinger width in its lowest 15% over a day) or neutral. Trend styles weigh 1.5× in a
   trend and 0.5× in a range; reversion styles the reverse; breakouts 1.6× in a squeeze.
   This is the catalogue's own regime table, and the measurements below show it points the
   wrong way at 5m.
4. **Threshold.** |composite| ≥ `entry` (0.25) calls UP or DOWN. A held position stays on while
   the composite keeps its sign above `exit` (0.10): hysteresis, because every flip pays a
   round trip.
5. **Gate.** Any enabled gate that blocks forces FLAT and is named in the call.

## Metrics

| Group | Metrics (id) | Source in the JSON |
| --- | --- | --- |
| Trend / direction | `ema_cross`, `macd`, `adx_dmi`, `vwap_side`, `htf_trend`, `ichimoku` | MA crossover, MACD, ADX, VWAP, execution step 3, Ichimoku |
| Momentum / adaptive | `roc`, `persistence` (lag-1 autocorrelation × last move) | Breakout / momentum; added |
| Oscillators (one family) | `rsi`, `stochastic`, `cci` | RSI, Stochastic; CCI added |
| Mean reversion | `bollinger`, `zscore`, `vwap_reversion` | Bollinger, Mean reversion, VWAP |
| Breakout / structure | `donchian`, `squeeze`, `trend_continuation`, `liquidity_sweep`, `fib_pullback` | Breakout, Volatility squeeze, 5m continuation, Liquidity sweep, Fibonacci |
| Volume / flow | `obv`, `money_flow` (candle proxy, not taker delta), `book_imbalance` (live) | OBV, Order-flow imbalance |
| Positioning | `funding`, `premium` (live), `oi_flow` (live) | Funding arbitrage input, cross-venue observation |
| Cross-asset | `btc_lead` | added |
| Lifecycle | `trend_lifecycle` (early / mature / exhausted), `cycle_phase` (markup / markdown / accumulation / distribution) | added |
| Gates | `gate_cost`, `gate_liquidation`, `gate_shock`, `gate_volume`, `gate_events`, `gate_session`, `gate_news` (live) | Execution checklist 1-2, regime table "no-trade" |

Every metric's formula, parameter ranges, "works when" and "fails when" are in the tab (select a
row) and in `python3 -m soltui.compound catalog`. Eight catalogue entries are not five-minute
direction calls (grid, scalping as a style, swing, DCA, three kinds of arbitrage, Jupiter's
unpublished flow imbalance); `scorecard.NOT_DIRECTIONAL` says why for each, and the tab lists
them.

## What else should be checked, and what is

* **The whole technicals arsenal? No.** Most indicators are re-expressions of three quantities:
  trend (moving-average distance), position in the recent range (oscillators, bands) and
  volume. Adding Williams %R, MFI, TRIX or KST adds votes, not information. One or two per
  family is enough, and family de-duplication stops the rest from stacking.
* **Higher timeframe.** Added (`htf_trend`, completed 15m–1h bars only).
* **Cost hurdle and liquidation distance.** Added as gates. These matter more than any
  indicator; see the findings.
* **Derivatives positioning.** Funding (backtestable from the Hyperliquid cache), premium, open
  interest change and order-book imbalance (live only: no venue serves their history).
* **Cross-asset lead.** BTC's last closed bar.
* **News.** Treated as *risk*, not as a predictor: a scheduled-event blackout (`gate_events`,
  your events file), a shock detector for unscheduled news (`gate_shock`: range or volume far
  outside normal), and an optional live headline gate (`gate_news`, CoinDesk and Cointelegraph
  RSS, keyword match). Headline *sentiment* is not scored: there is no timestamped archive to
  test it on, so it could only be a guess presented as a number. An enabled news gate whose
  feeds are unreachable blocks the call (fails closed).
* **Lifecycle stage.** Two kinds are scored. The *trend's* lifecycle (`trend_lifecycle`: bars
  since the EMAs crossed and extension in ATRs; exhausted trends get faded) and the *market
  cycle* phase (`cycle_phase`, a Wyckoff-style read of the last day). A *token's* lifecycle
  (listing age, unlock schedule, supply concentration) moves on a scale of weeks, not five
  minutes; it belongs in coin selection (`research/coin-intelligence/`), not in this call.

## Findings: 1,420 configurations, five coins, 30 days of 5m bars

Run `20261107T130441Z-f7fea5b2368e`: `python3 -m soltui.compound sweep --perturb --aggregate-grid`
over the cached 2026-07-06 to 2026-08-06 bars (8,927–8,929 per coin) (SOL native 5m; BTC, ETH, DOGE, ZEC aggregated from
1m). In-sample = first 70%, out-of-sample (OOS) = last 30% (about 2,680 bars per coin). Costs:
6 bps fee + 2 bps slippage per side, a 16 bps round trip (Jupiter base fee plus its 1 bp impact
floor and adverse execution).

**1. No configuration made money after costs.** 10 of 1,420 had a positive OOS return; every one
of them had an OOS hit rate within 1.2 standard errors of a coin flip, and 7 of the 10 lost in-sample.
That is the shape of luck, not edge.

**2. Even perfect foresight loses on four of five coins.** The `oracle net bps` column is what a
call that is *always right* earns per one-bar round trip after costs:

| | BTC | DOGE | ETH | SOL | ZEC |
| --- | --- | --- | --- | --- | --- |
| mean \|5m move\| (bps) | 6.2 | 8.7 | 8.6 | 8.5 | 15.6 |
| oracle net per one-bar trade (bps) | -9.8 | -7.3 | -7.4 | -7.5 | -0.4 |

A 5m direction call can only pay by holding through several bars in one round trip, which is
what the hysteresis and the cost gate (`hold_bars`) are for.

**3. Direction is weakly predictable, in the reversion direction.** Out-of-sample hit rates of
each metric alone (z = standard errors from 50%):

| Metric | BTC | DOGE | ETH | SOL | ZEC |
| --- | --- | --- | --- | --- | --- |
| `rsi` | 51.3% (+1.1) | 56.5% (+5.1) | 51.5% (+1.3) | 51.4% (+1.2) | 52.0% (+1.7) |
| `zscore` | 51.7% (+1.5) | 55.3% (+4.6) | 51.8% (+1.6) | 51.3% (+1.2) | 51.8% (+1.6) |
| `bollinger` | 51.0% (+0.9) | 54.5% (+4.0) | 52.4% (+2.1) | 50.8% (+0.7) | 52.0% (+1.8) |
| `ema_cross` | 48.7% (-1.2) | 45.8% (-3.9) | 48.6% (-1.4) | 48.5% (-1.4) | 48.0% (-1.9) |
| `htf_trend` | 47.9% (-2.0) | 47.2% (-2.6) | 47.8% (-2.0) | 46.6% (-3.2) | 49.2% (-0.7) |
| `trend_continuation` | 48.5% (-0.8) | 44.6% (-3.0) | 45.9% (-2.4) | 46.4% (-2.0) | 50.7% (+0.4) |

Reversion metrics beat 50% on every coin; trend metrics fall below it on nearly every coin. So
the catalogue's advice to favour continuation in trends is backwards at this horizon, and the
default compound (regime weighting on) inherits that: its OOS hit rate was 44–49% on all five.

**Read the reversion edge with three cautions.** (a) Part of it is probably bid-ask bounce:
Coinbase closes alternate between bid and ask prints, which creates negative autocorrelation
that cannot be traded. Jupiter fills at the oracle price, which has no bounce. (b) Calls on
consecutive bars overlap, so the z-scores overstate independence. (c) 1,420 configurations were
tried on one 30-day window; the best few are expected to look good by chance. Thirty days is
one regime. Run the full suite (a year of 5m bars) before trusting any of this.

## Commands

```bash
# Live call with every metric explained (public data, no keys, no orders)
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound signal --asset SOL

# Forward test unattended: one call per closed 5m bar, resolved when the next bar closes
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound forward --asset SOL --loop
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound status --asset SOL

# Backtest the saved config: the compound plus each enabled metric alone
/Users/mitch/.venvs/soltui/bin/python -m soltui.compound backtest --asset SOL

# Everything: fresh data for the universe, then every registry and compound backtest
/Users/mitch/.venvs/soltui/bin/python research/full_suite.py --plan
/Users/mitch/.venvs/soltui/bin/python research/full_suite.py
```

Files: config `~/.config/soltui/compound/config.json`; backtest rows
`~/.config/soltui/compound/backtests.jsonl`; forward ledger
`~/.config/soltui/compound/forward/<ASSET>.jsonl`. Scheduled events for `gate_events` go in the
config file's `events` list (`{"ts": <UTC epoch seconds>, "title": "CPI"}`) or through
`compound.save`.
