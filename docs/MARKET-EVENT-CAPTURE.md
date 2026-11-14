# Bounded raw market-event capture

Version: 1.0.3
Delta: record the completed 24 hour ZEC window and full MongoDB readback.
Previous delta: preserve malformed event type labels as raw payloads while keeping status counters serializable.

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
not a completed 24 hour dataset. A local spool is not a successful MongoDB upload.


## Completed ZEC-USD capture, November 12–13, 2026 UTC

The fixed 24 hour capture and MongoDB persistence are complete. The collector and
uploader both exited successfully after the original deadline. No records were
changed or inserted during the final read-only audit.

| Measurement | Verified result |
| --- | --- |
| Scheduled start | 2026-11-12T04:56:27.224912Z |
| Fixed deadline | 2026-11-13T04:56:27.224912Z |
| Stored records | 1,459,542, with sequence 1–1,459,542 present exactly once |
| Raw JSONL archive | 1,561,825,045 bytes; complete trailing newline |
| Level2 updates | 1,238,392 |
| Trade matches | 134,746 |
| Heartbeats | 86,370 |
| Other records | 7 snapshots, 7 last-match messages, 7 subscription messages, 7 connection-open markers, 6 connection-gap markers |
| Connection segments | 7, with 6 recorded reconnect gaps |
| Observed public-message receipt gaps over 2 seconds | 8; longest 17.307175 seconds |
| Unobserved trade-ID candidates within the observed match-ID range | 54 |

The observed local receipt span was 86,399.736219 seconds. The first record arrived
0.263455seconds after the scheduled start; the final record arrived about
0.000326seconds before the deadline. The average was 16.89 records per second;
individual records preserve their original nanosecond receipt times.

The final audit streamed every raw record and every MongoDB document. It
verified all sequence numbers, rejected duplicates or extra records, and
compared a SHA256 digest of every complete uploader projection against its
corresponding raw record. Only MongoDB's generated `_id` was excluded. Parsed
payload, exchange metadata, original nanosecond receipt, run metadata and the
BSON millisecond datetime all matched. The upload checkpoint covered the full
raw file, with no pending in-flight batch. The native time-series collection
has `received_at` as its time field, `meta` as its metadata field, seconds
granularity and no expiry.

An independent verifier confirmed the native count and collection layout,
compared nine independently selected complete records, reviewed the all-record
audit algorithm, and verified both supervised jobs were idle after successful
exit 0. Its 16 checks passed.

These results establish persistence of the received stream. They do not
establish uninterrupted or exchange-wide coverage: the six reconnects, eight
receipt gaps and 54 unobserved-ID candidates remain explicit. The public order
book is provider-batched at 50 ms. No missing events were invented or silently
backfilled. This collection alone does not establish forecast accuracy or
profitability.

The destination is
`market_capture.events_zec_usd_857db4e0787d4d17bc41e5a3e34ecbec`, run
`50dbd4f31de24c36a30d8c3786495ad5`. The exact wire text remains in
`/Users/mitch/.local/state/solmargintrader/market-captures/zec-usd-20261112T045627Z/events.jsonl`.
Its SHA256 is
`eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31`.

Complete audit evidence and coverage intervals are under
`/Users/mitch/.local/state/solmargintrader/market-captures/zec-final-audit-20261113/`.
`final-audit.json` has SHA256
`8d8808e35fec78a633037b426d114e58d57dd20c79538590a66576d0b7d7a26d`;
`acceptance.json` has SHA256
`549d4aab72394b36800c7ff9b5e0e11315ea9d9a5c57135b3571d1658c4ed9ed`.
The final `delivery.json` and `file-manifest.json` retain the release and complete
private artifact inventory. Credentials and raw market data are not published
in Git.
