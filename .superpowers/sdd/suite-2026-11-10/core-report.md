# Availability core implementation receipt

Version: 1.0.1
Delta: Bind all stop receipts to the prior verified generation and report null
retention when owned component release was unconfirmed.

The request is recorded in the repository's prompts.md and continuation state is
owned by the root agent in memory.md. This child owns only the three new core
modules, their three focused test files, and this report.

## Delivered contract

`botmanager.suite.operation(action, home=None, ecosystem_home=None)` accepts
status, start, run, stop, restart, install, and uninstall. Status reads observed
owners and includes the actual user-service registration receipt. Run holds one
private suite lease and runs the existing Supervisor in process. Start serializes
launches and requires the existing stable, non-editable executable gate. No new
bot intent, recorder, research producer, optimizer, signing, or order path is
created. Existing Supervisor generations, failure guards, and desired intent
remain authoritative.

`botmanager.machine_health.homes/check` honor explicit roots, SOLBOT_HOME,
SOLBOT_ECOSYSTEM_HOME, and the private persisted per-home binding. Check does not
create roots or invoke status dumps. Schema 1 contains observed_at, overall,
ready, fixed components suite/manager/control_room/market_data, and actual ui_url.
Only suite/manager/control_room determine ready. Optional SOL reference freshness
is a separate, bounded read-only SQLite observation. Unknown ages are omitted
from Prometheus and readiness is null where no measurement exists. Availability
does not certify market data or authorize orders.

`botmanager.suite.alerts(home=None, after=0, limit=100)` reads a private journal
with monotonic sequence cursors, a 256-event cap, and explicit history truncation.
The daemon emits failures, five-minute failure reminders, and immediate recovery
events to both the durable journal and sanitized stderr. Initial absent optional
market data produces no invented recorder failure. Disappearance after a known
available archive does alert. Journal failure makes suite readiness false.

UI monitoring retains only actual callback Popen handles. It never signals an
adopted PID. Failed owned children can restart with bounded backoff. Stop reaps
owned children and reports whether an independent UI remains. Transition queues
retain fast failure/recovery pairs even when repair completes between publishes.
An unclean prior suite generation produces a durable suite failure/recovery pair
when the next owner starts. Supervisor.close runs before optional UI teardown to
preserve the existing reap-before-journal shutdown guard.

The service backend writes fixed argv and fixed homes. macOS uses a per-user
LaunchAgent with RunAtLoad/KeepAlive and bounded restart delay. It begins at user
login, not before FileVault unlock. Linux uses a user systemd unit with explicit
enablement checks and bounded restart delay; persistence beyond logout requires
the documented user-manager/linger setup. Native Windows service mutation
returns an explicit unsupported capability and points to WSL2. Linux behavior is
fixture-tested here, not claimed as an installed native Linux acceptance run.

## Completed verification

Command, executed from botmanager with INDEX_NO_AUTO=1 and the worktree's source
PYTHONPATH:

```
/Users/mitch/.venvs/solbot-0.6.0/bin/python -m unittest tests.test_suite tests.test_suite_service tests.test_machine_health -v
```

Final result: 34 tests passed, exit 0. These include actual manager IPC; concurrent
start spawning only one real suite; actual manager-process SIGKILL and restart;
actual owned subprocess failure/restart/reap; adopted-PID noninterference; fast UI
failure/recovery persistence; unclean suite-generation alerting; alert cooldown,
pagination and rotation; noncreating reads; clock nulls; scope-bound UI probes;
macOS/Linux service-manager fixtures, failure acknowledgements, definition
identity refusals, source-install refusal, and native Windows refusal.

Ruff check and Ruff format of all six owned Python files passed, exit 0.

## Production installation boundary

This child did not install a service, signal a live process, replace existing
environments, or mutate production data. Root must install the verified regular
manager/ecosystem wheels, explicitly release the old default-home manager job,
and reconcile the old UI version before `solbot stack install`. The installer
refuses to take over an independent manager or mismatched service definition.
After installation, root must verify actual registration, matching runtime
identity, reboot/login policy, machine health and durable fault/recovery alerts.

The Linux service status registered field currently denotes a loaded, active or
activating job rather than mere on-disk unit presence; enabled is checked
separately using systemctl is-enabled. No native Linux boot test was performed.
