# Logging

What each component records, where it goes, and — the part worth reading — which paths
currently record nothing.

## The surfaces

| Component | Surface | Persistent? |
| --- | --- | --- |
| `extension/` | IndexedDB: the `events` store, the intent journal, the fill log (`src/storage/store.js`) | Yes |
| `extension/` | `console.error` in the service worker | No — lost when the worker is evicted |
| `backtester/` | The run manifest and report (`core/report.py`), written per run | Yes, as output files |
| `research/` | stdout, plus written result files | Output files only |
| `soltui/` | `print` to stdout/stderr, captured by the launchd agent's log | Yes, via launchd |

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

## Levels

There is no level system, and adding one would be premature: the events store is queried
by `type`, not filtered by severity. Use a specific `type` (`tick`, `blocked`,
`submitted`, `orphaned`) rather than a level string.

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

Audited against the code, not assumed. There are exactly two `logEvent` call sites in the
whole extension:

| Call site | Event |
| --- | --- |
| `extension/src/core/engine.js:402` | `{ type: 'tick', summary }` — one per tick |
| `extension/src/bg/service-worker.js:73` | `{ type: 'blocked', reason }` — feasibility refusal |

So the following paths are silent, and each one is a gap rather than a design choice:

1. **Every Jupiter call.** `src/jupiter/http.js` is the single HTTP layer for price and
   Trigger requests and it records neither request nor outcome. A venue that returns an
   unexpected envelope — and the Trigger order-list envelope is *guessed*, see
   `docs/known-issues.md` — leaves no trace to diagnose from.
2. **Per-rail risk rejections.** The `blocked` event carries one aggregate reason from the
   service worker. Which rail in `src/core/risk.js` fired is not recorded.
3. **The `unknown` intent transition.** An intent submitted but not found live becomes
   `unknown` and is never auto-retried — that rule exists because it is how a rung
   double-fires after a crash. It is the single most important state change in the system
   and it emits no event.
4. **A thrown tick.** `service-worker.js:129` sends it to `console.error`, which does not
   survive worker eviction, so a repeated failure is invisible after the fact.

Writing these logs is a code change, not a docs change: it belongs in `code-deep-optimizer`
pass **S5**, with tests that assert on the emitted event (pass **T1**) — an added log with
no test is not covered.

## Testing a log

Assert on the event, not on the fact that a line ran. `src/storage/memoryStore.js`
implements the same `logEvent` interface, so a test can drive a tick against the memory
store and assert the recorded event body. That is the pattern to follow for anything added
from the gap list above.
