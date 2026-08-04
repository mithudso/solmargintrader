# SOL Crypto Strategy Backtester

An offline, event-driven backtesting harness for crypto trading strategies,
built around SOL. Supports unlevered **spot** and **Jupiter-Perps-style
leveraged perpetuals** with a correctly-modelled borrow fee.

> **Historical simulation for research and education only. NOT investment
> advice, and not a recommendation to trade anything.** Simulated past
> performance does not predict future results. Leveraged perpetuals can lose
> your entire collateral. There is no live-trading capability in this codebase
> and none should be added — see [Scope](#scope).

## Why this exists

The ask was "backtest different crypto trading strategies, primarily SOL." The
hard part of that is not running strategies; it is running them *honestly*. A
backtester that is 20 lines shorter and silently leaks one future bar will
report a beautiful Sharpe ratio and lose money in production. So the design
priority here is: **correctness of the simulation outranks the number of
strategies shipped.** A tool that honestly reports a losing strategy is a
success; one that reports an inflated Sharpe because of a leaked bar is a
failure even if it runs.

## Install

```bash
cd /Users/mitch.hudson/dev/solmargintrader
pip install -r backtester/requirements.txt   # pandas, numpy, matplotlib
```

Python 3.13. `matplotlib` is optional (charts degrade to "skipped"); `pyarrow`,
`requests`, and `pytest` are deliberately **not** required.

## Usage

Fetch data once, then backtest from the local cache. The engine never touches
the network.

```bash
# 1. Populate the local CSV cache from the Coinbase public API (no key needed)
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01

# 2. Compare all strategies, with a 70/30 walk-forward split
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/

# 3. Leveraged perpetual run
python3 -m backtester.cli --asset SOL --mode perp --leverage 10 \
    --strategy breakout --start 2024-01-01

# Offline demo with no data file at all
python3 -m backtester.cli --synthetic 800 --strategy all
```

Run with no arguments to print usage. `python3 -m backtester.cli --help` lists
every flag.

### Key flags

| Flag | Meaning |
|---|---|
| `--mode {spot,perp}` | Unlevered spot, or Jupiter-style perpetual |
| `--leverage N` | Perp leverage. Spot rejects anything but 1 |
| `--fill-delay N` | `0` = fill at this bar's close; `N` = fill at open of bar *t+N*. **Default 1** |
| `--fee-bps` / `--slippage-bps` | Per-fill costs, charged on notional |
| `--split F` | Walk-forward in-sample fraction, e.g. `0.7` |
| `--rebalance-threshold F` | Deadband before rebalancing, as a fraction of equity |
| `--borrow-bps-long/short` | Max hourly borrow rate, bps (`1.6` = 0.016%/hr) |
| `--utilization U` | Pool utilization in `[0,1]`, drives the borrow rate |
| `--min-borrow-bps` | Hourly rate floor — models the *proposed* dual-slope minimum |
| `--seed N` | Recorded in the manifest; runs are deterministic |

## Output

`--out DIR` writes deterministically:

| File | Contents |
|---|---|
| `comparison.csv` | One row per strategy per book (`net`, `gross`), one column per metric |
| `run_manifest.json` | Asset, range, params, costs, data checksum, library versions |
| `trades_<strategy>.csv` | One row per fill, with fee, slippage, borrow settled, realized PnL |
| `equity_<strategy>.csv` | Per-bar equity and signed exposure |
| `report.md` | The human-readable report, including caveats |
| `equity_comparison.png`, `exposure.png` | Charts |

Machine-readable files carry no caveat prose, so a downstream consumer never
has to parse around it. The caveats live in stdout and `report.md`.

## How look-ahead bias is prevented

Structurally, not by convention. The per-bar ordering is:

1. accrue borrow fees for the elapsed bar (perp only)
2. execute any fill scheduled for this bar, **at this bar's open**
3. liquidation check against this bar's low/high (perp only)
4. ask the strategy for a target, **given data ≤ *i* only**
5. schedule that target for bar *i + fill_delay*
6. mark to market at this bar's close

A strategy receives a `BarWindow`, whose every accessor returns `arr[:i+1]`.
There is no unguarded path to the underlying arrays, so a strategy reaching for
`closes[i+1]` gets an `IndexError` rather than tomorrow's price. `tests/`
includes a deliberately-cheating strategy and asserts that it raises — a guard
that cannot fail is not a guard.

Also enforced: rolling statistics use trailing windows only (never full-sample
normalization, the most common form of this bug); indicator warm-up produces no
trades; and fees/slippage are charged on the fill, never netted at the end.

## The leverage cost model — a borrow fee, *not* a funding rate

This is the single most important thing to get right about Jupiter Perps, and
it is where a generic perp backtester goes wrong.

```
utilization      = custody.assets.locked / custody.assets.owned
hourlyBorrowRate = max_hourly_rate * utilization
hourlyBorrowFee  = hourlyBorrowRate * positionSizeUsd     # notional
```

* **Both sides always pay.** Longs and shorts both owe fees to the liquidity
  pool. There is no long-pays-short transfer, and no position is ever *paid* to
  stay open. The rate is a product of two non-negative quantities, so it is
  floor-bounded at zero. Porting funding-rate intuition here understates
  holding cost in one direction: always too low.
* The fee accrues on **notional**, not collateral and not units.
* Accrual is an index difference × notional — **additive, not fee-on-fee**.
  What feels like compounding is second-order: fees erode collateral,
  effective leverage rises, and the liquidation price drifts toward spot.
* Longs borrow volatile custody, shorts borrow stable custody, so the two sides
  take **separate rates** (`1.6` vs `0.3` bps/hr by default).

Rates are configured in **bps per hour** to sidestep the deci-bps ambiguity in
the venue docs: `1.6 bps/hr == 0.016%/hr == ~140% APR`, the documented SOL
reference point.

### Liquidation

Maintenance margin is `size / max_lev` where `max_lev` is a **protocol constant
of 500** — i.e. **0.2% of notional** — which is *not* the user-facing leverage
cap. The buffer as a fraction of entry price is:

```
buffer = 1/L - f_close - 0.002 - borrow_fee/size
```

| Leverage | Buffer at t=0 |
|---|---|
| 10× | 9.74% |
| 100× | 0.74% |
| 250× | 0.14% |

Because accrued borrow fees appear in that expression, **the liquidation price
drifts toward spot the longer you hold** — it is recomputed every bar, not
fixed at entry. Liquidation fills at the liquidation price and checks the
intrabar wick, so a bar that spikes through your level and recovers still
liquidates you.

The published formula's `abs()` bars are only valid while the bracketed term is
positive; past that the sign flips and the formula leaves its domain. That case
is flagged (`in_domain=False`) rather than propagated as a plausible price.

### One open question, not papered over

The published borrow formula is flat-linear in utilization, so the rate → 0 as
utilization → 0. But protocol governance separately proposed a **dual-slope
("jump rate") model with a kink near 80% utilization and a minimum floor around
10% APR**, which is mathematically *incompatible* with `utilization × max`.
Which is live cannot be settled from documentation.

So: flat-linear is the default, and `--min-borrow-bps` / `--kink-utilization`
let you model the proposed alternative. **If you are modelling low-utilization
periods, set the floor rather than trusting the flat-linear result, and read
the live value from the on-chain custody account.** All rate constants here are
governance-set configuration defaults, not constants of nature.

## Metric definitions

Ambiguous annualization is the most common source of a wrong Sharpe ratio, so:

* **Sharpe** = `mean(excess) / stdev(excess, ddof=1) × sqrt(periods_per_year)`.
  `periods_per_year` derives from the bar interval using a **365-day crypto
  year** (crypto trades every day — not 252). `stdev` is the **sample**
  standard deviation. The risk-free rate is an explicit parameter defaulting
  to 0. This convention is printed in every report, not just documented here.
* **Sortino** — same, against downside deviation.
* **Max drawdown** — peak-to-trough on the equity curve, reported with start
  date, end date, and duration in bars. Negative fraction (`-0.42` = −42%).
* **Calmar** = CAGR / |max drawdown|.
* **Profit factor** — gross wins / gross losses. Reported as `inf` when there
  are no losing trades; that is information, not an error.
* **Win rate / trade count** — over *closing* fills only. An opening fill has
  no outcome yet, so counting it would dilute the rate.
* **Exposure fraction** — mean |signed notional / equity|.
* Every run reports **gross** (zero-cost) alongside **net**, from a parallel
  book that mirrors each decision, so cost drag can't drift out of sync.

## Honest reporting

The comparison report is where a tool like this most easily misleads, so it
carries its own caveats:

* **Buy-and-hold is always included** as the baseline, and is added
  automatically if you leave it out. Underperformance against it is stated
  plainly, not buried in a sorted table.
* **Walk-forward** reports in-sample and out-of-sample as separate columns. The
  out-of-sample slice starts `warmup_bars` early so indicators warm from
  trailing in-sample bars — reading earlier history is not look-ahead, and
  starting cold would silently discard real out-of-sample data.
* **The multiple-comparisons warning is printed with the ranking.** The best of
  N backtests is upward-biased by selection, and the bias grows with N.
  Harvey, Liu & Zhu (2016) argue the significance bar should rise from t ≈ 2.0
  to **t ≈ 3.0+** once multiple testing is accounted for. McLean & Pontiff
  (2016) measured **26% in-sample and 58% out-of-sample decay** across 97
  published factors. The report prints how many configurations were evaluated.

### What the real data actually showed

On 1,875 real SOL daily bars (2021-06-17 → 2026-08-04), spot, 6bps fee + 2bps
slippage, 70/30 walk-forward:

| Strategy | Full-sample return | In-sample | **Out-of-sample** |
|---|---|---|---|
| buy_and_hold | +87.6% | +565.2% | **−70.8%** |
| ma_crossover_20_50 | +298.3% | +735.6% | **−52.3%** |
| rsi_14_30_50 | −15.7% | −9.6% | **−21.9%** |
| breakout_20_10 | +620.7% | +860.2% | **−7.5%** |

Read that table before trusting any full-sample number, here or anywhere. Every
strategy looked excellent in-sample and lost money out-of-sample. The
full-sample column is dominated by one enormous bull run inside the in-sample
window. This is the tool working correctly — it is *supposed* to make that
visible rather than hide it behind a ranked Sharpe leaderboard.

**Leveraged runs are worse, and the reason is the borrow fee.** A 10× long from
2024-01-01 goes to −100% with 26 liquidations, and the cost breakdown is
\$722 of borrow fees against only \$211 of trading fees — carry, not churn, is
what kills it. At 3× with a 15% rebalance deadband, borrow fees reach **\$10,023
on \$10,000 of starting capital** over ~580 days. That is the documented venue
behaviour, not a modelling artifact: this is a venue built for short holding
periods, and its fee structure actively penalises carrying a position.

## Adding a strategy

Implement the Protocol and add one registry entry. No engine changes.

```python
# core/strategies/my_strategy.py
from ..types import BarWindow

class MyStrategy:
    def __init__(self, lookback: int = 30) -> None:
        self.name = f"my_strategy_{lookback}"
        self.params = {"lookback": lookback}
        self.lookback = lookback

    def warmup_bars(self) -> int:
        return self.lookback

    def on_bar(self, history: BarWindow) -> float:
        """Target exposure for the NEXT bar, in [-1, 1]."""
        closes = history.closes          # only bars <= now
        return 1.0 if closes[-1] > closes[-self.lookback:].mean() else 0.0
```

Then in `core/strategies/__init__.py`:

```python
REGISTRY["my_strategy"] = MyStrategy
```

The engine — not the strategy — owns position sizing, fee application, and fill
timing. A strategy that can only emit a target exposure for the next bar cannot
leak the future.

**Sizing rule:** target exposure `e` means notional of
`|e| × current_equity × leverage`, marked at the fill price. Current equity,
not initial capital — so strategies compound.

## The ladder grid — backtesting what the extension actually trades

There are two different things called "grid" in this repo, and conflating them
would put a wrong number under the strategy that runs live:

| | What it is | Where |
|---|---|---|
| `grid` (`GridLong`) | An **exposure staircase**: exposure rises one rung per `step` below a rolling SMA anchor. A `Strategy` like any other, filled at a bar boundary. | `core/strategies/signals.py`, run via `backtester.cli` |
| **ladder grid** | A **ladder of resting limit orders** with paired exits one rung above each lot — the extension's strategy. Fills intrabar at known prices. | `core/gridsim.py`, run via `backtester.gridcli` |

`GridLong` can imitate a grid's *position profile*, but it can never capture a
rung width, because it never has an order sitting at a level waiting to be hit.
That capture is the entire economic engine of a real grid, so it needs its own
simulator rather than a `Strategy` returning one target exposure per bar.

```bash
# The ladder and what it costs to fund, without running anything
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
    --notional-per-rung 12 --levels

# A run on cached bars, or offline on synthetic ones
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
    --notional-per-rung 12 --interval 1h
python3 -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
    --notional-per-rung 12 --synthetic 400 --capital 500 --json
```

`core/gridsim.py` ports `extension/src/core/grid.js` function for function —
geometric/arithmetic spacing with pinned endpoints, top-rung extrapolation,
paired exits, the deadband, the $10 venue minimum, FIFO realization. Divergence
between the two would be worse than having no grid backtest at all, so
`rung_width_bps` is asserted against figures read off the JavaScript
implementation (699.1319 bps for a 60–90/7 ladder; 516.7 bps for the 0.85×–1.15×
ladder `tools/dryrun.js` builds).

**Three conventions keep it pessimistic**, because an optimistic grid simulator
makes a losing grid look profitable:

1. **An order cannot fill on the bar that planned it.** Planning happens at a
   bar's close, so the earliest fill is the next bar. This is the no-lookahead
   guard and it also makes a same-bar round trip impossible — "price dipped to
   the bid then rallied to the offer" is an assumption about the intrabar path,
   not an observation of it.
2. **Fills are adverse.** A buy fills at its level moved up by the full slippage
   allowance, a sell at its level moved down by it.
3. **Buys settle before sells**, so cash freed by a sell cannot fund a buy in the
   same bar.

FIFO is additionally bounded to lots opened *before* the current bar. Without
that bound, two exits filling in one bar let the second reach inventory bought
that same bar — an indirect same-bar round trip. It fired on synthetic data
during development, so the bound is load-bearing rather than theoretical; when
old inventory runs short the exit fills partially and the remainder is re-planned.

**Read per-round-trip gross carefully.** The planner pairs each exit to a
specific lot while realization matches FIFO, so with several rungs open the two
disagree per trip — an exit meant to close a cheap lot is matched against an older
expensive one, and gross per trip comes in below the nominal rung width.
Portfolio totals are identical either way. The extension documents the same
divergence; `test_pairing_and_fifo_disagree_per_trip_but_not_in_total` pins it.

Carry defaults to **0 bps/hr** because Trigger V2 is a spot venue with no borrow
leg — not because carry is free. `--carry-bps-per-hour` models a borrowed-margin
ladder, and the rate is echoed in the output so a run can never quietly claim a
cost structure it did not use.

Every run prints a buy-and-hold baseline on the same bars, paying entry costs
once. A grid that underperforms holding the asset has not earned its complexity.

## Tests

```bash
python3 -m unittest discover -s backtester/tests -t . -v
```

122 known-answer tests, no network required. The load-bearing ones:

| Test | Known answer |
|---|---|
| Buy-and-hold identity | Total return `== last_close/first_close − 1` at zero cost, to 12 dp |
| Look-ahead guard | A cheating strategy **raises** |
| Fill timing | Signal at bar *t* fills at bar *t+1*'s open |
| Fee arithmetic | Round-trip cost equals the hand-computed value |
| Borrow-fee sign | Non-negative for both sides at every utilization in `[0,1]` |
| Liquidation | Entry 100, 10×, zero borrow → **90.26** (matches venue docs) |
| Liquidation drift | Buffer shrinks monotonically as borrow fees accrue |
| Data validation | Duplicate/gap/negative/NaN/millisecond input is rejected |
| Determinism | Two runs produce identical output |
| Ladder round trip | Gross `== notional × rung width`, to 9 dp — the same contract the extension asserts |
| Ladder rung width | Matches the JavaScript `rungWidthBps` to 3 dp |
| Ladder same-bar guard | A bar spanning entry and exit books the entry only |
| Ladder first bar | A bar-0 sweep of the whole ladder fills nothing |
| Ladder downtrend | Every bid fills, no round trips, final equity below capital |
| Ladder cash limit | An unfundable rung is skipped, equity never negative |
| Ladder book identity | At zero cost, final equity `== capital + realized P&L` |

## Scope

**Out of scope, deliberately.** No live or paper order execution, no exchange
API keys, no wallet or private-key handling, and no code path that can place,
sign, or transmit a real trade. No automated parameter search — the tool
evaluates the configurations it is given and reports their metrics; sweeping
for a winner is exactly the overfitting this harness exists to expose. (You can
still run it repeatedly by hand, which is why the report counts configurations
evaluated. Counting is not searching.)

## Known limitations

* **Single asset per run.** No cross-sectional universe, so no survivorship
  bias — but also no portfolio-level analysis.
* **Bar-resolution fills.** No order book, no partial fills, no queue position.
  Slippage is a flat bps assumption, which understates cost in a crash.
* **Utilization is an input, not a history.** Real Jupiter utilization varies;
  a constant is a modelling simplification. Governance has documented SOL
  utilization sitting at 100% for sustained periods, which more than doubles
  the borrow cost versus the 0.5 default.
* **Oracle execution is not modelled.** Jupiter is oracle-priced peer-to-pool
  with keeper fulfilment and no FIFO guarantee; a stop can lose the race to a
  liquidation. This harness assumes your stop/target logic executes.
* **Liquidation ignores the price-impact fee** a real liquidation would incur,
  so it is still mildly optimistic — but it does fill at `min(level, bar_open)`
  for longs, so a bar that *gaps* through your level fills at the open rather
  than at a price that never traded.
* **Resize costs assume the venue's merge semantics** — a same-side size change
  pays the base fee on `|Δnotional|` and blends the entry price, rather than
  paying a synthetic round trip. If you point this at a venue that really does
  charge a full round trip per adjustment, leveraged costs here are too low.
* **No funding-rate mode.** By design — this models Jupiter's borrow fee. Do
  not repurpose it for a CEX perp without adding a signed funding model.

## Provenance

The specification this was built from is in `PROMPT.md`, produced by running
the deep prompt optimizer over the original one-line request. The venue
mechanics (borrow-fee formula, maintenance-margin constant, liquidation
formula) and the backtesting-statistics citations trace to the
`trading-and-investing` skill references, verified as of 2026-08-03. **Volatile
protocol values change — verify against the live on-chain custody account
before relying on them.**
