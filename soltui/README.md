# soltui — SOL strategy console

A thirteen-tab Textual TUI plus a macOS menu-bar indicator over the backtester.
Structured like `~/dev/net-dns-monitor`: pure, tested logic modules with a thin
wiring shell.

> **No order path.** There is no order path in this package — no keys, no signing,
> no venue client, not even unreachable code. Every figure it shows is a
> historical simulation, a replay of one, or (Liquidity tab only) a figure read
> from the liquidity daemon's state files. See [Safety](#safety).

## Install and run

```bash
cd /Users/mitch.hudson/dev/solmargintrader
uv venv ~/.venvs/soltui -p 3.13
uv pip install -p ~/.venvs/soltui/bin/python -r backtester/requirements.txt -r soltui/requirements.txt
ln -sf "$PWD/soltui/bin/soltui" ~/.local/bin/soltui    # once; ~/.local/bin must be on PATH

soltui          # the thirteen-tab console, from any directory
soltui app      # the macOS menu-bar indicator (needs rumps)
soltui serve    # the console in a browser window
```

### The menu-bar app bundle needs a framework Python

`soltui app` runs the indicator from the console venv. The double-clickable
`SolTUI.app` is different: it is a py2app alias bundle, and py2app's launcher can only
load a **framework build** of Python. uv's standalone CPython (what `~/.venvs/soltui`
uses) is not one, so build the bundle from a separate venv on Homebrew's python@3.13:

```bash
uv venv ~/.venvs/soltui-app -p /opt/homebrew/opt/python@3.13/bin/python3.13
uv pip install -p ~/.venvs/soltui-app/bin/python -r backtester/requirements.txt -r soltui/requirements.txt
~/.venvs/soltui-app/bin/python soltui/soltui-service build
```

The bundle records that framework through the stable `/opt/homebrew/opt` symlink, so
Homebrew patch upgrades do not break it. If the recorded framework disappears (the
python.org 3.13 install it was first built from did), the app dies with "A Python
runtime not could be located". `soltui-service build` now refuses a non-framework
interpreter and fails when the built bundle names no existing runtime;
`soltui-service status` reports the same check.

`soltui` is [`soltui/bin/soltui`](bin/soltui). It finds the repo through the
symlink, changes to the repo root and runs `python -m soltui.<module>` with
`$SOLTUI_PYTHON`, else `~/.venvs/soltui/bin/python`, else `python3`. Without the
launcher, `python3 -m soltui.tui` from the repo root still works.

The TUI needs price data. If a sweep reports "no data", fetch it:

```bash
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
```

## The menu-bar indicator

`status.build_title()` is a pure function, so what the bar shows is tested
without a macOS event loop. What you see, and why:

| State | Title | Why this and not something else |
|---|---|---|
| Idle | `◦ SOL: idle` | |
| Sweeping | `⟳ SOL: backtest 340/630` | While work is in flight, "how much is left" is the live question |
| Finished | `✓ SOL: last backtest +9.4%` | **"last backtest" is load-bearing** |
| Dry run open | `▷ SOL: paper +2.1% (12 fills)` | **"paper" is load-bearing** |
| Failed | `✕ SOL: error — no data` | Failures must be visible, not silent |

**Why every number carries a word.** A bare `+9.4%` in a menu bar reads, at a
glance, as *my money is up 9.4% right now*. There is no live account here. So the
source is always in the string, and a test asserts that exhaustively across every
phase rather than trusting review. If you add a phase that can show a percentage,
that test will fail until you label it.

Long titles clip from the **head**, never the tail, because the figure is at the
end — an earlier version clipped the tail and silently ate the number the
indicator exists to show. Its test is `test_clip_preserves_the_number_not_the_label`.

## The tabs

