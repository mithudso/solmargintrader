# Operate the paper ecosystem

The control room delegates work to the existing owners. It does not sign or
submit orders. The manual swap page uses an isolated Jupiter browser widget and
requires the user's wallet approval. Automated live readiness remains a separate
owner decision backed by actual evidence.

## Installation and ownership

Python 3.13 or newer is required. The bootstrap installs the five canonical local
packages into `/Users/mitch/.venvs/solecosystem-0.2.0`. It verifies installed module
locations, versions, strategy catalogs and actual Oracle MCP transport before use.

```sh
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py start
```

The primary experiment remains at
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1`. The UI runs as a
separate process and publishes its actual URL in that home's
`control-server.json`. Closing a terminal or stopping a pipeline does not remove
the UI's Start button. `control-server.lock` proves control-service ownership;
PIDs are diagnostic. The start helper verifies the bound HTTP instance against
the private checkpoint and never treats an old PID or file as liveness.

For an existing installed environment:

```sh
/Users/mitch/.venvs/solecosystem-0.2.0/bin/solecosystem start
/Users/mitch/.venvs/solecosystem-0.2.0/bin/solecosystem status
/Users/mitch/.venvs/solecosystem-0.2.0/bin/solecosystem-ui \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1 --port 8768
```

The last command runs a foreground viewer/controller if that home has no control
server owner. The bootstrap chooses an available port automatically. Use its
reported URL rather than assuming a port after restart. Completed environments
are immutable; do not upgrade a running environment in place.

## Server controls and action receipts

The Server page shows the control process, pipeline, F5 backtest/forward worker,
Oracle, existing shared recorder and Bot Manager. State, heartbeat, PID and source
availability are separate fields. Buttons reflect the actual supported commands:

| Component | Actions | Owner |
| --- | --- | --- |
| Pipeline | Start, cooperative stop, restart | `ecosystem.runner` |
| Backtest / forward worker | Start, stop, restart this run | `soltui.f5_batch` |
| Oracle | Enable, pause, restart its evaluation cache | Pipeline's Oracle instances |
| Shared recorder | Start existing singleton, stop current instance | `soltui.pricefeed` |
| Bot Manager | Explicit service install/start and uninstall/stop where supported | `botmanager.service` |
| Manager configuration | Create, save revision, adopt, start, stop | Manager command registry |

A shared-recorder stop requires an explicit acknowledgment. It disables recovery
for this control family, including its child runs. Other independently operated
owners may recover the global recorder. The UI reports this limit; it cannot
promise a permanent global stop. Pipeline stops retain archives and do not stop
that shared recorder.

Every mutation uses a canonical UUID and a durable receipt. Repeating the same
UUID and payload reads the original receipt; a different payload conflicts.
Queued, running, succeeded, failed and interrupted states remain distinct.
Succeeded means the owner command returned, not that a requested worker is
already healthy. Inspect observed state and progress after the request.

If the controller dies after an owner acted but before it saved the result, the
receipt becomes interrupted. It is never automatically replayed. Reconcile the
owner before issuing a new request. UI network failures also do not retry launches.
Automatic recovery and explicit actions share the control-family mutation lock.

Log buttons read only fixed owner sinks, with bounded tails, source timestamps
and redaction. Unknown paths, symlinks and nonregular files are refused. Truncated
tails are not complete history. Manager events remain in their native journals;
an absent configured freeform log sink is explicitly unavailable.

## Launch and inspect a bot

Choose a strategy card, assets, interval, horizon preset, date bounds, independent
paper capital and cost scenario. The launch review separates Coinbase USD
reference data from the intended swap provider. A launch creates a new immutable
experiment under the primary home's `research/` directory. It never changes the
inputs or parameters of a running experiment.

Acquisition, backtest, forward and live-readiness stages use actual owner
evidence. Progress bars report counts against a known target; unavailable or
unbounded stages do not acquire invented percentages. Missing history and
unsupported runners stay visible. A live-readiness stage is unavailable until
the responsible execution component provides its required evidence.

Select a run, then a bot to compare that strategy, interval and horizon across
all attributable coins. Historical rows show selected CPCV Sharpe, selected
median return and parameters. Those are selection evidence, not independent
validation. Forward rows show recorded, pending and resolved calls, cost coverage,
paper capital, realized paper P&L and the profitability assessment.

Manager configurations use the owner's schema and immutable revision APIs.
Saving a revision does not change a running worker. Adopt settings only through
the owner's stopped, reconciled zero-exposure boundary. Unsupported strategy
runtimes remain disabled with owner reasons. Research `grid` and Manager's grid
execution model are different components and are not joined by name alone.

## Forward-test profit and recording

The user selected recording **on by default**. Its versioned policy resides in
`paper-accounting.sqlite3`, separately from native source journals. Initial
projection can backfill existing native paper evidence and says so. Later policy
changes apply by the native call's issuance time. Disabling recording stops new
accounting entries, retains prior records and never erases source evidence.

Each native trial is a non-overlapping virtual account. Compound its resolved
`net_return` values in order. That return already includes modelled fees,
slippage, borrowing and liquidation. Do not subtract these costs twice. Frozen
F5 capital supplies an explicitly labelled paper-account basis. It is not
reserved or shared capital, and the UI does not sum trials into an invented
portfolio.

No resolved economic outcomes means profit is unknown, including when a native
summary initializes its equity to one. Unrecorded periods, missing economics,
expired outcomes, changed inputs or incomplete projection suppress a whole-trial
profit claim. Open outcomes have no invented unrealized P&L. Reference currencies
are retained; USD values require an explicitly USD source, without assuming a
stablecoin peg. Paper profitability under stated assumptions is not live profit
or a calibrated probability of future profit.

## Swap provider and costs

`swap_provider` is independent of the data source. `jupiter` can accompany
Coinbase reference observations. New experiments freeze explicit configured
base-fee, referral, slippage and borrowing assumptions. Base fee plus referral
becomes the paper engine's per-side fee exactly once.

These settings change the paper economics but do not certify historical Jupiter
spot routing. The reused F5 engine retains its documented execution model.
Network fees, priority fees, account rent and changing routes are not invented.
Actual Jupiter fees require a current quote for the exact token mints and size.
See `docs/ECOSYSTEM-SWAPS.md` for the separate manual wallet interface and the
published paid-referral minimum versus the retained 0.1% setting.

## Oracle voter selection and consumers

The Oracle page selects the instrument and its enabled strategy cards. Saved
selection is versioned per run and instrument. It changes aggregation only;
all cards continue their prospective shadow evaluation. Empty selection, stale
data, insufficient evidence and accuracy below policy thresholds abstain.

The prominent percentage is the signed weighted vote balance, not profit
probability. The existing 60% accuracy threshold and bonus after more than
100 hits remain unchanged. Issuance, expiry, horizon, contributing/excluded
cards and provenance remain available.

HTTP and current MCP consumers use the selected view. For an exact controller
archive layout the MCP server detects its home; explicit configuration is:

```sh
/Users/mitch/.venvs/solecosystem-0.2.0/bin/soloracle-mcp \
  --archive /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3 \
  --instrument SOL/USD \
  --control-home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1 \
  --repo /Users/mitch/dev/solmargintrader
