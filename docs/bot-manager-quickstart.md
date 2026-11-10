# Solbot: the working commands and what they actually do

Version: 1.0.0
Delta: Initial short walkthrough after executing create/register/start/daemon/status/stop on this machine.

`solbot` is a command-line program. It does not open a menu. Version 0.2.1 prints
help when run without arguments. Ordinary commands print JSON; `ok: true` means
the command succeeded, not that a trading worker is alive.

**What works today:** saved bot drafts with defaults, guarded existing-owner
controls when compatible, and manager-owned grid replay against recorded Coinbase
data. **What is unfinished:** editing a saved bot, new DCA/trend/momentum/arbitrage
workers, real-time Jupiter paper trading, blind optimization, learning and live trading.
The large handoff describes the architecture and roadmap; it is not evidence that
those later features have been delivered.

## The bot already created and run for you

The bot is named `session-demo-grid`, UUID `ca28be71-3b24-4473-874a-8ac97614edb8`.
It lives in the default `/Users/mitch/.config/solbot` home. The demonstration:

1. Created the grid with `range_pct=10`; all other settings used defaults.
2. Registered the actual recorded input described by
   `/Users/mitch/.config/solbot/session-demo-input.json`.
3. Requested start, then launched an owned foreground `solbot daemon`.
4. Observed its worker complete both bars and reach `waiting/reference_input_exhausted`.
5. Requested stop, observed `stopped` and a released worker lock, then closed that owned daemon.

The result was 2/2 bars, zero fills, zero exposure and zero net P&L on 1,000 USD of
virtual capital. Both process locks are released. This proves the workflow ran;
it does not establish a profitable strategy or a real-time trading bot. The input
is a historical Coinbase SOL-USD range from 2026-11-08 08:21–08:23 UTC, with explicit
illustrative costs. No Jupiter order, key, new recorder or persistent service was used.

Inspect the retained bot and results now:

```sh
/Users/mitch/.local/bin/solbot list
/Users/mitch/.local/bin/solbot config session-demo-grid --effective
/Users/mitch/.local/bin/solbot status session-demo-grid --why
/Users/mitch/.local/bin/solbot events session-demo-grid --limit 100
```

The full executed-command receipt is
`/Users/mitch/.config/solbot/session-demo-receipt.json`.

## Run that bot again

In terminal 1:

```sh
/Users/mitch/.local/bin/solbot start session-demo-grid
/Users/mitch/.local/bin/solbot daemon
```

`start` saves the request. `daemon` is the supervisor that actually owns the worker;
it stays in the foreground. A start request alone is not a running bot. This saved
run has already consumed its immutable input, so it will remain observable at EOF;
restarting does not reset its cursor or repeat trades.

In terminal 2, inspect it and stop it:

```sh
/Users/mitch/.local/bin/solbot status session-demo-grid --why
/Users/mitch/.local/bin/solbot stop session-demo-grid
/Users/mitch/.local/bin/solbot status session-demo-grid --why
```

Expected: saved stopped intent, then observed stopped state and worker lock false.
After stopping, press Ctrl-C in terminal 1 to close the foreground supervisor.
Stopping retains simulated lots/exposure; it does not sell positions. No automatic
service was installed. `service install` is an explicit optional later operation.

## Create a different grid with only the values you change

Use a new name. This creates a draft and does not start it:

```sh
/Users/mitch/.local/bin/solbot create grid --name my-grid --set range_pct=25
/Users/mitch/.local/bin/solbot config my-grid --effective
```

Defaults include seven geometric rungs, 1,000 virtual capital, one-minute bars,
paper mode and disarmed state. `config` shows the exact saved values and where
each came from. `--set` is a creation option. There is no edit/update command yet;
creating another named specification is the current way to try different settings.
Never edit the SQLite body or configuration hashes by hand.

To run the new grid against the already prepared demonstration input:

```sh
/Users/mitch/.local/bin/solbot register-input my-grid --descriptor /Users/mitch/.config/solbot/session-demo-input.json
/Users/mitch/.local/bin/solbot start my-grid
/Users/mitch/.local/bin/solbot daemon
```

Inspect and stop `my-grid` from another terminal using the same status/stop commands.
The descriptor's virtual capital must match the draft's saved capital. This
particular recording remains just two historical bars. New inputs require a new
compatible explicit descriptor; the current manager cannot append a live feed to
this run or reset it silently. A separately named bot has its own virtual account.

## What this session actually built

- Milestone 1: defaults and immutable saved specifications; CLI creation/inspection;
  truthful status; owner discovery and guarded legacy start/stop protocols.
- Milestone 2: installed shared simulator package; independent grid workers;
  persistent supervisor, cursor/fills/checkpoints and receipts; crash recovery;
  explicit macOS service lifecycle; bounded recorded input and reference P&L.
- Startup repair: bare invocation now gives usable instructions; the one actual
  demonstration above leaves a bot and evidence you can inspect.

The complete original request is not finished. The next planned milestone adds
other strategy runtimes and shared prospective/Solana data. The approved later
milestones cover blind research, diagnostics, learning, browser integration and
guarded execution. The separately delivered Oracle component is preserved; its
prospective feeds are not connected to the manager's grid worker yet.
See the full operations/source-maintenance handoff at
`/Users/mitch/dev/solmargintrader/docs/bot-manager-handoff.md`, or its remote copy:

https://github.com/mithudso/solmargintrader/blob/master/docs/bot-manager-handoff.md
