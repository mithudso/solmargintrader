# Testing and evidence

## Available tests

No first-party automated test runner, test script or coverage gate is declared in this bundle. `js/classes/test.js` is a browser experiment with a second Scanner; `test.html` references missing relative demo scripts. Vendor tests and vendor package scripts do not prove optimizer behavior. The parent solmargintrader CI tests other components and repository documentation; it does not run this ignored extension.

There is no numeric first-party coverage target or enforced optimizer CI gate to report. Meaningful future tests should cover the scanner state machine, ordered input commits, timeout/cancel paths, database round trips and privacy boundaries. This documentation pass does not add implementation tests.

## Checks for this pass

1. Enumerate every file and record SHA-256 hashes. Confirm documentation/index work leaves upstream source bytes unchanged.
2. Validate active HTML/manifest references; record existing missing references without changing source.
3. Check new Markdown links and per-file index pointers against the supplied local bundle. A parent clone without the ignored bundle cannot resolve source pointers.
4. Verify full text coverage, actual embedding counts/dimensions, no failed chunks, freshness and distinct keyword/semantic queries. Preserve results outside Git.
5. Run the parent documentation/index drift gate for tracked documentation changes. Parent CI success does not prove this optimizer loads or runs.

## Manual acceptance still needed

Use a disposable browser profile and disposable results. Check extension loading, popup preferences, chart input changes, scan pause/resume/stop, deep-backtest dates, report rendering and database import/export. Check failure behavior when the chart or license service is unavailable. These steps were not executed in this pass; no live acceptance receipt exists.
