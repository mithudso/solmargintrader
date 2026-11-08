# Optimizer component guidance

Read the parent `../../CLAUDE.md` and `../../AGENTS.md` first. This component is distinct from the order-placing extension under `../../extension/`.

## Repository shape

`manifest.json` wires the MV3 worker, popup and content scripts. `background.js` routes messages and license requests. `off_screen.js` bridges the SQLite worker. `js/classes/` contains scanner/dialog/queue classes; `js/content/` contains chart, popup and report controllers; `js/helpers/` and `js/injectors/` handle inputs and page-world events. `lib/` is bundled third-party code. See `docs/COMPONENTS.md`.

## Workflow records

Save each user request verbatim in `prompts.md` before implementation. Keep `memory.md` current with scope, evidence, verification, delivery and remaining steps. Increment the record version and delta on each update. Workflow record versions are separate from `manifest.json`'s extension version.

## Commands and verification

There is no first-party package manifest, build command or automated test runner in this bundle. Do not run a vendor package's build, prepare, deploy or test script as an extension command. Static inspection and retrieval verification are described in `docs/TESTING.md` and `docs/RETRIEVAL.md`. Manual browser acceptance is separate and was not performed by this pass.

## Editing boundaries

- Preserve the upstream bundle and vendor notices unless the user requests implementation changes.
- Do not change license checks or collect registration values into docs or index examples.
- Browser loading can alter chart inputs, local storage and local databases. Reading documentation does not authorize an optimization run or database deletion.
- Keep all script ordering and browser context boundaries explicit; content-script globals are not ES module imports.
- The parent ignores `tradingview/`. Stage only named task-owned documentation paths, never the whole upstream tree.
- Keep derived keyword/vector stores outside Git. Query freshness before treating retrieval results as current.
- Do not start index watchers or unrelated inference jobs for a documentation task. Explicit index generation is a separate authorized step.

## Retrieval routing

External dossier: `/Users/mitch/.global-ai-hub/skills.llms/mithudso-solmargintrader-tvio.repo/llms.txt`.
Scoped keyword/vector index: `/Users/mitch/.global-ai-hub/indexes/tradingviewinputoptimizer_v2-7/`.
Read `docs/RETRIEVAL.md` for precise commands and exclusions. The parent tracked-file index does not cover this ignored upstream bundle.
