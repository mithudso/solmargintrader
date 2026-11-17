# Logging

What each component records, where it goes, and — the part worth reading — which paths
currently record nothing.

## The surfaces

| Component | Surface | Persistent? |
| --- | --- | --- |
| `extension/` | IndexedDB: the `events` store, the intent journal, the fill log (`src/storage/store.js`) | Yes |
| `extension/` | `console.error` in the service worker | No — lost when the worker is evicted |
| Jupiter transport | Structured attempt/outcome metadata on Node stderr or browser debug console | No shared persistent sink |
| Local HTTP API | Structured, secret-free security/error events on stderr | Only when the operator captures stderr |
| `backtester/` | The run manifest and report (`core/report.py`), written per run | Yes, as output files |
| `research/` | stdout, plus written result files | Output files only |
| `soltui/` | App stdout/stderr, detached sweep/fetch logs and safe `soltui.market` read events | Captured app/worker streams; no common persistent request sink |
| `mongo/` | Loader counts, subprocess output and provenance stored in derived documents | Console/output records; no common JSONL error sink |
| `liquidity/` | `Daemon.log` writes SQLite ledger events and stdout; stage results retain transaction hashes | Ledger, state files and service `daemon.log` |
| `botmanager/` | Owner journals, `health.sqlite3`, and the suite's private `.suite/alerts.json` plus stdout/stderr | Yes; bounded derived alerts are distinct from financial/evidence journals |
| `ecosystem/` | Pipeline `supervisor.log`, control-room `control-room.log`, `control.sqlite3` action receipts and sanitized `telemetry.sqlite3` mirror | Yes; original manager evidence remains with its owner |
| `website/` | Worker fixed request-failure events; Python engine fixed HTTP/analysis events | Cloudflare runtime logs or captured engine stderr; no common persistent sink |
| `oracle/` | Selected archive events/forecasts; separate webhook SQLite signals, per-leg intents, sanitized results and public fill evidence | Durable journals; fixed CLI/MCP/HTTP failures are not a universal transport-attempt log |
| `executor/` | Append-only submission journal and registry `calls.jsonl` under its selected private log root | Journal persists intent/send/outcome; call metadata records parameter keys, not values; no shared per-HTTP-attempt sink |
| `website/` | D1 account/session/subscription/webhook receipts and fixed public API errors | Durable application state; not a shared JSONL error or transport-attempt log |
| Raw-event capture | Durable event spool, capture/upload status and upload-progress records in the explicit run home | Independent producer/uploader evidence; an acknowledged upload offset is distinct from a separate database read-back |

The extension's real log is **not the console**. `src/storage/store.js` defines four
object stores — `intents`, `fills`, `carry`, `events` — and the intent journal is what
makes the bot restart-safe: an intent is written before it is submitted, so a crash
between the two is recoverable rather than invisible. Any logging work should extend that
store, not add console noise.

```js
await store.logEvent({ type: 'tick', summary: summarise(result) });   // engine.js
const recent = await store.recentEvents(100);                          // for the dashboard
```

`logEvent` stamps `tsMs` itself, so a call site supplies only the event body.

Every engine tick outcome now reaches that sink, including early accounting holds and venue/limit
preparation failures. Summaries retain bounded hold codes, unresolved intent identities and failure
stage/class/HTTP status. Upstream exception messages and response bodies are excluded. An early
failure still throws to its caller after recording the diagnostic; the event does not authorize a retry.
The production HTTP API emits authentication, browser-origin and request-failure events to stderr.
Its logger excludes tokens, request URLs/bodies, headers and arbitrary upstream error text.

## Levels

Engine and transport callbacks carry `level` for diagnostics. The durable events store
is queried by `type`; keep that type (`tick`, `blocked`, `submitted`, `orphaned`) when
adding an event. Transport logs contain method, safe path, attempt and outcome only.

## Sensitive data — the hard rule

Never log secret material. Concretely, none of these may appear in an event body, a
console call, the DOM, or an HTTP response body:

- the Jupiter API key,
- the session-key vault contents or the passphrase that unseals it,
- a private key or seed in any encoding.

