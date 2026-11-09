# Signal Desk implementation acceptance

Version: 1.3
Delta: v1.2 to v1.3; bind final archive-view source hashes and verify archive provenance separation plus unavailable chart tooltips. Preserve the frozen pre-delivery scope and separate final delivery receipts.
Verifier: live-acceptance-verifier 1.0.0; independent agent context /root/signal_desk_acceptance.
Observed: 2026-11-09 04:51:59 UTC.
Status: **Frozen pre-delivery installed-unpacked checks passed. Final canonical post-install acceptance is outside this report's scope.**

## Installation and loaded identity

The verifier loaded the real unpacked MV3 extension into a fresh Chrome for Testing profile with `Extensions.loadUnpacked`. This is actual extension execution under its manifest/CSP. It does not reload or replace the owner's existing browser profile.

Source worktree: /Users/mitch/dev/solmargintrader-wt-signal-desk.

Source baseline: `6212fd81e5c33e9124a762a96efbc4662ee1ca3b`; implementation is the task-owned working tree at this checkpoint.

Loaded version: `0.5.0`.

Loaded acceptance target:

chrome-extension://jjdgjplmfkpcnidjabhkdcocidenhfgm/src/ui/dashboard.html#soltui/signal

| Resource | Loaded and on-disk SHA-256 |
| --- | --- |
| /Users/mitch/dev/solmargintrader-wt-signal-desk/extension/src/ui/signal-desk.js | `b904f1d6684eaad532a2f7887786d1cabcc9c6602b0f72da363226e77cbbfafe` |
| /Users/mitch/dev/solmargintrader-wt-signal-desk/extension/src/ui/desk-model.js | `b05e5945fabb73d7e75bf5b06e6d5dd13965d48f92a4d0951eae19f5047e6d09` |
| /Users/mitch/dev/solmargintrader-wt-signal-desk/extension/src/ui/signal-desk.css | `111fab5f36ff6df2bbe92bf4d42c4c1bdcb8ea78a48eb2c22ab01773ab45262c` |

The verifier compared local extension resource bytes to disk. Separately, `Debugger.getScriptSource` matched the executed module bodies, and `CSS.getStyleSheetText` matched the applied stylesheet. This does not infer loaded identity from the Git branch or a newly fetched file alone.

## Safe execution scope

The native-host integration half of the canonical harness permits only registry-listed read-only calls and existing non-operational browser fixtures. Write scenarios run in a separate extension target whose native transport and view-preference persistence are replaced in memory before production modules load. The fixture verifies production UI code with explicit fixture data; it is not a production market result or a claim that a backtest ran against the owner's data.

No trainer, recorder, scheduler, trading engine, indexing process or model runtime was started. No order was submitted. No signing or user credentials were used. The owner's installed browser profile and active native leases were not reloaded. All test browsers used throwaway profiles. The acceptance target requested only local extension resources; the broader harness blocked external market network and verified its read-only request allowlist.

## Observed behavior

