# Historical Backtester Integrity Implementation Plan

**Goal:** Build an offline, reproducible research backtester with verifiable history and recoverable results, without implying that past results predict future profits.

**Architecture:** Preserve the existing simulation engines. Add an explicit, separately invoked historical-data inventory and immutable versioned storage, and a proof-checking results archive. The runner consumes validated snapshots; user interface, forward testing, signal generation and all-strategy orchestration remain separate.

**Tech Stack:** Python, existing pandas/numpy simulator, standard-library SQLite and CSV; no new server or live-trading path.

**Spec:** The optimized request is recorded in `prompts.md`; existing simulation rules are in `CLAUDE.md` and `backtester/README.md`.

## Global Constraints

- SOL/USDC is the primary pair. Preserve USDC-denominated balances and P&L; do not silently convert USDC to USD or assume a fixed peg.
- Backtesting remains offline and simulation-only. Missing, corrupt, ambiguous, or insufficiently sourced information is reported rather than guessed.
- Strategies see only observations available at the decision time; model fills and all costs explicitly, retaining current engine behavior and compatibility.
- Existing local market caches and active tasks are never overwritten or interrupted. Historical chains, venues, asset identity and fee models are distinct; do not infer chain from an exchange price.
- Record provenance, data hashes, code version, configuration, scenarios, seed, costs, time semantics, and artifacts per run. Report assumptions, unsupported cases, and coverage gaps.
- Treat storage integrity and backups separately: local checksums detect alteration but are not a backup or proof of provenance.

## Review Focus

- A modified future bar cannot alter an earlier strategy decision or fill.
- Duplicate, missing, out-of-order, inconsistent or corrupted bars refuse use rather than silently filling history.
- A crash or interrupted update never exposes a partially committed dataset or result.
- A saved run with changed or missing artifacts is rejected, including path traversal and incomplete manifests.
- Unavailable data, chain identity, fees or liquidity is recorded as unknown and cannot become fabricated trade evidence.

## Existing state

`backtester/core/data.py` validates OHLCV; `core/engine.py`, `gridsim.py`, and `dcasim.py` provide distinct economic models. `core/report.py` publishes artifact hashes and a manifest last. `core/universe.py` has multiple lists, and the owner confirmed the requested universe: BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI, AVAX, JitoSOL, KMNO, USDC and XMR. The local cache already contains large CSVs; exact coverage and source status require a measured inventory. F5 orchestration and forward handoff are separately owned by `TASK-1046`.

## Deliverables and acceptance gates

### 1. Baseline and coverage

- [ ] Measure each configured asset, venue, interval, earliest/latest time, gaps, source and revision, without claiming that a file is complete based on its name.
- [x] Identify the 14 desired assets from the owner; exact instruments and missing venue histories remain explicit gaps. Preserve raw observations and provider corrections.
- [ ] Test duplicate, missing and inconsistent bars; a requested period outside validated coverage fails closed.

### 2. Versioned historical storage

- [ ] Implement append-only immutable snapshots with source metadata, complete SHA-256 and schema/version information, strict UTC and interval semantics, keyed access by instrument/venue/interval/time, integrity verification on read, and explicit revisions for corrections.
- [ ] Stream ingest and range queries for multi-gigabyte histories; prove peak memory and disk behavior on a realistic local fixture before migration.
- [ ] Test concurrent writers, interrupted publication, duplicate imports, corrections, corruption, indexed ranges, permissions and restore from an independently copied backup.
- [ ] Integrate snapshot loading with the existing data-loader protocol. Never allow a fetcher/network client inside simulation.

### 3. Simulation fidelity

- [ ] Verify USDC-denominated SOL/USDC spot accounting against independent hand-calculated fills and realistic source data. The new fixture path records USDC explicitly; other bot engines and perp models are not yet qualified for USDC.

- [ ] Inventory supported strategy and bot contracts and preserve their distinct engines. Reject unsupported strategy inputs and data types instead of presenting a proxy as a completed backtest.
- [ ] Test prefix invariance, next-bar timing, availability timestamps and leakage through cross-asset joins, higher-timeframe bars, normalizers and training labels.
- [ ] Reconcile per-fill cash, positions, realized/unrealized P&L, fees and borrow to marked equity with independent hand-calculated scenarios; include chain/venue only when actually specified and supported.
- [ ] Add deterministic, seeded stress scenarios for explicitly modeled latency, gaps, slippage, partial fills and outages. Label model assumptions and refuse scenarios the historical data cannot support.
- [ ] Check intrabar ambiguity pessimistically and preserve current grid-extension economic parity. Run walk-forward and selection-bias checks; report limitations rather than expected profit.

### 4. Durable run archive

- [x] Ingest only complete, hash-verified run manifests and artifacts into an atomic, indexed local archive with stable run identity, idempotent import, collision detection, and no path escape.
- [ ] Retrieve and independently reverify complete run evidence after restart and after a tested backup/restore. Fixture-level verification and backup reads exist; independent backup/restore on representative data remains.
- [ ] Bind all strategy code, dependencies, input snapshots, configuration, costs, seed, coverage and scenario definitions to the archive. Distinguish reproducible, partially evidenced, and non-reproducible runs.
- [ ] Benchmark range lookup, archive import and retrieval on representative data; record actual timings rather than promising speed.

### 5. Integration and delivery

- [ ] Expose a narrow storage interface to the existing orchestration owner without changing active forward testing, signal or UI components.
- [ ] Run focused integrity, accounting and fault-injection tests, then the relevant repository regression and documentation checks; preserve final exit codes.
- [ ] Record exactly what is implemented, what remains, evidence and recovery steps. Deliver only verified task-owned changes and do not label a partial foundation a completed backtester.
