# solmargintrader

Grid trading on Jupiter (Solana) with hard risk rails and P&L tracking, exposed through three
interchangeable surfaces: a Chrome MV3 extension, a CLI, and a local HTTP API.

**Dry-run by default.** Nothing places an order until you change the mode and type a confirmation.

> Educational tool, not financial advice. Grid trading is short volatility: it earns in a range and
> loses in a trend. Any leveraged position can be liquidated. Trade only capital you can lose.

## Layout

| Path | What it is |
| --- | --- |
| `extension/` | The whole product: engine, venues, surfaces, tests. See [extension/README.md](extension/README.md). |
| `jup.ag/` | A rendered-HTML dump of jup.ag, kept only as reference material. **Not** Jupiter's source — see below. |
| `docs/` | Architecture, testing, API/CLI reference, security model, operations runbook. |

## Quick start

```bash
cd extension
npm test                                        # 96 tests, no dependencies to install
node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # end-to-end tick loop
node tools/cli.js                               # every available command
```

Load the extension: `chrome://extensions` → Developer mode → **Load unpacked** → select
`extension/`. It loads disarmed, in dry-run.

## Three surfaces, one registry

Every action lives in `extension/src/core/commands.js`. The extension's message handler, the CLI, and
the HTTP API are thin adapters over that registry, and a parity test fails the build if any surface
falls behind. That means anything you can do in the extension UI you can also script:

```bash
cd extension
node tools/cli.js setConfig --lower 60 --upper 90 --rungs 7 --notionalPerRungUsd 12
node tools/cli.js levels
node tools/cli.js plan --price 75
node tools/cli.js arm
node tools/cli.js tick --count 3
node tools/cli.js pnl --json
```

```bash
node tools/api-server.js --port 8787          # prints a bearer token
curl -s -H "Authorization: Bearer $SMT_API_TOKEN" http://127.0.0.1:8787/v1/commands
```

Full reference: [docs/API.md](docs/API.md).

## Two findings that shaped this repo

**The HTML dump is not Jupiter's code.** `jup.ag/` contains 16 rendered HTML files and zero `.js`
bundles — it references `jup.ag/assets/index-*.js` but never downloaded them. It was still useful:
it identified the intended venue, yielded real token mints, and revealed a bundled `vendor-anchor-*.js`
implying client-side Anchor instruction building.

**Jupiter Perps has no public REST write API.** Jupiter's docs state the Perps API is a work in
progress and point at Anchor IDL parsing, so opening or closing a leveraged position is not
shippable from a service worker today. The executable venue is **Trigger V2**, whose price orders
are exactly the ladder a grid needs. Both sit behind one `VenueAdapter`; Perps drops in when its API
ships.

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — module map, the tick, restart safety, venue seam
- [docs/API.md](docs/API.md) — every command across all three surfaces
- [docs/TESTING.md](docs/TESTING.md) — what is tested, what is not, how to verify
- [docs/SECURITY.md](docs/SECURITY.md) — key custody, API token, threat model
- [docs/OPERATIONS.md](docs/OPERATIONS.md) — dry run to live, kill switch, incident steps
