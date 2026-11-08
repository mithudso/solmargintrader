# Development

## Setup

Use the supplied local bundle. There is no root `package.json`, dependency install step or first-party compilation command. The `lib/` package manifests describe vendored upstream development and publication tasks, not this component's workflow. Do not install dependencies merely to read or index the bundle.

Read the parent rules and component `CLAUDE.md`. Work in an isolated checkout when another session owns the shared repository. Preserve the ignored source copy and use exact documentation paths for staging.

## Configuration

`manifest.json` defines browser integration. `popup.html` exposes delay/minimum/maximum, timeout, data/replay delays, retry/refresh controls, warnings, theme and registration fields. `js/content/popup_script.js` uses Chrome local storage. HTML initial values do not establish effective runtime defaults; stored values and script initialization can override them. No first-party CLI/environment configuration interface was identified.

## Validation workflow

Check documentation links and source pointers, compare source hashes before/after the pass, and verify indexed file coverage. See `TESTING.md` and `RETRIEVAL.md`. Browser acceptance requires an explicit manual run and remains separate. Do not substitute the parent trading extension's tests for this optimizer's behavior.

## Troubleshooting

For a missing source file after cloning, restore the original local bundle: parent Git tracks the documentation only. For stale search, run the scoped index freshness check and rebuild explicitly. For chart automation failure, collect the exact selector/event, browser version and visible state before attributing a cause; TradingView DOM and React internals can change.
