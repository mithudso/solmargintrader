# Every file in this repository

**Generated** from `index/INDEX.json` at commit `ef61210` (2026-09-25T20:32:02+00:00). 423 tracked files, 7.0 MB.

Regenerate with:

```bash
python3 index/build.py all          # refresh the index
python3 index/make_files_doc.py     # rewrite this file
python3 index/build.py --check      # fail if the index is stale
```

## How to read an entry

Every entry marks where its description came from, because a generated one-liner and a considered one should not look alike:

- **curated** (42 files) — hand-written purpose and usage, in the `CURATED` table of `index/make_files_doc.py`. Used where extraction cannot give a reader what they need: the engine, the research drivers, the order-placing path, and the files with no prose of their own.
- **extracted** (300 files) — the file's own module docstring, JSDoc header, or frontmatter `summary`. Trustworthy here because 112/118 Python modules and 36/39 JS files carry a substantial one. (These counts are computed at generation time, not hardcoded — an earlier revision asserted a frozen ratio and it was wrong within a day as the repo grew.)
- **derived** (72 files) — shape only, for generated artifacts: a CSV's header and row count, a JSON's keys. Prose for a result file would be invented.

*How to use* is curated where it matters and otherwise inferred from the file's kind — a test gets its runner, a CLI gets `--help`, a module gets its import path.

## Related documents

This file is the **exhaustive** one: every tracked file, no exceptions, regenerated from the index. For orientation rather than lookup, read these first — they are shorter and they explain *why* the pieces fit together:

- `docs/codebase-overview.md` — the narrative tour.
- `docs/ARCHITECTURE.md` — how the three components relate.
- `docs/COMPONENTS.md` — component-level responsibilities.
- `docs/CONCEPTS.md` — the conceptual index: which files bear on which idea.

To *search* rather than browse: `python3 index/search.py "your question"`.

## Contents

