# Solbot managed availability, UI access and platform setup

Version: 1.0.0
Delta: Initial 0.7 managed-suite operations, complete CLI walkthrough, component telemetry and platform comparison.

The manager 0.7 CLI contains the ordered command reference itself:

```sh
/Users/mitch/.local/bin/solbot --help
```

The walkthrough covers every registered command, all persistent-service actions,
defaults and settings, prospective paper accounts, historical research, learning,
browser receipts, optional executor previews, backup and recovery. It is a set of
stages and conditional branches. A missing archive, certification, authority or
elapsed shadow period remains a reported blocker. Reading help starts no process.
`solbot help` returns the same stages as structured JSON in `data.workflow`.

## Find and open the interface

```sh
/Users/mitch/.local/bin/solbot ui status
/Users/mitch/.local/bin/solbot ui open
```

`ui status` is read-only. Its `data.url` is the current local control-room address
only after the private generation checkpoint, owner lock and HTTP identity agree.
The port is selected by the server and may change after restart. A stopped or
unverified server reports `running:false`, a null URL and a reason.

`ui open` explicitly starts the availability suite when needed and opens the
verified address with the system browser. `ui start` starts availability without
opening a tab. If the browser cannot launch, the result retains the verified URL
and reports `opened:false`; it does not claim that a tab opened.

The extension uses the same control-room discovery and fixed suite-start operation
through the installed native helper. The helper binds the manager and ecosystem
homes during installation. A web page cannot supply a shell command, executable,
arbitrary home or destination URL to the start operation. The existing browser
paper grid keeps its profile identity, control receipts and disarmed defaults.

## Install and control persistent availability

Inspect owners first. An existing independent manager must release its own home
before the suite takes that supervisor role:

```sh
/Users/mitch/.local/bin/solbot stack status
/Users/mitch/.local/bin/solbot service status
/Users/mitch/.local/bin/solbot stack install
/Users/mitch/.local/bin/solbot stack start
/Users/mitch/.local/bin/solbot stack status
/Users/mitch/.local/bin/solbot health-check
```

`stack install` writes and enables the current user's service with fixed installed
executable and homes. It requires a regular package installation. The suite owns
one reference supervisor in its process; it reuses the established worker locks
and desired bot intents. It starts or adopts the verified control room and checks
component readiness repeatedly. It does not create another recorder, optimizer,
research authority, strategy engine or funded account. Existing desired-running
paper accounts can resume under the supervisor; installation does not invent new
bot start requests. Market-data failure raises an availability alert and retains
the source's existing ownership.

The operating-system service manager restarts a crashed suite. The suite observes
and repairs the manager/UI components it owns within bounded retries; a conflicting
or unverifiable owner is a refusal with an alert, never permission to delete locks
or kill a process based only on its PID. Source tests do not establish that an
actual machine reboot has been exercised.

```sh
/Users/mitch/.local/bin/solbot component-alerts --after 0 --limit 100
/Users/mitch/.local/bin/solbot stack restart
/Users/mitch/.local/bin/solbot stack stop
/Users/mitch/.local/bin/solbot stack status
/Users/mitch/.local/bin/solbot stack uninstall
```

`stack stop` deliberately stops availability supervision, so it suppresses
automatic resurrection until an explicit start. Saved bot requests and account
evidence remain. `stack uninstall` removes the suite's service registration.
An adopted independently persistent control room is retained; inspect `ui_retained`
and `ui status`. Do not interpret a stopped suite as proof that every other owner
or the adopted UI has stopped. Stop individual paper accounts and verify their
released ownership before backup or configuration adoption.

For a foreground deployment, use `solbot stack run` in its own terminal with no
installed/running suite for that home. The older `solbot daemon` and
`solbot service install` remain manager-only alternatives. Never combine either
with the suite for the same home. A legacy service migration must record its
installed executable, label, versions, state and backup; uninstall that exact
service using its matching executable, verify its owner release, then install the
suite. The suite refuses the conflict instead of silently migrating unknown owners.

## Machine health and alert collection

```sh
/Users/mitch/.local/bin/solbot health-check
/Users/mitch/.local/bin/solbot metrics
/Users/mitch/.local/bin/solbot component-alerts --after 0 --limit 100
```

