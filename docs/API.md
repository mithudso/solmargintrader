# API and CLI reference

Every action lives in one registry: `extension/src/core/commands.js`. Three surfaces adapt it.

| Surface | How you call it |
| --- | --- |
| Chrome extension | `chrome.runtime.sendMessage({ type: '<command>', ...args })` |
| CLI | `node tools/cli.js <command> [--arg value]` |
| HTTP API | `POST /v1/<command>` with a JSON body, or `GET /v1/<command>?arg=value` for read-only commands |

`test/surfaces.test.js` fails the build if any surface is missing a command, so the three cannot
drift apart.

**The canonical, always-current listing is generated, not this file:**

```bash
cd extension
node tools/cli.js                  # all commands
node tools/cli.js <command> --help # arguments and types for one command
curl -H "Authorization: Bearer $SMT_API_TOKEN" http://127.0.0.1:8787/v1/commands
```

## Commands

`*` marks a required argument. 22 commands as of this writing.

### Inspection — read-only, safe to poll

| Command | Arguments | What it does |
| --- | --- | --- |
| `status` | — | Mode, arm state, limits, last tick, venue capabilities, leverage feasibility |
| `getConfig` | — | Effective grid configuration |
| `getLimits` | — | Effective risk rails |
| `price` | — | Live mark price for the configured base mint |
| `levels` | — | Rung ladder, rung width in bps, and the gross spread each round trip captures |
| `capital` | `price`:number | Capital the grid needs (bids only — exits are self-funding) |
| `plan` | `price`:number | Orders the grid **would** place right now. Computes only; places nothing |
| `pnl` | `price`:number | Realized, unrealized, fees, carry, equity curve, max drawdown, win rate |
| `data` | `limit`:number | Raw journal: intents, fills, carry entries, recent events |
| `exportCsv` | — | Fill log as CSV — the same export the dashboard button produces |
| `venueInfo` | — | Venue id, kind, capabilities, and why a venue is read-only |

### Configuration — writes settings, never orders

| Command | Arguments | Notes |
| --- | --- | --- |
| `setConfig` | `patch`:json, plus flat fields (`mode`, `lower`, `upper`, `rungs`, `spacing`, `notionalPerRungUsd`, `direction`, `slippageBps`, `leverage`, `marginSource`, `tickSeconds`, `userPubkey`, `baseMint`, `quoteMint`) | A blank numeric field is omitted, never coerced to 0 |
| `setLimits` | `patch`:json, plus each rail as a flat number | See [risk rails](#risk-rails) |
| `setApiKey` | `apiKey`:string\* | Returns a length only. The key is never echoed back |
| `createSessionKey` | `passphrase`:string\* | Generates a dedicated full-auto signing key, encrypted at rest. Minimum 12 characters |

### Lifecycle

| Command | Arguments | Notes |
| --- | --- | --- |
| `arm` | `confirmLive`:bool | Any non-dry-run mode **requires** `confirmLive` (412 without it). Refused while the kill switch is latched (409) |
| `disarm` | — | Stops placing new orders. Resting orders are left alone |
| `kill` | — | Latching hard stop: disarms and blocks every rail until cleared |
| `clearKill` | — | Releases the kill switch. Does **not** re-arm |

### Execution

| Command | Arguments | Notes |
| --- | --- | --- |
| `tick` | `count`:number | One full tick: reconcile → ingest fills → plan → admit → place. `count` is capped at 50 |
| `cancelOrder` | `venueOrderId`:string\* | Cancels one resting order and marks its intent cancelled |

### Destructive

| Command | Arguments | Notes |
| --- | --- | --- |
| `reset` | `confirm`:bool\* | Erases the local journal, fills, carry and events. **Does not cancel venue-side orders** |

## CLI

```bash
cd extension

node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
node tools/cli.js levels
node tools/cli.js plan --price 75
node tools/cli.js arm
node tools/cli.js tick --count 3
node tools/cli.js pnl --json
node tools/cli.js exportCsv > fills.csv
node tools/cli.js reset --confirm
```

Global flags:

| Flag | Effect |
| --- | --- |
| `--json` | Machine-readable output |
| `--ephemeral` | In-memory state; nothing is persisted |
| `--quiet` | Suppress engine log lines |
| `--store-path P` | Journal file (default `~/.solmargintrader/journal.json`) |
| `--config-path P` | Config file (default `~/.solmargintrader/config.json`) |
| `--passphrase P` | Unlock a full-auto session key |
| `--help` | Global help, or per-command help after a command name |

Exit codes: `0` success, `1` command error (e.g. a missing required argument), `2` usage error
(unknown command or unknown flag). An unknown flag is **rejected**, never ignored — a silently
dropped `--notionalPerRungUsd` would be a money bug.

## HTTP API

```bash
cd extension
node tools/api-server.js --port 8787          # prints a generated bearer token
SMT_API_TOKEN=your-secret node tools/api-server.js   # or pin one
```

| Route | Auth | Notes |
| --- | --- | --- |
| `GET /v1/health` | none | Liveness and command count |
| `GET /v1/commands` | bearer | Discovery: every command, argument and type |
| `GET /v1/<command>` | bearer | Read-only commands only; args from the query string |
| `POST /v1/<command>` | bearer | Any command; args from a JSON body (max 256 KB) |

Status codes: `400` invalid or unknown argument · `401` bad token · `403` browser-originated ·
`404` unknown command or route · `405` wrong method (including `GET` on a state-changing command) ·
`409` kill switch latched · `412` live arm without confirmation · `413` body too large ·
`500` unexpected error (message only, never a stack).

Security posture is documented in [SECURITY.md](SECURITY.md). In short: loopback-bound by default,
bearer token required, timing-safe comparison, and any request carrying `Origin` or `Sec-Fetch-Site`
is refused because a web page **can** post to localhost.

## Risk rails

Enforced in `extension/src/core/risk.js`. Every order passes all of them, and batch admission
applies caps incrementally so a batch cannot collectively breach a cap each member passes.

| Rail | Default |
| --- | --- |
| `killSwitch` | off |
| `maxTotalNotionalUsd` | 500 |
| `maxNotionalPerOrderUsd` | 100 |
| `maxConcurrentOrders` | 12 |
| `maxLeverage` | 1 |
| `dailyLossLimitUsd` | 50 |
| `maxSlippageBps` | 300 |
| `minLiquidationDistancePct` | 25 (perps only; ignored when the venue reports none) |
| `maxOrdersPerTick` | 4 |

Rails **fail closed**: a missing or NaN state field is neutralised to a safe value and reported
rather than silently disabling its rail.
