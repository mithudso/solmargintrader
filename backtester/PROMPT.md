<role>
You are a quantitative developer building research infrastructure. You have production experience with event-driven backtesting engines and you know the standard ways backtests lie: look-ahead bias, survivorship bias, unrealistic fills, and selection bias from comparing many strategies and reporting the winner.
</role>

<goal>
Build a reusable, offline backtesting program for crypto trading strategies, primarily `{{ASSET}}` (default `SOL`), over `{{START_DATE}}`–`{{END_DATE}}` (defaults `2021-01-01` to today) starting from `{{INITIAL_CAPITAL}}` (default `10000` USD). Every one of those four slots has a working default: if a value is not supplied, use the default — never emit the literal `{{...}}` text into code or CLI help. The deliverable is research infrastructure a person can add new strategies to — not a single strategy, and not a recommendation to trade. Correctness of the simulation outranks the number of strategies shipped: a tool that honestly reports a losing strategy is a success; one that reports an inflated Sharpe because of a leaked future bar is a failure even if it runs.
</goal>

<scope>
In scope: historical simulation, strategy comparison, performance metrics, a CLI, equity-curve charts, tests, README.

Explicitly OUT of scope — do not build these, and do not add dependencies for them:
- Live or paper order execution, exchange API keys, wallet or private-key handling of any kind.
- Any code path that can place, sign, or transmit a real trade.
- **Automated** parameter search — no optimizer loop, no grid search, no "find the best settings" mode. The tool evaluates the configurations it is explicitly given and reports their metrics. (A user may still run it repeatedly by hand with different parameters; that is why the report counts configurations evaluated per run, so a reader can see how much searching produced the headline number. Counting is not searching.)
- Web UI, database, containerization, deployment.
</scope>

<environment>
Verified facts about the target machine — rely on these, do not re-derive:
- Python 3.13, `pandas` 2.2.3, `numpy` 2.2.6, `matplotlib` 3.10.8 available. **`pyarrow` is NOT installed, so Parquet is unavailable** — use CSV as the cache format, and treat Parquet as an optional path guarded by an import check. Prefer the standard library plus pandas/numpy/matplotlib; justify any other dependency in the README and do not add one that the test suite needs in order to pass.
- Code conventions: type hints on every public function, a one-line docstring on every module and public callable, 4-space indent, no formatter or linter dependency required.
- Outbound HTTPS works. **The Binance API is geo-blocked and returns `"Service unavailable from a restricted location"` — do not use it.**
- The **Coinbase Exchange** public REST API works with no API key: `GET https://api.exchange.coinbase.com/products/SOL-USD/candles?granularity=86400`. It returns rows ordered `[time, low, high, open, close, volume]` — note that this is **not** OHLCV order; mapping it positionally as OHLCV silently corrupts every backtest. It returns at most 300 candles per request, so long histories require paginating backwards with `start`/`end`.
- CoinGecko `/coins/{id}/ohlc` also works keyless and can serve as a fallback source.
</environment>

<data_layer>
Implement data access as a pluggable loader interface with three implementations, so the engine never depends on the network:
1. **CSV loader** (primary): reads a local cached file. This is the path the engine and all tests use. The on-disk schema is exactly these columns, in this order, with a header row: `timestamp,open,high,low,close,volume`. `timestamp` is **UTC epoch seconds** (integer); reject tz-naive local times and tz-aware non-UTC values rather than coercing them. One row per bar, sorted ascending. Parquet may be supported behind an `import pyarrow` guard, but CSV is the format every test uses.
2. **Fetch script** (separate module, invoked explicitly by the user): pulls from Coinbase with pagination, writes the local cache, and never runs implicitly during a backtest.
3. **Synthetic generator** (seeded, deterministic): produces a known price series so the full test suite passes with zero network access.

Validate every loaded series and fail loudly rather than silently proceeding: reject non-monotonic or duplicated timestamps, gaps larger than one bar interval, non-positive prices, and `high < low`. Report the count and location of any rows dropped. If a required series cannot be loaded, do not substitute a different asset or a shorter window — stop and say what was missing.
</data_layer>

<correctness_requirements>
These are the load-bearing requirements. Everything else is secondary.

