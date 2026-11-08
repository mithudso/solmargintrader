---
id: dca_bot
name: DCA Safety-Order Bot
kind: bot
status: implemented
family: mean-reversion
summary: Base order plus a ladder of deeper safety orders and one take-profit above the average entry; restarts after each exit. Simulated by core/dcasim.py.
registry_key: null
runner: backtester.botcli
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: a-priori
params:
  base_order_usd: {default: 100.0, type: float, desc: "USD of the market buy that opens each deal"}
  safety_order_usd: {default: 100.0, type: float, desc: "USD of the first safety order; later ones scale by volume_scale"}
  max_safety_orders: {default: 5, type: int, desc: "how many safety orders rest below the base fill (0..50)"}
  price_deviation_pct: {default: 2.0, type: float, desc: "percent below the base fill where the first safety order rests"}
  step_scale: {default: 1.0, type: float, desc: "each deeper step is the previous step times this"}
  volume_scale: {default: 1.0, type: float, desc: "each deeper safety order is the previous size times this"}
  take_profit_pct: {default: 2.0, type: float, desc: "percent above the average entry where the whole position sells"}
  stop_loss_pct: {default: 0.0, type: float, desc: "percent below the average entry that closes the deal at the next open; 0 disables it"}
  cooldown_bars: {default: 0, type: int, desc: "bars to wait after a deal closes before the next base order"}
  min_order_usd: {default: 10.0, type: float, desc: "venue minimum; base and safety orders below it are refused"}
presets: {}
---
# DCA Safety-Order Bot

Design version: 1.0 (2026-11-08).

## This is not the `dca` strategy

`dca.md` is periodic dollar-cost averaging: buy a fixed amount every N bars, as an
exposure staircase. **This** card is the trading-bot sense of "DCA" (3Commas, Pionex,
Bitsgap): a deal-based state machine with resting limit orders. It is not a `Strategy`
in the `core.engine` sense and has no registry key; its edge, such as it is, comes from
limit orders that fill intrabar at known prices.

## Equations

With base fill price `P0`, deviation `d`, step scale `s`, volume scale `v`, `n` safety orders:

```text
depth_k  = d * (1 + s + s^2 + ... + s^(k-1))          percent below P0, k = 1..n
level_k  = P0 * (1 - depth_k / 100)
size_k   = safety_order_usd * v^(k-1)
avg      = (base + sum filled size_k) / (base/P0 + sum filled size_k/level_k)
TP       = avg * (1 + take_profit_pct / 100)
capital  = base + sum_{k=1..n} size_k                  per deal, before fees
```

A deal closes when the high reaches `TP` (profit) or, when `stop_loss_pct > 0`, when a
close falls to `avg * (1 - stop_loss_pct/100)` (loss, filled at the next open). The next
deal's base order is a market buy at the open after the exit plus `cooldown_bars`.

## Why it might work, and why it usually does not

The bot sells volatility around a level the way a grid does: in a range, every dip that
fills a safety order lowers the average and brings the take-profit closer, so small
oscillations convert into many small realized gains. Its failure mode is the trend.
A falling market fills every safety order, the take-profit recedes with the market, and
the deal then holds a full-size losing position until price recovers. Without a stop the
bot does not lose on paper until the run ends, which is why `dcasim` force-closes the
open deal at the final close and reports it separately (`open_deal_at_end`). A stop loss
converts the bag into a realized loss at the worst point of the range.

Expected profit is not the same as the deal win rate. The bot wins most deals by
construction, since a deal only closes at a profit unless a stop exists, so a high win
rate here is not evidence. Compare total return against buy-and-hold of the same capital,
which `dcasim` reports as the baseline.

## Simulation conventions (pessimistic)

`core/dcasim.py` mirrors `core/gridsim.py`'s bar order: queued market order at the open,
safety buys against the low (shallowest first), take-profit against the high, mark at the
close, plan from the close. Nothing fills on the bar that placed it. A bar that fills a
buy cannot also fill the take-profit, because the intrabar path is unknown. Every fill
pays the taker fee and adverse slippage. An unfundable safety order is skipped and counted.
`test_dcasim.py::test_a_future_spike_does_not_change_earlier_decisions` is the one-bar
leak test.

## Limitations

- Fills at a limit level assume enough size at that level; there is no depth model.
- One deal at a time on one asset; no multi-pair allocation or compounding of the deal size.
- The take-profit sells the whole position in one order; partial take-profit ladders are not modelled.
- On 1h bars a deal that would round-trip inside one hour is missed by construction.

## How to run

```bash
python -m backtester.botcli dca --synthetic 600
python -m backtester.botcli dca --asset SOL --interval 1h --start 2026-05-09 --allow-gaps
```

The soltui **Bots** tab runs the same simulator from a chosen start point, forward-tests
it on the recorded Coinbase stream, and auto-optimizes it across every cached coin.

## Likelihood of success: low

Basis: a-priori. The status is `implemented`, so no measured result is cited here. The
mechanism is a short-volatility position like the ladder grid, which lost to buy-and-hold
walk-forward on 9 of 9 coins in this repo's sweep (`ladder_grid.md`). Treat any single
backtest from the Bots tab as one path; only the auto-optimize out-of-sample sign test
says anything about one configuration being reliably better than another.
