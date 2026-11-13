# Oraclebot persistent operations

Version: 1.1.0
Delta: Supervise the actual paper pipeline, F5 worker and Oracle; preserve the failed historical cohort and require full runtime health.
Delta: Document supervised ecosystem availability, durable alerts, independent heartbeat checks and daily reports.

The existing Solbot suite owns the manager and independent local control room.
Its LaunchAgent has `RunAtLoad` and `KeepAlive`; it starts at user login and
restarts after process failure. It does not start before FileVault unlock/login,
prevent physical power loss, or turn a stopped research plan into a running one.
Paper intents, archives and execution rails remain unchanged. The manager-only
installer refuses a same-home managed suite, and its control-room action is
disabled while that suite owns the manager. The manager card identifies the
managed suite instead of showing the legacy definition as absent.

The November 12 repair removed the conflicting manager-only LaunchAgent after
backing it up. The two definitions had competed for one `supervisor.lock`, and
the suite repeatedly exited with `already_running`. The suite now owns that
manager. Never reinstall the manager-only service alongside it for the same home.

## Actual pipeline ownership

The owner screenshot exposed a narrower initial repair: the HTTP/UI and manager
were healthy while the actual paper pipeline, F5 worker and Oracle were stopped.
The old batch refuses changed evaluation code, and its Oracle archive refuses a
different policy. Those guards remain enforced. The historical home stays at
`/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2`.

A separately identified generation uses the same explicitly saved SOL/1d/RSI
medium plan, original date bounds and cost settings in
`/Users/mitch/.local/share/solmargintrader/ecosystem-operational-20261112`.
Its normal, fixed installed package bundle lives in
`/Users/mitch/.venvs/oraclebot-pipeline-0.4.8`. The suite, control room and native
helper bind to that generation. No historical code identifier, policy or result
is relabeled.

The home-derived pipeline LaunchAgent runs `ecosystem.cli run` in the foreground.
It starts at login and restarts unsuccessful exits. A30-second start interval
also checks recovery after a manually started detached owner exits. A matching
explicit stop marker keeps that generation stopped, including across login.
A manual Start creates a new generation; automatic recovery never clears a
matching stop marker. The existing F5 lock prevents a second worker, and a
surviving worker is adopted after a pipeline crash.

```sh
/Users/mitch/.venvs/oraclebot-pipeline-0.4.8/bin/python -I -m ecosystem.pipeline_service status --home /Users/mitch/.local/share/solmargintrader/ecosystem-operational-20261112
/Users/mitch/.venvs/oraclebot-pipeline-0.4.8/bin/solecosystem status --home /Users/mitch/.local/share/solmargintrader/ecosystem-operational-20261112
```

Monitor1.1.0 separately observes paper pipeline ownership/heartbeat, the actual
F5 worker lock/phase, enabled Oracle processing and fresh Oracle market inputs.
Pipeline, worker or Oracle failure makes operational readiness false even if
HTTP and Bot Manager remain up. Explicit operator pauses remain distinguishable.
An active Oracle with insufficient eligible evidence does not become a trading
recommendation; empirical eligibility and process health remain separate.

## Observe and operate

```sh
/Users/mitch/.local/bin/solbot stack status
/Users/mitch/.local/bin/solbot health-check
/Users/mitch/.local/bin/solbot ui status
```

The verified control-room URL comes from `ui status`; it can change after restart.
Use `solbot stack restart` for deliberate maintenance. The suite reports manager,
control-room and market-data health separately. Ready availability can coexist
with stale market data. Do not claim a healthy forecast because the HTTP server
is alive, and do not resume frozen research owners to silence a freshness warning.

## Monitoring and alerts

A separate read-only observer samples `solbot health-check` every minute. Two
consecutive failed observations trigger a component incident. Two successful
observations resolve it. Failure and recovery state, delivery keys and pending
notifications survive observer restart in SQLite. Alertlane accepts events using
its existing private ingest credential; that credential is read in place and is
never copied into the monitor configuration or reports. The installed Alertlane endpoint uses its existing verified HTTPS origin; the
production server rejects plain HTTP. Failed delivery exposes a sanitized error
code in monitor status and retries
with the same idempotency key. Mac notification attempts have separate state.

The current Alertlane instance is dry-run and has no active paired phone.
An accepted incident therefore proves the incident inbox, not phone push. The
observer also attempts Mac Notification Center notifications. A successful
AppleScript command does not prove that the user saw the banner. Notification
permissions and Focus settings still apply. The observer never changes global
Alertlane mode or pairs a phone automatically.

