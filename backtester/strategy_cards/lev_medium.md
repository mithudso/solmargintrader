---
id: lev_medium
name: Leverage tier, medium margin
kind: exposure-strategy
status: implemented
family: leverage-tier
summary: Runs any registered long/flat strategy as a Jupiter-Perps position at 5x by default, with borrow fees, open/close fees, slippage, maintenance margin and intrabar liquidation.
registry_key: lev_medium
runner: backtester.cli
warmup_bars: 53
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  base: {default: macd, type: str, desc: "registry key of the wrapped strategy"}
  leverage: {default: 5.0, type: float, desc: "perp leverage the harness must run the position at"}
  base_params: {default: "", type: str, desc: "JSON object of constructor params for the base strategy, empty for defaults"}
---
# Leverage tier: medium margin

## What it is
A wrapper, not a signal. The base strategy picks when to hold; the tier multiplies exposure by 5x (default, configurable) and lets the engine charge what that costs on the Jupiter Perps venue.

## What it looks for
Nothing new. It asks whether a signal that is marginal unlevered survives leverage once carry, fees and liquidation are paid.

## Equation
```
notional_t   = target_t * equity_t * L
collateral   = notional / L
borrow_fee   = rate_bps/hr * utilization * hours * notional      (paid by longs and shorts)
liq_buffer   = collateral/notional - close_fee - 0.002 - borrow_fee/notional
liq_price    = entry * (1 - liq_buffer)                          (long)
liq_fill     = min(liq_price, bar_open) * (1 - penalty)          (long, adverse)
payout       = 0 on liquidation (remaining collateral forfeited)
```
Break-even move is independent of L (docs/LEVERAGE-ECONOMICS.md, Stele DOC-714); L only moves the barrier and the carry drag on collateral.

## Implementation
`backtester/core/strategies/tiers.py`, run through `backtester/core/leverage.py::tier_config`. Liquidation is checked on every held bar, and on the finer 1h/1m bars inside it where a layer covers the bar (`IntrabarLayer`).

## Parameters
- **base / base_params** select and configure the wrapped strategy.
- **leverage** the multiple. A spot EngineConfig ignores it and runs the base strategy unlevered.

## Works when
The base signal is right early and the path never retraces by roughly 1/L before it pays.

## Fails when
Any adverse excursion near 1/L occurs before the signal resolves; the position is then closed at the liquidation level with collateral forfeited. At 20x that is about 4.7% before carry.

## Backtest notes
Daily bars hide order of events inside the bar. Intrabar layers restore it where the data exists (1h covers about a year of SOL, 1m about 30 days); other bars use the coarse low/high, which is never less severe. See research/LEVERAGE-TIERS.md.

## Pairs with
Nothing. Combining a tier with a leverage-hungry signal compounds the same risk.

## Measured on SOL
CPCV out-of-sample results per tier are in `research/LEVERAGE-TIERS.md` and `research/results/leverage_tiers_*.csv`.

## Likelihood of success: very-low

*Basis: base-rate. Leverage changes the barrier and the carry, not the break-even move, and the base-rate for these signals out of sample is poor (Stele KNOW-632, KNOW-596).*

Rated from the sweep's overall hit rate, not from this card's own result.

## Caveats and limitations
- The liquidation penalty (50 bps default) is an assumption, not a venue constant.
- Price-impact fees, keeper latency and priority fees are not modelled; each makes results worse.
- Long/flat only; the wrapped strategies never short.

## How to run
```bash
python3 -m research.leverage_tiers --asset SOL --interval 1d
```
