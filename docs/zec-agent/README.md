# Zec

Zec researches Jupiter GUM ZEC perpetuals, runs offline and forward paper tests,
and reviews exit decisions for an identified position. The [agent
definition](../../.claude/agents/zec.md) governs both harnesses. The
[optimized build prompt](optimized-prompt.md) records the brief and acceptance
criteria used for this delivery.

## Open Zec

From the repository root, start Claude Code with:

```sh
claude --agent zec
```

In a Codex session opened at the repository root, ask Codex to delegate a
bounded task to the custom `zec` agent. Its [project
definition](../../.codex/agents/zec.toml) loads the shared instructions. For
example, ask it to review the directional benchmark and identify the strongest
after-cost result and its holdout limitations.

Zec starts in read-only advisory mode. A request to review an open position
needs its exact venue, product, and position identity. Zec verifies those
details against authenticated account data, then checks fresh marks,
executable quotes, closed bars, costs, liquidation distance, and any protective
orders. It reports the exit trigger it can justify from current evidence and
the conditions that would invalidate it.

## Connect the Chrome advisory workflow

Load this revision of SolMarginTrader into Chrome. Get its extension ID from
`chrome://extensions`. Install the native host from the repository root:

```sh
node extension/tools/zec-native-install.js EXTENSION_ID
```

Open the SolMarginTrader dashboard, expand **Zec advisory**, and select
**Enable local connection**. The dashboard reports when Chrome has connected.
The bridge uses a private Unix socket for the current OS user. A second profile
using that socket cannot connect until the first disconnects. On Linux, use the
Chrome distribution's native host directory with `--dir` if its location differs.

```sh
node extension/tools/zec-advisor.mjs snapshot
node extension/tools/zec-advisor.mjs watch --samples 12 --interval 10
node extension/tools/zec-advisor.mjs ask --publish
node extension/tools/zec-advisor.mjs ask --provider codex --publish
```

The watch emits one JSON object per line. The snapshot includes the GUM ZEC mark
and its provider and receipt times, up to twelve complete five-minute candles,
the browser grid mode, and ZEC paper workbench state. The paper observation time
shows when its account was last observed. A stored running flag describes the
configured paper strategy. Funded position inventory is unavailable on this
channel. A disconnected host returns an error. Market or candle failures appear
in the relevant snapshot field.

`ask` invokes the project `zec` agent through Claude Code with tools disabled.
Use `--provider codex` to load the same definition in a tool-free Codex session.
Add `--question` to focus the assessment. `--publish` attaches the returned
suggestion to the snapshot and shows it in Chrome. Chrome accepts one suggestion
per recent snapshot, with idempotent retry of the same suggestion, and marks
older suggestions expired. Suggestions are for owner review. Orders, strategy
settings and signing remain under the existing controls.

| Operation | Shared CLI command | Existing authenticated API |
| --- | --- | --- |
| Get the browser snapshot | `zecSnapshot` | `GET /v1/zecSnapshot` |
| List suggestions | `zecAdvisories` | `GET /v1/zecAdvisories` |
| Submit advice | `zecAdvice --advice JSON` | `POST /v1/zecAdvice` with `{"advice":{...}}` |

Use `node extension/tools/cli.js <command> --json` for CLI JSON. The existing
HTTP API uses the owner bearer token. The Zec helper uses the scoped native
connection without that token. The registry continues to provide the owner
commands through the existing local CLI and HTTP API. The Chrome connection
can be enabled or disabled from its dashboard. Closing Chrome disconnects it.

## Check or monitor paper trading

Run one observation from the repository root:

```sh
zec_session="$(mktemp -d)/session"
node extension/tools/zec-gum-live.mjs --output "$zec_session" --once
```

The runner defaults to one observation if neither sample option is passed.
Expect `session.json` and `events.jsonl` in the fresh directory. A healthy
observation reports a current public GUM mark and each paper profile's
decision state. The first observation can bootstrap the profiles with no
open position. Missing or stale input can produce an issue event and a
nonzero exit. The log labels simulated fills and records the resulting
position separately for every profile.

For a monitoring request, give Zec a named owner, expiry, and finite sample
count. For example, ask for 30 attempts at a 10-second polling interval,
ending on the earlier of the agreed expiry or the final sample. The polling
interval excludes request time. Check the start receipt and process state
before relying on the monitor. Use the [directional
benchmark](../../research/papers/results/zec_gum_25x_5m_directions.md) for
retrospective results.

## Funded exit boundary

A supervised funded exit needs an authenticated, expiring, single-use
position mandate and a deployed GUM close-only service. The service must
verify the exact account and position before authorizing an at-most-once
reduce-only order, then reconcile the remaining position and actual fill.
Zec reports the capability verdict before attempting an exit. The
[TradingView webhook](../JUPITER-ZEC-WEBHOOK.md) targets a direction and can
reverse a position. It is outside this workflow. Wallet material stays with
the guarded signer. Paper evidence and an exit recommendation add no funded
authorization.

The [host-side guard](../../oracle/zec_exit.py) reuses the GUM signer,
position checks and venue reconciliation. Before deployment, the execution
owner must supply an authenticated mandate store, a stable position-lineage
attestor, and the same exclusive account lock used by every other execution
path. The installed webhook and hosted Oraclebot MCP currently lack a
compatible GUM close-only operation. The host guard is usable in offline
execution tests while Zec's funded operation stays unavailable.
