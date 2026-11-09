# Dashboard and SolTUI parity

The dashboard is the extension's primary workspace as of version 0.4.0. The popup links into it.
Open the extension's **Full workspace** link. The sidebar groups tools by the same work they perform
in the TUI. Existing holdings, alerts, swap quotes and the experimental grid remain available.

The dashboard reads the installed native host's complete command registry. It builds every form
from the command's declared parameters, including required fields, numbers, JSON and explicit
true/false values. **All tools** includes new registry commands without a browser update. The host
and dashboard must use the same checkout to include newly delivered tools.

| Workspace | Available workflows |
| --- | --- |
| Now | Recorder status, running backtests, sweep queue, forward workers, autopilot, optimizer schedule and saved portfolio |
| Signal | Compound catalog, per-coin configuration, metrics, signal, backtests, forward results, predictions, training and autopilot |
| Research & replay | Strategy cards, roster changes, CPCV backtests, queue controls, batches, cumulative results, Top 5, per-bar analysis, indicators, prospective paper experiments and replay start/step/reset/end |
| Bots & prices | Grid, DCA and triangle configuration, backtests, coin ranking/audit, forward testing, optimization, scheduling and recorder controls |
| Experiments | Schema, bounded search preview/create, saved runs, start/pause/cancel/finalize, candidates, cells, heatmap data, CSV import and comparisons |
| Money & orders | Public wallets, portfolio snapshots/changes, P&L by source, Coinbase catalog/account, Jupiter token search, market/percentage/conditional previews, reviewed submit and reconciliation |
| Library & editor | Document catalog/search/read, guarded save and draft export |
| TUI settings | Shared dates, costs, capital, CPCV settings, public addresses and forward autostart |
| Archive | Historical Aero LP status/data and existing registry controls; this release does not reactivate the discontinued service |

## Working in the dashboard

Choose a workspace and a tool, fill its fields, then run it. Field descriptions come from the
backend. Empty optional fields use the backend default. Optional strings have an explicit clear control
for sending an empty value, such as clearing a saved wallet address. Boolean fields offer default, true and false.
JSON fields accept arrays or objects as described beside them. Document text preserves whitespace.

Results have readable summary fields and tables, plus the original JSON envelope under **Raw
response**. Tables support filter, numeric/string sorting, pagination and CSV export of all filtered
rows across pages. Sort and filter choices survive status refreshes. Numeric time series have
charts when the source provides an explicit time and value. Sparse experiment heatmaps color observed cells and label unmeasured cells without
interpolation. Underlying observations remain available as tables. CSV exports quote
fields and neutralize spreadsheet formulas in strings. Downloads follow Chrome's download settings.

**Inspect / use row** shows the full row and copies matching declared fields into the current form.
Document rows open the shared editor. Preview results offer a button to open the appropriate
Coinbase/Jupiter submit form with its preview ID. Opening that form never submits the order.

The editor saves through `docs.write`, with the same catalog restrictions as the TUI. It checks the
latest text before saving and refuses a detected concurrent change. It leaves a refused draft in
the editor for export. Research/results files remain read only. The backend does not provide an
atomic compare-and-swap write, so the pre-save read cannot eliminate the small concurrent-write race.

Recent results and running calls remain accessible while switching tools. A running command cannot
be submitted again from that dashboard until it returns. Long native calls run independently so
status and cancellation tools remain available. Multiple dashboards share one native host/runtime.
This runtime is separate from an independently launched terminal TUI process; disk-backed evidence
and settings are shared, while process-local replay and sweep state belong to their owning process.

The Signal/Now live card reads the existing recorder every five seconds when **Follow stream** is
selected. It refreshes saved strategy predictions every minute. Each price retains its source time
and quote age; stale/offline records are labeled. This view never starts a recorder or trainer.
Selected status tools also offer a ten-second refresh. These controls only repeat explicitly
allowlisted read commands. Mutating commands never run automatically.

## Native host and safety

Use the existing host installation procedure in `extension/README.md`. The extension still uses
`com.mitchhudson.soltui` and adds no browser host permissions, localhost server or runtime dependency.

A dashboard renews a 90-second native session lease every 25 seconds. The extension retains one
multiplexed native port while dashboards or pending calls need it. Closing every dashboard ends
process-local sessions after pending calls finish. A crashed page's lease expires. Detached workers
and disk records retain their existing lifetimes. With no dashboard, background probes use the
original short-lived connection. Automatic extension reload defers while a dashboard lease or
native request is active, preserving replay, jobs and unsaved forms. Close the dashboard before an
automatic source update can take effect, or reload the extension explicitly when safe.

The native host admits at most four concurrent long-running calls. Other requests, including
status and cancellation, stay on the reader thread. Request IDs match out-of-order replies; a write
lock keeps frames intact. The Chrome 1 MB reply limit still applies; use paginated backend commands
or the CLI/API for oversized evidence.

Disconnects and timeouts never retry requests. A timed-out submit has an unknown outcome: inspect
saved order state and reconcile it. A session change disables dashboard polling and reports that
in-memory work may have been lost. Backend validation, confirmation, order caps, transaction
verification and reconciliation still decide whether an action is allowed. Confirmation resets
after each attempt and is never copied from a result row. Quick orders require their own explicit
`skip_confirm=true` choice. This release does not arm the extension, start any worker or submit an
order. Fresh installation remains disarmed and dry-run.

## Verification

Run from the repository root:

```bash
npm --prefix extension test
node extension/tools/dryrun.js --ticks 8 --osc 6 --offline 100
npm --prefix extension run e2e
python3 -m unittest soltui.tests.test_bridge_surfaces soltui.tests.test_bridge_parity soltui.tests.test_bridge_buttons
```

The browser gate loads the actual extension in a throwaway Chrome for Testing profile. It verifies
workspace routing, registry coverage, forms, structured tables, sorting/filtering, confirmation,
the native bridge and dry-run rails. It permits only read commands in the native registry. Native
framing tests prove that cancellation can reach a running long call using the same runtime. Browser
coverage does not exercise real trading, start trainers or prove every research result correct.