| Tab | What it does |
|---|---|
| **Settings** | Asset, interval, date range, capital, fees, fill delay, CPCV geometry. Saved to `~/.config/soltui/`. Validation refuses look-ahead (`fill_delay < 0`), a `k >= blocks` split, and any non-dry-run mode. |
| **Strategies** | Every registered strategy on the left, your roster on the right. Add with params (`fast=20 slow=50`). Validation happens **on add** — an unknown name fails with the valid list, bad params fail at the form, not mid-sweep. |
| **Signals** | Read-only reference: each indicator's actual equation as implemented in `backtester/core/indicators.py`, plus what each family is for and *when it fails*. |
| **Backtest** | Runs the roster through CPCV on a worker thread. Shows median path Sharpe, **IQR**, **% paths positive**, median return, trades. Cancellable. |
| **Execute** | Dry-run replay. Step a simulation bar by bar and see the fills a strategy *would* have made. |
| **Queue** | Starts and reads the low-priority background sweep. Start/Stop/Refresh, a live status line, a ranked table and a below-the-floor table. |
| **Liquidity** | Read-only view of the Aero (aero.xyz) liquidity daemon's state files (`$AERO_LP_HOME`, default `~/.aero-lp/`): mode badge (LIVE is red, dry-run is yellow), kill-switch banner ("Kill switch ON — bot paused"), idle vs deployed USD, totals; Positions, Scout (top pools by modelled net APR), Experiments (arms side by side, winner marked) and Recent actions (newest first, basescan tx links) tables. Refresh / Kill / Resume buttons (`F5` refresh, `F8` kill-resume toggle while the tab is open); re-reads every 15 s. |

### The Liquidity tab — a window onto a daemon, not a controller

`liquidity/` (the `aero-lp` daemon) manages the positions and writes
`status.json` (`aero-lp-status/1`) and `scout.json` (`aero-lp-scout/1`); the
contract is `liquidity/STATE_FILES.md`. `soltui/liquidity.py` is the pure reader
and formatter. A missing, corrupt or unknown-schema file shows "no data" and never
raises. If `generated_at` is older than three minutes the summary says the daemon
may be down.

Same labelling rule as the menu bar: P&L and APR columns say `live` or `dry-run`
(whichever the daemon reports; an unknown mode is `reported`, never guessed
`live`), and scout figures say `modelled`, because they are estimates, not results.
`test_every_percentage_column_carries_a_source_word` enforces it.

### The Queue tab — a sweep you interrupt, not one you finish

`python3 -m soltui.bgworker --asset SOL` grinds through parameter space in a
separate process at background QoS (`taskpolicy -b`, nice 19), so it can run
while you use the machine. The TUI only *reads* what it writes — the sweep keeps
going with the console closed. Resume requires a matching proof sidecar for the
settings, date range, CSV bytes and relevant Python source. Legacy or changed evidence
refuses before appending results; it never silently mixes runs or replaces old history.
Use an explicit fresh `--results-path /absolute/path/results.jsonl` for a new CLI run.
The Queue pane reads the default results path; it does not discover custom CLI paths.
Stop sends a nonce-bound request to the current worker's private control socket. It
never signals a PID taken from an old PID file. The worker consumes requests between jobs.

Because it is always interrupted rather than completed, the **order** is the
design, not the extent: every strategy card's own published preset is evaluated
before any variation of one, then near variations (0.75x/1.5x), then far
(0.5x/2x). Presets and the promise ordering come from the cards themselves
(`success_likelihood`, per-horizon presets), never a copy.

Two tables, and the split is the point. Ranking is out-of-sample CPCV median
Sharpe; anything under the 10-trade evidence floor is **listed but never
ranked**, because a Sharpe from three trades sorted descending is a ranking of
luck. The status line reports how many rows are *rankable*, not how many were
evaluated — the second number flatters the sweep.

```bash
python3 -m soltui.bgworker --plan --asset SOL      # what it would run, in order
python3 -m soltui.bgworker --asset SOL --max-tier 0  # presets only
```

