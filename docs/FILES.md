# Every file in this repository

**Generated** from `index/INDEX.json` at commit `582c730` (2026-11-08T07:09:26+00:00). 683 tracked files, 12.1 MB.

Regenerate with:

```bash
python3 index/build.py all          # refresh the index
python3 index/make_files_doc.py     # rewrite this file
python3 index/build.py --check      # fail if the index is stale
```

## How to read an entry

Every entry marks where its description came from, because a generated one-liner and a considered one should not look alike:

- **curated** (42 files) — hand-written purpose and usage, in the `CURATED` table of `index/make_files_doc.py`. Used where extraction cannot give a reader what they need: the engine, the research drivers, the order-placing path, and the files with no prose of their own.
- **extracted** (488 files) — the file's own module docstring, JSDoc header, or frontmatter `summary`. Trustworthy here because 232/243 Python modules and 56/81 JS files carry a substantial one. (These counts are computed at generation time, not hardcoded — an earlier revision asserted a frozen ratio and it was wrong within a day as the repo grew.)
- **derived** (101 files) — shape only, for generated artifacts: a CSV's header and row count, a JSON's keys. Prose for a result file would be invented.

*How to use* is curated where it matters and otherwise inferred from the file's kind — a test gets its runner, a CLI gets `--help`, a module gets its import path.

## Related documents

This file is the **exhaustive** one: every tracked file, no exceptions, regenerated from the index. For orientation rather than lookup, read these first — they are shorter and they explain *why* the pieces fit together:

- `docs/codebase-overview.md` — the narrative tour.
- `docs/ARCHITECTURE.md` — how the three components relate.
- `docs/COMPONENTS.md` — component-level responsibilities.
- `docs/CONCEPTS.md` — the conceptual index: which files bear on which idea.

To *search* rather than browse: `python3 index/search.py "your question"`.

## Contents

