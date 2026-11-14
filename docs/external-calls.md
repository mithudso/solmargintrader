# External calls

The original inventory was reviewed on 2026-11-06. The managed-suite, Oracle
and ecosystem boundary supplement below was reviewed on 2026-11-10. A call includes public HTTP/RPC,
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

## Managed suite, Oracle and ecosystem supplement — 2026-11-10

This supplement inventories the verified new transport owners below. It is not a
claim that every call site in the expanded repository has been exhaustively
classified. Existing rows retain their dated source references. The five-standard
assessment remains incomplete where central operation metadata is absent.

| ID | Source / logical boundary | Target and effect | Bounds, diagnostics and verification |
| --- | --- | --- | --- |
| N1 | `oracle/feeds.py` `_get_json`, `JupiterPriceFeed.poll` | Explicit Jupiter Price V3 HTTP GET, reference prices only | Default 5s, capped at 15s; response bound; redirects refused; fixed credential-free failures; no helper retry; `oracle/tests/test_feeds.py`, `oracle/README.md` |
| N2 | `oracle/server.py` `build_server`, `serve` | Local stdio MCP tools, resources and subscription notifications | Read-only tools; standalone startup may initialize archive schema; bounded history and subscriptions; fixed public failures; real SDK tests in `oracle/tests/test_server.py` and `oracle/tests/test_selected_server.py`; `docs/MCP.md` |
| N3 | `botmanager/src/botmanager/transport.py` `request` | Same-user manager Unix socket commands | Bounded request/response sizes and deadlines, verified peer/owner; existing manager commands own mutation semantics; `botmanager/tests/test_supervisor.py`, `botmanager/README.md` |
| N4 | `botmanager/src/botmanager/suite.py` `Suite`, `_start`, `_stop` | Suite control Unix socket and installed availability process | Private lease/generation checks; singleton launch; only owned Popen children may be terminated; durable component alerts; `botmanager/tests/test_suite.py`, `docs/bot-manager-managed-suite.md` |
| N5 | `botmanager/src/botmanager/suite_service.py` `_invoke` | Fixed launchctl/systemctl user-service lifecycle | 5s invocation bound; command result/registration checks and separate Linux enablement verification; no generic retry; `botmanager/tests/test_suite_service.py`, `docs/bot-manager-managed-suite.md` |
| N6 | `ecosystem/ui_service.py` `_health`, `ensure` | Loopback HTTP identity GET and installed UI process | 0.4s HTTP probe, bounded body, no redirect/proxy; lock/checkpoint/version/manager-home identity; bounded startup; adopted PIDs are not killed; `ecosystem/tests/test_ui_service.py`, `docs/ECOSYSTEM-WIKI.md` |
| N7 | `ecosystem/installation.py` `_command`, `verify_environment` | Explicit venv/pip installation and installed-runtime/MCP verification subprocesses | Separate bounded creation/install/health deadlines, output cap and child reap; receipts validate package identity; bootstrap start is explicit; `ecosystem/tests/test_setup.py`, `docs/ECOSYSTEM-BOOTSTRAP.md` |
| N8 | `botmanager/src/botmanager/research_owner.py` `OwnerClient.call` | Reviewed installed research-owner subprocess protocol | Fixed isolated module launch and narrow environment, 120s bound, identity checks and fixed refusal; no inferred retry of a final-evidence action; `botmanager/tests/test_research.py`, `botmanager/README.md` |
| N9 | `soltui/native_host.py`, `soltui/native_host_install.py`; `extension/src/core/control-room.js` | Chrome native-messaging suite status/health/explicit start | Origin allowlist and fixed locally bound homes; no browser-supplied command/path/URL; missing helper stays unknown; `soltui/tests/test_native_suite.py`, `extension/test/control-room.test.js`, `docs/bot-manager-managed-suite.md` |
| N10 | `ecosystem/telemetry.py`, `ecosystem/control.py` | Sanitized SQLite event mirror and durable local action receipts | Bounded cursors, explicit unavailable states and owner-scope checks; original evidence stays with owner; `ecosystem/tests/test_telemetry.py`, `ecosystem/tests/test_control.py`, `docs/ECOSYSTEM-CONTROL-ROOM.md` |

N2 is the repository's actual MCP server. It does not make the extension HTTP API
or manager socket into MCP services. N4 starts availability, not a recorder or
research optimizer. N5 does not authorize changing a bot's desired intent. The
suite can restart its own UI child; an incompatible or hung adopted owner remains
a refusal rather than a target for guessed-PID termination.

None of N1–N10 establishes a common five-standard operations registry. Component
CLI registries, typed errors, durable action journals and summary health cards are
useful implementations, but do not substitute for one generated per-call inventory,
central JSONL failure schema, complete remediation map or generated call cards.
Persistent data/evidence paths have their own verification tests; this review does
not infer universal datastore verification from the presence of those tests.

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

## SolTUI Base wallet discovery

