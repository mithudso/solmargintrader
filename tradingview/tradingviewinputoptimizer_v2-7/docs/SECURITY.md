# Security boundary

## Assets and actors

The extension sees chart content and can change chart inputs. It stores preferences and registration identity in Chrome local storage and optimization results in browser storage/SQLite OPFS. The background license POST contains `license_key`, `email` and `machine_code`. Never put real values in documentation, query examples, Git or exported verification receipts.

The manifest requests tabs, activeTab, storage, scripting, unlimitedStorage, declarativeNetRequest, declarativeNetRequestFeedback and offscreen. Content scripts run in all matching frames; page-world injection and custom events form an additional trust boundary. Declared permissions are not evidence that every permission is used safely.

## Threats and current controls

| Threat | Source evidence and limits |
| --- | --- |
| Page code spoofing events/data | Injector/custom-event and React-input bridges are visible; sender/origin validation was not audited completely |
| Local data disclosure | Registration and result data cross runtime/worker/storage boundaries; no privacy guarantee inferred from obfuscation |
| Data loss | Removal/import/export/database actions exist; no tested rollback or migration policy established |
| Remote service misuse | Background license request uses HTTPS; server behavior, ownership, retry behavior and current reachability were not tested |
| Code execution/dependency risk | Manifest declares self-only scripts plus wasm-unsafe-eval and isolation headers; vendored versions/licenses require their own review |

## Handling and reporting

Preserve upstream licensing checks and vendor notices. Do not run key-generation helpers or bypass validation during a docs pass. Use the parent repository security-reporting guidance for repository-owned concerns; do not invent an upstream support SLA. Static documentation is not a security certification.
