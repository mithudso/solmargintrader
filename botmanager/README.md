# Solbot manager 0.1.0

The standalone `solbot` CLI creates persistent named bot drafts and inspects their
pinned settings. It defaults to paper, disarmed, Solana spot, long-or-flat SOL/USDC.
There is no manager runtime in this release. Creating a draft cannot start a
process, fetch prices, initialize another component's database, load keys, or trade.
Arbitrage reports `Solana adapter unavailable`. Council is external-only.

## Install and use

Python 3.13 or newer is required. Runtime dependencies are entirely standard
library; building the package uses setuptools. Install in a dedicated environment:

```sh
python3 -m venv /tmp/solbot-venv
/tmp/solbot-venv/bin/python -m pip install /Users/mitch/dev/solmargintrader/botmanager
/tmp/solbot-venv/bin/solbot help
/tmp/solbot-venv/bin/solbot create grid --name sol-grid --set range_pct=10
/tmp/solbot-venv/bin/solbot create grid --name sol-grid-wide --set range_pct=25
/tmp/solbot-venv/bin/solbot list
/tmp/solbot-venv/bin/solbot config sol-grid --effective
/tmp/solbot-venv/bin/solbot status sol-grid
/tmp/solbot-venv/bin/solbot status sol-grid --why
```

The installed console script resolves the package from its environment; it does
not require a repository working directory or `PYTHONPATH`. Each invocation emits
a JSON envelope with `schema_version`, a new UUID `request_id`, `ok`, `data`, and
`error`. `--help` provides conventional parser help. Exit codes are 0 for success,
2 for invalid input or identity conflicts, 3 for an unavailable capability, and 4
for operational/store errors. Input errors never repeat submitted values.

Settings use `--set key=value`. JSON scalar types remain exact: `armed=false` is
a boolean; `deadband_bps=0` is zero. Enum strings may be unquoted, for example
`spacing=arith`. Integer fields reject strings, booleans, and fractional numbers.
Unknown keys, NaN/infinities, duplicate settings, invalid ranges, `armed=true`,
and non-paper modes refuse before a draft is saved. `start` and `stop` resolve
identity, then return `runtime_not_available` for manager drafts. Their presence
in parser help does not advertise runnable manager bots; draft status advertises
only `inspect`. A UUID always identifies one draft; display names are unique
case-insensitively, ASCII, and cannot look like UUIDs.

## Status and control contracts

