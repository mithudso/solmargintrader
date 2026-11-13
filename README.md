# solmargintrader

## oraclebot.io website

The public research and wallet-account workspace is hosted at https://oraclebot.io
See [the website guide](website/README.md) for account storage, Stripe seven-day
trials, the research archive and the separate Python analysis adapter. Billing,
analysis availability and live venue execution have independent readiness gates.
Bot configurations in this release are inactive paper definitions.

Trading research, execution tooling and the hosted workspace, in eleven parts:

| Path | What it is | Language |
| --- | --- | --- |
| [`website/`](website/README.md) | Cloudflare wallet accounts, optional Stripe billing, public research and a separate read-only canonical analysis adapter. Trading definitions remain inactive. | JavaScript ESM/Python |
| [`ecosystem/`](ecosystem/README.md) | Paper bootstrap, shared Oracle/F5 coordination, external bot registrations and a local paper control room with delegated operations. | Python 3.13 |
| [`oracle/`](oracle/README.md) | Source-labelled market observations, prospective strategy votes, durable history, read-only MCP subscriptions and explicitly enabled TradingView workers for Coinbase spot or Jupiter ZEC Beta perpetuals. | Python 3.13 |
| [`botmanager/`](botmanager/README.md) | Standalone `solbot` CLI: pinned bot specifications, legacy discovery/control and an explicit multi-instance reference-paper supervisor for Grid, DCA, Trend and Momentum. Reuses the shared Oracle archive; Jupiter quote evidence stays separate. | Python 3.13 |
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

## Automated paper ecosystem

The operational control room adds server buttons, configuration launches, stage progress, per-coin paper P&L, selected Oracle voters, a source-linked wiki and an isolated manual Jupiter swap page. Oracle also records all strategy directions, the full-catalog aggregate and prior-bar shape for each evaluated tick, then overlays those calls on its observed-price chart. See [the operating guide](docs/ECOSYSTEM-CONTROL-ROOM.md).

`python3 scripts/bootstrap_ecosystem.py start` installs the headless components,
checks health, acquires the configured universe, runs the complete strategy matrix
and hands usable results to registered forward trials with per-coin Oracle
forecasts. See [setup and recovery](docs/ECOSYSTEM-BOOTSTRAP.md) for source,
coverage and lifecycle limits.

## ZEC ensemble study

The ZEC study tests 1m and 1h hypotheses using checksum-verified Binance ZEC/USDT
history, a shared causal ensemble policy, validation-only selection and ten
independent paper forward accounts. The selected top configuration is published
on the Oracle page. See [measured results and reproduction](docs/ZEC-ENSEMBLE-STUDY.md)
and [forward owner and recovery](docs/ZEC-ENSEMBLES-FORWARD.md).

## Shape-aware spot study

The [Coinbase spot shape study](research/SHAPE-AWARE-SPOT.md) tags completed hourly,
six-hour and daily candles, compares individual strategies and mixtures, and tests
train-only shape routing. Its zero-commission scenarios retain spread/slippage;
Coinbase One does not waive Advanced Trade fees.

The [ZEC cycle validation](research/ZEC-CYCLE-VALIDATION.md) tests apparent regular
peak/dip spacing against no-clock simulations and frozen future forecasts. A
short local rhythm was visible, but the declared tests did not validate a stable clock.

The [Coinbase top50 study](research/COINBASE50-GRID-CYCLES.md) compares wavelength
consistency, hour-of-day seasonality, grid-coin selection, chart geometry and
persistent homology. Its factorial spot backtests count idle cash, residual
inventory and execution costs, and keep incomplete-history exclusions visible.

## Combined research and prospective plan

The [trial meta-analysis](research/META-ANALYSIS.md) consolidates the retained
strategy families, tests actual API fees and passive attribution, and compares
an independent recommendation. The [frozen paper cohort](docs/META-FORWARD.md)
runs ten separate accounts with durable future-only decisions. The tiny
authenticated live round trip validates execution plumbing; prospective profit
remains unqualified.

## News publication and price study

The [coin-news event study](research/NEWS-EVENT-STUDY.md) follows 61 reviewed
publication events across six coins, with prepublication moves, market controls
and delayed-observation checks. Its minute-bar proxies and selected historical
sample do not establish a causal effect or a calibrated trading forecast.

## Managed bot suite

The current coordinated source candidate is manager 0.7.3, research-runtime 0.4.1
and ecosystem 0.4.6, with backtester 0.2.1, Oracle 0.2.4, optional executor 0.2.1
and extension source 0.6.7. Archived liquidity source is 0.1.1 and remains disabled. It retains paper/disarmed defaults and separates source
checks from installed acceptance and final delivery. Run `solbot --help` for the ordered
walkthrough, `solbot ui open` for the verified control room, and `solbot health-check`
for collector measurements. The [managed suite guide](docs/bot-manager-managed-suite.md)
covers persistent startup, component alerts, Chrome recovery and platform setup.
Research operations and evidence limits are in [the 0.6 guide](docs/bot-manager-0.6-operations.md); the
[handoff](docs/bot-manager-handoff.md) preserves the earlier M4 0.5.0 release history.

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
npm test                                               # 483 tests
node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # end-to-end tick loop
node tools/cli.js                                      # every available command
```

Load the extension: `chrome://extensions` → Developer mode → **Load unpacked** → select
`extension/`. It loads **disarmed, in dry-run**.

## Tests

```bash
python3 -m unittest discover -s backtester/tests -t .   # 1120 tests
python3 -m unittest discover -s soltui/tests -t .       # 1564 tests (TUI dependencies required)
python3 -m unittest discover -s mongo/tests -t .        # 57 tests
cd extension && npm test                                # 483 tests
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

**The extension's Perps adapter remains read-only.** It does not implement
leveraged orders. Its separate live-capable adapter targets **Trigger V2** price
orders, whose bundled signing path remains blocked pending an independent
transaction-intent verifier. Jupiter's **GUM Beta** markets expose a distinct
order Action API; the optional Oracle TradingView worker implements ZEC execution
through that API. That implementation does not make the extension adapter live or
verify arbitrary deposit transactions. See [the separate GUM account and signing
boundary](docs/JUPITER-ZEC-WEBHOOK.md).

## Project wiki

The existing [control-room wiki](docs/ECOSYSTEM-WIKI.md) is the maintained project
navigation. It links verified commands, reference guides, scripts and strategy
material to their authoritative sources. Open the control room with `solbot ui open`
and select its Wiki view; `solbot ui status` only discovers a verified current URL.
The wiki guide also works from a source checkout without starting any service.

## Docs

**Start here**

- [docs/onboarding.md](docs/onboarding.md) — an offline-first entry path and optional component setup
- [docs/codebase-overview.md](docs/codebase-overview.md) — the file map, all ten components
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