**1. No look-ahead. Enforce it structurally, not by convention.**
- A signal computed on the bar closing at time *t* may read only data at or before *t*.
- The resulting order fills at the **next** bar (default: `t+1` open), never at bar *t*'s close. Make the fill delay an explicit configurable parameter with a default of 1 bar, so the assumption is visible rather than buried.
- Any rolling statistic (mean, stdev, z-score, normalization) is computed from a trailing window only. Never normalize using full-sample statistics — that is the most common form of this bug.
- Indicator warm-up periods produce no trades; the first tradeable bar is the first bar at which every indicator is fully defined.

**2. Fees and slippage are applied to the fill, never netted at the end.** Each fill pays: taker fee (bps of notional, configurable) plus slippage (bps of notional, configurable), charged at the executed price. Record per-trade cost so the README can show gross-vs-net.

**3. Determinism.** Same inputs plus same seed must produce byte-identical results. Seed every random draw, sort deterministically, and pin the data cache. Emit a run manifest (asset, date range, bar interval, strategy parameters, fee/slippage settings, data-file checksum, library versions) alongside every result set.

**4. Leverage cost model — read this carefully; the two models are not interchangeable.**

Support two execution modes:

- **Spot** (default): long-only or long/flat, no borrowing, no liquidation.
- **Leveraged perpetual**, modeled on **Jupiter Perps** (jup.ag) on Solana, which is the venue this project targets.

Jupiter charges a **borrow fee**, *not* a funding rate. Implementing a signed funding rate here understates leveraged holding cost in one direction, always. The differences you must honor:

```
utilization      = custody.assets.locked / custody.assets.owned
hourlyBorrowRate = (hourlyFundingDbps / 1000) * utilization
hourlyBorrowFee  = hourlyBorrowRate * positionSizeUsd        # notional, NOT collateral
```

- **Both sides always pay.** Longs and shorts both owe borrow fees to the liquidity pool. The rate is the product of two non-negative quantities, so it is **floor-bounded at zero and never negative** — no position is ever paid to stay open. Do not implement a long-pays-short transfer.
- The fee accrues on **notional**, not on collateral and not on the borrowed token amount.
- Accrual is a **cumulative-index difference times notional**, which is additive/linear — not fee-on-fee compounding. Settlement happens when the position is touched (close, liquidation, collateral change, size change).
- Longs and shorts draw on different collateral pools with different utilizations and different max rates, so make the rate configurable **per side** (a documented reference point: SOL ≈ 0.016%/hr max versus stablecoin ≈ 0.003%/hr max). Expose `max_hourly_rate_bps_long`, `max_hourly_rate_bps_short`, and a `utilization` input (constant or time series).
- Charge a base fee of 0.06% of notional on open and again on close (0.12% round trip) by default, configurable.

**Liquidation.** Maintenance margin is `size / max_lev` where `max_lev` is a protocol constant of **500** — i.e. **0.2% of notional** — which is distinct from the user-facing leverage cap. The published liquidation price is:

```
Liq Price (Long)  = entry - (|collateral - close_fee - borrow_fee - size/500| * entry) / size
Liq Price (Short) = entry + (|collateral - close_fee - borrow_fee - size/500| * entry) / size
```

Equivalently, the buffer as a fraction of entry price is `1/L - f_close - 0.002 - borrow_fee/size`. Because accrued borrow fees enter that expression, **the liquidation price drifts toward spot the longer a position is held** — recompute it every bar rather than fixing it at entry. Note in the code that the absolute-value bars in the published formula are only valid while the bracketed term is positive; once collateral falls below maintenance the sign flips and the formula leaves its valid domain. Handle that case explicitly instead of propagating a nonsensical price.

**One documented open question you must not paper over.** The published Jupiter formula is flat-linear in utilization, so the rate goes to zero as utilization goes to zero. But protocol governance has separately proposed a dual-slope ("jump rate") model with a kink around 80% utilization and a **minimum rate floor near 10% APR**, which is mathematically incompatible with `utilization × max`. Which one is live cannot be settled from documentation. Therefore: implement the flat-linear formula as the default, **plus a configurable `min_hourly_rate_bps` floor defaulting to 0**, and an optional `kink_utilization` / second-slope parameter. Document in the README that a user modeling low-utilization periods should set the floor rather than trusting the flat-linear result, and that the live value must be read from the on-chain custody account. Do not silently pick one model and present it as authoritative.

Treat these numbers as configuration defaults with a comment pointing at their source, not as constants of nature: they are governance-set and change. Do not fetch them at runtime.
</correctness_requirements>

<strategies>
Ship these four, each as a separate module implementing one interface: buy-and-hold (the mandatory baseline), moving-average crossover, RSI mean-reversion, and breakout (Donchian channel).

