# External calls

Inventory reviewed against source on 2026-11-06. A call includes public HTTP/RPC,
MongoDB, browser/OS services, and child processes. The tables name the transport
boundary and the logical callers that share it; they do not count each RPC inside a
Multicall3 batch as a separate transport implementation.

The simulation engines remain offline. Explicit fetch commands, including fetches
started from soltui, write caches before simulation. Liquidity dry-run is different:
it calls live RPC and `eth_simulateV1` but does not sign or send a transaction.

## Public HTTP

| ID | Source / logical caller | Target and transport | Timeout / retry | Log / tests / documentation |
| --- | --- | --- | --- | --- |
| H1 | `backtester/core/fetch.py:48` `_get_json`; `fetch_coinbase` | Coinbase Exchange candles, urllib | 20s; 3 attempts, linear backoff | CLI progress; no dedicated helper-transport test; `docs/SCRIPTS.md` |
| H2 | `backtester/core/universe.py:159` `list_coinbase_products` | Coinbase products through H1 | H1 policy | CLI availability/refusal; `backtester/tests/test_universe.py` injects JSON; `docs/SCRIPTS.md` |
| H3 | `backtester/core/ticks.py:73` `_trade_page` | Coinbase trades through H1 | H1 policy; cursor paging and pauses | CLI progress; `backtester/tests/test_ticks.py`; `docs/SCRIPTS.md` |
| H4 | `backtester/core/fetch_minutes.py:130` `get_candles` | Coinbase minute candles, urllib | 3s; bounded attempts, rate limiter, 429/5xx backoff | Per-fetch coverage/outcome; `backtester/tests/test_fetch_minutes.py`; `docs/SCRIPTS.md` |
| H5 | `backtester/core/funding.py:141` `_post_json` | Hyperliquid `/info`, urllib POST; metadata and funding pages | 30s; 4 attempts with exponential backoff | CLI per-asset outcomes; transport coverage not independently established; module docstring |
| H6 | `backtester/core/funding.py:280` `fetch_okx_funding` | OKX funding-history cross-check, urllib | 25s; no retry | CLI outcomes; no dedicated transport test; module docstring |
| H7 | `backtester/core/archive_price.py:62` | Jupiter Price v3 snapshot, urllib | Caller timeout; no retry | stdout CSV snapshot; no dedicated transport test; module docstring |
| H8 | `extension/src/jupiter/price.js` via `http.js` | Jupiter keyed/lite Price v3, fetch | 15s/attempt including body read; bounded GET retries with jitter | Redacted structured attempt/outcome diagnostics; `extension/test/http-audit.test.js`; `extension/README.md` |
| H9 | `extension/src/jupiter/trigger.js` via `http.js` | Jupiter Trigger v2 auth/vault/deposit/create/list/history/cancel/withdraw, fetch | Shared deadline; only GET/HEAD retry, writes never auto-replay | Redacted transport diagnostics and journal/tick events; `extension/test/trigger-audit.test.js`, `http-audit.test.js`; `docs/jupiter-trigger-contract.md` |
| H10 | `extension/tools/verify-endpoints.js` | Manual Jupiter reachability, direct fetch plus keyed price client | Direct reachability fetches have no explicit deadline/retry; keyed price uses H8 | stdout; manual/informational CI only; `docs/TESTING.md` |
| H11 | `liquidity/src/aero_lp/market.py:38` `MarketData._get` | GeckoTerminal token prices, pool info, hourly closes, Aero pool discovery, httpx | 20s client; 4 attempts for 429; TTL and pacing | No per-request structured sink; `liquidity/tests/test_market_state.py`, `test_metrics.py`; `liquidity/README.md` |
| H12 | `liquidity/src/aero_lp/providers.py:395` `load_llama` | DefiLlama yield pools, httpx | 120s; 6h disk cache, explicit refresh; no retry | Comparison report source metadata; `liquidity/tests/test_providers.py`; `liquidity/README.md` |
| H13 | `liquidity/src/aero_lp/providers.py:587` `LlamaPrices.current` | DefiLlama current token prices, httpx | 30s; batches, in-memory cache; failures can omit prices | No per-request structured sink; `liquidity/tests/test_providers.py`; `liquidity/README.md` |
| H14 | `liquidity/src/aero_lp/providers.py:603` `LlamaPrices.hourly` | DefiLlama chart prices, httpx | 40s; in-memory cache; no transport retry | No per-request structured sink; `liquidity/tests/test_providers.py`; `liquidity/README.md` |
| H15 | `liquidity/src/aero_lp/providers.py:1100` `gt_dex_pools` | GeckoTerminal cross-provider discovery through H11 | H11 policy | Comparison report; `liquidity/tests/test_providers.py`; `liquidity/README.md` |

