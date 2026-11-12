# Bounded raw market-event capture

Version: 1.0.2
Delta: preserve malformed event type labels as raw payloads while keeping status counters serializable.

`scripts/capture_market.py` records each application message received from a
single Coinbase USD product. It does not sign, trade or alter the existing
one-second sampled price recorder. The initial owner-selected product is ZEC-USD.

Channels are `matches`, `level2_batch` and `heartbeat`. The public book feed is
provider-batched every50milliseconds; recording every received message does not
expose every internal exchange event. Trade IDs can jump or arrive late. The
recorder preserves them, heartbeats, connection segments and provisional
`trade_gap_candidate` records. It does not silently assert complete exchange
coverage or manufacture missing trades. Source:
https://docs.cdp.coinbase.com/exchange/websocket-feed/channels

## Durable capture and separate upload

The `prepare` command creates a new private run directory and persists a start
and deadline. It refuses an existing directory. Restarts never extend the
deadline. The collector holds a per-product singleton lock plus a run lock.
Each event receives a per-run sequence, local nanosecond receipt timestamp,
original exchange time/sequence/trade ID when present, connection ID, and exact
raw text. Each complete JSONL line is flushed and fsynced before proceeding.
Only an incomplete trailing line is removed during recovery. A non-string or empty
message type is counted as `unparsed`; its exact original message remains in the
raw field. Malformed public labels cannot terminate the collector or break status
serialization.

The collector and uploader run independently. Database outages leave the durable
raw stream recording. The uploader checkpoints acknowledged batches and reports
the backlog separately. `market_capture.events_<product>_<unique-run>` is a native
time-series collection with `received_at` timeField and stable venue/product/run
metadata. No expiry is configured. Original nanosecond and exchange timestamp
fields are retained; the BSON datetime alone has only millisecond precision.
MongoDB stores the parsed payload; the exact wire text remains in the raw spool.
This database is outside `mongo/load.py` ownership and is never dropped here.

Time-series collections cannot enforce a unique event key. Before an insert, the
uploader persists an in-flight marker. An ambiguous insert or crash leaves that
marker and stops automatic uploading with `needs_reconciliation`, while raw
capture continues. Never clear the marker without comparing its sequence range
against the actual collection. This design favors an explicit pending batch over
silent duplicate data. Connection failures before insertion retry every30seconds.

## Credentials and supervision

The uploader reads only the selected `MONGODB_URI2` value from the environment or
the explicit dotenv file. It uses the owner-supplied X509 certificate with
`MONGODB-X509` and `$external`. URI/certificate contents are never written to
logs, command arguments or Git. Driver failures expose class names only.
The URI's default database path is ignored: this writer explicitly selects
`market_capture`, and authentication explicitly selects `$external`. This also
prevents an unused placeholder database name from failing PyMongo URI validation.
An obsolete nonexistent `tlsCAFile` reference is omitted in memory, so the TLS
library uses its system trust store. An explicit valid CA path is preserved.
Hostname/certificate verification stays enabled; insecure TLS flags are refused.

Launchd jobs use a stable reviewed source copy and isolated requirements from
`scripts/requirements-market-capture.txt`. Separate collector/uploader jobs use
KeepAlive only after nonzero exits. The collector exits successfully at its
persisted deadline. The uploader can continue after that deadline to drain the
spool, then exits successfully. Completed collection does not prove database
upload completion. A `stop-requested` file ends collection early and records that
state; SIGTERM interruption can restart under supervision until the deadline.

## Commands and evidence

Run unit regressions without market/database access:

```sh
python3 -m unittest discover -s scripts -p test_capture_market.py -v
```

Each CLI action requires an explicit `--home`. `prepare` additionally requires
`--certificate`, with `--product ZEC-USD`, `--duration-seconds 86400` and
`--dotenv` selecting non-secret configuration. `capture` and `upload` are the
independent supervised roles. `status` reads configuration and role status files
without starting a service or connecting to MongoDB.

The initial deployment receipt is maintained outside Git at
`/Users/mitch/.local/state/solmargintrader/market-captures/zec-capture-delivery-20261112.json`.
It records the actual run directory, source revision, launchd labels, UTC deadline,
initial observations and MongoDB write/readback status. A running collector is
not a completed24hour dataset. A local spool is not a successful MongoDB upload.
