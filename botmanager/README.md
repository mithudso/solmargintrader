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
