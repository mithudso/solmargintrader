# Task 6 report — browser discovery and delegated controls

Version: 1.1.0
Delta: 1.0.0 to 1.1.0; fix legacy-owner and failed-stop review findings, expand semantic source fencing, and repeat source-browser checks.

Implemented the actual browser-owner path. `browserManagerPoll` and `browserManagerSnapshot` live in the extension command registry. MV3 installation/startup events register the owner; a recreated 30-second Chrome alarm bounds polling. The installation UUID resides in actual `chrome.storage.local` and remains distinct between profiles. The browser advertises exactly one global `grid` slot. Per-coin settings do not create workers or manager-owned replacements.

The existing canonical extension tick consumes a separate paper-only grant. Persistent `runtime.armed` remains false. Every tick checks dry-run mode, configuration identity, kill state and the saved grant. Configuration changes, extension updates and changed loaded control source revoke the grant and increment the owner generation. Manager start/stop cannot control an existing live/armed legacy owner: both refuse that unsupported context. Stop stops the browser paper owner; it does not cancel resting orders, close exposure or claim a flat account. Registration does not export financial valuation, so manager accounting/exposure remains explicitly unavailable.

Native messages use a strict, bounded, versioned `browserManager` envelope. The host verifies Chrome's process caller-origin argument against the existing allowed-origin authority. JSON cannot supply an origin. Generated native wrappers now forward `"$@"`; no installed user wrapper or manifest was changed. Browser request identities are UUIDs. Unknown fields, invalid origins and secret canaries do not reach persistent owner records or response bodies.

`browser.sqlite3` schema 1 holds validated owner snapshots and durable write-ahead control records. `(browser, installation UUID, grid)` maps to a stable UUID/reference, `browser:<UUID>:grid`. Requests bind the configuration hash/revision, owner generation, runtime, operation, sequence, expiry and request UUID. Browser storage writes a prepared receipt before applying a control and commits the paper state with the final receipt. A prepared outcome after worker death remains unknown and is never re-executed. A lost native acknowledgement resends the same receipt. Accepted IDs cannot be transplanted or rebound. Later stops revoke queued starts; the browser can also stop a proven earlier start already fetched in flight. Replaying that old start never restarts the slot. Pending, acknowledged, skipped, failed and unknown outcomes remain distinct.

Controls expire after 90 seconds. Discovery expires independently when the browser stops polling. Offline registration never starts another owner. Ownership transfer remains unavailable with the explicit reason `owner_prepare_quiesce_snapshot_commit_unavailable`.

Public integration API:

- `discover_browser(home)` returns sanitized installation dictionaries.
- `resolve_browser(identity, *, home)` returns a `BrowserAdapter` or `None`.
- `BrowserAdapter.discover()` reads the stored owner report.
- `BrowserAdapter.control(operation, request_id, *, expected_generation, expected_config_hash)` queues or replays its bound receipt.
- `browser_commands.command_specs(CommandSpec)` defines `browser-status`, `browser-control`, and `browser-receipt`.
- `browser_quiescent(home, *, now=None)` requires fresh observed stopped paper owners and no unresolved operations beyond a later acknowledged stop. Backup verification may pass the capture clock; restored discovery retains the original timestamps and needs fresh native registration.

The ordinary e2e guard grants no additional permission. Its explicit forbidden classification now names the two manager commands, which were already refused as unknown. The separate `extension/tools/bot-manager-e2e.mjs` gate has a narrow paper-only policy, uses test-owned Chrome profiles/native manifests/manager homes and blocks external network traffic below the extension.

Verification completed with final exit code 0:

