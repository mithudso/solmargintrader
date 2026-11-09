# Historical backtester: implementation and recovery handoff

**Evidence date:** 2026-11-09. **Status:** the historical-data and result-storage foundation is implemented and in use. The complete, production-qualified multi-asset and multi-bot backtester is **not finished**. This handoff describes the work performed in this session, how to operate what exists, the decisions behind it, and the remaining implementation. Existing UI, forward testing, signal generation, and orchestration are separate workstreams.

Start with the local [market-data catalog](/Users/mitch/.local/share/solmargintrader/historical-data-1128/CATALOG.md) and its per-dataset receipts for current paths and exact coverage. Those files and the datasets are not in the public source repository. The snapshot inventories are as-of records, not a live freshness service. This document records a point-in-time state and must be rechecked before use.

## Scope and decisions

The owner selected BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI, AVAX, JitoSOL, KMNO, USDC and XMR; the primary market is SOL/USDC. The goal is reliable historical strategy and bot replay, with timestamped trades, balances, P&L, fees, realistic adverse conditions and recoverable results. Backtesting remains offline and simulation-only. Its output describes a model of past data, not proof of future returns.

The design separates **network collection**, **validation and storage**, **simulation**, and **result archival**. This keeps a replay from fetching mutable data mid-run, lets inputs be checked independently, and avoids interfering with the active forward-testing and UI owners. SQLite was selected for this local workload: it supplies indexed timestamp keys, transactions, and a consistent backup API without running a server. The trade-off is that the current full-snapshot verification and result loading can be expensive; a multi-gigabyte performance and memory qualification remains open.

The records use UTC bar-open timestamps and a declared interval, instrument, quote and venue. `SOL-USDC`, `SOL-USD`, and `SOL-USDT` are distinct instruments; prices from different venues are also distinct. A source label supplied at import is an operator assertion, not proof that a source is authentic. Stablecoins are not converted at a presumed peg, and a centralized-exchange candle is not evidence of an on-chain trade. Missing observations are recorded, never silently forward-filled. Checksums detect byte changes but do not prove that an exchange's data was complete, historically available at decision time, or economically representative.

## Work performed and delivery

