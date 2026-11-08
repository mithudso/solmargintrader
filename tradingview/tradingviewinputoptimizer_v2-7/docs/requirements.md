# Requirements

## Implemented surface, from static source

The manifest/HTML/source expose browser loading, popup preference/registration controls, input-search dialogs, scanner iterations and pause/stop states, result collection, SQLite/OPFS persistence, report tables, JSON/CSV controls and heatmap controls. These are visible implementation surfaces, not runtime acceptance claims.

## Runtime dependencies

Chrome MV3, matching TradingView pages, supported browser storage/offscreen/worker/WASM APIs and the shipped `lib/` assets. The manifest provides script order and isolation/CSP declarations. No first-party Node/Python install or package build is required by the supplied bundle metadata.

## Documentation/retrieval acceptance

Preserve upstream bytes and licensing; cite source for behavior; mark unknowns; maintain versioned workflow records. Inventory all nonprivate files, index complete readable text including vendor artifacts, account explicitly for binary and private exclusions, and keep keyword/vector stores outside Git with freshness and query receipts.
