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
evaluation: real-sol-daily-and-hourly-recentred-blocks
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
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

## Measured on real SOL

Previously this card said "not evaluated on real SOL history yet". It has now been run on
both real series — `research/results/ladder_grid_sol.csv`.

**The ladder bounds are the whole experiment**, and choosing them after seeing the data
would make any result meaningless. So they come from the extension's own pre-registered
convention in `tools/dryrun.js`: **0.85x to 1.15x of the current price, 7 rungs,
$12/rung**. Capital is twice the funding requirement, and P&L is reported against
*deployed* capital, the same denominator `extension/README.md` uses.

### One static ladder for the whole series — the naive configuration

| | SOL daily (1,875 bars) | SOL hourly (8,823 bars) |
|---|---|---|
| Ladder | $33.36–$45.14 | $144.71–$195.79 |
| Round trips | 68 | 36 |
| Realized on $72 deployed | **+$7.51 (+10.4%)** | **−$14.37 (−20.0%)** |
| **Bars outside the ladder** | **93.1%** | **86.0%** |
| Grid return / max drawdown | +5.21% / **−11.46%** | −9.98% / −18.68% |
| Hold return / max drawdown | +88.25% / **−96.27%** | −57.12% / −75.80% |

**The dominant fact is the 93%.** A static ladder set once is out of range almost all the
time — SOL went $39 → $262 → $74, and a $33–45 ladder simply stops being a market. The
drawdown comparison is the honest case *for* it: −11.46% against holding's −96.27%.

### Re-centred each block — the realistic configuration

Eight blocks, ladder reset from each block's first close. This is how a person actually
runs a grid, and it produces a distribution instead of one number.

| | SOL daily | SOL hourly |
|---|---|---|
| Median P&L on deployed capital | **+7.5%** | −1.2% |
| Blocks positive | 5 of 8 | 3 of 8 |
| Beat buy-and-hold | 4 of 8 | **6 of 8** |
| Median buy-and-hold over same blocks | −1.2% | −16.1% |
| Worst block | **−22.5%** | −13.8% |
| Bars outside the ladder | 48.7%–89.3% | 0.0%–82.8% |

The worst daily block is the documented failure mode arriving on schedule: a $28–38
ladder while SOL fell 39%, ending **−22.5% of deployed capital** with the position at
maximum size. That is within a couple of points of the extension's own dry-run figure
(−$8.62 on $48 deployed, −18%), which is a useful cross-check that the simulator and the
live engine agree.

### The product finding

**The extension does not re-centre.** `planGrid` reads `lower` and `upper` straight from
config and nothing recomputes them, so a live install behaves like the *static* column
above — out of range 86–93% of the time — rather than the re-centred one that produced
the positive daily median. The gap between those two columns is the value of a feature
that does not exist yet.

## Likelihood of success: low

*Basis: measured-oos, on real SOL for the first time. There is no 'high' rating in this
scheme — across 311 rankable configurations, 14% had a positive out-of-sample Sharpe and
9% made money.*

The case **for** it is the drawdown, and it is real. Re-centred each block on daily bars
it made a **median +7.5% of deployed capital with 5 of 8 blocks positive**, while
buy-and-hold's median over the same blocks was −1.2%; on hourly it beat holding in **6 of
8** blocks. The static single-ladder run cut max drawdown from **−96.27% to −11.46%**.
That is what a short-volatility strategy is supposed to look like: much less return, much
less pain.

Four things hold it at low.

1. **Out of range 86–93% of the time** with a static ladder. Most of the life of a
   deployed grid is spent with nothing to do, which means the returns above are earned in
   a small fraction of bars and the capital is idle in the rest.
2. **The trend failure mode arrived on schedule.** The worst daily block lost **22.5% of
   deployed capital** with the position at maximum size — the mechanism converting a trend
   into a large losing position, exactly as the card predicted before it was run.
3. **Hourly is negative** (median −1.2%, 3 of 8 blocks positive). Beating a −16.1% hold is
   not the same as making money.
4. **The positive result depends on a feature that does not exist.** The daily median is
   the *re-centred* configuration; the extension is static, so a live install gets the
   other column.

And the standing constraint that outranks all of it: **no live order has ever been
placed**, the Trigger order-list envelope is still unverified, and fee attribution is
still unconfirmed. A backtest cannot tell you what the venue will actually fill.

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
