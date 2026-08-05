# Every file in this repository

**Generated** from `index/INDEX.json` at commit `5a4f436` (2026-08-05T17:16:25+00:00). 267 tracked files, 3.6 MB.

Regenerate with:

```bash
python3 index/build.py all          # refresh the index
python3 index/make_files_doc.py     # rewrite this file
python3 index/build.py --check      # fail if the index is stale
```

## How to read an entry

Every entry marks where its description came from, because a generated one-liner and a considered one should not look alike:

- **curated** (42 files) — hand-written purpose and usage, in the `CURATED` table of `index/make_files_doc.py`. Used where extraction cannot give a reader what they need: the engine, the research drivers, the order-placing path, and the files with no prose of their own.
- **extracted** — the file's own module docstring, JSDoc header, or frontmatter `summary`. Trustworthy here because 63 of 67 Python modules and all 27 JS files carry a substantial one.
- **derived** — shape only, for generated artifacts: a CSV's header and row count, a JSON's keys. Prose for a result file would be invented.

*How to use* is curated where it matters and otherwise inferred from the file's kind — a test gets its runner, a CLI gets `--help`, a module gets its import path.

## Related documents

This file is the **exhaustive** one: every tracked file, no exceptions, regenerated from the index. For orientation rather than lookup, read these first — they are shorter and they explain *why* the pieces fit together:

- `docs/codebase-overview.md` — the narrative tour.
- `docs/ARCHITECTURE.md` — how the three components relate.
- `docs/COMPONENTS.md` — component-level responsibilities.
- `docs/CONCEPTS.md` — the conceptual index: which files bear on which idea.

To *search* rather than browse: `python3 index/search.py "your question"`.

## Contents

