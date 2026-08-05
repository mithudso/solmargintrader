# Components

What each module is for, what it exposes, and what it depends on. `docs/codebase-overview.md`
is the flat file map; this page is the shape of the thing.

Dependency direction, strictly one-way:

```
extension/  (JavaScript)          soltui/  (Python)
     |                                 |
     | ports grid economics            | reads
     v                                 v
backtester/core/gridsim.py <---- backtester/  <---- research/
```

`backtester/` depends on nothing else in the repo. `research/` imports `backtester`.
`soltui/` reads the research side. `extension/` shares no code with any of them — only an
obligation, described below.

---

## `backtester/`

### `core/engine.py` — the bar loop

The single place execution ordering is decided, and the reason lookahead is structurally
impossible rather than merely avoided. Per bar, in this order: accrue borrow fees, execute
a fill scheduled for this bar at this bar's **open**, check liquidation against this bar's
range, ask the strategy for a target using data `<= i` only, then schedule the resulting
order for `i + fill_delay`.

```python
run_backtest(strategy, arrays, config) -> BacktestResult
```

`EngineConfig` carries mode, leverage, `fill_delay` (default 1 — the conservative choice),
`rebalance_threshold` and costs. `BacktestResult.exposure` is the **applied** exposure
(signed notional over equity), not the raw target — a distinction that matters to anything
comparing against it.

**Depends on:** `types`, `metrics`, `perps`. No I/O, no network.

### `core/types.py` — the lookahead guard

`BarWindow` is the guard. A strategy receives only this object, every accessor truncates at
bar `i`, and reading past `i` raises `LookAheadError`. Also `CostConfig` (fees, slippage,
borrow rates in **bps per hour** to sidestep the venue's deci-bps ambiguity), `Position`,
`Trade`, and `RunManifest` — everything needed to reproduce a run byte-for-byte.

### `core/strategies/` — the registry

```python
REGISTRY: dict[str, Callable]   # 25 strategies, name -> factory
FAMILY: dict[str, str]          # taxonomy: trend, mean-reversion, regime-filter, ...
build(name, **params) -> Strategy
```

Factories rather than instances, because several strategies carry state and a shared
instance would leak position state between runs. A strategy implements
`warmup_bars()` and `on_bar(history) -> float`, returning a target exposure in `[-1, 1]`
for the **next** bar.

Adding one requires a module plus one `REGISTRY` entry — no engine change — **and** a
`strategy_cards/<id>.md` in the same commit, whose machine-readable half is checked against
the code in both directions.

### `core/indicators.py`

Trailing-window functions, each returning a scalar for the current bar rather than a
series — strategies are called once per bar, so a series would be wasted work and would
invite indexing the wrong position. Exponential recursions use a capped lookback
(`EMA_CAP_MULTIPLE = 12`, chosen for a measured 2.4e-13 relative error) and a smaller
warm-up multiple (`EMA_WARMUP_MULTIPLE = 3`).

### `core/gridsim.py` — the ladder grid

Separate from the exposure engine and deliberately so: the extension's edge comes from
limit orders filling *intrabar* at known prices, which a target exposure cannot express.
Own bar loop, own entry point (`backtester.gridcli`).

**This module is a port of `extension/src/core/grid.js`.** A change to either one's
economics needs the matching change in the other, or the backtest becomes a confident
wrong number about the live strategy. Do not confuse it with the `grid` strategy in
`core/strategies/signals.py`, which is an exposure staircase, not a ladder of resting
orders.

### `core/data.py` and `core/fetch.py`

`CsvLoader` and `SyntheticLoader` both satisfy one `DataLoader` protocol, so tests need no
network. `validate_bars` checks schema, ordering and gaps; `checksum_frame` makes a run
traceable to its input. `fetch.py` is the only network path and writes a cache — the engine
never fetches.

---

## `research/`

### `decide.py` — the per-bar readout

What every strategy, signal and indicator says about the last cached bar.

```python
replay_targets(strategy, arrays, *, mode, allow_short) -> np.ndarray
decide_strategy(key, arrays, ...) -> StrategyDecision
build_report(arrays, *, asset, interval, ...) -> dict
```

Strategies are replayed bar-by-bar from the start of history, because several are
path-dependent: a Donchian position opened on a breakout stays long through bars whose own
close would never have opened it. It imports the engine's own `_resolve_target` rather than
reimplementing the clamp, and its test suite asserts parity against a recording wrapper
around `run_backtest`.

### `cpcv_sweep.py` — and why `interpret()` exists

Combinatorial purged cross-validation over the strategy space. `interpret()` turns four
numbers into the reading a person should take from them, specifically to catch two
dangerous misreadings: a high positive-count with a high PBO ("lots of strategies work!"),
and a low PBO with a low positive-count. It has its own test file.

### `verify_numbers.py`

Re-derives every figure quoted in the research documents. Exit 0 means the prose matches
the code. This is the component's honesty gate — `research/`'s failure mode is overstating
a result, and this is what makes that detectable.

---

## `extension/`

### `src/core/commands.js` — one registry, three surfaces

Every action lives here. The Chrome message handler, `tools/cli.js` and
`tools/api-server.js` are thin adapters over it, and `test/surfaces.test.js` fails the
build if any surface drifts. Do not add a handler, CLI branch or HTTP route carrying its
own logic.

### `src/core/risk.js` — the rails

Every rail is a gate an order must pass. Two properties matter more than the list: a rail
documented but not enforced here is not a rail, and rails **fail closed** — a missing or
NaN state field must not silently disable one (see `normaliseState`).

### `src/core/engine.js` — reconcile, then plan

The venue's live order list is the source of truth at the top of every tick; local state is
a cache. An intent submitted but not found live becomes `unknown` and is **never**
auto-retried — that is exactly how a rung double-fires after a crash.

### `src/core/grid.js` and `pnl.js`

Ladder geometry and FIFO/paired-lot attribution. `grid.js` owns `expectedRoundTripUsd`,
which exists because the "exit at the level you bought at" bug shipped once: it captures
zero and pays two fees. Both files stay free of I/O and `chrome.*`.

### `src/jupiter/http.js`

The single HTTP layer: 4 attempts, full-jitter exponential backoff, a token-bucket request
budget charged **per attempt** so a retry storm cannot bypass it, 15s per-attempt timeout.
See `docs/external-calls.md`.

### `src/storage/`

Three implementations of one interface — `store.js` (IndexedDB: intents, fills, carry,
events), `fileStore.js` (mode-0600, for secret material), `memoryStore.js` (tests). The
intent journal is what makes the bot restart-safe: an intent is written before it is
submitted.

### `src/wallet/solana.js`

~150 lines that make a Solana dependency unnecessary, including the base58 zero-byte case.
Do not add a package to solve what this already solves.

---

## `soltui/`

macOS menu-bar app plus a TUI. Read-only over the research side; places no orders.

- `app.py` is the menu-bar app; `tui.py` the terminal UI; `signals.py`, `status.py`,
  `roster.py`, `paper.py` the display model.
- `menubar_launcher.py` exists because py2app runs its target as a top-level script, which
  breaks relative imports — and because a Finder or launchd launch starts at `/`, so it
  `chdir`s to the repo before `data_dir="data"` is resolved.
- `setup_app.py` is an **alias** build, so the bundle references this checkout and must be
  rebuilt if the repo moves. Never install a bundle built from a worktree — the worktree
  gets deleted and login startup breaks silently.
- `soltui-service` is the operational surface: `status`, `start`, `stop`, `build`,
  `install`.