- [`(root)`](#root) — 18 files
- [`docs`](#docs) — 39 files
- [`index`](#index) — 7 files
- [`backtester`](#backtester) — 138 files
- [`research`](#research) — 140 files
- [`extension`](#extension) — 92 files
- [`soltui`](#soltui) — 88 files
- [`.github`](#github) — 9 files
- [`tradingskilllist`](#tradingskilllist) — 1 files
- [`.remember`](#remember) — 1 files
- [`.claude`](#claude) — 1 files
- [`.githooks`](#githooks) — 2 files
- [`.vscode`](#vscode) — 3 files
- [`liquidity`](#liquidity) — 57 files
- [`llms`](#llms) — 3 files
- [`mongo`](#mongo) — 17 files
- [`scripts`](#scripts) — 2 files
- [`skills`](#skills) — 62 files
- [`tools`](#tools) — 3 files

---

## (root)

Repository-level entry points and agent instructions. `AGENTS.md` and `CLAUDE.md` are the operative rules for anyone — human or agent — changing this repo; read them before the code.

18 files.

#### `.editorconfig`

`other` · 24 lines · 324 B · description: **curated**

**Purpose.** Baseline whitespace and encoding rules so diffs stay about content.

**Use.** Nothing to run; editors apply it automatically.

#### `.env.example`

`config` · 19 lines · 858 B · description: **none**

**Purpose.** _No description available._

**Use.** Configuration; nothing to run.

#### `.gitattributes`

`other` · 28 lines · 744 B · description: **curated**

**Purpose.** Per-path git behaviour: line-ending normalisation, and which files are treated as binary or excluded from diffs and archives. Keeps a CSV or a generated artifact from producing noise in review.

**Use.** Nothing to run; git applies it. `git check-attr -a <path>` to inspect.

#### `.gitignore`

`other` · 140 lines · 4,255 B · description: **curated**

**Purpose.** Keeps derived and machine-specific artifacts out of the tree — `data/` price caches, the semantic embedding array, build output. Anything regenerable and large belongs here.

**Use.** Add a pattern when you add a derived artifact; commit the manifest that describes it instead of the artifact.

#### `.nvmrc`

`other` · 2 lines · 3 B · description: **curated**

**Purpose.** Pins the Node version for the extension's test and tooling surfaces, so `node --test` behaves the same locally and in CI.

**Use.** `nvm use` in the repo root.

#### `AGENTS.md`

`doc` · 28 lines · 1,473 B · description: **curated**

**Purpose.** The operative rules for changing this repo. The backtester never gains live-trading capability, no lookahead, costs are never optional, the engine does not touch the network; the extension defaults to dry-run and its risk rails fail closed.

**Use.** Read first. It outranks any suggestion a tool or agent would otherwise make.

#### `CLAUDE.md`

`doc` · 181 lines · 12,406 B · description: **curated**

**Purpose.** Agent-facing companion to AGENTS.md — the same non-negotiables plus the workflow conventions (commit discipline, where numbers may come from, what must be regenerable).

**Use.** Read before making changes with an agent.

#### `CODE_OF_CONDUCT.md`

`doc` · 10 lines · 469 B · description: **extracted**

**Purpose.** Discuss the code and evidence respectfully. Explain a reproducible problem and its impact. Critique a proposal without attacking its author. Do not post harassment, private information, signing keys or other secrets in issues, pull requests or logs.

**Use.** Read it.

#### `CONTRIBUTING.md`

`doc` · 23 lines · 1,118 B · description: **extracted**

**Purpose.** Read `CLAUDE.md`, then `docs/DEVELOPMENT.md` and the owning component's README before editing. The extension and liquidity manager can move money; the backtester remains simulation-only. Liquidity also has its own `liquidity/CLAUDE.md`.

**Use.** Read it.

#### `GEMINI.md`

`doc` · 64 lines · 3,485 B · description: **extracted**

**Purpose.** Agent instructions for this repository live in [CLAUDE.md](CLAUDE.md). Read that file first — it is the single source of truth, and this file only points at it. Save requests in `prompts.md` and versioned continuation records in `memory.md`, as

**Use.** Read it.

#### `README.md`

`doc` · 133 lines · 8,123 B · description: **curated**

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

#### `memory.md`

`doc` · 535 lines · 78,588 B · description: **extracted**

**Purpose.** Version: 51 Delta: v50 to v51; adaptive strategy Forwardtest and roster shortcuts. Active: repo-bootstrapper and code-deep-optimizer; Stele TASK-723.

**Use.** Read it.

#### `pagesource`

`other` · 54 lines · 113,673 B · description: **curated**

**Purpose.** A captured page source kept as a fixture for the scraping/parsing work. Reference data, not code.

**Use.** Read it; nothing to run.

#### `prompts.md`

`doc` · 317 lines · 19,403 B · description: **extracted**

**Purpose.** Version: 44 Delta: v43 to v44; Lightweight Charts chosen; deep prompt optimizer, then rebuild /dso as one pass per evaluation method. Delta: added the leverage-tier and reliable-trigger request.

**Use.** Read it.

---

## docs

Curated prose. `ARCHITECTURE.md` explains how the pieces fit, `TESTING.md` is the coverage contract, `SECURITY.md` covers the order-placing surface, and this file indexes everything.

39 files.

#### `docs/API.md`

`doc` · 176 lines · 9,221 B · description: **extracted**

**Purpose.** Every action lives in one registry: `extension/src/core/commands.js`. Three surfaces adapt it. drift apart. cd extension

**Use.** Read it.

#### `docs/ARCHITECTURE.md`

`doc` · 161 lines · 10,309 B · description: **extracted**

**Purpose.** Six components with explicit execution boundaries. The backtester and research do not place orders. The extension and liquidity manager each have their own live-capable execution path. Soltui reads research and liquidity status; MongoDB is a derived copy, never an execution dependency.

**Use.** Read it.

#### `docs/BASE-WALLET-QUERIES.md`

`doc` · 68 lines · 3,997 B · description: **extracted**

**Purpose.** The owner's Base address is `0x901a89cEC0608eB5435A915f006b45bD46405314` (CLAUDE.md, "Live on-chain actions"). The Coinbase Developer Platform (CDP) MCP server reads it without any key in this repo: the server holds its own credentials (`cdp_env` reports `Active: live`). This page is the recipe agents

**Use.** Read it.

#### `docs/COMPONENTS.md`

`doc` · 252 lines · 12,180 B · description: **extracted**

**Purpose.** What each module is for, what it exposes, and what it depends on. `docs/codebase-overview.md` is the flat file map; this page is the shape of the thing. Dependency direction, strictly one-way:

**Use.** Read it.

#### `docs/COMPOUND-5M-PAPER.md`

`doc` · 562 lines · 52,788 B · description: **extracted**

**Purpose.** The compound scorecard asks one question: **will the next five-minute bar of a crypto perpetual close up or down?** It scores 28 metrics from -1 (down) to +1 (up), removes the double-counting between metrics that measure the same thing, reweights styles by market regime, and combines the scores into one call (UP, DOWN or FLAT) behind seven veto gates.

**Use.** Read it.

#### `docs/COMPOUND-5M.md`

`doc` · 465 lines · 32,999 B · description: **extracted**

**Purpose.** A tester for one question: **will the next 5-minute bar close up or down?** Every metric in (up). The scores are combined into one call (UP, DOWN or FLAT), which you can backtest and forward test, metric by metric and combined. Nothing here places an order.

**Use.** Read it.

#### `docs/CONCEPTS.md`

`doc` · 316 lines · 15,302 B · description: **extracted**

**Purpose.** python3 index/build.py all # refresh python3 index/make_concepts_doc.py # rewrite this file python3 index/search.py --concepts # list them

**Use.** Read it.

#### `docs/DEVELOPMENT.md`

`doc` · 187 lines · 8,864 B · description: **extracted**

**Purpose.** Setup, the commands you will actually use, and the environment each component needs. Backtester and research use NumPy and pandas; mongo uses pymongo; soltui uses Textual and optional macOS packaging dependencies. Liquidity has a separate web3/httpx stack.

**Use.** Read it.

#### `docs/FILES.md`

`doc` · 6531 lines · 325,951 B · description: **extracted**

**Purpose.** Regenerate with: python3 index/build.py all # refresh the index python3 index/make_files_doc.py # rewrite this file

**Use.** Read it.

#### `docs/INSTALLATION.md`

`doc` · 183 lines · 7,638 B · description: **extracted**

**Purpose.** Six components with separate dependencies. The optional soltui app and liquidity daemon can each install a persistent macOS launchd service. Test commands below do not install them. verified against that runtime. Liquidity declares its own Python range in `pyproject.toml`.

**Use.** Read it.

#### `docs/MCP.md`

`doc` · 25 lines · 1,134 B · description: **extracted**

**Purpose.** This repository does not ship an MCP server, register MCP tools, or require a repository registry in `extension/src/core/commands.js`. They are not MCP transports. Development agents may have machine-wide MCP connections such as Stele and the global

**Use.** Read it.

#### `docs/OPERATIONS.md`

`doc` · 122 lines · 4,883 B · description: **extracted**

**Purpose.** cd extension && node tools/cli.js kill cannot resume trading. In the extension, the popup's red KILL SWITCH button does the same thing. node tools/cli.js data --json # find venueOrderId values

**Use.** Read it.

#### `docs/SCRIPTS.md`

`doc` · 978 lines · 49,252 B · description: **extracted**

**Purpose.** Every runnable entry point in this repo: what it is for, when to reach for it, **when not to**, its options, a real invocation, and the output you should expect. list. This page is the operator's manual — the commands you actually type.

**Use.** Read it.

#### `docs/SECURITY.md`

`doc` · 104 lines · 6,084 B · description: **extracted**

**Purpose.** This repository contains software that can move real money. Two assets matter: **signing keys** and the **Jupiter API key**. For the extension, `full-auto` is the only mode that uses its local signing key. Rules, all enforced in

**Use.** Read it.

#### `docs/TESTING.md`

`doc` · 216 lines · 16,924 B · description: **extracted**

**Purpose.** python3 -m unittest discover -s backtester/tests -t . # 853 tests python3 -m unittest discover -s soltui/tests -t . # 817 tests (~610s) python3 -m unittest discover -s mongo/tests -t . # 33 tests

**Use.** Read it.

#### `docs/TRADINGVIEW-REFERENCE.md`

`doc` · 3648 lines · 424,800 B · description: **extracted**

**Purpose.** Version: 1.0.0 (2026-11-07). Delta: first distillation of the `tradingview/` docs bundle. This page distills the TradingView Advanced Charts (Charting Library) and Trading Platform documentation, its TypeScript definitions, and the agentskills.io Agent Skills format into one reference for this repository.

**Use.** Read it.

#### `docs/caching-and-optimization.md`

`doc` · 36 lines · 2,580 B · description: **extracted**

**Purpose.** Preserve the economic and evidence contract before reducing runtime. A per-bar strategy replay cannot be replaced by one last-bar invocation: stateful strategies can return a different answer. The ladder simulator and extension must retain matching lot economics.

**Use.** Read it.

#### `docs/code-deep-optimizer-2026-11-06.md`

`doc` · 904 lines · 37,962 B · description: **extracted**

**Purpose.** Version: 1.1.0. Delta: record CI fixture correction after real-server validation. Target: solmargintrader, base `eebadbb`; integration preserves newer upstream work. This run audits 17 primary risk-first files across six components and their necessary

**Use.** Read it.

#### `docs/code-optimizer-scope-2026-11-06.json`

`doc` · 329 lines · 11,977 B · description: **derived**

**Purpose.** Generated JSON object, 7 keys (selected, remainder, triage_candidates, reason, primary, dependencies...).

**Use.** Read it.

#### `docs/codebase-overview.md`

`doc` · 301 lines · 19,899 B · description: **extracted**

**Purpose.** A file map for orientation, grouped by directory. Every path here is checked by Six components, in ascending order of how much damage a bug can do: Read `CLAUDE.md` before changing any of them; it carries the non-negotiables per

**Use.** Read it.

#### `docs/external-calls.md`

`doc` · 125 lines · 13,981 B · description: **extracted**

**Purpose.** Inventory reviewed against source on 2026-11-06. A call includes public HTTP/RPC, MongoDB, browser/OS services, and child processes. The tables name the transport boundary and the logical callers that share it; they do not count each RPC inside a

**Use.** Read it.

#### `docs/high_signal_file_index.json`

`doc` · 1256 lines · 37,089 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys ($comment, repo, components, files).

**Use.** Read it.

#### `docs/integrations-and-assumptions.md`

`doc` · 113 lines · 6,835 B · description: **extracted**

**Purpose.** External services this repo depends on, and the assumptions baked into the code that would be wrong somewhere else. The second list is the one that bites. Full per-call detail — timeouts, retries, what is logged — is in `docs/external-calls.md`.

**Use.** Read it.

#### `docs/jupiter-trigger-contract.md`

`doc` · 62 lines · 3,745 B · description: **extracted**

**Purpose.** Version: 1.0.0. Delta: record the source contract checked during the 2026-11-06 audit. This review checked public documentation and offline response fixtures. It did not place, cancel or sign a live order. The extension still installs disarmed in dry-run mode.

**Use.** Read it.

#### `docs/known-issues.md`

`doc` · 154 lines · 6,940 B · description: **extracted**

**Purpose.** Active limitations, in descending order of how much damage they could do. Nothing here is speculative — each item is either stated in the code or was reproduced. Source markers are not an exhaustive issue list. The dated bootstrap and optimizer

**Use.** Read it.

#### `docs/logging.md`

`doc` · 86 lines · 4,794 B · description: **extracted**

**Purpose.** What each component records, where it goes, and — the part worth reading — which paths currently record nothing. The extension's real log is **not the console**. `src/storage/store.js` defines four

**Use.** Read it.

#### `docs/onboarding.md`

`doc` · 145 lines · 5,985 B · description: **extracted**

**Purpose.** An offline verification path, followed by optional component setup. Identify the two components that can move money before running any live command. Six components with different failure modes:

**Use.** Read it.

#### `docs/profitable-crypto-strategies-analysis.md`

`doc` · 245 lines · 18,589 B · description: **extracted**

**Purpose.** The vast majority of headline yields in decentralized finance are economic illusions. In competitive, permissionless financial markets, sustained positive expected value ($+\text{EV}$) cannot exist without an economic counterparty taking an equal and opposite negative expected value ($-\text{EV}$) position, or an entity paying non-dilutive economic rent for a verifiable service (liquidity, credit,

**Use.** Read it.

#### `docs/repo-bootstrap-audit-2026-11-06.md`

`doc` · 160 lines · 13,249 B · description: **extracted**

**Purpose.** Version: 1.1.0. Delta: integrated code safety references and verified metadata choices. Scope: six-component repository at base `eebadbb`, isolated branch session-key worktree remain outside this change. No previous bootstrap audit ledger

**Use.** Read it.

#### `docs/requirements.md`

`doc` · 36 lines · 2,604 B · description: **extracted**

**Purpose.** These requirements describe existing code boundaries, not future product promises. interpreter range and locked dependencies live in `liquidity/pyproject.toml` and `uv.lock`. remains ESM with zero runtime/development dependencies and no build step.

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

### `docs/runbooks/`

#### `docs/runbooks/handoff.md`

`doc` · 34 lines · 1,310 B · description: **extracted**

**Purpose.** Know the canonical checkout, active branch/worktree, task and target behavior. Existing prompt and memory records are evidence; verify them against current source and Git. git status --short

**Use.** Read it.

#### `docs/runbooks/incident.md`

`doc` · 46 lines · 1,658 B · description: **extracted**

**Purpose.** Identify the execution component before acting. Record observed intent/order ids or transaction hashes without copying keys, passphrases or API headers. Keep local journals and the liquidity ledger; deleting evidence makes reconciliation harder.

**Use.** Read it.

#### `docs/runbooks/rollback.md`

`doc` · 34 lines · 1,249 B · description: **extracted**

**Purpose.** Identify the offending commit and the component it changes. Preserve unrelated dirty work. If the behavior can move funds, use `docs/runbooks/incident.md` first and record venue/chain state. Rolling back source cannot reverse a mined transaction or venue order.

**Use.** Read it.

---

## index

The search layer over the repo itself. Generators plus three committed indexes; the embedding array is gitignored and rebuilt on demand.

7 files.

#### `index/README.md`

`doc` · 167 lines · 9,855 B · description: **extracted**

**Purpose.** A searchable index over every tracked file in this repo: what exists, which files contain a word, which files mean something like a question, and which bear on an idea. Built to answer "where is the thing that does X" without reading every file.

**Use.** Read it.

#### `index/build.py`

`code-python` · 889 lines · 37,930 B · description: **curated**

**Purpose.** Builds the four indexes over every tracked file: metadata, BM25 text, concepts, and the opt-in semantic embeddings. `--check` re-hashes the tree so a stale index fails loudly.

**Contents.** Defines `REPO`, `OUT`, `SCHEMA_VERSION`, `INDEX_JSON`, `TEXT_JSON`, `CONCEPT_JSON`, `SEMANTIC_NPZ`, `SEMANTIC_MANIFEST`, `LOCAL_NPZ`, `LOCAL_MANIFEST` and 30 more.

**Use.** `python3 index/build.py all`, then `semantic` for embeddings, and `--check` before trusting it.

#### `index/idle.py`

`code-python` · 306 lines · 12,385 B · description: **extracted**

**Purpose.** Idle index check: rebuild the semantic index in the background when it is out of date. python3 index/idle.py --status # fresh / stale / missing, and why python3 index/idle.py --once # check; start a background rebuild if warranted python3 index/idle.py --force # rebuild now, ignoring load and throttle (foreground) python3 index/idle.py --install-schedule # hourly launchd agent (macOS): runs --once

**Contents.** Defines `HERE`, `OUT`, `STATE_FILE`, `LOCK_FILE`, `LOG_FILE`, `MIN_INTERVAL`, `DEFAULT_THRESHOLD`, `FORCE_INTERVAL`, `LABEL`, `DEFAULT_PYTHON` and 17 more.

**Use.** `python3 index/idle.py --help`

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

#### `index/ollama_ensure.py`

`code-python` · 166 lines · 7,192 B · description: **extracted**

**Purpose.** Make sure a LOCAL ollama server is reachable, starting it if it is not. python3 index/ollama_ensure.py # check, start if needed, report the model python3 index/ollama_ensure.py --pull # also pull the embedding model if absent Used by `search.py` (semantic and hybrid), `build.py semantic` and `idle.py`, so the three share one definition of "ollama is ready". Standard library only.

**Contents.** Defines `EMBED_MODEL`, `OLLAMA_BASE`, `LOCAL_HOSTS`, `MAC_APP`, `class Status`, `base_of()`, `is_local()`, `_get_json()`, `installed_models()`, `reachable()` and 5 more.

**Use.** `python3 index/ollama_ensure.py --help`

#### `index/search.py`

`code-python` · 427 lines · 17,814 B · description: **curated**

**Purpose.** Query the index three ways — exact (BM25), meaning (cosine over embeddings), or concept — with rank fusion as the default because a reader rarely knows which kind of query they are typing.

**Contents.** Defines `REPO`, `OUT`, `INDEX_JSON`, `TEXT_JSON`, `CONCEPT_JSON`, `SEMANTIC_NPZ`, `SEMANTIC_MANIFEST`, `LOCAL_NPZ`, `LOCAL_MANIFEST`, `QUERY_KEEP_ALIVE` and 19 more.

**Use.** `python3 index/search.py "how are costs applied"`, `--concepts`, `--concept <id>`, `--file <path>`, `--kind code-python`.

---

## backtester

The simulation engine and everything that supports it. Never gains live-trading capability, never touches the network, and costs are never optional. `core/` is the engine; `strategy_cards/` are the specs; `tests/` is the acceptance suite.

138 files.

#### `backtester/PROMPT.md`

`doc` · 200 lines · 20,191 B · description: **extracted**

**Purpose.** <role> You are a quantitative developer building research infrastructure. You have production experience with event-driven backtesting engines and you know the standard ways backtests lie: look-ahead bias, survivorship bias, unrealistic fills, and selection bias from comparing many strategies and reporting the winner. </role>

**Use.** Read it.

#### `backtester/README.md`

`doc` · 472 lines · 23,601 B · description: **extracted**

**Purpose.** An offline, event-driven backtesting harness for crypto trading strategies, built around SOL. Supports unlevered **spot** and **Jupiter-Perps-style leveraged perpetuals** with a correctly-modelled borrow fee.

**Use.** Read it.

#### `backtester/__init__.py`

`code-python` · 4 lines · 69 B · description: **extracted**

**Purpose.** SOL-focused crypto strategy backtester.

**Use.** `import backtester.__init__`

#### `backtester/cli.py`

`code-python` · 325 lines · 11,463 B · description: **extracted**

**Purpose.** Command-line entry point. python -m backtester.cli --asset SOL --strategy all --out results/ Running with no arguments prints usage rather than starting a long fetch.

**Contents.** Defines `build_parser()`, `_trimmed_metrics()`, `_run_one()`, `main()`.

**Use.** `python3 backtester/cli.py --help`

#### `backtester/gridcli.py`

`code-python` · 308 lines · 12,295 B · description: **extracted**

**Purpose.** Ladder-grid backtest entry point. python -m backtester.gridcli --lower 60 --upper 90 --rungs 7 --notional-per-rung 12 --synthetic 400 Separate from `backtester.cli` on purpose. That CLI runs `Strategy` objects — one target exposure per bar — and this one runs the resting-ladder simulator, whose config surface (lower/upper/rungs/notional) and execution model are different.

**Contents.** Defines `DISCLAIMER`, `_json_safe()`, `build_parser()`, `main()`.

**Use.** `python3 backtester/gridcli.py --help`

#### `backtester/paircli.py`

`code-python` · 238 lines · 9,682 B · description: **extracted**

**Purpose.** Peer-relative-value backtest entry point. python -m backtester.paircli --asset SOL --peer BTC --interval 1d --split 0.7 Separate from `backtester.cli` because this strategy needs **two** price series, and the strategy registry builds from zero arguments.

**Contents.** Defines `DISCLAIMER`, `_json_safe()`, `build_parser()`, `main()`.

**Use.** `python3 backtester/paircli.py --help`

#### `backtester/requirements.txt`

`data` · 14 lines · 507 B · description: **curated**

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

#### `backtester/core/compound.py`

`code-python` · 463 lines · 22,088 B · description: **extracted**

**Purpose.** Backtest a scorecard configuration on 5m bars: direction accuracy and net P&L, IS vs OOS. from backtester.core.compound import run_compound, load_bars_5m report = run_compound("SOL", config) Two different questions, answered separately because they disagree at 5m: * **Does the call predict the next bar?** `forecast_stats` scores every bar's call against sign(close[t+1] - close[t]).

**Contents.** Defines `BARS_PER_YEAR`, `MIN_SEGMENT_BARS`, `MIN_OOS_CALLS`, `MIN_OOS_TRADES`, `class CompoundDataError`, `_read()`, `resample_complete()`, `candidate_files()`, `load_bars_5m()`, `available_assets()` and 17 more.

**Use.** `import backtester.core.compound`

#### `backtester/core/cpcv.py`

`code-python` · 334 lines · 13,051 B · description: **curated**

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

`code-python` · 750 lines · 29,365 B · description: **curated**

**Purpose.** The event loop: maps a strategy's target exposure to fills, applies costs exactly once, and marks the book every bar. `fill_delay=1` is what keeps a signal at bar t from being filled at bar t.

**Contents.** Defines `class Strategy`, `class EngineConfig`, `class BacktestResult`, `class _Book`, `_resolve_target()`, `run_backtest()`, `_liquidate()`, `_walk_fine_bar()`, `_apply_target()`.

**Use.** `from backtester.core.engine import run_backtest, EngineConfig`. Every reported figure in this repo comes through here.

#### `backtester/core/fetch.py`

`code-python` · 222 lines · 7,788 B · description: **extracted**

**Purpose.** Explicit historical data fetch from the Coinbase Exchange public API. Never called implicitly by a backtest. Run it once to populate the local CSV cache, then every run and every test reads from disk. Two hazards this module exists to handle: 1. Coinbase returns rows as [time, low, high, open, close, volume] -- NOT in OHLCV order.

**Contents.** Defines `COINBASE_BASE`, `MAX_CANDLES_PER_REQUEST`, `COINBASE_ROW`, `SUPPORTED_GRANULARITIES`, `class FetchError`, `_get_json()`, `fetch_coinbase()`, `default_cache_path()`, `main()`.

**Use.** `python3 backtester/core/fetch.py --help`

#### `backtester/core/fetch_minutes.py`

`code-python` · 746 lines · 33,650 B · description: **extracted**

**Purpose.** Resumable, parallel 1-minute candle fetch with an honest coverage manifest. python3 -m backtester.core.fetch_minutes --asset BTC --years 5 python3 -m backtester.core.fetch_minutes --all --years 5 --workers 6 ## Why this is not `fetch.py` `fetch_coinbase` chains a cursor: each request's window start comes from the previous response's oldest bar.

**Contents.** Defines `MINUTE`, `WINDOW_SECONDS`, `REQUEST_TIMEOUT`, `REQUEST_RETRIES`, `RATE_LIMIT_PER_SECOND`, `EMPTY_RUN_TO_BELIEVE`, `MINUTE_ASSETS`, `DATA`, `MANIFEST`, `class RateLimiter` and 24 more.

**Use.** `python3 backtester/core/fetch_minutes.py --help`

#### `backtester/core/fetch_minutes_alt.py`

`code-python` · 328 lines · 14,679 B · description: **extracted**

**Purpose.** 1-minute candles for coins Coinbase does not list, from the venue that does. python3 -m backtester.core.fetch_minutes_alt --plan python3 -m backtester.core.fetch_minutes_alt --assets TRX,XMR,LEO --years 7 Like `fetch.py` and `fetch_minutes.py`, this is an explicit network step that writes the local cache; no backtest calls it.

**Contents.** Defines `USER_AGENT`, `EMPTY_PAGES_TO_STOP`, `SANITY_FAIL_LIMIT`, `class AltFetchError`, `class Venue`, `_okx_rows()`, `_kucoin_rows()`, `_bitget_rows()`, `_whitebit_rows()`, `http_json()` and 7 more.

**Use.** `python3 backtester/core/fetch_minutes_alt.py --help`

#### `backtester/core/funding.py`

`code-python` · 492 lines · 19,640 B · description: **extracted**

**Purpose.** Explicit historical **funding-rate** fetch, for the carry question `perps.py` cannot answer. python3 -m backtester.core.funding --plan-only python3 -m backtester.core.funding --assets BTC,ETH,SOL,DOGE,ZEC python3 -m backtester.core.funding --assets BTC --cross-check-okx Never called implicitly by a backtest.

**Contents.** Defines `HYPERLIQUID_URL`, `OKX_FUNDING_URL`, `MAX_ROWS_PER_REQUEST`, `FUNDING_INTERVAL_SECONDS`, `FUNDING_COLUMNS`, `REQUEST_SPACING_SECONDS`, `MAX_PLAUSIBLE_HOURLY_RATE`, `class FundingFetchError`, `class FundingOutcome`, `_post_json()` and 9 more.

**Use.** `python3 backtester/core/funding.py --help`

#### `backtester/core/gridsim.py`

`code-python` · 882 lines · 36,622 B · description: **extracted**

**Purpose.** Resting-ladder grid simulator — the strategy the extension actually trades. This is deliberately NOT a `Strategy` in the `core.engine` sense. That protocol maps history to one target exposure filled at a bar boundary, and a grid's entire edge comes from **resting limit orders that fill intrabar at known prices**.

**Contents.** Defines `SPACING_GEOM`, `SPACING_ARITH`, `SPACINGS`, `SIDE_BUY`, `SIDE_SELL`, `VENUE_MIN_ORDER_USD`, `MAX_GRID_RUNGS`, `_validate_rung_count()`, `class GridConfig`, `grid_levels()` and 14 more.

**Use.** `import backtester.core.gridsim`

#### `backtester/core/indicators.py`

`code-python` · 480 lines · 19,134 B · description: **extracted**

**Purpose.** Trailing-window indicator functions. Every function here takes an array that the caller has ALREADY truncated to bars <= now (a `BarWindow` accessor does this by construction) and returns the value for the latest bar. None of them can see the future, because none of them are ever handed it. Two conventions worth knowing: * Each returns a scalar for the current bar, not a series.

**Contents.** Defines `EMA_CAP_MULTIPLE`, `EMA_WARMUP_MULTIPLE`, `sma()`, `ema()`, `ema_series()`, `wilder_smooth()`, `rsi()`, `macd()`, `ppo()`, `fib_level()` and 16 more.

**Use.** `import backtester.core.indicators`

#### `backtester/core/leverage.py`

`code-python` · 89 lines · 3,575 B · description: **extracted**

**Purpose.** Low / medium / high margin tiers: run any long/flat strategy as a perp position. A tier is only a leverage multiple plus the venue's cost model. The wrapped strategy decides WHEN to hold exposure; the engine decides what holding it costs at leverage L: open/close fees, slippage, the hourly borrow fee on notional, maintenance margin, and liquidation with an adverse fill and forfeited collateral.

**Contents.** Defines `DEFAULT_LIQUIDATION_PENALTY_BPS`, `class LeverageTier`, `tier_costs()`, `tier_config()`, `resolve_tiers()`, `liquidation_distance()`, `describe()`.

**Use.** `import backtester.core.leverage`

#### `backtester/core/metrics.py`

`code-python` · 275 lines · 9,942 B · description: **extracted**

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

`code-python` · 369 lines · 13,519 B · description: **extracted**

**Purpose.** Comparison reporting, with the caveats the numbers require. A sorted Sharpe table is the most misleading artifact a backtester can emit. Everything here exists to stop that: buy-and-hold is always shown as the baseline, in-sample and out-of-sample are separate columns, and the count of configurations evaluated is printed so a reader can weigh the selection bias.

**Contents.** Defines `NOT_ADVICE`, `MULTIPLE_TESTING_NOTE`, `TABLE_COLUMNS`, `PERCENT_COLUMNS`, `class SplitResult`, `library_versions()`, `results_frame()`, `_fmt_cell()`, `render_table()`, `render_report()` and 1 more.

**Use.** `import backtester.core.report`

#### `backtester/core/scorecard.py`

`code-python` · 1997 lines · 99,922 B · description: **extracted**

**Purpose.** Compound five-minute scorecard: score each metric, aggregate into an UP / DOWN / FLAT call. from backtester.core.scorecard import default_config, evaluate, explain, Bars Every component maps visible history to a score in [-1, 1] (+1 = the metric says the next bar closes higher, -1 = lower, 0 = no opinion, NaN = undefined here). Gates map history to "blocked" (no trade, whatever the score says).

**Contents.** Defines `BAR_SECONDS`, `STYLES`, `REGIMES`, `class ScorecardError`, `class Bars`, `contiguous_segments()`, `_s()`, `ema()`, `sma()`, `rstd()` and 30 more.

**Use.** `import backtester.core.scorecard`

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

#### `backtester/core/trigger_conditions.py`

`code-python` · 107 lines · 5,692 B · description: **extracted**

**Purpose.** Causal trading conditions shared by the trigger miner and `trigger_trade`. Every value at index t is computed from bars 0..t only (trailing windows, EMAs). `research/triggers.py` mines conjunctions of these; `core/strategies/trigger.py` trades them. One implementation keeps the mined edge and the traded edge the same measurement. No I/O here.

**Contents.** Defines `GROUPS`, `FUNDING_CONDITIONS`, `BASE_CONDITIONS`, `_ema()`, `compute_conditions()`.

**Use.** `import backtester.core.trigger_conditions`

#### `backtester/core/types.py`

`code-python` · 453 lines · 17,321 B · description: **extracted**

**Purpose.** Core value types for the backtester, including the look-ahead guard.

**Contents.** Defines `BAR_COLUMNS`, `HOURS_PER_YEAR`, `periods_per_year()`, `hours_per_bar()`, `validate_bar_arrays()`, `class Mode`, `class Side`, `class LookAheadError`, `class Bar`, `class BarWindow` and 5 more.

**Use.** `import backtester.core.types`

#### `backtester/core/universe.py`

`code-python` · 320 lines · 13,370 B · description: **extracted**

**Purpose.** Fetch a multi-asset universe into the local CSV cache. `fetch.py` fetches one product. This fetches a named set of them and, more importantly, is honest about the set it could not fetch.

**Contents.** Defines `COINBASE_PRODUCTS_URL`, `TOP10_NON_PEGGED`, `ALREADY_CACHED`, `TRADEABLE_UNIVERSE`, `COMPOUND_5M_UNIVERSE`, `class FetchPlan`, `product_id()`, `plan_universe_fetch()`, `list_coinbase_products()`, `fetch_universe()` and 1 more.

**Use.** `python3 backtester/core/universe.py --help`

### `backtester/core/strategies/`

#### `backtester/core/strategies/__init__.py`

`code-python` · 181 lines · 5,827 B · description: **curated**

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

#### `backtester/core/strategies/textbook.py`

`code-python` · 239 lines · 10,218 B · description: **extracted**

**Purpose.** Five textbook mechanisms that the cited trading guides name and the registry lacked. Source: `tradingstrategyresults.json` (a catalogue of strategies and indicators from public trading guides).

**Contents.** Defines `class DollarCostAveraging`, `class EmaCrossover`, `class PpoCross`, `class FibRetracement`, `class SwingConfluence`.

**Use.** `import backtester.core.strategies.textbook`

#### `backtester/core/strategies/tiers.py`

`code-python` · 68 lines · 2,417 B · description: **extracted**

**Purpose.** Leverage-tier strategies: an existing strategy held as a perp position. The signal is the base strategy's, unchanged and long/flat. The tier supplies the leverage the HARNESS must run it at (`engine_leverage`, see `core/leverage.py::tier_config`).

**Contents.** Defines `class _LeverageTier`, `class LevLow`, `class LevMedium`, `class LevHigh`.

**Use.** `import backtester.core.strategies.tiers`

#### `backtester/core/strategies/trigger.py`

`code-python` · 85 lines · 4,023 B · description: **extracted**

**Purpose.** Trigger trading: wait for a mined trigger, enter next open, exit when the context expires. The conditions come from `core/trigger_conditions.py`, the same causal code the miner (`research/triggers.py`) scores, so what is traded is what was measured: * the trigger is evaluated at the CLOSE of bar t from bars <= t; * the target is returned then, so the engine fills it at the OPEN of bar t+1; * the p

**Contents.** Defines `WINDOW`, `class TriggerTrade`.

**Use.** `import backtester.core.strategies.trigger`

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

#### `backtester/strategy_cards/day_trading.md`

`strategy-card` · 61 lines · 2,492 B · description: **extracted**

**Purpose.** A holding-period rule, not a signal: open and close within one UTC day. Spec-only until a session-flat wrapper exists.

**Contents.** Frontmatter: `status`=spec-only, `family`=intraday, `evaluation`=None, `success_likelihood`=very-low, `data_available`=true, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/dca.md`

`strategy-card` · 73 lines · 3,947 B · description: **extracted**

**Purpose.** Deploy a fixed budget in equal instalments at a fixed bar interval; exposure ramps to 1.0. The guides' DCA, expressed as an exposure target.

**Contents.** Frontmatter: `status`=implemented, `family`=baseline, `success_likelihood`=very-low, `data_available`=true, `registry_key`=dca.

**Use.** Read the card, then build it: `build('dca', **params)`. Status: implemented.

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

#### `backtester/strategy_cards/ema_crossover.md`

`strategy-card` · 73 lines · 3,314 B · description: **extracted**

**Purpose.** Long while the fast EMA is above the slow EMA. At 50/200 this is the golden cross the guides describe.

**Contents.** Frontmatter: `status`=implemented, `family`=trend, `success_likelihood`=very-low, `data_available`=true, `registry_key`=ema_crossover.

**Use.** Read the card, then build it: `build('ema_crossover', **params)`. Status: implemented.

#### `backtester/strategy_cards/event_driven.md`

`strategy-card` · 62 lines · 2,298 B · description: **extracted**

**Purpose.** Trade around scheduled or news events (listings, unlocks, forks, macro prints). Spec-only: needs a dated event feed.

**Contents.** Frontmatter: `status`=spec-only, `family`=event, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/exchange_net_flow.md`

`strategy-card` · 56 lines · 1,889 B · description: **extracted**

**Purpose.** Stablecoins moving onto exchanges as a proxy for incoming buying power.

**Contents.** Frontmatter: `status`=spec-only, `family`=crypto-native, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/fib_retracement.md`

`strategy-card` · 77 lines · 4,227 B · description: **extracted**

**Purpose.** Buy a pullback into the 0.382-0.786 retracement zone of an up-swing once price turns up; exit on the swing high or a break of the zone.

**Contents.** Frontmatter: `status`=implemented, `family`=mean-reversion, `success_likelihood`=very-low, `data_available`=true, `registry_key`=fib_retracement.

**Use.** Read the card, then build it: `build('fib_retracement', **params)`. Status: implemented.

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

`strategy-card` · 228 lines · 11,962 B · description: **extracted**

**Purpose.** A ladder of resting limit orders with paired exits one rung above each lot. The strategy the extension trades.

**Contents.** Frontmatter: `status`=measured, `family`=mean-reversion, `evaluation`=real-sol-daily-and-hourly-recentred-blocks, `success_likelihood`=low, `data_available`=true, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: measured.

#### `backtester/strategy_cards/lev_high.md`

`strategy-card` · 77 lines · 3,644 B · description: **extracted**

**Purpose.** Runs any registered long/flat strategy as a Jupiter-Perps position at 20x by default, with borrow fees, open/close fees, slippage, maintenance margin and intrabar liquidation.

**Contents.** Frontmatter: `status`=implemented, `family`=leverage-tier, `success_likelihood`=very-low, `data_available`=true, `registry_key`=lev_high.

**Use.** Read the card, then build it: `build('lev_high', **params)`. Status: implemented.

#### `backtester/strategy_cards/lev_low.md`

`strategy-card` · 77 lines · 3,637 B · description: **extracted**

**Purpose.** Runs any registered long/flat strategy as a Jupiter-Perps position at 2x by default, with borrow fees, open/close fees, slippage, maintenance margin and intrabar liquidation.

**Contents.** Frontmatter: `status`=implemented, `family`=leverage-tier, `success_likelihood`=very-low, `data_available`=true, `registry_key`=lev_low.

**Use.** Read the card, then build it: `build('lev_low', **params)`. Status: implemented.

#### `backtester/strategy_cards/lev_medium.md`

`strategy-card` · 77 lines · 3,649 B · description: **extracted**

**Purpose.** Runs any registered long/flat strategy as a Jupiter-Perps position at 5x by default, with borrow fees, open/close fees, slippage, maintenance margin and intrabar liquidation.

**Contents.** Frontmatter: `status`=implemented, `family`=leverage-tier, `success_likelihood`=very-low, `data_available`=true, `registry_key`=lev_medium.

**Use.** Read the card, then build it: `build('lev_medium', **params)`. Status: implemented.

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

#### `backtester/strategy_cards/ppo.md`

`strategy-card` · 74 lines · 3,599 B · description: **extracted**

**Purpose.** Long while the PPO line is above its signal line. MACD divided by the slow EMA, so readings are comparable across price levels.

**Contents.** Frontmatter: `status`=implemented, `family`=trend, `success_likelihood`=very-low, `data_available`=true, `registry_key`=ppo.

**Use.** Read the card, then build it: `build('ppo', **params)`. Status: implemented.

#### `backtester/strategy_cards/prediction_markets.md`

`strategy-card` · 71 lines · 4,814 B · description: **extracted**

**Purpose.** Two distinct ideas to consider: read prediction-market odds as a forward-looking signal for crypto, or trade the markets themselves (cross-venue mispricing, calibration bias). Spec-only: needs a price and resolution history the repo does not have.

**Contents.** Frontmatter: `status`=spec-only, `family`=event, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/rsi.md`

`strategy-card` · 107 lines · 4,272 B · description: **extracted**

**Purpose.** Buy when Wilder's RSI is oversold, exit when it recovers past a midline. Stateful hold between.

**Contents.** Frontmatter: `status`=measured, `family`=oscillator-reversion, `evaluation`=single-split-70-30, `success_likelihood`=very-low, `data_available`=true, `registry_key`=rsi.

**Use.** Read the card, then build it: `build('rsi', **params)`. Status: measured.

#### `backtester/strategy_cards/scalping.md`

`strategy-card` · 61 lines · 2,290 B · description: **extracted**

**Purpose.** Many very small gains from tiny price moves on a tick or order-book edge. Spec-only: needs tick and book data the repo does not have.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

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

#### `backtester/strategy_cards/swing_confluence.md`

`strategy-card` · 77 lines · 4,416 B · description: **extracted**

**Purpose.** Enter a breakout above the prior N-bar high when at least two of SMA, MACD, RSI and OBV agree; exit below the prior M-bar low.

**Contents.** Frontmatter: `status`=implemented, `family`=breakout, `success_likelihood`=very-low, `data_available`=true, `registry_key`=swing_confluence.

**Use.** Read the card, then build it: `build('swing_confluence', **params)`. Status: implemented.

#### `backtester/strategy_cards/trade_flow_imbalance.md`

`strategy-card` · 57 lines · 2,017 B · description: **extracted**

**Purpose.** Signed trade prints. Naive flow-following is systematically picked off.

**Contents.** Frontmatter: `status`=spec-only, `family`=microstructure, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/triangular_arbitrage.md`

`strategy-card` · 288 lines · 16,003 B · description: **extracted**

**Purpose.** Three-leg spot cycle with executable bid/ask rates. Event-replay design only; independent cross-pair books and a dedicated runner are missing.

**Contents.** Frontmatter: `status`=spec-only, `family`=arbitrage, `evaluation`=None, `success_likelihood`=very-low, `data_available`=false, `registry_key`=null.

**Use.** Specification only — read it; there is no runner. Status: spec-only.

#### `backtester/strategy_cards/trigger_trade.md`

`strategy-card` · 74 lines · 3,161 B · description: **extracted**

**Purpose.** Waits for a conjunction of causal conditions, enters at the next bar open in the predicted direction, exits when the horizon expires or a MAE-derived stop is hit.

**Contents.** Frontmatter: `status`=implemented, `family`=trigger, `success_likelihood`=very-low, `data_available`=true, `registry_key`=trigger_trade.

**Use.** Read the card, then build it: `build('trigger_trade', **params)`. Status: implemented.

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

#### `backtester/tests/test_compound_backtest.py`

`test` · 206 lines · 11,099 B · description: **extracted**

**Purpose.** Compound backtest runner: data loading, gap handling, engine wiring, IS/OOS honesty.

**Contents.** Defines `frame()`, `class DataTests`, `class EngineWiringTests`, `class HyperliquidMarginTests`, `class RunTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_compound_backtest.py -q`

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

`test` · 923 lines · 41,176 B · description: **extracted**

**Purpose.** Tests for the per-bar rule readout in `research/decide.py`. The readout's one substantive claim is that its target exposures are the same numbers the engine would have acted on. Three tests defend it: * **Engine parity.** A recording wrapper captures every `on_bar` return the engine asks for, and the replay must reproduce that sequence exactly, for every registered strategy.

**Contents.** Defines `REPO`, `ZERO_COST`, `SYNTHETIC_BARS`, `synthetic_arrays()`, `truncate()`, `make_arrays()`, `class Recorder`, `class TestEngineParity`, `class TestNoLeak`, `class TestPathDependence` and 6 more. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_decide.py -q`

#### `backtester/tests/test_decide_audit.py`

`test` · 76 lines · 4,205 B · description: **extracted**

**Purpose.** Readout trust boundaries over synthetic arrays; no cache/network dependency.

**Contents.** Defines `class ReadoutAuditTests`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_decide_audit.py -q`

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

#### `backtester/tests/test_engine_audit.py`

`test` · 226 lines · 13,093 B · description: **extracted**

**Purpose.** Offline counterexamples for money, timing and history-boundary invariants.

**Contents.** Defines `zero_cost()`, `bars()`, `class Always`, `class EngineAudit`, `class GridAudit`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_engine_audit.py -q`

#### `backtester/tests/test_fetch_minutes.py`

`test` · 387 lines · 17,630 B · description: **extracted**

**Purpose.** Tests for the resumable 1-minute fetch. Each class here guards a bug that was live on disk, not a hypothetical one. The fetch is a multi-hour job against a rate-limited venue, so its failure modes are all of the same shape: something is recorded as done that was not done, and no count reveals it.

**Contents.** Defines `REPO`, `class PlanWindowsTests`, `class SidecarTests`, `class EffectiveWindowsTests`, `class FirstAvailableTests`, `class CoverageTests`, `class CoverageDoesNotDriftTests`, `class CacheTests`, `class RateLimiterTests`, `class RetryAfterTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_fetch_minutes.py -q`

#### `backtester/tests/test_fetch_minutes_alt.py`

`test` · 117 lines · 5,012 B · description: **extracted**

**Purpose.** Non-Coinbase 1m fetcher: venue row orders, sanity abort, backward paging, resume, manifest.

**Contents.** Defines `NOW`, `class ParserTests`, `class WalkTests`, `class ManifestTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_fetch_minutes_alt.py -q`

#### `backtester/tests/test_full_suite.py`

`test` · 77 lines · 3,523 B · description: **extracted**

**Purpose.** research/full_suite.py: the plan, and stopping before the sweeps when a fetch fails.

**Contents.** Defines `class FullSuiteTests`. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_full_suite.py -q`

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

`test` · 531 lines · 24,327 B · description: **extracted**

**Purpose.** Tests for the resting-ladder grid simulator. The load-bearing test in this file is `test_round_trip_captures_exactly_one_rung`. The extension shipped a bug once where the exit rested at the level it had just bought at, capturing zero and paying two fees; `expectedRoundTripUsd` and its JS test exist to keep that fixed.

**Contents.** Defines `FREE`, `bars()`, `flat()`, `class TestLadderGeometry`, `class TestRoundTripEconomics`, `class TestNoLookahead`, `class TestFailureModes`, `class TestAccounting`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_gridsim.py -q`

#### `backtester/tests/test_index.py`

`test` · 241 lines · 10,913 B · description: **extracted**

**Purpose.** The repository index: isolation, correctness, and the staleness gate. No test here builds the real index or calls the network. `index/build.py`'s `semantic` subcommand is the only thing in this repo that opens a socket, and it talks to localhost ollama; a test that exercised it would be neither deterministic nor available in CI. The load-bearing test is the first one.

**Contents.** Defines `REPO`, `INDEX_DIR`, `class IsolationTests`, `class ClassificationTests`, `class ExtractionTests`, `class TextIndexTests`, `class ConceptTests`, `class StalenessGateTests`.

**Use.** `python3 -m pytest backtester/tests/test_index.py -q`

#### `backtester/tests/test_index_search_tooling.py`

`test` · 378 lines · 19,385 B · description: **extracted**

**Purpose.** The index helper scripts: ollama auto-start, the idle rebuild decision, and library search. No test touches a real ollama or embeds anything. Servers, clocks, load and processes are injected or patched, so these are deterministic and offline.

**Contents.** Defines `REPO`, `class EnsureTests`, `class IdleTests`, `class QueryTests`.

**Use.** `python3 -m pytest backtester/tests/test_index_search_tooling.py -q`

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

#### `backtester/tests/test_intrabar_liquidation.py`

`test` · 149 lines · 6,486 B · description: **extracted**

**Purpose.** A liquidation hidden inside a coarse bar must not be rescued by its close. The engine checks a held bar's low/high, but a daily range says only THAT a level was visited. These tests pin the finer-bar walk (IntrabarLayer) and the cases where a daily bar and its hourly bars disagree.

**Contents.** Defines `DAY`, `T0`, `class Always`, `daily()`, `hourly_for()`, `cfg()`, `class TestIntrabarLiquidation`, `class TestTierNoLeak`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_intrabar_liquidation.py -q`

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

#### `backtester/tests/test_scorecard.py`

`test` · 620 lines · 31,523 B · description: **extracted**

**Purpose.** Compound five-minute scorecard: no look-ahead, honest aggregation, honest statistics.

**Contents.** Defines `synthetic()`, `aux_for()`, `slice_aux()`, `same()`, `class PrefixInvarianceTests`, `class ConfigTests`, `only()`, `class AggregationTests`, `class AdaptiveTests`, `class TuningTests` and 3 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_scorecard.py -q`

#### `backtester/tests/test_signal_redundancy.py`

`test` · 314 lines · 14,442 B · description: **extracted**

**Purpose.** The redundancy script's pure parts. Following `test_cross_asset_cpcv.py`: no test here opens a price file, steps the engine, or writes anywhere under `research/results/`.

**Contents.** Defines `frame()`, `class TestRedundancy`, `class TestTwinVerdict`, `class TestPairTable`, `class TestFamilyVerdict`, `class TestResolveOutputPath`, `class TestPerStrategyTable`. Depends on `research`.

**Use.** `python3 -m pytest backtester/tests/test_signal_redundancy.py -q`

#### `backtester/tests/test_simulation_blind_audit.py`

`test` · 123 lines · 6,400 B · description: **extracted**

**Purpose.** Independent held-out selection and raw-bar refusal regressions.

**Contents.** Defines `class Always`, `arrays()`, `zero()`, `class RawMarketBoundary`, `class HeldOutSelection`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest backtester/tests/test_simulation_blind_audit.py -q`

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

#### `backtester/tests/test_textbook_strategies.py`

`test` · 256 lines · 11,614 B · description: **extracted**

**Purpose.** Tests for the five mechanisms named by the cited trading guides. Source catalogue: `tradingstrategyresults.json`. Each test targets what the mechanism could get *wrong*: DCA's ramp arithmetic, the PPO's scale invariance (the one property that separates it from MACD), the Fibonacci up-swing order and the turn-up condition, and the swing breakout level excluding its own bar.

**Contents.** Defines `window()`, `walk()`, `class TestDca`, `class TestEmaCrossover`, `class TestPpo`, `class TestFibLevel`, `class TestFibRetracement`, `class TestSwingConfluence`, `class TestNoLookahead`, `class TestRegistered`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_textbook_strategies.py -q`

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

#### `backtester/tests/test_triggers.py`

`test` · 184 lines · 8,297 B · description: **extracted**

**Purpose.** The trigger miner and trigger_trade: causality, statistics, gates and timing.

**Contents.** Defines `REPO`, `DAY`, `T0`, `_load_triggers()`, `T`, `walk()`, `class TestConditionsAreCausal`, `class TestStatistics`, `class TestForwardOutcomes`, `class TestMiningGates` and 1 more. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_triggers.py -q`

#### `backtester/tests/test_universe.py`

`test` · 264 lines · 11,902 B · description: **extracted**

**Purpose.** The multi-asset universe fetch. No test here touches the network. `list_coinbase_products` takes an injected `get_json` and `fetch_universe` takes an injected `fetcher`, for the reason `fetch.py`'s own docstring gives: fetching is an explicit step, and a test suite that performs it is neither deterministic nor polite to the venue. The behaviour most worth pinning is the refusal.

**Contents.** Defines `LISTED`, `bars()`, `class PlanTests`, `class FetchTests`, `class CliTests`, `class CompoundUniverseTests`. Depends on `backtester`.

**Use.** `python3 -m pytest backtester/tests/test_universe.py -q`

---

## research

Drivers that produce the numbers, and the write-ups that quote them. Everything here is reproducible from a committed script — the two occasions that was not true both produced a wrong published figure.

140 files.

#### `research/5minleveragestrategies.json`

`config` · 473 lines · 37,754 B · description: **derived**

**Purpose.** Generated JSON object, 9 keys (as_of, scope_note, answer_summary, jupiter_perps_context, current_cross_venue_observation, regime_identification...).

**Use.** Configuration; nothing to run.

#### `research/CANDLE-GAP-AUDIT.md`

`doc` · 209 lines · 12,779 B · description: **extracted**

**Purpose.** Generated by `research/candle_gap_audit.py` over 2026-07-06 .. 2026-08-06, five assets. Every figure comes from the Coinbase **trades** endpoint compared against the 1m candle cache in `data/`.

**Use.** Read it.

#### `research/COMPOUND-FRONTIER.md`

`doc` · 155 lines · 10,577 B · description: **extracted**

**Purpose.** The owner's question: the reversion metrics "are doing ok in testing" (52% out-of-sample hit on SOL) but every row says the profit is eaten by fees. How do you get around that, and is there a better strategy nearby? This page answers both with the frontier sweep (run `20261107T202943Z`, 1,250

**Use.** Read it.

#### `research/CROSS-ASSET-TRANSFER.md`

`doc` · 225 lines · 14,429 B · description: **extracted**

**Purpose.** python3 research/cross_asset_cpcv.py --self-test # gate: reproduces the BTC/ETH file python3 research/cross_asset_cpcv.py --assets SOL,DOGE,ZEC # 25 singles, medium horizon python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC # the five, with SOL as control

**Use.** Read it.

#### `research/GRID-REVIEW.md`

`doc` · 51 lines · 4,974 B · description: **extracted**

**Purpose.** Reviewed 2026-11-07 using engine `ad6fe0830c661fa1437a0c5606118f076dd13888`. The strategy named `grid` in the roster increases exposure as price falls below a rolling average. It is an exposure staircase, not a set of resting buy and sell orders. Its archived single-split SOL results lost money out of sample (see `backtester/strategy_cards/grid.md`).

**Use.** Read it.

#### `research/LEVERAGE-ECONOMICS.md`

`doc` · 162 lines · 8,146 B · description: **extracted**

**Purpose.** No network, no data files — this is closed-form arithmetic over published venue parameters, so it reproduces exactly. python3 research/leverage_economics.py --self-test # gate: 7 load-bearing claims

**Use.** Read it.

#### `research/LEVERAGE-TIERS.md`

`doc` · 63 lines · 5,740 B · description: **extracted**

**Purpose.** Simulation only. Reproduce with `python3 -m research.leverage_tiers --asset SOL --interval 1d` (about 6 seconds). Raw rows: `research/results/leverage_tiers_sol_1d_summary.csv`, Leverage multiplies the existing result and adds carry, so it can only help a signal that already

**Use.** Read it.

#### `research/PROMPT_STRATEGIES.md`

`doc` · 175 lines · 14,396 B · description: **extracted**

**Purpose.** <!-- HISTORICAL SPEC — preserved as written, do not retro-edit. This is the pdo-optimized spec that drove the first pass of the work. Two of its

**Use.** Read it.

#### `research/RANKED_LISTS.md`

`doc` · 1084 lines · 74,160 B · description: **extracted**

**Purpose.** configuration, so realised path counts are lower; see "How many paths each figure actually rests on" below. The earlier single 70/30 walk-forward is retained as List 1b, because the disagreement between the two methods is the most instructive result here.

**Use.** Read it.

#### `research/RATIO-ROTATION.md`

`doc` · 270 lines · 12,571 B · description: **extracted**

**Purpose.** Reproduce with: python3 -m backtester.core.universe --assets BTC,ETH,SOL,DOGE,ZEC --interval 1d python3 -m backtester.core.universe --assets XRP --interval 1d --allow-gaps

**Use.** Read it.

#### `research/RELIABLE_SIGNALS.md`

`doc` · 144 lines · 12,002 B · description: **extracted**

**Purpose.** Generated by `python3 -m research.triggers` (`build_report`). Simulation only. Not investment advice. A **trigger** is a conjunction of 1 to 3 conditions, each computed from bars up to and including bar t. When it fires at the close of bar t the trade enters at the open of bar t+1 and is judged at the close

**Use.** Read it.

#### `research/STRATEGIES.md`

`doc` · 802 lines · 41,316 B · description: **extracted**

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

`code-python` · 1298 lines · 49,940 B · description: **extracted**

**Purpose.** What every registered strategy, signal and indicator says about the last bar. python3 research/decide.py --asset SOL --interval 1d python3 research/decide.py --data data/BTC_1d.csv --json Three sections, because they are three different kinds of claim: * **Strategies** -- every entry in `core.strategies.REGISTRY`, replayed bar-by-bar from the start of history.

**Contents.** Defines `REPO`, `DEFAULT_TOLERANCE`, `FLAT_EPSILON`, `STALE_AFTER_BARS`, `HOLD_LONG`, `HOLD_SHORT`, `FLAT`, `BUY`, `SELL`, `INSUFFICIENT` and 30 more. Depends on `backtester`.

**Use.** `python3 research/decide.py --help`

#### `research/defillama-llms-risk-analysis.md`

`doc` · 41 lines · 4,845 B · description: **extracted**

**Purpose.** These protocols suffered catastrophic security exploits but have since recovered, compensated victims, or completely redesigned their architecture:

**Use.** Read it.

#### `research/dso_audit.py`

`code-python` · 365 lines · 16,073 B · description: **extracted**

**Purpose.** Mechanical half of the /dso statistical-honesty passes, run over the CPCV result CSVs. python3 research/dso_audit.py # audit every cpcv_* result file python3 research/dso_audit.py --floor 30 # raise the evidence floor `/dso` (the deep-strategy-optimizer skill) defines 19 audit passes.

**Contents.** Defines `REPO`, `RESULTS`, `FLAT_TOL`, `RESULT_KEYS`, `class AuditError`, `load()`, `KNOWN_DUPLICATE_GROUPS`, `DATA_DIR`, `DEFAULT_ASSET`, `ASSET_TOKENS` and 8 more. Depends on `backtester`.

**Use.** `python3 research/dso_audit.py --help`

#### `research/exchangefees.json`

`config` · 136 lines · 8,846 B · description: **derived**

**Purpose.** Generated JSON object, 3 keys (compiled_at, scope, exchanges).

**Use.** Configuration; nothing to run.

#### `research/frontier_tune.py`

`code-python` · 250 lines · 12,345 B · description: **extracted**

**Purpose.** Tune the frontier's promising rows without peeking at the out-of-sample window. /Users/mitch/.venvs/soltui/bin/python research/frontier_tune.py --run-id <frontier sweep run id> Input: one `python -m soltui.compound sweep --frontier` run in the compound results file (every metric alone, its strongest 2% of readings, held 1 h / 4 h / 24 h, unlevered, on every coin). 1.

**Contents.** Defines `REPO`, `HOLDS`, `QUANTILES`, `FACTORS`, `results_file()`, `load_run()`, `is_sharpe()`, `oos()`, `candidates()`, `config_for()` and 4 more. Depends on `backtester`.

**Use.** `python3 research/frontier_tune.py --help`

#### `research/full_suite.py`

`code-python` · 242 lines · 13,053 B · description: **extracted**

**Purpose.** Pull fresh data, then run every backtest: all coins, all strategies, all configurations. python3 research/full_suite.py --plan # print every step; touches nothing python3 research/full_suite.py # fetch, then both sweeps (hours) python3 research/full_suite.py --skip-fetch # re-run the sweeps on the cache you have python3 research/full_suite.py --fetch-only # refresh the cache and stop Run it with t

**Contents.** Defines `REPO`, `DEFAULT_ASSETS`, `fetch_steps()`, `sweep_steps()`, `listed_only()`, `archive_registry_results()`, `main()`. Depends on `backtester`, `soltui`.

**Use.** `python3 research/full_suite.py --help`

#### `research/geometry.py`

`code-python` · 300 lines · 12,846 B · description: **curated**

**Purpose.** Sensitivity of results to the CPCV geometry itself. Changing 8 blocks to 9 moved the best pair's median Sharpe more than the worst parameter nudge did — the evaluation design mattered more than the strategy.

**Contents.** Defines `REPO`, `OUT`, `class GeometryRun`, `spearman()`, `evaluate_geometry()`, `tidy_frame()`, `render()`, `verdict()`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/geometry.py --help`.

#### `research/grid_holdout.py`

`code-python` · 83 lines · 3,278 B · description: **extracted**

**Purpose.** Run the predeclared ladder from research/results/grid_review_20261107.json on bars it never saw. The review used a cache that ended 2026-08-04. This script scores the same configuration (bounds 85%-115% of the first close, seven geometric rungs, $12 per rung, $144 account) on bars from 2026-08-05 onward, at the review's costs and at twice those costs. Nothing is fitted.

**Contents.** Defines `HOLDOUT_START_TS`, `HOLDOUT_END_TS`, `ACCOUNT_USD`, `run()`, `main()`. Depends on `backtester`.

**Use.** `python3 research/grid_holdout.py --help`

#### `research/leverage_economics.py`

`code-python` · 170 lines · 8,131 B · description: **extracted**

**Purpose.** Cost economics of high-leverage perpetuals, for Jupiter Perps specifically. Generates every table in research/LEVERAGE-ECONOMICS.md. No network, no data files -- this is closed-form arithmetic over published venue parameters, so it reproduces exactly.

**Contents.** Defines `FEE_RT`, `R_LONG`, `R_SHORT`, `HOLDS`, `LEVS`, `break_even_move()`, `carry_crossover_hours()`, `hours_to_zero_collateral()`, `liquidation_move()`, `_fmt_h()` and 3 more.

**Use.** `python3 research/leverage_economics.py --help`

#### `research/leverage_tiers.py`

`code-python` · 177 lines · 7,993 B · description: **extracted**

**Purpose.** Low / medium / high margin tiers across the existing strategies, CPCV out-of-sample. python3 -m research.leverage_tiers --asset SOL --interval 1d python3 -m research.leverage_tiers --asset SOL --interval 1d --tiers 2,5,20 Every registered strategy (at the sweep's horizon parameters) is run as a Jupiter-Perps position at each tier's leverage, with fees, slippage, borrow carry, maintenance margin an

**Contents.** Defines `REPO`, `OUT`, `RUIN_LEVEL`, `HORIZON_FOR`, `_layer()`, `load_layers()`, `path_stats()`, `run()`, `coverage_audit()`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/leverage_tiers.py --help`

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

#### `research/profitable-crypto-strategies-analysis.md`

`doc` · 245 lines · 18,589 B · description: **extracted**

**Purpose.** The vast majority of headline yields in decentralized finance are economic illusions. In competitive, permissionless financial markets, sustained positive expected value ($+\text{EV}$) cannot exist without an economic counterparty taking an equal and opposite negative expected value ($-\text{EV}$) position, or an entity paying non-dilutive economic rent for a verifiable service (liquidity, credit,

**Use.** Read it.

#### `research/ratio_rotation.py`

`code-python` · 1493 lines · 64,498 B · description: **extracted**

**Purpose.** Numeraire-switching rotation: hold whichever coin is cheapest against its peers. python3 research/ratio_rotation.py --self-test python3 research/ratio_rotation.py --turnover-table python3 research/ratio_rotation.py --demo-chain python3 research/ratio_rotation.py --sweep python3 research/ratio_rotation.py --sweep --assets BTC,ETH,SOL,DOGE,ZEC,XRP This answers a question the single-asset engine cann

**Contents.** Defines `REPO`, `OUT_DIR`, `PRIMARY_ASSETS`, `SECONDARY_ASSETS`, `MIN_OOS_ROTATIONS`, `SPLIT`, `SWEEP_WINDOWS`, `SWEEP_TOP_K`, `SWEEP_DIRECTIONS`, `SWEEP_MARGINS` and 26 more. Depends on `backtester`.

**Use.** `python3 research/ratio_rotation.py --help`

#### `research/run_backfill.sh`

`code-shell` · 111 lines · 4,015 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `research/short_horizon_economics.py`

`code-python` · 283 lines · 13,637 B · description: **extracted**

**Purpose.** Cost economics of SHORT-HORIZON leveraged perpetuals on Jupiter Perps. Sibling of research/leverage_economics.py, which stops at a 1-hour hold.

**Contents.** Defines `FEE_RT`, `R_LONG`, `R_SHORT`, `UTIL`, `VOL_ANNUAL`, `HOURS_PER_YEAR`, `HORIZONS`, `TX_COSTS`, `NOTIONALS`, `LEVS` and 11 more.

**Use.** `python3 research/short_horizon_economics.py --help`

#### `research/signal_redundancy.py`

`code-python` · 629 lines · 26,889 B · description: **extracted**

**Purpose.** Measure how many independent bets the strategy registry actually contains. python3 research/signal_redundancy.py # SOL, medium python3 research/signal_redundancy.py --horizon short # SOL hourly, slower python3 research/signal_redundancy.py --asset BTC --out auto # BTC, canonical name python3 research/signal_redundancy.py --top 25 # longer pair list Why this script exists.

**Contents.** Defines `REPO`, `OUT`, `VARIANCE_TARGET`, `SKIP_FAMILIES`, `exposure_matrix()`, `redundancy()`, `pair_table()`, `per_strategy_table()`, `family_verdict()`, `twin_groups()` and 6 more. Depends on `backtester`, `research`.

**Use.** `python3 research/signal_redundancy.py --help`

#### `research/sweep.py`

`code-python` · 877 lines · 37,060 B · description: **curated**

**Purpose.** Defines `HORIZONS` — the per-horizon data file, interval, gap policy and parameter set — and runs the single-split walk-forward that CPCV superseded. The parameter tables here are what every other driver imports, so an edit moves every downstream number.

**Contents.** Defines `REPO`, `data_dir()`, `set_data_dir()`, `OUT_DIR`, `MIN_OOS_TRADES`, `MIN_DISCOVERY_TRADES`, `SPLIT`, `COMBO_CANDIDATES`, `class Row`, `load_horizon()` and 17 more. Depends on `backtester`.

**Use.** `python3 research/sweep.py --help`. Imported by the other drivers for `HORIZONS` and `load_horizon`.

#### `research/sweep_untested.py`

`code-python` · 103 lines · 3,769 B · description: **extracted**

**Purpose.** Finds and sweeps untested strategies and configurations. Identifies strategies in the REGISTRY that do not have baseline parameters in `research/sweep.py` or runs new configurations for existing strategies to compute profitability metrics like Sharpe, Kelly, and Drawdown.

**Contents.** Defines `REPO`, `main()`. Depends on `backtester`, `research`.

**Use.** `python3 research/sweep_untested.py --help`

#### `research/tick_backfill.py`

`code-python` · 351 lines · 14,899 B · description: **extracted**

**Purpose.** Long-running, resumable tick backfill and candle-integrity audit. Built to run for hours at low priority in the background. See `research/run_backfill.sh` for the wrapper that sets the priority. Why a streaming walk instead of `candle_gap_audit.py`'s per-gap fetch.

**Contents.** Defines `REPO`, `PAGE`, `CHECKPOINT_EVERY`, `_handle_stop()`, `class MinuteAggregator`, `_page()`, `backfill()`, `_write_ck()`, `audit()`, `rerun_decision()` and 1 more. Depends on `backtester`.

**Use.** `python3 research/tick_backfill.py --help`

#### `research/tradingstrategyresults.json`

`config` · 197 lines · 15,075 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys (scope, as_of, strategies, indicators_and_signals).

**Use.** Configuration; nothing to run.

#### `research/trigger_backtest.py`

`code-python` · 105 lines · 5,781 B · description: **extracted**

**Purpose.** Trade the mined triggers through the leverage tiers, out of sample only. Called by `python3 -m research.triggers --backtest`. Takes the qualified (reliable) triggers; if none qualified, takes the best near-misses and labels every number EXPLORATORY. The stop for each trigger is its discovery-period MAE (`stop_frac`), never a number chosen after seeing the validation period.

**Contents.** Defines `OUT`, `TOP_NEAR_MISSES`, `VALIDATION_BLOCKS`, `select()`, `run()`. Depends on `backtester`, `research`.

**Use.** `import research.trigger_backtest`

#### `research/triggers.py`

`code-python` · 606 lines · 29,750 B · description: **extracted**

**Purpose.** Reliable-trigger miner: which conjunctions of conditions predict direction, and how well. python3 -m research.triggers --asset SOL --interval 1d python3 -m research.triggers --asset SOL --interval 1h python3 -m research.triggers --asset SOL --interval 1d --backtest Simulation and research only: no network, no keys, no orders.

**Contents.** Defines `REPO`, `OUT`, `HORIZONS`, `H_MAX`, `MIN_EVENTS`, `FDR_Q`, `HLZ_Z`, `DISCOVERY_FRACTION`, `STABILITY_MIN_EVENTS`, `STABILITY_SHARE` and 30 more. Depends on `backtester`, `research`.

**Use.** `python3 research/triggers.py --help`

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

#### `research/results/compound-10coin-fullhistory-2026-11-07.json`

`result` · 422 lines · 8,760 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (run_id, configurations, round_trip_bps, leverage, coins, command...).

**Use.** `json.load(open('research/results/compound-10coin-fullhistory-2026-11-07.json'))`

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

#### `research/results/frontier-2026-11-07.json`

`result` · 5556 lines · 143,755 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (run_id, coins, configurations_tried_per_coin, note, candidates, chosen...).

**Use.** `json.load(open('research/results/frontier-2026-11-07.json'))`

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

#### `research/results/grid_holdout_20261107.json`

`result` · 34 lines · 987 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (bars, data_sha256, first_close, first_ts, last_close, last_ts...).

**Use.** `json.load(open('research/results/grid_holdout_20261107.json'))`

#### `research/results/grid_review_20261107.json`

`result` · 296 lines · 9,023 B · description: **derived**

**Purpose.** Generated JSON object, 13 keys (schema, review_date, engine_revision, data_file, data_sha256, costs...).

**Use.** `json.load(open('research/results/grid_review_20261107.json'))`

#### `research/results/hyperliquid-costs-2026-11-07.json`

`result` · 187 lines · 3,599 B · description: **derived**

**Purpose.** Generated JSON object, 10 keys (as_of, source, perp_fee_schedule_base, vip_tiers, referral_discount, book_cost_definition...).

**Use.** `json.load(open('research/results/hyperliquid-costs-2026-11-07.json'))`

#### `research/results/ladder_grid_sol.csv`

`result` · 20 lines · 2,679 B · description: **derived**

**Purpose.** Generated data: 18 rows x 18 columns (interval, mode, block, bars, lower, upper, capital_deployed, round_trips...).

**Contents.** Columns: `interval`, `mode`, `block`, `bars`, `lower`, `upper`, `capital_deployed`, `round_trips`, `realized_usd`, `pct_of_deployed`, `grid_total_return`, `grid_max_drawdown`, `hold_total_return`, `hold_max_drawdown`, `pct_bars_outside_ladder`, `buys`, `sells`, `forced_exit_qty`.

**Use.** `pandas.read_csv('research/results/ladder_grid_sol.csv')` — regenerate with the driver that names it.

#### `research/results/leverage_tiers_sol_1d.json`

`result` · 78 lines · 2,255 B · description: **derived**

**Purpose.** Generated JSON object, 5 keys (coverage, summary, ruin_level, groups, k).

**Use.** `json.load(open('research/results/leverage_tiers_sol_1d.json'))`

#### `research/results/leverage_tiers_sol_1d_per_strategy.csv`

`result` · 102 lines · 11,176 B · description: **derived**

**Purpose.** Generated data: 100 rows x 10 columns (tier, leverage, strategy, median_sharpe, frac_positive, median_return, trades, liquidations...).

**Contents.** Columns: `tier`, `leverage`, `strategy`, `median_sharpe`, `frac_positive`, `median_return`, `trades`, `liquidations`, `median_max_dd`, `p_ruin`.

**Use.** `pandas.read_csv('research/results/leverage_tiers_sol_1d_per_strategy.csv')` — regenerate with the driver that names it.

#### `research/results/leverage_tiers_sol_1d_summary.csv`

`result` · 6 lines · 787 B · description: **derived**

**Purpose.** Generated data: 4 rows x 12 columns (tier, leverage, strategies, paths, oos_median_sharpe, pct_paths_positive, median_path_return_pct, liquidations_per_path...).

**Contents.** Columns: `tier`, `leverage`, `strategies`, `paths`, `oos_median_sharpe`, `pct_paths_positive`, `median_path_return_pct`, `liquidations_per_path`, `pct_paths_with_liquidation`, `median_max_dd_pct`, `worst_max_dd_pct`, `p_ruin_pct`.

**Use.** `pandas.read_csv('research/results/leverage_tiers_sol_1d_summary.csv')` — regenerate with the driver that names it.

#### `research/results/minute_coverage.json`

`result` · 225 lines · 6,481 B · description: **derived**

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

#### `research/results/top50-nonpegged-2026-11-07.json`

`result` · 487 lines · 10,633 B · description: **derived**

**Purpose.** Generated JSON object, 8 keys (as_of, source, listing_source, rule, excluded_pegged, coins...).

**Use.** `json.load(open('research/results/top50-nonpegged-2026-11-07.json'))`

#### `research/results/top50-screen-2026-11-07.json`

`result` · 580 lines · 16,416 B · description: **derived**

**Purpose.** Generated JSON object, 7 keys (as_of, universe_source, sources, criteria, not_checked, kept...).

**Use.** `json.load(open('research/results/top50-screen-2026-11-07.json'))`

#### `research/results/top_coins.csv`

`result` · 17 lines · 910 B · description: **derived**

**Purpose.** Generated data: 15 rows x 8 columns (rank, symbol, name, price_usd, market_cap_usd, volume_24h_usd, pegged, local_data).

**Contents.** Columns: `rank`, `symbol`, `name`, `price_usd`, `market_cap_usd`, `volume_24h_usd`, `pegged`, `local_data`.

**Use.** `pandas.read_csv('research/results/top_coins.csv')` — regenerate with the driver that names it.

#### `research/results/trigger_backtest_sol_1d.csv`

`result` · 22 lines · 3,887 B · description: **derived**

**Purpose.** Generated data: 20 rows x 18 columns (label, conditions, direction, horizon, stop, tier, leverage, oos_trades...).

**Contents.** Columns: `label`, `conditions`, `direction`, `horizon`, `stop`, `tier`, `leverage`, `oos_trades`, `oos_liquidations`, `oos_return`, `oos_sharpe`, `oos_max_dd`, `cpcv_paths`, `cpcv_median_sharpe`, `cpcv_pct_positive`, `cpcv_median_return`, `cpcv_liquidations`, `cpcv_p_ruin`.

**Use.** `pandas.read_csv('research/results/trigger_backtest_sol_1d.csv')` — regenerate with the driver that names it.

#### `research/results/trigger_backtest_sol_1d.json`

`result` · 6 lines · 133 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys (label, validation_start, validation_end, triggers).

**Use.** `json.load(open('research/results/trigger_backtest_sol_1d.json'))`

#### `research/results/triggers_sol_1d.csv`

`result` · 302 lines · 262,454 B · description: **derived**

**Purpose.** Generated data: 300 rows x 37 columns (conditions, depth, direction, horizon, is_n, is_hit, is_base, is_p...).

**Contents.** Columns: `conditions`, `depth`, `direction`, `horizon`, `is_n`, `is_hit`, `is_base`, `is_p`, `is_z`, `is_ci_lo`, `is_ci_hi`, `is_mean_ret`, `is_median_ret`, `oos_n`, `oos_hit`, `oos_base`, `oos_p`, `oos_ci_lo`, `oos_ci_hi`, `oos_mean_ret`, `oos_median_ret`, `oos_mae_median`, `oos_mae_p10`, `oos_mfe_median`, `decay_hit`, `stop_frac`, `stable_share`, `stable_periods`, `stable_detail`, `repl_assets`, `repl_beating`, `repl_detail`, `path_is`, `path_oos`, `reliable`, `failed_gates`, `uses_funding`.

**Use.** `pandas.read_csv('research/results/triggers_sol_1d.csv')` — regenerate with the driver that names it.

#### `research/results/triggers_sol_1d.json`

`result` · 50 lines · 983 B · description: **derived**

**Purpose.** Generated JSON object, 25 keys (asset, interval, bars, first_bar_utc, last_bar_utc, discovery_start...).

**Use.** `json.load(open('research/results/triggers_sol_1d.json'))`

#### `research/results/triggers_sol_1h.csv`

`result` · 302 lines · 237,022 B · description: **derived**

**Purpose.** Generated data: 300 rows x 37 columns (conditions, depth, direction, horizon, is_n, is_hit, is_base, is_p...).

**Contents.** Columns: `conditions`, `depth`, `direction`, `horizon`, `is_n`, `is_hit`, `is_base`, `is_p`, `is_z`, `is_ci_lo`, `is_ci_hi`, `is_mean_ret`, `is_median_ret`, `oos_n`, `oos_hit`, `oos_base`, `oos_p`, `oos_ci_lo`, `oos_ci_hi`, `oos_mean_ret`, `oos_median_ret`, `oos_mae_median`, `oos_mae_p10`, `oos_mfe_median`, `decay_hit`, `stop_frac`, `stable_share`, `stable_periods`, `stable_detail`, `repl_assets`, `repl_beating`, `repl_detail`, `path_is`, `path_oos`, `reliable`, `failed_gates`, `uses_funding`.

**Use.** `pandas.read_csv('research/results/triggers_sol_1h.csv')` — regenerate with the driver that names it.

#### `research/results/triggers_sol_1h.json`

`result` · 42 lines · 902 B · description: **derived**

**Purpose.** Generated JSON object, 25 keys (asset, interval, bars, first_bar_utc, last_bar_utc, discovery_start...).

**Use.** `json.load(open('research/results/triggers_sol_1h.json'))`

---

## extension

The Chrome extension, and the only component that can place a real order. Dry-run is the default, risk rails live in code and fail closed, and a fresh install must not be able to trade.

92 files.

#### `extension/README.md`

`doc` · 613 lines · 40,568 B · description: **extracted**

**Purpose.** A Chrome MV3 extension for the owner's Base and Solana money: **holdings, profit and loss, pool discovery, backtests and strategy changes, swap quotes, and alerts** when a more profitable pool or strategy appears. It also keeps an **experimental grid trading strategy on Jupiter (Solana)** with

**Use.** Read it.

#### `extension/manifest.json`

`config` · 47 lines · 1,287 B · description: **curated**

**Purpose.** MV3 manifest: permissions, the service worker entry point, and the UI surfaces. The permission list is the extension's blast radius, so review any addition against `docs/SECURITY.md`.

**Use.** Load unpacked from `extension/` in `chrome://extensions`.

#### `extension/package.json`

`config` · 22 lines · 604 B · description: **curated**

**Purpose.** Node scripts for the extension's test and tooling surfaces.

**Use.** `npm test` inside `extension/`.

### `extension/e2e/fixtures/`

#### `extension/e2e/fixtures/fake-soltui-host.mjs`

`code-js` · 29 lines · 1,191 B · description: **extracted**

**Purpose.** Speaks Chrome's native messaging framing on stdio, over the fake registry. SOLTUI_FAKE_MODE: hang (never answers) | crash (exits at once) | garbage (bad frame).

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/e2e/fixtures/fake-soltui-registry.js`

`code-js` · 33 lines · 2,217 B · description: **extracted**

**Purpose.** A stand-in for soltui's registry with the same envelope shapes as the contract. It exists so the extension's side of the bridge is tested without Python; the real host is exercised in tools/e2e.mjs.

**Contents.** Defines `FAKE_COMMANDS`, `fakeHandle`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/e2e/lib/`

#### `extension/e2e/lib/cdp.mjs`

`code-js` · 206 lines · 7,244 B · description: **extracted**

**Purpose.** Minimal Chrome DevTools Protocol client over the DevTools pipe. Why the pipe and not a WebSocket: `Extensions.loadUnpacked` is only exposed on `--remote-debugging-pipe` (with `--enable-unsafe-extension-debugging`), and the branded Chrome channel ignores `--load-extension`. So this needs Chrome for Testing or Chromium, and it needs no port, no HTTP discovery and no package.

**Contents.** Defines `CALL_TIMEOUT_MS`, `EXIT_GRACE_MS`, `findChromeForTesting`, `launch`, `parseFrames`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/e2e/lib/guard.mjs`

`code-js` · 94 lines · 3,167 B · description: **extracted**

**Purpose.** What the e2e harness may ask the extension to do. The harness drives the real service worker through `chrome.runtime.sendMessage`. It must never arm the extension, change its mode, create a key or cancel an order, so every message goes through this allowlist first.

**Contents.** Defines `ALLOWED_MESSAGES`, `FORBIDDEN_MESSAGES`, `assertAllowedMessage`, `assertDisarmed`, `assertSoltuiCallAllowed`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/e2e/lib/soltui-host.mjs`

`code-js` · 83 lines · 3,758 B · description: **extracted**

**Purpose.** The soltui native messaging host, for the real-browser e2e. Chrome for Testing runs with a throwaway --user-data-dir, and Chrome looks for native messaging host manifests in <user-data-dir>/NativeMessagingHosts first.

**Contents.** Defines `EXT`, `FIXTURE`, `HOST_NAME`, `installHost`, `realHostAnswers`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/icons/`

#### `extension/icons/icon-128.png`

`other` · 0 lines · 1,662 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `extension/icons/icon-16.png`

`other` · 0 lines · 251 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `extension/icons/icon-32.png`

`other` · 0 lines · 491 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `extension/icons/icon-48.png`

`other` · 0 lines · 672 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

### `extension/src/bg/`

#### `extension/src/bg/service-worker.js`

`code-js` · 370 lines · 15,758 B · description: **extracted**

**Purpose.** MV3 service worker — the extension surface of the command registry. There is no long-lived process here. The worker is woken by an alarm, runs one tick, and is free to die. Nothing may be held in module scope that the next tick depends on: everything durable lives in IndexedDB or chrome.storage.local, and the tick rebuilds its world from those plus the venue's live state.

**Contents.** Defines `ALARM`, `ALERT_ALARM`, `ALIASES`, `BUILD_ALARM`, `MIN_PERIOD_MINUTES`, `chromeDeps`, `handleInstalled`, `handleMessage`, `openAlertCount`, `paintBadge` and 8 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/bg/soltui-transport.js`

`code-js` · 85 lines · 3,339 B · description: **extracted**

**Purpose.** Service-worker transport to the soltui native messaging host. Chrome starts `com.mitchhudson.soltui` (soltui/native_host.py) on demand and speaks length-prefixed JSON with it. This file owns what is Chrome-specific about that: the port, the request id, the per-call timeout and the clean error when the host is not installed.

**Contents.** Defines `INSTALL_HINT`, `createNativeTransport`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/core/`

#### `extension/src/core/alerts.js`

`code-js` · 257 lines · 13,110 B · description: **extracted**

**Purpose.** Alerts: "there is a more profitable pool or strategy than what you have now". Pure. No I/O, no chrome.*, no clock of its own: the scan in commands.js reads the inputs, and this file decides.

**Contents.** Defines `DEFAULT_PREFS`, `PREF_TYPES`, `SEVERITY`, `computeAlerts`, `mergeAlerts`, `notifiable`, `prefsProblem`, `qualifyingLeads`, `scoutAgeHours`, `viableScoutPools`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/autoreload.js`

`code-js` · 105 lines · 4,558 B · description: **extracted**

**Purpose.** Auto-reload on update, as a pure decision with injected effects. Once a minute the service worker asks the soltui host for `buildHash`, a SHA-256 over the manifest and src/ of the extension directory on disk. When that hash differs from the one the worker stored, the code on disk is newer than the code Chrome loaded, and `chrome.runtime.reload()` picks it up. A reload kills the worker.

**Contents.** Defines `BUILD_STATE_KEY`, `HASH`, `OUTCOME`, `checkForUpdate`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/commands.js`

`code-js` · 906 lines · 41,150 B · description: **extracted**

**Purpose.** The command registry — single source of truth for every action this project can perform. Three surfaces drive this one registry: extension src/bg/service-worker.js (chrome.runtime messages) CLI tools/cli.js (argv) HTTP API tools/api-server.js (POST /v1/<command>) Nothing may be reachable from one surface and not the others.

**Contents.** Defines `ACKS_KEY`, `COMMANDS`, `COMMAND_NAMES`, `CONTEXT_FIELDS`, `DISARM_FIELDS`, `LADDER_FIELDS`, `MAX_ACKS`, `MAX_ALERT_ID`, `PREFS_KEY`, `SCAN_KEY` and 14 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/engine.js`

`code-js` · 576 lines · 24,245 B · description: **extracted**

**Purpose.** The tick. Order of operations is the whole design: RECONCILE before PLAN, always. A MV3 service worker can be killed at any moment, including between "write the intent" and "the venue accepted the order". So the venue's live order list — not our local records — is the source of truth at the top of every tick. Local state is a cache and a journal, nothing more.

**Contents.** Defines `PRICE_MATCH_TOLERANCE`, `enginePending`, `engineStopGeneration`, `ingestFills`, `ingestFillsUnlocked`, `keyForLiveOrder`, `matchIntent`, `occupiedIntentKeys`, `pricesMatch`, `reconcile` and 7 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/grid.js`

`code-js` · 388 lines · 14,840 B · description: **extracted**

**Purpose.** Pure grid-strategy engine. No I/O, no chrome.* APIs, no network. Everything here is a deterministic function of (config, price, open state) so the whole strategy is unit testable and a service-worker restart can recompute intent from scratch.

**Contents.** Defines `DIRECTION`, `MAX_GRID_RUNGS`, `SIDE`, `SPACING`, `capitalRequirement`, `expectedRoundTripUsd`, `gridLevels`, `intentKey`, `nearestLevelIndex`, `pairedExitLevel` and 5 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/pnl.js`

`code-js` · 253 lines · 9,038 B · description: **extracted**

**Purpose.** P&L accounting. Two lot-matching modes, because two consumers want different answers: PAIRED (default) A sell fill that records the lots its intent was paired with (`closesLots`) closes THOSE lots. Grid exits are placed one rung above a specific buy, so when rung B's exit fills before rung A's, the inventory still held is A's, and strict FIFO would instead consume A and leave B behind.

**Contents.** Defines `EPS`, `equityCurve`, `fillsToCsv`, `matchFifo`, `maxDrawdown`, `snapshot`, `totalCarryUsd`, `winRate`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/risk.js`

`code-js` · 293 lines · 11,797 B · description: **extracted**

**Purpose.** Risk rails. Every rail is enforced here, in code, as a gate the executor must pass before anything is submitted. A rail that lives only in the README is not a rail. `evaluate()` is pure so the dashboard can show exactly which rail would block a grid before you arm it.

**Contents.** Defines `DEFAULT_LIMITS`, `RAILS`, `VERDICT`, `admitBatch`, `capitalExposure`, `dayKey`, `evaluate`, `inventoryPool`, `normaliseLimits`, `normaliseState` and 1 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/core/soltui.js`

`code-js` · 132 lines · 5,505 B · description: **extracted**

**Purpose.** The soltui bridge, transport-free. soltui (Python) owns its own command registry and answers every call with one JSON envelope: {"ok": true, "command": "x.y", "result": <json>, "error": null} {"ok": false, "command": "x.y", "result": null, "error": {"code", "message"}} This module forwards a call to an injected transport and hands that envelope back UNCHANGED, so the extension, the extension's nod

**Contents.** Defines `COMMAND_NAME`, `META_TTL_MS`, `SOLTUI_ERROR`, `SOLTUI_HOST_NAME`, `SOLTUI_TIMEOUT_MS`, `ask`, `class SoltuiTransportError`, `isEnvelope`, `isLongRunning`, `soltuiBuildHash` and 2 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/jupiter/`

#### `extension/src/jupiter/attribution.js`

`code-js` · 73 lines · 3,303 B · description: **extracted**

**Purpose.** Licence-required attribution, in one place. The Jupiter SDK & API License Agreement (read 2026-08-04) imposes two display obligations that are easy for a private tool to miss, because nobody else sees the UI: §8.4 the product "shall prominently display to end users ... 'Powered by Jupiter'".

**Contents.** Defines `POWERED_BY`, `ROUTING_API`, `ROUTING_NOTE`, `SURFACES`, `attributionDetail`, `attributionLine`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/http.js`

`code-js` · 166 lines · 6,195 B · description: **extracted**

**Purpose.** HTTP layer for the Jupiter APIs. A grid ticking every 30s across N rungs will hit rate limits on the free tier, so retry/backoff and a per-tick request budget are part of the client rather than something callers remember to add.

**Contents.** Defines `DEFAULT_TIMEOUT_MS`, `RETRYABLE_STATUS`, `backoffDelayMs`, `class JupiterHttpError`, `class RequestBudget`, `defaultRequestLog`, `headers`, `request`, `safePath`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/price.js`

`code-js` · 86 lines · 2,853 B · description: **extracted**

**Purpose.** Price lookup. Two shapes have shipped across Price API versions (`{ <mint>: {...} }` in v3, `{ data: { <mint>: {...} } }` in v2). The parser accepts either and throws a named error on anything else, so a version bump surfaces as one clear failure instead of `undefined` propagating into order sizing.

**Contents.** Defines `PRICE_HOSTS`, `class PriceShapeError`, `getDecimals`, `getPriceTable`, `getPrices`, `parsePrices`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/jupiter/trigger.js`

`code-js` · 340 lines · 12,437 B · description: **extracted**

**Purpose.** Jupiter Trigger V2 client. Endpoint shapes below are transcribed from the live docs (verified 2026-11-06, with contract regression fixtures): https://developers.jup.ag/docs/trigger https://developers.jup.ag/docs/trigger/create-order https://developers.jup.ag/docs/trigger/authentication https://developers.jup.ag/docs/trigger/deposit https://developers.jup.ag/docs/trigger/manage-orders Flow: authent

**Contents.** Defines `CONDITION`, `ORDER_TYPE`, `TRIGGER_BASE`, `TRIGGER_LIMITS`, `confirmCancel`, `craftDeposit`, `createPriceOrder`, `getChallenge`, `initiateCancel`, `listOrders` and 6 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/market/`

#### `extension/src/market/evm.js`

`code-js` · 131 lines · 5,098 B · description: **extracted**

**Purpose.** The small slice of EVM ABI encoding the market reads need, in BigInt. Kept by hand rather than pulling in viem or ethers: the extension has zero runtime dependencies (CLAUDE.md, house style), and the reads here are a handful of fixed-shape view calls.

**Contents.** Defines `ADDRESS`, `HEX`, `SELECTOR`, `ZERO_ADDRESS`, `abiString`, `addressOf`, `fromUnits`, `hexBytes`, `hexToBigInt`, `intArray` and 6 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/market/holdings.js`

`code-js` · 296 lines · 12,337 B · description: **extracted**

**Purpose.** Live holdings: what the owner's public Base and Solana addresses hold, in USD. Read-only. No key, no signature, no transaction: Base is read with eth_getBalance and ERC-20 balanceOf through one JSON-RPC batch, Solana with getBalance and getTokenAccountsByOwner, prices from DefiLlama (Base) and the keyless Jupiter price API (Solana).

**Contents.** Defines `DUST_USD`, `MIN_LIQUIDITY_USD`, `SOLANA_KNOWN`, `STABLE_MINTS`, `chainResult`, `fail`, `finish`, `readBase`, `readHoldings`, `readSolana` and 3 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/market/net.js`

`code-js` · 115 lines · 4,533 B · description: **extracted**

**Purpose.** Read-only network access for the market modules (holdings, pools, quotes). Everything here goes through `request` in src/jupiter/http.js, so the timeout, retry and JSON handling are the same ones the trading path uses. The fetch implementation comes from `deps.fetch`: the service worker, the CLI and the HTTP API inject the platform fetch, and tests inject a stub.

**Contents.** Defines `READ_METHOD`, `assertReadMethod`, `class MarketError`, `fetchOf`, `getJson`, `postJson`, `rpcBatch`, `rpcCall`, `safeHost`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/market/pools.js`

`code-js` · 101 lines · 4,403 B · description: **extracted**

**Purpose.** Pool discovery from DefiLlama yields (keyless, https://yields.llama.fi/pools). Every APY here is QUOTED by DefiLlama, not measured by this project. It includes reward emissions and can be a short-window spike.

**Contents.** Defines `CHAIN_NAMES`, `POOL_CACHE_MS`, `fetchPools`, `fetchPoolsCached`, `newPoolIds`, `normalisePool`, `rankPools`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/market/quote.js`

`code-js` · 201 lines · 10,579 B · description: **extracted**

**Purpose.** Swap quotes. Quote only: nothing here builds, signs or sends a transaction. The extension's signer has no semantic transaction verifier, so live signing stays blocked (CLAUDE.md, "Known-unverified areas"). A quote is handed to the venue's own page, where the owner reviews and signs in their wallet. See Stele KNOW-837.

**Contents.** Defines `Q96`, `activeRange`, `baseToken`, `quote`, `quoteBase`, `quoteSolana`, `swapWithinRange`, `tickAtSqrtX96`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/market/tokens.js`

`code-js` · 96 lines · 5,458 B · description: **extracted**

**Purpose.** Chains, endpoints and the known-token lists the market reads use. Base: chain id 8453 (0x2105), public RPC https://mainnet.base.org (docs.base.org network table), with base-rpc.publicnode.com first because soltui/wallet.py found it less throttled. Since Denim (Base mainnet, 2026-11-05) the `pending` tag no longer returns preconfirmation state, so every read here uses `latest`.

**Contents.** Defines `BASE`, `BASE_TOKENS`, `CHAINS`, `ENDPOINTS`, `JUPITER_MARKET_BASES`, `SOLANA`, `SOLANA_ADDRESS`, `SOLANA_TOKENS`, `findToken`.

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

`code-js` · 258 lines · 8,470 B · description: **extracted**

**Purpose.** Persistence. Two surfaces, chosen by what the data is: chrome.storage.local — config and limits. Small, synchronously readable at worker start, and NEVER `.sync` (that would push settings, and anything near them, to Google's servers). IndexedDB — the intent journal and fill log.

**Contents.** Defines `CONFIG_KEY`, `DB_NAME`, `DB_VERSION`, `DEFAULT_CONFIG`, `INTENT_STATUS`, `RUNTIME_KEY`, `STORES`, `class ConfigStore`, `class Store`, `openDb` and 1 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/ui/`

#### `extension/src/ui/charts.js`

`code-js` · 131 lines · 4,780 B · description: **extracted**

**Purpose.** Charts drawn with TradingView Lightweight Charts, the one vendored runtime library (extension/vendor/lightweight-charts/, Apache-2.0, pinned 5.2.1). The library is imported lazily, on first draw, so node tests and the service worker never load it, and a missing or broken copy degrades to the caller's SVG fallback instead of a blank panel.

**Contents.** Defines `LIB_PATH`, `disposeChart`, `loadLibrary`, `renderEquityChart`, `toLineData`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/dashboard.html`

`code-web` · 520 lines · 27,650 B · description: **curated**

**Purpose.** Full-page dashboard shell for open state, ladder rungs and recent ticks. Markup only.

**Use.** Opened from the popup.

#### `extension/src/ui/dashboard.js`

`code-js` · 193 lines · 7,643 B · description: **extracted**

**Purpose.** Dashboard shell: hash routing between views, the top bar, the stored scan, and Settings. Views load on first visit and on their own Refresh buttons; Overview paints from the stored scan first so the page is useful before any network answers. Every action goes through a registry command (src/core/commands.js) — this page holds no trading or alert logic of its own.

**Contents.** Defines `ALIASES`, `VIEWS`, `ack`, `current`, `loadOverview`, `loadSettings`, `mountSettings`, `repaint`, `show`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/popup.html`

`code-web` · 85 lines · 3,601 B · description: **curated**

**Purpose.** Browser-action popup shell — status at a glance and the dry-run toggle. Markup only; behaviour lives in the JS modules.

**Use.** Opens from the toolbar icon.

#### `extension/src/ui/popup.js`

`code-js` · 220 lines · 8,547 B · description: **extracted**

**Purpose.** Popup: holdings and alerts at a glance, shortcuts into the dashboard, and the grid's arm / disarm / kill controls (collapsed: the grid is experimental). All state comes from the service worker over messages. The popup holds no strategy logic — it can be closed mid-tick without consequence, and it must never be the thing that decides whether an order is placed.

**Contents.** Defines `act`, `paintAlerts`, `paintHoldings`, `paintPnl`, `refresh`, `refreshOverview`, `scan`, `showError`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/session-key-form.js`

`code-js` · 44 lines · 1,701 B · description: **extracted**

**Purpose.** Pure helpers for the dashboard's "Create session key" control. Kept free of DOM and chrome.* so the input rules and the message shape are unit-testable. The command in src/core/commands.js stays the authority; this only catches a typo before a passphrase is sealed into a vault that nothing can reopen.

**Contents.** Defines `MIN_PASSPHRASE_LENGTH`, `buildCreateSessionKeyMessage`, `describeCreateResult`, `validateSessionKeyInputs`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/soltui-panel.js`

`code-js` · 190 lines · 7,017 B · description: **extracted**

**Purpose.** Dashboard panel for the soltui command bridge. The command list comes from the registry (`soltuiCommands`), the form is built from each command's declared params by type, and a Run sends only `soltuiCall` with a command name taken from that list. Nothing here knows a soltui command by name, so a new soltui command shows up with no change.

**Contents.** Defines `buildParams`, `coerceField`, `fieldFor`, `loadList`, `mountSoltuiPanel`, `renderForm`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/ui-kit.js`

`code-js` · 186 lines · 8,123 B · description: **extracted**

**Purpose.** Shared helpers for the dashboard views: DOM building, number formatting, tables, chips and a small SVG line chart. Every string that reaches the page goes through textContent or a DOM attribute, never innerHTML. Token names, pool symbols, venue errors and soltui output are third-party data, and these pages hold extension privileges (KNOW-407): one missed escape would be XSS with real reach.

**Contents.** Defines `SOURCE_CHIP`, `SVG`, `ago`, `amount`, `call`, `chip`, `clear`, `el`, `guard`, `lineChart` and 5 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/ui.css`

`code-web` · 270 lines · 13,059 B · description: **curated**

**Purpose.** Shared styling for both surfaces, kept in one file so the popup and dashboard cannot drift visually.

**Use.** Linked by the HTML; nothing to run.

#### `extension/src/ui/view-grid.js`

`code-js` · 375 lines · 13,422 B · description: **extracted**

**Purpose.** Grid view: the Jupiter ladder grid's configuration, risk rails, journal and P&L. Moved off the front page in the 0.3.0 redesign because the strategy loses to buy-and-hold walk-forward (Stele KNOW-605); the behaviour is unchanged. The equity curve is drawn with the vendored Lightweight Charts library (src/ui/charts.js; local file, because MV3 forbids remote code).

**Contents.** Defines `PAD`, `appendRow`, `emptyRow`, `equitySvg`, `fillForm`, `ladderSvg`, `mountGrid`, `readForm`, `refreshGrid`, `renderBanner` and 4 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/view-markets.js`

`code-js` · 222 lines · 12,757 B · description: **extracted**

**Purpose.** Holdings, Profit & loss and Discover views. Holdings come from the extension's own read-only market reads (holdings); the deeper scan, snapshots, P&L history and the Aero scout come from soltui. Every figure keeps its source label: a quoted APY is never shown as income.

**Contents.** Defines `chainCard`, `mountDiscover`, `mountHoldings`, `mountPnl`, `pnlSection`, `refreshHoldings`, `refreshPnl`, `refreshPools`, `refreshScout`, `renderHoldings`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/view-overview.js`

`code-js` · 150 lines · 7,548 B · description: **extracted**

**Purpose.** Overview and Alerts views. The overview paints from the stored scan first (instant, no network), then refreshes holdings live. Alerts come from the background scan (scanAlerts, src/core/alerts.js); this page only shows and acknowledges them.

**Contents.** Defines `SEVERITY_LABEL`, `alertCard`, `holdingsKpis`, `lpKpi`, `mountAlertPrefs`, `renderAlerts`, `renderOverview`, `scoutTable`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/view-trade.js`

`code-js` · 277 lines · 12,477 B · description: **extracted**

**Purpose.** Backtest & strategies and Swap views. Strategy work runs in soltui (the backtester is Python): Top 5 evidence, the roster, CPCV sweeps and signal defaults. Swaps are quotes from the extension's registry (swapQuote); signing happens on the venue page (Stele KNOW-837).

**Contents.** Defines `backtestRows`, `fillTokenSelects`, `loadCatalogue`, `loadHistory`, `loadRoster`, `loadSignals`, `loadTop5`, `mountStrategies`, `mountSwap`, `pollStatus` and 4 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/ui/wallet-pubkey.js`

`code-js` · 74 lines · 2,965 B · description: **extracted**

**Purpose.** "Use soltui Solana address": fill the Wallet pubkey field from the address saved in soltui. The address comes through the same bridge as every other soltui call: the page sends `soltuiCall` for the read-only `wallet.addresses` command, which returns the public Solana and EVM addresses and nothing else (never an extended public key, never key material).

**Contents.** Defines `B58`, `fetchSolanaAddress`, `isSolanaPubkey`, `mountWalletPubkeyButton`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/venues/`

#### `extension/src/venues/index.js`

`code-js` · 257 lines · 9,103 B · description: **extracted**

**Purpose.** Venue layer. The grid engine is venue-agnostic: it emits intents, and a venue adapter turns them into orders. That seam exists because the two candidate venues on Jupiter are in very different states of readiness: Trigger V2 — REST, returns signable transactions. Live-capable today. SPOT. Perps — NO public REST write API as of 2026-08-04.

**Contents.** Defines `MODE`, `buildVenue`, `class DryRunVenue`, `class NotImplemented`, `class PerpsVenueReadOnly`, `leverageFeasibility`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/venues/triggerVenue.js`

`code-js` · 520 lines · 20,938 B · description: **extracted**

**Purpose.** Jupiter Trigger V2 venue adapter. Live writes require a trusted semantic-verification signing bridge. The bundled raw session-key signer does not provide one, so it cannot sign remote-crafted money movements. A grid is a ladder of resting price orders, which is exactly what this API is for, and V2 keeps pending orders off-chain so the ladder is not a public roadmap for front-runners.

**Contents.** Defines `MARGIN_SOURCE`, `ORDER_LIST_KEYS`, `ORDER_REQUIRED_FIELDS`, `class OrderEnvelopeError`, `class TriggerVenue`, `normaliseOrders`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/src/wallet/`

#### `extension/src/wallet/signer.js`

`code-js` · 319 lines · 11,960 B · description: **extracted**

**Purpose.** Signing. Three honest modes, because "unattended bot" and "wallet popup per trade" are mutually exclusive and pretending otherwise ships a broken default: DRY_RUN nothing is ever signed. The signer throws if asked. SEMI_AUTO the worker prepares the transaction and queues it; a human approves each one in the dashboard. Safe, not unattended.

**Contents.** Defines `IV_BYTES`, `KDF_ITERATIONS`, `KEY_BINDING_MESSAGE`, `PENDING_KEY`, `PKCS8_ED25519_PREFIX`, `SALT_BYTES`, `SIGNER_KIND`, `VAULT_KEY`, `base64UrlToBytes`, `class NullSigner` and 10 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/src/wallet/solana.js`

`code-js` · 225 lines · 7,839 B · description: **extracted**

**Purpose.** Minimal Solana wire-format helpers. Hand-rolled instead of pulling in @solana/web3.js because the extension needs exactly two things — base58 and inserting a signature into an already-built transaction — and shipping a megabyte of bundled dependencies into a service worker for that is a poor trade. The transaction itself is always built by Jupiter; we never construct instructions.

**Contents.** Defines `B58_ALPHABET`, `B58_MAP`, `CHUNK`, `base58Decode`, `base58Encode`, `base64ToBytes`, `bytesToBase64`, `decodeShortVec`, `encodeShortVec`, `messageSigners` and 3 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/test/`

#### `extension/test/accounting-audit.test.js`

`code-js` · 35 lines · 1,879 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/alerts.test.js`

`code-js` · 316 lines · 18,301 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `NOW`, `deps`, `soltuiStub`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/api-audit.test.js`

`code-js` · 42 lines · 1,845 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/autoreload.test.js`

`code-js` · 194 lines · 8,353 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `rig`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/blind-core-audit.test.js`

`code-js` · 104 lines · 6,923 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `setup`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/charts.test.js`

`code-js` · 157 lines · 5,561 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `POINTS`, `VENDOR`, `fakeElement`, `fakeLib`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/core.test.js`

`code-js` · 1555 lines · 61,740 B · description: **curated**

**Purpose.** Node test-runner suite for the pure core — grid maths, planner, reconciler. No `chrome.*`, so it runs headless.

**Contents.** Defines `CONFIG`, `LINK_CONFIG`, `ORDER`, `RC_CONFIG`, `RECON_CONFIG`, `STATE`, `seedResting`, `seedUnknown`.

**Use.** `node --test extension/test/` or `npm test` in `extension/`.

#### `extension/test/e2e-harness.test.js`

`code-js` · 66 lines · 3,192 B · description: **extracted**

**Purpose.** The browser e2e (tools/e2e.mjs) cannot run under `node --test`: it needs Chrome for Testing. What can be tested without a browser is the part that makes it safe.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/engine-command-audit.test.js`

`code-js` · 247 lines · 14,178 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `setup`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/final-gate-audit.test.js`

`code-js` · 52 lines · 2,499 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `context`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/grid-audit.test.js`

`code-js` · 12 lines · 518 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/http-audit.test.js`

`code-js` · 53 lines · 2,326 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/market.test.js`

`code-js` · 377 lines · 21,757 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `MID`, `MID75`, `OWNER`, `PRICE_MID`, `SOL_OWNER`, `USDC`, `baseRpc`, `slipstreamRpc`, `stubFetch`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/node-deps-audit.test.js`

`code-js` · 25 lines · 1,099 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/risk-audit.test.js`

`code-js` · 47 lines · 2,043 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/service-worker.test.js`

`code-js` · 242 lines · 10,359 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/session-key-form.test.js`

`code-js` · 51 lines · 2,137 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/soltui-bridge.test.js`

`code-js` · 281 lines · 14,607 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `HOST`, `fakePort`, `fakeTransport`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/soltui-panel.test.js`

`code-js` · 84 lines · 5,178 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `ROOT`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/soltui-parity.test.js`

`code-js` · 116 lines · 6,553 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `HOST`, `ROOT`, `TOKEN`, `everySurface`, `withApi`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/surfaces.test.js`

`code-js` · 469 lines · 18,523 B · description: **curated**

**Purpose.** Covers the command registry as driven by each surface (popup, dashboard, CLI), so one registry change cannot silently break one caller.

**Contents.** Defines `CLI`, `ROOT`, `TOKEN`, `run`, `testDeps`, `withServer`.

**Use.** `node --test extension/test/`.

#### `extension/test/trigger-audit.test.js`

`code-js` · 101 lines · 5,608 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `BASE`, `QUOTE`, `venue`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/venues.test.js`

`code-js` · 97 lines · 4,474 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `CONFIG`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/version.test.js`

`code-js` · 27 lines · 1,259 B · description: **extracted**

**Purpose.** The manifest version is what the owner sees in chrome://extensions and in the popup header. A change that ships without bumping it looks like no change at all (2026-11-07: the SolTUI panel shipped as 0.1.0 and read as "nothing changed"). CI also fails a pull request that edits src/ or manifest.json without bumping the version; this test keeps the two version fields in step.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/wallet-audit.test.js`

`code-js` · 204 lines · 10,343 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `transaction`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/wallet-pubkey.test.js`

`code-js` · 134 lines · 6,692 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `EVM`, `ROOT`, `SOL`, `bridge`, `fakeRoot`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/test/wallet.test.js`

`code-js` · 252 lines · 9,200 B · description: **curated**

**Purpose.** Wallet and signing path tests, including the refusals — the cases that must NOT produce a transaction.

**Contents.** Defines `SOL_MINT`, `SYSTEM_PROGRAM`, `USDC_MINT`, `concat`, `fakeTx`.

**Use.** `node --test extension/test/`.

### `extension/tools/`

#### `extension/tools/api-server.js`

`code-js` · 260 lines · 9,402 B · description: **extracted**

**Purpose.** HTTP API surface. Routes are generated from the registry in src/core/commands.js — the same registry the CLI and the extension use — so no endpoint can drift from the extension's behaviour.

**Contents.** Defines `MAX_BODY_BYTES`, `coerceQuery`, `createApiServer`, `createRequestHandler`, `main`, `parseArgs`, `readJsonBody`, `send`, `tokenMatches`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/cli.js`

`code-js` · 217 lines · 6,971 B · description: **extracted**

**Purpose.** CLI surface. Every command is generated from the registry in src/core/commands.js, so this file contains no per-command logic and cannot fall behind the extension. Add a command there and it appears here, in the help text, and in the HTTP API.

**Contents.** Defines `GLOBAL_FLAGS`, `coerce`, `commandHelp`, `helpText`, `main`, `parseArgv`, `render`, `summariseSkips`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/deps.js`

`code-js` · 94 lines · 3,525 B · description: **extracted**

**Purpose.** Node dependency wiring for the command registry. The CLI and the HTTP API share this so they behave identically — the only difference between the two surfaces is how arguments arrive. Kept out of src/ because it imports node:fs, which would break the extension bundle if it were ever pulled into a browser context.

**Contents.** Defines `createNodeDeps`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/dryrun.js`

`code-js` · 163 lines · 6,054 B · description: **extracted**

**Purpose.** Headless dry run. Runs the real tick — real Jupiter price, real grid engine, real risk rails, real journal — with simulated fills, in Node. This is the integration gate: loading an unpacked extension cannot be automated (chrome://extensions needs a human), so end-to-end verification happens here instead.

**Contents.** Defines `class ScriptedPriceVenue`, `main`, `parseArgs`, `round`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/e2e.mjs`

`code-js` · 554 lines · 28,372 B · description: **extracted**

**Purpose.** Real-browser end-to-end check. Loads the unpacked extension into Chrome for Testing, drives the real service worker, popup and dashboard over the DevTools pipe, and asserts what a human would otherwise have to click through at chrome://extensions.

**Contents.** Defines `CANARY`, `EXT`, `MARKET_GETS`, `READ_RPC`, `RPC_ORIGINS`, `SOL`, `STUB_PRICE`, `USDC`, `assert`, `check` and 5 more.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/measure-recentre.js`

`code-js` · 160 lines · 6,399 B · description: **extracted**

**Purpose.** How often does the shipped auto-recentre gate actually open? node tools/measure-recentre.js --csv ../data/SOL_1d.csv `recentreDecision()` refuses to move the ladder while anything is resting or any lot is open, because `tick()` cannot cancel. That gate is deliberately tight, and the honest question is whether it is so tight the feature never fires.

**Contents.** Defines `closeColumn`, `main`, `parseArgs`, `recordingVenue`, `run`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/soltui-transport.js`

`code-js` · 122 lines · 5,597 B · description: **extracted**

**Purpose.** Node transport to the soltui native messaging host. The extension's CLI (tools/cli.js) and HTTP API (tools/api-server.js) reach soltui the same way the browser does: by running the native host and speaking Chrome's framing, a 4-byte little-endian length then UTF-8 JSON, on its stdio.

**Contents.** Defines `HOST_ENV`, `MAX_FRAME_BYTES`, `REPO_ROOT`, `createNodeSoltuiTransport`, `decodeFrame`, `defaultHostCommand`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

#### `extension/tools/verify-endpoints.js`

`code-js` · 80 lines · 3,155 B · description: **extracted**

**Purpose.** Live endpoint check. Confirms the read-side assumptions this extension hardcodes still hold, so a Jupiter API change surfaces here rather than mid-tick. Read-only: nothing is signed, deposited, or ordered. node tools/verify-endpoints.js JUPITER_API_KEY=... node tools/verify-endpoints.js # also checks the keyed tier

**Contents.** Defines `MINTS`, `checkPrice`, `checkTriggerReachable`, `report`.

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

### `extension/vendor/lightweight-charts/`

#### `extension/vendor/lightweight-charts/LICENSE`

`other` · 202 lines · 11,347 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `extension/vendor/lightweight-charts/NOTICE`

`other` · 3 lines · 101 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `extension/vendor/lightweight-charts/README.md`

`doc` · 35 lines · 2,025 B · description: **extracted**

**Purpose.** The extension's one runtime library. The owner chose it on 2026-11-07 (Stele KNOW-859) over TradingView Advanced Charts, whose licence covers public, attributed websites only (`docs/TRADINGVIEW-REFERENCE.md`, "Licensing and what stays out of git").

**Use.** Read it.

#### `extension/vendor/lightweight-charts/lightweight-charts.standalone.production.mjs`

`code-js` · 8 lines · 197,827 B · description: **none**

**Purpose.** _No description available._

**Use.** Loaded by the extension; see `extension/manifest.json` for entry points.

---

## soltui

The macOS menu-bar app that surfaces state locally. Packaged with py2app and supervised by launchd.

88 files.

#### `soltui/README.md`

`doc` · 434 lines · 33,643 B · description: **extracted**

**Purpose.** A sixteen-tab Textual TUI plus a macOS menu-bar indicator over the backtester. Structured like `~/dev/net-dns-monitor`: pure, tested logic modules with a thin wiring shell.

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

`code-python` · 272 lines · 11,288 B · description: **extracted**

**Purpose.** What every strategy, signal and indicator said about one coin at one moment. Pure logic behind the Analyze tab. No Textual import, no widget. ## It wraps `research/decide.py`; it does not reimplement it `decide.py`'s one substantive guarantee is that the exposures it reports are the numbers the engine would have acted on.

**Contents.** Defines `REPO`, `DATA_DIR`, `class Series`, `class Analysis`, `available_assets()`, `load_series()`, `parse_as_of()`, `slice_to()`, `_prepare()`, `_first_close()` and 2 more. Depends on `backtester`, `research`.

**Use.** `import soltui.analyze`

#### `soltui/api.py`

`code-python` · 203 lines · 8,302 B · description: **extracted**

**Purpose.** HTTP surface: `soltui api [--port N]`. Stdlib `http.server`; mirrors extension/tools/api-server.js. GET /v1/health liveness, no auth GET /v1/commands the `list` envelope GET /v1/<command>?a=1 read-only commands, args from the query string POST /v1/<command> any command, args from a JSON object body Command routes return the registry envelope exactly as `commands.dumps` renders it, so the body is b

**Contents.** Defines `HOST`, `DEFAULT_PORT`, `MAX_BODY_BYTES`, `_ROUTE`, `_STATUS`, `support_dir()`, `token_path()`, `load_token()`, `token_matches()`, `make_handler()` and 2 more.

**Use.** `python3 soltui/api.py --help`

#### `soltui/app.py`

`code-python` · 284 lines · 11,787 B · description: **extracted**

**Purpose.** macOS menu-bar shell. Thin by design. python3 -m soltui.app Mirrors `netdnsmonitor/app.py`: every decision lives in already-tested modules (`status`, `config`, `roster`, `runner`), and this file only wires them to a `rumps.Timer` and a status-item title.

**Contents.** Defines `REPO`, `RESULTS_DIR`, `_wait_for_port()`, `_rumps()`, `build_app()`, `main()`.

**Use.** `python3 soltui/app.py --help`

#### `soltui/bgcontrol.py`

`code-python` · 515 lines · 20,511 B · description: **extracted**

**Purpose.** Start, stop and inspect the background sweep process. Separated from `bgqueue` (which is pure logic) and from `bgworker` (which is the work) because process lifecycle is the part with the OS-specific behaviour, and keeping it in one small module is what lets the other two stay testable.

**Contents.** Defines `LOCK_PATH`, `LOCK_FD_ENV`, `CONTROL_FD_ENV`, `TASKPOLICY_PATHS`, `taskpolicy_path()`, `taskpolicy_available()`, `describe_priority()`, `read_pid()`, `acquire_lock()`, `inherited_lock()` and 10 more.

**Use.** `import soltui.bgcontrol`

#### `soltui/bgqueue.py`

`code-python` · 914 lines · 35,544 B · description: **extracted**

**Purpose.** Job queue for the background backtest sweep. Pure logic; no UI, no processes. The TUI's own sweep (`runner.py`) evaluates the roster and blocks a thread until it finishes.

**Contents.** Defines `BG_DIR`, `RESULTS_PATH`, `STATE_PATH`, `PID_PATH`, `ASSET_RE`, `MIN_TRADES`, `HORIZON_INTERVAL`, `LIKELIHOOD_ORDER`, `_UNKNOWN_LIKELIHOOD`, `class Job` and 30 more. Depends on `backtester`.

**Use.** `import soltui.bgqueue`

#### `soltui/bgworker.py`

`code-python` · 579 lines · 21,839 B · description: **extracted**

**Purpose.** The background backtest worker: a separate, low-priority process. python3 -m soltui.bgworker --asset SOL python3 -m soltui.bgworker --asset SOL --horizons medium --max-tier 1 --limit 50 Run directly it is a normal foreground script; the TUI launches it through `bgcontrol.start()`, which is what applies the background scheduling policy.

**Contents.** Defines `REPO`, `NICE_LEVEL`, `evaluation_code_fingerprint()`, `_file_hash()`, `evaluation_proof()`, `verify_evaluation_proof()`, `_validate_limit()`, `_limit_argument()`, `class EvaluationContextChanged`, `_check_price_input()` and 8 more. Depends on `backtester`.

**Use.** `python3 soltui/bgworker.py --help`

#### `soltui/cli.py`

`code-python` · 73 lines · 2,967 B · description: **extracted**

**Purpose.** Command-line surface: `soltui call <name> [--param k=v ...] [--json '{...}']` and `soltui list`. Prints the registry envelope (`commands.dumps`) on stdout, one line, and exits 0 when `ok` else 1. No logic of its own: parsing arguments into params is all it does; `dispatch` does the rest, including the call log.

**Contents.** Defines `_build_parser()`, `params_from_args()`, `main()`.

**Use.** `python3 soltui/cli.py --help`

#### `soltui/commands.py`

`code-python` · 2013 lines · 94,614 B · description: **extracted**

**Purpose.** The soltui command registry: one set of calls for the TUI, CLI, HTTP API and native host. Every action the console can take is a registered `Command`. Every surface goes through `dispatch(name, params, surface)`, which validates parameters, applies the confirm gate, runs the handler, wraps the outcome in the response envelope and appends one line to the call log.

**Contents.** Defines `REPO`, `UNTESTED_SWEEP_TIMEOUT_S`, `DOCS_TABLE_CAP`, `ERROR_CODES`, `PARAM_TYPES`, `LOG_ROTATE_BYTES`, `untested_sweep_command()`, `failure_summary()`, `class CommandError`, `class Param` and 30 more. Depends on `backtester`.

**Use.** `import soltui.commands`

#### `soltui/compound.py`

`code-python` · 1973 lines · 96,950 B · description: **extracted**

**Purpose.** Compound five-minute tester: saved configuration, live reads, forward ledger, sweeps. python3 -m soltui.compound signal --asset SOL # score now, explain every metric python3 -m soltui.compound forward --asset SOL --loop # record a call per closed 5m bar python3 -m soltui.compound status --asset SOL # forward-test hit rates python3 -m soltui.compound backtest --asset SOL # compound + each component

**Contents.** Defines `REPO`, `COINBASE_CANDLES`, `HYPERLIQUID_INFO`, `NEWS_FEEDS`, `USER_AGENT`, `LIVE_BARS`, `ADAPTIVE_LIVE_BARS`, `HTTP_TIMEOUT`, `class CompoundError`, `home()` and 30 more. Depends on `backtester`.

**Use.** `python3 soltui/compound.py --help`

#### `soltui/compound_agent.py`

`code-python` · 150 lines · 5,809 B · description: **extracted**

**Purpose.** Install, remove or inspect the compound 5m autopilot LaunchAgent. python -m soltui.compound_agent install [--python P] [--repo R] [--no-start] python -m soltui.compound_agent uninstall python -m soltui.compound_agent status The job is `com.mitchhudson.soltui.compound-autopilot`: every five minutes (and once at load) it runs `python -m soltui.compound autopilot` from the repo root.

**Contents.** Defines `LABEL`, `INTERVAL_S`, `DEFAULT_PYTHON`, `REPO`, `agents_dir()`, `plist_path()`, `log_path()`, `is_worktree()`, `plist_dict()`, `_launchctl()` and 5 more.

**Use.** `python3 soltui/compound_agent.py --help`

#### `soltui/config.py`

`code-python` · 233 lines · 10,270 B · description: **extracted**

**Purpose.** Settings load/save for the TUI. Pure logic; no UI, no I/O beyond one file. Config lives at `~/.config/soltui/config.yaml`, following the same convention as `netdnsmonitor`. YAML is optional at runtime -- if PyYAML is missing the app falls back to JSON at the same path with a `.json` suffix, so a missing optional dependency degrades rather than crashes.

**Contents.** Defines `CONFIG_DIR`, `CONFIG_PATH`, `CONFIG_PATH_JSON`, `INTERVALS`, `XPUB_FIELDS`, `MODES`, `class ConfigError`, `class Settings`, `default_settings()`, `validate()` and 4 more.

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

#### `soltui/eth_scan.py`

`code-python` · 99 lines · 5,062 B · description: **extracted**

**Purpose.** Ethereum mainnet (L1) holdings of one public address: native ETH plus a well-known token list. `base_address` in Settings is the same EVM key viewed on Base; `eth_address` is the mainnet view. Reads only: `eth_getBalance` and `balanceOf` over public JSON-RPC, USD prices from Coinbase. There is no indexer here, so a token that is not in `TOKENS` is not discovered, and the scan says so.

**Contents.** Defines `ETH_RPCS`, `EXPLORER`, `scan_ethereum()`.

**Use.** `import soltui.eth_scan`

#### `soltui/forwardtest.py`

`code-python` · 317 lines · 14,607 B · description: **extracted**

**Purpose.** Prospective, paper-only trials of registered strategies on closed Coinbase minutes.

**Contents.** Defines `HORIZONS`, `HISTORY`, `WARM_REPLAY`, `KNOBS`, `revision()`, `_json()`, `_db()`, `_factory()`, `member()`, `neighbours()` and 5 more. Depends on `backtester`.

**Use.** `import soltui.forwardtest`

#### `soltui/hdwallet.py`

`code-python` · 370 lines · 14,784 B · description: **extracted**

**Purpose.** Public-key-only BIP32 derivation and address encoding. Stdlib only, no private keys anywhere. An extended PUBLIC key (xpub and its SLIP-132 cousins) is enough to derive every receive and change address of a wallet, so the console can watch a wallet without ever holding anything that can spend.

**Contents.** Defines `_P`, `_N`, `_G`, `_add()`, `_mul()`, `_decompress()`, `_compress()`, `_ALPHABET`, `_INDEX`, `b58encode()` and 26 more.

**Use.** `import soltui.hdwallet`

#### `soltui/help.py`

`code-python` · 561 lines · 81,266 B · description: **extracted**

**Purpose.** Plain-language help shared by hover tooltips and the F1 reference.

**Contents.** Defines `HEADER_GLOSSARY`, `TAB_HELP`, `SETTING_HELP`, `SIGNAL_HELP`, `CONTROL_HELP`, `TERMS`, `column_help()`, `control_help()`, `row_help()`.

**Use.** `import soltui.help`

#### `soltui/help_screen.py`

`code-python` · 68 lines · 3,060 B · description: **extracted**

**Purpose.** Keyboard-accessible, scrollable counterpart of the hover help.

**Contents.** Defines `class HelpScreen`.

**Use.** `import soltui.help_screen`

#### `soltui/liquidity.py`

`code-python` · 601 lines · 20,353 B · description: **extracted**

**Purpose.** Liquidity tab logic: read the Aero LP daemon's state files, format them. Pure, stdlib-only, and read-only with one exception. The liquidity daemon (`liquidity/`, `aero-lp daemon`) writes `status.json` and `scout.json`; this module only reads them. The single write is the `KILL` switch file, which `set_kill()` creates or deletes. The contract is `liquidity/STATE_FILES.md`.

**Contents.** Defines `STATUS_SCHEMA`, `SCOUT_SCHEMA`, `STATUS_FILE`, `SCOUT_FILE`, `KILL_FILE`, `ENV_HOME`, `DEFAULT_HOME`, `REFRESH_SECONDS`, `STALE_AFTER_SECONDS`, `SCOUT_ROWS` and 30 more.

**Use.** `import soltui.liquidity`

#### `soltui/live_run.py`

`code-python` · 123 lines · 4,680 B · description: **extracted**

**Purpose.** Live Run dashboard for SolTUI. Loads the best configuration from TOP5-RECOMMENDATION (or untested sweep) and provides a UI to launch the Node.js extension in dry-run mode.

**Contents.** Defines `REPO`, `RECOMMENDATION_FILE`, `get_best_strategy()`, `run_dryrun()`, `_CAPITAL_RE`, `_TICK_NET_RE`, `dryrun_net_pct()`, `spawn_dryrun()`. Depends on `backtester`.

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

#### `soltui/native_host.py`

`code-python` · 154 lines · 5,915 B · description: **extracted**

**Purpose.** Chrome native-messaging host `com.mitchhudson.soltui`: the extension's door into the registry. Speaks Chrome's framing on stdio: a 4-byte little-endian length, then that many bytes of UTF-8 JSON. It serves many requests per connection (`connectNative`) or one (`sendNativeMessage`).

**Contents.** Defines `HOST_NAME`, `PROTOCOL`, `MAX_REPLY_BYTES`, `MAX_REQUEST_BYTES`, `OVERSIZE_MESSAGE`, `class FrameError`, `read_frame()`, `write_frame()`, `extension_dir()`, `build_hash()` and 4 more.

**Use.** `python3 soltui/native_host.py --help`

#### `soltui/native_host_install.py`

`code-python` · 149 lines · 6,099 B · description: **extracted**

**Purpose.** Install, remove or inspect the native-messaging host registration. python -m soltui.native_host_install install [--python P] [--repo R] [--extra-id ID ...] [--dir D ...] python -m soltui.native_host_install uninstall python -m soltui.native_host_install status `install` writes an executable wrapper (absolute paths, no arguments, which is what Chrome requires of a manifest `path`) that runs the con

**Contents.** Defines `EXTENSION_ID`, `DEFAULT_PYTHON`, `REPO`, `BROWSERS`, `support_root()`, `wrapper_path()`, `browser_host_dirs()`, `allowed_origins()`, `wrapper_text()`, `manifest()` and 4 more.

**Use.** `python3 soltui/native_host_install.py --help`

#### `soltui/netpct.py`

`code-python` · 41 lines · 1,694 B · description: **extracted**

**Purpose.** Net percentage growth or decline, always with the word that names its source. One definition for every results view: `final / initial - 1`, as a signed fraction. A bare "+9.4%" reads as "my money is up", and most figures in this package are simulations, so the text form never leaves the source word off.

**Contents.** Defines `SOURCES`, `net_pct()`, `fmt()`, `labelled()`.

**Use.** `import soltui.netpct`

#### `soltui/paper.py`

`code-python` · 198 lines · 6,741 B · description: **extracted**

**Purpose.** Dry-run simulator for the Execute tab. ## Why this is a replay and not a live loop The obvious design -- step forward bar by bar and compute fills as you go -- would create a SECOND order-execution path alongside `backtester/core/engine.py`.

**Contents.** Defines `MODE_LABEL`, `class IntendedFill`, `class PaperSession`, `start_session()`. Depends on `backtester`.

**Use.** `import soltui.paper`

#### `soltui/pnl.py`

`code-python` · 688 lines · 31,138 B · description: **extracted**

**Purpose.** Profit and loss over a variable window: the maths behind the P&L tab. Pure functions over plain data, so every figure can be checked with a fixture and no event loop, network or price file.

**Contents.** Defines `UTC`, `DAY_S`, `PRESETS`, `DEFAULT_PRESET`, `_PRESET_SECONDS`, `SOURCES`, `GROUPS`, `SOURCE_ALIASES`, `NOTICE`, `LP_WORDS` and 30 more.

**Use.** `import soltui.pnl`

#### `soltui/portfolio.py`

`code-python` · 307 lines · 13,314 B · description: **extracted**

**Purpose.** Portfolio monitoring: timestamped per-chain snapshots, the changes between them, and a notice line. A snapshot is one line of `snapshots.jsonl` under `~/Library/Application Support/soltui/portfolio/` (mode 600). It holds per-chain balances by symbol, a USD value, the prices used and the script types an xpub scan found.

**Contents.** Defines `SNAPSHOT_FILE`, `SEEN_FILE`, `FETCH_BUDGET_S`, `MAX_NOTICE_ITEMS`, `support_dir()`, `portfolio_dir()`, `snapshots_path()`, `LAST_SCAN_FILE`, `last_scan_path()`, `save_last_scan()` and 17 more.

**Use.** `python3 soltui/portfolio.py --help`

#### `soltui/portfolio_agent.py`

`code-python` · 131 lines · 4,813 B · description: **extracted**

**Purpose.** Install, remove or inspect the hourly portfolio-snapshot LaunchAgent. python -m soltui.portfolio_agent install [--python P] [--repo R] [--no-start] python -m soltui.portfolio_agent uninstall python -m soltui.portfolio_agent status The job is `com.mitchhudson.soltui.portfolio`: once an hour (and once at load) it runs `python -m soltui.cli call portfolio.snapshot` from the repo root, so it goes thro

**Contents.** Defines `LABEL`, `INTERVAL_S`, `DEFAULT_PYTHON`, `REPO`, `agents_dir()`, `plist_path()`, `log_path()`, `plist_dict()`, `_launchctl()`, `domain()` and 4 more.

**Use.** `python3 soltui/portfolio_agent.py --help`

#### `soltui/presets.py`

`code-python` · 120 lines · 5,276 B · description: **extracted**

**Purpose.** The Top 5 configurations as ready-to-use presets for Analyze, Live Run and Execute. `top5.py` reads the committed evidence; this module turns each row into something a tab can apply with one click, from one place, so every surface (TUI, CLI, API, extension) sees the same list.

**Contents.** Defines `PREFIX`, `preset_value()`, `parse_value()`, `_horizons()`, `build_presets()`, `find_preset()`, `build_strategy()`, `load_preset_arrays()`. Depends on `backtester`, `research`.

**Use.** `import soltui.presets`

#### `soltui/reference.py`

`code-python` · 87 lines · 5,483 B · description: **extracted**

**Purpose.** Static reference content for the Research and Signals tabs. Kept out of `tui.py` so the command registry (`research.get`, `signals.reference`) can serve the same data to every surface without importing Textual.

**Contents.** Defines `RESEARCH_DRIVERS`, `RESEARCH_FINDINGS`, `FAMILY_NOTES`, `SIGNAL_REFERENCE`.

**Use.** `import soltui.reference`

#### `soltui/requirements.txt`

`data` · 35 lines · 1,862 B · description: **curated**

**Purpose.** Runtime dependencies for the menu-bar app (rumps/pyobjc and the py2app build tooling).

**Use.** `python3 -m pip install -r soltui/requirements.txt`.

#### `soltui/roster.py`

`code-python` · 165 lines · 5,965 B · description: **extracted**

**Purpose.** The user's strategy roster: which strategies are active, with what parameters. Backs the Strategies tab. Kept pure so add/remove is testable without a UI. Two invariants worth stating, because both prevent a class of confusing failure later rather than at the point of the mistake: 1.

**Contents.** Defines `class RosterError`, `class RosterEntry`, `class Roster`, `available_strategies()`. Depends on `backtester`.

**Use.** `import soltui.roster`

#### `soltui/runner.py`

`code-python` · 288 lines · 9,745 B · description: **extracted**

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

`code-python` · 369 lines · 15,557 B · description: **extracted**

**Purpose.** Editable signal parameters: the tunables behind the Signals tab. ## The model, because it needs to be unambiguous A *signal* is an indicator with a period or threshold (RSI's period, Bollinger's width, MACD's spans). A *strategy* is a rule built on one or more signals. The same signal is shared by several strategies -- `rsi` and any composite containing it both read the RSI period.

**Contents.** Defines `class SignalError`, `class SignalDefaults`, `validate()`, `params_for()`, `merged_params()`, `field_names()`, `coerce()`, `from_dict()`, `mapped_strategies()`.

**Use.** `import soltui.signals`

#### `soltui/soltui-service`

`other` · 405 lines · 16,240 B · description: **curated**

**Purpose.** Install-and-supervise script for the menu-bar app: builds the py2app bundle, writes the launchd agent, and manages the flag file that is the real off switch (because `KeepAlive` necessarily overrides the app's own Quit item).

**Use.** `python3 soltui/soltui-service status|start|stop|build`.

#### `soltui/spot_prices.py`

`code-python` · 37 lines · 1,582 B · description: **extracted**

**Purpose.** USD spot prices from Coinbase's public endpoint (no key). A price it cannot give is None, never 0. `https://api.coinbase.com/v2/prices/<SYMBOL>-USD/spot` answers `{"data": {"amount": "76021.455"}}`. A symbol Coinbase does not list answers an error body; that, a network failure and a non-positive or non-finite amount all become None, so the caller reports the value as unknown instead of as zero.

**Contents.** Defines `COINBASE_SPOT`, `spot_prices()`.

**Use.** `import soltui.spot_prices`

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

`code-python` · 3774 lines · 188,192 B · description: **extracted**

**Purpose.** Textual TUI: the console over the backtester. python3 -m soltui.tui Tabs: Settings, Strategies, Signals, Backtest, Top 5, Execute (dry-run only), Analyze, Cumulative, Research, Docs. All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`, `status`); this file is presentation and wiring.

**Contents.** Defines `_mtime()`, `sort_key()`, `_pct()`, `_num()`, `DOCS_TABLE_CAP`, `class GlossaryTable`, `class VimTextArea`, `class CompoundTable`, `class EditorBar`, `class SolTuiApp` and 1 more. Depends on `backtester`.

**Use.** `python3 soltui/tui.py --help`

#### `soltui/utxo_scan.py`

`code-python` · 227 lines · 10,859 B · description: **extracted**

**Purpose.** Watch a Bitcoin, Litecoin or Dogecoin wallet from its extended PUBLIC key. Read-only, keyless. The xpub is turned into addresses on this machine (`hdwallet`). Only addresses are sent to the public explorers, never the xpub, and the derived addresses are never logged, printed or returned: a result carries counts and balances only. ## How a wallet is found * Chains 0 (receive) and 1 (change).

**Contents.** Defines `GAP_LIMIT`, `SATS`, `CHAIN_NAMES`, `ESPLORA`, `BLOCKCYPHER`, `BLOCKCYPHER_BATCH`, `class AddrStat`, `_int()`, `class EsploraBackend`, `class BlockCypherBackend` and 5 more.

**Use.** `import soltui.utxo_scan`

#### `soltui/wallet.py`

`code-python` · 848 lines · 43,405 B · description: **extracted**

**Purpose.** Read-only wallet discovery: what the owner's two public addresses hold, and where it lives. Nothing here can move funds. There is no key, no signature, no transaction and no write to a chain: only public JSON-RPC reads (`getBalance`, `getTokenAccountsByOwner`, `getProgramAccounts`, `eth_getBalance`, `eth_call` to `balanceOf`), the public Jupiter, DefiLlama and DexScreener price APIs, and, when it

**Contents.** Defines `LABEL`, `USER_AGENT`, `SOLANA_RPC`, `BASE_RPCS`, `JUPITER_PRICE`, `JUPITER_TOKENS`, `BLOCKSCOUT`, `LLAMA_PRICES`, `DEXSCREENER`, `TOKEN_PROGRAM` and 30 more.

**Use.** `import soltui.wallet`

### `soltui/bin/`

#### `soltui/bin/soltui`

`other` · 52 lines · 2,293 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

### `soltui/tests/`

#### `soltui/tests/__init__.py`

`test` · 19 lines · 740 B · description: **curated**

**Purpose.** Package marker for the app's tests. Empty.

**Contents.** Defines `_ROOT`.

**Use.** Nothing to run.

#### `soltui/tests/bridge_support.py`

`test` · 219 lines · 10,217 B · description: **extracted**

**Purpose.** Shared fixtures for the command-bridge tests: an isolated world and the four surface runners.

**Contents.** Defines `TOKEN`, `HEAVY`, `default_params()`, `class World`, `stub_heavy()`, `via_tui()`, `via_cli()`, `class ApiServer`, `via_api()`, `host_call()` and 1 more. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/bridge_support.py -q`

#### `soltui/tests/test_bgcontrol.py`

`test` · 234 lines · 9,675 B · description: **extracted**

**Purpose.** Tests for the background worker's process lifecycle. Two of these exist because the bug they describe actually shipped in an earlier draft of this module and only turned up when the worker was spawned for real: `taskpolicy` lives in /usr/sbin rather than /usr/bin, and the pidfile was written by the child late enough that Stop-after-Start found nothing to signal.

**Contents.** Defines `class TestTaskpolicyLookup`, `class TestStartReleasesTheLockOnFailure`, `class TestWorkerCommand`, `class TestFetchCommand`, `class TestPidfile`, `class TestLivenessLock`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgcontrol.py -q`

#### `soltui/tests/test_bgcontrol_identity.py`

`test` · 190 lines · 8,294 B · description: **extracted**

**Purpose.** Stop addresses a temporary worker instance, never a recorded process id.

**Contents.** Defines `class TestStopIdentity`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgcontrol_identity.py -q`

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

#### `soltui/tests/test_bgworker_audit.py`

`test` · 227 lines · 10,682 B · description: **extracted**

**Purpose.** Offline regression cases for provenance, lock handoff, and job budgets.

**Contents.** Defines `class TestEvaluationProof`, `class TestInheritedLock`, `class TestCLI`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bgworker_audit.py -q`

#### `soltui/tests/test_bridge_buttons.py`

`test` · 54 lines · 2,155 B · description: **extracted**

**Purpose.** Every TUI button is a registry command: a new button cannot skip the registry.

**Contents.** Defines `SRC`, `pressed_selectors()`, `class ButtonRegistryTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bridge_buttons.py -q`

#### `soltui/tests/test_bridge_parity.py`

`test` · 82 lines · 3,627 B · description: **extracted**

**Purpose.** One registry, four surfaces: the same call returns the same envelope bytes everywhere. Driven by the registry itself, so a command added tomorrow is covered the day it is registered (the way extension/test/surfaces.test.js covers the extension's registry).

**Contents.** Defines `class ParityTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bridge_parity.py -q`

#### `soltui/tests/test_bridge_surfaces.py`

`test` · 361 lines · 18,998 B · description: **extracted**

**Purpose.** Access, framing, logging and install behaviour of the command bridge.

**Contents.** Defines `class ConfirmGateTests`, `class ApiAccessTests`, `class NativeFramingTests`, `class LoggingTests`, `class ValidationTests`, `class InstallerTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_bridge_surfaces.py -q`

#### `soltui/tests/test_compound.py`

`test` · 1229 lines · 67,034 B · description: **extracted**

**Purpose.** Compound five-minute tester: saved config, live reads, forward ledger, and the tab.

**Contents.** Defines `T0`, `candles()`, `class Venue`, `autopiloted()`, `class TempConfig`, `class ConfigTests`, `class LiveReadTests`, `class ForwardLedgerTests`, `ADDR`, `USDC` and 16 more. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_compound.py -q`

#### `soltui/tests/test_docs_browser.py`

`test` · 147 lines · 6,034 B · description: **extracted**

**Purpose.** Tests for the Docs tab's editing guards. The load-bearing assertions are the refusals: a file under `research/results/` or not in the catalogue must never be writable, regardless of what the caller claims about it. Those are the properties a UI bug could silently violate, so they are asserted directly rather than left to code review.

**Contents.** Defines `_entry()`, `class IsEditableTests`, `class WriteDocumentTests`, `class ReadDocumentRealTextFlagTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_docs_browser.py -q`

#### `soltui/tests/test_docs_search.py`

`test` · 148 lines · 6,821 B · description: **extracted**

**Purpose.** Docs-tab index search: the `docs.search` commands and the lazy loading around them. The memory claim is the point: the keyword postings, the embedding matrix and the ~670 MB embedding model must not be loaded until someone searches, and must be releasable. Ollama and the idle indexer are patched out; nothing here embeds anything or starts a process.

**Contents.** Defines `REPO`, `forget_search()`, `class DocsSearchCommands`, `class DocsSearchTab`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_docs_search.py -q`

#### `soltui/tests/test_eth_scan.py`

`test` · 72 lines · 3,076 B · description: **extracted**

**Purpose.** Ethereum mainnet scan: native ETH, the built-in token list, Coinbase prices, partial results.

**Contents.** Defines `ADDR`, `class FakeEth`, `class EthScanTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_eth_scan.py -q`

#### `soltui/tests/test_forwardtest.py`

`test` · 187 lines · 8,863 B · description: **extracted**

**Purpose.** Prospective evidence, horizon isolation, and the roster keyboard workflow.

**Contents.** Defines `BASE`, `candles()`, `class ForwardEvidence`, `class ForwardPlan`, `class RosterForwardUI`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_forwardtest.py -q`

#### `soltui/tests/test_hdwallet.py`

`test` · 158 lines · 8,495 B · description: **extracted**

**Purpose.** BIP32 public derivation, address encoding and the refusal of private keys, on published test vectors. Every key here is a public test vector from BIP32 or BIP84, or is built in the test from filler bytes. None is a real wallet.

**Contents.** Defines `V2_M`, `V2_M0`, `V1_M0H`, `V1_M0H_1`, `BIP84_ZPUB`, `BIP84_RECEIVE`, `BIP84_CHANGE0`, `G`, `serialise()`, `class DerivationTests` and 2 more. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_hdwallet.py -q`

#### `soltui/tests/test_help.py`

`test` · 132 lines · 6,406 B · description: **extracted**

**Purpose.** Exercise help discovery and keyboard/mouse access without invoking actions.

**Contents.** Defines `class HelpTests`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_help.py -q`

#### `soltui/tests/test_launcher.py`

`test` · 73 lines · 2,449 B · description: **extracted**

**Purpose.** The `soltui` shell launcher (soltui/bin/soltui). A fake interpreter stands in for Python, so these tests check the launcher's own job — find the repo through a symlink, cd there, pick the module, pass arguments through — without starting Textual.

**Contents.** Defines `REPO`, `LAUNCHER`, `FAKE_PY`, `class LauncherTest`.

**Use.** `python3 -m pytest soltui/tests/test_launcher.py -q`

#### `soltui/tests/test_liquidity.py`

`test` · 581 lines · 27,044 B · description: **extracted**

**Purpose.** The Liquidity tab: loader tolerance, formatting, summary math, KILL toggle. The logic is in `soltui.liquidity` (pure); the last class mounts the real app against a fixture state dir. Fixtures follow `liquidity/STATE_FILES.md`. The load-bearing test is `test_every_percentage_column_carries_a_source_word`: a bare "+4.6%" under a header with no source reads as "my money is up".

**Contents.** Defines `NOW`, `TX1`, `TX2`, `status_doc()`, `scout_doc()`, `write()`, `class TestHome`, `class TestLoaderTolerance`, `class TestFormatting`, `class TestSummary` and 6 more. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_liquidity.py -q`

#### `soltui/tests/test_panes.py`

`test` · 263 lines · 11,679 B · description: **extracted**

**Purpose.** The four modules behind the new console tabs. No test here drives a terminal, opens a socket, or reads `data/`. That is the same split the rest of this package keeps: `tui.py` is presentation, and the logic lives in modules that can be tested without an event loop. The two worth reading first are `test_a_below_floor_row_is_never_rankable` and `test_slicing_happens_before_the_replay`.

**Contents.** Defines `write_index()`, `class DocsBrowserTests`, `class CumulativeTests`, `class AnalyzeTests`, `class ServeTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_panes.py -q`

#### `soltui/tests/test_pnl.py`

`test` · 406 lines · 20,458 B · description: **extracted**

**Purpose.** The P&L maths, on fixtures: window edges, costs, realized vs unrealized, drawdown, the no-data case. No test here reads a price file, a state file or the network. The numbers are small round ones so each expected value can be checked by hand.

**Contents.** Defines `UTC`, `at()`, `NOW`, `curve()`, `class WindowTests`, `class RunStatsTests`, `class SeriesTests`, `class DrawdownTests`, `class BestWorstTests`, `class TradeStatsTests` and 4 more. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_pnl.py -q`

#### `soltui/tests/test_portfolio.py`

`test` · 261 lines · 14,479 B · description: **extracted**

**Purpose.** Snapshots, balance changes, the notice line, the wallet value curve and the hourly LaunchAgent plist.

**Contents.** Defines `chain()`, `snap()`, `class DiffTests`, `class ValueCurveTests`, `class StorageAndNoticeTests`, `class LastScanTests`, `class SnapshotCommandTests`, `class AgentTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_portfolio.py -q`

#### `soltui/tests/test_presets_netpct.py`

`test` · 307 lines · 15,158 B · description: **extracted**

**Purpose.** Top 5 presets, the net % helper, and the P&L commands end to end on synthetic data. No price file, state file or network: the series is `SyntheticLoader`, the Top 5 evidence is a temp CSV, the liquidity home and journal are temp paths.

**Contents.** Defines `HEADER`, `ROWS`, `top5_csv()`, `class NetPctTests`, `class PresetTests`, `class DryRunNetTests`, `class CommandTests`, `class NoBareFiguresTests`. Depends on `backtester`, `research`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_presets_netpct.py -q`

#### `soltui/tests/test_service.py`

`test` · 176 lines · 7,350 B · description: **extracted**

**Purpose.** Tests for `soltui-service`, the LaunchAgent manager. The script is dash-named so that it reads as a command rather than a module, which means it cannot be imported normally; it is loaded by path below. What these cover is one failure that cost a debugging session: the agent plist sitting on disk while launchd knows nothing about it.

**Contents.** Defines `HAVE_SUPERVISOR`, `SKIP_REASON`, `REPO`, `SERVICE`, `load_service()`, `ok()`, `fail()`, `class ServiceTestCase`, `class StartLoadsTheAgent`, `class BuildNeedsALoadablePython`.

**Use.** `python3 -m pytest soltui/tests/test_service.py -q`

#### `soltui/tests/test_service_plist_parity.py`

`test` · 69 lines · 2,645 B · description: **extracted**

**Purpose.** The LaunchAgent plist soltui-service renders must not change. `soltui-service` used to build the plist itself; it now renders it through macos-launchd-supervisor.

**Contents.** Defines `HAVE_SUPERVISOR`, `SKIP_REASON`, `SERVICE`, `GOLDEN`, `load_service()`, `class PlistParity`.

**Use.** `python3 -m pytest soltui/tests/test_service_plist_parity.py -q`

#### `soltui/tests/test_signals.py`

`test` · 215 lines · 9,006 B · description: **extracted**

**Purpose.** Tests for editable signal parameters. The load-bearing property: **an explicit per-entry parameter always beats a signal default.** Getting that direction backwards would mean the Signals tab silently overwrites a value the user deliberately pinned in the Strategies tab, and the symptom would be a strategy quietly not doing what its own label says.

**Contents.** Defines `class TestPrecedence`, `class TestMapping`, `class TestValidation`, `class TestCoercion`, `class TestPersistence`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_signals.py -q`

#### `soltui/tests/test_status_roster.py`

`test` · 424 lines · 17,013 B · description: **extracted**

**Purpose.** Tests for the pure soltui layer: indicator title, settings, roster, replay. The load-bearing assertion in this file is that **no money figure in the menu-bar title is ever unlabelled**. A naked '+9.4%' in a status bar reads as a live account balance, and there is no live account. That property is asserted directly rather than left to code review.

**Contents.** Defines `class TestIndicatorTitle`, `class TestMenuSummary`, `class TestSettings`, `class TestRoster`, `class TestPaperSession`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_status_roster.py -q`

#### `soltui/tests/test_strategies_tab_history.py`

`test` · 105 lines · 4,910 B · description: **extracted**

**Purpose.** The Strategies tab as a user sees it: history columns and the three Backtest buttons.

**Contents.** Defines `cells()`, `class StrategiesTabHistory`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_strategies_tab_history.py -q`

#### `soltui/tests/test_strategy_history.py`

`test` · 223 lines · 11,401 B · description: **extracted**

**Purpose.** The Strategies tab's test history and its three Backtest buttons. History is derived from the background sweep's results file, so what it can get wrong is counting and choosing: a duplicate line counted as a second test, a best-of-many row shown as "the" result, an untestable strategy shown as merely untested, a button that starts a sweep that has nothing to do. Each test targets one of those.

**Contents.** Defines `row()`, `class TestHistory`, `class TestQueueFilter`, `class TestCommands`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_strategy_history.py -q`

#### `soltui/tests/test_top5.py`

`test` · 133 lines · 5,758 B · description: **extracted**

**Purpose.** Tests for the Top 5 tab's pure module. The load-bearing assertions: the module reads the committed evidence file faithfully (ranks, home rows, transfers), never turns absent evidence into a zero, and recovers composite members from labels without a duplicated name-to-members table that could drift from research/cross_asset_cpcv.py.

**Contents.** Defines `HEADER`, `write_csv()`, `class ParseMembersTests`, `class LoadTop5Tests`, `class RosterCandidatesTests`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_top5.py -q`

#### `soltui/tests/test_tradingstrategyresults_coverage.py`

`test` · 147 lines · 6,417 B · description: **extracted**

**Purpose.** Every strategy and indicator in `tradingstrategyresults.json` is represented in soltui. That file is a catalogue of strategies and indicators from public trading guides.

**Contents.** Defines `REPO`, `CATALOGUE`, `STRATEGIES`, `EXTRA_CARDS`, `INDICATORS`, `REFERENCE_LABEL`, `_all_card_ids()`, `class TestCatalogueCoverage`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_tradingstrategyresults_coverage.py -q`

#### `soltui/tests/test_tui.py`

`test` · 1323 lines · 58,782 B · description: **extracted**

**Purpose.** Smoke tests for the Textual app, driven through Textual's own test harness. An app that imports cleanly but explodes on mount is not working, so these actually mount it, click things, and assert on widget state. `run_test()` runs a headless terminal, so no TTY is required and this is safe in CI.

**Contents.** Defines `_queue_row()`, `TEST_SIZE`, `text_of()`, `make_settings()`, `class TestSortKey`, `class TestSortableTables`, `class TestAppMounts`, `class TestQueueTab`, `class TestExecuteTabSafety`, `class TestStrategiesTab` and 12 more. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_tui.py -q`

#### `soltui/tests/test_tui_presets_pnl.py`

`test` · 202 lines · 9,889 B · description: **extracted**

**Purpose.** The Top 5 presets in three tabs, the P&L tab, and the "every percentage names its source" rule across every table in the app. Driven through Textual's headless harness.

**Contents.** Defines `SOURCE_WORDS`, `class Isolated`, `class TestPresets`, `class TestPnlTab`, `class TestEveryPercentageNamesItsSource`. Depends on `backtester`, `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_tui_presets_pnl.py -q`

#### `soltui/tests/test_utxo_scan.py`

`test` · 229 lines · 10,782 B · description: **extracted**

**Purpose.** xpub scanning against recorded-shape explorer replies: script types, the gap limit, partial results. The network is a fake that answers from a table of derived addresses. Keys are BIP32/BIP84 test vectors.

**Contents.** Defines `esplora()`, `class Net`, `addr()`, `class ScriptTypeTests`, `class GapLimitTests`, `class PartialAndPriceTests`, `class RateLimitTests`, `class PrivacyTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_utxo_scan.py -q`

#### `soltui/tests/test_wallet.py`

`test` · 569 lines · 29,872 B · description: **extracted**

**Purpose.** Wallet discovery on recorded fixtures: no network, no key, no transaction. `fixtures/wallet/*.json` hold real replies recorded on 2026-11-07 for the owner's two public addresses (Solana token accounts, Jupiter price and token data, Base eth_getBalance / balanceOf / DefiLlama / DexScreener).

**Contents.** Defines `FIX`, `SOL_ADDR`, `BASE_ADDR`, `USDC_BASE`, `JUPSOL`, `SPAM_MINT`, `SPAM_TOKEN`, `load()`, `class Fake`, `class SolanaTests` and 6 more. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_wallet.py -q`

#### `soltui/tests/test_wallet_integration.py`

`test` · 287 lines · 14,924 B · description: **extracted**

**Purpose.** Wallet discovery wired into the console: Settings addresses, the key-source row, `portfolio.scan`, the Wallet tab, and the separate `wallet (live)` section of the P&L tab. The network is replaced by the recorded-fixture `Fake` from test_wallet; nothing here reads a key file.

**Contents.** Defines `class Env`, `class SettingsTests`, `class KeySourceCommandTests`, `class ScanCommandTests`, `class PnlWalletSectionTests`, `class WalletTabTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_wallet_integration.py -q`

#### `soltui/tests/test_wallet_settings.py`

`test` · 203 lines · 9,609 B · description: **extracted**

**Purpose.** Wallet fields in Settings: validation, private-key refusal, redaction, file mode, and the read-only `wallet.addresses` command the extension's Wallet pubkey button uses.

**Contents.** Defines `ETH`, `xprv()`, `class ValidationTests`, `class SaveAndRedactTests`, `class AddressesCommandTests`, `class KeySourceLabelTests`, `class TuiSettingsTests`. Depends on `soltui`.

**Use.** `python3 -m pytest soltui/tests/test_wallet_settings.py -q`

### `soltui/tests/fixtures/wallet/`

#### `soltui/tests/fixtures/wallet/base_recorded.json`

`test` · 54 lines · 1,067 B · description: **derived**

**Purpose.** Generated JSON object, 5 keys (eth_getBalance, balances, npm, llama, dexscreener).

**Use.** `python3 -m pytest soltui/tests/fixtures/wallet/base_recorded.json -q`

#### `soltui/tests/fixtures/wallet/jupiter_recorded.json`

`test` · 340 lines · 10,491 B · description: **derived**

**Purpose.** Generated JSON object, 2 keys (price, tokens).

**Use.** `python3 -m pytest soltui/tests/fixtures/wallet/jupiter_recorded.json -q`

#### `soltui/tests/fixtures/wallet/solana_recorded.json`

`test` · 122 lines · 2,817 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys (token, token2022, stake_staker, stake_withdrawer).

**Use.** `python3 -m pytest soltui/tests/fixtures/wallet/solana_recorded.json -q`

---

## .github

CI. Runs the test suite and the figure verifier.

9 files.

#### `.github/CODEOWNERS`

`ci` · 17 lines · 591 B · description: **curated**

**Purpose.** Review ownership per path. Matters most for the order-placing surface under `extension/` and the risk rails, where an unreviewed change is the expensive kind.

**Use.** Nothing to run; GitHub requests reviewers automatically.

#### `.github/FUNDING.yml`

`ci` · 9 lines · 237 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `.github/PULL_REQUEST_TEMPLATE.md`

`ci` · 58 lines · 2,108 B · description: **extracted**

**Purpose.** <!-- One or two sentences. What does this do that the repo could not do before? --> <!-- Which concrete problem does this fix? --> Paste the actual output, not a claim that it passed.

**Use.** Read it.

#### `.github/SECURITY.md`

`ci` · 37 lines · 2,148 B · description: **extracted**

**Purpose.** This is personal tooling with local services and no users other than its author. There is no security mailbox and no disclosure SLA. Report anything you find by opening an issue, or directly to the repository owner. The extension **can place real orders and move real money**. That makes three things

**Use.** Read it.

#### `.github/copilot-instructions.md`

`ci` · 93 lines · 5,115 B · description: **extracted**

**Purpose.** Read [CLAUDE.md](../CLAUDE.md) before proposing a change. It is the source of truth for this repository; this file is a pointer plus the rules that get broken most often. 1. Read relevant source before editing; never invent a command or path.

**Use.** Read it.

#### `.github/dependabot.yml`

`ci` · 49 lines · 1,332 B · description: **curated**

**Purpose.** Dependency update schedule. The dependency surface here is deliberately thin — pandas and numpy for the engine, node built-ins for the extension — so updates should be few and individually reviewable.

**Use.** Nothing to run; GitHub opens PRs on the configured schedule.

### `.github/ISSUE_TEMPLATE/`

#### `.github/ISSUE_TEMPLATE/bug_report.md`

`ci` · 37 lines · 853 B · description: **extracted**

**Purpose.** <!-- Actual behaviour. Paste real output; quote the shortest decisive line. --> <!-- Which doc, test, or strategy card states the expected behaviour? -->

**Use.** Read it.

#### `.github/ISSUE_TEMPLATE/feature_request.md`

`ci` · 27 lines · 833 B · description: **extracted**

**Purpose.** <!-- Which component, and what question can you not currently answer / what can you not currently do? --> <!-- The important part. For a strategy: what would show it is not curve-fit?

**Use.** Read it.

### `.github/workflows/`

#### `.github/workflows/ci.yml`

`ci` · 281 lines · 11,944 B · description: **curated**

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

## .claude

1 files.

### `.claude/agents/`

#### `.claude/agents/aero-pool-scout.md`

`doc` · 42 lines · 3,732 B · description: **extracted**

**Purpose.** Research agent that scouts Aero (aero.xyz) Slipstream pools on Base for the most likely profitable liquidity positions. It runs the liquidity component's scout, checks the top candidates' tokens and numbers against independent sources, and writes a ranked recommendation.

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

## .vscode

3 files.

#### `.vscode/extensions.json`

`config` · 4 lines · 89 B · description: **derived**

**Purpose.** Generated JSON object, 1 keys (recommendations).

**Use.** Configuration; nothing to run.

#### `.vscode/launch.json`

`config` · 22 lines · 527 B · description: **derived**

**Purpose.** Generated JSON object, 2 keys (version, configurations).

**Use.** Configuration; nothing to run.

#### `.vscode/settings.json`

`config` · 9 lines · 237 B · description: **derived**

**Purpose.** Generated JSON object, 6 keys (files.insertFinalNewline, files.trimTrailingWhitespace, editor.detectIndentation, editor.tabSize, [python], [markdown]).

**Use.** Configuration; nothing to run.

---

## liquidity

57 files.

#### `liquidity/.gitignore`

`other` · 13 lines · 118 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `liquidity/CLAUDE.md`

`doc` · 66 lines · 4,958 B · description: **extracted**

**Purpose.** The Aero Slipstream LP manager. See README.md. **It can move real money.** On 2026-11-06 the owner authorized autonomous live operation for the owner's own wallet The repo-wide standing authorization for live on-chain actions is in the root `CLAUDE.md`

**Use.** Read it.

#### `liquidity/README.md`

`doc` · 198 lines · 13,094 B · description: **extracted**

**Purpose.** The **liquidity** component of solmargintrader. It manages concentrated-liquidity positions on **Aero** (aero.xyz) **Slipstream** on **Base**, in one daemon: soltui's **Liquidity** tab shows all of it. The tab reads the daemon's state files and nothing else (see

**Use.** Read it.

#### `liquidity/STATE_FILES.md`

`doc` · 155 lines · 7,018 B · description: **extracted**

**Purpose.** The liquidity daemon (`aero-lp daemon`) writes these files. `soltui`'s Liquidity tab only **reads** them; the one exception is the kill-switch file, which soltui may create or delete. soltui never imports `aero_lp`, web3 or any key material.

**Use.** Read it.

#### `liquidity/config.example.toml`

`config` · 54 lines · 3,281 B · description: **none**

**Purpose.** _No description available._

**Use.** Configuration; nothing to run.

#### `liquidity/pyproject.toml`

`config` · 40 lines · 884 B · description: **none**

**Purpose.** _No description available._

**Use.** Configuration; nothing to run.

#### `liquidity/pyrightconfig.json`

`config` · 7 lines · 100 B · description: **derived**

**Purpose.** Generated JSON object, 4 keys (venvPath, venv, extraPaths, typeCheckingMode).

**Use.** Configuration; nothing to run.

#### `liquidity/uv.lock`

`other` · 0 lines · 393,181 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

### `liquidity/scripts/`

#### `liquidity/scripts/aero-lp-service`

`other` · 61 lines · 2,793 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

### `liquidity/src/aero_lp/`

#### `liquidity/src/aero_lp/__init__.py`

`code-python` · 4 lines · 103 B · description: **extracted**

**Purpose.** aero-lp: cost-aware auto-rebalancer for Aero Slipstream deposits on Base.

**Use.** `import liquidity.src.aero_lp.__init__`

#### `liquidity/src/aero_lp/abi.py`

`code-python` · 245 lines · 9,756 B · description: **extracted**

**Purpose.** Minimal ABIs for the Aero Slipstream contracts the bot touches. Signatures were copied from github.com/dromos-labs/metadex-slipstream-public (v1.1.0): contracts/periphery/interfaces/INonfungiblePositionManager.sol contracts/core/interfaces/pool/ICLPoolState.sol, ICLPoolConstants.sol contracts/gauge/interfaces/ICLGauge.sol, IGauge.sol, ICLGaugeFactory.sol contracts/periphery/interfaces/ISwapRouter.

**Contents.** Defines `_p()`, `fn()`, `ev()`, `ERC20`, `_MINT`, `_DECREASE`, `_COLLECT`, `_INCREASE`, `NPM`, `CL_POOL` and 11 more.

**Use.** `import liquidity.src.aero_lp.abi`

#### `liquidity/src/aero_lp/addresses.py`

`code-python` · 55 lines · 2,976 B · description: **extracted**

**Purpose.** Aero contract addresses on Base (chain id 8453). Every address here appears in two independent sources that agree: 1. Aero docs "Security Overview" -> "Contract addresses" (https://aero.xyz/docs/security) 2.

**Contents.** Defines `BASE_CHAIN_ID`, `CL_FACTORY`, `NONFUNGIBLE_POSITION_MANAGER`, `SWAP_ROUTER`, `METAQUOTER`, `CL_GAUGE_FACTORY`, `LEAF_VOTER`, `AERO_TOKEN`, `WETH`, `UNISWAP_V3_FACTORY` and 11 more.

**Use.** `import liquidity.src.aero_lp.addresses`

#### `liquidity/src/aero_lp/allocator.py`

`code-python` · 189 lines · 8,031 B · description: **extracted**

**Purpose.** Put idle wallet coins to work, but only when a pool is worth it. A pool qualifies only when **both** independent estimates clear `min_net_apr`: * the model: income - LVR - rebalance cost at the optimized width (metrics.expected_net_apr); * the replay: the best width on the pool's actual recent price path vs holding the pair (metrics.backtest_net_apr).

**Contents.** Defines `CONF_RANK`, `MIN_BACKTEST_DAYS`, `ARM_SIZE_FLOOR`, `class Candidate`, `class Arm`, `class AllocationPlan`, `_at_least()`, `_sym_ok()`, `qualify()`, `plan_allocation()` and 2 more.

**Use.** `import liquidity.src.aero_lp.allocator`

#### `liquidity/src/aero_lp/backtest.py`

`code-python` · 134 lines · 4,851 B · description: **extracted**

**Purpose.** Hourly backtest of range widths on a historical price path. Model (deliberately simple and conservative): * Earnings while in range = yield_per_usd_day(half_width) * position value / 24 per hour, where the yield curve comes from today's on-chain pool economics (fee or AERO flow per unit liquidity). * Out of range earns nothing.

**Contents.** Defines `class BacktestResult`, `_amounts()`, `_liq_for_value()`, `run()`, `format_table()`.

**Use.** `import liquidity.src.aero_lp.backtest`

#### `liquidity/src/aero_lp/chain.py`

`code-python` · 486 lines · 21,362 B · description: **extracted**

**Purpose.** Read-only access to Aero Slipstream state on Base. All multi-value reads go through Multicall3 in one eth_call pinned to one block, so a snapshot is internally consistent and public RPC rate limits are respected.

**Contents.** Defines `ZERO`, `MULTICALL3`, `MULTICALL3_ABI`, `DEFAULT_RPCS`, `MAX_HEAD_LAG_S`, `_type_str()`, `MIN_BLOCK_READ_TRIES`, `MIN_BLOCK_READ_DELAY_S`, `class PositionGone`, `class Call` and 7 more.

**Use.** `import liquidity.src.aero_lp.chain`

#### `liquidity/src/aero_lp/cli.py`

`code-python` · 556 lines · 25,191 B · description: **extracted**

**Purpose.** aero-lp command line. aero-lp verify check contract addresses + RPC freshness aero-lp pools top Aero Slipstream pools on Base (GeckoTerminal) aero-lp positions --owner 0x..

**Contents.** Defines `_print_eval()`, `_print_result()`, `cmd_verify()`, `cmd_pools()`, `cmd_positions()`, `_engine()`, `cmd_status()`, `cmd_simulate()`, `cmd_withdraw()`, `_live_gate()` and 9 more.

**Use.** `python3 liquidity/src/aero_lp/cli.py --help`

#### `liquidity/src/aero_lp/clmath.py`

`code-python` · 240 lines · 8,698 B · description: **extracted**

**Purpose.** Concentrated-liquidity math for Slipstream (Uniswap-v3-compatible tick math). Integer functions are exact ports of TickMath / SqrtPriceMath / LiquidityAmounts. Float helpers are for planning and reporting only, never for on-chain min-amount checks without a slippage margin.

**Contents.** Defines `Q96`, `Q128`, `MIN_TICK`, `MAX_TICK`, `MIN_SQRT_RATIO`, `MAX_SQRT_RATIO`, `UINT128_MAX`, `LOG_BASE`, `get_sqrt_ratio_at_tick()`, `tick_from_price()` and 19 more.

**Use.** `import liquidity.src.aero_lp.clmath`

#### `liquidity/src/aero_lp/config.py`

`code-python` · 243 lines · 10,855 B · description: **extracted**

**Purpose.** TOML configuration.

**Contents.** Defines `REWARD_MODES`, `class SafetyConfig`, `DEFAULT_ALLOWED`, `class AllocatorConfig`, `SAFE_EXIT_TARGETS`, `class GateConfig`, `class SafeExitConfig`, `class Config`, `_pick()`, `load()`.

**Use.** `import liquidity.src.aero_lp.config`

#### `liquidity/src/aero_lp/daemon.py`

`code-python` · 1350 lines · 65,768 B · description: **extracted**

**Purpose.** The liquidity daemon: one loop that manages every position, compounds, scouts and allocates. Each tick, in order: 1. Kill switch. If `$AERO_LP_HOME/KILL` exists, the tick takes no on-chain action; it still reads and reports. 2. Wallet snapshot: balances of the allowed tokens plus native ETH, recorded in the ledger for idle detection. 3.

**Contents.** Defines `STATUS_SCHEMA`, `SYMBOL_TO_ADDR`, `CONVERT_PRICE_TOLERANCE`, `SCOUT_MAX_AGE_INTERVALS`, `PRICE_RETRY_S`, `SCOUT_BUDGET_S`, `class KillSwitchEngaged`, `class Timers`, `class Daemon`.

**Use.** `import liquidity.src.aero_lp.daemon`

#### `liquidity/src/aero_lp/engine.py`

`code-python` · 654 lines · 30,000 B · description: **extracted**

**Purpose.** Glue: read chain + market state, decide, preflight-simulate, and (in live mode) execute.

**Contents.** Defines `_finite()`, `class Evaluation`, `class Engine`, `defer_sigint()`, `_single_width_cfg()`, `forced_decision()`.

**Use.** `import liquidity.src.aero_lp.engine`

#### `liquidity/src/aero_lp/executor.py`

`code-python` · 1134 lines · 50,575 B · description: **extracted**

**Purpose.** Builds and runs the rebalance transaction sequence. Sequence (one stage at a time; later stages are sized from the real results of earlier ones): A. unstake gauge.withdraw(tokenId) (only if staked; claims AERO to owner) B. remove npm.multicall([decreaseLiquidity, collect, burn]) C. swap approve(tokenIn -> SwapRouter), exactInputSingle on the same pool D.

**Contents.** Defines `T`, `UINT128_MAX`, `TRANSFER_TOPIC`, `class ExecConfig`, `class PlannedTx`, `class ConfirmedTx`, `class StageResult`, `class Runner`, `_hex()`, `token_delta()` and 13 more.

**Use.** `import liquidity.src.aero_lp.executor`

#### `liquidity/src/aero_lp/gates.py`

`code-python` · 261 lines · 10,419 B · description: **extracted**

**Purpose.** Pre-live gates: a dry-run soak and a research-gate check. Why these exist: on 2026-11-06 the bot was built, its research gate failed (9 of 70 claims unsupported), and it was switched to live signing within hours. Two gates now stand between a configuration and live signing. 1. Dry-run soak.

**Contents.** Defines `SOAK_SCHEMA`, `RESEARCH_SCHEMA`, `MAX_TICK_GAP_S`, `MAX_RESETS_KEPT`, `class LiveGateError`, `config_fingerprint()`, `_soak_path()`, `load_soak()`, `_empty()`, `record_dry_run_tick()` and 11 more.

**Use.** `import liquidity.src.aero_lp.gates`

#### `liquidity/src/aero_lp/ledger.py`

`code-python` · 431 lines · 16,363 B · description: **extracted**

**Purpose.** P&L ledger (SQLite, stdlib only). A *slot* is one strategy line. It keeps its id when a rebalance replaces the NFT, so its P&L runs across rebalances. Money flows in and out of a slot as `flows` (deposit, topup, withdraw). Gas and rewards are `events`. Periodic `snapshots` hold the slot's market value and its HODL value: what the deposited token amounts would be worth now if never deployed.

**Contents.** Defines `IDLE_MAX_GAP_S`, `SCHEMA`, `class SlotPnl`, `class Ledger`.

**Use.** `import liquidity.src.aero_lp.ledger`

#### `liquidity/src/aero_lp/market.py`

`code-python` · 200 lines · 8,825 B · description: **extracted**

**Purpose.** Off-chain market data (GeckoTerminal public API) and the earnings model. GeckoTerminal lists Aero Slipstream on Base as dex id `aero-slipstream-base`. The free API allows about 30 requests/minute, so responses are cached for `ttl` seconds.

**Contents.** Defines `GT`, `STABLES`, `class MarketData`, `vol_from_closes()`, `class PoolEconomics`, `fee_usd_per_liquidity_per_day()`, `liquidity_for_usd()`, `earn_usd_per_day()`, `with_realized_fees()`.

**Use.** `import liquidity.src.aero_lp.market`

#### `liquidity/src/aero_lp/metrics.py`

`code-python` · 438 lines · 17,939 B · description: **extracted**

**Purpose.** Every measure of a pool's likely profit or loss for a concentrated-liquidity deposit. Income (what the deposit earns while in range), measured, not quoted: * fee income - change in feeGrowthGlobal over the last day. CLPool.calculateFees credits it per unit of *unstaked* in-range liquidity, net of the unstaked fee, so it already reflects dynamic fees, router discounts and MEV capture.

**Contents.** Defines `REF_HALF_WIDTH`, `NO_DATA`, `KNOWN_TOKENS`, `class PoolMetrics`, `economics_from()`, `pool_economics()`, `pool_sigma()`, `BACKTEST_WIDTHS_PCT`, `backtest_best()`, `backtest_at_width()` and 4 more.

**Use.** `import liquidity.src.aero_lp.metrics`

#### `liquidity/src/aero_lp/providers.py`

`code-python` · 1625 lines · 66,259 B · description: **extracted**

**Purpose.** Liquidity-provider comparison: which AMMs on a chain pay a small passive LP, and how sure are we? The Aero scout judges Slipstream pools only. This module widens the same judgement to every provider DefiLlama lists on the chain, in two tiers: Tier 1, *measured* (on chain).

**Contents.** Defines `SCHEMA`, `LLAMA_POOLS_URL`, `LLAMA_COINS`, `GT`, `LLAMA_TTL_S`, `NATIVE`, `CHAIN_LABELS`, `BLOCKS_PER_DAY`, `CHART_MAX_POINTS`, `CONF_ORDER` and 30 more.

**Use.** `import liquidity.src.aero_lp.providers`

#### `liquidity/src/aero_lp/providers_report.py`

`code-python` · 300 lines · 11,664 B · description: **extracted**

**Purpose.** Markdown report for `aero-lp providers` (providers-report.md). Pure formatting: no I/O, no network.

**Contents.** Defines `BAR_NOTE`, `_pct()`, `_usd()`, `_ratio()`, `_cell()`, `_table()`, `provider_table()`, `pool_table()`, `HOW_TO_READ`, `HOW_TO_READ_2` and 3 more.

**Use.** `import liquidity.src.aero_lp.providers_report`

#### `liquidity/src/aero_lp/recovery.py`

`code-python` · 160 lines · 8,329 B · description: **extracted**

**Purpose.** Shared, idempotent ledger recovery for daemon and CLI submission journals. Construct LedgerRecovery with the recorded ledger and a fresh-price callback, then pass apply as the journal's reconciliation callback. It never broadcasts or retries a transaction.

**Contents.** Defines `class LedgerRecovery`.

**Use.** `import liquidity.src.aero_lp.recovery`

#### `liquidity/src/aero_lp/safe_exit.py`

`code-python` · 337 lines · 15,105 B · description: **extracted**

**Purpose.** Exit to safe: take every managed LP position out and leave the coins in the wallet. This is separate from the kill switch. KILL only halts the daemon: positions stay open and keep losing money. `exit-to-safe` removes the liquidity (unstake, remove, collect fees, burn the empty NFT), and can optionally convert the withdrawn coins into a stable coin.

**Contents.** Defines `REPORT_SCHEMA`, `CONVERT_PRICE_TOLERANCE`, `SYMBOL_TO_ADDRESS`, `class ConvertStep`, `class PositionPlan`, `class ExitReport`, `managed_token_ids()`, `best_direct_pool()`, `plan_conversion()`, `_value_usd()` and 6 more.

**Use.** `import liquidity.src.aero_lp.safe_exit`

#### `liquidity/src/aero_lp/scout.py`

`code-python` · 156 lines · 6,569 B · description: **extracted**

**Purpose.** Pool scout: find the Aero Slipstream pools most likely to be profitable for a deposit of a given size. Candidates come from two places, because the most profitable pools for a small passive deposit are usually *not* the highest-volume ones: 1. the top pools by 24h volume on GeckoTerminal (dex `aero-slipstream-base`); 2.

**Contents.** Defines `SCHEMA`, `_SYM`, `discover_correlated()`, `candidate_pools()`, `rank()`, `run_scout()`, `load_scout()`, `format_report()`.

**Use.** `import liquidity.src.aero_lp.scout`

#### `liquidity/src/aero_lp/state.py`

`code-python` · 80 lines · 2,693 B · description: **extracted**

**Purpose.** Small JSON state file: which NFT currently represents each managed slot, plus hysteresis counters. A rebalance burns the old NFT and mints a new one, so the bot tracks positions by *slot* (the token id it was first configured with) and follows the chain of replacements.

**Contents.** Defines `class SlotState`, `home()`, `atomic_write_json()`, `_sync_directory()`, `class State`.

**Use.** `import liquidity.src.aero_lp.state`

#### `liquidity/src/aero_lp/strategy.py`

`code-python` · 337 lines · 13,788 B · description: **extracted**

**Purpose.** Range selection and the rebalance decision. Pure functions: no I/O, fully unit-tested. Profit model ------------ A concentrated deposit earns only while price sits inside its range.

**Contents.** Defines `class Action`, `class StrategyConfig`, `class Range`, `half_width_log()`, `lvr_fraction_per_day()`, `rebalances_per_day()`, `class WidthScore`, `score_widths()`, `best_width()`, `target_range()` and 8 more.

**Use.** `import liquidity.src.aero_lp.strategy`

#### `liquidity/src/aero_lp/submissions.py`

`code-python` · 224 lines · 10,016 B · description: **extracted**

**Purpose.** Durable public transaction intents. Unknown outcomes block another live runner. The journal stores hashes and decoded intent metadata, never calldata, signed payloads or keys. A receipt is retained until the caller applies its state/accounting effects idempotently.

**Contents.** Defines `class PendingSubmission`, `_hex()`, `receipt_metadata()`, `transaction_intent()`, `class SubmissionJournal`.

**Use.** `import liquidity.src.aero_lp.submissions`

#### `liquidity/src/aero_lp/validation.py`

`code-python` · 32 lines · 1,245 B · description: **extracted**

**Purpose.** Shared numeric validation for safety settings. Never coerce TOML strings or booleans.

**Contents.** Defines `finite_number()`, `measured_gas()`.

**Use.** `import liquidity.src.aero_lp.validation`

#### `liquidity/src/aero_lp/wallet.py`

`code-python` · 78 lines · 2,870 B · description: **extracted**

**Purpose.** Signing key loading. The key is never printed, logged or written to disk by this program. Sources, in order: 0. `key_file` in the config (or AERO_LP_KEY_FILE): a file holding the hex key. It must be owned by the current user and not readable by group or others (chmod 600), or it is refused. 1. macOS Keychain generic password, service "aero-lp", account = owner address (lowercase).

**Contents.** Defines `class WalletError`, `_from_keychain()`, `_from_file()`, `load_signer()`.

**Use.** `import liquidity.src.aero_lp.wallet`

### `liquidity/tests/`

#### `liquidity/tests/test_abi_config_wallet.py`

`test` · 126 lines · 5,229 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `test_abi_parser_tuple_array_and_names()`, `test_abis_encode_offline()`, `test_minted_token_id_parses_transfer_from_zero()`, `test_config_load_and_reject_unknown()`, `test_example_config_parses()`, `test_wallet_rejects_mismatch_without_leaking_key()`, `test_misplaced_strategy_slippage_key_warns_instead_of_silently_doing_nothing()`, `test_config_rejects_negative_safety_limits()`, `test_key_file_must_be_private_and_owned()`.

**Use.** `python3 -m pytest liquidity/tests/test_abi_config_wallet.py -q`

#### `liquidity/tests/test_allocator_ledger.py`

`test` · 310 lines · 12,926 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `WETH`, `WSTETH`, `CBETH`, `USDC`, `SCAM`, `row()`, `test_both_estimates_must_clear_threshold()`, `test_filters_reject_risky_pools()`, `test_single_clear_winner_gets_everything_capped_per_position()`, `test_close_candidates_become_side_by_side_experiment()` and 20 more.

**Use.** `python3 -m pytest liquidity/tests/test_allocator_ledger.py -q`

#### `liquidity/tests/test_backtest.py`

`test` · 49 lines · 2,002 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `test_flat_price_earns_yield_and_never_rebalances()`, `test_trend_out_of_range_triggers_rebalances_and_costs()`, `test_wider_range_rebalances_less()`, `test_format_table_has_header_and_rows()`, `test_net_apr_is_on_starting_capital_not_end_hodl_value()`.

**Use.** `python3 -m pytest liquidity/tests/test_backtest.py -q`

#### `liquidity/tests/test_chain_audit.py`

`test` · 127 lines · 4,488 B · description: **extracted**

**Purpose.** Pinned-state, economic ownership and unknown-penalty regressions.

**Contents.** Defines `staked_chain()`, `test_head_pins_at_our_receipt_and_retries_lagging_nodes()`, `test_old_postmint_snapshot_cannot_prove_position_gone()`, `test_foreign_staked_hint_is_not_an_economic_owner()`, `test_unknown_or_invalid_penalty_cannot_become_zero()`, `test_staked_membership_must_be_positive_evidence()`, `test_penalty_bounds_are_validated()`, `test_verified_staked_owner_retains_measured_active_penalty()`, `test_explicit_zero_penalty_is_allowed()`, `test_unknown_accrued_reward_cannot_erase_early_exit_cost()`.

**Use.** `python3 -m pytest liquidity/tests/test_chain_audit.py -q`

#### `liquidity/tests/test_chain_vol.py`

`test` · 82 lines · 3,073 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `_window_average_ticks()`, `test_twap_window_vol_is_unbiased()`, `test_vol_needs_enough_points()`, `test_twap_series_spans_the_requested_hours_not_a_window_count()`, `test_latest_balance_reads_are_pinned_to_a_block_no_older_than_our_last_transaction()`.

**Use.** `python3 -m pytest liquidity/tests/test_chain_vol.py -q`

#### `liquidity/tests/test_clmath.py`

`test` · 88 lines · 3,625 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `test_sqrt_ratio_known_points()`, `test_sqrt_ratio_matches_high_precision_reference()`, `test_sqrt_ratio_monotonic()`, `test_human_price_weth_usdc()`, `test_liquidity_amount_round_trip()`, `test_amounts_single_sided_outside_range()`, `test_fee_growth_inside_wraparound()`, `test_value0_fraction_bounds()`, `test_swap_to_ratio_hits_target()`, `test_impermanent_loss_zero_at_entry_and_negative_after_move()`.

**Use.** `python3 -m pytest liquidity/tests/test_clmath.py -q`

#### `liquidity/tests/test_config_audit.py`

`test` · 48 lines · 1,824 B · description: **extracted**

**Purpose.** Configuration must not disable a safety gate through coercion or IEEE special values.

**Contents.** Defines `OWNER`, `test_all_execution_and_safety_numbers_must_be_finite()`, `test_estimates_and_intervals_cannot_disable_gas_or_scheduling_checks()`, `test_allocator_settings_reject_boolean_and_collection_coercion()`, `test_execution_timing_requires_positive_whole_seconds()`.

**Use.** `python3 -m pytest liquidity/tests/test_config_audit.py -q`

#### `liquidity/tests/test_daemon.py`

`test` · 1336 lines · 55,822 B · description: **extracted**

**Purpose.** Offline tests of the daemon with a stubbed chain, market, engine and rebalancer. The stubs record every call, so the tests can prove what the daemon did and did not send: which runner kind each rebalancer call received ("sim" or "live"), and that nothing signs in dry run or under the kill switch.

**Contents.** Defines `OWNER`, `WETH`, `USDC`, `AERO`, `WSTETH`, `GAUGE`, `DEC`, `PRICES`, `addr()`, `tick_for()` and 30 more.

**Use.** `python3 -m pytest liquidity/tests/test_daemon.py -q`

#### `liquidity/tests/test_daemon_audit.py`

`test` · 219 lines · 8,296 B · description: **extracted**

**Purpose.** Every live path shares safety gates; capital and ownership cannot bypass them.

**Contents.** Defines `make_daemon()`, `test_every_live_write_path_honors_zero_gas_cap()`, `test_foreign_direct_wallet_position_is_not_registered()`, `test_compound_clamps_rewards_to_fresh_position_and_total_caps()`, `test_pool_pushed_during_conversions_cannot_be_deployed()`, `test_compound_rechecks_total_exposure_after_simulation()`, `test_successful_compound_refreshes_snapshot_before_later_allocation()`, `test_deploy_checks_twap_after_the_simulation_too()`, `test_missing_simulation_gas_evidence_refuses_write()`, `test_preflight_never_uses_cached_price_when_feed_is_down()` and 2 more.

**Use.** `python3 -m pytest liquidity/tests/test_daemon_audit.py -q`

#### `liquidity/tests/test_engine.py`

`test` · 282 lines · 11,379 B · description: **extracted**

**Purpose.** Engine safety gates and partial-failure bookkeeping, with the chain and market stubbed out.

**Contents.** Defines `OWNER`, `NEW_RANGE`, `make_engine()`, `chain_stub()`, `make_ev()`, `test_clean_evaluation_passes_live_safety()`, `test_live_mode_fails_closed()`, `test_dry_run_only_reports_unknown_twap_and_missing_prices()`, `_step_with()`, `test_failed_stake_keeps_tracking_the_minted_nft()` and 14 more.

**Use.** `python3 -m pytest liquidity/tests/test_engine.py -q`

#### `liquidity/tests/test_engine_audit.py`

`test` · 103 lines · 3,673 B · description: **extracted**

**Purpose.** Live safety and interrupted-operation persistence regressions (all I/O stubbed).

**Contents.** Defines `setup_live()`, `test_fresh_position_above_cap_never_reaches_live_runner()`, `test_invalid_market_eth_quote_cannot_withdraw_live()`, `test_deferred_stop_persists_successful_withdraw()`, `test_deferred_stop_persists_rebalance_history_and_cooldown()`.

**Use.** `python3 -m pytest liquidity/tests/test_engine_audit.py -q`

#### `liquidity/tests/test_executor.py`

`test` · 907 lines · 38,360 B · description: **extracted**

**Purpose.** Offline tests of the rebalance sequence with a fake chain and a fake runner.

**Contents.** Defines `W3`, `OWNER`, `GAUGE`, `T0`, `T1`, `AERO`, `HUGE`, `transfer_log()`, `increase_log()`, `class FakeChain` and 30 more.

**Use.** `python3 -m pytest liquidity/tests/test_executor.py -q`

#### `liquidity/tests/test_executor_audit.py`

`test` · 177 lines · 7,158 B · description: **extracted**

**Purpose.** Transaction-scoped accounting and receipt-recovery regressions.

**Contents.** Defines `test_topup_drift_aborts_before_swapping_and_restakes()`, `test_incoming_transfer_during_remove_never_enters_rebalance_budget()`, `test_increase_receipt_survives_failed_state_read()`, `test_missing_remove_transfer_evidence_aborts_before_spending()`, `test_actual_mint_amounts_come_from_confirmed_increase_receipt()`, `test_unrelated_incoming_transfer_during_topup_unstake_stays_out_of_budget()`, `test_mint_without_increase_evidence_stops_but_preserves_new_nft()`, `test_live_increase_receipt_is_kept_before_failed_postreceipt_read()`, `test_repeated_transaction_labels_preserve_total_gas()`, `test_capped_topup_leaves_unstake_proceeds_in_wallet()`.

**Use.** `python3 -m pytest liquidity/tests/test_executor_audit.py -q`

#### `liquidity/tests/test_gates.py`

`test` · 201 lines · 8,437 B · description: **extracted**

**Purpose.** Soak gate, research gate, grandfather record and the CLI refusal. Offline; nothing is signed.

**Contents.** Defines `OWNER`, `H`, `cfg()`, `passing()`, `soak()`, `test_live_refused_without_a_soak_record()`, `test_live_allowed_after_the_configured_soak()`, `test_default_soak_is_24_hours()`, `test_downtime_between_dry_run_ticks_is_not_credited()`, `test_strategy_or_cap_change_resets_the_soak()` and 11 more.

**Use.** `python3 -m pytest liquidity/tests/test_gates.py -q`

#### `liquidity/tests/test_market_state.py`

`test` · 179 lines · 6,838 B · description: **extracted**

**Purpose.** Earnings model, volatility estimate, price cache and state file (offline).

**Contents.** Defines `WETH`, `USDC`, `econ()`, `test_earn_staked_is_share_of_emissions()`, `test_earn_unstaked_is_share_of_net_fees()`, `test_earn_is_zero_out_of_range_or_without_liquidity()`, `test_liquidity_for_usd_round_trips_to_the_requested_value()`, `test_vol_from_closes_scales_hourly_to_daily()`, `test_vol_from_closes_ignores_bid_ask_bounce_but_keeps_real_moves()`, `_market()` and 4 more.

**Use.** `python3 -m pytest liquidity/tests/test_market_state.py -q`

#### `liquidity/tests/test_metrics.py`

`test` · 236 lines · 8,856 B · description: **extracted**

**Purpose.** Metrics and scout numeric edge cases, with a stubbed chain and market (no network).

**Contents.** Defines `WETH`, `WSTETH`, `AERO`, `POOL`, `GAUGE`, `PRICES`, `make_pool()`, `class StubChain`, `class StubMarket`, `wobble()` and 15 more.

**Use.** `python3 -m pytest liquidity/tests/test_metrics.py -q`

#### `liquidity/tests/test_network.py`

`test` · 71 lines · 2,574 B · description: **extracted**

**Purpose.** Live Base checks. Run with: pytest -m network They read public chain state and run eth_simulateV1. Nothing is signed or broadcast.

**Contents.** Defines `USDC`, `chain()`, `test_deployment_verifies()`, `test_weth_usdc_pool_state()`, `_find_staked_position()`, `test_full_rebalance_simulates_on_a_real_staked_position()`.

**Use.** `python3 -m pytest liquidity/tests/test_network.py -q`

#### `liquidity/tests/test_providers.py`

`test` · 1044 lines · 48,994 B · description: **extracted**

**Purpose.** Provider comparison (offline): DefiLlama parsing, AMM mapping, Tier 2 LVR, the generic v3 and v4 readers against a fake chain, ranking, and the report. HTTP goes through httpx.MockTransport; no network, no chain.

**Contents.** Defines `WETH`, `USDC`, `USDT`, `CBBTC`, `POOL`, `raw_pool()`, `test_llama_pool_parses_fee_tick_spacing_and_native_tokens()`, `test_llama_pool_tolerates_missing_and_null_numbers()`, `test_quoted_base_apy_falls_back_to_the_total_less_rewards_for_vaults()`, `test_amm_type_mapping()` and 30 more.

**Use.** `python3 -m pytest liquidity/tests/test_providers.py -q`

#### `liquidity/tests/test_providers_network.py`

`test` · 62 lines · 2,573 B · description: **extracted**

**Purpose.** Live Base reads for the provider comparison. Run with: pytest -m network Reads public chain state, GeckoTerminal and DefiLlama. Nothing is signed or broadcast.

**Contents.** Defines `USDC`, `V4_USDC_USDT`, `chain()`, `test_registry_addresses_verify_on_chain()`, `test_a_real_uniswap_v3_weth_usdc_pool_scores_with_finite_measured_numbers()`, `test_a_real_uniswap_v4_pool_reads_through_state_view()`.

**Use.** `python3 -m pytest liquidity/tests/test_providers_network.py -q`

#### `liquidity/tests/test_safe_exit.py`

`test` · 273 lines · 10,835 B · description: **extracted**

**Purpose.** exit-to-safe with a stubbed engine: dry run signs nothing, live sets KILL, every check fails closed.

**Contents.** Defines `OWNER`, `WETH`, `USDC`, `PRICES`, `token()`, `POOL`, `pos()`, `result()`, `class StubEngine`, `run()` and 21 more.

**Use.** `python3 -m pytest liquidity/tests/test_safe_exit.py -q`

#### `liquidity/tests/test_strategy.py`

`test` · 144 lines · 5,113 B · description: **none**

**Purpose.** _No description available._

**Contents.** Defines `cost()`, `decide()`, `test_target_range_contains_tick_and_is_snapped()`, `test_target_range_minimum_width()`, `test_hold_when_centered()`, `test_rebalance_when_out_of_range_and_profitable()`, `test_cooldown_blocks()`, `test_edge_needs_confirmation()`, `test_unprofitable_when_costs_dominate()`, `test_waits_out_gauge_penalty_when_cheaper()` and 7 more.

**Use.** `python3 -m pytest liquidity/tests/test_strategy.py -q`

#### `liquidity/tests/test_submission_audit.py`

`test` · 395 lines · 17,250 B · description: **extracted**

**Purpose.** Ambiguous broadcasts stay blocked until durable receipt and ownership reconciliation.

**Contents.** Defines `test_simrunner_requires_positive_measured_gas()`, `test_engine_rejects_unknown_sequence_gas()`, `test_live_runner_refuses_to_broadcast_without_durable_journal()`, `mint_transaction()`, `late_mint_receipt()`, `test_journal_is_durable_before_send_and_blocks_another_runner()`, `test_late_mint_is_tracked_across_daemon_restart_before_retry()`, `proven_receipt()`, `test_late_rebalance_mint_recovers_engine_state_and_existing_slot()`, `test_recovered_position_flows_are_idempotent()` and 5 more.

**Use.** `python3 -m pytest liquidity/tests/test_submission_audit.py -q`

---

## llms

3 files.

#### `llms/aero-lp-explained-2026-11-06.md`

`doc` · 106 lines · 7,086 B · description: **extracted**

**Purpose.** The message confirms that the kill switch is **on**. The background bot (the "daemon") is paused and will not send any transaction until you press **Resume**. While paused it still reads prices and keeps the Liquidity tab up to date. What the kill switch does **not** do: So pressing Kill was harmless but changed nothing about your positions.

**Use.** Read it.

#### `llms/defillama-llms-free.txt`

`data` · 289 lines · 14,067 B · description: **derived**

**Purpose.** Generated report. Opens: # DefiLlama Free API / > Free API — no authentication required. All endpoints below use base URL https://api.llama.fi

**Use.** Read it.

#### `llms/defillama-llms.txt`

`data` · 120 lines · 9,228 B · description: **derived**

**Purpose.** Generated report. Opens: # DefiLlama API / > DefiLlama provides free, open-source DeFi analytics data. There are two separate APIs with different base URLs and authentication. Do NOT mix them.

**Use.** Read it.

---

## mongo

17 files.

#### `mongo/README.md`

`doc` · 182 lines · 9,035 B · description: **extracted**

**Purpose.** A read-mostly MongoDB copy of everything this repo has measured: price history, strategies and their cards, the signal and indicator layers, per-bar readouts, backtest runs, CPCV and sweep results, the coin write-ups, and the test-suite

**Use.** Read it.

#### `mongo/__init__.py`

`code-python` · 0 lines · 0 B · description: **none**

**Purpose.** _No description available._

**Use.** `import mongo.__init__`

#### `mongo/load.py`

`code-python` · 820 lines · 30,524 B · description: **extracted**

**Purpose.** Load the repo's research artifacts into the local MongoDB store. pip install -r mongo/requirements.txt python3 mongo/load.py # everything python3 mongo/load.py --only bars,strategies python3 mongo/load.py --dry-run # count what would load, write nothing **This loader is destructive by design and idempotent by consequence.** It drops and recreates every collection it writes.

**Contents.** Defines `REPO`, `LOADED_AT`, `sha256()`, `source_snapshot()`, `provenance()`, `clean()`, `maybe_number()`, `read_csv_snapshot()`, `read_csv_rows()`, `read_bar_snapshot()` and 26 more. Depends on `backtester`, `research`.

**Use.** `python3 mongo/load.py --help`

#### `mongo/requirements.txt`

`data` · 6 lines · 287 B · description: **derived**

**Purpose.** Generated report. Opens: # Deliberately separate from backtester/requirements.txt. The backtester is / # stdlib-first and its dependency list is short on purpose; a driver needed only

**Use.** Read it.

#### `mongo/schema.py`

`code-python` · 473 lines · 19,535 B · description: **extracted**

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

`test` · 332 lines · 14,034 B · description: **extracted**

**Purpose.** Tests for the local MongoDB research store. The load is destructive by design, so the test that matters most asserts it is therefore *idempotent*: loading twice must leave identical counts. Without that, the time series collections would silently double on a second run -- they accept no unique index, so nothing else would catch it.

**Contents.** Defines `REPO`, `server_available()`, `SERVER`, `class TestPureHelpers`, `class TestSchemaLayout`, `class TestLoadedStore`, `class TestIdempotency`. Depends on `backtester`, `research`.

**Use.** `python3 -m pytest mongo/tests/test_load.py -q`

#### `mongo/tests/test_load_audit.py`

`test` · 157 lines · 8,012 B · description: **extracted**

**Purpose.** Offline loader regressions: fixtures and fake databases only.

**Contents.** Defines `class FakeDatabase`, `class LoaderAuditTests`.

**Use.** `python3 -m pytest mongo/tests/test_load_audit.py -q`

#### `mongo/tests/test_snapshot_audit.py`

`test` · 96 lines · 4,694 B · description: **extracted**

**Purpose.** Source byte and run-artifact identity, without a MongoDB connection.

**Contents.** Defines `class SnapshotAudit`. Depends on `backtester`.

**Use.** `python3 -m pytest mongo/tests/test_snapshot_audit.py -q`

---

## scripts

2 files.

#### `scripts/build_doc_index.py`

`code-python` · 180 lines · 6,253 B · description: **extracted**

**Purpose.** Generate `docs/high_signal_file_index.json` from `docs/codebase-overview.md`. python3 scripts/build_doc_index.py The overview is the human-readable file map; the JSON is the machine-readable one for LLM retrieval.

**Contents.** Defines `REPO`, `OVERVIEW`, `INDEX`, `COMPONENTS`, `ROW`, `KIND_BY_SUFFIX`, `git_ok()`, `is_tracked()`, `is_ignored()`, `excluded()` and 4 more.

**Use.** `python3 scripts/build_doc_index.py --help`

#### `scripts/check_docs.py`

`code-python` · 390 lines · 14,927 B · description: **extracted**

**Purpose.** Fail the build when the docs drift from the repo. python3 scripts/check_docs.py python3 scripts/check_docs.py --prune # drop dead index entries Two kinds of rot, both of which happened here before this existed: * **Stale test counts.** The docs claimed 250 backtester tests for several commits while the suite had grown to 454.

**Contents.** Defines `REPO`, `COUNT_DOCS`, `INDEX_JSON`, `OVERVIEW_MD`, `is_ignored()`, `is_tracked()`, `missing_and_tracked()`, `committed_test_files()`, `count_tests()`, `load_failures()` and 9 more.

**Use.** `python3 scripts/check_docs.py --help`

---

## skills

62 files.

#### `skills/README.md`

`doc` · 35 lines · 1,905 B · description: **extracted**

**Purpose.** Version-controlled copies of the Claude Code skills this project's research depends on. The live skills are installed at `~/.claude/skills/`, which is outside this repository and not version-controlled. Several of this project's research documents cite them as the source of a

**Use.** Read it.

### `skills/five-minute-signal/`

#### `skills/five-minute-signal/SKILL.md`

`doc` · 136 lines · 8,044 B · description: **extracted**

**Purpose.** >-

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

`code-shell` · 81 lines · 2,599 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `tools/install-hooks.sh`

`code-shell` · 23 lines · 865 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.

#### `tools/land.sh`

`code-shell` · 92 lines · 3,982 B · description: **none**

**Purpose.** _No description available._

**Use.** Read it.