- [`(root)`](#root) — 9 files
- [`docs`](#docs) — 18 files
- [`index`](#index) — 5 files
- [`backtester`](#backtester) — 93 files
- [`research`](#research) — 77 files
- [`extension`](#extension) — 33 files
- [`soltui`](#soltui) — 20 files
- [`.github`](#github) — 8 files
- [`tradingskilllist`](#tradingskilllist) — 1 files
- [`.remember`](#remember) — 1 files
- [`scripts`](#scripts) — 2 files

---

## (root)

Repository-level entry points and agent instructions. `AGENTS.md` and `CLAUDE.md` are the operative rules for anyone — human or agent — changing this repo; read them before the code.

9 files.

#### `.editorconfig`

`other` · 24 lines · 324 B · description: **curated**

**Purpose.** Baseline whitespace and encoding rules so diffs stay about content.

**Use.** Nothing to run; editors apply it automatically.

#### `.gitattributes`

`other` · 28 lines · 744 B · description: **curated**

**Purpose.** Per-path git behaviour: line-ending normalisation, and which files are treated as binary or excluded from diffs and archives. Keeps a CSV or a generated artifact from producing noise in review.

**Use.** Nothing to run; git applies it. `git check-attr -a <path>` to inspect.

#### `.gitignore`

`other` · 98 lines · 2,866 B · description: **curated**

**Purpose.** Keeps derived and machine-specific artifacts out of the tree — `data/` price caches, the semantic embedding array, build output. Anything regenerable and large belongs here.

**Use.** Add a pattern when you add a derived artifact; commit the manifest that describes it instead of the artifact.

#### `.nvmrc`

`other` · 2 lines · 3 B · description: **curated**

**Purpose.** Pins the Node version for the extension's test and tooling surfaces, so `node --test` behaves the same locally and in CI.

**Use.** `nvm use` in the repo root.

#### `AGENTS.md`

`doc` · 15 lines · 735 B · description: **curated**

**Purpose.** The operative rules for changing this repo. The backtester never gains live-trading capability, no lookahead, costs are never optional, the engine does not touch the network; the extension defaults to dry-run and its risk rails fail closed.

**Use.** Read first. It outranks any suggestion a tool or agent would otherwise make.

#### `CLAUDE.md`

`doc` · 94 lines · 5,616 B · description: **curated**

**Purpose.** Agent-facing companion to AGENTS.md — the same non-negotiables plus the workflow conventions (commit discipline, where numbers may come from, what must be regenerable).

**Use.** Read before making changes with an agent.

#### `GEMINI.md`

`doc` · 55 lines · 2,806 B · description: **extracted**

**Purpose.** Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file first — it is the single source of truth, and this file only points at it. that a fresh install can place an order.

**Use.** Read it.

#### `README.md`

`doc` · 113 lines · 5,793 B · description: **curated**

**Purpose.** Entry point: what the project is, the three components, and the honest summary of what the research established.

**Use.** Start here.

#### `pagesource`

`other` · 54 lines · 113,673 B · description: **curated**

**Purpose.** A captured page source kept as a fixture for the scraping/parsing work. Reference data, not code.

**Use.** Read it; nothing to run.

---

## docs

Curated prose. `ARCHITECTURE.md` explains how the pieces fit, `TESTING.md` is the coverage contract, `SECURITY.md` covers the order-placing surface, and this file indexes everything.

18 files.

#### `docs/API.md`

`doc` · 148 lines · 6,449 B · description: **extracted**

**Purpose.** Every action lives in one registry: `extension/src/core/commands.js`. Three surfaces adapt it. drift apart. cd extension

**Use.** Read it.

#### `docs/ARCHITECTURE.md`

`doc` · 118 lines · 6,905 B · description: **extracted**

**Purpose.** Two independent systems that share a subject (SOL) and nothing else. There is no code path from the backtester into the extension: research does not place orders, and the extension does not simulate. backtester/ research/ extension/

**Use.** Read it.

#### `docs/COMPONENTS.md`

`doc` · 190 lines · 8,118 B · description: **extracted**

**Purpose.** What each module is for, what it exposes, and what it depends on. `docs/codebase-overview.md` is the flat file map; this page is the shape of the thing. Dependency direction, strictly one-way:

**Use.** Read it.

#### `docs/CONCEPTS.md`

`doc` · 312 lines · 14,521 B · description: **extracted**

**Purpose.** python3 index/build.py all # refresh python3 index/make_concepts_doc.py # rewrite this file python3 index/search.py --concepts # list them

**Use.** Read it.

#### `docs/DEVELOPMENT.md`

`doc` · 145 lines · 6,328 B · description: **extracted**

**Purpose.** Setup, the commands you will actually use, and the environment each component needs. Everything else is stdlib. There is no build step anywhere in the repo. git clone <this repo> && cd solmargintrader

**Use.** Read it.

#### `docs/FILES.md`

`doc` · 2633 lines · 131,143 B · description: **extracted**

**Purpose.** Regenerate with: python3 index/build.py all # refresh the index python3 index/make_files_doc.py # rewrite this file

**Use.** Read it.

#### `docs/INSTALLATION.md`

`doc` · 138 lines · 5,238 B · description: **extracted**

**Purpose.** Four components, four different install stories. Only one of them installs anything persistent on your machine. features (`enum.StrEnum`).

**Use.** Read it.

#### `docs/OPERATIONS.md`

`doc` · 122 lines · 4,883 B · description: **extracted**

**Purpose.** cd extension && node tools/cli.js kill cannot resume trading. In the extension, the popup's red KILL SWITCH button does the same thing. node tools/cli.js data --json # find venueOrderId values

**Use.** Read it.

#### `docs/SECURITY.md`

`doc` · 81 lines · 4,411 B · description: **extracted**

**Purpose.** This repository contains software that can move real money. Two assets matter: **signing keys** and the **Jupiter API key**. 600,000 iterations**), with a fresh 16-byte salt and 12-byte IV per encryption. Identical

**Use.** Read it.

#### `docs/TESTING.md`

`doc` · 129 lines · 8,372 B · description: **extracted**

**Purpose.** python3 -m unittest discover -s backtester/tests -t . # 454 tests python3 -m unittest discover -s soltui/tests -t . # 95 tests (~70s) cd extension && npm test # 114 tests

**Use.** Read it.

#### `docs/codebase-overview.md`

`doc` · 185 lines · 10,275 B · description: **extracted**

**Purpose.** A file map for orientation, grouped by directory. Every path here is checked by Four components, in ascending order of how much damage a bug can do: Read `CLAUDE.md` before changing any of them; it carries the non-negotiables per

**Use.** Read it.

#### `docs/external-calls.md`

`doc` · 88 lines · 5,364 B · description: **extracted**

**Purpose.** Every call in this repo that leaves the machine. Four of them, across two components; The engine and the readout never touch the network — that is a stated invariant, not an accident. Fetching is always a separate explicit step that writes a local cache, so a

**Use.** Read it.

#### `docs/high_signal_file_index.json`

`doc` · 731 lines · 20,437 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys ($comment, repo, components, files).

**Use.** Read it.

#### `docs/integrations-and-assumptions.md`

`doc` · 106 lines · 5,560 B · description: **extracted**

**Purpose.** External services this repo depends on, and the assumptions baked into the code that would be wrong somewhere else. The second list is the one that bites. Full per-call detail — timeouts, retries, what is logged — is in `docs/external-calls.md`.

**Use.** Read it.

#### `docs/known-issues.md`

`doc` · 144 lines · 5,963 B · description: **extracted**

**Purpose.** Active limitations, in descending order of how much damage they could do. Nothing here is speculative — each item is either stated in the code or was reproduced. There are no `TODO`, `FIXME`, `XXX` or `HACK` markers anywhere in

**Use.** Read it.

#### `docs/logging.md`

`doc` · 86 lines · 4,200 B · description: **extracted**

**Purpose.** What each component records, where it goes, and — the part worth reading — which paths currently record nothing. The extension's real log is **not the console**. `src/storage/store.js` defines four

**Use.** Read it.

#### `docs/onboarding.md`

`doc` · 127 lines · 5,264 B · description: **extracted**

**Purpose.** A first hour that ends with you having run every component and knowing which one can lose money. Four components, three of which are harmless and one of which is not:

**Use.** Read it.

#### `docs/trading-signals-concept-family.md`

`doc` · 443 lines · 27,593 B · description: **extracted**

**Purpose.** automated trading signals and their execution on Jupiter (jup.ag) on Solana. This is a *map*, not an implementation plan, and not financial advice. Facts about Jupiter APIs were verified against live `developers.jup.ag`;

**Use.** Read it.

---

## index

The search layer over the repo itself. Generators plus three committed indexes; the embedding array is gitignored and rebuilt on demand.

5 files.

#### `index/README.md`

`doc` · 133 lines · 6,823 B · description: **extracted**

**Purpose.** A searchable index over every tracked file in this repo: what exists, which files contain a word, which files mean something like a question, and which bear on an idea. Built to answer "where is the thing that does X" without reading 266 files.

**Use.** Read it.

#### `index/build.py`

`code-python` · 832 lines · 35,114 B · description: **curated**

**Purpose.** Builds the four indexes over every tracked file: metadata, BM25 text, concepts, and the opt-in semantic embeddings. `--check` re-hashes the tree so a stale index fails loudly.

**Contents.** Defines `REPO`, `OUT`, `SCHEMA_VERSION`, `INDEX_JSON`, `TEXT_JSON`, `CONCEPT_JSON`, `SEMANTIC_NPZ`, `SEMANTIC_MANIFEST`, `TEXT_EXT`, `BODY_EXCLUDED_EXT` and 30 more.

**Use.** `python3 index/build.py all`, then `semantic` for embeddings, and `--check` before trusting it.

#### `index/make_concepts_doc.py`

`code-python` · 160 lines · 6,405 B · description: **extracted**

**Purpose.** Generate `docs/CONCEPTS.md` — the conceptual index, as prose. python3 index/make_concepts_doc.py python3 index/make_concepts_doc.py --stdout Reads `index/CONCEPT-INDEX.json`, so run `python3 index/build.py all` first. The concepts are not an invented taxonomy.

**Contents.** Defines `REPO`, `SRC`, `DEST`, `render()`, `main()`.

**Use.** `python3 index/make_concepts_doc.py --help`

#### `index/make_files_doc.py`

`code-python` · 517 lines · 26,825 B · description: **curated**

**Purpose.** Generates `docs/FILES.md` from the index plus the curated table in this module, so per-file documentation is regenerable and curation is never discarded by a rebuild.

**Contents.** Defines `REPO`, `INDEX_JSON`, `DEST`, `DIR_ORDER`, `derived_use()`, `contents_of()`, `render()`, `main()`.

**Use.** `python3 index/make_files_doc.py`.

#### `index/search.py`

`code-python` · 263 lines · 10,906 B · description: **curated**

**Purpose.** Query the index three ways — exact (BM25), meaning (cosine over embeddings), or concept — with rank fusion as the default because a reader rarely knows which kind of query they are typing.

**Contents.** Defines `REPO`, `OUT`, `INDEX_JSON`, `TEXT_JSON`, `CONCEPT_JSON`, `SEMANTIC_NPZ`, `SEMANTIC_MANIFEST`, `BM25_K1`, `BM25_B`, `RRF_K` and 7 more.

**Use.** `python3 index/search.py "how are costs applied"`, `--concepts`, `--concept <id>`, `--file <path>`, `--kind code-python`.

---

## backtester

The simulation engine and everything that supports it. Never gains live-trading capability, never touches the network, and costs are never optional. `core/` is the engine; `strategy_cards/` are the specs; `tests/` is the acceptance suite.

93 files.

#### `backtester/PROMPT.md`

`doc` · 200 lines · 20,191 B · description: **extracted**

**Purpose.** <role> You are a quantitative developer building research infrastructure. You have production experience with event-driven backtesting engines and you know the standard ways backtests lie: look-ahead bias, survivorship bias, unrealistic fills, and selection bias from comparing many strategies and reporting the winner. </role>

**Use.** Read it.

#### `backtester/README.md`

`doc` · 463 lines · 22,760 B · description: **extracted**

**Purpose.** An offline, event-driven backtesting harness for crypto trading strategies, built around SOL. Supports unlevered **spot** and **Jupiter-Perps-style leveraged perpetuals** with a correctly-modelled borrow fee.

**Use.** Read it.

#### `backtester/__init__.py`

`code-python` · 4 lines · 69 B · description: **extracted**

**Purpose.** SOL-focused crypto strategy backtester.

**Use.** `import backtester.__init__`

#### `backtester/cli.py`

`code-python` · 324 lines · 11,371 B · description: **extracted**

**Purpose.** Command-line entry point. python -m backtester.cli --asset SOL --strategy all --out results/ Running with no arguments prints usage rather than starting a long fetch.

**Contents.** Defines `build_parser()`, `_trimmed_metrics()`, `_run_one()`, `main()`.

**Use.** `python3 backtester/cli.py --help`

#### `backtester/gridcli.py`

`code-python` · 308 lines · 12,295 B · description: **extracted**

**Purpose.** Ladder-grid backtest entry point. python -m backtester.gridcli --lower 60 --upper 90 --rungs 7 --notional-per-rung 12 --synthetic 400 Separate from `backtester.cli` on purpose. That CLI runs `Strategy` objects — one target exposure per bar — and this one runs the resting-ladder simulator, whose config surface (lower/upper/rungs/notional) and execution model are different.

**Contents.** Defines `DISCLAIMER`, `_json_safe()`, `build_parser()`, `main()`.

**Use.** `python3 backtester/gridcli.py --help`

#### `backtester/paircli.py`

`code-python` · 237 lines · 9,589 B · description: **extracted**

**Purpose.** Peer-relative-value backtest entry point. python -m backtester.paircli --asset SOL --peer BTC --interval 1d --split 0.7 Separate from `backtester.cli` because this strategy needs **two** price series, and the strategy registry builds from zero arguments.

**Contents.** Defines `DISCLAIMER`, `_json_safe()`, `build_parser()`, `main()`.

**Use.** `python3 backtester/paircli.py --help`

#### `backtester/requirements.txt`

`data` · 14 lines · 500 B · description: **curated**

**Purpose.** Dependencies for the engine and research drivers — deliberately thin: pandas and numpy. No network client, no broker SDK, nothing that could place an order.

**Use.** `python3 -m pip install -r backtester/requirements.txt`.

### `backtester/core/`

#### `backtester/core/__init__.py`

`code-python` · 0 lines · 0 B · description: **curated**

**Purpose.** Marks `backtester.core` as a package. Intentionally empty — the engine's public surface is the individual modules, so nothing is re-exported here and there is no import-time side effect.

**Use.** Import the module you need directly, e.g. `from backtester.core.engine import run_backtest`.

#### `backtester/core/archive_price.py`

`code-python` · 154 lines · 5,934 B · description: **extracted**

**Purpose.** Append-only spot-price archiver, for series nobody publishes history for. python -m backtester.core.archive_price --mint JLP --out data/JLP_spot.csv Some cards are blocked on data that **cannot be fetched retroactively**. JLP is the clearest case: Jupiter's Price API serves its current price keyless, no exchange this repo can reach lists a JLP pair, and there is no charts endpoint.

**Contents.** Defines `PRICE_URL`, `KNOWN_MINTS`, `HEADER`, `class ArchiveError`, `fetch_spot()`, `append_observation()`, `count_rows()`, `main()`.

**Use.** `python3 backtester/core/archive_price.py --help`

#### `backtester/core/cointegration.py`

`code-python` · 198 lines · 7,218 B · description: **extracted**

**Purpose.** Engle-Granger cointegration and an Augmented Dickey-Fuller test. This is the machinery `zscore` should have had. A z-score trade assumes the series is stationary; raw SOL price is not, so applying it there is a known theoretical error that no measured result repairs.

**Contents.** Defines `_ADF_CRITICAL`, `_ADF_LEVELS`, `class AdfResult`, `class CointegrationResult`, `_ols()`, `_interp_critical()`, `adf_pvalue()`, `adf_test()`, `engle_granger()`.

**Use.** `import backtester.core.cointegration`

#### `backtester/core/cpcv.py`

`code-python` · 331 lines · 12,907 B · description: **curated**

**Purpose.** Combinatorial purged cross-validation and PBO. Produces a distribution of out-of-sample paths instead of one split, and measures whether the in-sample ranking predicts anything.

**Contents.** Defines `class BlockResult`, `class CpcvResult`, `make_groups()`, `evaluate_block()`, `_sharpe()`, `cpcv_evaluate()`, `pbo_cscv()`.

**Use.** `from backtester.core.cpcv import cpcv_evaluate, pbo_cscv`. Note that a configuration below `min_total_trades` is marked `insufficient` and printed DROPPED but still returns a full path count.

#### `backtester/core/data.py`

`code-python` · 289 lines · 11,022 B · description: **curated**

**Purpose.** Loading and validating bars. Refuses gaps rather than filling them, resolves columns by name, and requires monotone de-duplicated timestamps — a forward-filled gap flatters every volatility and reversion statistic computed after it.

**Contents.** Defines `class DataValidationError`, `class DataLoader`, `validate_bars()`, `_slice_dates()`, `checksum_frame()`, `class CsvLoader`, `class SyntheticLoader`, `frame_to_arrays()`.

**Use.** `CsvLoader(path, allow_gaps=False).load(asset, start, end, interval)`.

#### `backtester/core/engine.py`

`code-python` · 589 lines · 21,466 B · description: **curated**

**Purpose.** The event loop: maps a strategy's target exposure to fills, applies costs exactly once, and marks the book every bar. `fill_delay=1` is what keeps a signal at bar t from being filled at bar t.

**Contents.** Defines `class Strategy`, `class EngineConfig`, `class BacktestResult`, `class _Book`, `_resolve_target()`, `run_backtest()`, `_apply_target()`.

**Use.** `from backtester.core.engine import run_backtest, EngineConfig`. Every reported figure in this repo comes through here.

#### `backtester/core/fetch.py`

`code-python` · 222 lines · 7,788 B · description: **extracted**

**Purpose.** Explicit historical data fetch from the Coinbase Exchange public API. Never called implicitly by a backtest. Run it once to populate the local CSV cache, then every run and every test reads from disk. Two hazards this module exists to handle: 1. Coinbase returns rows as [time, low, high, open, close, volume] -- NOT in OHLCV order.

**Contents.** Defines `COINBASE_BASE`, `MAX_CANDLES_PER_REQUEST`, `COINBASE_ROW`, `SUPPORTED_GRANULARITIES`, `class FetchError`, `_get_json()`, `fetch_coinbase()`, `default_cache_path()`, `main()`.

**Use.** `python3 backtester/core/fetch.py --help`

#### `backtester/core/gridsim.py`

`code-python` · 875 lines · 36,077 B · description: **extracted**

**Purpose.** Resting-ladder grid simulator — the strategy the extension actually trades. This is deliberately NOT a `Strategy` in the `core.engine` sense. That protocol maps history to one target exposure filled at a bar boundary, and a grid's entire edge comes from **resting limit orders that fill intrabar at known prices**.

**Contents.** Defines `SPACING_GEOM`, `SPACING_ARITH`, `SPACINGS`, `SIDE_BUY`, `SIDE_SELL`, `VENUE_MIN_ORDER_USD`, `class GridConfig`, `grid_levels()`, `rung_width_bps()`, `nearest_level_index()` and 12 more.

**Use.** `import backtester.core.gridsim`

#### `backtester/core/indicators.py`

`code-python` · 442 lines · 17,415 B · description: **extracted**

**Purpose.** Trailing-window indicator functions. Every function here takes an array that the caller has ALREADY truncated to bars <= now (a `BarWindow` accessor does this by construction) and returns the value for the latest bar. None of them can see the future, because none of them are ever handed it. Two conventions worth knowing: * Each returns a scalar for the current bar, not a series.

**Contents.** Defines `EMA_CAP_MULTIPLE`, `EMA_WARMUP_MULTIPLE`, `sma()`, `ema()`, `ema_series()`, `wilder_smooth()`, `rsi()`, `macd()`, `bollinger()`, `true_range()` and 14 more.

**Use.** `import backtester.core.indicators`

#### `backtester/core/metrics.py`

`code-python` · 252 lines · 8,319 B · description: **extracted**

**Purpose.** Performance metrics with explicitly stated conventions. Ambiguous annualisation is the most common source of a wrong Sharpe ratio, so every convention here is named in the signature and echoed into the report: sample stdev (ddof=1), a 365-day crypto year, and an explicit risk-free rate.

**Contents.** Defines `class DrawdownInfo`, `class Metrics`, `simple_returns()`, `total_return()`, `cagr()`, `sharpe_ratio()`, `sortino_ratio()`, `annual_volatility()`, `max_drawdown()`, `_fmt_ts()` and 2 more.

**Use.** `import backtester.core.metrics`

#### `backtester/core/pairs.py`

`code-python` · 173 lines · 7,071 B · description: **extracted**

**Purpose.** Peer-relative-value reversion: trade a cointegrated spread, not a raw price. One mechanism serving two cards. `pairs_cointegration.md` runs it against BTC or ETH, which this repo can fetch keyless; `jlp_vs_sol_relative_value.md` runs it against JLP, whose price history nobody publishes — the code is identical and only the peer series differs.

**Contents.** Defines `align_peer()`, `class PeerSpreadReversion`.

**Use.** `import backtester.core.pairs`

#### `backtester/core/perps.py`

`code-python` · 182 lines · 6,542 B · description: **extracted**

**Purpose.** Jupiter-Perps-style borrow fees, margin, and liquidation. The one thing to get right about this venue: it charges a **borrow fee**, not a funding rate. Consequences encoded here: * Longs and shorts BOTH pay. There is no long-pays-short transfer. * The rate is a product of two non-negative quantities, so it is floor-bounded at zero. No position is ever paid to stay open.

**Contents.** Defines `class LiquidationInfo`, `hourly_borrow_rate()`, `accrue_borrow_fee()`, `liquidation_price()`, `is_liquidated()`, `required_collateral()`.

**Use.** `import backtester.core.perps`

#### `backtester/core/plotting.py`

`code-python` · 99 lines · 2,907 B · description: **extracted**

**Purpose.** Equity-curve and drawdown charts. matplotlib is imported lazily behind a guard so that a missing install degrades to "no charts" rather than failing an otherwise complete run.

**Contents.** Defines `charts_available()`, `plot_comparison()`.

**Use.** `import backtester.core.plotting`

#### `backtester/core/report.py`

`code-python` · 342 lines · 11,959 B · description: **extracted**

**Purpose.** Comparison reporting, with the caveats the numbers require. A sorted Sharpe table is the most misleading artifact a backtester can emit. Everything here exists to stop that: buy-and-hold is always shown as the baseline, in-sample and out-of-sample are separate columns, and the count of configurations evaluated is printed so a reader can weigh the selection bias.

**Contents.** Defines `NOT_ADVICE`, `MULTIPLE_TESTING_NOTE`, `TABLE_COLUMNS`, `PERCENT_COLUMNS`, `class SplitResult`, `library_versions()`, `results_frame()`, `_fmt_cell()`, `render_table()`, `render_report()` and 1 more.

**Use.** `import backtester.core.report`

#### `backtester/core/strategy_cards.py`

`code-python` · 653 lines · 26,520 B · description: **extracted**

**Purpose.** Strategy cards: one self-contained file per strategy or signal. A card is a Markdown file with YAML-subset frontmatter under `backtester/strategy_cards/`.

**Contents.** Defines `CARD_DIR`, `FRONTMATTER_FENCE`, `STATUSES`, `KINDS`, `RUNNERS`, `REQUIRED_FIELDS`, `SUCCESS_LIKELIHOODS`, `SUCCESS_BASES`, `HORIZONS`, `ALLOWED_FIELDS` and 13 more.

**Use.** `import backtester.core.strategy_cards`

#### `backtester/core/types.py`

`code-python` · 293 lines · 8,542 B · description: **extracted**

**Purpose.** Core value types for the backtester, including the look-ahead guard.

**Contents.** Defines `BAR_COLUMNS`, `HOURS_PER_YEAR`, `periods_per_year()`, `hours_per_bar()`, `class Mode`, `class Side`, `class LookAheadError`, `class Bar`, `class BarWindow`, `class Trade` and 3 more.

**Use.** `import backtester.core.types`

#### `backtester/core/universe.py`

`code-python` · 313 lines · 12,797 B · description: **extracted**

**Purpose.** Fetch a multi-asset universe into the local CSV cache. `fetch.py` fetches one product. This fetches a named set of them and, more importantly, is honest about the set it could not fetch.

**Contents.** Defines `COINBASE_PRODUCTS_URL`, `TOP10_NON_PEGGED`, `ALREADY_CACHED`, `TRADEABLE_UNIVERSE`, `class FetchPlan`, `product_id()`, `plan_universe_fetch()`, `list_coinbase_products()`, `fetch_universe()`, `main()`.

**Use.** `python3 backtester/core/universe.py --help`

### `backtester/core/strategies/`

#### `backtester/core/strategies/__init__.py`

`code-python` · 138 lines · 4,004 B · description: **curated**

**Purpose.** The strategy registry and the `FAMILY` taxonomy. `build(name, **params)` and `build_composite(specs, mode)` are the only sanctioned ways to construct a configuration, so the registry stays the single source of truth for what exists.

**Contents.** Defines `DEFAULT_SET`, `build()`, `build_all()`, `build_composite()`.

**Use.** `from backtester.core.strategies import build, build_composite, FAMILY`.

#### `backtester/core/strategies/advanced.py`

`code-python` · 469 lines · 18,889 B · description: **extracted**

**Purpose.** The nine mechanisms that needed code rather than data. Every strategy here was a `spec-only` card whose stated gap was "implementable now — needs code, not data". Each one is deliberately the *simplest honest* version of its mechanism, because the point of implementing them was to measure them, and a nine-parameter implementation measured on one split tells you less than a three-parameter one.

**Contents.** Defines `class DualMomentum`, `class AdxFilteredTrend`, `class MaRibbon`, `class IchimokuCloud`, `class OuHalfLifeReversion`, `class HurstRegimeSwitch`, `class VolRegimeSwitch`, `class AtrSizedTrend`, `class GarchVolTarget`.

**Use.** `import backtester.core.strategies.advanced`

#### `backtester/core/strategies/breakout.py`

`code-python` · 55 lines · 2,033 B · description: **extracted**

**Purpose.** Donchian-channel breakout: long on a new N-bar high, flat on an M-bar low.

**Contents.** Defines `class DonchianBreakout`.

**Use.** `import backtester.core.strategies.breakout`

#### `backtester/core/strategies/buy_and_hold.py`

`code-python` · 29 lines · 740 B · description: **extracted**

**Purpose.** Buy-and-hold: the mandatory baseline every other strategy must beat.

**Contents.** Defines `class BuyAndHold`.

**Use.** `import backtester.core.strategies.buy_and_hold`

#### `backtester/core/strategies/composite.py`

`code-python` · 72 lines · 2,875 B · description: **extracted**

**Purpose.** Combine several signals into one strategy. This is what makes pair and multi-signal testing possible without writing a bespoke class per combination. Four combination modes, because the choice materially changes what is being tested: * ``all`` -- min of member exposures. Every member must agree. Cuts trade count hard and raises precision at the cost of recall.

**Contents.** Defines `COMBINE_MODES`, `class Composite`.

**Use.** `import backtester.core.strategies.composite`

#### `backtester/core/strategies/ma_crossover.py`

`code-python` · 55 lines · 1,702 B · description: **extracted**

**Purpose.** Moving-average crossover: long while the fast SMA is above the slow SMA.

**Contents.** Defines `class MaCrossover`.

**Use.** `import backtester.core.strategies.ma_crossover`

#### `backtester/core/strategies/rsi.py`

`code-python` · 78 lines · 2,675 B · description: **extracted**

**Purpose.** RSI mean-reversion: buy oversold, exit on reversion to the midline.

**Contents.** Defines `wilder_rsi()`, `class RsiMeanReversion`.

**Use.** `import backtester.core.strategies.rsi`

#### `backtester/core/strategies/signals.py`

`code-python` · 436 lines · 16,578 B · description: **extracted**

**Purpose.** Indicator-driven strategies. Each class is a thin wrapper over `core.indicators`: the indicator layer does the arithmetic, the class turns a value into a target exposure. Grouped in one module because they are one-screen each and share the same imports; the registry treats them exactly like separately-filed strategies.

**Contents.** Defines `class MacdCross`, `class BollingerReversion`, `class BollingerBreakout`, `class KeltnerBreakout`, `class TsMomentum`, `class StochasticOversold`, `class VwapReversion`, `class ObvTrend`, `class ZScoreReversion`, `class Sma200Regime` and 2 more.

**Use.** `import backtester.core.strategies.signals`

### `backtester/strategy_cards/`

#### `backtester/strategy_cards/README.md`

`strategy-card` · 233 lines · 11,558 B · description: **extracted**

**Purpose.** One file per strategy or signal. Each card is self-contained: the equations, the code pointer, the reasoning, the failure modes, the caveats, the measured results, and the or an agent to run without reading anything else.

**Use.** Specification only — read it; there is no runner. Status: ?.

#### `backtester/strategy_cards/adx_filtered_trend.md`

`strategy-card` · 128 lines · 5,621 B · description: **extracted**

**Purpose.** Long only while a directional trend is both present (ADX) and up (+DI > -DI).

**Contents.** Frontmatter: `status`=measured, `family`=regime-filter, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=low, `data_available`=true, `registry_key`=adx_trend.

**Use.** Read the card, then build it: `build('adx_trend', **params)`. Status: measured.

#### `backtester/strategy_cards/atr_position_sizing.md`

`strategy-card` · 108 lines · 4,662 B · description: **extracted**

**Purpose.** Trend entry sized so one ATR of adverse move costs a fixed fraction of equity.

**Contents.** Frontmatter: `status`=measured, `family`=risk-overlay, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=atr_sized.

**Use.** Read the card, then build it: `build('atr_sized', **params)`. Status: measured.

#### `backtester/strategy_cards/avellaneda_stoikov_mm.md`

`strategy-card` · 60 lines · 2,331 B · description: **extracted**

**Purpose.** Optimal quotes around a reservation price with an inventory penalty. Wrong shape for this harness.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/bb_breakout.md`

`strategy-card` · 143 lines · 6,371 B · description: **extracted**

**Purpose.** Long a close above the upper Bollinger band, with an optional volatility-squeeze pre-filter.

**Contents.** Frontmatter: `status`=measured, `family`=breakout, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=low, `data_available`=true, `registry_key`=bb_breakout.

**Use.** Read the card, then build it: `build('bb_breakout', **params)`. Status: measured.

#### `backtester/strategy_cards/bb_reversion.md`

`strategy-card` · 101 lines · 4,120 B · description: **extracted**

**Purpose.** Buy a close below the lower Bollinger band, exit on reversion to the mid. Same inequality as zscore.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=bb_reversion.

**Use.** Read the card, then build it: `build('bb_reversion', **params)`. Status: measured.

#### `backtester/strategy_cards/breakout.md`

`strategy-card` · 106 lines · 4,374 B · description: **extracted**

**Purpose.** Long on a new n-bar high, flat on an m-bar low. The Turtle mechanism.

**Contents.** Frontmatter: `status`=measured, `family`=breakout, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=breakout.

**Use.** Read the card, then build it: `build('breakout', **params)`. Status: measured.

#### `backtester/strategy_cards/buy_and_hold.md`

`strategy-card` · 101 lines · 3,670 B · description: **extracted**

**Purpose.** Fully invested from the first tradeable bar. The null hypothesis every other card must beat.

**Contents.** Frontmatter: `status`=measured, `family`=baseline, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=buy_and_hold.

**Use.** Read the card, then build it: `build('buy_and_hold', **params)`. Status: measured.

#### `backtester/strategy_cards/dex_cex_dislocation.md`

`strategy-card` · 188 lines · 10,321 B · description: **extracted**

**Purpose.** Cross-venue basis as both a signal and an arbitrage.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/discount_to_anchor.md`

`strategy-card` · 147 lines · 7,266 B · description: **extracted**

**Purpose.** Buy in proportion to the discount against a fair-value anchor. Documented as a duplicate of the existing mean-reversion family rather than registered.

**Contents.** Frontmatter: `status`=spec-only, `family`=mean-reversion, `evaluation`=None, `success_likelihood`=very-low, `data_available`=true, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/dual_momentum_12_1.md`

`strategy-card` · 122 lines · 5,418 B · description: **extracted**

**Purpose.** Trailing formation-window return excluding the most recent bars, to skip short-term reversal.

**Contents.** Frontmatter: `status`=measured, `family`=momentum, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=very-low, `data_available`=true, `registry_key`=dual_momentum.

**Use.** Read the card, then build it: `build('dual_momentum', **params)`. Status: measured.

#### `backtester/strategy_cards/exchange_net_flow.md`

`strategy-card` · 56 lines · 1,889 B · description: **extracted**

**Purpose.** Stablecoins moving onto exchanges as a proxy for incoming buying power.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/funding_utilization_extremes.md`

`strategy-card` · 78 lines · 3,649 B · description: **extracted**

**Purpose.** On Jupiter there is no funding rate. The tradeable signal is pool UTILIZATION. Highest-ranked spec-only signal.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/garch_vol_forecast.md`

`strategy-card` · 115 lines · 5,113 B · description: **extracted**

**Purpose.** Vol-targeted trend using an EWMA variance forecast instead of a trailing stdev.

**Contents.** Frontmatter: `status`=measured, `family`=risk-overlay, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=garch_voltarget.

**Use.** Read the card, then build it: `build('garch_voltarget', **params)`. Status: measured.

#### `backtester/strategy_cards/grid.md`

`strategy-card` · 105 lines · 4,401 B · description: **extracted**

**Purpose.** Staircase accumulation as price falls below a rolling anchor. NOT the extension's resting-order ladder.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=grid.

**Use.** Read the card, then build it: `build('grid', **params)`. Status: measured.

#### `backtester/strategy_cards/hurst_regime_test.md`

`strategy-card` · 222 lines · 11,273 B · description: **extracted**

**Purpose.** A meta-signal: measure whether the series trends or reverts, then run the matching rule.

**Contents.** Frontmatter: `status`=measured, `family`=regime-filter, `evaluation`=cpcv-8-groups-k2-sol-btc-eth, `success_likelihood`=low, `data_available`=true, `registry_key`=hurst_switch.

**Use.** Read the card, then build it: `build('hurst_switch', **params)`. Status: measured.

#### `backtester/strategy_cards/ichimoku_cloud.md`

`strategy-card` · 107 lines · 4,514 B · description: **extracted**

**Purpose.** Long while price is above the cloud that was projected onto this bar displacement bars ago.

**Contents.** Frontmatter: `status`=measured, `family`=trend, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=ichimoku.

**Use.** Read the card, then build it: `build('ichimoku', **params)`. Status: measured.

#### `backtester/strategy_cards/implied_vs_realised_vol.md`

`strategy-card` · 60 lines · 2,234 B · description: **extracted**

**Purpose.** Harvest the variance risk premium when implied minus realised volatility is historically wide.

**Contents.** Frontmatter: `status`=spec-only, `family`=volatility, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/jlp_vs_sol_relative_value.md`

`strategy-card` · 107 lines · 5,035 B · description: **extracted**

**Purpose.** The peer-spread mechanism pointed at JLP. Code is done; the price history does not exist yet.

**Contents.** Frontmatter: `status`=implemented, `family`=mean-reversion, `evaluation`=null, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: implemented.

#### `backtester/strategy_cards/kalman_hedge_ratio.md`

`strategy-card` · 60 lines · 2,256 B · description: **extracted**

**Purpose.** Let the hedge ratio evolve as a state variable instead of fixing it per window.

**Contents.** Frontmatter: `status`=spec-only, `family`=mean-reversion, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/keltner.md`

`strategy-card` · 99 lines · 3,854 B · description: **extracted**

**Purpose.** Breakout of an ATR-width channel around an EMA. Like Bollinger, but its volatility measure sees gaps.

**Contents.** Frontmatter: `status`=measured, `family`=breakout, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=keltner.

**Use.** Read the card, then build it: `build('keltner', **params)`. Status: measured.

#### `backtester/strategy_cards/ladder_grid.md`

`strategy-card` · 212 lines · 10,702 B · description: **extracted**

**Purpose.** A ladder of resting limit orders with paired exits one rung above each lot. The strategy the extension trades.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=real-sol-daily-and-hourly-recentred-blocks, `success_likelihood`=low, `data_available`=true, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: measured.

#### `backtester/strategy_cards/liquidation_cascade_proximity.md`

`strategy-card` · 59 lines · 2,244 B · description: **extracted**

**Purpose.** Estimate clustered liquidation levels, then fade or follow the cascade.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/ma_crossover.md`

`strategy-card` · 106 lines · 4,271 B · description: **extracted**

**Purpose.** Long while a fast SMA sits above a slow SMA. The canonical trend-following rule.

**Contents.** Frontmatter: `status`=measured, `family`=trend, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=ma_crossover.

**Use.** Read the card, then build it: `build('ma_crossover', **params)`. Status: measured.

#### `backtester/strategy_cards/ma_ribbon.md`

`strategy-card` · 90 lines · 3,494 B · description: **extracted**

**Purpose.** Exposure scales with the fraction of adjacent MA pairs in correct order.

**Contents.** Frontmatter: `status`=measured, `family`=trend, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=ma_ribbon.

**Use.** Read the card, then build it: `build('ma_ribbon', **params)`. Status: measured.

#### `backtester/strategy_cards/macd.md`

`strategy-card` · 110 lines · 4,389 B · description: **extracted**

**Purpose.** Long while the MACD line is above its signal line. Momentum of the gap between two EMAs.

**Contents.** Frontmatter: `status`=measured, `family`=trend, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=macd.

**Use.** Read the card, then build it: `build('macd', **params)`. Status: measured.

#### `backtester/strategy_cards/mvrv_nupl_valuation.md`

`strategy-card` · 59 lines · 2,077 B · description: **extracted**

**Purpose.** Market value against realised value as a cycle-position gauge.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/obv_trend.md`

`strategy-card` · 145 lines · 6,794 B · description: **extracted**

**Purpose.** Long while cumulative signed volume is above its own moving average. Price-blind by construction.

**Contents.** Frontmatter: `status`=measured, `family`=volume-flow, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=low, `data_available`=true, `registry_key`=obv_trend.

**Use.** Read the card, then build it: `build('obv_trend', **params)`. Status: measured.

#### `backtester/strategy_cards/open_interest_divergence.md`

`strategy-card` · 57 lines · 1,902 B · description: **extracted**

**Purpose.** Open interest rising while price is flat marks leverage build-up and liquidation risk.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/order_book_imbalance.md`

`strategy-card` · 57 lines · 1,912 B · description: **extracted**

**Purpose.** The highest-frequency edge available, and completely out of reach here.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/ou_half_life_sizing.md`

`strategy-card` · 194 lines · 9,686 B · description: **extracted**

**Purpose.** Z-score reversion with an Ornstein-Uhlenbeck hold cap and a stationarity screening rule.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=cpcv-8-groups-k2-sol-btc-eth, `success_likelihood`=low, `data_available`=true, `registry_key`=ou_reversion.

**Use.** Read the card, then build it: `build('ou_reversion', **params)`. Status: measured.

#### `backtester/strategy_cards/pairs_cointegration.md`

`strategy-card` · 120 lines · 5,983 B · description: **extracted**

**Purpose.** Trade a spread whose stationarity is actually tested. The rigorous version of zscore.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: measured.

#### `backtester/strategy_cards/rsi.md`

`strategy-card` · 107 lines · 4,272 B · description: **extracted**

**Purpose.** Buy when Wilder's RSI is oversold, exit when it recovers past a midline. Stateful hold between.

**Contents.** Frontmatter: `status`=measured, `family`=oscillator-reversion, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=rsi.

**Use.** Read the card, then build it: `build('rsi', **params)`. Status: measured.

#### `backtester/strategy_cards/sma_regime.md`

`strategy-card` · 117 lines · 4,827 B · description: **extracted**

**Purpose.** Long above a slow moving average, flat below it. The most valuable partner in the set.

**Contents.** Frontmatter: `status`=measured, `family`=regime-filter, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=sma_regime.

**Use.** Read the card, then build it: `build('sma_regime', **params)`. Status: measured.

#### `backtester/strategy_cards/social_sentiment.md`

`strategy-card` · 59 lines · 2,156 B · description: **extracted**

**Purpose.** Documented alpha horizon of 1-2 days with fast decay; bot noise is the principal difficulty.

**Contents.** Frontmatter: `status`=spec-only, `family`=alt-data, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/staking_ratio_flow.md`

`strategy-card` · 57 lines · 2,029 B · description: **extracted**

**Purpose.** SOL-specific float dynamics: a rising staked fraction reduces liquid supply.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/stochastic.md`

`strategy-card` · 100 lines · 3,870 B · description: **extracted**

**Purpose.** Long when %K is oversold AND already above %D, so the turn has visibly begun.

**Contents.** Frontmatter: `status`=measured, `family`=oscillator-reversion, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=stochastic.

**Use.** Read the card, then build it: `build('stochastic', **params)`. Status: measured.

#### `backtester/strategy_cards/trade_flow_imbalance.md`

`strategy-card` · 57 lines · 2,017 B · description: **extracted**

**Purpose.** Signed trade prints. Naive flow-following is systematically picked off.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/triangular_arbitrage.md`

`strategy-card` · 173 lines · 9,507 B · description: **extracted**

**Purpose.** Three-leg currency cycle priced off parity. Not backtestable on this project's data, for a structural reason rather than a resolution one.

**Contents.** Frontmatter: `status`=spec-only, `family`=arbitrage, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/ts_momentum.md`

`strategy-card` · 103 lines · 4,122 B · description: **extracted**

**Purpose.** Long when the trailing n-bar return is positive. The Moskowitz/Ooi/Pedersen time-series form.

**Contents.** Frontmatter: `status`=measured, `family`=momentum, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=ts_momentum.

**Use.** Read the card, then build it: `build('ts_momentum', **params)`. Status: measured.

#### `backtester/strategy_cards/vol_of_vol_term_structure.md`

`strategy-card` · 57 lines · 1,885 B · description: **extracted**

**Purpose.** Trade the shape and instability of the volatility surface.

**Contents.** Frontmatter: `status`=spec-only, `family`=volatility, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/vol_regime_hmm.md`

`strategy-card` · 177 lines · 8,216 B · description: **extracted**

**Purpose.** Trend-follow in calm volatility, stand aside when volatility is elevated.

**Contents.** Frontmatter: `status`=measured, `family`=regime-filter, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=low, `data_available`=true, `registry_key`=vol_regime.

**Use.** Read the card, then build it: `build('vol_regime', **params)`. Status: measured.

#### `backtester/strategy_cards/voltarget.md`

`strategy-card` · 119 lines · 5,189 B · description: **extracted**

**Purpose.** Trend entry sized inversely to realised volatility. Continuous exposure, not binary.

**Contents.** Frontmatter: `status`=measured, `family`=risk-overlay, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=voltarget.

**Use.** Read the card, then build it: `build('voltarget', **params)`. Status: measured.

#### `backtester/strategy_cards/vwap_reversion.md`

`strategy-card` · 101 lines · 4,042 B · description: **extracted**

**Purpose.** Buy a discount to rolling volume-weighted average price, exit on reversion.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=vwap_reversion.

**Use.** Read the card, then build it: `build('vwap_reversion', **params)`. Status: measured.

#### `backtester/strategy_cards/xs_momentum.md`

`strategy-card` · 64 lines · 2,571 B · description: **extracted**

**Purpose.** Rank a universe by trailing return and hold the top decile. Needs peers this repo does not have.

**Contents.** Frontmatter: `status`=spec-only, `family`=momentum, `evaluation`=None, `success_likelihood`=low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/zscore.md`

`strategy-card` · 134 lines · 5,924 B · description: **extracted**

**Purpose.** Buy when price is z sample-stdevs below its trailing mean. Top-ranked medium single, at the evidence floor.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=very-low, `data_available`=true, `registry_key`=zscore.

**Use.** Read the card, then build it: `build('zscore', **params)`. Status: measured.

### `backtester/tests/`

#### `backtester/tests/__init__.py`

`test` · 0 lines · 0 B · description: **curated**

**Purpose.** Makes the test directory a package so `python3 -m unittest discover -t .` resolves `backtester.*` imports. Empty by design.

**Use.** Nothing to run.

#### `backtester/tests/test_advanced_strategies.py`

`test` · 285 lines · 13,340 B · description: **extracted**

**Purpose.** Tests for the nine strategies implemented from spec-only cards. Each test targets the thing that mechanism could get *wrong*, not that it runs: the skipped window in dual momentum, the strength gate in ADX, the displacement trap in Ichimoku, the screening rule in the OU reversion, and the regime selection in both switches.

**Contents.** Defines `window()`, `trending()`, `oscillating()`, `class TestDualMomentum`, `class TestAdxFilteredTrend`, `class TestMaRibbon`, `class TestIchimokuDisplacement`, `class TestOuHalfLifeReversion`, `class TestHurstRegimeSwitch`, `class TestVolRegimeSwitch` and 3 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_advanced_strategies.py -q`

#### `backtester/tests/test_cpcv.py`

`test` · 279 lines · 12,378 B · description: **extracted**

**Purpose.** Known-answer tests for combinatorial purged CV and PBO. The PBO cases are constructed so the correct answer is known by design: a signal set where the in-sample winner always wins out-of-sample must yield PBO ~ 0, and one where in-sample rank carries no information must yield PBO ~ 0.5. Without those two anchors, a PBO implementation can be arbitrarily wrong and still look plausible.

**Contents.** Defines `class TestMakeGroups`, `class TestEvaluateBlock`, `class TestCpcvEvaluate`, `class TestPboCscv`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_cpcv.py -q`

#### `backtester/tests/test_cross_asset_cpcv.py`

`test` · 1198 lines · 58,911 B · description: **extracted**

**Purpose.** The cross-asset CPCV script's pure parts. No test here loads a price file, runs the engine, or writes anywhere under `research/results/`. That is not tidiness -- it is what makes these tests runnable at all, and safe to run: * `data/` is gitignored, so a test that opened `data/BTC_1d.csv` would pass on a development machine and fail in CI for a reason unrelated to the code.

**Contents.** Defines `REPO`, `SHARPES`, `RETURNS`, `TRADES`, `USABLE`, `N_PATHS`, `cpcv_result()`, `class PatchMixin`, `class Top5SpecTests`, `class MakeTop5StrategyTests` and 7 more. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_cross_asset_cpcv.py -q`

#### `backtester/tests/test_decide.py`

`test` · 923 lines · 41,039 B · description: **extracted**

**Purpose.** Tests for the per-bar rule readout in `research/decide.py`. The readout's one substantive claim is that its target exposures are the same numbers the engine would have acted on. Three tests defend it: * **Engine parity.** A recording wrapper captures every `on_bar` return the engine asks for, and the replay must reproduce that sequence exactly, for every registered strategy.

**Contents.** Defines `REPO`, `ZERO_COST`, `SYNTHETIC_BARS`, `synthetic_arrays()`, `truncate()`, `make_arrays()`, `class Recorder`, `class TestEngineParity`, `class TestNoLeak`, `class TestPathDependence` and 6 more. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_decide.py -q`

#### `backtester/tests/test_engine.py`

`test` · 606 lines · 25,376 B · description: **extracted**

**Purpose.** Acceptance tests for the backtest engine. These are known-answer tests, not smoke tests. Each one has a hand-computed expected value, so a failure localises the bug rather than just signalling that something changed.

**Contents.** Defines `make_frame()`, `ZERO_COST`, `class TestBuyAndHoldIdentity`, `class TestLookAheadGuard`, `class TestFillTiming`, `class TestFeeArithmetic`, `class TestResizeCosts`, `class TestGapLiquidation`, `class TestBorrowFeeSign`, `class TestLiquidation` and 3 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_engine.py -q`

#### `backtester/tests/test_geometry.py`

`test` · 516 lines · 23,797 B · description: **extracted**

**Purpose.** Tests for the block-count geometry sweep. `geometry.py` answers whether the CPCV leaderboard is a property of the strategies or of the block count. Two pieces carry the whole conclusion and are covered here: * **the comparability intersection.** Larger N means smaller blocks means more strategies fail their warm-up.

**Contents.** Defines `REPO`, `class SpearmanTests`, `class RankingTests`, `class VerdictTests`, `frame()`, `class GeometryStatsTests`, `class TidyFrameTests`, `class MarkdownTableRowsTests`, `class CensusTests`, `class VerdictLabelTests` and 4 more. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_geometry.py -q`

#### `backtester/tests/test_gridcli.py`

`test` · 173 lines · 7,491 B · description: **extracted**

**Purpose.** Tests for the ladder-grid CLI. The CLI is a thin adapter over a tested core, so these tests cover only what lives in the adapter itself: exit-code mapping, argument rejection, JSON validity, and the disclaimer. Each one exists because that logic cannot fail anywhere else.

**Contents.** Defines `LADDER`, `run()`, `_reject_constant()`, `class TestJsonOutput`, `class TestDisclaimer`, `class TestExitCodes`, `class TestReportedConfigMatchesTheRun`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_gridcli.py -q`

#### `backtester/tests/test_gridsim.py`

`test` · 512 lines · 23,402 B · description: **extracted**

**Purpose.** Tests for the resting-ladder grid simulator. The load-bearing test in this file is `test_round_trip_captures_exactly_one_rung`. The extension shipped a bug once where the exit rested at the level it had just bought at, capturing zero and paying two fees; `expectedRoundTripUsd` and its JS test exist to keep that fixed.

**Contents.** Defines `FREE`, `bars()`, `flat()`, `class TestLadderGeometry`, `class TestRoundTripEconomics`, `class TestNoLookahead`, `class TestFailureModes`, `class TestAccounting`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_gridsim.py -q`

#### `backtester/tests/test_index.py`

`test` · 239 lines · 10,755 B · description: **extracted**

**Purpose.** The repository index: isolation, correctness, and the staleness gate. No test here builds the real index or calls the network. `index/build.py`'s `semantic` subcommand is the only thing in this repo that opens a socket, and it talks to localhost ollama; a test that exercised it would be neither deterministic nor available in CI. The load-bearing test is the first one.

**Contents.** Defines `REPO`, `INDEX_DIR`, `class IsolationTests`, `class ClassificationTests`, `class ExtractionTests`, `class TextIndexTests`, `class ConceptTests`, `class StalenessGateTests`.

**Use.** `python3 -m pytest backtester/tests/test_index.py -q`

#### `backtester/tests/test_indicators.py`

`test` · 329 lines · 14,341 B · description: **extracted**

**Purpose.** Known-answer tests for indicators, strategies, and the composite combiner. Indicator values here are hand-computed, not captured from a previous run, so a regression points at the arithmetic rather than at "something changed".

**Contents.** Defines `class TestIndicatorArithmetic`, `class TestEveryRegisteredStrategy`, `class TestComposite`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_indicators.py -q`

#### `backtester/tests/test_interpret.py`

`test` · 147 lines · 5,675 B · description: **extracted**

**Purpose.** Tests for the self-explaining sweep output. `interpret()` turns four numbers into the reading a person should take from them. Its most important job is catching the two dangerous misreadings: * a high positive-count with a high PBO ("lots of strategies work!") * a LOW PBO with a low positive-count ("great, rank generalises!") The second is the subtle one, so it gets the most coverage here.

**Contents.** Defines `REPO`, `joined()`, `class TestAntiInformative`, `class TestLowPboTrap`, `class TestNearNoise`, `class TestDroppedAndEdges`. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_interpret.py -q`

#### `backtester/tests/test_pairs.py`

`test` · 204 lines · 9,082 B · description: **extracted**

**Purpose.** Tests for cointegration and peer-relative-value reversion. The statistics are checked against series whose answer is known by construction — white noise is stationary, a random walk is not, a synthetic pair is cointegrated and two independent walks are not.

**Contents.** Defines `bars()`, `window_at()`, `class TestAdf`, `class TestEngleGranger`, `class TestAlignPeer`, `class TestPeerSpreadReversion`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_pairs.py -q`

#### `backtester/tests/test_strategy_cards.py`

`test` · 627 lines · 26,487 B · description: **extracted**

**Purpose.** Tests for strategy cards. These are the tests that make a card a contract rather than a claim. Prose in a card can be wrong and no test will catch it; a *number* in a card is checked against the code that would use it.

**Contents.** Defines `REPO_ROOT`, `constructor_defaults()`, `synthetic_bars()`, `class TestFrontmatterParser`, `class TestCardValidation`, `class TestCardsLoad`, `class TestSuccessRatings`, `class TestRegistryDrift`, `class TestLadderDrift`, `class TestSweepDrift` and 2 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_strategy_cards.py -q`

#### `backtester/tests/test_universe.py`

`test` · 242 lines · 10,859 B · description: **extracted**

**Purpose.** The multi-asset universe fetch. No test here touches the network. `list_coinbase_products` takes an injected `get_json` and `fetch_universe` takes an injected `fetcher`, for the reason `fetch.py`'s own docstring gives: fetching is an explicit step, and a test suite that performs it is neither deterministic nor polite to the venue. The behaviour most worth pinning is the refusal.

**Contents.** Defines `LISTED`, `bars()`, `class PlanTests`, `class FetchTests`, `class CliTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_universe.py -q`

---

## research

Drivers that produce the numbers, and the write-ups that quote them. Everything here is reproducible from a committed script — the two occasions that was not true both produced a wrong published figure.

77 files.

#### `research/CROSS-ASSET-TRANSFER.md`

`doc` · 225 lines · 14,429 B · description: **extracted**

**Purpose.** python3 research/cross_asset_cpcv.py --self-test # gate: reproduces the BTC/ETH file python3 research/cross_asset_cpcv.py --assets SOL,DOGE,ZEC # 25 singles, medium horizon python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC # the five, with SOL as control

**Use.** Read it.

#### `research/PROMPT_STRATEGIES.md`

`doc` · 175 lines · 14,396 B · description: **extracted**

**Purpose.** <!-- HISTORICAL SPEC — preserved as written, do not retro-edit. This is the pdo-optimized spec that drove the first pass of the work. Two of its

**Use.** Read it.

#### `research/RANKED_LISTS.md`

`doc` · 929 lines · 62,054 B · description: **extracted**

**Purpose.** configuration, so realised path counts are lower; see "How many paths each figure actually rests on" below. The earlier single 70/30 walk-forward is retained as List 1b, because the disagreement between the two methods is the most instructive result here.

**Use.** Read it.

#### `research/STRATEGIES.md`

`doc` · 779 lines · 39,574 B · description: **extracted**

**Purpose.** The request asked for a `/dr` deep-research pass. Subagent fan-out is unavailable in this environment, so this is grounded in the **local citation-backed corpus** — technical analysis, trading styles, algorithmic/quant methods, ML-for-trading pitfalls, crypto

**Use.** Read it.

#### `research/TOP5-RECOMMENDATION.md`

`doc` · 108 lines · 7,216 B · description: **extracted**

**Purpose.** files. Nothing is transcribed by hand. PBO (probability of backtest overfitting) is **0.700** for singles at both daily horizons, against a measured pure-noise line of 0.500. Above the noise line means selecting by in-sample

**Use.** Read it.

#### `research/TOP_COINS.md`

`doc` · 142 lines · 7,828 B · description: **extracted**

**Purpose.** Machine-readable copy: `research/results/top_coins.csv`. Regenerate rather than edit by hand — every figure here came from that one API call and none is transcribed. market cap and that is what market cap says. They are marked because a trading universe that

**Use.** Read it.

#### `research/cpcv_sweep.py`

`code-python` · 462 lines · 20,524 B · description: **curated**

**Purpose.** The primary evaluation driver: CPCV over singles, pairs and triples, then PBO across the configuration set. Prints its own legend so the numbers cannot travel without their meaning.

**Contents.** Defines `REPO`, `OUT`, `LEGEND`, `PBO_NOISE`, `PBO_INFORMATIVE`, `LOW_POSITIVE_SHARE`, `interpret()`, `TRIPLE_CANDIDATES`, `run_horizon()`, `run_combos()` and 1 more. Depends on `backtester`, `research`.

**Use.** `python3 research/cpcv_sweep.py --horizon medium --groups 8 --k 2`.

#### `research/cross_asset_cpcv.py`

`code-python` · 799 lines · 38,561 B · description: **curated**

**Purpose.** Runs the registered strategy set on another coin with the SOL-tuned parameters deliberately NOT refitted, so the measurement is transfer rather than fit. Two gates: it reproduces the committed BTC/ETH reference, and reproduces SOL's five published medians.

**Contents.** Defines `REPO`, `OUT`, `REFERENCE`, `REFERENCE_ASSETS`, `REFERENCE_HORIZON`, `REFERENCE_GROUPS`, `REFERENCE_K`, `MIN_RANKABLE_TRADES`, `MAX_PATHS`, `COLUMNS` and 17 more. Depends on `backtester`, `research`.

**Use.** `python3 research/cross_asset_cpcv.py --self-test` then `--assets SOL,DOGE,ZEC` or `--top5 --assets DOGE,ZEC`.

#### `research/decide.py`

`code-python` · 1219 lines · 46,127 B · description: **extracted**

**Purpose.** What every registered strategy, signal and indicator says about the last bar. python3 research/decide.py --asset SOL --interval 1d python3 research/decide.py --data data/BTC_1d.csv --json Three sections, because they are three different kinds of claim: * **Strategies** -- every entry in `core.strategies.REGISTRY`, replayed bar-by-bar from the start of history.

**Contents.** Defines `REPO`, `DEFAULT_TOLERANCE`, `FLAT_EPSILON`, `STALE_AFTER_BARS`, `HOLD_LONG`, `HOLD_SHORT`, `FLAT`, `BUY`, `SELL`, `INSUFFICIENT` and 30 more. Depends on `backtester`.

**Use.** `python3 research/decide.py --help`

#### `research/geometry.py`

`code-python` · 300 lines · 12,846 B · description: **curated**

**Purpose.** Sensitivity of results to the CPCV geometry itself. Changing 8 blocks to 9 moved the best pair's median Sharpe more than the worst parameter nudge did — the evaluation design mattered more than the strategy.

**Contents.** Defines `REPO`, `OUT`, `class GeometryRun`, `spearman()`, `evaluate_geometry()`, `tidy_frame()`, `render()`, `verdict()`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/geometry.py --help`.

#### `research/perturb.py`

`code-python` · 451 lines · 18,755 B · description: **curated**

**Purpose.** The second independent robustness axis: nudge each parameter ±10% and re-run CPCV. A point that collapses under a small nudge was fitted to noise, whatever its Sharpe.

**Contents.** Defines `REPO`, `OUT`, `BOUNDED_UNIT`, `REFERENCE`, `REFERENCE_HIGH`, `class Trial`, `class Report`, `perturbed_values()`, `evaluate()`, `run()` and 4 more. Depends on `backtester`, `research`.

**Use.** `python3 research/perturb.py --help`.

#### `research/sweep.py`

`code-python` · 494 lines · 20,232 B · description: **curated**

**Purpose.** Defines `HORIZONS` — the per-horizon data file, interval, gap policy and parameter set — and runs the single-split walk-forward that CPCV superseded. The parameter tables here are what every other driver imports, so an edit moves every downstream number.

**Contents.** Defines `REPO`, `OUT_DIR`, `MIN_OOS_TRADES`, `SPLIT`, `COMBO_CANDIDATES`, `class Row`, `load_horizon()`, `walk_forward()`, `sweep_singles()`, `cross_family_combos()` and 3 more. Depends on `backtester`.

**Use.** `python3 research/sweep.py --help`. Imported by the other drivers for `HORIZONS` and `load_horizon`.

#### `research/turnover_table.py`

`code-python` · 200 lines · 8,358 B · description: **curated**

**Purpose.** The one comparable turnover table for the ten coins, plus a checker. Exists because ten spokes each pulling their own snapshot produced ten figures that were ranked against each other anyway, and the ranking was wrong.

**Contents.** Defines `REPO`, `SOURCE`, `AS_OF`, `SPOKE_DIRS`, `SPOKES`, `turnover_table()`, `render()`, `find_spoke()`, `check()`, `main()`.

**Use.** `python3 research/turnover_table.py` or `--check`.

#### `research/verify_numbers.py`

`code-python` · 1082 lines · 48,324 B · description: **curated**

**Purpose.** The figure gate. Re-checks every number quoted in `RANKED_LISTS.md` and `STRATEGIES.md` against the result files that produced them, so a transcription slip cannot survive in prose. CI runs it.

**Contents.** Defines `RESEARCH`, `CSV`, `DOCS`, `EXPECTED_FIGURES`, `TOL_SHARPE`, `TOL_PCT`, `ROW`, `PAIR_ROW`, `PROSE_IS_OOS`, `PROSE_OOS_SHARPE` and 30 more.

**Use.** `python3 research/verify_numbers.py` — currently 950 figures, exit 0.

### `research/coin-intelligence/`

#### `research/coin-intelligence/README.md`

`coin-reference` · 138 lines · 10,431 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `research/coin-intelligence/bnb-binance-coin.md`

`coin-reference` · 570 lines · 38,287 B · description: **extracted**

**Purpose.** Trader-facing reference for BNB (Binance Coin) — exchange-token mechanics, the Auto-Burn supply schedule, extreme address concentration, venue and issuer risk, and what its 0.73% headline turnover really means for sizing and backtesting.

**Use.** Read it.

#### `research/coin-intelligence/btc-bitcoin.md`

`coin-reference` · 1092 lines · 75,540 B · description: **extracted**

**Purpose.** Trader-facing reference on Bitcoin — mechanics, supply, price regimes, market structure, volatility/correlation, liquidity, and what a BTC backtest does and does not prove about SOL. Read before using BTC as a signal source, a benchmark, or a cross-asset generalisation test.

**Use.** Read it.

#### `research/coin-intelligence/doge-dogecoin.md`

`coin-reference` · 199 lines · 22,951 B · description: **extracted**

**Purpose.** Trader-facing reference for Dogecoin (DOGE) — uncapped supply with fixed ~5.256B/yr issuance and therefore a declining inflation rate, merge-mined with Litecoin, and the purest sentiment/reflexivity asset in this set; a stable high-beta BTC proxy rather than a diversifier.

**Use.** Read it.

#### `research/coin-intelligence/eth-ethereum.md`

`coin-reference` · 1077 lines · 72,932 B · description: **extracted**

**Purpose.** Trader-facing reference on Ethereum (ETH) — mechanics, supply and burn, the L2 value-accrual bear case, the ETH/BTC ratio, market structure, measured volatility and beta vs BTC, and what backtesting on the local ETH_1d.csv does and does not establish. Educational only, not investment advice.

**Use.** Read it.

#### `research/coin-intelligence/hype-hyperliquid.md`

`coin-reference` · 520 lines · 37,041 B · description: **extracted**

**Purpose.** Trader-facing reference on Hyperliquid (HYPE) — on-chain CLOB perp DEX with its own L1, the HLP vault versus Jupiter's JLP, fee-funded buybacks, unlock overhang, and validator centralisation caveats.

**Use.** Read it.

#### `research/coin-intelligence/rain-rain.md`

`coin-reference` · 568 lines · 39,204 B · description: **extracted**

**Purpose.** Sceptical trader-facing reference on Rain (RAIN), an Arbitrum prediction-market token whose ~$8.6B headline market cap is not corroborated by tracked protocol activity, tradeable float, or order-book depth.

**Use.** Read it.

#### `research/coin-intelligence/sol-solana.md`

`coin-reference` · 364 lines · 25,475 B · description: **extracted**

**Purpose.** Solana (SOL) for a systematic trader — execution reality on a no-mempool chain, supply and staking, and what this project's own 1,287-configuration backtest actually measured on it. Read before designing or trusting any SOL strategy.

**Use.** Read it.

#### `research/coin-intelligence/trx-tron.md`

`coin-reference` · 187 lines · 23,730 B · description: **extracted**

**Purpose.** Trader-facing reference for TRON (TRX) — the dominant USDT settlement chain by transfer count, a low-turnover asset whose recent realized volatility runs below Bitcoin's despite a −51% historical drawdown, with contested holder concentration, and NOT listed on Coinbase (a hard blocker for this project's fetcher).

**Use.** Read it.

#### `research/coin-intelligence/xrp-ripple.md`

`coin-reference` · 593 lines · 40,556 B · description: **extracted**

**Purpose.** Trader-facing reference for XRP — XRPL mechanics, the 100B pre-mine and escrow release schedule, what Ripple actually holds, the SEC litigation record with dates, venue structure, and what its 1.37% turnover means for sizing and backtesting.

**Use.** Read it.

#### `research/coin-intelligence/zec-zcash.md`

`coin-reference` · 228 lines · 32,501 B · description: **extracted**

**Purpose.** Trader-facing reference for Zcash (ZEC) — $513/coin on a ~16.8M supply and an $8.6B cap, optional-privacy design with transparent and shielded pools, a 38x move dated to a 2025-10-01 breakout, and real venue-availability risk (Coinbase lists ZEC-USD but has delisted ZEC-BTC and ZEC-USDC).

**Use.** Read it.

### `research/results/`

#### `research/results/configuration_counts.json`

`result` · 12 lines · 201 B · description: **derived**

**Purpose.** Generated JSON object, 9 keys (long/pairs, long/singles, medium/pairs, medium/singles, medium/triples, short/pairs...).

**Use.** `json.load(open('research/results/configuration_counts.json'))`

#### `research/results/cpcv_all25_1h.csv`

`result` · 27 lines · 2,503 B · description: **derived**

**Purpose.** Generated data: 25 rows x 11 columns (strategy, label, n_paths, usable_blocks, median_sharpe, q1_sharpe, q3_sharpe, iqr...).

**Contents.** Columns: `strategy`, `label`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr`, `frac_paths_positive`, `median_return`, `total_trades`.

**Use.** `pandas.read_csv('research/results/cpcv_all25_1h.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_all25_btc_eth_1d.csv`

`result` · 52 lines · 3,619 B · description: **derived**

**Purpose.** Generated data: 50 rows x 10 columns (asset, strategy, n_paths, usable_blocks, median_sharpe, q1_sharpe, q3_sharpe, frac_paths_positive...).

**Contents.** Columns: `asset`, `strategy`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `frac_paths_positive`, `median_return`, `total_trades`.

**Use.** `pandas.read_csv('research/results/cpcv_all25_btc_eth_1d.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_all25_doge_zec_1d.csv`

`result` · 52 lines · 6,153 B · description: **derived**

**Purpose.** Generated data: 50 rows x 10 columns (asset, strategy, n_paths, usable_blocks, median_sharpe, q1_sharpe, q3_sharpe, frac_paths_positive...).

**Contents.** Columns: `asset`, `strategy`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `frac_paths_positive`, `median_return`, `total_trades`.

**Use.** `pandas.read_csv('research/results/cpcv_all25_doge_zec_1d.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_all25_sol_doge_zec_1d.csv`

`result` · 77 lines · 9,194 B · description: **derived**

**Purpose.** Generated data: 75 rows x 10 columns (asset, strategy, n_paths, usable_blocks, median_sharpe, q1_sharpe, q3_sharpe, frac_paths_positive...).

**Contents.** Columns: `asset`, `strategy`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `frac_paths_positive`, `median_return`, `total_trades`.

**Use.** `pandas.read_csv('research/results/cpcv_all25_sol_doge_zec_1d.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_combos_pbo.json`

`result` · 97 lines · 1,288 B · description: **derived**

**Purpose.** Generated JSON array, 6 entries.

**Use.** `json.load(open('research/results/cpcv_combos_pbo.json'))`

#### `research/results/cpcv_combos_results.csv`

`result` · 1214 lines · 235,511 B · description: **derived**

**Purpose.** Generated data: 1212 rows x 16 columns (horizon, kind, label, mode, family, n_paths, usable_blocks, median_sharpe...).

**Contents.** Columns: `horizon`, `kind`, `label`, `mode`, `family`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr_spread`, `frac_paths_positive`, `median_path_return`, `total_trades`, `insufficient`, `reason`.

**Use.** `pandas.read_csv('research/results/cpcv_combos_results.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_combos_tables.md`

`result` · 145 lines · 12,314 B · description: **extracted**

**Purpose.** _Top 15 of 320 evaluable shown._ _Top 15 of 61 evaluable shown._ _Top 15 of 297 evaluable shown._

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/cpcv_pbo.json`

`result` · 127 lines · 2,601 B · description: **derived**

**Purpose.** Generated JSON array, 3 entries.

**Use.** `json.load(open('research/results/cpcv_pbo.json'))`

#### `research/results/cpcv_results.csv`

`result` · 77 lines · 13,395 B · description: **derived**

**Purpose.** Generated data: 75 rows x 15 columns (horizon, strategy, label, family, n_paths, usable_blocks, median_sharpe, q1_sharpe...).

**Contents.** Columns: `horizon`, `strategy`, `label`, `family`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr_spread`, `frac_paths_positive`, `median_path_return`, `total_trades`, `insufficient`, `reason`.

**Use.** `pandas.read_csv('research/results/cpcv_results.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_tables.md`

`result` · 94 lines · 7,055 B · description: **curated**

**Purpose.** Generated Markdown tables from the CPCV sweep — the human-readable face of `cpcv_results.csv`, including the IQR column the headline medians must be read against.

**Use.** Regenerate with `python3 research/cpcv_sweep.py`. Read alongside `research/RANKED_LISTS.md`.

#### `research/results/cpcv_top5_sol_doge_zec_1d.csv`

`result` · 17 lines · 2,599 B · description: **derived**

**Purpose.** Generated data: 15 rows x 14 columns (asset, rank, label, horizon, sol_median_sharpe, median_sharpe, delta_vs_sol, q1_sharpe...).

**Contents.** Columns: `asset`, `rank`, `label`, `horizon`, `sol_median_sharpe`, `median_sharpe`, `delta_vs_sol`, `q1_sharpe`, `q3_sharpe`, `frac_paths_positive`, `median_return`, `total_trades`, `n_paths`, `usable_blocks`.

**Use.** `pandas.read_csv('research/results/cpcv_top5_sol_doge_zec_1d.csv')` — regenerate with the driver that names it.

#### `research/results/geometry_long_k2.csv`

`result` · 177 lines · 10,235 B · description: **derived**

**Purpose.** Generated data: 175 rows x 7 columns (horizon, blocks, k, strategy, median_sharpe, frac_positive, trades).

**Contents.** Columns: `horizon`, `blocks`, `k`, `strategy`, `median_sharpe`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/geometry_long_k2.csv')` — regenerate with the driver that names it.

#### `research/results/geometry_long_k2.json`

`result` · 52 lines · 725 B · description: **derived**

**Purpose.** Generated JSON array, 7 entries.

**Use.** `json.load(open('research/results/geometry_long_k2.json'))`

#### `research/results/geometry_long_k2.txt`

`result` · 61 lines · 4,420 B · description: **derived**

**Purpose.** Generated report. Opens: CPCV GEOMETRY SWEEP — long horizon, k=2 / block counts: 6, 7, 8, 9, 10, 11, 12

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/geometry_medium_k2.csv`

`result` · 177 lines · 10,708 B · description: **derived**

**Purpose.** Generated data: 175 rows x 7 columns (horizon, blocks, k, strategy, median_sharpe, frac_positive, trades).

**Contents.** Columns: `horizon`, `blocks`, `k`, `strategy`, `median_sharpe`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/geometry_medium_k2.csv')` — regenerate with the driver that names it.

#### `research/results/geometry_medium_k2.json`

`result` · 52 lines · 742 B · description: **derived**

**Purpose.** Generated JSON array, 7 entries.

**Use.** `json.load(open('research/results/geometry_medium_k2.json'))`

#### `research/results/geometry_medium_k2.txt`

`result` · 61 lines · 4,388 B · description: **derived**

**Purpose.** Generated report. Opens: CPCV GEOMETRY SWEEP — medium horizon, k=2 / block counts: 6, 7, 8, 9, 10, 11, 12

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/geometry_short_k2.csv`

`result` · 177 lines · 10,438 B · description: **derived**

**Purpose.** Generated data: 175 rows x 7 columns (horizon, blocks, k, strategy, median_sharpe, frac_positive, trades).

**Contents.** Columns: `horizon`, `blocks`, `k`, `strategy`, `median_sharpe`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/geometry_short_k2.csv')` — regenerate with the driver that names it.

#### `research/results/geometry_short_k2.json`

`result` · 52 lines · 747 B · description: **derived**

**Purpose.** Generated JSON array, 7 entries.

**Use.** `json.load(open('research/results/geometry_short_k2.json'))`

#### `research/results/geometry_short_k2.txt`

`result` · 61 lines · 4,369 B · description: **derived**

**Purpose.** Generated report. Opens: CPCV GEOMETRY SWEEP — short horizon, k=2 / block counts: 6, 7, 8, 9, 10, 11, 12

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/ladder_grid_sol.csv`

`result` · 20 lines · 2,698 B · description: **derived**

**Purpose.** Generated data: 18 rows x 18 columns (interval, mode, block, bars, lower, upper, capital_deployed, round_trips...).

**Contents.** Columns: `interval`, `mode`, `block`, `bars`, `lower`, `upper`, `capital_deployed`, `round_trips`, `realized_usd`, `pct_of_deployed`, `grid_total_return`, `grid_max_drawdown`, `hold_total_return`, `hold_max_drawdown`, `pct_bars_outside_ladder`, `buys`, `sells`, `forced_exit_qty`.

**Use.** `pandas.read_csv('research/results/ladder_grid_sol.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_all_singles_long.csv`

`result` · 27 lines · 3,018 B · description: **derived**

**Purpose.** Generated data: 25 rows x 10 columns (horizon, label, median_sharpe, iqr, max_abs_delta, ratio_to_iqr, sign_flips, perturbations...).

**Contents.** Columns: `horizon`, `label`, `median_sharpe`, `iqr`, `max_abs_delta`, `ratio_to_iqr`, `sign_flips`, `perturbations`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/perturb_all_singles_long.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_all_singles_long.txt`

`result` · 35 lines · 2,331 B · description: **derived**

**Purpose.** Generated report. Opens: PERTURBATION STABILITY — every single strategy, long horizon / perturbation: +/-10% one at a time; ratio = max|delta median| / baseline path IQR

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_all_singles_medium.csv`

`result` · 27 lines · 3,120 B · description: **derived**

**Purpose.** Generated data: 25 rows x 10 columns (horizon, label, median_sharpe, iqr, max_abs_delta, ratio_to_iqr, sign_flips, perturbations...).

**Contents.** Columns: `horizon`, `label`, `median_sharpe`, `iqr`, `max_abs_delta`, `ratio_to_iqr`, `sign_flips`, `perturbations`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/perturb_all_singles_medium.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_all_singles_medium.txt`

`result` · 35 lines · 2,333 B · description: **derived**

**Purpose.** Generated report. Opens: PERTURBATION STABILITY — every single strategy, medium horizon / perturbation: +/-10% one at a time; ratio = max|delta median| / baseline path IQR

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_all_singles_short.csv`

`result` · 27 lines · 3,025 B · description: **derived**

**Purpose.** Generated data: 25 rows x 10 columns (horizon, label, median_sharpe, iqr, max_abs_delta, ratio_to_iqr, sign_flips, perturbations...).

**Contents.** Columns: `horizon`, `label`, `median_sharpe`, `iqr`, `max_abs_delta`, `ratio_to_iqr`, `sign_flips`, `perturbations`, `frac_positive`, `trades`.

**Use.** `pandas.read_csv('research/results/perturb_all_singles_short.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_all_singles_short.txt`

`result` · 35 lines · 2,368 B · description: **derived**

**Purpose.** Generated report. Opens: PERTURBATION STABILITY — every single strategy, short horizon / perturbation: +/-10% one at a time; ratio = max|delta median| / baseline path IQR

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_all_dual_momentum_vol_regime.csv`

`result` · 15 lines · 1,469 B · description: **derived**

**Purpose.** Generated data: 13 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_all_dual_momentum_vol_regime.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_all_dual_momentum_vol_regime.json`

`result` · 11 lines · 274 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_all_dual_momentum_vol_regime.json'))`

#### `research/results/perturb_long_all_dual_momentum_vol_regime.txt`

`result` · 27 lines · 1,979 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : all(dual_momentum+vol_regime)

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_all_macd_vol_regime.csv`

`result` · 15 lines · 1,407 B · description: **derived**

**Purpose.** Generated data: 13 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_all_macd_vol_regime.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_all_macd_vol_regime.json`

`result` · 11 lines · 265 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_all_macd_vol_regime.json'))`

#### `research/results/perturb_long_all_macd_vol_regime.txt`

`result` · 25 lines · 1,678 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : all(macd+vol_regime)

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_any_adx_trend_ou_reversion.csv`

`result` · 13 lines · 1,276 B · description: **derived**

**Purpose.** Generated data: 11 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_any_adx_trend_ou_reversion.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_any_adx_trend_ou_reversion.json`

`result` · 11 lines · 273 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_any_adx_trend_ou_reversion.json'))`

#### `research/results/perturb_long_any_adx_trend_ou_reversion.txt`

`result` · 25 lines · 1,843 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : any(adx_trend+ou_reversion)

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_any_hurst_switch_ou_reversion.csv`

`result` · 15 lines · 1,485 B · description: **derived**

**Purpose.** Generated data: 13 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_any_hurst_switch_ou_reversion.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_any_hurst_switch_ou_reversion.json`

`result` · 11 lines · 274 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_any_hurst_switch_ou_reversion.json'))`

#### `research/results/perturb_long_any_hurst_switch_ou_reversion.txt`

`result` · 27 lines · 2,024 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : any(hurst_switch+ou_reversion)

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_any_ou_reversion_obv_trend.csv`

`result` · 11 lines · 1,094 B · description: **derived**

**Purpose.** Generated data: 9 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_any_ou_reversion_obv_trend.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_any_ou_reversion_obv_trend.json`

`result` · 11 lines · 271 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_any_ou_reversion_obv_trend.json'))`

#### `research/results/perturb_long_any_ou_reversion_obv_trend.txt`

`result` · 23 lines · 1,670 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : any(ou_reversion+obv_trend)

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_obv_trend.csv`

`result` · 5 lines · 387 B · description: **derived**

**Purpose.** Generated data: 3 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_obv_trend.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_obv_trend.json`

`result` · 11 lines · 253 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_obv_trend.json'))`

#### `research/results/perturb_long_obv_trend.txt`

`result` · 17 lines · 1,081 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : obv_trend

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/perturb_long_vol_regime.csv`

`result` · 9 lines · 837 B · description: **derived**

**Purpose.** Generated data: 7 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_long_vol_regime.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_long_vol_regime.json`

`result` · 11 lines · 254 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_long_vol_regime.json'))`

#### `research/results/perturb_long_vol_regime.txt`

`result` · 21 lines · 1,469 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : vol_regime

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/sweep_results.csv`

`result` · 522 lines · 155,426 B · description: **derived**

**Purpose.** Generated data: 520 rows x 21 columns (label, kind, horizon, families, mode, rankable, full_return, full_sharpe...).

**Contents.** Columns: `label`, `kind`, `horizon`, `families`, `mode`, `rankable`, `full_return`, `full_sharpe`, `full_maxdd`, `full_trades`, `full_exposure`, `is_return`, `is_sharpe`, `is_maxdd`, `is_trades`, `is_exposure`, `oos_return`, `oos_sharpe`, `oos_maxdd`, `oos_trades`, `oos_exposure`.

**Use.** `pandas.read_csv('research/results/sweep_results.csv')` — regenerate with the driver that names it.

#### `research/results/tables.md`

`result` · 157 lines · 15,951 B · description: **extracted**

**Purpose.** _1 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`._ _15 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(breakout+rsi)`, `all(breakout+stochastic)`, `all(breakout+bb_reversion)`, `all(breakout+zscore)`, `all(breakout+vwap_reversion)`, `all(bb_breakout+rsi)`, `all(bb_breakout+stochastic)`, `all(bb_breakout+bb_

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/top_coins.csv`

`result` · 17 lines · 926 B · description: **derived**

**Purpose.** Generated data: 15 rows x 8 columns (rank, symbol, name, price_usd, market_cap_usd, volume_24h_usd, pegged, local_data).

**Contents.** Columns: `rank`, `symbol`, `name`, `price_usd`, `market_cap_usd`, `volume_24h_usd`, `pegged`, `local_data`.

**Use.** `pandas.read_csv('research/results/top_coins.csv')` — regenerate with the driver that names it.

---

## extension

The Chrome extension, and the only component that can place a real order. Dry-run is the default, risk rails live in code and fail closed, and a fresh install must not be able to trade.

33 files.

#### `extension/README.md`

`doc` · 412 lines · 24,396 B · description: **extracted**

**Purpose.** A Chrome MV3 extension that runs a **grid trading strategy on Jupiter (Solana)** with hard risk rails and full P&L tracking. **Dry-run by default** — it will not place an order until you change the mode and type a confirmation.

**Use.** Read it.

#### `extension/manifest.json`

`config` · 26 lines · 751 B · description: **curated**

**Purpose.** MV3 manifest: permissions, the service worker entry point, and the UI surfaces. The permission list is the extension's blast radius, so review any addition against `docs/SECURITY.md`.

**Use.** Load unpacked from `extension/` in `chrome://extensions`.

#### `extension/package.json`

`config` · 21 lines · 516 B · description: **curated**

**Purpose.** Node scripts for the extension's test and tooling surfaces.

**Use.** `npm test` inside `extension/`.

### `extension/src/bg/`

#### `extension/src/bg/service-worker.js`

`code-js` · 179 lines · 6,679 B · description: **extracted**

**Purpose.** MV3 service worker — the extension surface of the command registry. There is no long-lived process here. The worker is woken by an alarm, runs one tick, and is free to die. Nothing may be held in module scope that the next tick depends on: everything durable lives in IndexedDB or chrome.storage.local, and the tick rebuilds its world from those plus the venue's live state.

**Contents.** Defines `ALARM`, `ALIASES`, `MIN_PERIOD_MINUTES`, `chromeDeps`, `handleMessage`, `paintBadge`, `rescheduleAlarm`, `runTick`, `setBadge`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/core/`

#### `extension/src/core/commands.js`

`code-js` · 486 lines · 17,557 B · description: **extracted**

**Purpose.** The command registry — single source of truth for every action this project can perform. Three surfaces drive this one registry: extension src/bg/service-worker.js (chrome.runtime messages) CLI tools/cli.js (argv) HTTP API tools/api-server.js (POST /v1/<command>) Nothing may be reachable from one surface and not the others.

**Contents.** Defines `COMMANDS`, `COMMAND_NAMES`, `TYPE`, `class CommandError`, `currentPrice`, `describeCommands`, `pnlSnapshot`, `runCommand`, `summarisePnl`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/engine.js`

`code-js` · 422 lines · 16,220 B · description: **extracted**

**Purpose.** The tick. Order of operations is the whole design: RECONCILE before PLAN, always. A MV3 service worker can be killed at any moment, including between "write the intent" and "the venue accepted the order". So the venue's live order list — not our local records — is the source of truth at the top of every tick. Local state is a cache and a journal, nothing more.

**Contents.** Defines `PRICE_MATCH_TOLERANCE`, `ingestFills`, `keyForLiveOrder`, `matchIntent`, `pricesMatch`, `reconcile`, `summarise`, `tick`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/grid.js`

`code-js` · 268 lines · 9,331 B · description: **extracted**

**Purpose.** Pure grid-strategy engine. No I/O, no chrome.* APIs, no network. Everything here is a deterministic function of (config, price, open state) so the whole strategy is unit testable and a service-worker restart can recompute intent from scratch.

**Contents.** Defines `DIRECTION`, `SIDE`, `SPACING`, `capitalRequirement`, `expectedRoundTripUsd`, `gridLevels`, `intentKey`, `nearestLevelIndex`, `pairedExitLevel`, `planGrid` and 2 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/pnl.js`

`code-js` · 214 lines · 7,006 B · description: **extracted**

**Purpose.** P&L accounting. Realized P&L uses FIFO lot matching: a sell fill is matched against the oldest unmatched buy lots, which is both the IRS default for property and the convention every crypto tax tool expects, so the CSV export lines up with whatever you reconcile against later. Costs are never optional.

**Contents.** Defines `equityCurve`, `fillsToCsv`, `matchFifo`, `maxDrawdown`, `snapshot`, `totalCarryUsd`, `winRate`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/risk.js`

`code-js` · 189 lines · 6,624 B · description: **extracted**

**Purpose.** Risk rails. Every rail is enforced here, in code, as a gate the executor must pass before anything is submitted. A rail that lives only in the README is not a rail. `evaluate()` is pure so the dashboard can show exactly which rail would block a grid before you arm it.

**Contents.** Defines `DEFAULT_LIMITS`, `RAILS`, `VERDICT`, `admitBatch`, `dayKey`, `evaluate`, `normaliseState`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/jupiter/`

#### `extension/src/jupiter/attribution.js`

`code-js` · 61 lines · 2,682 B · description: **extracted**

**Purpose.** Licence-required attribution, in one place. The Jupiter SDK & API License Agreement (read 2026-08-04) imposes two display obligations that are easy for a private tool to miss, because nobody else sees the UI: §8.4 the product "shall prominently display to end users ... 'Powered by Jupiter'".

**Contents.** Defines `POWERED_BY`, `ROUTING_API`, `ROUTING_NOTE`, `SURFACES`, `attributionDetail`, `attributionLine`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/http.js`

`code-js` · 157 lines · 5,163 B · description: **extracted**

**Purpose.** HTTP layer for the Jupiter APIs. A grid ticking every 30s across N rungs will hit rate limits on the free tier, so retry/backoff and a per-tick request budget are part of the client rather than something callers remember to add.

**Contents.** Defines `DEFAULT_TIMEOUT_MS`, `RETRYABLE_STATUS`, `backoffDelayMs`, `class JupiterHttpError`, `class RequestBudget`, `headers`, `request`, `safePath`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/price.js`

`code-js` · 86 lines · 2,853 B · description: **extracted**

**Purpose.** Price lookup. Two shapes have shipped across Price API versions (`{ <mint>: {...} }` in v3, `{ data: { <mint>: {...} } }` in v2). The parser accepts either and throws a named error on anything else, so a version bump surfaces as one clear failure instead of `undefined` propagating into order sizing.

**Contents.** Defines `PRICE_HOSTS`, `class PriceShapeError`, `getDecimals`, `getPriceTable`, `getPrices`, `parsePrices`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/trigger.js`

`code-js` · 305 lines · 10,165 B · description: **extracted**

**Purpose.** Jupiter Trigger V2 client. Endpoint shapes below are transcribed from the live docs (verified 2026-08-04): https://developers.jup.ag/docs/trigger https://developers.jup.ag/docs/trigger/create-order https://developers.jup.ag/docs/trigger/authentication https://developers.jup.ag/docs/trigger/deposit https://developers.jup.ag/docs/trigger/manage-orders Flow: authenticate -> resolve vault -> craft dep

**Contents.** Defines `CONDITION`, `ORDER_TYPE`, `TRIGGER_BASE`, `TRIGGER_LIMITS`, `confirmCancel`, `craftDeposit`, `createPriceOrder`, `getChallenge`, `initiateCancel`, `listOrders` and 6 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/storage/`

#### `extension/src/storage/fileStore.js`

`code-js` · 157 lines · 4,443 B · description: **extracted**

**Purpose.** Node-side persistence, API-compatible with the browser surfaces. The CLI and HTTP API need the same durability the extension gets from IndexedDB + chrome.storage.local, so this provides: FileStore the Store API (intents, fills, carry, events) on a JSON file createFileArea a chrome.storage.local-shaped {get,set} on a JSON file, so ConfigStore works unchanged outside the browser Writes go through a

**Contents.** Defines `DEFAULT_CONFIG_PATH`, `DEFAULT_DATA_DIR`, `DEFAULT_STORE_PATH`, `class FileStore`, `createFileArea`, `readJson`, `writeJsonAtomic`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/storage/memoryStore.js`

`code-js` · 73 lines · 1,699 B · description: **extracted**

**Purpose.** In-memory Store, API-compatible with the IndexedDB one. Exists so the tick can run headless — under `node --test` and in tools/dryrun.js — without Chrome or a fake IndexedDB. The engine takes its store as a dependency precisely so this substitution is possible.

**Contents.** Defines `class MemoryStore`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/storage/store.js`

`code-js` · 249 lines · 7,777 B · description: **extracted**

**Purpose.** Persistence. Two surfaces, chosen by what the data is: chrome.storage.local — config and limits. Small, synchronously readable at worker start, and NEVER `.sync` (that would push settings, and anything near them, to Google's servers). IndexedDB — the intent journal and fill log.

**Contents.** Defines `CONFIG_KEY`, `DB_NAME`, `DB_VERSION`, `DEFAULT_CONFIG`, `INTENT_STATUS`, `RUNTIME_KEY`, `STORES`, `class ConfigStore`, `class Store`, `openDb` and 1 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/ui/`

#### `extension/src/ui/dashboard.html`

`code-web` · 154 lines · 6,534 B · description: **curated**

**Purpose.** Full-page dashboard shell for open state, ladder rungs and recent ticks. Markup only.

**Use.** Opened from the popup.

#### `extension/src/ui/dashboard.js`

`code-js` · 341 lines · 12,089 B · description: **extracted**

**Purpose.** Dashboard: configuration, risk rails, journal, and P&L. Charts are hand-built SVG rather than a charting library, because the extension CSP forbids remote script and bundling one for two charts is not worth the weight. Both carry text alternatives so the numbers are reachable without reading the picture.

**Contents.** Defines `PAD`, `appendRow`, `emptyRow`, `equitySvg`, `fillForm`, `ladderSvg`, `readForm`, `refresh`, `renderBanner`, `renderCapital` and 3 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/popup.html`

`code-web` · 67 lines · 2,016 B · description: **curated**

**Purpose.** Browser-action popup shell — status at a glance and the dry-run toggle. Markup only; behaviour lives in the JS modules.

**Use.** Opens from the toolbar icon.

#### `extension/src/ui/popup.js`

`code-js` · 126 lines · 4,727 B · description: **extracted**

**Purpose.** Popup: status at a glance, plus arm / disarm / kill. All state comes from the service worker over messages. The popup holds no strategy logic — it can be closed mid-tick without consequence, and it must never be the thing that decides whether an order is placed.

**Contents.** Defines `act`, `paintPnl`, `refresh`, `showError`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/ui.css`

`code-web` · 118 lines · 4,258 B · description: **curated**

**Purpose.** Shared styling for both surfaces, kept in one file so the popup and dashboard cannot drift visually.

**Use.** Linked by the HTML; nothing to run.

### `extension/src/venues/`

#### `extension/src/venues/index.js`

`code-js` · 238 lines · 7,999 B · description: **extracted**

**Purpose.** Venue layer. The grid engine is venue-agnostic: it emits intents, and a venue adapter turns them into orders. That seam exists because the two candidate venues on Jupiter are in very different states of readiness: Trigger V2 — REST, returns signable transactions. Live-capable today. SPOT. Perps — NO public REST write API as of 2026-08-04.

**Contents.** Defines `MODE`, `buildVenue`, `class DryRunVenue`, `class NotImplemented`, `class PerpsVenueReadOnly`, `leverageFeasibility`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/venues/triggerVenue.js`

`code-js` · 443 lines · 16,186 B · description: **extracted**

**Purpose.** Jupiter Trigger V2 venue adapter. This is the only venue that can currently place live orders: Trigger returns a signable transaction over HTTP. A grid is a ladder of resting price orders, which is exactly what this API is for, and V2 keeps pending orders off-chain so the ladder is not a public roadmap for front-runners. Leverage note: Trigger is a SPOT venue.

**Contents.** Defines `MARGIN_SOURCE`, `ORDER_LIST_KEYS`, `ORDER_REQUIRED_FIELDS`, `class OrderEnvelopeError`, `class TriggerVenue`, `normaliseOrders`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/wallet/`

#### `extension/src/wallet/signer.js`

`code-js` · 252 lines · 9,002 B · description: **extracted**

**Purpose.** Signing. Three honest modes, because "unattended bot" and "wallet popup per trade" are mutually exclusive and pretending otherwise ships a broken default: DRY_RUN nothing is ever signed. The signer throws if asked. SEMI_AUTO the worker prepares the transaction and queues it; a human approves each one in the dashboard. Safe, not unattended.

**Contents.** Defines `IV_BYTES`, `KDF_ITERATIONS`, `PENDING_KEY`, `PKCS8_ED25519_PREFIX`, `SALT_BYTES`, `SIGNER_KIND`, `VAULT_KEY`, `base64UrlToBytes`, `class NullSigner`, `class PendingApproval` and 8 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/wallet/solana.js`

`code-js` · 204 lines · 6,356 B · description: **extracted**

**Purpose.** Minimal Solana wire-format helpers. Hand-rolled instead of pulling in @solana/web3.js because the extension needs exactly two things — base58 and inserting a signature into an already-built transaction — and shipping a megabyte of bundled dependencies into a service worker for that is a poor trade. The transaction itself is always built by Jupiter; we never construct instructions.

**Contents.** Defines `B58_ALPHABET`, `B58_MAP`, `CHUNK`, `base58Decode`, `base58Encode`, `base64ToBytes`, `bytesToBase64`, `decodeShortVec`, `encodeShortVec`, `messageSigners` and 2 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/test/`

#### `extension/test/core.test.js`

`code-js` · 1092 lines · 40,052 B · description: **curated**

**Purpose.** Node test-runner suite for the pure core — grid maths, planner, reconciler. No `chrome.*`, so it runs headless.

**Contents.** Defines `CONFIG`, `ORDER`, `RECON_CONFIG`, `STATE`, `seedResting`.

**Use.** `node --test extension/test/` or `npm test` in `extension/`.

#### `extension/test/surfaces.test.js`

`code-js` · 376 lines · 13,984 B · description: **curated**

**Purpose.** Covers the command registry as driven by each surface (popup, dashboard, CLI), so one registry change cannot silently break one caller.

**Contents.** Defines `CLI`, `ROOT`, `TOKEN`, `run`, `testDeps`, `withServer`.

**Use.** `node --test extension/test/`.

#### `extension/test/wallet.test.js`

`code-js` · 252 lines · 9,200 B · description: **curated**

**Purpose.** Wallet and signing path tests, including the refusals — the cases that must NOT produce a transaction.

**Contents.** Defines `SOL_MINT`, `SYSTEM_PROGRAM`, `USDC_MINT`, `concat`, `fakeTx`.

**Use.** `node --test extension/test/`.

### `extension/tools/`

#### `extension/tools/api-server.js`

`code-js` · 251 lines · 8,812 B · description: **extracted**

**Purpose.** HTTP API surface. Routes are generated from the registry in src/core/commands.js — the same registry the CLI and the extension use — so no endpoint can drift from the extension's behaviour.

**Contents.** Defines `MAX_BODY_BYTES`, `coerceQuery`, `createApiServer`, `createRequestHandler`, `main`, `parseArgs`, `readJsonBody`, `send`, `tokenMatches`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/cli.js`

`code-js` · 217 lines · 6,971 B · description: **extracted**

**Purpose.** CLI surface. Every command is generated from the registry in src/core/commands.js, so this file contains no per-command logic and cannot fall behind the extension. Add a command there and it appears here, in the help text, and in the HTTP API.

**Contents.** Defines `GLOBAL_FLAGS`, `coerce`, `commandHelp`, `helpText`, `main`, `parseArgv`, `render`, `summariseSkips`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/deps.js`

`code-js` · 67 lines · 2,395 B · description: **extracted**

**Purpose.** Node dependency wiring for the command registry. The CLI and the HTTP API share this so they behave identically — the only difference between the two surfaces is how arguments arrive. Kept out of src/ because it imports node:fs, which would break the extension bundle if it were ever pulled into a browser context.

**Contents.** Defines `createNodeDeps`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/dryrun.js`

`code-js` · 150 lines · 5,421 B · description: **extracted**

**Purpose.** Headless dry run. Runs the real tick — real Jupiter price, real grid engine, real risk rails, real journal — with simulated fills, in Node. This is the integration gate: loading an unpacked extension cannot be automated (chrome://extensions needs a human), so end-to-end verification happens here instead.

**Contents.** Defines `class ScriptedPriceVenue`, `main`, `parseArgs`, `round`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/verify-endpoints.js`

`code-js` · 80 lines · 3,155 B · description: **extracted**

**Purpose.** Live endpoint check. Confirms the read-side assumptions this extension hardcodes still hold, so a Jupiter API change surfaces here rather than mid-tick. Read-only: nothing is signed, deposited, or ordered. node tools/verify-endpoints.js JUPITER_API_KEY=... node tools/verify-endpoints.js # also checks the keyed tier

**Contents.** Defines `MINTS`, `checkPrice`, `checkTriggerReachable`, `report`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

---

## soltui

The macOS menu-bar app that surfaces state locally. Packaged with py2app and supervised by launchd.

20 files.

#### `soltui/README.md`

`doc` · 122 lines · 5,922 B · description: **extracted**

**Purpose.** A five-tab Textual TUI plus a macOS menu-bar indicator over the backtester. Structured like `~/dev/net-dns-monitor`: pure, tested logic modules with a thin wiring shell.

**Use.** Read it.

#### `soltui/SolTUI.icns`

`other` · 0 lines · 370,625 B · description: **curated**

**Purpose.** macOS app icon for the packaged bundle.

**Use.** Referenced by the py2app build; nothing to run.

#### `soltui/__init__.py`

`code-python` · 0 lines · 0 B · description: **curated**

**Purpose.** Package marker for the menu-bar app. Empty.

**Use.** Nothing to run.

#### `soltui/app.py`

`code-python` · 168 lines · 5,933 B · description: **extracted**

**Purpose.** macOS menu-bar shell. Thin by design. python3 -m soltui.app Mirrors `netdnsmonitor/app.py`: every decision lives in already-tested modules (`status`, `config`, `roster`, `runner`), and this file only wires them to a `rumps.Timer` and a status-item title.

**Contents.** Defines `REPO`, `RESULTS_DIR`, `_rumps()`, `build_app()`, `main()`.

**Use.** `python3 soltui/app.py --help`

#### `soltui/config.py`

`code-python` · 175 lines · 6,883 B · description: **extracted**

**Purpose.** Settings load/save for the TUI. Pure logic; no UI, no I/O beyond one file. Config lives at `~/.config/soltui/config.yaml`, following the same convention as `netdnsmonitor`. YAML is optional at runtime -- if PyYAML is missing the app falls back to JSON at the same path with a `.json` suffix, so a missing optional dependency degrades rather than crashes.

**Contents.** Defines `CONFIG_DIR`, `CONFIG_PATH`, `CONFIG_PATH_JSON`, `INTERVALS`, `MODES`, `class ConfigError`, `class Settings`, `default_settings()`, `validate()`, `load_settings()` and 3 more.

**Use.** `import soltui.config`

#### `soltui/make_icon.py`

`code-python` · 281 lines · 10,446 B · description: **extracted**

**Purpose.** Generate the SolTUI app icon: a tree of life whose roots are the Solana mark. python3 soltui/make_icon.py # writes soltui/SolTUI.icns python3 soltui/make_icon.py --preview # also writes a 512px PNG to look at ## The design constraint that drives everything The icon has to work at **16px** (menu bar, Finder list, Cmd-Tab at small sizes), not at 1024. A finely detailed tree becomes mush there.

**Contents.** Defines `HERE`, `PURPLE`, `GREEN`, `BACKDROP`, `SS`, `BASE`, `ICONSET`, `vertical_gradient()`, `rounded_tile()`, `draw_branches()` and 5 more.

**Use.** `python3 soltui/make_icon.py --help`

#### `soltui/menubar_launcher.py`

`code-python` · 52 lines · 1,919 B · description: **extracted**

**Purpose.** py2app entry point for the menu-bar app. ## Why this file exists py2app executes its target as a **top-level script**, not as a module inside a package.

**Contents.** Defines `REPO`. Depends on `soltui`.

**Use.** `import soltui.menubar_launcher`

#### `soltui/paper.py`

`code-python` · 198 lines · 6,741 B · description: **extracted**

**Purpose.** Dry-run simulator for the Execute tab. ## Why this is a replay and not a live loop The obvious design -- step forward bar by bar and compute fills as you go -- would create a SECOND order-execution path alongside `backtester/core/engine.py`.

**Contents.** Defines `MODE_LABEL`, `class IntendedFill`, `class PaperSession`, `start_session()`. Depends on `backtester`.

**Use.** `import soltui.paper`

#### `soltui/requirements.txt`

`data` · 17 lines · 726 B · description: **curated**

**Purpose.** Runtime dependencies for the menu-bar app (rumps/pyobjc and the py2app build tooling).

**Use.** `python3 -m pip install -r soltui/requirements.txt`.

#### `soltui/roster.py`

`code-python` · 165 lines · 5,965 B · description: **extracted**

**Purpose.** The user's strategy roster: which strategies are active, with what parameters. Backs the Strategies tab. Kept pure so add/remove is testable without a UI. Two invariants worth stating, because both prevent a class of confusing failure later rather than at the point of the mistake: 1.

**Contents.** Defines `class RosterError`, `class RosterEntry`, `class Roster`, `available_strategies()`. Depends on `backtester`.

**Use.** `import soltui.roster`

#### `soltui/runner.py`

`code-python` · 254 lines · 8,481 B · description: **extracted**

**Purpose.** Background sweep runner. Turns a roster into results while keeping the UI live. The menu-bar indicator and the Backtest tab both need "how much is left", which means the sweep has to report progress as it goes rather than blocking until done. This module owns that: a worker thread, a progress callback, and a cancellation flag.

**Contents.** Defines `class SweepRow`, `class SweepOutcome`, `load_arrays()`, `engine_config()`, `class SweepRunner`, `quick_backtest()`. Depends on `backtester`.

**Use.** `import soltui.runner`

#### `soltui/setup_app.py`

`code-python` · 105 lines · 4,141 B · description: **extracted**

**Purpose.** py2app build for the soltui menu-bar app. cd /Users/mitch.hudson/dev/solmargintrader python3 soltui/setup_app.py py2app -A # alias build (recommended, see below) ## Why alias mode A full py2app freeze would have to embed pandas and numpy, which the backtester imports. That is slow, large, and a well-known source of missing-dylib breakage.

**Contents.** Defines `REPO`, `APP_NAME`, `BUNDLE_ID`, `PLIST`, `ICON`, `OPTIONS`, `main()`.

**Use.** `python3 soltui/setup_app.py --help`

#### `soltui/signals.py`

`code-python` · 334 lines · 13,734 B · description: **extracted**

**Purpose.** Editable signal parameters: the tunables behind the Signals tab. ## The model, because it needs to be unambiguous A *signal* is an indicator with a period or threshold (RSI's period, Bollinger's width, MACD's spans). A *strategy* is a rule built on one or more signals. The same signal is shared by several strategies -- `rsi` and any composite containing it both read the RSI period.

**Contents.** Defines `class SignalError`, `class SignalDefaults`, `validate()`, `params_for()`, `merged_params()`, `field_names()`, `coerce()`, `from_dict()`, `mapped_strategies()`.

**Use.** `import soltui.signals`

#### `soltui/soltui-service`

`other` · 314 lines · 11,943 B · description: **curated**

**Purpose.** Install-and-supervise script for the menu-bar app: builds the py2app bundle, writes the launchd agent, and manages the flag file that is the real off switch (because `KeepAlive` necessarily overrides the app's own Quit item).

**Use.** `python3 soltui/soltui-service status|start|stop|build`.

#### `soltui/status.py`

`code-python` · 207 lines · 7,938 B · description: **extracted**

**Purpose.** Pure menu-bar title logic, kept out of the rumps shell so it is testable without a real macOS event loop. Mirrors `netdnsmonitor/status.py`: one pure `build_title()` the app calls every tick, plus the state it reads.

**Contents.** Defines `ICONS`, `MAX_TITLE_CHARS`, `MAX_ACTIVITY_CHARS`, `MAX_ERROR_CHARS`, `class Phase`, `class AppState`, `format_pct()`, `build_title()`, `_shorten()`, `_clip()` and 1 more.

**Use.** `import soltui.status`

#### `soltui/tui.py`

`code-python` · 610 lines · 25,482 B · description: **extracted**

**Purpose.** Textual TUI: five tabs over the backtester. python3 -m soltui.tui Tabs: Settings, Strategies, Signals, Backtest, Execute (dry-run only). All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`, `status`); this file is presentation and wiring.

**Contents.** Defines `FAMILY_NOTES`, `SIGNAL_REFERENCE`, `class SolTuiApp`, `main()`. Depends on `backtester`.

**Use.** `python3 soltui/tui.py --help`

### `soltui/tests/`

#### `soltui/tests/__init__.py`

`test` · 0 lines · 0 B · description: **curated**

**Purpose.** Package marker for the app's tests. Empty.

**Use.** Nothing to run.

#### `soltui/tests/test_signals.py`

`test` · 210 lines · 8,725 B · description: **extracted**

**Purpose.** Tests for editable signal parameters. The load-bearing property: **an explicit per-entry parameter always beats a signal default.** Getting that direction backwards would mean the Signals tab silently overwrites a value the user deliberately pinned in the Strategies tab, and the symptom would be a strategy quietly not doing what its own label says.

**Contents.** Defines `class TestPrecedence`, `class TestMapping`, `class TestValidation`, `class TestCoercion`, `class TestPersistence`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_signals.py -q`

#### `soltui/tests/test_status_roster.py`

`test` · 424 lines · 17,013 B · description: **extracted**

**Purpose.** Tests for the pure soltui layer: indicator title, settings, roster, replay. The load-bearing assertion in this file is that **no money figure in the menu-bar title is ever unlabelled**. A naked '+9.4%' in a status bar reads as a live account balance, and there is no live account. That property is asserted directly rather than left to code review.

**Contents.** Defines `class TestIndicatorTitle`, `class TestMenuSummary`, `class TestSettings`, `class TestRoster`, `class TestPaperSession`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_status_roster.py -q`

#### `soltui/tests/test_tui.py`

`test` · 293 lines · 12,138 B · description: **extracted**

**Purpose.** Smoke tests for the Textual app, driven through Textual's own test harness. An app that imports cleanly but explodes on mount is not working, so these actually mount it, click things, and assert on widget state. `run_test()` runs a headless terminal, so no TTY is required and this is safe in CI.

**Contents.** Defines `TEST_SIZE`, `text_of()`, `make_settings()`, `class TestAppMounts`, `class TestExecuteTabSafety`, `class TestStrategiesTab`, `class TestSignalsTab`, `class TestSettingsTab`, `class TestSignalsTabEditable`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_tui.py -q`

---

## .github

CI. Runs the test suite and the figure verifier.

8 files.

#### `.github/CODEOWNERS`

`ci` · 12 lines · 470 B · description: **curated**

**Purpose.** Review ownership per path. Matters most for the order-placing surface under `extension/` and the risk rails, where an unreviewed change is the expensive kind.

**Use.** Nothing to run; GitHub requests reviewers automatically.

#### `.github/PULL_REQUEST_TEMPLATE.md`

`ci` · 48 lines · 1,812 B · description: **extracted**

**Purpose.** <!-- One or two sentences. What does this do that the repo could not do before? --> Paste the actual output, not a claim that it passed. python3 -m unittest discover -s backtester/tests -t .

**Use.** Read it.

#### `.github/SECURITY.md`

`ci` · 35 lines · 1,745 B · description: **extracted**

**Purpose.** This is a personal repository with no deployed service and no users other than its author. There is no security mailbox and no disclosure SLA. Report anything you find by opening an issue, or directly to the repository owner.

**Use.** Read it.

#### `.github/copilot-instructions.md`

`ci` · 87 lines · 4,442 B · description: **extracted**

**Purpose.** Read [CLAUDE.md](../CLAUDE.md) before proposing a change. It is the source of truth for this repository; this file is a pointer plus the rules that get broken most often. 1. **Identify the component first.** The correct level of caution differs by an order of

**Use.** Read it.

#### `.github/dependabot.yml`

`ci` · 32 lines · 957 B · description: **curated**

**Purpose.** Dependency update schedule. The dependency surface here is deliberately thin — pandas and numpy for the engine, node built-ins for the extension — so updates should be few and individually reviewable.

**Use.** Nothing to run; GitHub opens PRs on the configured schedule.

### `.github/ISSUE_TEMPLATE/`

#### `.github/ISSUE_TEMPLATE/bug_report.md`

`ci` · 37 lines · 825 B · description: **extracted**

**Purpose.** <!-- Actual behaviour. Paste real output; quote the shortest decisive line. --> <!-- Which doc, test, or strategy card states the expected behaviour? -->

**Use.** Read it.

#### `.github/ISSUE_TEMPLATE/feature_request.md`

`ci` · 27 lines · 833 B · description: **extracted**

**Purpose.** <!-- Which component, and what question can you not currently answer / what can you not currently do? --> <!-- The important part. For a strategy: what would show it is not curve-fit?

**Use.** Read it.

### `.github/workflows/`

#### `.github/workflows/ci.yml`

`ci` · 138 lines · 4,353 B · description: **curated**

**Purpose.** The gate. Runs the Python suite and `research/verify_numbers.py`, so a documented figure that no longer matches its result file fails the build rather than surviving in prose.

**Use.** Runs on push. Reproduce locally with `python3 -m pytest backtester/tests -q` and `python3 research/verify_numbers.py`.

---

## tradingskilllist

An inventory of the trading, finance and crypto skills the research drew on.

1 files.

#### `tradingskilllist/trading-skills.md`

`doc` · 186 lines · 8,063 B · description: **extracted**

**Purpose.** Counts are read from the filesystem, not transcribed — regenerate with the script in this directory's sibling note. Skill *descriptions* in a live session have reported inconsistent spoke counts for the trading hub (23, 27, 34, 35 within one session); the filesystem is the

**Use.** Read it.

---

## .remember

Session handoff notes, newest first. Prose, not machine-read.

1 files.

#### `.remember/remember.md`

`doc` · 786 lines · 44,628 B · description: **extracted**

**Purpose.** Run unchanged on DOGE and ZEC, **all ten transfers degraded and not one improved** (median −0.821 DOGE, −0.753 ZEC). Only #3 `any(ou_reversion+obv_trend)` and #4 `obv_trend_60` stayed positive on all three assets. On ZEC, zero-parameter `buy_and_hold` (+0.659) beat all five, the

**Use.** Read it.

---

## scripts

2 files.

#### `scripts/build_doc_index.py`

`code-python` · 180 lines · 6,231 B · description: **extracted**

**Purpose.** Generate `docs/high_signal_file_index.json` from `docs/codebase-overview.md`. python3 scripts/build_doc_index.py The overview is the human-readable file map; the JSON is the machine-readable one for LLM retrieval.

**Contents.** Defines `REPO`, `OVERVIEW`, `INDEX`, `COMPONENTS`, `ROW`, `KIND_BY_SUFFIX`, `git_ok()`, `is_tracked()`, `is_ignored()`, `excluded()` and 4 more.

**Use.** `python3 scripts/build_doc_index.py --help`

#### `scripts/check_docs.py`

`code-python` · 321 lines · 11,892 B · description: **extracted**

**Purpose.** Fail the build when the docs drift from the repo. python3 scripts/check_docs.py python3 scripts/check_docs.py --prune # drop dead index entries Two kinds of rot, both of which happened here before this existed: * **Stale test counts.** The docs claimed 250 backtester tests for several commits while the suite had grown to 454.

**Contents.** Defines `REPO`, `COUNT_DOCS`, `INDEX_JSON`, `OVERVIEW_MD`, `is_ignored()`, `is_tracked()`, `missing_and_tracked()`, `committed_test_files()`, `count_tests()`, `discover()` and 8 more.

**Use.** `python3 scripts/check_docs.py --help`
