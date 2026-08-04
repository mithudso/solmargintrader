---
id: ladder_grid
name: Resting-Ladder Grid
kind: ladder
status: measured
family: mean-reversion
summary: A ladder of resting limit orders with paired exits one rung above each lot. The strategy the extension trades.
registry_key: null
runner: backtester.gridcli
warmup_bars: null
evaluation: intrabar-ladder-simulation
data_required: [ohlcv]
data_available: true
params:
  lower: {required: true, type: float, desc: "lowest rung price in USD; no default exists"}
  upper: {required: true, type: float, desc: "highest rung price in USD; no default exists"}
  rungs: {required: true, type: int, desc: "number of ladder levels, minimum 2; gridcli defaults to 7"}
  notional_per_rung_usd: {required: true, type: float, desc: "USD per rung; gridcli defaults to 12, venue minimum is 10"}
  spacing: {default: geom, type: str, desc: "geom for equal percentage width or arith for equal dollar width"}
  deadband_bps: {default: 25.0, type: float, desc: "suppress rungs this close to the market"}
  min_order_usd: {default: 10.0, type: float, desc: "venue minimum; rungs below it are never placed"}
presets: {}
---
# Resting-Ladder Grid

## This is not the `grid` strategy
`grid.md` is an **exposure staircase** off a rolling SMA anchor: a `Strategy` filled at
a bar boundary that can never capture a rung width, because it never has an order
resting at a level. **This** card is the ladder of resting limit orders with paired
exits that `extension/src/core/grid.js` actually trades, simulated by
`backtester/core/gridsim.py`.

It is not a `Strategy` at all — no `on_bar`, no registry key, no target exposure. It has
its own bar loop and its own entry point, because a grid's entire edge comes from limit
orders filling **intrabar at known prices**, which a target-exposure engine cannot
express.

## Parameters
`lower`, `upper`, `rungs` and `notional_per_rung_usd` are **required — `GridConfig` gives
them no default**, because there is no defensible default ladder. The numbers in this
card's examples are examples. `backtester/gridcli.py` supplies its own CLI defaults for
`rungs` (7) and `notional_per_rung_usd` (12), and requires `--lower` and `--upper`.

## What it looks for
Range-bound oscillation, harvested one rung width at a time.

## Equations
```
# ladder geometry (geometric spacing)
ratio    = (upper/lower)^(1/(rungs-1))
level_i  = lower * ratio^i           for i in 0..rungs-1, endpoints pinned
width_bps= mean over i of (level_i/level_{i-1} - 1) * 10000

# the economic contract
exit(lot bought at level_i) = level_{i+1}          # ONE RUNG UP, never at level_i
gross per round trip        = (notional/level_i) * (level_{i+1} - level_i)
                            = notional * rung_width
```
A lot bought on the top rung has no rung above it, so the exit extrapolates one more
step at the same ratio rather than selling flat.

## Implementation
`backtester/core/gridsim.py`, a function-for-function port of
`extension/src/core/grid.js`. Parity is asserted against figures read off the
JavaScript: **699.1319 bps** for a 60–90/7 ladder, **516.7 bps** for the 0.85x–1.15x
ladder `extension/tools/dryrun.js` builds.

**A change to either implementation's economics needs the matching change in the
other**, or the backtest becomes a confident wrong number about the live strategy. This
is a `CLAUDE.md` non-negotiable.

## Three pessimism conventions
1. **An order cannot fill on the bar that planned it.** Planning happens at a bar's
   close, so the earliest fill is the next bar. This is the no-lookahead guard, and it
   also makes a same-bar round trip impossible — "price dipped to the bid then rallied
   to the offer" is an assumption about the intrabar path, not an observation of it.
2. **Fills are adverse.** A buy fills at its level moved up by the full slippage
   allowance, a sell at its level moved down by it.
3. **Buys settle before sells**, so cash freed by a sell cannot fund a buy in the same
   bar.

FIFO realization is additionally bounded to lots opened *before* the current bar.
Without that bound, two exits filling in one bar let the second reach inventory bought
that same bar — an indirect same-bar round trip. It fired on real synthetic data during
development, so the bound is load-bearing rather than theoretical.

## Works when
Price oscillates inside the ladder. Every completed round trip captures the rung width
minus two fees and two slippage legs.

## Fails when
**A one-way move.** Every bid fills, no exit is reached, and the position is maximum-size
at the worst moment. The extension's own dry run records a 24% drawdown leaving the grid
at **-\$8.62 on \$48 deployed** with four open lots and no closed round trips.

## Backtest notes
- Read **per-round-trip gross carefully**. The planner pairs each exit to a specific lot
  while realization matches FIFO, so with several rungs open the two disagree per trip:
  an exit meant to close a cheap lot is matched against an older expensive one, and
  gross per trip comes in below the nominal rung width. Portfolio totals are identical
  either way.
- Carry defaults to **0 bps/hr** because Trigger V2 is a spot venue with no borrow leg —
  not because carry is free. `--carry-bps-per-hour` models a borrowed-margin ladder.
- Every run prints a buy-and-hold baseline on the same bars. A grid that underperforms
  holding the asset has not earned its complexity.

## Pairs with
A regime filter, which vetoes precisely the condition that ruins it. Untested.

## Measured
On 290 synthetic bars with \$500 capital and a 60–90/7 ladder at \$12/rung: 52 round
trips, gross \$14.32, costs \$1.05, realized **\$13.27**, and the book reconciles
exactly (final equity \$513.27 = \$500 + \$13.27). Grid total return +2.65% with a
-1.92% max drawdown, against buy-and-hold +9.93% with a **-41.53%** max drawdown on the
same bars — the characteristic trade: far less return, far less pain.

**Not evaluated on real SOL history yet**, and synthetic bars cannot tell you whether
the real series ranged or trended. That is the one thing that determines a grid's result.

## Caveats and limitations
- Grid results are dominated by whether the window contained a range or a trend, so a
  single-window backtest of a grid is close to meaningless.
- The venue minimum is \$10 per order, so a 7-rung ladder needs meaningful capital
  before it is even legal on Trigger V2.
- `expected_round_trip_usd()` is the invariant to check after any edit:
  gross must equal `notional x rung_width`.

## How to run
```bash
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
    --notional-per-rung 12 --levels
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
    --notional-per-rung 12 --synthetic 400 --capital 500
```