`health-check` returns the normal JSON response envelope with a compact
`data` snapshot: schema version, observation time, overall state, readiness,
verified UI URL and four components (`suite`, `manager`, `control_room`,
`market_data`). Each component carries a fixed state/reason, readiness and any
observed heartbeat or source freshness age. Missing ages are omitted; zero means
an observed zero age. `ready:true` requires the three availability components.
Overall state can still be degraded because the separately owned market stream
is missing or stale. Availability is independent of profit, exposure and venue
certification.

A successfully observed degraded/down snapshot is still a successful read with
exit code 0. A collector should evaluate `data.ready`, `data.overall` and component
fields. An invalid configuration or failed operation returns a sanitized error
envelope and nonzero exit code. `metrics` prints Prometheus text on success and
the ordinary JSON error envelope on failure. Neither command starts components.
The local UI exposes `/api/health` (compact snapshot), `/healthz` (HTTP-server
liveness), `/readyz` (critical-component readiness, HTTP 503 when unavailable),
and `/metrics` (Prometheus text). `ui status` supplies the actual origin. The older
`/health` route retains its server identity contract and does not establish
component readiness. The richer `status`/`health BOT` commands retain their
operator and paper-account purposes.

`component-alerts` is the suite's durable bounded component failure/recovery feed.
`alerts BOT` retains the separate attributable bot-health feed. Poll with each
response's exact `next_after` value; row count is not a cursor. The monitor records
state transitions and recovery evidence. A terminal read does not itself send an
email, Slack message or hosted notification. External alerting can evaluate the
compact health and Prometheus gauges without scraping human status text.

## Fixed local homes and source selection

The manager defaults to `/Users/mitch/.config/solbot` on this Mac. The control-room
home defaults to `/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2`.
`SOLBOT_HOME`, `SOLBOT_ECOSYSTEM_HOME` and the global `--ecosystem-home` select
explicit homes. Installed suite/native-helper configuration freezes those paths.
An existing private suite configuration supplies the ecosystem home when no
explicit argument or environment override is given.

The `shared-sol-usd` input alias still refers to the established V1 Oracle archive,
/Users/mitch/.local/share/solmargintrader/ecosystem-paper-v1/oracle/SOL/history.sqlite3
on this Mac. Selecting a different UI home does not relabel that archive. A new
Linux installation needs an actual archive from its chosen existing producer or
an explicit absolute `--archive` path. UI readiness does not establish source
freshness or populated history. Do not create an empty substitute database or
claim that historical capture is prospective evidence.

## macOS, Linux and Windows comparison

| Capability | macOS | Native Linux | Native Windows / WSL2 |
| --- | --- | --- | --- |
| Python runtime | Python 3.13+, regular dedicated environment | Same; Python and venv packages depend on the distribution | Native full stack unsupported; install Python inside WSL2 for the Linux path |
| Manager, reference workers and HTTP UI | Supported Unix implementation; installed acceptance required | Unix locking and same-user sockets supported by source; validate on the actual host | Native imports and ownership model need a port; WSL2 provides Linux semantics |
| Persistent suite | User LaunchAgent, RunAtLoad/KeepAlive | User systemd unit, Restart=always, enabled for default.target | WSL2 systemd user service when enabled; Windows boot/WSL distribution startup is separate |
| After reboot | Starts after this user logs in; FileVault/pre-login startup is outside this user agent | Starts with the user manager at login; linger can keep/start it without an interactive login | WSL itself must start; Linux linger alone does not launch a stopped WSL distribution |
| Production anonymous blind judge | Existing macOS sandbox-exec isolation | Refuses unsupported production isolation; numerical fixtures are not production isolation | WSL2 also lacks the current macOS isolation contract |
| Extension native messaging | Per-browser NativeMessagingHosts manifest and executable helper | Linux XDG/browser manifest paths and executable helper | Windows Chrome requires a Windows native-host registration/bridge into WSL; that bridge is additional, unverified setup |
| Signing/live admission | Existing guards and separate owner authorization; manager remains paper/disarmed | Same logical refusals; platform availability is not execution certification | WSL2 setup does not certify live execution or Windows Chrome integration |

Native Windows cannot currently run the complete suite. Modules depend on Unix
`fcntl` locks, owner-checked Unix-domain sockets, Unix user IDs/permissions and
the macOS production blind-judge sandbox. Modern Windows socket support alone
does not supply these ownership and isolation contracts. A native Windows port
needs implementation and acceptance work rather than a different pip command.