- [`(root)`](#root) — 13 files
- [`docs`](#docs) — 24 files
- [`index`](#index) — 5 files
- [`backtester`](#backtester) — 106 files
- [`research`](#research) — 109 files
- [`extension`](#extension) — 37 files
- [`soltui`](#soltui) — 36 files
- [`.github`](#github) — 8 files
- [`tradingskilllist`](#tradingskilllist) — 1 files
- [`.remember`](#remember) — 1 files
- [`.githooks`](#githooks) — 2 files
- [`mongo`](#mongo) — 15 files
- [`scripts`](#scripts) — 2 files
- [`skills`](#skills) — 61 files
- [`tools`](#tools) — 3 files

---

## (root)

Repository-level entry points and agent instructions. `AGENTS.md` and `CLAUDE.md` are the operative rules for anyone — human or agent — changing this repo; read them before the code.

13 files.

#### `.editorconfig`

`other` · 24 lines · 324 B · description: **curated**

**Purpose.** Baseline whitespace and encoding rules so diffs stay about content.

**Use.** Nothing to run; editors apply it automatically.

#### `.gitattributes`

`other` · 28 lines · 744 B · description: **curated**

**Purpose.** Per-path git behaviour: line-ending normalisation, and which files are treated as binary or excluded from diffs and archives. Keeps a CSV or a generated artifact from producing noise in review.

**Use.** Nothing to run; git applies it. `git check-attr -a <path>` to inspect.

#### `.gitignore`

`other` · 106 lines · 3,178 B · description: **curated**

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

`doc` · 103 lines · 6,255 B · description: **curated**

**Purpose.** Agent-facing companion to AGENTS.md — the same non-negotiables plus the workflow conventions (commit discipline, where numbers may come from, what must be regenerable).

**Use.** Read before making changes with an agent.

#### `GEMINI.md`

`doc` · 57 lines · 2,982 B · description: **extracted**

**Purpose.** Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file first — it is the single source of truth, and this file only points at it. that a fresh install can place an order.

**Use.** Read it.

#### `README.md`

`doc` · 117 lines · 6,311 B · description: **curated**

**Purpose.** Entry point: what the project is, the three components, and the honest summary of what the research established.

**Use.** Start here.

#### `llms-facts.txt`

`data` · 32 lines · 2,827 B · description: **derived**

**Purpose.** Generated report. Opens: <!-- generated: llms-suite 1.0, 2026-09-25; verified-as-of 2026-09-25; local paths rewritten to repo-relative --> / # solmargintrader: Sourced Facts

**Use.** Read it.

#### `llms-full.txt`

`data` · 2111 lines · 108,845 B · description: **derived**

**Purpose.** Generated report. Opens: <!-- generated: llms-suite 1.0, 2026-09-25; verified-as-of 2026-09-25; local paths rewritten to repo-relative --> / ---

**Use.** Read it.

#### `llms-small.txt`

`data` · 10 lines · 1,320 B · description: **derived**

**Purpose.** Generated report. Opens: <!-- generated: llms-suite 1.0, 2026-09-25; verified-as-of 2026-09-25; local paths rewritten to repo-relative --> / # solmargintrader (small)

**Use.** Read it.

#### `llms.txt`

`data` · 41 lines · 2,340 B · description: **derived**

**Purpose.** Generated report. Opens: <!-- generated: llms-suite 1.0, 2026-09-25; verified-as-of 2026-09-25; local paths rewritten to repo-relative --> / # solmargintrader

**Use.** Read it.

#### `pagesource`

`other` · 54 lines · 113,673 B · description: **curated**

**Purpose.** A captured page source kept as a fixture for the scraping/parsing work. Reference data, not code.

**Use.** Read it; nothing to run.

---

## docs

Curated prose. `ARCHITECTURE.md` explains how the pieces fit, `TESTING.md` is the coverage contract, `SECURITY.md` covers the order-placing surface, and this file indexes everything.

24 files.

#### `docs/API.md`

`doc` · 148 lines · 6,449 B · description: **extracted**

**Purpose.** Every action lives in one registry: `extension/src/core/commands.js`. Three surfaces adapt it. drift apart. cd extension

**Use.** Read it.

#### `docs/ARCHITECTURE.md`

`doc` · 118 lines · 6,905 B · description: **extracted**

**Purpose.** Two independent systems that share a subject (SOL) and nothing else. There is no code path from the backtester into the extension: research does not place orders, and the extension does not simulate. backtester/ research/ extension/

**Use.** Read it.

#### `docs/COMPONENTS.md`

`doc` · 216 lines · 9,476 B · description: **extracted**

**Purpose.** What each module is for, what it exposes, and what it depends on. `docs/codebase-overview.md` is the flat file map; this page is the shape of the thing. Dependency direction, strictly one-way:

**Use.** Read it.

#### `docs/CONCEPTS.md`

`doc` · 312 lines · 14,637 B · description: **extracted**

**Purpose.** python3 index/build.py all # refresh python3 index/make_concepts_doc.py # rewrite this file python3 index/search.py --concepts # list them

**Use.** Read it.

#### `docs/DEVELOPMENT.md`

`doc` · 145 lines · 6,328 B · description: **extracted**

**Purpose.** Setup, the commands you will actually use, and the environment each component needs. Everything else is stdlib. There is no build step anywhere in the repo. git clone <this repo> && cd solmargintrader

**Use.** Read it.

#### `docs/FILES.md`

`doc` · 2803 lines · 141,194 B · description: **extracted**

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

#### `docs/SCRIPTS.md`

`doc` · 962 lines · 48,256 B · description: **extracted**

**Purpose.** Every runnable entry point in this repo: what it is for, when to reach for it, **when not to**, its options, a real invocation, and the output you should expect. list. This page is the operator's manual — the commands you actually type.

**Use.** Read it.

#### `docs/SECURITY.md`

`doc` · 81 lines · 4,411 B · description: **extracted**

**Purpose.** This repository contains software that can move real money. Two assets matter: **signing keys** and the **Jupiter API key**. 600,000 iterations**), with a fresh 16-byte salt and 12-byte IV per encryption. Identical

**Use.** Read it.

#### `docs/TESTING.md`

`doc` · 149 lines · 9,488 B · description: **extracted**

**Purpose.** python3 -m unittest discover -s backtester/tests -t . # 571 tests python3 -m unittest discover -s soltui/tests -t . # 313 tests (~300s) python3 -m unittest discover -s mongo/tests -t . # 20 tests

**Use.** Read it.

#### `docs/codebase-overview.md`

`doc` · 225 lines · 12,806 B · description: **extracted**

**Purpose.** A file map for orientation, grouped by directory. Every path here is checked by Five components, in ascending order of how much damage a bug can do: Read `CLAUDE.md` before changing any of them; it carries the non-negotiables per

**Use.** Read it.

#### `docs/external-calls.md`

`doc` · 88 lines · 5,364 B · description: **extracted**

**Purpose.** Every call in this repo that leaves the machine. Four of them, across two components; The engine and the readout never touch the network — that is a stated invariant, not an accident. Fetching is always a separate explicit step that writes a local cache, so a

**Use.** Read it.

#### `docs/high_signal_file_index.json`

`doc` · 840 lines · 23,681 B · description: **derived**

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

#### `docs/short-horizon-leverage-concept-family.md`

`doc` · 468 lines · 26,932 B · description: **extracted**

**Purpose.** leveraged perpetual position for seconds to hours, on Jupiter Perps (jup.ag) specifically. This is a *map*, not an implementation plan, and **not financial advice.** Every figure is generated by `research/short_horizon_economics.py`:

**Use.** Read it.

#### `docs/strategy-optimization-concept-family.md`

`doc` · 303 lines · 19,699 B · description: **extracted**

**Purpose.** Scoping document for `/dso` (deep strategy optimizer). Written to answer one question: **what would a strategy optimizer have to do to be worth running on this repo, given what this repo has already measured?**

**Use.** Read it.

#### `docs/trading-signals-concept-family.md`

`doc` · 443 lines · 27,593 B · description: **extracted**

**Purpose.** automated trading signals and their execution on Jupiter (jup.ag) on Solana. This is a *map*, not an implementation plan, and not financial advice. Facts about Jupiter APIs were verified against live `developers.jup.ag`;

**Use.** Read it.

### `docs/dso-skill/`

#### `docs/dso-skill/README.md`

`doc` · 64 lines · 2,669 B · description: **extracted**

**Purpose.** ~/.claude/skills/deep-strategy-optimizer -> <repo>/docs/dso-skill follows the link. There is exactly one copy, which is the point — the earlier arrangement kept two and had to warn that they could drift. They can't now.

**Use.** Read it.

#### `docs/dso-skill/SKILL.md`

`doc` · 348 lines · 21,947 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

### `docs/dso-skill/references/`

#### `docs/dso-skill/references/passes.md`

`doc` · 110 lines · 8,384 B · description: **extracted**

**Purpose.** Read this before the Step-3 dispatch. `SKILL.md` carries the pass index and the group summaries; the per-pass checks, precedents, and severity specifics live here. Every precedent cited below is a real defect from the codebase this skill was written against, not a

**Use.** Read it.

---

## index

The search layer over the repo itself. Generators plus three committed indexes; the embedding array is gitignored and rebuilt on demand.

5 files.

#### `index/README.md`

`doc` · 146 lines · 7,584 B · description: **extracted**

**Purpose.** A searchable index over every tracked file in this repo: what exists, which files contain a word, which files mean something like a question, and which bear on an idea. Built to answer "where is the thing that does X" without reading every file.

**Use.** Read it.

#### `index/build.py`

`code-python` · 835 lines · 35,294 B · description: **curated**

**Purpose.** Builds the four indexes over every tracked file: metadata, BM25 text, concepts, and the opt-in semantic embeddings. `--check` re-hashes the tree so a stale index fails loudly.

**Contents.** Defines `REPO`, `OUT`, `SCHEMA_VERSION`, `INDEX_JSON`, `TEXT_JSON`, `CONCEPT_JSON`, `SEMANTIC_NPZ`, `SEMANTIC_MANIFEST`, `TEXT_EXT`, `BODY_EXCLUDED_EXT` and 30 more.

**Use.** `python3 index/build.py all`, then `semantic` for embeddings, and `--check` before trusting it.

#### `index/make_concepts_doc.py`

`code-python` · 160 lines · 6,405 B · description: **extracted**

**Purpose.** Generate `docs/CONCEPTS.md` — the conceptual index, as prose. python3 index/make_concepts_doc.py python3 index/make_concepts_doc.py --stdout Reads `index/CONCEPT-INDEX.json`, so run `python3 index/build.py all` first. The concepts are not an invented taxonomy.

**Contents.** Defines `REPO`, `SRC`, `DEST`, `render()`, `main()`.

**Use.** `python3 index/make_concepts_doc.py --help`

#### `index/make_files_doc.py`

`code-python` · 538 lines · 28,249 B · description: **curated**

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

106 files.

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

`code-python` · 316 lines · 12,107 B · description: **curated**

**Purpose.** Loading and validating bars. Refuses gaps rather than filling them, resolves columns by name, and requires monotone de-duplicated timestamps — a forward-filled gap flatters every volatility and reversion statistic computed after it.

**Contents.** Defines `resolve_data_dir()`, `class DataValidationError`, `class DataLoader`, `validate_bars()`, `_slice_dates()`, `checksum_frame()`, `class CsvLoader`, `class SyntheticLoader`, `frame_to_arrays()`.

**Use.** `CsvLoader(path, allow_gaps=False).load(asset, start, end, interval)`.

#### `backtester/core/deflated_sharpe.py`

`code-python` · 245 lines · 10,129 B · description: **extracted**

**Purpose.** Deflated Sharpe Ratio: the haircut a Sharpe owes to the size of the search. PBO answers "is this leaderboard informative?" The Deflated Sharpe Ratio answers a different question that PBO leaves open: **given that N configurations were tried, how much of this particular Sharpe is simply the expected maximum of N draws?** Comparing a best-of-N Sharpe against zero is the mistake.

**Contents.** Defines `EULER_MASCHERONI`, `_NORMAL`, `class DeflatedSharpeError`, `class DsrResult`, `deannualise()`, `expected_max_sharpe()`, `probabilistic_sharpe_ratio()`, `deflated_sharpe_ratio()`, `effective_trials()`, `trial_sharpe_variance()`.

**Use.** `import backtester.core.deflated_sharpe`

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

#### `backtester/core/fetch_minutes.py`

`code-python` · 721 lines · 32,457 B · description: **extracted**

**Purpose.** Resumable, parallel 1-minute candle fetch with an honest coverage manifest. python3 -m backtester.core.fetch_minutes --asset BTC --years 5 python3 -m backtester.core.fetch_minutes --all --years 5 --workers 6 ## Why this is not `fetch.py` `fetch_coinbase` chains a cursor: each request's window start comes from the previous response's oldest bar.

**Contents.** Defines `MINUTE`, `WINDOW_SECONDS`, `REQUEST_TIMEOUT`, `REQUEST_RETRIES`, `RATE_LIMIT_PER_SECOND`, `EMPTY_RUN_TO_BELIEVE`, `MINUTE_ASSETS`, `DATA`, `MANIFEST`, `class RateLimiter` and 24 more.

**Use.** `python3 backtester/core/fetch_minutes.py --help`

#### `backtester/core/funding.py`

`code-python` · 492 lines · 19,640 B · description: **extracted**

**Purpose.** Explicit historical **funding-rate** fetch, for the carry question `perps.py` cannot answer. python3 -m backtester.core.funding --plan-only python3 -m backtester.core.funding --assets BTC,ETH,SOL,DOGE,ZEC python3 -m backtester.core.funding --assets BTC --cross-check-okx Never called implicitly by a backtest.

**Contents.** Defines `HYPERLIQUID_URL`, `OKX_FUNDING_URL`, `MAX_ROWS_PER_REQUEST`, `FUNDING_INTERVAL_SECONDS`, `FUNDING_COLUMNS`, `REQUEST_SPACING_SECONDS`, `MAX_PLAUSIBLE_HOURLY_RATE`, `class FundingFetchError`, `class FundingOutcome`, `_post_json()` and 9 more.

**Use.** `python3 backtester/core/funding.py --help`

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

#### `backtester/core/ticks.py`

`code-python` · 316 lines · 13,073 B · description: **extracted**

**Purpose.** Explicit trade-tick fetch from the Coinbase Exchange public API. Sibling of fetch.py, and deliberately separate from it. Candles and ticks are different contracts: a tick frame is not a bar frame and must never be loaded as one, so nothing here writes into the `data/<ASSET>_<interval>.csv` namespace that CsvLoader reads. Ticks land under `data/ticks/`.

**Contents.** Defines `MAX_TRADES_PER_REQUEST`, `TRADE_COLUMNS`, `_parse_trades()`, `_trade_page()`, `newest_trade_id()`, `seek_trade_id()`, `fetch_trades()`, `trades_to_bars()`, `default_tick_path()`, `main()`.

**Use.** `python3 backtester/core/ticks.py --help`

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

`code-python` · 151 lines · 4,820 B · description: **curated**

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

`strategy-card` · 193 lines · 9,503 B · description: **extracted**

**Purpose.** Long only while a directional trend is both present (ADX) and up (+DI > -DI).

**Contents.** Frontmatter: `status`=measured, `family`=regime-filter, `evaluation`=cpcv-8-groups-k2, `success_likelihood`=low, `data_available`=true, `registry_key`=adx_trend.

**Use.** Read the card, then build it: `build('adx_trend', **params)`. Status: measured.

#### `backtester/strategy_cards/atr_position_sizing.md`

`strategy-card` · 108 lines · 4,659 B · description: **extracted**

**Purpose.** Trend entry sized so one ATR of adverse move costs a fixed fraction of equity.

**Contents.** Frontmatter: `status`=measured, `family`=sma-gated, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=atr_sized.

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

`strategy-card` · 117 lines · 5,085 B · description: **extracted**

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

`strategy-card` · 115 lines · 5,110 B · description: **extracted**

**Purpose.** Vol-targeted trend using an EWMA variance forecast instead of a trailing stdev.

**Contents.** Frontmatter: `status`=measured, `family`=sma-gated, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=garch_voltarget.

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

`strategy-card` · 221 lines · 11,531 B · description: **extracted**

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

`strategy-card` · 117 lines · 4,823 B · description: **extracted**

**Purpose.** Long above a slow moving average, flat below it. The most valuable partner in the set.

**Contents.** Frontmatter: `status`=measured, `family`=sma-gated, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=sma_regime.

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

`strategy-card` · 119 lines · 5,186 B · description: **extracted**

**Purpose.** Trend entry sized inversely to realised volatility. Continuous exposure, not binary.

**Contents.** Frontmatter: `status`=measured, `family`=sma-gated, `evaluation`=single-split-70-30, `success_likelihood`=low, `data_available`=true, `registry_key`=voltarget.

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

`strategy-card` · 139 lines · 6,225 B · description: **extracted**

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

#### `backtester/tests/test_candle_gap_audit.py`

`test` · 114 lines · 4,400 B · description: **extracted**

**Purpose.** Gap detection and repair-merge logic in `research/candle_gap_audit.py`. The audit's whole value is the distinction between "this minute was quiet" and "this minute traded and the exchange dropped it", so the tests here pin the mechanics that decision rests on: which bars are reported missing, and that a repaired series replaces the damaged bars rather than accumulating duplicates of them.

**Contents.** Defines `REPO`, `MINUTE`, `_bars()`, `class TestGapRuns`, `class TestRepairMerge`. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_candle_gap_audit.py -q`

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

#### `backtester/tests/test_deflated_sharpe.py`

`test` · 194 lines · 9,192 B · description: **extracted**

**Purpose.** Tests for the Deflated Sharpe Ratio. The first test is the one that matters: it pins the implementation to a figure the source paper states in prose, so the formula cannot drift into something plausible but wrong. Bailey & López de Prado report that at N=1,000 independent trials with unit cross-sectional variance and zero mean, the expected maximum Sharpe is **3.26**.

**Contents.** Defines `class TestExpectedMaxSharpe`, `class TestProbabilisticSharpe`, `class TestDeflatedSharpe`, `class TestUnitsAndHelpers`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_deflated_sharpe.py -q`

#### `backtester/tests/test_engine.py`

`test` · 606 lines · 25,376 B · description: **extracted**

**Purpose.** Acceptance tests for the backtest engine. These are known-answer tests, not smoke tests. Each one has a hand-computed expected value, so a failure localises the bug rather than just signalling that something changed.

**Contents.** Defines `make_frame()`, `ZERO_COST`, `class TestBuyAndHoldIdentity`, `class TestLookAheadGuard`, `class TestFillTiming`, `class TestFeeArithmetic`, `class TestResizeCosts`, `class TestGapLiquidation`, `class TestBorrowFeeSign`, `class TestLiquidation` and 3 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_engine.py -q`

#### `backtester/tests/test_fetch_minutes.py`

`test` · 387 lines · 17,630 B · description: **extracted**

**Purpose.** Tests for the resumable 1-minute fetch. Each class here guards a bug that was live on disk, not a hypothetical one. The fetch is a multi-hour job against a rate-limited venue, so its failure modes are all of the same shape: something is recorded as done that was not done, and no count reveals it.

**Contents.** Defines `REPO`, `class PlanWindowsTests`, `class SidecarTests`, `class EffectiveWindowsTests`, `class FirstAvailableTests`, `class CoverageTests`, `class CoverageDoesNotDriftTests`, `class CacheTests`, `class RateLimiterTests`, `class RetryAfterTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_fetch_minutes.py -q`

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

#### `backtester/tests/test_ratio_rotation.py`

`test` · 324 lines · 13,927 B · description: **extracted**

**Purpose.** Tests for research/ratio_rotation.py. The module's self-test is the fast gate a human runs; this is the suite CI runs. They overlap deliberately on the two invariants that matter most -- the one-bar leak and the cost path -- because CLAUDE.md requires a test that would catch a leak for anything touching signal generation or fill timing, and a self-test that someone can forget to run does not satis

**Contents.** Defines `REPO`, `make_panel()`, `class TestNoLookahead`, `class TestCosts`, `class TestChainIsNotFree`, `class TestWeights`, `class TestNeutralBook`, `class TestControlsAndAttribution`, `class TestRuin`, `class TestTurnoverArithmetic`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_ratio_rotation.py -q`

#### `backtester/tests/test_signal_redundancy.py`

`test` · 314 lines · 14,442 B · description: **extracted**

**Purpose.** The redundancy script's pure parts. Following `test_cross_asset_cpcv.py`: no test here opens a price file, steps the engine, or writes anywhere under `research/results/`.

**Contents.** Defines `frame()`, `class TestRedundancy`, `class TestTwinVerdict`, `class TestPairTable`, `class TestFamilyVerdict`, `class TestResolveOutputPath`, `class TestPerStrategyTable`. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_signal_redundancy.py -q`

#### `backtester/tests/test_strategy_cards.py`

`test` · 627 lines · 26,487 B · description: **extracted**

**Purpose.** Tests for strategy cards. These are the tests that make a card a contract rather than a claim. Prose in a card can be wrong and no test will catch it; a *number* in a card is checked against the code that would use it.

**Contents.** Defines `REPO_ROOT`, `constructor_defaults()`, `synthetic_bars()`, `class TestFrontmatterParser`, `class TestCardValidation`, `class TestCardsLoad`, `class TestSuccessRatings`, `class TestRegistryDrift`, `class TestLadderDrift`, `class TestSweepDrift` and 2 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_strategy_cards.py -q`

#### `backtester/tests/test_strategy_duplication.py`

`test` · 143 lines · 6,622 B · description: **extracted**

**Purpose.** `bb_reversion` and `zscore` are one hypothesis counted twice. Found by `research/dso_audit.py`'s S4 pass, which flagged them as posting identical summary scalars on BTC daily, and confirmed by comparing per-bar exposure: on 1,875 BTC daily bars the two strategies took **exactly the same position on every bar**. The reason is algebra, not coincidence.

**Contents.** Defines `exposures()`, `series()`, `class TestTheTwoAreTheSameRule`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_strategy_duplication.py -q`

#### `backtester/tests/test_sweep_pair_gate.py`

`test` · 348 lines · 16,427 B · description: **extracted**

**Purpose.** The sweep's combination gate, and the measurement it now consults. No test here loads a price file or runs the engine; the gate is pure set logic over a CSV, and `OUT_DIR` is redirected into a tempdir wherever a read could otherwise reach `research/results/` -- which holds published evidence. What is worth pinning is that the three gates genuinely disagree, and disagree in BOTH directions.

**Contents.** Defines `NAMES`, `CSV`, `class GateFixture`, `class TestRedundancyFilename`, `class TestMeasuredRedundantPairs`, `class TestIndependentCombos`, `class TestRedundancyClasses`, `class TestCanonicalDeduplication`, `COMBO_CSV`, `class TestMeasuredRedundantCombinations` and 1 more. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_sweep_pair_gate.py -q`

#### `backtester/tests/test_tick_backfill.py`

`test` · 146 lines · 6,174 B · description: **extracted**

**Purpose.** Incremental aggregation and checkpoint round-trip in `research/tick_backfill.py`. The backfill walks a month of trades BACKWARD in pages, folding each page into a running per-bar aggregate. That means a bar's opening trade usually arrives *after* its closing trade, and often in a different page entirely.

**Contents.** Defines `REPO`, `BASE`, `_trades()`, `class TestMinuteAggregator`, `class TestCheckpointRoundTrip`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_tick_backfill.py -q`

#### `backtester/tests/test_ticks.py`

`test` · 192 lines · 8,031 B · description: **extracted**

**Purpose.** Tick fetch and tick->bar aggregation. No network: every test uses fixtures.

**Contents.** Defines `RAW`, `class TestParseTrades`, `class TestTradesToBars`, `class TestTruncationIsNotWritableBySilence`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_ticks.py -q`

#### `backtester/tests/test_universe.py`

`test` · 242 lines · 10,859 B · description: **extracted**

**Purpose.** The multi-asset universe fetch. No test here touches the network. `list_coinbase_products` takes an injected `get_json` and `fetch_universe` takes an injected `fetcher`, for the reason `fetch.py`'s own docstring gives: fetching is an explicit step, and a test suite that performs it is neither deterministic nor polite to the venue. The behaviour most worth pinning is the refusal.

**Contents.** Defines `LISTED`, `bars()`, `class PlanTests`, `class FetchTests`, `class CliTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_universe.py -q`

---

## research

Drivers that produce the numbers, and the write-ups that quote them. Everything here is reproducible from a committed script — the two occasions that was not true both produced a wrong published figure.

109 files.

#### `research/CANDLE-GAP-AUDIT.md`

`doc` · 209 lines · 12,779 B · description: **extracted**

**Purpose.** Generated by `research/candle_gap_audit.py` over 2026-07-06 .. 2026-08-06, five assets. Every figure comes from the Coinbase **trades** endpoint compared against the 1m candle cache in `data/`.

**Use.** Read it.

#### `research/CROSS-ASSET-TRANSFER.md`

`doc` · 225 lines · 14,429 B · description: **extracted**

**Purpose.** python3 research/cross_asset_cpcv.py --self-test # gate: reproduces the BTC/ETH file python3 research/cross_asset_cpcv.py --assets SOL,DOGE,ZEC # 25 singles, medium horizon python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC # the five, with SOL as control

**Use.** Read it.

#### `research/LEVERAGE-ECONOMICS.md`

`doc` · 162 lines · 8,146 B · description: **extracted**

**Purpose.** No network, no data files — this is closed-form arithmetic over published venue parameters, so it reproduces exactly. python3 research/leverage_economics.py --self-test # gate: 7 load-bearing claims

**Use.** Read it.

#### `research/PROMPT_STRATEGIES.md`

`doc` · 175 lines · 14,396 B · description: **extracted**

**Purpose.** <!-- HISTORICAL SPEC — preserved as written, do not retro-edit. This is the pdo-optimized spec that drove the first pass of the work. Two of its

**Use.** Read it.

#### `research/RANKED_LISTS.md`

`doc` · 1069 lines · 73,638 B · description: **extracted**

**Purpose.** configuration, so realised path counts are lower; see "How many paths each figure actually rests on" below. The earlier single 70/30 walk-forward is retained as List 1b, because the disagreement between the two methods is the most instructive result here.

**Use.** Read it.

#### `research/RATIO-ROTATION.md`

`doc` · 270 lines · 12,571 B · description: **extracted**

**Purpose.** Reproduce with: python3 -m backtester.core.universe --assets BTC,ETH,SOL,DOGE,ZEC --interval 1d python3 -m backtester.core.universe --assets XRP --interval 1d --allow-gaps

**Use.** Read it.

#### `research/STRATEGIES.md`

`doc` · 786 lines · 40,210 B · description: **extracted**

**Purpose.** The request asked for a `/dr` deep-research pass. Subagent fan-out is unavailable in this environment, so this is grounded in the **local citation-backed corpus** — technical analysis, trading styles, algorithmic/quant methods, ML-for-trading pitfalls, crypto

**Use.** Read it.

#### `research/SWEEP-9COIN.md`

`doc` · 146 lines · 7,123 B · description: **extracted**

**Purpose.** into `sweep_results_9coin.json`, `sweep_wf_9coin.json` and `sweep_grid_9coin.json`. cd ~/Downloads/sol-backtest-data/_scripts python3 run_sweep.py --interval 1h --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT,XRPUSDT,DOGEUSDT,LINKUSDT,AVAXUSDT,TRXUSDT

**Use.** Read it.

#### `research/TOP5-RECOMMENDATION.md`

`doc` · 108 lines · 7,216 B · description: **extracted**

**Purpose.** files. Nothing is transcribed by hand. PBO (probability of backtest overfitting) is **0.700** for singles at both daily horizons, against a measured pure-noise line of 0.500. Above the noise line means selecting by in-sample

**Use.** Read it.

#### `research/TOP_COINS.md`

`doc` · 142 lines · 7,828 B · description: **extracted**

**Purpose.** Machine-readable copy: `research/results/top_coins.csv`. Regenerate rather than edit by hand — every figure here came from that one API call and none is transcribed. market cap and that is what market cap says. They are marked because a trading universe that

**Use.** Read it.

#### `research/candle_crosscheck.py`

`code-python` · 155 lines · 6,668 B · description: **extracted**

**Purpose.** Check the candle cache against itself: does a 1d bar equal its own 24 1h bars? No network, no ticks, and it covers the **entire** history rather than the month a tick rebuild can reach. That matters because the alternative -- rebuilding five years of ticks to audit the 1d series -- is several days of API calls, and this answers a large part of the same question in seconds.

**Contents.** Defines `REPO`, `PRICE_REL_TOL`, `VOLUME_REL_TOL`, `compare()`, `main()`, `_resolve()`. Depends on `backtester`.

**Use.** `python3 research/candle_crosscheck.py --help`

#### `research/candle_gap_audit.py`

`code-python` · 286 lines · 11,708 B · description: **extracted**

**Purpose.** Audit -- and optionally repair -- gaps in Coinbase 1m candle data using ticks. Why this exists. A missing 1m candle has two possible causes that look identical in the file and have opposite consequences: * the minute genuinely had no trades (thin market), or * the minute traded and the candle endpoint dropped it. The first is honest data.

**Contents.** Defines `REPO`, `PAD_BARS`, `gap_runs()`, `classify_run()`, `_fetch_window()`, `repair_window()`, `main()`. Depends on `backtester`.

**Use.** `python3 research/candle_gap_audit.py --help`

#### `research/cpcv_sweep.py`

`code-python` · 477 lines · 21,212 B · description: **curated**

**Purpose.** The primary evaluation driver: CPCV over singles, pairs and triples, then PBO across the configuration set. Prints its own legend so the numbers cannot travel without their meaning.

**Contents.** Defines `REPO`, `OUT`, `LEGEND`, `PBO_NOISE`, `PBO_INFORMATIVE`, `LOW_POSITIVE_SHARE`, `interpret()`, `TRIPLE_CANDIDATES`, `run_horizon()`, `run_combos()` and 1 more. Depends on `backtester`, `research`.

**Use.** `python3 research/cpcv_sweep.py --horizon medium --groups 8 --k 2`.

#### `research/cross_asset_cpcv.py`

`code-python` · 835 lines · 40,047 B · description: **curated**

**Purpose.** Runs the registered strategy set on another coin with the SOL-tuned parameters deliberately NOT refitted, so the measurement is transfer rather than fit. Two gates: it reproduces the committed BTC/ETH reference, and reproduces SOL's five published medians.

**Contents.** Defines `REPO`, `data_dir()`, `OUT`, `REFERENCE`, `REFERENCE_ASSETS`, `REFERENCE_HORIZON`, `REFERENCE_GROUPS`, `REFERENCE_K`, `MIN_RANKABLE_TRADES`, `MAX_PATHS` and 18 more. Depends on `backtester`, `research`.

**Use.** `python3 research/cross_asset_cpcv.py --self-test` then `--assets SOL,DOGE,ZEC` or `--top5 --assets DOGE,ZEC`.

#### `research/decide.py`

`code-python` · 1219 lines · 46,127 B · description: **extracted**

**Purpose.** What every registered strategy, signal and indicator says about the last bar. python3 research/decide.py --asset SOL --interval 1d python3 research/decide.py --data data/BTC_1d.csv --json Three sections, because they are three different kinds of claim: * **Strategies** -- every entry in `core.strategies.REGISTRY`, replayed bar-by-bar from the start of history.

**Contents.** Defines `REPO`, `DEFAULT_TOLERANCE`, `FLAT_EPSILON`, `STALE_AFTER_BARS`, `HOLD_LONG`, `HOLD_SHORT`, `FLAT`, `BUY`, `SELL`, `INSUFFICIENT` and 30 more. Depends on `backtester`.

**Use.** `python3 research/decide.py --help`

#### `research/dso_audit.py`

`code-python` · 365 lines · 16,073 B · description: **extracted**

**Purpose.** Mechanical half of the /dso statistical-honesty passes, run over the CPCV result CSVs. python3 research/dso_audit.py # audit every cpcv_* result file python3 research/dso_audit.py --floor 30 # raise the evidence floor `/dso` (the deep-strategy-optimizer skill) defines 19 audit passes.

**Contents.** Defines `REPO`, `RESULTS`, `FLAT_TOL`, `RESULT_KEYS`, `class AuditError`, `load()`, `KNOWN_DUPLICATE_GROUPS`, `DATA_DIR`, `DEFAULT_ASSET`, `ASSET_TOKENS` and 8 more. Depends on `backtester`.

**Use.** `python3 research/dso_audit.py --help`

#### `research/geometry.py`

`code-python` · 300 lines · 12,846 B · description: **curated**

**Purpose.** Sensitivity of results to the CPCV geometry itself. Changing 8 blocks to 9 moved the best pair's median Sharpe more than the worst parameter nudge did — the evaluation design mattered more than the strategy.

**Contents.** Defines `REPO`, `OUT`, `class GeometryRun`, `spearman()`, `evaluate_geometry()`, `tidy_frame()`, `render()`, `verdict()`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/geometry.py --help`.

#### `research/leverage_economics.py`

`code-python` · 170 lines · 8,131 B · description: **extracted**

**Purpose.** Cost economics of high-leverage perpetuals, for Jupiter Perps specifically. Generates every table in research/LEVERAGE-ECONOMICS.md. No network, no data files -- this is closed-form arithmetic over published venue parameters, so it reproduces exactly.

**Contents.** Defines `FEE_RT`, `R_LONG`, `R_SHORT`, `HOLDS`, `LEVS`, `break_even_move()`, `carry_crossover_hours()`, `hours_to_zero_collateral()`, `liquidation_move()`, `_fmt_h()` and 3 more.

**Use.** `python3 research/leverage_economics.py --help`

#### `research/minute_sweep.py`

`code-python` · 481 lines · 22,623 B · description: **extracted**

**Purpose.** Preliminary backtest of every registered strategy against every 1-minute series. python3 research/minute_sweep.py # default 500k-bar window python3 research/minute_sweep.py --all-bars # full history, hours python3 research/minute_sweep.py --common-window # one calendar for all assets python3 research/minute_sweep.py --param-scale 60 # wall-clock-preserving params ## This is preliminary, and the wo

**Contents.** Defines `REPO`, `OUT`, `BAR_KEYS`, `FEE_BPS`, `SLIPPAGE_BPS`, `DEFAULT_BARS`, `MINUTE`, `SLICES`, `class Cell`, `scaled_params()` and 10 more. Depends on `backtester`, `research`.

**Use.** `python3 research/minute_sweep.py --help`

#### `research/perturb.py`

`code-python` · 453 lines · 18,930 B · description: **curated**

**Purpose.** The second independent robustness axis: nudge each parameter ±10% and re-run CPCV. A point that collapses under a small nudge was fitted to noise, whatever its Sharpe.

**Contents.** Defines `REPO`, `OUT`, `BOUNDED_UNIT`, `REFERENCE`, `REFERENCE_HIGH`, `class Trial`, `class Report`, `perturbed_values()`, `evaluate()`, `run()` and 4 more. Depends on `backtester`, `research`.

**Use.** `python3 research/perturb.py --help`.

#### `research/ratio_rotation.py`

`code-python` · 1493 lines · 64,498 B · description: **extracted**

**Purpose.** Numeraire-switching rotation: hold whichever coin is cheapest against its peers. python3 research/ratio_rotation.py --self-test python3 research/ratio_rotation.py --turnover-table python3 research/ratio_rotation.py --demo-chain python3 research/ratio_rotation.py --sweep python3 research/ratio_rotation.py --sweep --assets BTC,ETH,SOL,DOGE,ZEC,XRP This answers a question the single-asset engine cann

**Contents.** Defines `REPO`, `OUT_DIR`, `PRIMARY_ASSETS`, `SECONDARY_ASSETS`, `MIN_OOS_ROTATIONS`, `SPLIT`, `SWEEP_WINDOWS`, `SWEEP_TOP_K`, `SWEEP_DIRECTIONS`, `SWEEP_MARGINS` and 26 more. Depends on `backtester`.

**Use.** `python3 research/ratio_rotation.py --help`

#### `research/run_backfill.sh`

`other` · 0 lines · 4,015 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `research/short_horizon_economics.py`

`code-python` · 283 lines · 13,637 B · description: **extracted**

**Purpose.** Cost economics of SHORT-HORIZON leveraged perpetuals on Jupiter Perps. Sibling of research/leverage_economics.py, which stops at a 1-hour hold.

**Contents.** Defines `FEE_RT`, `R_LONG`, `R_SHORT`, `UTIL`, `VOL_ANNUAL`, `HOURS_PER_YEAR`, `HORIZONS`, `TX_COSTS`, `NOTIONALS`, `LEVS` and 11 more.

**Use.** `python3 research/short_horizon_economics.py --help`

#### `research/signal_redundancy.py`

`code-python` · 629 lines · 26,862 B · description: **extracted**

**Purpose.** Measure how many independent bets the strategy registry actually contains. python3 research/signal_redundancy.py # SOL, medium python3 research/signal_redundancy.py --horizon short # SOL hourly, slower python3 research/signal_redundancy.py --asset BTC --out auto # BTC, canonical name python3 research/signal_redundancy.py --top 25 # longer pair list Why this script exists.

**Contents.** Defines `REPO`, `OUT`, `VARIANCE_TARGET`, `SKIP_FAMILIES`, `exposure_matrix()`, `redundancy()`, `pair_table()`, `per_strategy_table()`, `family_verdict()`, `twin_groups()` and 6 more. Depends on `backtester`, `research`.

**Use.** `python3 research/signal_redundancy.py --help`

#### `research/sweep.py`

`code-python` · 872 lines · 36,598 B · description: **curated**

**Purpose.** Defines `HORIZONS` — the per-horizon data file, interval, gap policy and parameter set — and runs the single-split walk-forward that CPCV superseded. The parameter tables here are what every other driver imports, so an edit moves every downstream number.

**Contents.** Defines `REPO`, `data_dir()`, `set_data_dir()`, `OUT_DIR`, `MIN_OOS_TRADES`, `SPLIT`, `COMBO_CANDIDATES`, `class Row`, `load_horizon()`, `walk_forward()` and 15 more. Depends on `backtester`.

**Use.** `python3 research/sweep.py --help`. Imported by the other drivers for `HORIZONS` and `load_horizon`.

#### `research/sweep_untested.py`

`code-python` · 103 lines · 3,723 B · description: **extracted**

**Purpose.** Finds and sweeps untested strategies and configurations. Identifies strategies in the REGISTRY that do not have baseline parameters in `research/sweep.py` or runs new configurations for existing strategies to compute profitability metrics like Sharpe, Kelly, and Drawdown.

**Contents.** Defines `REPO`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/sweep_untested.py --help`

#### `research/tick_backfill.py`

`code-python` · 351 lines · 14,899 B · description: **extracted**

**Purpose.** Long-running, resumable tick backfill and candle-integrity audit. Built to run for hours at low priority in the background. See `research/run_backfill.sh` for the wrapper that sets the priority. Why a streaming walk instead of `candle_gap_audit.py`'s per-gap fetch.

**Contents.** Defines `REPO`, `PAGE`, `CHECKPOINT_EVERY`, `_handle_stop()`, `class MinuteAggregator`, `_page()`, `backfill()`, `_write_ck()`, `audit()`, `rerun_decision()` and 1 more. Depends on `backtester`.

**Use.** `python3 research/tick_backfill.py --help`

#### `research/turnover_table.py`

`code-python` · 200 lines · 8,358 B · description: **curated**

**Purpose.** The one comparable turnover table for the ten coins, plus a checker. Exists because ten spokes each pulling their own snapshot produced ten figures that were ranked against each other anyway, and the ranking was wrong.

**Contents.** Defines `REPO`, `SOURCE`, `AS_OF`, `SPOKE_DIRS`, `SPOKES`, `turnover_table()`, `render()`, `find_spoke()`, `check()`, `main()`.

**Use.** `python3 research/turnover_table.py` or `--check`.

#### `research/verify_numbers.py`

`code-python` · 1102 lines · 49,895 B · description: **curated**

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

`coin-reference` · 498 lines · 35,638 B · description: **extracted**

**Purpose.** Solana (SOL) for a systematic trader — execution reality on a no-mempool chain, a 98.6%-volatility and −96.3%-drawdown record with a +1.31 beta to BTC, and what this project's own 1,287-configuration backtest measured, including that its five recommended configurations do not transfer off SOL. Read before designing or trusting any SOL strategy.

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

#### `research/results/combination_redundancy_sol_long.csv`

`result` · 1124 lines · 127,605 B · description: **derived**

**Purpose.** Generated data: 1122 rows x 9 columns (horizon, size, mode, a, b, corr, agree_active, both_flat...).

**Contents.** Columns: `horizon`, `size`, `mode`, `a`, `b`, `corr`, `agree_active`, `both_flat`, `redundant`.

**Use.** `pandas.read_csv('research/results/combination_redundancy_sol_long.csv')` — regenerate with the driver that names it.

#### `research/results/combination_redundancy_sol_medium.csv`

`result` · 1124 lines · 142,905 B · description: **derived**

**Purpose.** Generated data: 1122 rows x 9 columns (horizon, size, mode, a, b, corr, agree_active, both_flat...).

**Contents.** Columns: `horizon`, `size`, `mode`, `a`, `b`, `corr`, `agree_active`, `both_flat`, `redundant`.

**Use.** `pandas.read_csv('research/results/combination_redundancy_sol_medium.csv')` — regenerate with the driver that names it.

#### `research/results/combination_redundancy_sol_short.csv`

`result` · 2162 lines · 276,925 B · description: **derived**

**Purpose.** Generated data: 2160 rows x 9 columns (horizon, size, mode, a, b, corr, agree_active, both_flat...).

**Contents.** Columns: `horizon`, `size`, `mode`, `a`, `b`, `corr`, `agree_active`, `both_flat`, `redundant`.

**Use.** `pandas.read_csv('research/results/combination_redundancy_sol_short.csv')` — regenerate with the driver that names it.

#### `research/results/configuration_counts.json`

`result` · 13 lines · 222 B · description: **derived**

**Purpose.** Generated JSON object, 10 keys (long/pairs, long/singles, long/triples, medium/pairs, medium/singles, medium/triples...).

**Use.** `json.load(open('research/results/configuration_counts.json'))`

#### `research/results/cpcv_all25_1h.csv`

`result` · 27 lines · 2,477 B · description: **derived**

**Purpose.** Generated data: 25 rows x 11 columns (strategy, label, n_paths, usable_blocks, median_sharpe, q1_sharpe, q3_sharpe, iqr...).

**Contents.** Columns: `strategy`, `label`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr`, `frac_paths_positive`, `median_return`, `total_trades`.

**Use.** `pandas.read_csv('research/results/cpcv_all25_1h.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_all25_btc_eth_1d.csv`

`result` · 52 lines · 3,568 B · description: **derived**

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

`result` · 1048 lines · 203,572 B · description: **derived**

**Purpose.** Generated data: 1046 rows x 16 columns (horizon, kind, label, mode, family, n_paths, usable_blocks, median_sharpe...).

**Contents.** Columns: `horizon`, `kind`, `label`, `mode`, `family`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr_spread`, `frac_paths_positive`, `median_path_return`, `total_trades`, `insufficient`, `reason`.

**Use.** `pandas.read_csv('research/results/cpcv_combos_results.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_combos_tables.md`

`result` · 145 lines · 12,226 B · description: **extracted**

**Purpose.** _Top 15 of 262 evaluable shown._ _Top 15 of 52 evaluable shown._ _Top 15 of 260 evaluable shown._

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/cpcv_pbo.json`

`result` · 127 lines · 2,601 B · description: **derived**

**Purpose.** Generated JSON array, 3 entries.

**Use.** `json.load(open('research/results/cpcv_pbo.json'))`

#### `research/results/cpcv_results.csv`

`result` · 77 lines · 13,356 B · description: **derived**

**Purpose.** Generated data: 75 rows x 15 columns (horizon, strategy, label, family, n_paths, usable_blocks, median_sharpe, q1_sharpe...).

**Contents.** Columns: `horizon`, `strategy`, `label`, `family`, `n_paths`, `usable_blocks`, `median_sharpe`, `q1_sharpe`, `q3_sharpe`, `iqr_spread`, `frac_paths_positive`, `median_path_return`, `total_trades`, `insufficient`, `reason`.

**Use.** `pandas.read_csv('research/results/cpcv_results.csv')` — regenerate with the driver that names it.

#### `research/results/cpcv_tables.md`

`result` · 94 lines · 7,016 B · description: **curated**

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

`result` · 20 lines · 2,679 B · description: **derived**

**Purpose.** Generated data: 18 rows x 18 columns (interval, mode, block, bars, lower, upper, capital_deployed, round_trips...).

**Contents.** Columns: `interval`, `mode`, `block`, `bars`, `lower`, `upper`, `capital_deployed`, `round_trips`, `realized_usd`, `pct_of_deployed`, `grid_total_return`, `grid_max_drawdown`, `hold_total_return`, `hold_max_drawdown`, `pct_bars_outside_ladder`, `buys`, `sells`, `forced_exit_qty`.

**Use.** `pandas.read_csv('research/results/ladder_grid_sol.csv')` — regenerate with the driver that names it.

#### `research/results/minute_coverage.json`

`result` · 153 lines · 4,392 B · description: **derived**

**Purpose.** Generated JSON object, 5 keys (generated, interval, venue, note, assets).

**Use.** `json.load(open('research/results/minute_coverage.json'))`

#### `research/results/minute_sweep_x1_common.csv`

`result` · 202 lines · 36,423 B · description: **derived**

**Purpose.** Generated data: 200 rows x 19 columns (asset, strategy, params, bars, first, last, trades, net_return_pct...).

**Contents.** Columns: `asset`, `strategy`, `params`, `bars`, `first`, `last`, `trades`, `net_return_pct`, `gross_return_pct`, `net_sharpe`, `gross_sharpe`, `max_drawdown_pct`, `fees_usd`, `borrow_fees_usd`, `cost_share_of_capital`, `exposure_fraction`, `liquidations`, `seconds`, `error`.

**Use.** `pandas.read_csv('research/results/minute_sweep_x1_common.csv')` — regenerate with the driver that names it.

#### `research/results/minute_sweep_x1_common.txt`

`result` · 265 lines · 23,244 B · description: **derived**

**Purpose.** Generated report. Opens: PRELIMINARY 1-MINUTE SWEEP -- all cached assets x all registered strategies / parameter scale: x1 (bar counts as written)   window: common calendar across assets, capped at 500,000   fees 6bps + slippage 2bps

**Use.** Read it; regenerate with the driver that produced it.

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

#### `research/results/perturb_medium_adx_trend.csv`

`result` · 10 lines · 954 B · description: **derived**

**Purpose.** Generated data: 8 rows x 7 columns (what, median_sharpe, iqr, frac_positive, median_return, trades, evaluable).

**Contents.** Columns: `what`, `median_sharpe`, `iqr`, `frac_positive`, `median_return`, `trades`, `evaluable`.

**Use.** `pandas.read_csv('research/results/perturb_medium_adx_trend.csv')` — regenerate with the driver that names it.

#### `research/results/perturb_medium_adx_trend.json`

`result` · 11 lines · 256 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (target, horizon, baseline_median_sharpe, baseline_iqr, max_abs_delta, ratio_to_iqr...).

**Use.** `json.load(open('research/results/perturb_medium_adx_trend.json'))`

#### `research/results/perturb_medium_adx_trend.txt`

`result` · 22 lines · 1,516 B · description: **derived**

**Purpose.** Generated report. Opens: PARAMETER-PERTURBATION STABILITY CHECK / target   : adx_trend

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/rotation_5coin_1d.csv`

`result` · 146 lines · 25,046 B · description: **derived**

**Purpose.** Generated data: 144 rows x 14 columns (window, top_k, direction, margin, book, is_sharpe, is_monthly_pct, oos_sharpe...).

**Contents.** Columns: `window`, `top_k`, `direction`, `margin`, `book`, `is_sharpe`, `is_monthly_pct`, `oos_sharpe`, `oos_monthly_pct`, `oos_gross_sharpe`, `oos_rotations`, `oos_max_dd`, `decay_sharpe`, `rankable`.

**Use.** `pandas.read_csv('research/results/rotation_5coin_1d.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_btc_long.csv`

`result` · 278 lines · 31,033 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_btc_long.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_btc_medium.csv`

`result` · 278 lines · 31,016 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_btc_medium.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_eth_long.csv`

`result` · 278 lines · 30,720 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_eth_long.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_eth_medium.csv`

`result` · 278 lines · 30,787 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_eth_medium.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_sol_long.csv`

`result` · 278 lines · 30,680 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_sol_long.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_sol_medium.csv`

`result` · 278 lines · 30,826 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_sol_medium.csv')` — regenerate with the driver that names it.

#### `research/results/signal_redundancy_sol_short.csv`

`result` · 278 lines · 31,085 B · description: **derived**

**Purpose.** Generated data: 276 rows x 9 columns (a, b, family_a, family_b, cross_family, corr, agree_active, agree_all...).

**Contents.** Columns: `a`, `b`, `family_a`, `family_b`, `cross_family`, `corr`, `agree_active`, `agree_all`, `redundant`.

**Use.** `pandas.read_csv('research/results/signal_redundancy_sol_short.csv')` — regenerate with the driver that names it.

#### `research/results/sweep_results.csv`

`result` · 955 lines · 290,780 B · description: **derived**

**Purpose.** Generated data: 953 rows x 21 columns (label, kind, horizon, families, mode, rankable, full_return, full_sharpe...).

**Contents.** Columns: `label`, `kind`, `horizon`, `families`, `mode`, `rankable`, `full_return`, `full_sharpe`, `full_maxdd`, `full_trades`, `full_exposure`, `is_return`, `is_sharpe`, `is_maxdd`, `is_trades`, `is_exposure`, `oos_return`, `oos_sharpe`, `oos_maxdd`, `oos_trades`, `oos_exposure`.

**Use.** `pandas.read_csv('research/results/sweep_results.csv')` — regenerate with the driver that names it.

#### `research/results/tables.md`

`result` · 178 lines · 17,493 B · description: **extracted**

**Purpose.** _1 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `buy_and_hold`._ _27 configuration(s) excluded from the ranking for fewer than 10 out-of-sample trades: `all(macd+hurst_switch)`, `all(ichimoku+hurst_switch)`, `all(dual_momentum+hurst_switch)`, `all(sma_regime+hurst_switch)`, `all(adx_trend+bb_reversion)`, `all(adx_trend+vwap_reversion)`, `all(adx_trend+ou_rever

**Use.** Read it; regenerate with the driver that produced it.

#### `research/results/top_coins.csv`

`result` · 17 lines · 910 B · description: **derived**

**Purpose.** Generated data: 15 rows x 8 columns (rank, symbol, name, price_usd, market_cap_usd, volume_24h_usd, pegged, local_data).

**Contents.** Columns: `rank`, `symbol`, `name`, `price_usd`, `market_cap_usd`, `volume_24h_usd`, `pegged`, `local_data`.

**Use.** `pandas.read_csv('research/results/top_coins.csv')` — regenerate with the driver that names it.

---

## extension

The Chrome extension, and the only component that can place a real order. Dry-run is the default, risk rails live in code and fail closed, and a fresh install must not be able to trade.

37 files.

#### `extension/README.md`

`doc` · 471 lines · 28,325 B · description: **extracted**

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

`code-js` · 509 lines · 18,754 B · description: **extracted**

**Purpose.** The command registry — single source of truth for every action this project can perform. Three surfaces drive this one registry: extension src/bg/service-worker.js (chrome.runtime messages) CLI tools/cli.js (argv) HTTP API tools/api-server.js (POST /v1/<command>) Nothing may be reachable from one surface and not the others.

**Contents.** Defines `COMMANDS`, `COMMAND_NAMES`, `TYPE`, `class CommandError`, `currentPrice`, `describeCommands`, `pnlSnapshot`, `runCommand`, `summarisePnl`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/engine.js`

`code-js` · 445 lines · 17,211 B · description: **extracted**

**Purpose.** The tick. Order of operations is the whole design: RECONCILE before PLAN, always. A MV3 service worker can be killed at any moment, including between "write the intent" and "the venue accepted the order". So the venue's live order list — not our local records — is the source of truth at the top of every tick. Local state is a cache and a journal, nothing more.

**Contents.** Defines `PRICE_MATCH_TOLERANCE`, `ingestFills`, `keyForLiveOrder`, `matchIntent`, `pricesMatch`, `reconcile`, `summarise`, `tick`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/grid.js`

`code-js` · 374 lines · 13,928 B · description: **extracted**

**Purpose.** Pure grid-strategy engine. No I/O, no chrome.* APIs, no network. Everything here is a deterministic function of (config, price, open state) so the whole strategy is unit testable and a service-worker restart can recompute intent from scratch.

**Contents.** Defines `DIRECTION`, `SIDE`, `SPACING`, `capitalRequirement`, `expectedRoundTripUsd`, `gridLevels`, `intentKey`, `nearestLevelIndex`, `pairedExitLevel`, `planGrid` and 4 more.

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

#### `extension/src/jupiter/websocket.js`

`code-js` · 95 lines · 2,377 B · description: **extracted**

**Purpose.** Jupiter / Solana native RPC WebSocket integration. Subscribes to account/log events for real-time trade data and execution feedback without polling.

**Contents.** Defines `class JupiterWebsocket`.

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

`code-js` · 255 lines · 8,153 B · description: **extracted**

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

`code-js` · 246 lines · 8,438 B · description: **extracted**

**Purpose.** Venue layer. The grid engine is venue-agnostic: it emits intents, and a venue adapter turns them into orders. That seam exists because the two candidate venues on Jupiter are in very different states of readiness: Trigger V2 — REST, returns signable transactions. Live-capable today. SPOT. Perps — NO public REST write API as of 2026-08-04.

**Contents.** Defines `MODE`, `buildVenue`, `class DryRunVenue`, `class NotImplemented`, `class PerpsVenueReadOnly`, `leverageFeasibility`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/venues/jupiterLiveVenue.js`

`code-js` · 86 lines · 2,580 B · description: **extracted**

**Purpose.** Live Jupiter execution venue (standard Swaps).

**Contents.** Defines `class JupiterLiveVenue`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/venues/krakenVenue.js`

`code-js` · 154 lines · 4,955 B · description: **extracted**

**Purpose.** Kraken REST and WebSocket venue adapter. Handles live order execution and margin capabilities on Kraken.

**Contents.** Defines `class KrakenVenue`.

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

`code-js` · 1308 lines · 49,607 B · description: **curated**

**Purpose.** Node test-runner suite for the pure core — grid maths, planner, reconciler. No `chrome.*`, so it runs headless.

**Contents.** Defines `CONFIG`, `ORDER`, `RC_CONFIG`, `RECON_CONFIG`, `STATE`, `seedResting`.

**Use.** `node --test extension/test/` or `npm test` in `extension/`.

#### `extension/test/surfaces.test.js`

`code-js` · 444 lines · 16,906 B · description: **curated**

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

#### `extension/tools/measure-recentre.js`

`code-js` · 160 lines · 6,399 B · description: **extracted**

**Purpose.** How often does the shipped auto-recentre gate actually open? node tools/measure-recentre.js --csv ../data/SOL_1d.csv `recentreDecision()` refuses to move the ladder while anything is resting or any lot is open, because `tick()` cannot cancel. That gate is deliberately tight, and the honest question is whether it is so tight the feature never fires.

**Contents.** Defines `closeColumn`, `main`, `parseArgs`, `recordingVenue`, `run`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/verify-endpoints.js`

`code-js` · 80 lines · 3,155 B · description: **extracted**

**Purpose.** Live endpoint check. Confirms the read-side assumptions this extension hardcodes still hold, so a Jupiter API change surfaces here rather than mid-tick. Read-only: nothing is signed, deposited, or ordered. node tools/verify-endpoints.js JUPITER_API_KEY=... node tools/verify-endpoints.js # also checks the keyed tier

**Contents.** Defines `MINTS`, `checkPrice`, `checkTriggerReachable`, `report`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

---

## soltui

The macOS menu-bar app that surfaces state locally. Packaged with py2app and supervised by launchd.

36 files.

#### `soltui/README.md`

`doc` · 168 lines · 8,656 B · description: **extracted**

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

#### `soltui/analyze.py`

`code-python` · 214 lines · 8,255 B · description: **extracted**

**Purpose.** What every strategy, signal and indicator said about one coin at one moment. Pure logic behind the Analyze tab. No Textual import, no widget. ## It wraps `research/decide.py`; it does not reimplement it `decide.py`'s one substantive guarantee is that the exposures it reports are the numbers the engine would have acted on.

**Contents.** Defines `REPO`, `DATA_DIR`, `class Series`, `class Analysis`, `available_assets()`, `load_series()`, `parse_as_of()`, `slice_to()`, `analyse()`. Depends on `backtester`, `research`.

**Use.** `import soltui.analyze`

#### `soltui/app.py`

`code-python` · 254 lines · 10,172 B · description: **extracted**

**Purpose.** macOS menu-bar shell. Thin by design. python3 -m soltui.app Mirrors `netdnsmonitor/app.py`: every decision lives in already-tested modules (`status`, `config`, `roster`, `runner`), and this file only wires them to a `rumps.Timer` and a status-item title.

**Contents.** Defines `REPO`, `RESULTS_DIR`, `_wait_for_port()`, `_rumps()`, `build_app()`, `main()`.

**Use.** `python3 soltui/app.py --help`

#### `soltui/bgcontrol.py`

`code-python` · 329 lines · 13,275 B · description: **extracted**

**Purpose.** Start, stop and inspect the background sweep process. Separated from `bgqueue` (which is pure logic) and from `bgworker` (which is the work) because process lifecycle is the part with the OS-specific behaviour, and keeping it in one small module is what lets the other two stay testable.

**Contents.** Defines `LOCK_PATH`, `LOCK_FD_ENV`, `TASKPOLICY_PATHS`, `taskpolicy_path()`, `taskpolicy_available()`, `describe_priority()`, `read_pid()`, `acquire_lock()`, `is_running()`, `worker_command()` and 4 more.

**Use.** `import soltui.bgcontrol`

#### `soltui/bgqueue.py`

`code-python` · 822 lines · 31,401 B · description: **extracted**

**Purpose.** Job queue for the background backtest sweep. Pure logic; no UI, no processes. The TUI's own sweep (`runner.py`) evaluates the roster and blocks a thread until it finishes.

**Contents.** Defines `BG_DIR`, `RESULTS_PATH`, `STATE_PATH`, `PID_PATH`, `ASSET_RE`, `MIN_TRADES`, `HORIZON_INTERVAL`, `LIKELIHOOD_ORDER`, `_UNKNOWN_LIKELIHOOD`, `class Job` and 26 more. Depends on `backtester`.

**Use.** `import soltui.bgqueue`

#### `soltui/bgworker.py`

`code-python` · 408 lines · 14,648 B · description: **extracted**

**Purpose.** The background backtest worker: a separate, low-priority process. python3 -m soltui.bgworker --asset SOL python3 -m soltui.bgworker --asset SOL --horizons medium --max-tier 1 --limit 50 Run directly it is a normal foreground script; the TUI launches it through `bgcontrol.start()`, which is what applies the background scheduling policy.

**Contents.** Defines `REPO`, `NICE_LEVEL`, `class _Stop`, `lower_priority()`, `class ArrayCache`, `evaluate()`, `failed_result()`, `run()`, `build_parser()`, `main()`. Depends on `backtester`.

**Use.** `python3 soltui/bgworker.py --help`

#### `soltui/config.py`

`code-python` · 175 lines · 6,883 B · description: **extracted**

**Purpose.** Settings load/save for the TUI. Pure logic; no UI, no I/O beyond one file. Config lives at `~/.config/soltui/config.yaml`, following the same convention as `netdnsmonitor`. YAML is optional at runtime -- if PyYAML is missing the app falls back to JSON at the same path with a `.json` suffix, so a missing optional dependency degrades rather than crashes.

**Contents.** Defines `CONFIG_DIR`, `CONFIG_PATH`, `CONFIG_PATH_JSON`, `INTERVALS`, `MODES`, `class ConfigError`, `class Settings`, `default_settings()`, `validate()`, `load_settings()` and 3 more.

**Use.** `import soltui.config`

#### `soltui/cumulative.py`

`code-python` · 242 lines · 9,053 B · description: **extracted**

**Purpose.** Aggregate every committed backtest result — with the evidence floor applied. Pure logic behind the Cumulative tab. No Textual import, no widget. ## The defect this module is built to avoid `cpcv_evaluate` marks a configuration `insufficient` when it falls below `min_total_trades`, prints it **DROPPED**, and **still returns a full path count**.

**Contents.** Defines `REPO`, `RESULTS_DIR`, `MIN_RANKABLE_TRADES`, `COLUMNS`, `_pick()`, `_as_float()`, `_as_int()`, `class ResultRow`, `class FileSummary`, `load_result_file()` and 4 more.

**Use.** `import soltui.cumulative`

#### `soltui/docs_browser.py`

`code-python` · 235 lines · 9,848 B · description: **extracted**

**Purpose.** Read-only catalogue and file reader behind the Docs tab. Pure logic: no Textual import, no widget, no I/O beyond reading files the catalogue already lists. That split is what lets this be tested without driving a terminal, and it matches `config.py`, `roster.py` and the other modules the TUI sits on.

**Contents.** Defines `REPO`, `INDEX_JSON`, `MAX_VIEW_BYTES`, `NO_WRITE_PREFIXES`, `LANGUAGES`, `class DocEntry`, `class CatalogUnavailable`, `load_catalog()`, `kinds_of()`, `filter_entries()` and 6 more.

**Use.** `import soltui.docs_browser`

#### `soltui/live_run.py`

`code-python` · 85 lines · 2,925 B · description: **extracted**

**Purpose.** Live Run dashboard for SolTUI. Loads the best configuration from TOP5-RECOMMENDATION (or untested sweep) and provides a UI to launch the Node.js extension in dry-run mode.

**Contents.** Defines `REPO`, `RECOMMENDATION_FILE`, `get_best_strategy()`, `spawn_dryrun()`. Depends on `backtester`.

**Use.** `import soltui.live_run`

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

`data` · 27 lines · 1,359 B · description: **curated**

**Purpose.** Runtime dependencies for the menu-bar app (rumps/pyobjc and the py2app build tooling).

**Use.** `python3 -m pip install -r soltui/requirements.txt`.

#### `soltui/roster.py`

`code-python` · 165 lines · 5,965 B · description: **extracted**

**Purpose.** The user's strategy roster: which strategies are active, with what parameters. Backs the Strategies tab. Kept pure so add/remove is testable without a UI. Two invariants worth stating, because both prevent a class of confusing failure later rather than at the point of the mistake: 1.

**Contents.** Defines `class RosterError`, `class RosterEntry`, `class Roster`, `available_strategies()`. Depends on `backtester`.

**Use.** `import soltui.roster`

#### `soltui/runner.py`

`code-python` · 281 lines · 9,472 B · description: **extracted**

**Purpose.** Background sweep runner. Turns a roster into results while keeping the UI live. The menu-bar indicator and the Backtest tab both need "how much is left", which means the sweep has to report progress as it goes rather than blocking until done. This module owns that: a worker thread, a progress callback, and a cancellation flag.

**Contents.** Defines `class SweepRow`, `class SweepOutcome`, `load_arrays()`, `engine_config()`, `run_cpcv()`, `class SweepRunner`, `quick_backtest()`. Depends on `backtester`.

**Use.** `import soltui.runner`

#### `soltui/serve.py`

`code-python` · 134 lines · 4,875 B · description: **extracted**

**Purpose.** Serve the Textual console as a real window, without needing a TTY. python3 -m soltui.serve # then open the printed URL python3 -m soltui.serve --port 8899 --no-open ## Why this exists The console has had five tabs, buttons and settings since it was written — but the only way to reach them was `app.py`'s "Open TUI" menu item, which does: tell application "Terminal" to do script "cd <repo> && python

**Contents.** Defines `REPO`, `DEFAULT_PORT`, `HOST`, `app_command()`, `port_is_free()`, `find_port()`, `url_for()`, `serve()`, `main()`.

**Use.** `python3 soltui/serve.py --help`

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

`other` · 349 lines · 13,509 B · description: **curated**

**Purpose.** Install-and-supervise script for the menu-bar app: builds the py2app bundle, writes the launchd agent, and manages the flag file that is the real off switch (because `KeepAlive` necessarily overrides the app's own Quit item).

**Use.** `python3 soltui/soltui-service status|start|stop|build`.

#### `soltui/status.py`

`code-python` · 207 lines · 7,938 B · description: **extracted**

**Purpose.** Pure menu-bar title logic, kept out of the rumps shell so it is testable without a real macOS event loop. Mirrors `netdnsmonitor/status.py`: one pure `build_title()` the app calls every tick, plus the state it reads.

**Contents.** Defines `ICONS`, `MAX_TITLE_CHARS`, `MAX_ACTIVITY_CHARS`, `MAX_ERROR_CHARS`, `class Phase`, `class AppState`, `format_pct()`, `build_title()`, `_shorten()`, `_clip()` and 1 more.

**Use.** `import soltui.status`

#### `soltui/top5.py`

`code-python` · 219 lines · 8,608 B · description: **extracted**

**Purpose.** The five recommended configurations, read from the committed evidence. Pure logic behind the Top 5 tab. No Textual import, no widget, and — like `cumulative.py` — no re-computation: this reads what the research drivers wrote and cannot disagree with `verify_numbers.py`.

**Contents.** Defines `REPO`, `TOP5_CSV`, `HOME_ASSET`, `REPRO_COMMAND`, `_COMPOSITE`, `class EvidenceUnavailable`, `class AssetResult`, `class Top5Config`, `parse_members()`, `_f()` and 3 more.

**Use.** `import soltui.top5`

#### `soltui/tui.py`

`code-python` · 1976 lines · 91,010 B · description: **extracted**

**Purpose.** Textual TUI: the console over the backtester. python3 -m soltui.tui Tabs: Settings, Strategies, Signals, Backtest, Top 5, Execute (dry-run only), Analyze, Cumulative, Research, Docs. All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`, `status`); this file is presentation and wiring.

**Contents.** Defines `RESEARCH_DRIVERS`, `RESEARCH_FINDINGS`, `FAMILY_NOTES`, `SIGNAL_REFERENCE`, `_mtime()`, `sort_key()`, `HEADER_GLOSSARY`, `class GlossaryTable`, `class VimTextArea`, `class SolTuiApp` and 1 more. Depends on `backtester`.

**Use.** `python3 soltui/tui.py --help`

### `soltui/tests/`

#### `soltui/tests/__init__.py`

`test` · 0 lines · 0 B · description: **curated**

**Purpose.** Package marker for the app's tests. Empty.

**Use.** Nothing to run.

#### `soltui/tests/test_bgcontrol.py`

`test` · 234 lines · 9,675 B · description: **extracted**

**Purpose.** Tests for the background worker's process lifecycle. Two of these exist because the bug they describe actually shipped in an earlier draft of this module and only turned up when the worker was spawned for real: `taskpolicy` lives in /usr/sbin rather than /usr/bin, and the pidfile was written by the child late enough that Stop-after-Start found nothing to signal.

**Contents.** Defines `class TestTaskpolicyLookup`, `class TestStartReleasesTheLockOnFailure`, `class TestWorkerCommand`, `class TestFetchCommand`, `class TestPidfile`, `class TestLivenessLock`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgcontrol.py -q`

#### `soltui/tests/test_bgqueue.py`

`test` · 640 lines · 28,607 B · description: **extracted**

**Purpose.** Tests for the background sweep's queue, file contract and leaderboard. The properties worth defending here are the ones a background process makes hard to notice going wrong: an ordering that stops putting the published preset first, a resume that re-runs finished work, a reader that dies on a torn line, and — most importantly — a leaderboard that quietly ranks a Sharpe computed from three trades.

**Contents.** Defines `_result()`, `class TestJobIdentity`, `class TestPerturbation`, `class TestOrdering`, `class TestDedupe`, `class TestHorizonInterval`, `class TestBuildQueue`, `class TestPending`, `class TestFileContract`, `class TestLeaderboard` and 8 more. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgqueue.py -q`

#### `soltui/tests/test_bgworker.py`

`test` · 248 lines · 9,998 B · description: **extracted**

**Purpose.** Tests for the background worker's run loop. `run()` takes its results path, state path, settings and stop flag as arguments precisely so the loop can be driven without spawning a process or touching real price data — the strategy evaluation itself is patched out, because what is under test here is the *loop*: resume, stop, limit, and the failure paths.

**Contents.** Defines `_jobs()`, `_ok()`, `class _RunCase`, `class TestRunLoop`, `class TestFailurePaths`, `class TestFailedResult`, `class TestArrayCache`, `class TestPriority`, `class TestAssetValidation`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgworker.py -q`

#### `soltui/tests/test_docs_browser.py`

`test` · 147 lines · 6,034 B · description: **extracted**

**Purpose.** Tests for the Docs tab's editing guards. The load-bearing assertions are the refusals: a file under `research/results/` or not in the catalogue must never be writable, regardless of what the caller claims about it. Those are the properties a UI bug could silently violate, so they are asserted directly rather than left to code review.

**Contents.** Defines `_entry()`, `class IsEditableTests`, `class WriteDocumentTests`, `class ReadDocumentRealTextFlagTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_docs_browser.py -q`

#### `soltui/tests/test_panes.py`

`test` · 263 lines · 11,679 B · description: **extracted**

**Purpose.** The four modules behind the new console tabs. No test here drives a terminal, opens a socket, or reads `data/`. That is the same split the rest of this package keeps: `tui.py` is presentation, and the logic lives in modules that can be tested without an event loop. The two worth reading first are `test_a_below_floor_row_is_never_rankable` and `test_slicing_happens_before_the_replay`.

**Contents.** Defines `write_index()`, `class DocsBrowserTests`, `class CumulativeTests`, `class AnalyzeTests`, `class ServeTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_panes.py -q`

#### `soltui/tests/test_service.py`

`test` · 132 lines · 5,091 B · description: **extracted**

**Purpose.** Tests for `soltui-service`, the LaunchAgent manager. The script is dash-named so that it reads as a command rather than a module, which means it cannot be imported normally; it is loaded by path below. What these cover is one failure that cost a debugging session: the agent plist sitting on disk while launchd knows nothing about it.

**Contents.** Defines `REPO`, `SERVICE`, `load_service()`, `ok()`, `fail()`, `class ServiceTestCase`, `class StartLoadsTheAgent`.

**Use.** `python3 -m pytest soltui/tests/test_service.py -q`

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

#### `soltui/tests/test_top5.py`

`test` · 133 lines · 5,758 B · description: **extracted**

**Purpose.** Tests for the Top 5 tab's pure module. The load-bearing assertions: the module reads the committed evidence file faithfully (ranks, home rows, transfers), never turns absent evidence into a zero, and recovers composite members from labels without a duplicated name-to-members table that could drift from research/cross_asset_cpcv.py.

**Contents.** Defines `HEADER`, `write_csv()`, `class ParseMembersTests`, `class LoadTop5Tests`, `class RosterCandidatesTests`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_top5.py -q`

#### `soltui/tests/test_tui.py`

`test` · 1164 lines · 50,479 B · description: **extracted**

**Purpose.** Smoke tests for the Textual app, driven through Textual's own test harness. An app that imports cleanly but explodes on mount is not working, so these actually mount it, click things, and assert on widget state. `run_test()` runs a headless terminal, so no TTY is required and this is safe in CI.

**Contents.** Defines `_queue_row()`, `TEST_SIZE`, `text_of()`, `make_settings()`, `class TestSortKey`, `class TestSortableTables`, `class TestAppMounts`, `class TestQueueTab`, `class TestExecuteTabSafety`, `class TestStrategiesTab` and 8 more. Depends on `backtester`, `soltui`.

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

`ci` · 89 lines · 4,623 B · description: **extracted**

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

`ci` · 219 lines · 7,878 B · description: **curated**

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

`doc` · 93 lines · 5,322 B · description: **extracted**

**Purpose.** Commits `724bedf` + `a90455a`. `recentreDecision()` moves the ladder to 0.85x–1.15x of price (`tools/dryrun.js`'s convention, deliberately not a second one). **Off by default.** inventory can place that lot's sell **below its own entry** — the zero-spread bug, except it now

**Use.** Read it.

---

## .githooks

2 files.

#### `.githooks/pre-commit`

`other` · 39 lines · 1,298 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `.githooks/pre-merge-commit`

`other` · 27 lines · 944 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

---

## mongo

15 files.

#### `mongo/README.md`

`doc` · 172 lines · 8,328 B · description: **extracted**

**Purpose.** A read-mostly MongoDB copy of everything this repo has measured: price history, strategies and their cards, the signal and indicator layers, per-bar readouts, backtest runs, CPCV and sweep results, the coin write-ups, and the test-suite

**Use.** Read it.

#### `mongo/__init__.py`

`code-python` · 0 lines · 0 B · description: **none**

**Purpose.** _No description available._

**Use.** `import mongo.__init__`

#### `mongo/load.py`

`code-python` · 794 lines · 27,517 B · description: **extracted**

**Purpose.** Load the repo's research artifacts into the local MongoDB store. pip install -r mongo/requirements.txt python3 mongo/load.py # everything python3 mongo/load.py --only bars,strategies python3 mongo/load.py --dry-run # count what would load, write nothing **This loader is destructive by design and idempotent by consequence.** It drops and recreates every collection it writes.

**Contents.** Defines `REPO`, `LOADED_AT`, `sha256()`, `provenance()`, `clean()`, `maybe_number()`, `read_csv_rows()`, `git_sha()`, `utc()`, `bar_files()` and 18 more. Depends on `backtester`, `research`.

**Use.** `python3 mongo/load.py --help`

#### `mongo/requirements.txt`

`data` · 6 lines · 287 B · description: **derived**

**Purpose.** Generated report. Opens: # Deliberately separate from backtester/requirements.txt. The backtester is / # stdlib-first and its dependency list is short on purpose; a driver needed only

**Use.** Read it.

#### `mongo/schema.py`

`code-python` · 466 lines · 19,165 B · description: **extracted**

**Purpose.** Collection layout for the local research store: specs, validators, indexes. python3 mongo/schema.py --create # create everything (drops first) python3 mongo/schema.py --describe # print the layout, touch nothing Design notes, because the shape is the part worth arguing about: * **Bars are a native time series collection.** Per-bar, time-ordered, append-only measurements are what that collection ty

**Contents.** Defines `DB_NAME`, `PROVENANCE_REQUIRED`, `_doc()`, `ALL_COLLECTIONS`, `connect()`, `create()`, `describe()`, `main()`.

**Use.** `python3 mongo/schema.py --help`

### `mongo/queries/`

#### `mongo/queries/01-coins-and-bars.js`

`code-js` · 110 lines · 3,592 B · description: **extracted**

**Purpose.** Coins and price history. mongosh solmargintrader mongo/queries/01-coins-and-bars.js `bars` is a native time series collection: `ts` is the time field and `series` the metaField, so every query below should filter on `series.*` and a time range. MongoDB creates the meta+time index itself; there are no user indexes to add.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/02-strategies-and-cards.js`

`code-js` · 105 lines · 3,577 B · description: **extracted**

**Purpose.** Strategies and their cards. mongosh solmargintrader mongo/queries/02-strategies-and-cards.js One document per strategy card (45). The card's own vocabulary is preserved rather than flattened into a boolean: registry_key a string for the 25 registered `Strategy` implementations, null otherwise.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/03-signals-and-indicators.js`

`code-js` · 72 lines · 2,448 B · description: **extracted**

**Purpose.** Signals and indicators — the two layers beneath the strategies. mongosh solmargintrader mongo/queries/03-signals-and-indicators.js These are small reference collections (15 and 20 documents). They exist so a reader can answer "what does this rule actually compare?" without opening research/decide.py, and so the readouts in `decisions` can be joined to their definitions.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/04-decisions.js`

`code-js` · 131 lines · 4,298 B · description: **extracted**

**Purpose.** Per-bar readouts: what every rule said about the last bar of a series. mongosh solmargintrader mongo/queries/04-decisions.js Each document is `research.decide.build_report()` output verbatim, plus provenance. That is deliberate -- re-deriving a Mongo-specific shape would let the store and the readout disagree about what a strategy said. Read the header fields before the verdicts.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/05-backtests.js`

`code-js` · 119 lines · 3,852 B · description: **extracted**

**Purpose.** Backtest runs: manifests, per-strategy metrics, equity curves, fills. mongosh solmargintrader mongo/queries/05-backtests.js Three collections, split by cardinality rather than by topic: backtest_runs one document per run. The manifest is embedded because it is always read with the run, and the per-strategy metrics table is bounded by the strategies that ran.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/06-experiments-and-pbo.js`

`code-js` · 151 lines · 4,901 B · description: **extracted**

**Purpose.** Experiments: CPCV, sweeps, perturbations, geometry — and PBO. mongosh solmargintrader mongo/queries/06-experiments-and-pbo.js Two collections: experiments one document per result file: kind, name, columns, and the JSON sidecar when it is a single object. experiment_rows one document per row.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/07-documents-and-search.js`

`code-js` · 75 lines · 2,642 B · description: **extracted**

**Purpose.** Reference prose: coin intelligence, research write-ups, component docs. mongosh solmargintrader mongo/queries/07-documents-and-search.js One document per markdown file, with a full-text index on title and body. A server allows one text index per collection, and this is it. Caveat worth keeping in mind: prose in a strategy card is *argument*, not checked fact.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `mongo/queries/08-provenance-and-health.js`

`code-js` · 125 lines · 4,287 B · description: **extracted**

**Purpose.** Provenance, freshness and store health — run this before trusting anything else. mongosh solmargintrader mongo/queries/08-provenance-and-health.js Every document carries `source_path`, `source_sha256` and `loaded_at`. That is not bookkeeping: it is what lets a number here be traced to a file, and a file to the run that produced it. A figure with no provenance is not a figure.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `mongo/tests/`

#### `mongo/tests/__init__.py`

`test` · 0 lines · 0 B · description: **none**

**Purpose.** _No description available._

**Use.** `python3 -m pytest mongo/tests/__init__.py -q`

#### `mongo/tests/test_load.py`

`test` · 326 lines · 13,584 B · description: **extracted**

**Purpose.** Tests for the local MongoDB research store. The load is destructive by design, so the test that matters most asserts it is therefore *idempotent*: loading twice must leave identical counts. Without that, the time series collections would silently double on a second run -- they accept no unique index, so nothing else would catch it.

**Contents.** Defines `REPO`, `server_available()`, `SERVER`, `class TestPureHelpers`, `class TestSchemaLayout`, `class TestLoadedStore`, `class TestIdempotency`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest mongo/tests/test_load.py -q`

---

## scripts

2 files.

#### `scripts/build_doc_index.py`

`code-python` · 180 lines · 6,231 B · description: **extracted**

**Purpose.** Generate `docs/high_signal_file_index.json` from `docs/codebase-overview.md`. python3 scripts/build_doc_index.py The overview is the human-readable file map; the JSON is the machine-readable one for LLM retrieval.

**Contents.** Defines `REPO`, `OVERVIEW`, `INDEX`, `COMPONENTS`, `ROW`, `KIND_BY_SUFFIX`, `git_ok()`, `is_tracked()`, `is_ignored()`, `excluded()` and 4 more.

**Use.** `python3 scripts/build_doc_index.py --help`

#### `scripts/check_docs.py`

`code-python` · 381 lines · 14,768 B · description: **extracted**

**Purpose.** Fail the build when the docs drift from the repo. python3 scripts/check_docs.py python3 scripts/check_docs.py --prune # drop dead index entries Two kinds of rot, both of which happened here before this existed: * **Stale test counts.** The docs claimed 250 backtester tests for several commits while the suite had grown to 454.

**Contents.** Defines `REPO`, `COUNT_DOCS`, `INDEX_JSON`, `OVERVIEW_MD`, `is_ignored()`, `is_tracked()`, `missing_and_tracked()`, `committed_test_files()`, `count_tests()`, `load_failures()` and 9 more.

**Use.** `python3 scripts/check_docs.py --help`

---

## skills

61 files.

#### `skills/README.md`

`doc` · 29 lines · 1,436 B · description: **extracted**

**Purpose.** Version-controlled copies of the Claude Code skills this project's research depends on. The live skills are installed at `~/.claude/skills/`, which is outside this repository and not version-controlled. Several of this project's research documents cite them as the source of a

**Use.** Read it.

### `skills/trading-and-investing/`

#### `skills/trading-and-investing/SCHEDULED-RESEARCH.md`

`doc` · 80 lines · 3,887 B · description: **extracted**

**Purpose.** in-file, and each file's header note states that an `UNSOURCED` marker is *not* a citation. 21 footnote markers across two references cite claims that **have no source**. They are not broken links — the definitions were never written by the original `/dr` research artifact, which cited five

**Use.** Read it.

#### `skills/trading-and-investing/SKILL.md`

`doc` · 363 lines · 70,317 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/manifest.yaml`

`config` · 204 lines · 12,308 B · description: **none**

**Purpose.** _No description available._

**Use.** Configuration; nothing to run.

### `skills/trading-and-investing/references/`

#### `skills/trading-and-investing/references/ai-and-ml-for-trading.md`

`doc` · 389 lines · 39,597 B · description: **extracted**

**Purpose.** Machine learning applied to financial markets: feature engineering on market data (info bars, fractional differentiation, PIT normalization), gradient boosting for cross-sectional equity signals (Gu/Kelly/Xiu, SHAP, purged CV), neural networks (918-experiment architecture study), alternative data taxonomy (satellite, transaction, NLP), LLMs in finance (FinBERT, BloombergGPT, hallucination risk), R

**Use.** Read it.

#### `skills/trading-and-investing/references/algorithmic-and-quant-trading.md`

`doc` · 448 lines · 34,296 B · description: **extracted**

**Purpose.** <!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/algorithmic-and-quant-trading.md by scripts/persist-spoke.mjs. --> 1. [Overview](#overview) 2. [Backtesting Frameworks](#1-backtesting-frameworks)

**Use.** Read it.

#### `skills/trading-and-investing/references/asset-classes-and-instruments.md`

`doc` · 125 lines · 15,173 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". --> What the major asset classes **are** and how a US retail participant **accesses** each. This is the "what can I trade or own" layer.

**Use.** Read it.

#### `skills/trading-and-investing/references/asset-specific-vs-universal-parameters.md`

`doc` · 259 lines · 15,123 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/cross-asset-generalisation-testing.md`

`doc` · 256 lines · 14,556 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/crypto-and-digital-asset-trading.md`

`doc` · 444 lines · 36,993 B · description: **extracted**

**Purpose.** <!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md by scripts/persist-spoke.mjs. --> 1. [Overview](#overview) 2. [Core Concepts](#core-concepts)

**Use.** Read it.

#### `skills/trading-and-investing/references/defi-and-onchain-trading.md`

`doc` · 629 lines · 38,800 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/derivatives-futures-and-swaps.md`

`doc` · 293 lines · 28,960 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/empirical-backtest-findings-log.md`

`doc` · 437 lines · 27,085 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/equity-fundamentals-and-corporate-actions.md`

`doc` · 290 lines · 39,270 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/fixed-income-and-bond-markets.md`

`doc` · 252 lines · 17,901 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/forex-and-currency-trading.md`

`doc` · 495 lines · 27,004 B · description: **extracted**

**Purpose.** <!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/forex-and-currency-trading.md by scripts/persist-spoke.mjs. --> A spoke of the **`trading-and-investing`** hub.

**Use.** Read it.

#### `skills/trading-and-investing/references/grid-trading-strategy.md`

`doc` · 252 lines · 24,098 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/indicator-signal-implementation-and-backtesting.md`

`doc` · 690 lines · 39,237 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/investing-vs-trading.md`

`doc` · 106 lines · 12,883 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment/tax advice. Volatile claims dated "as of 2026".

**Use.** Read it.

#### `skills/trading-and-investing/references/jlp-risk-profile-and-anti-patterns.md`

`doc` · 151 lines · 21,459 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/jupiter-jlp-pool.md`

`doc` · 229 lines · 23,130 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/jupiter-perps-leverage-and-liquidation.md`

`doc` · 175 lines · 13,808 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/jupiter-perps-trading.md`

`doc` · 262 lines · 29,785 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/jupiter-swap-routing-and-orders.md`

`doc` · 243 lines · 22,095 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/leverage-cost-arithmetic-and-the-viable-region.md`

`doc` · 211 lines · 10,045 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/liquidation-as-an-absorbing-barrier.md`

`doc` · 190 lines · 9,843 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/market-microstructure-and-execution.md`

`doc` · 213 lines · 18,170 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/market-participants-and-structure.md`

`doc` · 88 lines · 10,767 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". --> - **Agency broker** — acts as *agent*, matching your order to the market for a **commission**; doesn't take the other side.

**Use.** Read it.

#### `skills/trading-and-investing/references/market-sessions-and-venues.md`

`doc` · 93 lines · 9,984 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". --> Where things trade, when the market is open, how hours differ across asset classes, and the trading halts that protect markets. Overview depth for the hub. <a id="major-us-venues"></a>

**Use.** Read it.

#### `skills/trading-and-investing/references/ml-backtesting-pitfalls-and-production-systems.md`

`doc` · 189 lines · 15,486 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/onchain-pnl-and-tax-accounting.md`

`doc` · 366 lines · 38,324 B · description: **extracted**

**Purpose.** <!-- run closed 2026-08-04: 3 of 9 sections complete (§2 denominator problem, §7 taxable disposals, §8 per-wallet tax lots). Remaining sections are marked pending in-body and tabulated under "Coverage status — this run". Complete with: /dr --refresh onchain-pnl-and-tax-accounting --> name: onchain-pnl-and-tax-accounting hub: trading-and-investing

**Use.** Read it.

#### `skills/trading-and-investing/references/options-fundamentals.md`

`doc` · 246 lines · 20,081 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/options-trading-and-strategies.md`

`doc` · 218 lines · 18,648 B · description: **extracted**

**Purpose.** <!-- hub-reference-banner --> name: options-trading-and-strategies version: "1.0.0"

**Use.** Read it.

#### `skills/trading-and-investing/references/order-lifecycle-and-execution.md`

`doc` · 91 lines · 11,615 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". --> How a retail order travels from the broker app to the market, the order types every participant should know, and the routing concepts (PFOF, NBBO, best execution).

**Use.** Read it.

#### `skills/trading-and-investing/references/portfolio-theory-and-asset-allocation.md`

`doc` · 232 lines · 18,575 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/regime-detection-and-classification.md`

`doc` · 317 lines · 19,053 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/sampling-frequency-and-bar-aggregation.md`

`doc` · 232 lines · 12,859 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/selection-rule-design.md`

`doc` · 211 lines · 11,615 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/self-custody-wallets-and-key-security.md`

`doc` · 169 lines · 10,267 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/signal-backtest-protocol-and-regime-evidence.md`

`doc` · 475 lines · 32,545 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/signal-pairing-volume-and-pattern-signal-sets.md`

`doc` · 588 lines · 34,234 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/sleeve-weighting-and-objective-selection.md`

`doc` · 224 lines · 12,397 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/solana-dex-and-amm-landscape.md`

`doc` · 245 lines · 15,486 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/solana-execution-agents-keepers-and-rfq.md`

`doc` · 227 lines · 12,630 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/solana-oracles-pyth-switchboard.md`

`doc` · 220 lines · 13,079 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/stock-and-equity-trading.md`

`doc` · 246 lines · 39,324 B · description: **extracted**

**Purpose.** <!-- Provenance: spoke reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research (6 concepts; ~40 independent sources, regulator/exchange/index-provider/peer-reviewed grade). Educational only — NOT financial/investment/tax advice. Volatile claims dated "as of 2026".

**Use.** Read it.

#### `skills/trading-and-investing/references/strategies-and-risk.md`

`doc` · 278 lines · 22,819 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/strategy-backtesting-and-development-workflow.md`

`doc` · 202 lines · 13,373 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/strategy-failure-modes-and-synergy.md`

`doc` · 327 lines · 21,162 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/technical-analysis-breadth-frameworks-and-evidence.md`

`doc` · 455 lines · 37,454 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/technical-analysis.md`

`doc` · 506 lines · 36,934 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/the-greeks.md`

`doc` · 245 lines · 17,626 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-bot-infrastructure-and-monitoring.md`

`doc` · 212 lines · 11,546 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-psychology-and-behavioral-finance.md`

`doc` · 216 lines · 19,836 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-regulation-compliance-and-taxes.md`

`doc` · 244 lines · 22,176 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-risk-management.md`

`doc` · 436 lines · 21,438 B · description: **extracted**

**Purpose.** <!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/trading-risk-management.md by scripts/persist-spoke.mjs. --> A spoke of the **`trading-and-investing`** hub.

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-risks-and-protections.md`

`doc` · 111 lines · 15,315 B · description: **extracted**

**Purpose.** <!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026".

**Use.** Read it.

#### `skills/trading-and-investing/references/trading-strategies-and-styles.md`

`doc` · 308 lines · 27,398 B · description: **extracted**

**Purpose.** <!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/trading-strategies-and-styles.md by scripts/persist-spoke.mjs. --> 1. [Overview](#overview) 2. [Trading Styles by Time Horizon](#1-trading-styles-by-time-horizon)

**Use.** Read it.

#### `skills/trading-and-investing/references/volatility-and-pricing.md`

`doc` · 255 lines · 20,318 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/walk-forward-window-length-and-refit-cadence.md`

`doc` · 270 lines · 16,007 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

#### `skills/trading-and-investing/references/why-high-frequency-strategies-die-at-leverage.md`

`doc` · 183 lines · 8,709 B · description: **extracted**

**Purpose.** >-

**Use.** Read it.

---

## tools

3 files.

#### `tools/gate.sh`

`other` · 0 lines · 2,490 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `tools/install-hooks.sh`

`other` · 0 lines · 865 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `tools/land.sh`

`other` · 0 lines · 3,816 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.
