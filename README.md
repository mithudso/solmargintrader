# solmargintrader

SOL trading research and execution tooling, in four parts:

| Path | What it is | Language |
| --- | --- | --- |
| [`backtester/`](backtester/README.md) | Offline event-driven backtester for spot and Jupiter-Perps-style leveraged strategies, with an honestly modelled borrow fee. **No live-trading capability, by design.** | Python 3.13 |
| [`research/`](research/STRATEGIES.md) | Strategy survey, ranked lists, parameter sweeps and the per-bar rule readout, built on the backtester. | Python |
| [`extension/`](extension/README.md) | Grid trading on Jupiter (Solana) with hard risk rails and P&L tracking — a Chrome MV3 extension plus a CLI and a local HTTP API over one shared command registry. **This is the part that can place real orders.** | JavaScript (ESM, no deps) |
| [`soltui/`](soltui/README.md) | macOS menu-bar app and TUI that surfaces signals and paper positions, supervised by launchd. Read-only over the research side. | Python 3.13 |

> Research and educational tooling, not financial advice. Simulated past performance does not
> predict future results. Grid trading is short volatility: it earns in a range and loses in a trend.
> Leveraged positions can be liquidated. Trade only capital you can lose entirely.

## Quick start

```bash
# Backtester — fetch once, then simulate offline
pip install -r backtester/requirements.txt
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/

# Extension — no install step, no dependencies
cd extension
npm test                                               # 131 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # end-to-end tick loop
node tools/cli.js                                      # every available command
```

Load the extension: `chrome://extensions` → Developer mode → **Load unpacked** → select
`extension/`. It loads **disarmed, in dry-run**.

## Tests

```bash
python3 -m unittest discover -s backtester/tests -t .   # 521 tests
python3 -m unittest discover -s soltui/tests -t .       # 95 tests (~70s)
cd extension && npm test                                # 131 tests
```

Counts are asserted by CI, so a stale number here fails the build rather than
misleading a reader. See [docs/TESTING.md](docs/TESTING.md) for what each suite covers.

## Three surfaces, one registry

Every extension action lives in `extension/src/core/commands.js`. The Chrome message handler, the
CLI and the HTTP API are thin adapters over that registry, and a parity test fails the build if any
surface drifts. So anything you can do in the extension UI, you can script:

```bash
cd extension
node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
node tools/cli.js levels          # rung ladder + gross spread per round trip
node tools/cli.js plan --price 75 # what it WOULD place; places nothing
node tools/cli.js arm
node tools/cli.js tick --count 3
node tools/cli.js pnl --json
```

```bash
node tools/api-server.js --port 8787     # prints a bearer token
curl -s -H "Authorization: Bearer $SMT_API_TOKEN" http://127.0.0.1:8787/v1/commands
```

Full reference: [docs/API.md](docs/API.md).

## Two findings that shaped the extension

**The bundled HTML dump is not Jupiter's code.** `jup.ag/` holds 16 rendered HTML files and zero
`.js` bundles — it references `jup.ag/assets/index-*.js` but never fetched them. It was still
useful: it identified the intended venue, yielded real token mints, and revealed a bundled
`vendor-anchor-*.js` implying client-side Anchor instruction building. It is gitignored (~42 MB).

**Jupiter Perps has no public REST write API.** Jupiter's docs state the Perps API is a work in
progress and point at Anchor IDL parsing, so opening or closing a leveraged position is not
shippable from a service worker today. The executable venue is **Trigger V2**, whose price orders
are exactly the ladder a grid needs. Both sit behind one `VenueAdapter`; Perps drops in when its API
ships.

## Docs

**Start here**

- [docs/onboarding.md](docs/onboarding.md) — a first hour that ends with every component run
- [docs/codebase-overview.md](docs/codebase-overview.md) — the file map, all four components
- [docs/COMPONENTS.md](docs/COMPONENTS.md) — what each module does and depends on

**Working in it**

- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — setup, commands, env vars, troubleshooting
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — prerequisites, install, verify, uninstall
- [docs/SCRIPTS.md](docs/SCRIPTS.md) — every runnable entry point: purpose, options, real output, when *not* to use it
- [docs/TESTING.md](docs/TESTING.md) — what is covered, what is not, how to verify
- [docs/known-issues.md](docs/known-issues.md) — what is already known to be broken

**Design and behaviour**

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — component map, the tick, restart safety, venue seam
- [docs/API.md](docs/API.md) — every command across all three surfaces
- [docs/integrations-and-assumptions.md](docs/integrations-and-assumptions.md) — external services and the assumptions baked in
- [docs/external-calls.md](docs/external-calls.md) — every call that leaves the machine
- [docs/logging.md](docs/logging.md) — what is recorded, and which paths record nothing

**Operating and safety**

- [docs/SECURITY.md](docs/SECURITY.md) — key custody, API token, threat model
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — dry run to live, kill switch, incident steps
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) / [GEMINI.md](GEMINI.md) — rules for agents working in this repo

`docs/high_signal_file_index.json` is the machine-readable form of the overview, generated by
`scripts/build_doc_index.py`. `scripts/check_docs.py` fails the build if either drifts from the
code — including the test counts quoted above.
