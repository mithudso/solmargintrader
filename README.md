# solmargintrader

SOL trading research and execution tooling, in seven parts:

| Path | What it is | Language |
| --- | --- | --- |
| [`backtester/`](backtester/README.md) | Offline event-driven backtester for spot and Jupiter-Perps-style leveraged strategies, with an honestly modelled borrow fee. **No live-trading capability, by design.** | Python 3.13 |
| [`research/`](research/STRATEGIES.md) | Strategy survey, ranked lists, parameter sweeps and the per-bar rule readout, built on the backtester. | Python |
| [`extension/`](extension/README.md) | Holdings, P&L, pool discovery, backtests and strategy changes, swap quotes and alerts for Base and Solana, plus an experimental grid on Jupiter (Solana) with hard risk rails — a Chrome MV3 extension plus a CLI and a local HTTP API over one shared command registry. **The grid is the part that can place real orders.** | JavaScript (ESM, no deps) |
| [`soltui/`](soltui/README.md) | macOS menu-bar app and TUI for signals, paper positions and research, supervised by launchd. Manual Coinbase spot orders use a separately armed path. | Python 3.13 |
| [`mongo/`](mongo/README.md) | Local MongoDB copy of everything measured — bars, strategies, readouts, backtests, CPCV results — plus a runnable query reference. Derived; the files stay the source of truth. | Python 3.13 + pymongo |
| [`executor/`](executor/README.md) | **Guarded live swaps.** Jupiter spot swaps on Solana behind a semantic transaction verifier, hard rails, a research gate, a dry-run soak and an append-only journal. CLI and loopback API share one JSON envelope. Dry-run by default. | Python 3.13 (own venv) |
| [`liquidity/`](liquidity/README.md) | **Archived on 2026-11-08.** Aero Slipstream LP manager and pool scout on Base, retained for reference. The service stays disabled with its kill switch set. | Python 3.13 + web3 (own venv) |

> Research and educational tooling, not financial advice. Simulated past performance does not
> predict future results. Grid trading is short volatility: it earns in a range and loses in a trend.
> Leveraged positions can be liquidated. Trade only capital you can lose entirely.

## Quick start

The dated research tables preserve earlier experiments. The 2026-11-06 audit changes
simulation accounting and metrics; rerun experiments before treating stored rankings as
current-engine results. Archive-number checks verify transcription, not a fresh experiment.

Trigger live signing also requires an independent transaction-intent verifier that the
bundled signer does not yet provide. Dry-run remains the verified execution path.

```bash
# Backtester — fetch once, then simulate offline
pip install -r backtester/requirements.txt
python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2021-01-01
python3 -m backtester.cli --asset SOL --strategy all --split 0.7 --out results/

# Extension — no install step, no dependencies
cd extension
npm test                                               # 408 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # end-to-end tick loop
node tools/cli.js                                      # every available command
```

Load the extension: `chrome://extensions` → Developer mode → **Load unpacked** → select
`extension/`. It loads **disarmed, in dry-run**.

## Tests

```bash
python3 -m unittest discover -s backtester/tests -t .   # 941 tests
python3 -m unittest discover -s soltui/tests -t .       # 1384 tests (~840s, optional)
python3 -m unittest discover -s mongo/tests -t .        # 46 tests
cd extension && npm test                                # 408 tests
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
- [docs/codebase-overview.md](docs/codebase-overview.md) — the file map, all seven components
- [docs/COMPONENTS.md](docs/COMPONENTS.md) — what each module does and depends on

**Working in it**

- [docs/repository-review-2026-11-08.md](docs/repository-review-2026-11-08.md) — architecture review, executor integrity repairs and remaining limits
- [CONTRIBUTING.md](CONTRIBUTING.md) — focused changes, verification and workflow records
- [docs/requirements.md](docs/requirements.md) — implemented requirements and runtime boundaries
- [docs/MCP.md](docs/MCP.md) — connector boundaries and offline retrieval
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — setup, commands, env vars, troubleshooting
- [mongo/README.md](mongo/README.md) — the local research store and its query reference
- [docs/INSTALLATION.md](docs/INSTALLATION.md) — prerequisites, install, verify, uninstall
- [docs/SCRIPTS.md](docs/SCRIPTS.md) — every runnable entry point: purpose, options, real output, when *not* to use it
- [docs/TESTING.md](docs/TESTING.md) — what is covered, what is not, how to verify
- [docs/known-issues.md](docs/known-issues.md) — what is already known to be broken

**Design and behaviour**

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — component map, the tick, restart safety, venue seam
- [docs/API.md](docs/API.md) — every command across all three surfaces
- [docs/integrations-and-assumptions.md](docs/integrations-and-assumptions.md) — external services and the assumptions baked in
- [docs/external-calls.md](docs/external-calls.md) — every call that leaves the machine
- [docs/TRADINGVIEW-CARD-COVERAGE.md](docs/TRADINGVIEW-CARD-COVERAGE.md) — source inventory, existence matches and missing indicator/strategy cards
- [docs/TRADINGVIEW-REFERENCE.md](docs/TRADINGVIEW-REFERENCE.md) — TradingView charting docs distilled: indicator parity, PineJS, datafeed, drawings, Broker API, licensing
- [docs/caching-and-optimization.md](docs/caching-and-optimization.md) — cache ownership and invalidation
- [docs/logging.md](docs/logging.md) — what is recorded, and which paths record nothing

**Operating and safety**

- [docs/SECURITY.md](docs/SECURITY.md) — key custody, API token, threat model
- [docs/runbooks/incident.md](docs/runbooks/incident.md) — stop execution and reconcile an unknown outcome
- [docs/runbooks/rollback.md](docs/runbooks/rollback.md) — revert code while preserving live-state evidence
- [docs/runbooks/handoff.md](docs/runbooks/handoff.md) — resume from prompt, memory and Git state
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — dry run to live, kill switch, incident steps
- [CLAUDE.md](CLAUDE.md) / [AGENTS.md](AGENTS.md) / [GEMINI.md](GEMINI.md) — rules for agents working in this repo

`docs/high_signal_file_index.json` is the machine-readable form of the overview, generated by
`scripts/build_doc_index.py`. `scripts/check_docs.py` fails the build if either drifts from the
code — including the test counts quoted above.

## Coin suitability skill and Bots ranking

The simulation-only coin-fit tool supports single and bulk screens, fast provisional ranking and a detailed ten-scenario audit. The Bots tab provides ranking, selected-coin audit, reasons, equity and cancellation; the CLI and reusable Codex skill call the same backend. See [coin-fit usage and limits](docs/coin-fit/README.md).
