# Chrome control-room launcher and fixed native availability bridge

Version: 1.0.1
Delta: 1.0.0 → 1.0.1; installed macOS acceptance, short private socket paths, preserved failure evidence and accurate native controller failure classification.
Task: TASK-1247. Parent owns final runtime build, installation, live acceptance and delivery.

## Implemented

- Popup and dashboard lead with the same `Sol · Bot control room` launcher, four component states, availability readiness, verified address, explicit Start servers and Open control room buttons. Existing Signal Desk, holdings, grid and native command views remain available. The shared light palette matches the control room; dark mode remains supported. The workflow labels lead to the real control room for each bot's actual stage and gates.
- All extension actions use the canonical registry: `controlRoomStatus`, `controlRoomStart`, `controlRoomOpen`. Status is read-only. Open reads availability, explicitly starts the fixed suite if necessary, then creates a fresh tab only for a helper-verified address. No additional permissions or localhost host access were added.
- The native host accepts only `{id,op:"suite",action:"status"|"health"|"start"}`. It checks the canonical Chrome process origin against locally configured allowed origins before importing controllers. It rejects browser-provided homes, paths, URLs, environment, argv and unknown fields. UUID admission deduplicates completed requests, bounds its cache to 128 entries and refuses concurrent startup requests on one port. Core filesystem ownership provides cross-process startup exclusion. Startup uses the bounded worker pool so a retained native connection can still read health.
- The helper returns `{schema_version:1,capability:"control-room-v1",status,health}`. Status contains only schema/state/readiness and the latest health-verified UI address. Both native and extension boundaries reject all URLs except `http://127.0.0.1:<port>` with a valid numeric port, an optional trailing slash, and no credentials, path, query or fragment. Local exceptions become fixed messages.
- A controller exception returns `suite_failed` with the fixed `solbot stack status` hint. The extension reports an answered helper and unknown suite health. It does not misclassify this local configuration/controller failure as a missing helper or certify a component as up/down.
- UI states distinguish unavailable helper, incompatible helper, stopped servers, pending startup, degraded components and healthy servers. Unknown helper health never becomes a server-down claim. Startup polling is bounded and read-only.
- A one-minute Chrome alarm reads the registered status action only. Component notifications require a measured up state before a subsequent down/degraded transition. Local state deduplicates repeats; a five-minute cooldown bounds flapping. Recovery emits a distinct notification. Missing/incompatible helpers do not certify component failures. Existing `alertsEnabled:false` disables these notifications. The daemon remains the durable monitor and recovery owner.
- Native installation preserves the Chrome process arguments and now pins the CLI `--extra-id` allowlist in the wrapper, so Chrome's manifest allowlist agrees with the host's own allowlist. Optional local-only `--manager-home` and `--ecosystem-home` flags pin the suite's homes. Every wrapper exports `INDEX_NO_AUTO=1` and pins `SOLTUI_EXTENSION_DIR` to the local repository's extension assets. Optional `--isolated` loads installed packages with `python -I`; use it for the regular production runtime.
- Linux installation discovers supported browser profile paths under `XDG_CONFIG_HOME` or `~/.config`. Native Windows installation refuses clearly because this Unix helper and suite are not a native Windows implementation. A Windows Chrome ↔ WSL shell bridge is not provided or claimed.

## Completed verification

- `INDEX_NO_AUTO=1 npm test`, extension directory: **434/434 passed**, final exit 0. Includes canonical command parity, source-identity coverage, all existing economics/risk tests, strict URL handling, unknown field refusal, non-mutating health, helper/controller failure distinctions and notification transition/dedup/recovery tests.
- `INDEX_NO_AUTO=1 SOLTUI_E2E_HOST=fixture node tools/e2e.mjs`, extension directory: **25/25 passed**, final exit 0. Real Chrome loaded popup/dashboard, ordinary read-only allowlist stayed strict, and dry-run/disarmed/no-order endpoint invariants held.
- Python native suite/browser-origin/registration/legacy bridge parity/surfaces/CDO set: **84 tests passed**, final exit 0. After the final URL sanitization change, the focused suite/browser-origin/registration set passed again: **14 tests**, exit 0. The focused set includes actual core status/check calls against absent temporary homes and proves they do not create either home.
- `node --check extension/tools/control-room-e2e.mjs`: passed, exit 0.
- `git diff --check` on owned changes: passed, exit 0.
- Test logs: `/tmp/solbot-1247-extension-tests-final.log`, `/tmp/solbot-1247-chrome-e2e.log`, `/tmp/solbot-1247-native-tests.log`, `/tmp/solbot-1247-native-focused-final.log`.