The observer publishes only observation time, readiness, overall state and
observer version to the `ORACLEBOT_HEARTBEAT` GitHub repository variable. It uses
the existing `gh` credential store. No local URL, home path, account credential,
market position or wallet key is published. A separate GitHub Actions runner also probes the hosted website health API and
checks heartbeat freshness and local readiness every five minutes, subject to GitHub scheduling
delays. A missing heartbeat covers host, network, observer and publisher failures.
The runner opens one dedicated availability issue, mentions the repository owner,
and closes that issue after a fresh ready heartbeat. It cannot distinguish a
power failure from a GitHub credential failure without further investigation.
GitHub notification acceptance is separate from inbox delivery.

The external workflow has isolated `failure` and `recovery` acceptance modes.
They use a separate issue and never stop a service or modify the real incident.
Recovery mode requires an actual fresh ready heartbeat. This exercises independent
issue creation and closure; it does not establish physical power-loss acceptance
or a guaranteed paging deadline.

## Reports and installed paths

- Observer state and reports: `/Users/mitch/.local/state/oraclebot-operations`.
- Current report: `/Users/mitch/.local/state/oraclebot-operations/reports/latest.md`.
- Daily JSON and Markdown reports: the same reports directory, named by date.
- Monitor LaunchAgent: `/Users/mitch/Library/LaunchAgents/com.mitchhudson.oraclebot-operations.plist`.
- Suite LaunchAgent: `/Users/mitch/Library/LaunchAgents/com.solmargintrader.suite.3bbfdc4f6989.plist`.
- Repair and acceptance evidence: `/Users/mitch/.local/state/oraclebot-operations-20261112`.

The observer writes the previous day's report after 09:00 local time, including
weekends, and updates the current report each sample. Reports count observed
checks and expose the largest inter-sample gap. They do not extrapolate unobserved
time into uptime. A partial day or zero-observation day remains explicit.
Reports retain 90 days of observations. Every independent workflow run has a
GitHub run summary; a separate 14:00 UTC weekday schedule provides a morning
report even when five-minute runs are delayed.

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oraclebot_ops.py status --home /Users/mitch/.local/state/oraclebot-operations
```

A fresh monitor status does not replace the component `ready` and `overall`
fields. `external_heartbeat_accepted` and pending delivery counts expose broken
publisher or notification paths independently.

Installation creates a source-hashed immutable script copy and a private
configuration under the observer state home. Run from the accepted source:

```sh
/Users/mitch/.venvs/soltui/bin/python /Users/mitch/dev/solmargintrader/scripts/oraclebot_ops.py install --home /Users/mitch/.local/state/oraclebot-operations --solbot /Users/mitch/.local/bin/solbot --gh /opt/homebrew/bin/gh --alertlane-env '/Users/mitch/Library/Application Support/Alertlane/service.env' --alertlane-url https://m5.tail0781b8.ts.net:8443 --pipeline-python /Users/mitch/.venvs/oraclebot-pipeline-0.4.8/bin/python --pipeline-home /Users/mitch/.local/share/solmargintrader/ecosystem-operational-20261112
```

The installer refuses an existing differing configuration or LaunchAgent. Review
and back up the exact owned definition before a future explicit migration. To
stop just the observer, boot out `gui/501/com.mitchhudson.oraclebot-operations`
and preserve its state. That does not stop the suite. Delete only its matching
LaunchAgent after confirming unload if uninstalling permanently.

## Hosted website boundary

`https://oraclebot.io/api/health` reports hosted storage, engine configuration,
billing and live execution separately. The initial hosted engine is unconfigured;
restoring the local suite does not connect it. Connecting the hosted research
adapter is a separate deployment from the local control room and requires an
HTTPS read-only engine with a server-side bearer credential. Never tunnel the
owner's control room, account sessions or signing services to make that flag true.

## Checks

```sh
python3 -m unittest discover -s scripts -p test_oraclebot_ops.py -v
ruff check scripts/oraclebot_ops.py scripts/oraclebot_watchdog.py scripts/test_oraclebot_ops.py
```

Tests exercise persisted transitions, authentication and retry against a real
loopback HTTP fixture, stale and malformed heartbeat refusal, report limits and
owned-issue isolation. Installed launchd and actual GitHub workflow acceptance
remain separate evidence.
