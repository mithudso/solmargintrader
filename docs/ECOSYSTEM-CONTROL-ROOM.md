# Operational paper control room

The control room observes the actual ecosystem owners and sends explicit,
scoped requests to their existing control interfaces. It combines server state,
configuration launches, research progress, per-coin results, forward accounting,
Oracle voter selection and the documentation wiki. Automated operation remains
paper/disarmed. Oracle has no order, signing or submission authority.

## Release and installation

Release 0.2.1 installs these compatible local packages:

| Package | Version |
| --- | --- |
| Ecosystem | 0.2.1 |
| Bot Manager | 0.4.0 |
| Oracle | 0.2.1 |
| Headless research runtime | 0.1.2 |
| Canonical Backtester | 0.1.1 |

Python 3.13 or newer is required. The dedicated environment is
`/Users/mitch/.venvs/solecosystem-0.2.1`. The primary experiment home is
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2`.

From a clean source checkout, installation and start use:

```sh
python3 /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py start \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2
```

The installer checks package identities, strategy catalogs and actual local MCP
transport. It binds a completed environment to its exact package inputs,
including packaged web, API and wiki files. It refuses an incompatible existing
environment. It does not upgrade an active environment in place. A health check
does not establish that market history, future outcomes or live execution exist.

The installed lifecycle commands are:

```sh
/Users/mitch/.venvs/solecosystem-0.2.1/bin/solecosystem start \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2
/Users/mitch/.venvs/solecosystem-0.2.1/bin/solecosystem status \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2
/Users/mitch/.venvs/solecosystem-0.2.1/bin/solecosystem stop \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2
```

Use the current `ui_url` from status. The control server publishes its bound
address, instance, version and diagnostic PID in
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2/control-server.json`.
Its owner lock and matching HTTP response establish readiness; a PID alone does
not. Ports can change after a restart.

## Independent control service

The HTTP control service has a different lifetime and owner lock from the paper
pipeline. Stopping a pipeline or its F5 worker retains the control room so its
Start button remains usable. The pipeline can ensure that its control service
exists without taking ownership of the shared recorder.

A foreground control service can also run independently:

```sh
/Users/mitch/.venvs/solecosystem-0.2.1/bin/solecosystem-ui \
  --home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2 --port 8768
```

Its address is then `http://127.0.0.1:8768`. A second server for the same home
refuses while the first owner holds its lock. Do not start another server merely
because a pipeline is stopped; inspect the published control-server identity.
No OS login auto-start is implied by these commands.

For the 0.2.1 fee release, update only the independent UI generation using the
new environment after reconciling its prior owner lock, checkpoint and HTTP
identity. Keep the running V1 and V2 pipelines, recorder, archives and frozen
economic settings unchanged. Each owner retains its observed version. Do not
restart a pipeline merely to replace the UI, and do not use a blanket process
kill. Existing explicit 10 bps cohorts remain 10 bps; a newly launched Jupiter
paper scenario defaults to the user-approved 50 bps referral assumption.
Keep `/Users/mitch/.venvs/solecosystem-0.1.1` and
`/Users/mitch/.venvs/solecosystem-0.2.0` immutable for their existing pipeline
owners; the replacement UI runs from `/Users/mitch/.venvs/solecosystem-0.2.1`.

## Preserve the existing V1 experiment

The running V1 producer, F5 worker and data remain associated with:

- `/Users/mitch/.venvs/solecosystem-0.1.1`
- `/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1`

The new interface registers that experiment as `legacy-v1`. It reads its native
evidence without restarting its producer, changing its frozen configuration or
replaying its native ledgers. Recording and voter preferences are separate
projections; their controls do not grant authority to restart the legacy owner.

The new Backtester changes F5's economic-code fingerprint and Oracle's strategy
versions. A new runtime must not reopen a legacy Oracle archive through its own
policy constructor or resume a legacy F5 batch under a different fingerprint.
New experiments use new homes and archives. Raw legacy observations remain
usable through the explicit read-only source adapter, with their recorded policy
identity intact. No policy metadata is renamed to make incompatible code pass.

## Server actions and observations

Each supported action has its own button. Disabled actions show the owner's
capability reason. The interface separates requested state, observed state,
process liveness, input freshness and completed evidence.

| Owner | Controls | Evidence to inspect |
| --- | --- | --- |
| Paper pipeline | Start, stop, restart | Owner lock, phase, heartbeat and current work |
| F5 Backtester / forward worker | Start, stop, restart the selected experiment | Frozen matrix, terminal cell counts, forward checks and backlog |
| Oracle evaluator | Start, pause, restart on a compatible active pipeline | Observed runtime settings, per-instrument freshness and issued forecasts |
| Shared recorder | Start and acknowledged shared stop | Singleton owner, snapshot age, received messages, reconnects and recording location |
| Bot Manager | Explicit macOS service install/start and uninstall/stop | Matching service definition and observed supervisor lock |

Stop requests are cooperative and preserve evidence. A completed request receipt
does not substitute for a fresh observed state. Some actions wait for the owner
to reach a safe checkpoint. A timed-out or interrupted acknowledgment is not a
reason to submit a new conflicting request automatically.