```

Tools, resources, subscriptions and advisory veto read the same selection.
Selection changes invalidate the resource without rewriting forecasts. Current
standalone archives without a control binding keep their original behavior.
An explicitly required selector fails unavailable if its adapter cannot load.
Clients pinned to older installed server versions need the current executable.
Veto remains advisory unless an executor demonstrably consumes it.

## Wiki and locations

The Wiki tab compiles Oracle, ecosystem, Manager, Backtester, strategy-card and
relevant architecture/operating guides into an installed snapshot. It searches
full text and displays original file locations, content hashes and provenance.
It treats source Markdown as content, never instructions to execute. Imported
or incomplete cards are labelled and are not execution evidence.

Runtime evidence remains with its owners:

- `state.json`, `runtime-settings.json`: experiment state and requested controls.
- `control.sqlite3`: action receipts and durable child-run identities.
- `registrations.sqlite3`: external trial identities and observations.
- `paper-accounting.sqlite3`: recording policy and economic projection.
- `voters.sqlite3`: immutable selection revisions.
- `batches/<id>/batch.sqlite3`, `forward.sqlite3`: authoritative F5 results.
- `oracle/<asset>/history.sqlite3`: observations, calls and resolutions.
- Bot Manager's configured home: specifications, revisions and runtime journals.

The API contract is packaged at `ecosystem/api/control.openapi.json` and served
at `/api/openapi`. GET routes expose observations. `/api/actions` requires JSON,
the exact local Origin and the in-memory `X-Sol-CSRF` nonce from `/api/session`.
Reads and writes stay loopback-only; this is not a remotely authenticated service.

## Verification

```sh
python -m unittest discover -s ecosystem/tests -t .
python -m unittest discover -s oracle/tests -t .
ruff check ecosystem oracle scripts/bootstrap_ecosystem.py scripts/build_ecosystem_wiki.py
node --check ecosystem/web/app.js
node --check ecosystem/web/swap.js
python scripts/build_ecosystem_wiki.py --check
```

Unit and controlled-HTTP tests include restart, duplicates, origin isolation,
credential redaction, recording gaps, cost conversion, source mutation, selected
MCP resource notifications and no-order behavior. Real installed acceptance must
separately check package identity, browser controls and an actual paper lifecycle.
A synthetic profitable or losing example does not establish profitability of
the still-open real forward trials. Manual wallet signing and funded Jupiter
swaps require separate evidence and are not exercised by these checks.