- Extension unit/parity suite: **416 tests passed**. Log `/tmp/task6-js-final.log`.
- Native/browser/bridge tests: **37 tests passed**. Log `/tmp/task6-native-complete.log`.
- Manager browser/backup/read-consistency checks: **26 tests passed**. Log `/tmp/task6-manager-finish.log`.
- Ordinary Chrome e2e: **26/26 checks passed**, still disarmed. Log `/tmp/task6-ordinary-e2e-final.log`.
- Offline canonical economics: one completed round trip, net **$0.3492**, zero unknown-fee fills. Log `/tmp/task6-offline-economics.log`.
- Ruff passed for all task-owned Python paths. `git diff --check` passed.
- Separate real paper gate passed in Chrome **156.0.8078.47**. Both test profiles loaded the reviewed extension source/version, registered through the real native host, acknowledged manager start/stop, placed **four canonical simulated orders each with no errors**, retained actual `runtime.armed:false`, preserved the installation UUID across actual MV3 worker eviction/restart, verified the actual native origin and observed native-host removal failure. Distinct actual profile UUIDs were `65a488e1-746f-4632-9b14-b36034eae4ad` and `8dd303c8-d964-425b-ae61-641db31473b6`. Receipt/source evidence is committed in `task-6-paper-chrome.json` beside this report.

Limitations and controller-owned delivery:

The everyday browser installation is unchanged. Existing installed wrappers that drop Chrome's origin argument will safely refuse this registration until the wrapper is explicitly updated and verified. No user's Chrome database was opened, and no user's native manifest or browser profile was modified. Test-owned profiles and native manifests were removed. No arming, signing, live order or ownership transfer was performed or verified. Tests used source-loaded existing Python environments and an actual unpacked browser extension; final package version/pin updates, installed-environment acceptance, independent review and remote delivery remain controller-owned. The paper gate tested the checkout's then-current manifest version 0.6.3; the controller must rerun installed acceptance after its version bump.


## Independent-review fixes (version 1.1.0)

Registration no longer unconditionally stops or resumes the engine. Only a committed manager generation transition changes the paper engine gate. Registration, pending requests, lost acknowledgment/replay, failed expired/stale stops and prepared unknown controls preserve the owner's execution fields and queue generation. Armed legacy owners in both dry-run and semi-auto retain engine ownership. Failed/skipped controls record receipts without changing running, runtime UUID, generation or the accepted sequence fence.

Source identity schema 2 covers the manifest and every shipped JavaScript module, including engine, grid, risk, P&L, venue, storage/configuration and worker modules. A regression checks completeness against the source tree. The worker captures the packaged-resource hash at startup and verifies resources before manager registration/control and effective paper tick permission. Changed resources revoke an existing paper grant and permanently require extension reload for that worker, even if the resource later reverts. An engine.js resource-change regression exercises this fence through the actual worker dependency factory. The source hash describes fetched packaged resources; it does not attest Chrome's internal ESM module cache. Final installed-source acceptance must establish a fresh actual extension load. The read-only registry snapshot never initializes or durably revokes owner state: source validation refuses with reload-required while registration/tick paths own revocation writes. A registry regression checks this classification and durable-state boundary.

Completed checks (each final exit code 0):

- `cd /Users/mitch/dev/solmargintrader-wt-01a1c447/extension && npm test`: 422 tests including registry parity and new owner/source regressions; `/tmp/task6-review-js.log`.
- `node /Users/mitch/dev/solmargintrader-wt-01a1c447/extension/tools/dryrun.js --ticks 8 --osc 6 --offline 100`: one closed round trip, net $0.3492, zero unknown-fee fills.
- Ordinary guarded Chrome e2e: 26/26 checks; `/tmp/task6-review-ordinary.log`.
- Separate paper Chrome gate: two distinct profiles registered and acknowledged manager start/stop, each placed four canonical simulated orders, persisted disarmed state and installation UUID across worker recreation, and verified native origin/offline failure. Manifest version 0.6.4. Packaged-resource comparison spans the complete source list; `/tmp/task6-review-paper.log`.
- `git diff --check`: passed.

The separate gate preserved the controller's `SOLBOT_TEST_INSTALLED` mode, but this source gate used `installed_owner:false`. Final independently reviewed installed 0.6.4 acceptance and remote delivery remain controller-owned. The everyday browser profile and native manifest remain unchanged. No signing, arming or real orders were performed.