1. Ran the explicitly requested prompt optimization and wrote the [integrity implementation plan](superpowers/plans/2026-11-09-backtester-integrity.md). The [prompt review](superpowers/plans/2026-11-09-backtester-prompt-review.md) records the actual scope: structural reviews were performed, but the full optimizer manifest, mechanical acceptance gate, behavioral comparison and telemetry were not produced. The subsequent SOL/USDC clarification was not independently re-audited. Do not call the full optimizer protocol formally clean.
2. Added and tested immutable, content-addressed OHLCV snapshots; an adapter to the existing loader; an atomic run-artifact archive; and SQLite backup/verification. Added explicit USDC and USDT accounting for matching snapshot-backed **spot** runs. The main foundation merged in [PR 174](https://github.com/mithudso/solmargintrader/pull/174), with its continuation record in [PR 176](https://github.com/mithudso/solmargintrader/pull/176).
3. Measured existing history, retained raw source pages and original files, and created source-labelled daily snapshots for all 14 assets where a contiguous series was available. Existing daily files with unknown venue or quote remain distinct; the snapshot loader refuses an unknown venue. Early BTC/ETH daily attempts that failed continuity were retained separately, not promoted as complete.
4. Added the resumable KuCoin minute collector and gap-aware indexed CSV segments in [PR 177](https://github.com/mithudso/solmargintrader/pull/177). Recorded a verified recent snapshot per asset, deeper SOL/USDC and KMNO/USDT data, gap ledgers and quarantined suspect inputs.
5. Used Firecrawl to locate primary Jito and OKX documentation and Kraken's downloadable historical archive. Retrieved selected Kraken archive members by HTTP range, normalized and indexed 14 markets, and backed up the acquired datasets to a private GitHub repository. The research and backup record merged in [PR 178](https://github.com/mithudso/solmargintrader/pull/178).
6. Executed real-data simulations as **smoke tests**, not profitability claims. One four-strategy daily SOL/USDC run covered 1,631 bars with a 70/30 split; one minute snapshot smoke covered 43,200 bars; a later one-day SOL/USDC buy-and-hold smoke used the deep snapshot. The one-day run covered 1,440 bars, used assumed 6 bps fee and 2 bps slippage, and was archived as run `d37b58aea6dffecf1fa744127ce1cb67b7a3a7503dae68e0fd9668a0ea659137`. These assumptions are not a verified historical fee schedule.

## Components and data flow

| Component | Role and boundary |
| --- | --- |
| `backtester/core/kucoin_history.py` | Explicit 1-minute spot collector. Each fixed window stores the raw response bytes, SHA-256, normalized candles and page metadata in a single SQLite transaction. The engine itself does not fetch. |
| `backtester/core/segmented_history.py` | Validates and privately copies an ordered canonical CSV; indexes contiguous ranges by byte offset and hash. Queries refuse ranges containing gaps. This is a Python API, not a module CLI. |
| `backtester/core/history_store.py` | Imports strictly contiguous canonical CSV into a content-addressed snapshot with metadata and normalized row digest. `snapshot_info` and `read_history` verify stored content. |
| `backtester/core/data.py` | `SnapshotLoader` checks the asset-quote label, venue, interval and requested boundaries, then reads the snapshot through the existing data-loader seam. |
| `backtester/core/engine.py` and `types.py` | Existing event-driven single-series engine, cost configuration, positions/trades, and bounded `BarWindow`. Other bot engines are separate and not qualified merely by this adapter. |
| `backtester/core/report.py` and `run_archive.py` | A report manifest inventories artifacts by hash. The run archive verifies the manifest and artifacts, then stores them atomically in SQLite; `read_run` verifies them again. |
| `docs/superpowers/plans/2026-11-09-backtester-integrity.md` | Intended acceptance gates and remaining implementation. Its open checklist is a plan, not proof that a capability has shipped. |

The canonical CSV header is exactly `timestamp,open,high,low,close,volume`, in that order, with UTC epoch **seconds**, a newline-terminated header and rows, and one bar-open timestamp per row. The importer validates alignment, ordering, finite positive prices, nonnegative volume, and OHLC consistency. `history_store` requires full continuity; `segmented_history` allows missing minutes in the source but splits at gaps and caps segments at 1,440 rows.

A snapshot's identity is derived from canonical metadata and the normalized row hash; repeating an identical import is idempotent, and changed content or metadata creates a different identity. The run archive derives its run ID from the exact manifest bytes. It requires the listed comparison, report, trade and equity files, rejects unsafe artifact names, and checks every listed digest. Charts written after manifest creation are not included unless they appear in the manifest. Neither archive provides tamper-proof signing or source authenticity.

## Time and simulation semantics

`kucoin_history.collect` and `kucoin_history.read_range` accept **half-open** `[start, end)` epoch-second bounds. Its `audit_store` ledger also reports exclusive ends. In contrast, `segmented_history.read_range` and `history_store.read_history` use **inclusive** start and end bar-open timestamps. The CLI accepts dates as inclusive calendar dates; an intraday end only includes bars that have fully closed. Do not interchange these interfaces without converting and testing the boundary.

In `engine.py`, an existing perpetual position is checked for a liquidation at the current open first; scheduled open-price fills run next; borrow accrual and the bar's liquidation check follow; the strategy receives a `BarWindow` through the current bar; the engine schedules a later fill or, if explicitly configured with `fill_delay=0`, fills at this bar's close; then it marks equity. The default delay is one bar. A zero-delay close fill is a distinct modeling assumption and must not be described as a next-bar fill. `BarWindow` limits a strategy's exposed history, and tests include a deliberately cheating strategy, but broader cross-asset joins, feature availability, training labels and every bot adapter still require independent prefix-invariance tests.

The snapshot-backed spot CLI permits `--quote USD`, `USDC`, or `USDT` when the snapshot instrument matches; stablecoin accounting is refused for non-snapshot inputs and perp mode. Perp funding/borrow and chain fees must not be inferred from unrelated spot candles. No architecture here independently reconstructs historical order-book depth, real fill probabilities, chain-specific execution, or all bot state transitions.

## Data inventory and provenance

The detailed, machine-readable inventory is under `/Users/mitch/.local/share/solmargintrader/historical-data-1128/`:

| Dataset | Observed state at acquisition | Where to inspect |
| --- | --- | --- |
| Deep KuCoin SOL/USDC | 2,349,374 contiguous one-minute bars, 2022-05-23 08:00 through 2026-11-09 20:13 UTC inclusive. The first 480 requested minutes were unobserved. | `kucoin-sol-usdc-1m.sqlite`, `sol-usdc-deep-audit.json`, `sol-usdc-deep-gaps.csv`, `kucoin-sol-usdc-deep/receipt-v2.json` |
| Deep KuCoin KMNO/USDT | 1,326,148 observations; six interior gap runs contain 3,467 absent minutes. The requested-window audit reports eight gap runs and 4,190 absent slots including both boundaries. The source rechecks returned no candles; that alone does not establish no trading. | `kucoin-kmno-usdt-1m.sqlite`, `kmno-usdt-deep-audit.json`, `kmno-usdt-deep-gaps.csv`, `kmno-gap-rechecks/`, `kucoin-kmno-usdt-deep/receipt.json` |
| Fourteen recent snapshots | Eleven KuCoin USDC markets and OKX JITOSOL/USDT have 43,200 continuous minute bars; KMNO/USDT has 43,195; Kraken USDC/USD has 720. For these exact 14 snapshots the common intersection is 717 minutes. There is also a separate 43,200-bar USDC/USDT snapshot. | `backtest-ready/inventory.json`, `recent-snapshots.sqlite`, `deep-snapshots-v2.sqlite` |
| Kraken archive | 8,266,148 observed 1-minute candles across 14 venue-specific markets, each ending on 2026-09-30. Starts, gaps and quote currencies vary. Kraken says it omits no-trade intervals; readers still refuse gap crossings. | `kraken-archive-20260930/inventory.json`, each asset's `receipt.json`, `gaps.csv`, raw OHLCVT CSV and `segments/` |
| Legacy minute caches | 28,045,077 observations across 11 assets with 2,436,585 unobserved slots; source/quote provenance is incomplete for most. Separate reconstructed samples have their own coverage. | `legacy-segments/inventory.json`, `repaired-legacy-segments/inventory.json` |
| Daily histories | One source-labelled contiguous daily snapshot per asset, with differing dates, sources and quotes. The real SOL/USDC daily test used the 1,631-bar snapshot. | `/Users/mitch/.local/share/solmargintrader/backtester-task-1117/validated-market-inventory.json` and its source-page directories |
| Funding | Historical files named hourly contained 28,800-second gaps and timestamps off the hour by 3,599/3,601 seconds. They were not rounded or normalized to a fictional cadence. | `funding-quarantine/inventory.json` |

Kraken members were fetched by byte ranges from a five-part ZIP and `zipfile` checked each selected member's CRC32. A local SHA-256 was computed for each extracted raw member. The publisher's complete-archive SHA-256 was **not** verified because the complete roughly 9 GiB archive was not downloaded. CRC32 is not cryptographic authenticity. Preserve the source file, member identity, local hash, provider statement, gap ledger and indexed copy together. The 8,266,148 count is observations, not 8,266,148 independently executable trades.

The official [Jito deployed-programs page](https://www.jito.network/docs/jitosol/jitosol-liquid-staking/security/deployed-programs/) and [OKX spot listing](https://www.okx.com/help/okx-to-list-jitosol-jito-staked-sol-for-spot-trading) both identify Solana mainnet JitoSOL mint `J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn`. This resolves the prior exchange-ticker identity question. Older OKX script descriptions still say the identity was unverified; that historical text is superseded by these sources, not rewritten provenance. The [official staking app](https://www.jito.network/staking/) describes the liquid staking token; its exchange rate is not the same thing as an observed exchange fill.

**Do not use** stores whose names contain `boundary-omission-v1`: the earlier collector used `endAt=hi-60` and skipped a minute per window. A live boundary check established the tested API's exclusive end behavior; schema 2 requests `endAt=hi` and rejects incompatible old metadata. Preserve the quarantined files for diagnosis. Likewise, `deep-snapshots.sqlite` contains earlier slash-delimited labels rejected by `SnapshotLoader`; use the verified `deep-snapshots-v2.sqlite` and its IDs instead. The live catalog contains an older sentence saying backups are on the same machine; the later off-machine backup section supersedes that sentence.

## Operating the existing modules

Run from the repository root with the backtester dependencies installed. This machine's previously used interpreter is `/Users/mitch/.venvs/solmargintrader-docs/bin/python`; it is an environment-specific path, not a repository dependency. `python -m backtester.core.kucoin_history --help`, `python -m backtester.core.history_store --help`, and `python -m backtester.core.run_archive --help` describe their actual arguments.

### Verify a saved snapshot and query a segment

The following read-only example was run successfully against the local artifacts. Full `snapshot_info` hashes every stored bar, so a large snapshot can take time. Do not modify the files while verifying them.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c1b1
/Users/mitch/.venvs/solmargintrader-docs/bin/python - <<'PY'
from pathlib import Path
from backtester.core.history_store import snapshot_info
from backtester.core.segmented_history import read_range
root = Path('/Users/mitch/.local/share/solmargintrader/historical-data-1128')
snapshot = '2ccb359d87420a9a28baac2a1affef7f0f39cc867fe39aaad784dab655555425'
print(snapshot_info(root / 'backtest-ready/deep-snapshots-v2.sqlite', snapshot))
print(read_range(root / 'kucoin-sol-usdc-deep/segments', 1653292800, 1653292800))
PY
```

Expect `instrument: SOL-USDC`, interval 60, count 2,349,374, and one first-bar tuple. A `SegmentError` means the selected interval is invalid, absent, noncontiguous or corrupt; do not work around it with an interpolated candle. The segment index verifies touched segments, not the entire upstream provider.

### Run and archive a reproducible smoke test

The command below uses the verified deep snapshot and creates a **new** result directory and archive. Pick unused private paths if repeating it; do not overwrite the existing smoke evidence. Set assumptions deliberately. Here 6 bps fee and 2 bps slippage are illustrative, not measured costs.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c1b1
/Users/mitch/.venvs/solmargintrader-docs/bin/python -m backtester.cli \
  --asset SOL --quote USDC --start 2026-11-01 --end 2026-11-01 \
  --interval 1m --history-archive /Users/mitch/.local/share/solmargintrader/historical-data-1128/backtest-ready/deep-snapshots-v2.sqlite \
  --snapshot-id 2ccb359d87420a9a28baac2a1affef7f0f39cc867fe39aaad784dab655555425 \
  --strategy buy_and_hold --fee-bps 6 --slippage-bps 2 --fill-delay 1 \
  --out /Users/mitch/.local/share/solmargintrader/historical-data-1128/backtest-ready/example-new-output \
  --archive /Users/mitch/.local/share/solmargintrader/historical-data-1128/backtest-ready/example-new-runs.sqlite --no-charts
```

The observed prior run produced `run_manifest.json`, `comparison.csv`, `trades_buy_and_hold.csv`, `equity_buy_and_hold.csv`, `report.md`, and an archive ID. The manifest records 1,440 bars, costs, seed, split, library versions and the snapshot ID. It is not a complete reproducibility attestation: an independently bound source-code revision, all dependencies and every execution assumption remain future work.

To re-read the **existing** archived smoke evidence and verify its four manifest-listed artifacts:

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c1b1
/Users/mitch/.venvs/solmargintrader-docs/bin/python - <<'PY'
from backtester.core.run_archive import read_run
archive = '/Users/mitch/.local/share/solmargintrader/historical-data-1128/backtest-ready/deep-smoke-runs.sqlite'
run = 'd37b58aea6dffecf1fa744127ce1cb67b7a3a7503dae68e0fd9668a0ea659137'
manifest, artifacts = read_run(archive, run)
print(sorted(artifacts))
PY
```

`backup_archive(source, destination)` is the Python API for a consistent SQLite copy. It refuses an existing destination, runs `PRAGMA integrity_check`, verifies every stored run and, when present, every history snapshot. Copying the resulting file to a separate machine and testing recovery are separate operations.

### Collect and audit a new KuCoin range

Collection is an explicit network operation. Set one private `KUCOIN_HTTP_LOCK` path for **all** cooperating collectors; the `fcntl` lock serializes requests and stays held through rate-limit backoff. Processes that do not use that path are not coordinated. Pick UTC minute-aligned bounds with a closed exclusive end, a new private database, and an existing private parent. A page window is at most 1,440 minutes; the collector retries bounded 429/5xx/network failures and commits each page with its normalized rows. Keep identical bounds on resume, especially for a partial last page. A source correction that conflicts with an existing verified page is an error, not an in-place revision.

```bash
# Example only: replace all three placeholders with a completed UTC range and new private path.
KUCOIN_HTTP_LOCK=/private/path/kucoin-http.lock python -m backtester.core.kucoin_history \
  /private/path/SOL-USDC.sqlite --symbol SOL-USDC --start START_EPOCH --end END_EXCLUSIVE_EPOCH
```

`audit_store(database, symbol, start, end, gap_file)` is a Python API, not an audit subcommand. It verifies pages and normalized rows and creates a **new** gap file; it refuses an existing ledger. `UNFETCHED` means a page was not committed. `UNOBSERVED` means a committed response omitted a slot, which is not by itself proof of no trades. `read_range` verifies touched page bytes and normalized values, then refuses any missing minute. Never treat a successful HTTP response or the number of rows alone as proof of a complete range.

### Import a new contiguous CSV

After independently checking identity, cadence, boundaries and source provenance, invoke `python -m backtester.core.history_store ARCHIVE CSV --instrument SOL-USDC --venue kucoin --source 'specific source and revision' --interval-seconds 60`. The CSV is unchanged by import; save the printed snapshot ID and source receipt. Use `segmented_history.build` for genuinely gapped source files, not as a way to make a contiguous snapshot appear complete. Its destination directory must not already exist. If a build fails, inspect its `.partial` files and use a fresh destination; do not mix partial and completed data.

## One-off acquisition scripts

These scripts were created for this session and are saved with the private evidence; they are **not maintained repository commands**. They have hard-coded local paths, market names, dates, output directories or upstream archive layout. Read them and their receipts before reuse. They do not implement an automatic recurring refresh service.

- `/Users/mitch/.local/share/solmargintrader/historical-data-1128/collect_jitosol.py` collected OKX JITOSOL/USDT hourly and recent minute pages, saved raw JSON pages, parsed confirmed candles through `backtester.core.fetch_minutes_alt._okx_rows`, and built indexed segments. It uses `mkdir(exist_ok=False)` and a fixed hourly start; rerunning it at the existing destination fails. Its description predates the mint verification above.
- `/Users/mitch/.local/share/solmargintrader/historical-data-1128/resume_jitosol_minute.py` was a specific recovery for the fixed `[1791663600,1794255600)` range. It reuses numbered response pages and retries network failures. It opens its final source file with exclusive creation and is **not** a safe general rerun after completion or with unrelated saved pages.
- `/Users/mitch/.local/share/solmargintrader-backups/kraken_zip_reader.py` implements a seekable read over five specific Kraken archive parts using `curl` range requests. Its part sizes, URL and market list were bound to the 2026-09-30 archive. `python /Users/mitch/.local/share/solmargintrader-backups/kraken_zip_reader.py` lists the specific markets if that exact upstream archive remains available; it performs network reads. Confirm part sizes, version, server range behavior and checksums before adapting it to a newer archive.
- `/Users/mitch/.local/share/solmargintrader-backups/extract_kraken_ohlcvt.py` imports that reader, selects 14 hard-coded Kraken member names, checks ZIP member CRC through full extraction, writes canonical CSV and gaps, builds segments and writes receipts. Existing `receipt.json` files are skipped; incomplete directories and `.partial` files need explicit inspection. It hard-codes the backup helper path and output root, so invoking it after relocation or on another archive without adaptation is unsafe. At creation it required `PYTHONPATH` to include the repository root. The scripts are also in the supplemental GitHub backup.

To inspect the original Kraken market list, run the reader command above. The original extraction was invoked from the repository root as shown below. On the current machine it skips directories with a `receipt.json`; that skip does not re-verify a receipt. Run it only against an explicitly prepared, private destination after reviewing and changing its hard-coded root and fixed archive parameters. It cannot safely refresh an existing directory or recover every partial failure automatically.

```bash
cd /Users/mitch/dev/solmargintrader-wt-01a1c1b1
PYTHONPATH=/Users/mitch/dev/solmargintrader-wt-01a1c1b1 /Users/mitch/.venvs/solmargintrader-docs/bin/python /Users/mitch/.local/share/solmargintrader-backups/extract_kraken_ohlcvt.py
```

The two OKX scripts can similarly be invoked with `PYTHONPATH` set to the repository and the same Python interpreter, followed by the script's absolute path; first edit a separate copy to use a fresh root and appropriate fixed bounds, and revalidate paging. Do not run the existing scripts unchanged over the retained evidence. Their page files are evidence from a particular execution, not a general API contract.

The Binance public archive is a candidate for more coverage, not a completed ingestion. Its [publisher documentation](https://github.com/binance/binance-public-data) says spot timestamps from 2025-01-01 use microseconds and each ZIP has a checksum; corrections can replace historical files. Check venue, legal terms, symbol, timestamp units, source revision, gaps and available data before building a new importer. Never merge a different market's bars into a gap as if they were the original venue's observations.

## GitHub backup and restore

The owner selected GitHub for off-machine backup. The [private backup release](https://github.com/mithudso/solmargintrader-history-backups/releases/tag/historical-data-20261109) contains:

| Asset | SHA-256 | Contents |
| --- | --- | --- |
| `historical-data-20261109.tar.gz` | `eb521363267949dcfbbf49b466bfa04d8adcc05f0786c19f56e8d192dddc8f35` | Initial `historical-data-1128` and `backtester-task-1117` trees, including source and quarantine evidence. |
| `kraken-ohlcvt-20260930.tar.gz` | `fd63daee65c3128249a02d0f1d7b3f94b58140cdb4d54babc76851acd973638a` | Kraken extracts, indexes, gaps, catalog and one-off acquisition scripts. |
| Companion `.sha256`, `CATALOG-current.md`, `RESTORE.md`, `restore-metadata.sha256` | See release assets | Checksums and extraction order. |

Both archives were independently downloaded from GitHub, checked against their SHA-256 files, and tar-listed. A SOL/USDC SQLite snapshot from the downloaded base archive and a Kraken segment index from the downloaded supplemental archive matched their local originals byte for byte. This was a representative member read-back, **not** a demonstrated full restore of every file on a separate machine. SQLite integrity and full snapshot/run verification should be repeated in the restored environment. This is a point-in-time backup, not continuous replication; newly acquired files require a new backup and restore test.

For a clean recovery, download the release assets into an empty private directory, check `shasum -a 256 -c` on each companion checksum, extract the base archive into a new restore parent, extract the Kraken archive into its restored `historical-data-1128` directory, then copy `CATALOG-current.md` to `historical-data-1128/CATALOG.md`. Follow the release's `RESTORE.md`; do not extract over the only existing copy. The backup repository is private, but GitHub access is subject to the owner's account, credentials, retention and service availability.

## Verification and incidents

- Snapshot and archive tests cover invalid rows, gaps, duplicate imports, metadata/content mismatch, tampering, transaction rollback, unsafe paths, private file modes and backup reads. KuCoin and segment tests cover provider page validation, boundary semantics, retry behavior, local HTTP simulation, source replay, concurrent same-page handling, corruption and gap refusal. The previous final backtester suite passed 999 tests; the subsequent PR 178 CI and documentation checks passed. Counts describe that checkpoint, not a promise about future revisions.
- A real live boundary test caught the `hi-60` omission before accepting the corrupted collection. Older schema-1 stores remain quarantined. Two collectors also raced on `pages.start`; `BEGIN IMMEDIATE` plus source/row comparison now allows only equivalent concurrent results and rejects conflicting responses.
- A real CLI smoke caught `snapshot must match the requested asset and quote` when the deep snapshot used `SOL/USDC`. The `SnapshotLoader` contract requires `SOL-USDC`; a corrected v2 snapshot was created and tested without deleting the original evidence.
- Re-reading the 2,349,374-bar v2 snapshot, querying its first segment and re-verifying all four saved smoke artifacts succeeded during this handoff. Local SQLite integrity checks and first/last segment reads were performed for all 14 Kraken indexes. These are integrity and plumbing checks, not an independent market-data quality audit.
- Postman CLI was unavailable and the Orbit API returned HTTP 403 during the acquisition work. The API work instead used provider documentation, live boundary probes and local HTTP simulation; do not claim Postman simulation passed.

## Streaming oracle or periodic refresh?

Use both as complementary inputs. A continuous stream can capture higher-frequency observations and fresh evidence for forward testing; scheduled source refreshes provide historical backfill, corrected bars and recovery after disconnects. Persist raw stream events with event time, receive/availability time, source, market, sequence where available and explicit gaps. Validate and reconcile each time range against an appropriate historical source, then publish immutable, content-addressed snapshots. A backtest pins one snapshot and runs offline, so a new quote or correction cannot change a run in progress. A correction produces a new revision, leaving the old run reproducible. Streaming alone cannot reconstruct years before recording began; periodic OHLCV alone cannot reconstruct the actual book or every fill.

The existing `soltui/pricefeed.py` recorder is an integration candidate, not a reason to start a second recorder. Its source code records Coinbase `level2_batch` book tops and ticker last prices in gzip JSONL and maintains a recorder lock. Confirm the loaded service, health, products, timestamps, retention, outages and actual SOL/USDC coverage before relying on it. The project previously found that ticker bid/ask can remain stale between trades on thin pairs; book-top freshness and feed sequence/reconnection checks matter. A generic oracle may publish a reference or aggregated price rather than the executable venue price, volume or order book; identify its actual source and semantics before using it as fill evidence. Do not route live streaming into the offline replay loop or infer historical fills from a reference price.

This is a design recommendation, not an implemented integration. Define who owns the recorder and ingestion interface with the forward-testing and signal sessions, then test reconnect, duplicates, ordering, gaps, late arrivals, clock skew, backfill, snapshot publication and backup before enabling it.

## Future implementation and acceptance gates

1. **Source coverage and revisions.** Build a maintained source registry with exact instrument IDs, venue, quote, chain/mint when applicable, timestamp semantics, availability/retrieval times, license and version. Measure coverage per market, refresh completed bars incrementally, retain raw provider revisions, and report provider gaps separately from unfetched windows and verified no-trade periods. Investigate Binance and other sources without silently substituting their prices. Back up every new revision.
2. **Storage and performance.** Add a stable query/inventory interface over snapshots and segments. Support immutable correction revisions and atomic publication. Benchmark representative multi-year, multi-asset ingestion and reads, peak memory, disk usage, crash recovery and concurrent access. Full snapshot rehash on every read is safe but potentially costly. Verify permissions, isolation, independent backup restoration and recovery after partial writes.
3. **Causality.** Define event time, publication/availability time and decision time separately. Test that changing future data cannot alter earlier decisions across indicators, cross-asset joins, resampling, normalizers, labels, training and strategy adapters. Check bar close boundaries and any provider corrections. Reject unobservable future information.
4. **Ledger and execution fidelity.** Establish a canonical per-order/fill ledger with venue, chain when supported, timestamp, quote/base amounts, balances, fees and explicit valuation. Reconcile realized and unrealized P&L, equity and positions against hand-calculated fixtures. Add historical fee tiers, spreads, liquidity and borrow/funding evidence only when actually sourced. Define partial fills, latency, failed transactions and intrabar ambiguity; refuse unsupported models rather than label assumptions as facts.
5. **Bots and adverse scenarios.** Inventory actual strategy and bot contracts and route each to its compatible engine. Preserve the grid-extension economic parity. Add deterministic seeded outage, latency, slippage, gap, failed-fill and partial-fill scenarios, with explicit assumptions and recorded seeds. OHLCV alone cannot reconstruct depth or all on-chain behavior.
6. **Results and validity.** Bind the exact source revision, snapshot IDs, code revision, dependencies, strategy configuration, cost model, seed, timestamps and artifacts to a run. Add realistic benchmarks, independent review and repeatability checks. Separate exploratory, in-sample and untouched out-of-sample periods; report selection bias, sample size, drawdowns and uncertainty rather than promising future profits.
7. **Integration and operations.** Agree a narrow, versioned history/result interface with the separate signal, forward-testing, UI and orchestration owners. Keep simulation offline and fail closed. Add scheduling only when explicitly designed, with monitoring, retry limits, integrity alerts, fresh GitHub backups and periodic independent restore drills. Avoid modifying other live sessions or their data stores.

The umbrella historical-backtester task remains `TASK-1117`; the coverage task remains `TASK-1128`. Their records are continuation aids, not substitutes for source verification. PRs 174, 176, 177 and 178 are merged checkpoints, not evidence that these future gates have passed.