H9 is a money-moving boundary. Reconciliation treats the venue's order list as truth;
its wallet-specific live responses and fee attribution remain unverified. A timeout after a
write is not proof that the write failed. Never retry an ambiguous order submission
without reconciliation. Generic read retry policies must not be assumed safe for writes.
The bundled signer cannot verify the economic intent of server-crafted transactions.
The Trigger venue refuses live deposit/cancellation signing until a trusted verifier
implements the required interface. Public-contract fixtures do not establish live acceptance.

## Base RPC and contract calls

`liquidity/src/aero_lp/chain.py:146` builds Web3's HTTP provider with a 30s timeout,
6 configured retries and 0.8 backoff factor. The provider decides which methods are
retryable. The rows below share that provider. The configured chain must be Base;
contract addresses live in `liquidity/src/aero_lp/addresses.py`.

| ID | Source / logical calls | Target / effect | Log / tests / documentation |
| --- | --- | --- | --- |
| R1 | `chain.py:169`, `head`, `check_fresh`, `verify_deployment` | Chain id, head block, code, NPM factory; read-only | CLI verify output; `liquidity/tests/test_chain_vol.py`, `test_network.py`; `liquidity/README.md` |
| R2 | `chain.py:188` `multicall`; `token`, `pool_state`, `position`, `erc20_balances`, `fee_growth_delta` | Multicall3 aggregate3 eth_call, optionally at a historical block | No universal per-call sink; chain/metrics/network tests; `liquidity/README.md` |
| R3 | `chain.py:253`, `twap_tick_series`, `positions_of`, `gauge_aero_per_day`, `gas_price_wei` | Factory lookup, observe, wallet/staked NFTs, historical gauge emissions, gas; read-only | Evaluation/daemon outcomes; chain/network tests; `liquidity/README.md` |
| R4 | `liquidity/src/aero_lp/providers.py:289`, `read_v3_pool`, `find_v3_pools`, `read_v4_pool` | Comparison venue code/registry/pool/growth reads through Web3 and R2 | Provider report diagnostics; provider unit/network tests; `liquidity/README.md` |
| R5 | `liquidity/src/aero_lp/daemon.py:180`, `207`, `354` | Pool tick spacings and native ETH balance; read-only | Daemon ledger/events and stdout; `liquidity/tests/test_daemon.py`; `liquidity/README.md` |
| R6 | `liquidity/src/aero_lp/executor.py:91` `SimRunner` | Base block read and `eth_simulateV1`; no signature or broadcast | Stage result / simulation error; `liquidity/tests/test_executor.py`, `test_network.py`; `liquidity/README.md` |
| R7 | `executor.py:152`–`205` `LiveRunner` reads | Timestamp, pending nonce, estimate gas, transaction visibility, base/priority fees | Stage result/errors; executor tests; `liquidity/README.md` |
| R8 | `executor.py:206` `LiveRunner.execute` | Sign locally, `eth_sendRawTransaction`, wait for receipt, read post-state | Transaction hashes + stage callbacks/ledger; executor tests; `liquidity/README.md` |

Paths abbreviated to `chain.py` and `executor.py` in this table mean
`liquidity/src/aero_lp/chain.py` and `liquidity/src/aero_lp/executor.py`.
R8 uses `ExecConfig.receipt_timeout_s` for receipts and bounded same-byte rebroadcast;
callers must surface partial sequences and reconcile before another sequence. A mined
receipt and changed balances are evidence about the chain; persisting a ledger row alone
is not evidence that a transaction landed.

## Local services, subprocesses and storage