The recorder serves other consumers. Its stop action requires explicit shared
impact acknowledgment. Recovery preferences affect this control family; another
independent owner can still restart its recorder. The UI reports that boundary.

Manager stop retains positions and journals. It is not a cancel-orders,
close-position or live emergency-liquidation command. Those capabilities remain
unavailable unless their actual execution owner supports them.

## Choose a configuration and launch

Research launches select a name, coins, registered strategy cards, bar intervals,
card presets, historical dates, virtual capital, paper cost assumptions and P&L
recording preference. The configuration is frozen in a new experiment under
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2/research`.
Repeating the same action identity reuses its receipt instead of silently
creating another experiment.

The stages are acquisition, historical backtesting and prospective forward
testing. Progress bars use real attempted inputs and cell counts. A completed
historical matrix can contain missing, unsupported, failed or partial cells.
Those states stay visible. Only configurations with usable owner evidence enter
the forward stage. Forward testing remains an ongoing observation stage; a
recorded call is not a resolved outcome or approval for live operation.

Select a bot or research trial to inspect its strategy version, configuration,
coin, source, historical selection evidence, forward calls and economics. The
per-coin view separates successful and losing resolved trials from unavailable
or incomplete evidence. CPCV selection scores and historical returns retain
their stated scope; selected performance is not independent validation.

Manager configuration controls use its typed schema and immutable revisions.
Create saves a draft. Edit saves a revision without replacing active settings.
Apply requires the owner's stopped, reconciled zero-exposure boundary. Start
and stop control the selected owner rather than constructing another worker.
Input preparation, registration and data checks use owned descriptors; HTTP
callers cannot supply arbitrary filesystem paths.

The current canonical manager families support bounded historical and
prospective reference paper runs. Its accepted prospective Oracle source is
specifically SOL/USD reference observations, with explicit consent for the
Jupiter SOL/USDC target difference. The broader per-coin research matrix belongs
to F5. A matching strategy name does not imply that the manager and F5 use the
same execution model. Conditional quote-cycle research requires actual evidence;
the interface does not invent a cycle to enable a button.

## Forward P&L recording and profit assessment

Recording defaults to on. The recording switch applies to the selected
experiment's accounting projection, using each native call's issuance time.
Changes create a new policy revision. Prior entries and the owner's native
forward journal remain intact. Re-enabling recording does not fill an excluded
period retrospectively.

The projection binds source call identity, policy revision and later settlement.
Existing native calls are included under the initial default-on policy. Disabling
recording excludes newly issued calls from this projection; it does not prevent
the forward owner from recording its own calls or economics. An experiment with
an unrecorded period cannot claim complete whole-period profit.

Forward P&L compounds resolved, non-overlapping calls within each independent
virtual trial. `net_return` already includes the model's fees, slippage and
borrowing costs. The UI does not subtract those costs a second time. Each trial's
frozen virtual capital is an explicit display basis, not a shared funded cash
allocation. Adding independent trial balances does not establish portfolio P&L.

Profit, loss and break-even labels refer to resolved recorded paper economics.
No resolved economics means unknown, not zero profit. Missing economics,
expired outcomes, unavailable source data or unrecorded periods also remain
unknown. Pending calls remain visible. Unresolved positions do not receive an
invented unrealized valuation. Reference currency is retained; USDC is not
silently valued as USD.

The provider selector is separate from the market-data source. Configured
Jupiter fees and borrow/slippage rates are modelling assumptions. They do not
establish executable quotes, actual route charges, network fees or realized
profit after every real execution cost.

## Oracle voters and aggregate strength

Choose voters per instrument from the fourteen identified cards. Save creates a
selection revision; it does not alter strategy parameters, recorded predictions,
resolution history or the producer's policy. Deselected cards remain observable
and continue their existing shadow evaluation.

The aggregate displays its direction, signed weighted vote balance, horizon,
timestamps, policy/selection identity and contributing/excluded votes. Freshness,
minimum resolved evidence and measured accuracy still gate every selected vote.
The displayed percentage is agreement, not a calibrated probability of profit.

The retained vote policy uses accuracy as weight and excludes accuracy at or
below 50%; a strategy must exceed 50% to vote.
It doubles the accuracy weight only after more than 100 hits. Thus a perfect
record at 101 hits has a 200% total vote; it is not a 200% addition. Flat votes
contribute to the denominator. The current policy uses all resolved evidence in
that strategy version and requires at least twenty resolutions.

Aggregate thresholds use signed balance: Strong Buy at or above 60%, Buy at or
above 20%, Strong Sell at or below -60%, Sell at or below -20%, and Flat between
the inner thresholds. Missing, stale, expired, deselected or insufficient votes
produce their explicit exclusion reasons. An empty eligible set is unavailable,
not Flat. New selection settings never manufacture resolved evidence.

The Oracle page also shows append-only graph history stored beside forecasts
in the Oracle archive. One completed-bar evaluation records all fourteen
strategy directions, their then-known accuracy and voting weights, the
full-catalog aggregate, observed price and shape metrics from prior completed
bars. The chart overlays directions at observed prices; it does not infer price
targets. The latest 240 ticks are returned with `/api/oracle` for the vendored
TradingView Lightweight Charts renderer. Existing v1 archives remain readable;
they show no graph history until the v2 evaluator records new ticks.

## Wiki, security and manual swaps

The Wiki tab searches the packaged source-linked documentation snapshot. It
includes component guides, strategy cards, architecture, lifecycle, design and
historical plans. Each page retains its original file location, content hash and
commit provenance when available. Historical plans are not marked delivered by
appearing in the wiki. See
`/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-WIKI.md`.

The control origin binds loopback only. It validates Host and Origin, accepts no
CORS access, bounds requests and requires a per-instance session nonce for
mutations. Actions use UUIDs and durable receipts; reusing an ID with different
content is rejected. Stored guides, external data and manager events are text,
not instructions or executable HTML. No secrets or arbitrary log bodies are
returned to the browser. Full server observability remains bounded by what the
actual owner persists; absent manager log sinks remain unavailable.

The manual Jupiter page uses a separate public loopback origin and a browser
wallet. It has no privileged control session or server signing/submission API.
The owner approved 0.5% = 50 bps as the manual page's default referral fee and
for new Jupiter paper scenarios. This is within the current published range of
50 through 255 bps. Existing explicit 10 bps cost models remain frozen; earlier
results are not recalculated under the new default. A supported configuration
only makes the manual integration eligible for initialization. A manual click,
provider availability, referral-account eligibility, wallet connection and each
wallet approval remain separate gates. Supported configuration is not evidence
of an eligible on-chain referral account or funded-swap readiness. See
`/Users/mitch/dev/solmargintrader/docs/ECOSYSTEM-SWAPS.md`.

## Verification and source locations

```sh
cd /Users/mitch/dev/solmargintrader
/Users/mitch/.venvs/solecosystem-0.2.1/bin/python -m unittest discover -s /Users/mitch/dev/solmargintrader/ecosystem/tests -t /Users/mitch/dev/solmargintrader -v
/Users/mitch/.venvs/solecosystem-0.2.1/bin/python -m unittest discover -s /Users/mitch/dev/solmargintrader/oracle/tests -t /Users/mitch/dev/solmargintrader -v
PYTHONPATH=/Users/mitch/dev/solmargintrader/botmanager/src /Users/mitch/.venvs/solecosystem-0.2.1/bin/python -m unittest discover -s /Users/mitch/dev/solmargintrader/botmanager/tests -t /Users/mitch/dev/solmargintrader/botmanager
ruff check /Users/mitch/dev/solmargintrader/ecosystem /Users/mitch/dev/solmargintrader/oracle /Users/mitch/dev/solmargintrader/scripts/bootstrap_ecosystem.py /Users/mitch/dev/solmargintrader/scripts/build_ecosystem_wiki.py
node --check /Users/mitch/dev/solmargintrader/ecosystem/web/app.js
node --check /Users/mitch/dev/solmargintrader/ecosystem/web/swap.js
python3 /Users/mitch/dev/solmargintrader/scripts/build_ecosystem_wiki.py --check
```

Tests use isolated stores, controlled source data and local HTTP servers.
Separate installed acceptance must verify the loaded package/asset identity,
actual action receipts and state transitions, browser behavior and retained
evidence after restart. A simulated profit case is not evidence that a live
market or a current real forward trial is profitable. A wiki integrity check
does not establish owner health.

| Responsibility | Source location |
| --- | --- |
| Durable controls and owner dispatch | `/Users/mitch/dev/solmargintrader/ecosystem/control.py` |
| HTTP contracts and origin isolation | `/Users/mitch/dev/solmargintrader/ecosystem/web.py` and `/Users/mitch/dev/solmargintrader/ecosystem/api/control.openapi.json` |
| Independent UI ownership and readiness | `/Users/mitch/dev/solmargintrader/ecosystem/ui_service.py` |
| Forward accounting and recording policy | `/Users/mitch/dev/solmargintrader/ecosystem/performance.py` |
| Voter selection and aggregate projection | `/Users/mitch/dev/solmargintrader/ecosystem/votes.py` |
| Native owner event projection | `/Users/mitch/dev/solmargintrader/ecosystem/telemetry.py` |
| F5 historical/forward lifecycle | `/Users/mitch/dev/solmargintrader/soltui/f5_batch.py` and `/Users/mitch/dev/solmargintrader/soltui/forwardtest.py` |
| Manager commands and canonical strategies | `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/registry.py` and `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/strategies/__init__.py` |
| Manager Oracle input preparation | `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/input_commands.py` and `/Users/mitch/dev/solmargintrader/botmanager/src/botmanager/oracle_data.py` |
| Wiki selection, serving and compilation | `/Users/mitch/dev/solmargintrader/ecosystem/wiki.py` and `/Users/mitch/dev/solmargintrader/scripts/build_ecosystem_wiki.py` |
