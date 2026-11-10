# MCP and repository tooling

## Oracle stdio service

The repository ships one local stdio MCP server in `oracle/server.py`, installed
as `soloracle-mcp` by `oracle/pyproject.toml`. It exposes read-only archive views,
guide routing, readiness and advisory veto. It never signs or submits orders.
The Chrome extension, its CLI and local HTTP API instead use
`extension/src/core/commands.js`; they are not MCP transports. The manager's
`botmanager/src/botmanager/registry.py` is another CLI registry, not an MCP server.

Configure a reviewed installed `soloracle-mcp` executable, or an installed Python
with `-I -m oracle.server`, as a client-local stdio server. Select the exact archive,
instrument, repository and optional manager/control home through its documented
arguments. See [Oracle setup and subscriptions](../oracle/README.md#mcp-contract-and-subscriptions)
and [the control-room guide](ECOSYSTEM-CONTROL-ROOM.md). Control-home archives
use the inert `oracle/reader.py` adapter; missing or incompatible input remains
unavailable. Standalone startup outside that layout uses
`oracle/engine.py` and may initialize the selected archive schema. It does not start
a market feed, create observations or grant order permission.

Inspect available options without starting the service:

```sh
INDEX_NO_AUTO=1 /Users/mitch/.venvs/solbot-0.7.0/bin/python -I -m oracle.server --help
```

The eight tools in `oracle/server.py` are:

| Tool | Scope |
| --- | --- |
| `oracle_status` | Source and archive status |
| `oracle_market` | Source-labelled market snapshot |
| `oracle_predictions` | Selected prospective forecast view |
| `oracle_strategies` | Strategy catalog/view |
| `oracle_history` | Bounded historical event pagination |
| `oracle_guidance` | Source-backed repository guide routing |
| `oracle_readiness` | Evidence and manager readiness view |
| `oracle_veto` | Expiring advisory veto; enforcement remains with each executor |

Three resources, `oracle://market`, `oracle://predictions` and `oracle://status`,
support subscriptions. Notifications invalidate a snapshot; clients read it again.
They do not guarantee delivery of every tick. Use bounded history cursors to recover
archive events. Subscriptions are per client and do not persist across reconnects.
Unknown request fields refuse. Fixed public error envelopes exclude dependency
exception text. Neither tool availability nor an advisory veto proves live readiness.

The local process/filesystem owner is the access boundary. This stdio service has
no network listener or remote authentication layer. A repository `.mcp.json` or
`.vscode/mcp.json` is not supplied; client registration is optional and host-specific.
Development agents may also use machine-wide Stele/global-AI-hub connectors.
Never copy machine credentials or host-specific secret values into tracked files.

## Contract verification

There is no invented `--self-test` flag. The existing tests exercise actual SDK
stdio sessions, resource subscriptions, selection, request validation and teardown
with temporary archives:

```sh
INDEX_NO_AUTO=1 python3 -m unittest oracle.tests.test_server oracle.tests.test_selected_server
```

Use the reviewed environment from [installation](INSTALLATION.md); tests do not
certify a live feed, authenticated trading account or executor enforcement.

## Retrieval without a connector

```sh
INDEX_NO_AUTO=1 python3 index/build.py --check
INDEX_NO_AUTO=1 python3 index/search.py --text "fee_bps"
INDEX_NO_AUTO=1 python3 index/search.py --file extension/src/core/risk.js
```

Keyword retrieval is local. Set `INDEX_NO_AUTO=1` even for text lookup: the search
entry point can otherwise trigger idle semantic indexing. Semantic vectors remain
an explicit optional operation; see `index/README.md`. A missing connector does not
authorize starting inference, indexers, watchers or another runtime owner.

When Stele is configured, follow the project task/knowledge workflow. Never create
or bind a different project automatically.