The native suite tests updated the old installer fixture's invalid example extension IDs to valid 32-character Chrome IDs. The production allowlist now validates those IDs before writing its wrapper.

## Installed acceptance

The actual installed-suite Chrome gate is implemented at `/Users/mitch/dev/solmargintrader-wt-1247-suite/extension/tools/control-room-e2e.mjs`. It deliberately requires a regular installed compatible runtime because suite startup correctly refuses a source checkout.

The macOS gate passed with Chrome `156.0.8078.47`, extension `0.6.5` and the regular `/Users/mitch/.venvs/solbot-0.7.0/bin/python` runtime. All 11 checks passed, including actual Start servers and Open control room clicks, UI health, legacy native ping/help/buildHash/settings/status reads, a verified test-owned UI fault followed by recovery observed from Chrome, missing/offline unknown health, disarmed/dry-run persistence and complete shutdown. The first verified UI was `http://127.0.0.1:59337`; the monitor recovered it at `http://127.0.0.1:59385`. Receipt: `/tmp/solbot-1247-availability-short.log`. A private durable copy is `/Users/mitch/.local/state/solbot/releases/0.7.0/chrome-failure-20261110-1209/chrome-short-pass.json`.

The first fixture used Darwin's long per-user `TMPDIR`. The native installer resolves its fixed home paths; the resolved `.suite/control.sock` path was 111 bytes and a direct bind reproduced `OSError: AF_UNIX path too long`. The corrected gate uses canonical `/private/tmp/solbot-ui-*` private homes. Failed fixture logs and bounded startup observations remain private at `/Users/mitch/.local/state/solbot/releases/0.7.0/chrome-failure-20261110-1209`. The gate now preserves evidence on failure and still shuts down its owned components.

The final `suite_failed` refinement changes the installed native module. The parent must rebuild/install the research-runtime wheel and rerun this gate. The gate now includes a twelfth check: a local wrapper-only invalid ecosystem-home fixture proves a failed fixed status read keeps the helper available and health unknown. The browser cannot supply that fixture path.

Run from `/Users/mitch/dev/solmargintrader-wt-1247-suite/extension` after the parent installs the final wheels:

```sh
INDEX_NO_AUTO=1 SOLBOT_TEST_INSTALLED=1 SOLBOT_TEST_PYTHON=/Users/mitch/.venvs/solbot-0.7.0/bin/python node tools/control-room-e2e.mjs
```

This separate gate owns a temporary Chrome profile, manager home, ecosystem home and console home. It verifies missing-helper unknown health, installed headless native ping/list/buildHash/settings.get/prices.status compatibility, distinct controller failure, strict actual native caller origin, servers down before a click, real Start servers button bringup, real Open control room button navigation, the actual HTTP health endpoint, a verified test-owned UI process fault followed by suite recovery observed from Chrome, offline helper recovery semantics, dry-run/disarmed persistence, and complete test-owned component shutdown. It blocks external network traffic and all non-GET loopback HTTP requests. It never edits everyday profiles or installs a user service.

For the parent's production helper installation, use the fresh runtime's installed installer with `--isolated` and fixed homes:

```sh
INDEX_NO_AUTO=1 /Users/mitch/.venvs/solbot-0.7.0/bin/python -I -m soltui.native_host_install install --python /Users/mitch/.venvs/solbot-0.7.0/bin/python --repo /Users/mitch/dev/solmargintrader --isolated --manager-home /Users/mitch/.config/solbot --ecosystem-home /Users/mitch/.local/share/solmargintrader/ecosystem-paper-v2
```

The parent must first reconcile the existing manager/UI owners and service, as already tracked in the parent continuation records. This child made no live profile, manifest, process or service changes.

## Documentation consulted

- `/Users/mitch/.agents/skills/chrome-extension-expert/SKILL.md` and its native messaging, tabs management and extension security references.
- Context7 Chrome runtime/tabs reference: `tabs.create` needs no broad tabs permission; URL-based tab discovery requires tabs or matching host permission. A fresh tab avoids widening permissions.
- Official references: https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging and https://developer.chrome.com/docs/extensions/reference/api/tabs