**Missing price data is reported before the sweep, not during it.** The queue
interleaves 1h and 1d jobs by promise, so an absent `data/SOL_1h.csv` would
otherwise surface minutes in — with the whole short horizon quietly absent from
the results while the pane still said "running". The tab names each missing
series and the exact `backtester.core.fetch` command, and **Fetch missing data**
runs those commands for you.

That button is the only network action in this package, and it stays the
separate explicit step `CLAUDE.md` requires: it runs `backtester.core.fetch`,
writes a local cache, and does **not** start a sweep as a side effect. A sweep
missing one interval still runs every job at the intervals it does have, and
says so rather than reporting a clean "done". Note the hourly series is refused
by the loader unless `--allow-gaps` is passed (it has disclosed gaps). Even with that
loader flag, the simulation engine refuses irregular intervals rather than guessing
carry cost or annualization. Use a complete cache for simulation. When a fetch leaves
a series missing, the tab points at `~/.config/soltui/bg/fetch.log`.

Inspect it while it runs: `~/.config/soltui/bg/` holds `results.jsonl` (one JSON
object per job), `state.json` (progress) and `worker.log`.

### Read the Backtest tab correctly

Median Sharpe alone is not the answer. A median of `+0.5` with an IQR of `1.4`
straddles zero heavily, and `% paths positive` below ~70% means the sign of the
result depends on which regime you happened to sample. Both columns are shown for
that reason. The measured PBO for this strategy set is 0.43–0.46 against a 0.500
pure-noise control — so treat *ordering* as weakly informative at best, and read
the distribution.

## The command bridge: one registry, four surfaces

Every action in the console is a command in `soltui/commands.py` (`soltui list` prints them all).
The TUI, the CLI, the HTTP API and the Chrome extension's native-messaging host all call
`dispatch(name, params, surface)`, so one call returns one envelope, byte for byte, wherever it came from:

```
{"ok": true,  "command": "roster.list", "result": {...}, "error": null}
{"ok": false, "command": "...", "result": null, "error": {"code": "bad_params|unknown_command|forbidden|failed|timeout", "message": "..."}}
```

```bash
soltui list                                         # every command with its parameters
soltui call roster.list
soltui call roster.add --param name=rsi --json '{"params": {"period": 9}}'
soltui call liquidity.resume --param confirm=true   # see the confirm gate below
soltui api --port 8788                              # http://127.0.0.1:8788/v1/<command>
soltui host-install install                         # register the Chrome native host
```

- **Confirm gate.** `liquidity.resume` deletes the aero-lp `KILL` file, which removes a safety stop on a
  real-money daemon. It refuses with `forbidden` unless `confirm` is the boolean `true`, on every surface;
  the TUI's Resume button asks you to press it twice within 10 seconds. `liquidity.kill` only adds the stop
  and needs no confirm. No command moves funds: soltui has no keys, signer or venue client.
- **API access.** Binds `127.0.0.1` only. Every route except `GET /v1/health` needs
  `Authorization: Bearer <token>`; the token is in `~/Library/Application Support/soltui/api-token`
  (mode 600, created on first run). A request with an `Origin` or `Sec-Fetch-Site` header is refused, since a
  web page can post to localhost. `GET` runs read-only commands only; `POST` takes a JSON object of params.
- **Native host** `com.mitchhudson.soltui` (`soltui/native_host.py`): Chrome's 4-byte little-endian framing,
  ops `ping`, `list`, `call`, `buildHash`. `buildHash` hashes the extension's manifest and `src/` so the
  extension can reload itself when its source changes. A reply over Chrome's 1 MB limit comes back as a
  `failed` envelope that points at the CLI or API. `soltui host-install install|uninstall|status` writes the
  wrapper script (`~/Library/Application Support/soltui/native-host/soltui-native-host`, running
  `~/.venvs/soltui/bin/python -m soltui.native_host`) and a manifest in each installed Chromium browser,
  allowing extension `pnokcppamfghgaimmmghoegjllhonhbh` plus any ids in `SOLTUI_EXTRA_EXTENSION_IDS`.
  Chrome loads host manifests at launch, so restart it after the first install.
