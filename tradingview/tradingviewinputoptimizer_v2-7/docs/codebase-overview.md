# File overview

Source bundle paths below are relative to this component; they resolve only where the ignored original bundle exists. This is a curated static map, not a runtime acceptance record. The external dossier inventories every upstream file.

| Path | Role |
| --- | --- |
| `_locales/en/messages.json` | Defines the extension name, short name and purpose used by the manifest. |
| `background.js` | Routes extension messages, creates the offscreen document, selects the chart tab and validates licenses. |
| `css/popup.css` | Styles the extension popup. |
| `css/report.css` | Styles report controls, tables and heatmaps. |
| `css/trading-view.css` | Styles the optimizer UI inserted into TradingView. |
| `js/classes/dialogs.js` | Defines DialogWindow, InputWindow, StartOptimizationWindow, ReportWindow and linked/rule editor classes. |
| `js/classes/queues.js` | Defines Queue and AutoQueue for queued actions. |
| `js/classes/scanner.js` | Scanner coordinates iteration state, strategy input changes, result capture, retries and database messages. |
| `js/classes/test.js` | Contains a separate Scanner and deepBackTest experiment; absent from manifest content scripts. |
| `js/content/popup_script.js` | Loads and stores popup preferences and sends license and database requests. |
| `js/content/report_script.js` | Defines Report and report normalization, result table and visualization behavior. |
| `js/content/tradingview-content-script.js` | Coordinates optimization dialogs, input combinations, TradingView UI interactions and performance capture. |
| `js/globals/globals.js` | Initializes shared content-script state including the search name. |
| `js/helpers/helpers.js` | Defines timing, Cartesian combinations, numeric sanitization and event helpers. |
| `js/helpers/inputs.js` | Finds and changes chart inputs and popup choices, loads/saves settings and handles input metadata. |
| `js/helpers/license.js` | Contains license/product-key and hashing helpers; preserve the upstream licensing implementation. |
| `js/helpers/linked_search.js` | Draws and updates linked-input ropes and SVG clip paths. |
| `js/helpers/manipulators.js` | Defines chart ticker/timeframe selection and save-profile interactions. |
| `js/helpers/security.js` | Sends license-validation requests to the background worker with the selected service domain. |
| `js/helpers/strategy.js` | Orders strategies and timeframes by scan priority. |
| `js/injectors/after.js` | Injects after_inject.js into the page at document_end. |
| `js/injectors/after_inject.js` | Changes page before-unload handling. |
| `js/injectors/before.js` | Injects before_inject.js into the page at document_start. |
| `js/injectors/before_inject.js` | Installs page-side offline and event hooks. |
| `js/injectors/page-script.js` | Handles page-world input events, React input setters and deep-backtest date changes. |
| `manifest.json` | Declares MV3 permissions, script order, page matches, worker, popup, CSP and isolation policies. |
| `off_screen.html` | Loads the module that bridges runtime messages to the database worker. |
| `off_screen.js` | Forwards database requests to sqlite_worker.js and sends its results back to extension contexts. |
| `popup.html` | Defines settings, delay controls, theme, machine identity and registration inputs. |
| `report.html` | Defines result table, export/import controls and heatmap UI with vendored visualization scripts. |
| `sqlite_worker.js` | Implements SQLite database creation, row insertion, filtering, export, import and OPFS operations. |
| `test.html` | References a worker demo whose relative scripts are absent from this bundle. |

Vendor dependencies live under `lib/`; styles/icons under `css/` and `assets/`. Documentation and workflow records describe this pass rather than adding application modules.