| ID | Source | Boundary / effect | Timeout, retry, log and verification |
| --- | --- | --- | --- |
| L1 | `mongo/schema.py:357` `connect`; `create`; `mongo/load.py:728` | Local MongoDB selection, selected collection drop/create/index/insert | 3s server-selection timeout; loader prints counts; `mongo/tests/test_load.py` checks idempotency/provenance/validation with a server; no common error sink |
| L2 | `mongo/load.py:124`, `639`, `656` | Git provenance and optional Python/Node suite subprocesses | Captured output; test suite invocations have no explicit timeout; `--run-tests` is explicit; loader docs |
| L3 | `backtester/core/data.py:36` | Git common-dir lookup to locate the shared CSV cache | 10s; falls back to local path; data/worker tests exercise consumers |
| L4 | `research/tick_backfill.py:271` | Gap-audit subprocess after tick backfill | 1800s; captured result/timeout; `backtester/tests/test_tick_backfill.py`; `docs/SCRIPTS.md` |
| L5 | `soltui/bgcontrol.py:224` `start` | Detached offline sweep subprocess with inherited lock FD | No overall timeout; cooperative stop; `worker.log`; `soltui/tests/test_bgcontrol.py`, `test_bgworker.py` |
| L6 | `soltui/bgcontrol.py:294` `start_fetch` | Explicit sequential fetch subprocess; reaches H1 | No overall timeout; per-request H1 timeout; `fetch.log`; bgcontrol tests |
| L7 | `soltui/live_run.py:76` | Node extension dry-run subprocess (no live order submission) | No explicit timeout; captured stdout/stderr; may fetch public prices; selected strategy argument is not a verified simulator contract |
| L8 | `soltui/tui.py:1122` | Manual untested-strategy sweep subprocess | Captured output; no explicit timeout; `soltui/tests/test_tui.py` |
| L9 | `soltui/app.py:158`, `194`; `soltui/serve.py` | Browser-console subprocess, osascript Terminal opening, loopback textual-serve/webbrowser | Console startup probe / osascript timeout; app stderr; packaging/browser acceptance remains manual |
| L10 | `soltui/make_icon.py:253`; `soltui/soltui-service` | macOS iconutil, py2app, launchctl service lifecycle | Build/service output; service/plist tests; installed bundle still needs acceptance |
| L11 | `liquidity/src/aero_lp/wallet.py:33` | macOS Keychain via `security`; sensitive stdout consumed in-process | 20s; no retry; never print/copy returned key; `liquidity/tests/test_abi_config_wallet.py` |
| L12 | `liquidity/scripts/aero-lp-service` | launchd install/status/kill/resume/uninstall | Service stdout and `daemon.log`; installer defaults live; manual service acceptance |
| L13 | `extension/src/storage/store.js`, `fileStore.js` | IndexedDB, chrome.storage.local, CLI/API mode-0600 files | Persist intents before submit; local state is a cache; core/surface/service-worker tests |
| L14 | `liquidity/src/aero_lp/state.py`, `ledger.py`; `soltui/liquidity.py` | Atomic daemon state files and SQLite ledger; TUI creates/removes KILL only | State schema/read-back and ledger tests; `liquidity/STATE_FILES.md`, `soltui/tests/test_liquidity.py` |
| L15 | `index/build.py`, `index/search.py` | Optional local Ollama embedding HTTP calls | Explicit semantic modes only; not run by offline builds; `index/README.md` |

Extension Chrome alarms/messages/storage are platform boundaries described in
`extension/README.md`. The local HTTP listener in `extension/tools/api-server.js` is
an inbound boundary: bearer token, loopback default and browser-origin rejection. The
optional soltui browser listener is likewise loopback. Neither is a hosted service or
an MCP server. Maintenance tools may read Git or local files; they must not start
inference, watchers or services simply because an entry point exists.

## Five-standard audit

The full mdb-tam contract requires an operation registry, a CLI/MCP trigger per
operation, a central JSONL error sink, a remediation map, a generated dashboard card,
and explicit datastore verification. **This repository does not pass that contract.**
Its existing component boundaries do not implement that server infrastructure.

| Call IDs | Trigger | Central errors | Remediation map | Per-call dashboard | Landed verification |
| --- | --- | --- | --- | --- | --- |
| H1–H7 | Explicit data CLIs | Missing | Missing | Missing | Schema/coverage checks vary; no universal post-write read-back |
| H8–H10 | Shared command registry / probe | Partial tick events | Missing | Tick state only | Venue reconciliation; response envelope still unverified |
| H11–H15, R1–R7 | Liquidity CLIs / daemon | Partial ledger/stdout | Missing | Summary via soltui | Read-only calls need no persisted-data check; snapshots/schema are separate |
| R8 | Rebalancer + live Runner | Ledger/stage outcomes | No registry map | Action summary | Receipts/post-balances plus ledger; ambiguous partial sequences remain explicit |
| L1–L4 | CLI helpers | stdout/captured output | Missing | Missing | MongoDB integration tests; no universal runtime read-back |
| L5–L10 | TUI/service/CLI | Worker/service logs | Missing | Worker status, not call cards | Completion/status varies; not the five-standard contract |
| L11–L15 | In-process helpers or explicit CLI | Component-specific | Missing | Missing | Read-only probes N/A; state/ledger/index checks exist |

Each missing cell is a remaining standards gap, not an implied implementation or a
claim of safety. Retrofitting a server, generated cards and a common remediation
engine changes architecture and stays a separate design task. Never attach generic
auto-retry to R8 or Trigger write operations. The current audit and code-optimizer
report track smaller grounded fixes separately.

## Adding a call

1. Reuse the owning component's transport and preserve explicit offline/live boundaries.
2. Set a timeout and distinguish retry-safe reads from ambiguous side effects.
3. Record request/outcome metadata without headers, credentials, passphrases or key material.
4. Test failure and success against fakes; public outages must not fail offline CI.
5. Add its row, test path, retry policy and verification limits here.

This inventory is manually reviewed. `scripts/check_docs.py` checks counts and retrieval
paths, not transport coverage; a new external call does not automatically fail CI.