`soltui/wallet.py:HttpFetcher.base_token_balances` invokes the configured `cdp data evm token-balances
base <public-address> pageSize==100 [pageToken==<cursor>]` read command. The independent CDP CLI owns
API authentication. SolTUI never loads its credentials or a wallet key. Each subprocess has closed
stdin, no shell, captured output, a deadline, and sanitized errors. Discovery follows at most 25 pages.
If CDP fails, the scanner tries paginated Blockscout and public RPC checks for trusted/requested tokens.
Unknown indexed tokens cause no contract calls. DefiLlama price URLs contain at most 40 identifiers.
`soltui/tests/test_wallet.py:BaseDiscoveryTests` covers pagination, partial failures, malformed amounts,
read-only argv, credential-safe errors and the unsolicited-contract boundary.

## TradingView venue boundaries (reviewed 2026-11-11)

These additions describe the actual transport implementations. They do not
establish a generated per-call registry or a shared error sink.

| ID | Source / logical caller | Target and transport | Timeout / retry | Log / tests / documentation |
| --- | --- | --- | --- | --- |
| W1 | `oracle/webhook.py:134` `serve`, `Handler.do_POST` | Loopback TradingView HTTP ingress; external tunnel is independently managed | 4096-byte body, 5s socket timeout before request parsing, maximum16 concurrent request threads, 300s past/30s future window; excess sockets close without parsing; no sender replay by receiver | Durable deduplicated signal and fixed response; access logs deliberately disabled to exclude the body secret; `oracle/tests/test_webhook.py`; `docs/JUPITER-ZEC-WEBHOOK.md` |
| W2 | `oracle/coinbase_orders.py:117` `_invoke` | Authenticated official Coinbase CLI subprocess; balance/product/order reads and one create | 30s subprocess deadline, capped captured output, no shell; no automatic submit retry | Sanitized fixed failure and durable intent/result in `oracle/webhook_orders.py`; `oracle/tests/test_coinbase_orders.py`, `test_webhook_orders.py`; `oracle/README.md#tradingview-webhook` |
| W3 | `oracle/gum_orders.py:171` `_http`, `discover`, `GumOrders` | Owner-scoped GUM market/health/account/position/order-history GET and `/order/create` POST | 15s transport deadline, 2MiB response bound, redirects refused; no automatic POST retry | Fixed credential-free failure; per-leg journal retains acceptance, fills, actual fee and public transaction signatures; no common per-request attempt sink; `oracle/tests/test_gum_orders.py`, `test_gum_webhook_orders.py`; `docs/JUPITER-ZEC-WEBHOOK.md` |

GUM order Actions are constructed locally and signed only after account, market,
lot, collateral, cost and final signal checks. Neither W3 nor the optional private
loader verifies an opaque server-built funding transaction. An ambiguous POST,
missing history or partial close holds the next open; a public API acknowledgment
is not fill evidence. Account provisioning, GUM application-wallet funding and
perps collateral deposits are separate operations and are not implemented by the
order adapter. Coinbase portfolio transfers are not onchain withdrawals.

## Hosted Oraclebot boundaries — reviewed 2026-11-12

| ID | Caller | Target and effect | Bounds, retries and proof |
| --- | --- | --- | --- |
| WEB1 | `website/src/worker.js` `stripe` | Stripe customer, subscription, Checkout and portal HTTPS API | 10s timeout and bounded response; server credentials only; no automatic write retry; customer/Checkout idempotency and ambiguous-create lock; `website/test/api.test.js` |
| WEB2 | `website/src/worker.js` `webhook` | Inbound Stripe subscription/Checkout events plus canonical subscription read through WEB1 | Raw-body HMAC and timestamp validation, durable processed-event identity and current-state reconciliation; no browser success entitlement |
| WEB3 | `website/src/worker.js` `engine` | Operator-configured HTTPS public-analysis adapter | Fixed allow-listed paths, server bearer, 20s timeout, redirect rejection and bounded JSON; no signing or order endpoint |
| WEB4 | `website/src/worker.js` `query`, account/bot routes | Cloudflare D1 account, challenge, session, billing and inactive configuration storage | Bound SQL, tenant predicates, atomic challenge consumption and conditional deletion; SQL behavior exercised through SQLite fixtures and deployed acceptance |
| WEB5 | `website/public/app.js` `api`, wallet sign-in | Same-origin account/analysis API and injected Solana wallet message signing | Abort deadline; account message only, no transaction signing; safe DOM rendering and explicit unavailable states |
| WEB6 | `website/engine/server.py` | Inbound bearer-authenticated public-analysis HTTP and dedicated local cache/archive reads | Bounded bodies/cache sizes, one calculation slot, symbolic errors; no browser Origin, feed acquisition, signing or order submission |

These rows describe actual boundaries; they do not establish universal five-standard
compliance or a provisioned analysis service. The website’s current package has
no common persistent request/outcome/remediation sink. Retry policy must preserve
the distinction between safe reads and an ambiguous side effect. Billing and
analysis calls remain unavailable when their required server configuration is absent.