Hosted integration credentials (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` and
`ENGINE_TOKEN`), wallet challenge signatures, session tokens, MongoDB connection
strings and X509 private material follow the same rule. Log symbolic failure codes
and bounded nonsensitive metadata. Never copy raw provider/driver errors into a public
response or persist request bodies to obtain transport observability.

`commands.js` already models the rule: `setApiKey` deliberately returns only a length,
with the comment that echoing a secret puts it in shell history. Follow that. If a value
must be referenced in a log, log its length, a hash prefix, or the fact of its presence.

Prices, quantities, order ids and rejection reasons are **not** sensitive and should be
logged — they are what makes a wrong order diagnosable after the fact.

## Coverage gaps

The code-optimizer report records changes to engine state-transition logging. The
following distinctions remain load-bearing after any such fix:

- A persistent **tick summary** is not a complete transport attempt log. Jupiter price
  and Trigger calls share `extension/src/jupiter/http.js`; it emits safe structured
  request/outcome metadata, but has no common persistent error sink.
- Risk diagnostics must name the refusing rail and preserve safe input metadata. Pure
  `risk.js` stays free of I/O; the owning engine/surface records outcomes.
- An **unknown** intent means submission may have succeeded. Its journal state is the
  durable authority for withholding another order; a human-visible event helps diagnosis
  but does not itself resolve the ambiguity.
- `console.error` in an evicted MV3 worker is not persistent history. A thrown tick needs
  a persistent failure record if it is to remain visible after restart.
- Liquidity's **ledger event** is an operation-level outcome, not per-RPC logging.
  `MarketData._get`, `LlamaPrices` and Web3 provider retries do not all write attempts to
  a shared sink. A simulated result, a broadcast hash and a mined receipt are different
  states; their labels must survive into any displayed action.
- Offline data fetchers print progress/outcomes, but do not share a central JSONL error
  schema. Some subprocesses also lack an overall timeout. See `docs/external-calls.md`.

These are remaining coverage/contract limits, not a claim that every listed path is
silent. Log changes need behavior assertions on the emitted event and redaction. The
full five-standard contract is not implemented; see `docs/repo-bootstrap-audit-2026-11-06.md`.

## Managed-suite and local-control diagnostics

`botmanager/src/botmanager/suite.py` records component failure/recovery events in
`.suite/alerts.json` under the selected manager home and emits sanitized JSON to
stderr. The journal retains at most 256 events, monotonic cursors and explicit
history truncation. Repeated failures have a five-minute reminder cooldown.
Fast UI transitions pass through a bounded queue and a single journal writer;
a quick repair must not erase the incident. The manager shares the suite process,
so an unclean suite incident covers their shared owner loss. See
[managed-suite operation](bot-manager-managed-suite.md).

The suite's stdout/stderr files rotate at the implemented size bound. These are
availability diagnostics, not immutable financial evidence. `health-check` and
`metrics` report compact measurements; `component-alerts` reads the durable event
cursor. An unavailable alert journal makes suite monitoring readiness false.
Tests in `botmanager/tests/test_suite.py` and
`botmanager/tests/test_machine_health.py` exercise transition persistence,
cooldowns, read-only measurements and journal failures.

`ecosystem/telemetry.py` mirrors bounded, sanitized manager events. It does not
copy free-form logs or take ownership of the original journals. Control actions
have durable receipts in `ecosystem/control.py`; public HTTP failures in
`ecosystem/web.py` return fixed codes rather than raw exceptions. See
`ecosystem/tests/test_telemetry.py`, `ecosystem/tests/test_control_http.py` and
`ecosystem/tests/test_machine_health_http.py` for failure/redaction assertions.

`oracle/store.py` persists source observations and forecast/outcome events. An
archive write failure must not become an unlogged forecast (`oracle/cli.py`).
The public boundaries in `oracle/feeds.py` and `oracle/server.py` sanitize provider
and dependency errors. Protocol stdout belongs to JSON/MCP frames. These existing
records do not provide the common per-request JSONL error sink, remediation maps
or generated call cards required by the complete five-standard contract.

## Read-only market diagnostics

`soltui/market_diagnostics.py` emits `market.operation` through the
`soltui.market` logger. Wrapped operations in `live_price.py`, `spot_prices.py`
and `current_signal.py` record a fixed operation name and started/completed,
unavailable or failed outcome. Failures include the exception class, never its
message, raw URL, token, symbol or provider body. An expected HTTP 404 uses info
level; other failures use warning and still propagate to the caller.

The installed application's logging handlers own collection. These tested read
boundaries do not supply a persistent event sink for every market or transport
call in the repository.

## Testing a log

Assert on the event, not on the fact that a line ran. `src/storage/memoryStore.js`
implements the same `logEvent` interface, so a test can drive a tick against the memory
store and assert the recorded event body. That is the pattern to follow for anything added
from the gap list above.

## TradingView execution journal

The webhook inbox retains event identity, execution mode, venue/account binding,
planned legs and sanitized results. GUM reconciliation records actual fill
quantity, fee and public transaction signatures. An acknowledgment is labelled
accepted; it is not promoted to filled without matching venue evidence. Unknown
submission remains a durable hold rather than a retry instruction.

HTTP access logging is deliberately disabled because alerts contain a secret.
Failures return fixed symbolic errors; upstream exception bodies and signed
requests are excluded. The worker failure boundary stops the receiver and exposes
`venue_worker_failed`. The journal provides operation-level state and evidence,
not a complete shared per-request error sink. Tests are in
`oracle/tests/test_webhook.py`, `test_webhook_orders.py`, `test_gum_orders.py` and
`test_gum_webhook_orders.py` under `oracle/tests/`.

## Hosted website diagnostic boundary

The website’s account/session/subscription tables and processed Stripe-event
identities are operational state, not a complete per-request audit log.
`website/src/worker.js` emits `oraclebot.request_failed` with a fixed operation,
code and HTTP status. Server failures use error level; refused requests use warn.
It excludes raw URLs, query strings, request bodies, wallet signatures, cookies,
Stripe headers and provider response text. Regression tests assert the fields,
levels and redaction.

`website/engine/server.py` suppresses HTTP access logs. Its structured response
and failure events use fixed operation/status metadata and exception class names.
They exclude arbitrary request targets, credentials, bodies and exception text.
The CLI configures these JSON events on stderr. Cloudflare observability captures
Worker events when enabled in `website/wrangler.jsonc`; engine stderr still needs
an operator-owned collector. These tested boundaries do not establish a common
persistent request/outcome sink across the repository.

A universal safe transport/security event sink remains an implementation gap
unless the code-optimizer report records a tested repair. Adding one must retain
redaction and tenant boundaries. Never treat the presence of a subscription row,
a successful HTTP response or platform request log as proof of an executed order.
