---
id: trigger_trade
name: Reliable-trigger trade
kind: exposure-strategy
status: implemented
family: trigger
summary: Waits for a conjunction of causal conditions, enters at the next bar open in the predicted direction, exits when the horizon expires or a MAE-derived stop is hit.
registry_key: trigger_trade
runner: backtester.cli
warmup_bars: 120
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  conditions: {default: "rsi_lt30&bb_touch_lo", type: str, desc: "1 to 3 condition names joined by &, from core/trigger_conditions.py"}
  direction: {default: 1, type: int, desc: "1 long, -1 short (short needs perp mode with allow_short)"}
  horizon: {default: 3, type: int, desc: "bars to hold; the trigger context expires after this"}
  stop: {default: 0.0, type: float, desc: "adverse close fraction that exits early; 0 disables"}
---
# Reliable-trigger trade

## What it is
The execution half of the trigger miner. `research/triggers.py` scores conjunctions of conditions by how often the next h bars go the predicted way; this strategy trades one of them.

## What it looks for
A trigger firing at the close of bar t. Example: `volume >= 10x its rolling median and close at a 2-sigma low`.

## Equation
```
fire_t      = AND(condition_k(bars 0..t))
entry       = open[t+1]              (engine fill_delay=1)
exit        = decided at close[t+h]  (filled at the next open), or close[i] <= entry*(1 - stop) for longs
target      = direction while the context is live, else 0
```
Evaluation in the miner uses entry open[t+1] and exit close[t+h], the same window.

## Implementation
`backtester/core/strategies/trigger.py`; conditions in `backtester/core/trigger_conditions.py`.

## Parameters
- **conditions** which trigger. Funding conditions are refused (OHLCV only).
- **horizon** the context expiry. **stop** is derived from the trigger's discovery-period MAE (80th percentile adverse excursion of winning events) by `research/trigger_backtest.py`.

## Works when
The trigger's hit rate beats the base rate out of sample by enough to cover 12 bps fees, 4 bps slippage and carry.

## Fails when
The trigger was a chance in-sample pattern. On SOL no trigger passed all honesty gates out of sample; see `research/RELIABLE_SIGNALS.md`.

## Backtest notes
Stops are checked on closes and fill at the next open, so a gap through the stop is not rescued. Run through the leverage tiers with `--backtest`.

## Pairs with
`lev_low`, `lev_medium`, `lev_high` wrap other strategies; this one carries its own direction, so run it at a tier through `backtester.core.leverage.tier_config`.

## Measured on SOL
See `research/RELIABLE_SIGNALS.md`.

## Likelihood of success: very-low

*Basis: base-rate. No mined trigger qualified as reliable out of sample (Stele KNOW-632, KNOW-596, KNOW-617).*

Rated from the sweep's overall hit rate, not from this card's own result.

## Caveats and limitations
- Exploratory unless a trigger passed every gate.
- Exits at the next open after expiry, not exactly the close of bar t+h.

## How to run
```bash
python3 -m research.triggers --asset SOL --interval 1d --backtest
```