Each draft status has its own `schema_version=1`, inside the unchanged five-key
command envelope. `status --why` includes a JSON explanation; the option is
declared in the shared command registry. Existing status keys remain available,
including `owner` (the saved specification's owner), `observed_state=not_running`,
`capabilities=["inspect"]`, and `reason=runtime_not_available`.

`spec_owner`, the stable `bot_id`, and `config_revision`/`config_hash` describe the
saved configuration. `runtime_id`, `runtime_owner_id`, and `owner_generation`
describe an actual runtime and remain null for drafts, with `runtime_reason`.
Mode/arming, lifecycle, desired/observed state, input quality, owner reachability,
submission certainty, heartbeat/data age, evaluation/decision, blockers and next
trigger are separate dimensions. Unknown observations use `{value: null, reason:
"..."}`; missing heartbeats and results never become fresh data or successful work.
The snapshot mapper performs no I/O and does not query an owner or a clock.

`financials` keeps exposure, allocated capital, realized/unrealized net P&L and
costs null with explicit reasons. `configured_virtual_capital` is the saved
virtual-account setting and is never reserved allocation or measured P&L.
`evidence_identity` pins strategy/version, config revision/hash, venue/mints,
bar duration and execution model. Backtest, paper and live evidence have separate
records; absent dataset/proof hashes, dates, engine/cost identities and result
references remain null. No evidence certifies a proxy venue or execution model.

`action_capabilities` explains inspect, start, pause entries, stop, cancel orders,
close position and emergency stop separately. Only inspect is available for
drafts. Stopping a worker retains orders, positions, arming and journals;
cancellation, closing and engine kill/disarm require their own supported actions.
`manual_pins` preserves exact override values and provenance at the config
revision/hash. Tuning proposals are unavailable and read-only; versioned adoption
and automatic runtime edits are unavailable. Status never adopts new settings.

`botmanager.receipts.CommandReceipt` defines the version-1 per-bot control
contract for later owner adapters. No draft command emits a pretend owner
receipt. It carries distinct bot/request UUIDs, operation, runtime/owner identity,
nullable nonnegative owner generation, config revision, a symbolic
reason and one of `acknowledged`, `pending`, `skipped`, `failed` or `unknown`.
Pinned manager configurations require a positive integer revision. An external
owner without numeric revisions uses `config_revision=null` with the required
`config_revision_unavailable_reason=owner_does_not_version_configurations`.
The reason must be null when the revision is known; never invent revision 1.
Acknowledgment alone proves neither stopped execution nor cleared exposure.
All receipts serialize `safe_to_retry=false`; `unknown` additionally requires
reconciliation and never means zero exposure. Deserialization rejects forged
retry/reconciliation flags, unsupported versions/operations/outcomes and invalid
types. Metadata is immutable and restricted to token-like `detail_ref`,
`reconciliation_ref`, `owner_revision`, finite nonnegative `elapsed_seconds`, and
optional `config_hash` (exactly 64 lowercase hexadecimal characters) for an
available legacy configuration snapshot.
Arbitrary owner response bodies and credential fields are refused. Callers must
keep secrets out of every identity, reason and reference.

## Configuration contract

The resolver accepts `(strategy_id, context, overrides, shared_snapshot)`. Packaged
defaults precede exactly compatible shared settings, then explicit overrides.
Every effective field carries its source, source revision, and compatibility or
manual-pin reason. Original user overrides remain separate from effective values.
Mappings are recursively immutable. Specs pin strategy/version, venue/mints,
closed-bar duration, execution model, config revision, SHA-256 config hash and
provenance. Reads reconstruct that snapshot without resolving new defaults.
Changing settings or adopting new defaults is intentionally unavailable until an
explicit versioned update/adoption command exists.

A shared snapshot has this shape (all context fields are mandatory):

```json
{
  "schema_version": 1,
  "revision": "learned-7",
  "strategy_id": "grid",
  "strategy_version": "grid-ladder-v1",
  "context": {
    "venue": "jupiter",
    "base_mint": "So11111111111111111111111111111111111111112",
    "quote_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "bar_seconds": 60,
    "execution_model": "trigger_ladder"
  },
  "values": {"range_pct": 20.0}
}
```

Coinbase venue, different bars, missing mints, unknown schema or different strategy
version reject shared adoption and record the incompatibility. An otherwise
compatible snapshot with invalid settings refuses. Shared defaults may change
strategy parameters only; capital, order sizes, stop loss, venue minimum, mode,
arming and operating settings cannot be learned. This slice accepts snapshots
through its Python registry context only;
it does not read or overwrite existing optimizers, named profiles or owner stores.

## Default sources and semantics

The constructor snapshot is pinned to repository revision
`78468489cc968e25b87786246a5aa3edf43d2277`. Source-parity tests inspect syntax trees
without importing NumPy or starting existing applications.

| Family/version | Constructor defaults | Source |
| --- | --- | --- |
| grid / `grid-ladder-v1` | `range_pct=15.0`, `rungs=7`, `spacing=geom`, `deadband_bps=25.0`, `capital_usd=1000.0` | `/Users/mitch/dev/solmargintrader/soltui/bots.py`, `GRID_DEFAULTS` |
| dca / `safety-order-v1` | `base_order_usd=100.0`, `safety_order_usd=100.0`, `max_safety_orders=5`, `price_deviation_pct=2.0`, `step_scale=1.0`, `volume_scale=1.0`, `take_profit_pct=2.0`, `stop_loss_pct=0.0`, `cooldown_bars=0`, `min_order_usd=10.0` | `/Users/mitch/dev/solmargintrader/backtester/core/dcasim.py`, `DcaConfig` |
| trend / `sma-crossover-v1` | `fast_period=10`, `slow_period=30`, `entry_buffer_bps=10.0`, `capital_usd=1000.0` | `/Users/mitch/dev/solmargintrader/soltui/trend.py`, `TrendConfig` |
| momentum / `ts-momentum-v1` | `window=60`, `threshold=0.0` | `/Users/mitch/dev/solmargintrader/backtester/core/strategies/signals.py`, `TsMomentum` |

Application defaults (`manager-defaults-v1`) are `mode=paper`, `armed=false`,
`venue=jupiter`, wrapped SOL and mainnet USDC mints shown above, `bar_seconds=60`,
`capital_usd=1000.0` for each independent virtual account, `timezone=UTC`, and
`lot_method=FIFO`. Capital is virtual and does not change live limits. The only
accepted mint pair is SOL/USDC; bar duration is a positive integer and remains
part of the exact compatibility key. No prices, fees, credentials, balances or
decimals are fabricated as defaults.

Execution models retain their reference semantics: grid `trigger_ladder`, DCA
`safety_order_ladder`, trend/momentum `next_open`. A Jupiter venue label on a draft
does not certify a fill model, costs, market data, Trigger signing or swaps.
DCA's `$10` minimum is the retained constructor assumption, **not a verified
Jupiter venue minimum**. Future adapters must validate real observations and
venue constraints. Periods count bars; the manager does not convert hourly
research periods into equivalent minute periods or relabel Coinbase evidence.

## Storage and read behavior

The home defaults to the actual user's home plus `.config/solbot` (on this
machine, `/Users/mitch/.config/solbot`). `SOLBOT_HOME` selects an isolated home.
Construction, `list`, `status`, `config` and `help` do not create a home or database.
Existing reads open SQLite with `mode=ro` and `query_only`. Writes create the home
with mode 0700 and `/Users/mitch/.config/solbot/manager.sqlite3` with mode 0600.
No credentials belong in a spec, event or installation descriptor.

Store schema 1 uses SQLite `user_version=1`; migration 1 initializes the schema
under a write transaction. Unknown schemas fail closed. One transaction inserts
the immutable spec and its `spec.created` event. Database constraints enforce UUID,
name and source-identity uniqueness. Events have a fixed reference-only schema
and unique event IDs; arbitrary owner response bodies are refused. Config hashes
detect accidentally altered snapshots; they are not signatures.

Backup descriptor schema 1 reports the store schema, format, path, included
tables, and `sqlite_connection_backup` method. A consistent copy must use SQLite's
backup API; copying a database during writes is not the supported backup method.
This release exposes the descriptor but has no backup/restore CLI.

## Verify

```sh
PYTHONPATH=/Users/mitch/dev/solmargintrader/botmanager/src python3 -m unittest discover -s /Users/mitch/dev/solmargintrader/botmanager/tests -t /Users/mitch/dev/solmargintrader/botmanager
```

Tests use temporary homes and fresh CLI processes. They cover strict typed
defaults, source parity, compatible/incompatible learning, manual pins, immutable
reloads, transactional rollback, unique identities, corrupt/future schemas,
credential canaries and read-only filesystem behavior. Existing strategy engines
remain offline and untouched. Multi-instance runtime, actual owner discovery,
live execution, data certification and browser integration are separate work.
