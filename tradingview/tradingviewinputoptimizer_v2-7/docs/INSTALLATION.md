# Installation and lifecycle

## Prerequisites

Keep the full local extension bundle and its vendored assets. Use Chrome with extension developer mode and a TradingView page/account appropriate to the intended workflow. Registration/license requirements are implemented by the supplied code and service; this pass neither contacted that service nor tested entitlement.

`manifest.json` declares a minimum Chrome version of 88. That declaration is not proof that every used API works there: the source uses offscreen documents and runtime context queries. No tested browser-version range was established.

## Manual load procedure

Open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the local optimizer directory. Inspect extension errors and service-worker startup before opening a chart or running a scan. This is a documented manual procedure, not an action performed in this documentation task.

## Verify

Check that Chrome identifies the localized Tradingview Input Optimizer at version 2.3.11, that the popup renders, and that the expected chart tab is selected. Verify report/database operations on disposable data before relying on them. No successful runtime loading or optimization is claimed by these docs.

## Upgrade, rollback and removal

Back up desired settings and export database results before replacing the bundle. Keep the old folder for rollback; browser storage/database compatibility across replacements was not tested. Reload only after preserving the old copy. Removing an extension may discard extension storage; exported data recovery must be verified separately. Do not use Clear database as an upgrade step.
