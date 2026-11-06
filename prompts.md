# Prompt history

Version: 3
Delta: added the DOC-754 workstream M request (liquidity safety features).

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