- **Call log.** `dispatch` appends one line per call to `~/Library/Logs/soltui/calls.jsonl`:
  `{ts, surface, command, ok, error_code, ms, params_keys}`. Parameter *keys* only, never values; rotated at
  5 MB. The TUI's timer-driven refreshes are not logged, calls anyone asked for are.
- **State.** Mutating commands persist (roster with its params, signal defaults, settings), so a roster built
  through the API is the roster the TUI shows. The dry-run replay (`paper.*`) and the sweep live in the
  running process: use them through the TUI, the API server or the native host, or give `paper.start` a
  `bars` parameter for a one-shot CLI replay.

`soltui/tests/test_bridge_parity.py` walks the registry and proves byte-identical envelopes across the four
surfaces for every command; `test_bridge_buttons.py` fails when a TUI button is not a registry command.

## Safety

`CLAUDE.md` for this repo states: dry-run is the default, the extension installs
disarmed, and *"never change a default so that a fresh install can place an
order."* This package holds to that:

- **No order path exists.** Not stubbed, not disabled — absent. `grep` the package
  for a venue client and you will find none.
- **`config.MODES` contains only `dry-run`.** A config selecting `live` is refused
  by `validate()` with an explanatory error.
- **`armed` cannot be inherited.** Setting it requires an explicit second
  acknowledgement flag, so an old config file cannot silently arm a future build.
  Nothing in this build reads `armed` for anything.
- **The Execute tab is a replay, not a live loop.** Stepping bars and computing
  fills would create a *second* order-execution path alongside
  `backtester/core/engine.py`, outside the coverage of the engine's known-answer
  tests, and the two could diverge into wrong money. Instead `paper.py` runs the
  tested engine once and exposes a cursor over the result.
- `summary()["live_orders_placed"]` is structurally always `0`, and a test asserts
  it so a regression is loud.

Adding live execution later means routing through
`extension/src/core/commands.js` and its risk rails as separate, explicit work —
not extending this package.

## Tests

```bash
python3 -m unittest discover -s soltui/tests -t .        # see docs/DEVELOPMENT.md for the current count
python3 -m unittest discover -s backtester/tests -t .    # 119 tests
```

The TUI tests mount the real app through Textual's `run_test()` headless harness
and click real buttons, so a crash-on-mount is caught rather than shipped. Two
genuine bugs were found this way: a timer that queried a widget during teardown
and took the app down with it, and the title-clipping bug above.

## Layout

```
soltui/
  status.py    pure: AppState, build_title(), build_menu_summary()
  config.py    pure: Settings, validate(), load/save
  roster.py    pure: Roster add/remove, validated against the strategy registry
  paper.py     pure: PaperSession replay cursor over one backtest
  runner.py    worker thread: roster -> CPCV rows, progress for the indicator
  tui.py       Textual app, one tab per pane (presentation only)
  bgqueue.py   background sweep: job list, ordering, file contract, leaderboard
  bgworker.py  the background sweep process itself (python3 -m soltui.bgworker)
  bgcontrol.py spawn/stop the worker; the liveness lock
  liquidity.py pure: read/validate/format the liquidity daemon's state files; KILL toggle
  app.py       rumps menu-bar shell (wiring only, lazy rumps import)
  commands.py  the command registry: dispatch, envelope, confirm gate, call log (every action lives here)
  reference.py static Research/Signals tab content, served by research.get / signals.reference
  cli.py       `soltui call` / `soltui list`
  api.py       `soltui api`: loopback HTTP, bearer token, browser requests refused
  native_host.py, native_host_install.py   Chrome native-messaging host and its installer
```

Anything that makes a decision lives in the pure modules. `tui.py` and `app.py` are
deliberately dumb, which is what lets the logic be tested without a terminal or a
macOS event loop.