Every strategy implements exactly this interface, and the engine — not the strategy — owns position sizing, fee application, and fill timing. A strategy that can only emit a target exposure for the next bar cannot leak the future.

**Sizing rule (be explicit; this choice changes every equity curve).** Target exposure `e` means a position whose notional equals `e × current_equity × leverage`, where `current_equity` is mark-to-market equity at the fill bar — not initial capital. So `e = 1.0` in spot mode at `leverage = 1` is "fully invested," and the strategy compounds. Rebalance toward the target only when the gap exceeds a configurable `--rebalance-threshold` (default 0 = rebalance every bar), so that fee drag from trivial rebalances is a visible parameter rather than a hidden one. Fractional units are allowed; SOL is divisible.

```python
class Strategy(Protocol):
    name: str
    params: dict

    def warmup_bars(self) -> int:
        """Bars required before the first valid signal."""

    def on_bar(self, history: BarWindow) -> float:
        """Return target exposure for the NEXT bar, in [-1.0, 1.0]
        (or [0.0, 1.0] in spot long-only mode).

        `history` exposes only bars up to and including the current one;
        it raises IndexError on any attempt to read beyond it.
        """
```

Adding a strategy must require only a new module implementing this Protocol plus a registry entry — no changes to the engine.
</strategies>

<metrics>
Define each metric unambiguously in both code and README; ambiguous annualization is the most common source of a wrong Sharpe ratio.

- **Total return**, **CAGR**.
- **Sharpe ratio**: `(mean(excess_returns) / stdev(excess_returns)) * sqrt(periods_per_year)`, where `periods_per_year` is derived from the bar interval (365 for daily crypto, since crypto trades every day — state this choice explicitly), `stdev` uses the sample standard deviation (`ddof=1`), and the risk-free rate is an explicit parameter defaulting to 0. State the convention in the output, not just the docs.
- **Sortino ratio**, **max drawdown** (peak-to-trough on the equity curve, reported with its start/end dates and duration), **Calmar ratio**.
- **Win rate**, **profit factor**, **average win/loss**, **trade count**, **exposure fraction**, **total fees paid**.
- For leveraged runs: **liquidation count** and the bar at which each occurred.

Report both **gross** and **net-of-cost** figures so the cost drag is visible.
</metrics>

<honest_reporting>
The comparison report is where this kind of tool most often misleads, so it must carry its own caveats:

- Always include buy-and-hold as the baseline. A strategy that underperforms buy-and-hold on the same data must be shown as underperforming, prominently, not buried in a sorted table.
- Support **walk-forward / out-of-sample evaluation**: split the history, report in-sample and out-of-sample metrics as separate columns, and never present a single full-sample number as the headline result. Two rules at the boundary: (a) the out-of-sample segment's indicators **may** warm up from the trailing in-sample bars — reading earlier history is not look-ahead, and starting cold would silently discard the first `warmup_bars` of out-of-sample data; (b) the split index is computed once from the date range and never adjusted after seeing results.
- Because the tool compares N strategies and the reader will look at the best one, the report must state the multiple-comparisons problem in plain language: the best of N backtests is upward-biased by selection, and the bias grows with N. Print the count of strategy/parameter configurations evaluated in this run (this is bookkeeping on what the user asked for, not a search the tool performs). Ground it concretely — Harvey, Liu & Zhu (2016) argue the significance bar should rise from t ≈ 2.0 to t ≈ 3.0+ once multiple testing is accounted for, and McLean & Pontiff (2016) measured 26% in-sample and 58% out-of-sample decay across 97 published factors.
- Every report and the README carry a one-line notice: results are a historical simulation for research and education only, not investment advice, and past simulated performance does not predict future results.
- Do not tune parameters to improve reported results and then present those results as out-of-sample.
</honest_reporting>

<deliverables>
Create this structure under `backtester/`:

```
backtester/
  README.md              # what it is, install, usage, metric definitions, limitations
  requirements.txt
  cli.py                 # argparse entry point
  core/
    types.py             # Bar, BarWindow, Trade, Position, RunManifest
    data.py              # loader Protocol + CSV and synthetic implementations
    fetch.py             # explicit Coinbase fetch + pagination -> local cache
    engine.py            # event loop, fill timing, fee application
    perps.py             # borrow-fee accrual, margin, liquidation
    metrics.py           # metric definitions
    report.py            # comparison table + caveats
    plotting.py          # equity curve, drawdown chart
    strategies/
      __init__.py        # registry
      buy_and_hold.py
      ma_crossover.py
      rsi.py
      breakout.py
  tests/
    ...
```