| Check | Actual result |
| --- | --- |
| Four primary routes | Live signals, Backtesting, Forward testing and Bot monitor render their intended title and content |
| Backtest units and scope | `-0.02` renders as `-2%`; median path metrics and aggregate trades remain separately labeled; unsupported richer metrics remain unavailable |
| Existing archives | The read-only cumulative summary displays original source, rankable/below-floor counts and recorded median Sharpe; inspection identifies an original summary, while archive rows supply no comparison checkbox or pinned-paper staging action |
| Saved comparisons | Matched contexts display a compatible summary; changed dataset evidence displays incompatible/no combined ranking |
| Paper handoff | Exact data/strategy/cost snapshot, strategy label, horizon and disabled optimization stage into the review form; staging sends no native mutation |
| Explicit preparation | Reviewed preparation sends only snapshot/source label/horizons/optimization; no forwardtest.run is sent |
| Forward arithmetic | 137 correct of 216 resolved renders 63.43%; one pending forecast stays separate; `-0.006` net renders `-0.6%` |
| Worker responsibilities | Native-session checks and detached trainers have distinct lifetime labels; an alive trainer can show output 18 minutes old |
| Expired signal | Current interpretation becomes neutral Unavailable; a strictly newer chart tick records no score and its tooltip says Unavailable without Flat; fresh recovery restores the correct directional agreement |
| Filter recovery | Query and focus survive prediction refresh; no matches has an explanation and Clear filter restores rows |
| Disconnected evidence | Missing forward status displays Unavailable rather than a fabricated zero, then recovers after a successful read |
| Search | Filters tool metadata locally; from a legacy Settings view it opens the visible workspace and selects a form without running it |
| Archived controls | liquidity.resume stays visible but disabled; even direct expert-form submission sends no archived mutation |
| Dialogs | Both dialogs have heading-based accessible names; trusted Escape closes them and focus returns to a connected trigger or workspace heading |
| Desktop layout | All four screens fit at 1440px with table overflow contained inside tables |
| Narrow layout | All four screens and Settings remain reachable at 390px without document horizontal overflow |
| Zoom-equivalent layout | All four screens fit a 720px CSS viewport with device scale 2, a reflow smoke check for a 1440px/200% scenario |
| Density | Compact preference changes the rendered density and its saved view preference |
| Console and safety | Canonical harness reports no uncaught worker/page exceptions and ends disarmed in dry-run |

## Visual and accessibility sample

The verifier inspected screenshots of the actual rendered extension, not the proposal mockup. The warm near-white cards, deep teal navigation, four prominent workflows and restrained signal color preserve the approved direction. The dark variant retains the same hierarchy and readable contrast.

Screenshot artifacts:

- /tmp/signal-desk-acceptance-light.png
- /tmp/signal-desk-acceptance-dark.png

Seven sampled text/background pairs passed 4.5:1 in each theme. Lowest observed light ratio: 5.6167:1. Lowest observed dark ratio: 8.0248:1. These samples cover body text, view subtitle, KPI label/detail, navigation, selected primary navigation and interpretation eyebrow.

This is not a full WCAG conformance audit. A screen-reader task audit, every color/state pair, native browser zoom controls and all possible backend payloads were outside this smoke check. The viewport/scale test is labeled as a zoom-equivalent reflow check, not a full 200% zoom certification.

## Finding and correction

**A01 Medium — Escape dismissal: resolved.** Before the correction, a trusted Escape event reached the focused search input but the open native dialog stayed open. The implementation now explicitly closes the open Signal Desk dialog on Escape and uses onclose to restore focus. The same trusted-key browser test passes for both search and evidence dialogs. The test gate was not weakened.

No residual actionable finding remains in the pre-delivery implementation subject.

## Canonical commands and current gates

Executed successfully:

```bash
SOLTUI_E2E_HOST=fixture npm --prefix /Users/mitch/dev/solmargintrader-wt-signal-desk/extension run e2e
```

Result: 24/24 checks, exit 0. Log: /tmp/signal-desk-independent-e2e.log.

Executed successfully after the final harness additions:

```bash
SOLTUI_E2E_HOST=real npm --prefix /Users/mitch/dev/solmargintrader-wt-signal-desk/extension run e2e
```

Result: 25/25 checks, exit 0. Log: /tmp/signal-desk-independent-real-e2e.log. This includes production native-host and Python CLI parity with read-only calls. The UI write scenarios still run only against the separate memory fixture. Both final local variants completed before the parent commits implementation.

## Separate final post-install gate

This is a frozen record of the pre-delivery installed-unpacked checks above. It does not assert the later canonical installation's status. After delivery and synchronization, the independent verifier loads /Users/mitch/dev/solmargintrader/extension into a new isolated Chrome profile, binds the loaded version and executed/applied resource hashes to the delivered source, and runs the real-host read-only plus memory-only-write harness as the final acceptance gate.

The implementation PR's delivery receipt and /tmp/signal-desk-installed-acceptance.json record that gate's actual result, delivered revision, time and remaining limitations. Consult those receipts for final delivery status; this historical report is not updated after installation. The owner's existing browser profile remains outside that gate unless a separate safe reload is performed and observed.
