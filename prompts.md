# Prompt history

Version: 9
Delta: added the owner's report that the extension looked unchanged after reload (version still 0.1.0).

Delta: added the leverage-tier and reliable-trigger request.

## v1 - 2026-11-06

```text
Run the repo-bootstrapper skill on this repo. And the deep code optimizer.
```

Target: /Users/mitch/dev/solmargintrader.
Skills: repo-bootstrapper 5.4.1; code-deep-optimizer 1.16.0.

## v3 - 2026-11-06 (delegated prompt, workstream M of Stele EPIC-764; owner request: "Implement all of the recommendations.")

```
WORKSTREAM M: aero-liquidity safety features (DOC-754 product feature). This code MOVES REAL MONEY. In this workstream you never send a transaction, never sign, never restart or reload the live daemon (LaunchAgent `com.mithudso.aero-lp`), and never change `~/.aero-lp/config.toml` caps or `min_net_apr`.
Build: (1) Exit to safe, separate from halt/kill: removes liquidity from managed LP positions, collects fees, returns assets to the wallet; optional configurable stable conversion, off by default; goes through caps, fail-closed price checks and eth_simulateV1; dry-run default printing the exact plan; CLI entry; mock tests only. (2) Dry-run soak gate: live signing refused until the configuration ran in dry-run for a configurable minimum (default about 24h) with a persisted soak record; one-time documented, visible grandfather entry for the current live configuration; strategy/cap change resets the soak. (3) Research-gate block: live refused when the latest gate result failed or is missing for the active strategy; owner override only through an explicit logged config flag covered by a test. (4) Update docs, run the full suite (.venv/bin/pytest -q, Ruff), ship: PR, CI green, merge, fast-forward the live checkout if clean; do NOT restart the daemon; report that the running daemon picks up the code on its next natural restart and whether the grandfather record keeps it live.
```

## v4 - 2026-11-06

```text
Implement all of the recommendations.
```

Target: /Users/mitch/dev/solmargintrader. Scope of this record: the real-browser end-to-end test for the extension (DOC-754 workstream L); other recommendations are separate workstreams.

## v5 - 2026-11-07

```text
When trying to run the soltui.app I get this error: [Image #1]
```

The attached screenshot shows the macOS dialog: "SolTUI has encountered a fatal error, and will now terminate. A Python runtime not could be located. You may need to install a framework build of Python, or edit the PyRuntimeLocations array in this application's Info.plist file."

## v6 - 2026-11-07

```text
In the soltui when I click on "run untested sweep" I get this error: [Image #2]
```

The attached screenshot shows the Backtest tab status: "error: Traceback (most recent call last): File "/Users/mitch/dev/solmargintrader/research/sweep_untested.py", line 18, in <module> from research.sweep import HORIZONS, load_horizon, walk_forward, Row, fmt_table".

## v7 - 2026-11-07

```text
Make everything available in the tui also available via the extension, and using the same mechanisms and calls, which will require a helper script. The extension has ID: pnokcppamfghgaimmmghoegjllhonhbh make it auto reload on update. All calls should be available via the extension, TUI, CLI, and API with the same output response, testing, verification, logging, and access.
```

Workstream P (Python side) of the soltui command bridge, and workstream X (the extension side: soltuiCommands/soltuiCall, transports, `nativeMessaging`, dashboard panel, auto-reload, tests, e2e); workstream X builds the extension side against the same contract.

## v8 - 2026-11-07

```text
For all of the top 5, pre-populate that strategy as a clickable option in the analyze, live runs, and execute tabs. Make it so I can add my wallet  address and private key and it will find all of my coins and contracts, and then add the ability to swap between coins and chains using the best pricing, and ultimately I want a "run this strategy live" button on the top 5 page that will make actual real money transactions using the signals and strategy that bacvktested well. Also on all the pages that show results add a net % growth or decline but also create a dedicated profit and loss page which does a detailed and in depth analysis of profit and loss over a variable time..
```

Scope of this session: the read-only part only (presets, net %, the P&L tab, read-only wallet discovery). Swaps, transaction signing and the live-run button are a later, separately gated workstream; no private-key field was added.

Add strategies for low, medium, and high margin trading, I want to backtest high margin perp trades. And I want to compile a list of very reliable signals, what I mean is not that I think that signal will work all the time with no context, but look for signals that are correct a vast majority of the time and to what degree. The idea being if we have what amount to triggers then we can wait for the reliable trigger to happen, place an order in the direction it is likely to go, and exit before the trigger context expires. For instance I could imagine something like "every time macd crosses while balance is strongly negative and there is a down sloped moving average the next 5 bars are always down"  (I'm making that up), or "When volume spikes to 10x normal, the next several bars will be negative followed by a sharp rise." things like that can be validated and backtested and used when they occur.
```

Delivered in two PRs: (1) leverage tiers, (2) the reliable-trigger miner.

## v9 - 2026-11-07

```text
The solmargintrader has not changed at all, the version number is the same, I loaded the extension from /Users/mitch/dev/solmargintrader/extension
```
