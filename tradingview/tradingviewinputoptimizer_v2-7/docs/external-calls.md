# External and cross-context call inventory

This is a static inventory of first-party call families. Obfuscated dispatch prevents a verified exhaustive branch/call-site ledger. Do not interpret the rows as full operations compliance.

| Source / call family | Target and data | Logging / tests / retry evidence |
| --- | --- | --- |
| `background.js:1`, `validateLicense`, `fetch` | HTTPS selected TradingTools domain `/api/security/verify-license`; registration key/email/machine identity | Console diagnostics visible; no first-party automated fixture; exact retry policy unverified |
| `background.js:1`, TradingView online check | `https://tradingview.com` HTTP read | Response/error handling visible; no first-party fixture; retry policy unverified |
| `background.js:1`, Chrome runtime/tabs/windows | Tab lookup/focus/reload, message routing, report-tab creation and offscreen setup | No centralized operation registry or tested timeout contract established |
| `off_screen.js:1`, `new Worker`, runtime/postMessage | SQLite worker command/result payloads | Worker/message console output visible; no round-trip test established |
| `sqlite_worker.js:1`, SQLite/OPFS calls | Local schema/row operations, files, import/export/removal | SQL/result diagnostics visible; failure and migration/recovery semantics unverified |
| `js/content/`, `js/classes/scanner.js`, helpers | Runtime messages, chart DOM/React/custom events, result readout and input mutation | Console diagnostics and retries/states visible; completeness/timeout semantics unverified |
| `js/injectors/` | Page-world script insertion and event hooks | Console diagnostics; sender/event trust validation not fully audited |

Vendor code can contain additional transport paths and examples; the retrieval index includes that text but this inventory does not certify it. No license-service, chart or database operation was executed in this pass.

The five-standard mdb-tam operations contract (CLI trigger, centralized error log, remediation map, dashboard card, datastore verification) is not implemented by these docs. Creating it would require runtime changes outside this request.
