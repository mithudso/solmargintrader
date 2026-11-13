# Hosted analysis owner

The authenticated `POST /v1/signals` route supplies the managed trading driver
with canonical default spot targets from closed public candles. Its exact body
is `{ "coin":"SOL", "strategy":"rsi", "interval":"1h" }`. It publishes a
stable closed-bar signal ID, full selected-input hash, loaded source identity,
strategy revision and short expiry only with a genuine current venue event.
`desiredExposure` is exactly `0` or `1`; fractional/unusable targets are
unavailable. `GET /v1/strategies` exposes that same strategy revision before a
customer signs preauthorization. The signal is not an execution quote or order
permission. The driver obtains its own fresh quote and checks the signed
customer policy. See `website/engine/README.md` for the complete signal contract.

This separate Worker owns one named native Durable Object and one Python
Container. The public website binds it as `ENGINE_SERVICE`; it does not expose
the operator control room or reuse an operator archive. `ENGINE_TOKEN` remains
server-side. Analysis never receives wallet or venue credentials.

The production configuration uses the documented native Container API and
`durable_object` scheduling policy, with SQLite DO storage and R2 persistence.
No runtime npm SDK is required. Fixed `idFromName('public-analysis-v1')` routing
prevents callers from selecting or spawning additional container instances.

## Provisioning

Use the project's pinned Wrangler. Create the dedicated
`oraclebot-analysis-state` R2 bucket, configure `ENGINE_TOKEN` and the distinct
`RUNTIME_STATE_TOKEN` as secrets, and set `RUNTIME_PUBLIC_ORIGIN` to the exact
HTTPS origin of this runtime Worker. That origin has no path or query. It is
used only by the container's authenticated checkpoint client; it is never
selected by a user. Enable the required Workers Paid/Containers entitlement.

Build with the repository root as Docker context. Dockerfile installs the
canonical packages and `oraclebot-analysis-runtime`, pins its numeric/runtime
dependencies and starts Python in isolated import mode as an unprivileged user.
If the local Docker daemon is intentionally stopped, use a separately authorized
remote build or a digest-pinned prebuilt image. A dry-run that stops at Docker
is a failed image gate, not successful deployment.

Container rollout is separate from public-site rollout. Deploy and verify this
runtime first. Verify its actual image reference and Python `sourceIdentity`
through authenticated `/health`, the durable checkpoint sequence, live public
observations, native ZEC forecasts and a real backtest/restart round trip.
Then bind the public Worker. Source tests and a bundle-only dry-run do not
establish those hosted results.

## Durability and ownership

The Durable Object increments an owner epoch before each new container start.
Old epochs cannot upload or publish state. On an image change, the old epoch is
fenced before its owned container is replaced. Alarms maintain the service;
`running` is never treated as application readiness.

The container restores and validates the previous checkpoint before constructing
writers or accepting jobs. SQLite files use the backup API. Files are split into
content-addressed512KiB R2 chunks; unchanged chunks are reused. A manifest binds
every filename, size, full-file SHA256 and ordered chunk hashes. The DO checks
uploaded chunk receipts and lengths, then atomically publishes only the next
manifest sequence under the current epoch. Publication of that head is the
commit point. Individual orphan chunks are harmless after a failed CAS.

Checkpoint callbacks have a distinct bearer secret and may use only:

- `GET/PUT /internal/state/manifest`
- `GET/PUT /internal/state/chunks/{sha256}`

Browsers are refused. Filenames are allowlisted; no key, environment file, WAL,
operator directory or executable is persisted. Corrupt, incomplete or
incompatible restores withhold readiness and never create replacement history.
Cold restore validates every chunk, file and SQLite database before replacing
live paths, and removes only allowlisted unpublished files and obsolete WAL
sidecars. Bounded parallel reads cap restore buffering.

The app caps one active calculation,512pending jobs,32MB per input,6000bars,
2MB results,8GiB checkpoint state and a4MB manifest. Native history and completed
job results are retained until those explicit physical bounds; capacity must be
expanded or an audited archival lifecycle introduced before exhaustion. R2
objects have no automatic deletion policy in this configuration. Do not add one
that can delete chunks referenced by a checkpoint or retained history.

## Contracts and verification

The existing three synchronous analysis routes remain. `/health` reports
infrastructure readiness separately from per-coin data/Oracle warmup and source
freshness. It includes actual Python code identity and the gateway's image
reference. Jobs use:

```json
POST /v1/jobs
{"id":"<edge-generated UUID>","request":{"coin":"SOL","strategy":"buy_and_hold","interval":"1h","capital":10000,"leverage":1}}
```

Response fields are `id`, `status`, `requestHash`, `inputHash`, `createdAt` and
`updatedAt`. Complete results add `result`; terminal failures add a symbolic
`error`. Status is `queued`, `running`, `complete` or `failed`.
`GET /v1/jobs/{id}` returns the same shape. Duplicate ID and canonical request
return the existing job; a different request under that ID returns409.
`requestHash` is SHA256 over sorted, compact, ASCII JSON without numeric coercion.
Input CSV and its provider acquisition metadata are pinned before durable
enqueue. Pure calculations may retry after a crash with that same snapshot;
financial retry semantics do not belong to this service. Complete is exposed
only after its result and status have a durable checkpoint.

Admission refusals for a valid UUID and structurally valid canonical request are
also persisted: semantic validation, capacity or input/history refusal creates
a terminal `failed` receipt with its exact ID/request hash and symbolic error.
It has `inputHash: null` if no input snapshot was admitted. The gateway returns
HTTP200 only after checkpoint acknowledgement. Duplicate requests return that
same terminal failure, including after cache/registry changes or restart.
The authenticated edge can then release the matching reserved credit safely.
Malformed envelopes/IDs remain HTTP400 with no accepted receipt; an ID/hash
conflict remains HTTP409. Storage/transport uncertainty never proves failure
and cannot authorize quota release.

Run source gates from the repository root with the declared dependencies:

```sh
INDEX_NO_AUTO=1 python -m unittest website.engine.test_server website.engine.test_research website.engine.test_state website.engine.test_jobs website.engine.test_runtime -v
node --test website/runtime/worker.test.js
ruff check website/engine
```

Tests exercise actual HTTP/TLS serialization against controlled stand-ins,
WAL snapshot integrity, corruption/epoch/CAS failures, pinned-input recovery,
real canonical calculation, process timeout cleanup and zero historical
forecast/outcome creation. These fixtures are not Coinbase or Cloudflare
production acceptance.