### Fresh Linux environment

Provide Python 3.13+ with venv support, Git, and a functioning systemd user manager.
Use the distribution's supported installation method for Python. For a fresh
reviewed checkout under the following declared location:

```sh
export SOLBOT_REPO="$HOME/dev/solmargintrader"
git clone https://github.com/mithudso/solmargintrader.git "$SOLBOT_REPO"
python3.13 -m venv "$HOME/.venvs/solecosystem-0.4.0"
export SOLBOT_PYTHON="$HOME/.venvs/solecosystem-0.4.0/bin/python"
"$SOLBOT_PYTHON" -m pip install "$SOLBOT_REPO/backtester" "$SOLBOT_REPO/oracle" "$SOLBOT_REPO/botmanager" "$SOLBOT_REPO/soltui" "$SOLBOT_REPO/ecosystem"
export PATH="$HOME/.venvs/solecosystem-0.4.0/bin:$PATH"
export SOLBOT_HOME="$HOME/.config/solbot"
export SOLBOT_ECOSYSTEM_HOME="$HOME/.local/share/solmargintrader/ecosystem-paper-v2"
solbot --help
solbot stack status
solbot stack install
solbot health-check
solbot ui open
```

The install command above installs headless components, not the native macOS app
or optional executor. Start with an unused environment; do not upgrade a running
experiment in place. Without an existing producer/archive, expect unavailable
market data even when the manager/UI are ready. Follow the source-selection stage
in help before starting a paper account. The suite does not acquire a replacement
feed automatically.

The systemd definition is written into the current user's
`$HOME/.config/systemd/user` directory with its home-derived label, reported by
`stack status`. `systemctl --user` must be reachable. For operation without an
interactive login, this explicit host policy is separate:

```sh
loginctl enable-linger "$(id -un)"
```

That command may require host administrator/polkit approval. Linger keeps the user
manager available at boot and after logout; it does not prove network readiness,
available mounted homes, a browser session or market input. Containers, cron-only
sessions and Linux hosts without a user systemd manager can use the foreground
`stack run` under their own reviewed service manager instead of claiming the
automatic installer succeeded.

The Linux native helper installer supports recognized existing browser profile
directories under `$XDG_CONFIG_HOME` or `$HOME/.config`. After loading the reviewed
extension in Chrome, install the helper with the matching regular interpreter:

```sh
"$SOLBOT_PYTHON" -m soltui.native_host_install install --python "$SOLBOT_PYTHON" --repo "$SOLBOT_REPO" --manager-home "$SOLBOT_HOME" --ecosystem-home "$SOLBOT_ECOSYSTEM_HOME"
"$SOLBOT_PYTHON" -m soltui.native_host_install status
```

The default allowlisted extension identity must match the installed extension.
An explicitly reviewed alternate ID uses `--extra-id` and an existing browser
profile directory can be selected with `--dir`. Do not widen the allowlist to
arbitrary web origins. Source/native-message fixtures do not establish that a
particular Linux browser distribution or sandboxed package can launch this helper.

### Windows through WSL2

Install a WSL2 Linux distribution using Microsoft's supported process, enable
systemd in that distribution where needed, and follow the Linux commands above
inside Linux. Keep the repository, virtual environment and SQLite state on the
Linux filesystem so Unix permissions and locking retain their intended meaning.
The loopback UI can be opened from the Windows browser only after verifying the
actual WSL/Windows networking configuration and URL. That access is independent
of extension native messaging.

A Windows Chrome process does not automatically see Linux NativeMessagingHosts
manifests. The current POSIX helper is not a Windows native-host installer.
Using the extension in Windows Chrome therefore requires a separately reviewed
Windows host registration and bounded bridge into WSL. No automatic bridge or
Windows boot task is supplied by this release. A Chrome process running inside
Linux uses the Linux helper path, subject to that host's browser support.

Platform statements above describe implemented contracts and setup requirements.
macOS installation receipts, Linux service-definition fixtures and shell/parser
tests are separate evidence. They do not constitute an executed Linux/Windows
installation, physical reboot or production blind-judge qualification.

Sources for service semantics:

https://github.com/systemd/systemd/blob/main/man/systemd.special.xml

https://github.com/systemd/systemd/blob/main/src/login/loginctl.c

https://learn.microsoft.com/windows/wsl/install

https://learn.microsoft.com/windows/wsl/systemd
