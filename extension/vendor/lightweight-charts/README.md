# Vendored: TradingView Lightweight Charts 5.2.1

The extension's one runtime library. The owner chose it on 2026-11-07 (Stele KNOW-859) over
TradingView Advanced Charts, whose licence covers public, attributed websites only
(`docs/TRADINGVIEW-REFERENCE.md`, "Licensing and what stays out of git").

| Field | Value |
| --- | --- |
| Package | `lightweight-charts` 5.2.1 (npm, published 2026-08-12) |
| Licence | Apache-2.0 (`LICENSE`); attribution notice in `NOTICE` |
| Source tarball | https://registry.npmjs.org/lightweight-charts/-/lightweight-charts-5.2.1.tgz |
| Tarball integrity (npm) | `sha512-IVwoK1RLFiLPubaKIjNbtjWLnpPMqiABSrTay6whmNa8L1+19292VtHJ+BWyPUuLCwF0tcQlhEWd1CLB2a1nsQ==` (verified on download) |
| File | `dist/lightweight-charts.standalone.production.mjs` (standalone ESM; bundles its one dependency, `fancy-canvas`) |
| File sha256 | `1bb1ee79f9d4dd17261b53d930f7a8995748276f80e7ba0e24412b5068062f5f` (pinned by `test/charts.test.js`) |
| NOTICE source | https://raw.githubusercontent.com/tradingview/lightweight-charts/v5.2.1/NOTICE |

## Rules

- **Local only.** MV3 forbids remotely hosted code. Never load the library from a CDN.
- **Unmodified.** Do not edit the file. Apache-2.0 requires modified files to carry change notices,
  and the sha256 test fails on any changed byte.
- **Attribution stays on.** The licence asks for the NOTICE text and a link to
  https://www.tradingview.com/ where users see the chart; `layout.attributionLogo: true` (set in
  `src/ui/charts.js`) supplies the link on the chart.
- **Lazy import.** Only `src/ui/charts.js` imports it, on first draw. The service worker, the CLI
  and node tests never load it.

## Updating

1. Download the new tarball and check its `dist.integrity` against
   `https://registry.npmjs.org/lightweight-charts/<version>`.
2. Copy `dist/lightweight-charts.standalone.production.mjs`, `LICENSE`, and the tag's `NOTICE`.
3. Update this table and the sha256 in `test/charts.test.js` in the same commit.
4. Run `npm test` and `npm run e2e`.