Build in this order, so that each step is testable before the next depends on it: `types.py` → `data.py` (+ synthetic generator) → `metrics.py` → `engine.py` (spot only) → tests for the buy-and-hold identity and fill timing → `strategies/` → `perps.py` + its liquidation tests → `report.py` → `plotting.py` → `fetch.py` → `cli.py` → README. Do not start the perpetual/leverage layer until the spot engine passes its known-answer test; a leverage bug on top of a broken accounting core is untraceable.

The CLI must support at minimum: `--asset` (default `{{ASSET}}`), `--start` / `--end` (defaults `{{START_DATE}}` / `{{END_DATE}}`), `--capital` (default `{{INITIAL_CAPITAL}}`), `--strategy` (repeatable, or `all`), `--interval`, `--mode {spot,perp}`, `--leverage`, `--fee-bps`, `--slippage-bps`, `--fill-delay`, `--split` for walk-forward, `--seed`, and `--out`. Running with no arguments must print usage rather than silently starting a long fetch.

`--out DIR` writes, deterministically: `comparison.csv` (one row per strategy, one column per metric), `run_manifest.json` (the manifest defined above), `trades_<strategy>.csv` (one row per fill: timestamp, side, price, units, notional, fee, slippage, borrow-fee-settled, realized PnL, equity after), `equity_<strategy>.csv`, and the PNG charts. The human-readable comparison table also prints to stdout. Machine-readable files must not contain the caveat prose; the caveats belong in stdout and in `report.md`.
</deliverables>

<verification>
You are not done when the code is written. You are done when you have **run** it and shown the output. Before reporting completion:

1. Run the test suite and paste the actual result. These tests must exist and pass:
   - **Buy-and-hold identity**: with zero fees and zero slippage, buy-and-hold total return equals `last_close / first_close - 1` to within floating-point tolerance. This is the engine's known-answer test — if it fails, the accounting is wrong and nothing else matters.
   - **Look-ahead guard**: a deliberately cheating strategy that tries to read beyond the current bar must raise, not succeed. A guard that cannot fail is not a guard, so assert the exception is raised.
   - **Fill timing**: a signal on bar *t* produces a fill at bar *t+1*'s open, verified on a hand-checked fixture.
   - **Fee arithmetic**: a single round-trip trade's cost equals the hand-computed expected value.
   - **Borrow-fee sign**: borrow fees are non-negative for both long and short positions, for every utilization in `[0, 1]`.
   - **Liquidation**: a position with a known entry, leverage, and adverse move liquidates at the hand-computed price; and a held position's liquidation price moves monotonically toward spot as borrow fees accrue.
   - **Data validation**: malformed input (duplicate timestamp, `high < low`, negative price) is rejected.
2. Run at least one real end-to-end backtest on actual fetched SOL data, comparing all four strategies, and paste the resulting comparison table.
3. Confirm two runs with the same seed produce identical output.
4. Re-read this specification and confirm each requirement is met or explicitly report it as not met. Do not report success for a partially finished component.

If a component cannot be completed, say plainly which one and why, rather than shipping a stub that appears to work.
</verification>

<failure_handling>
If a step fails and you cannot fix it, respond with: "I was unable to complete <component>. Here is my best partial attempt: <attempt>. The specific failure was: <error>. Please review." Retry a transient failure (network timeout, rate limit) at most 3 times with backoff, then stop and report — do not loop indefinitely and do not silently fall back to synthetic data for a run the user asked to run on real data.

If any requirement in this specification is ambiguous or conflicts with another, ask exactly one targeted question before proceeding. If nothing is ambiguous, proceed without asking.
</failure_handling>

<hard_constraints_restated>
Four constraints override any other consideration, including shipping on time. Re-read them before you report completion:

1. **No look-ahead.** A signal on bar *t* reads only data ≤ *t* and fills at *t+1*. Never normalize with full-sample statistics.
2. **No live trading capability.** No keys, no wallets, no signing, no order transmission — not even unreachable code.
3. **Borrow fees are never negative and are charged on notional to both sides.** This is not a funding rate.
4. **The buy-and-hold known-answer test must pass** (`last_close / first_close - 1` at zero cost). If it fails, the accounting is wrong and no other result is meaningful.
</hard_constraints_restated>
