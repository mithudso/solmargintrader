# Components

| Area | Role and interfaces |
| --- | --- |
| `manifest.json`, `_locales/en/messages.json` | Name/version, permissions, browser matches, ordered script wiring, CSP and isolation declarations |
| `background.js` | Tab selection, offscreen setup, runtime message routing, registration/license request |
| `popup.html`, `js/content/popup_script.js` | Theme, delays, retries, refresh behavior, identity and registration fields; Chrome local storage and runtime messages |
| `js/classes/scanner.js` | `Scanner` iteration lifecycle, pause/resume/stop, chart input changes, result capture and database messages |
| `js/classes/dialogs.js` | Dialog/input/optimization/report/link/rule windows |
| `js/classes/queues.js` | `Queue` and `AutoQueue` action scheduling |
| `js/content/tradingview-content-script.js` | UI orchestration, combinations, commit ordering, performance readout and optimizer actions |
| `js/helpers/` | Inputs/popups, numeric/cartesian helpers, strategy priorities, ticker/timeframe clicks, linked-input drawing and licensing helpers |
| `js/injectors/` | Page-world hooks, custom events, React input setting, deep-backtest fields |
| `off_screen.html`, `off_screen.js` | Offscreen document and runtime-to-worker bridge |
| `sqlite_worker.js` | Database creation/rows/schema/query/import/export/removal in SQLite/OPFS |
| `report.html`, `js/content/report_script.js` | Result selection, table/export/import and heatmap controls |
| `css/`, `assets/` | Component styles and icons |
| `lib/` | Bundled third-party JS/CSS/types/maps/WASM; retain vendor package metadata and licenses |
| `js/classes/test.js`, `test.html`, `lib/subworkers/test/` | Experiments/vendor demos; no first-party test-runner declaration |

These are static source roles. Shared globals and obfuscated calls are not a complete typed API. Follow manifest/HTML ordering before changing a dependency.
