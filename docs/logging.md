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
| `soltui/` | App stdout/stderr plus detached sweep/fetch logs | Yes, via launchd or worker files |
| `mongo/` | Loader counts, subprocess output and provenance stored in derived documents | Console/output records; no common JSONL error sink |
| `liquidity/` | `Daemon.log` writes SQLite ledger events and stdout; stage results retain transaction hashes | Ledger, state files and service `daemon.log` |

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

## Testing a log

Assert on the event, not on the fact that a line ran. `src/storage/memoryStore.js`
implements the same `logEvent` interface, so a test can drive a tick against the memory
store and assert the recorded event body. That is the pattern to follow for anything added
from the gap list above.
