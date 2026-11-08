# Integrations and assumptions

| Integration | Evidence | Unverified assumptions |
| --- | --- | --- |
| Chrome MV3 | `manifest.json`: module worker, popup, content scripts, offscreen permission, CSP/COOP/COEP | Runtime API compatibility and service-worker lifecycle |
| TradingView | Manifest matches and DOM/input/performance symbols in content scripts | DOM selectors, React internals, chart entitlement and backtest UI compatibility |
| TradingTools | `js/helpers/security.js` domains and background `/api/security/verify-license` POST | Current endpoint reachability, entitlement, HTTP permissions/CORS and server behavior |
| SQLite WASM/OPFS | Worker SQL/OPFS symbols and `lib/@sqlite.org/sqlite-wasm/` | Browser storage availability, database compatibility, recovery and quota |
| Tabulator/Highcharts/three.js | Active report HTML imports | Actual report runtime behavior and redistribution terms |
| jQuery/lodash/Luxon/datetimepicker/UUID | Manifest, HTML and background imports | Compatibility among these pinned bundled versions |

No external service was contacted for application verification. No cloud service, deployment target, wallet integration or order execution is established by this bundle documentation. Vendored metadata is retained as supplied.
