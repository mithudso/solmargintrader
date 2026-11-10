# Task 3 — backup and health/load verification

Version: 1.1.0
Delta: 1.0.0 -> 1.1.0; repair independent-review pause ownership, aged browser restore and fast failure alerts.

Status: source backup implementation and owned tests ready. Controller owns health.py, supervisor/status/control/registry integration and release verification.

## Backup

create_backup(home, destination) requires an initialized manager home and an absent external destination. It takes supervisor/worker/mutation locks, requires stopped runtime intent/observation with no pid or unresolved tick, reserves local database writers, and snapshots each SQLite database through SQLite backup. The manifest includes checksums, schema versions, table counts/max-rowid cutoffs, captured time, external input dependencies and an explicit consistency label. Includes manager/runtime/health/controls journals, research-owner.json and research-plan-*.json. It excludes logs, locks, credentials and the external canonical research database.

restore_backup(source, destination) validates manifest/inventory/checksums/cutoffs, current/archived immutable runtime decoders, pinned input dependencies, installed owner identity and canonical research registration before creating an absent destination. It copies no service definition and starts nothing. It leaves the canonical optimizer database untouched. Registration must still identify the same authority/namespace/config root. Captured holdout/exposure row commitments must remain present, allowing additional later spending but rejecting rollback. This preserves spent research dates across manager-home restoration.

The owner describe protocol is inert; backup deliberately does not call owner status, whose current implementation constructs ExperimentStore. Owner installation checks use describe plus direct mode=ro SQLite reads. Local research proposals require the local reviewed research-owner.json binding. Input files are referenced, not copied.

Conservative limits: unknown/pending delegated owner receipts refuse snapshot. A historical acknowledged external start also refuses because local journals alone do not prove external owner quiescence. browser.sqlite3 is a known journal name but refuses until its ownership-quiescence contract is integrated. Research spending verification caps each spending table at 100000 rows. Backups are local consistency snapshots, not whole external research authority backups or relocation tools.

## Verification

17 backup/health tests passed, exit 0. Covers exact restored identity, no worker start, schema/table cutoffs, corruption, missing input/canonical dependencies, changed owner identity, canonical history nonmutation and rollback refusal, no overwrite, unresolved delegated controls, plan inclusion and secret/log exclusion. Health tests verify fresh process/stale input, stopped retained exposure, independent stalled evaluation/valid loss/unavailable result, deduplicated cooldown alerts and resolution evidence, read nonmutation and bounded diagnostics rotation. Ruff passed.

Real process capacity/load fixture passed, exit 0, in 16.735 seconds. Initial admission is ten paper bot intents, with four active workers and six queued. The extra process provides synthetic CPU pressure while holding the real canonical optimizer lease; it is explicitly not a research-quality optimizer workload.

Measured: status p95 0.013618s, durable stop acknowledgement 0.001194s, owner release 0.008544s, crash detection 0.012351s. SIGSTOP stale heartbeat detection measured 15.006080s from freeze and 15.011962s from last heartbeat. The strict <=15-second detection target is missed by polling overhead; the test allows 16 seconds and this is a measured limitation, not a passed strict SLO.

Forced restart retained the exact canonical checkpoint/fills; no duplicate tick financial events occurred. Under a saturated pool, queued accounts initially occupied a crashed account's retry slot; controller is repairing retry-slot reservation. The current committed fixture isolates restart by stopping other accounts before restart, then probes the actual watchdog separately. Re-run saturated automatic recovery after controller fix.

Full manager and changed owner suites, actual installed acceptance and remote delivery remain controller release gates.


## Controller repair and stricter recheck

Supervisor now reserves a recovering worker slot during bounded retry delays and detects stale work at14seconds, leaving polling/termination headroom for the15second SLO. The saturated crash fixture retains all other desired-running intents through automatic recovery. Recheck passed: active4,queued6,statusp95=0.010360s,stopack=0.001163s,release=0.008282s,crashdetect=0.007881s,staledetectfromheartbeat=14.022469s. Strict assertions now require both watchdog measurements below15seconds. Supervisor18testregressions passed. Original failed/tolerant measurements above remain historical evidence.


## Independent review repair — version 1.1.0

All three numbered findings in task-3-review.md are repaired. Pause/resume now atomically fence the prior generation and move eligible desired-running accounts to recovering with an explicit entry-policy handoff reason. The supervisor reserves that handoff slot against queued work. Failed/blocked states and failure counters remain intact; a blocked account does not claim that exits continue. A real four-active/six-queued worker regression pauses after a buy, proves the replacement owner retains the exact lot checkpoint, releases a later exit bar, verifies existing lots sell without new buys, and verifies resume also replaces the owner without resetting the account or charging a failure.

Backup records its capture timestamp immediately after the copied journals pass quiescence. Restore validates browser quiescence at that immutable capture cutoff, then preserves every copied timestamp. A one-hour-delayed browser restore regression checks the exact copied journal bytes, acknowledged stop receipt and original account identity. Current discovery correctly remains offline until a fresh browser-owner reconciliation; restore does not manufacture fresh ownership.

Health now exposes observed lifecycle/reason separately from heartbeat liveness, and retains worker-exit/spawn/stall/blocked/failed identities as alert blockers. The supervisor writes the failure observation immediately after ledger.failed, before termination/replacement can clear its reason or refresh heartbeat. Alert resolution preserves the original source/runtime/generation/reason together with the fresh resolution evidence. A real worker crash regression disables periodic health sampling during the failure, proves an attributable alert is persisted and later resolved, and verifies checkpoint/fills remain unchanged. A watchdog reason regression verifies tick_stalled and evaluation_stalled survive cleared transient tick clocks. A valid measured loss remains independent of those failures and does not create an unsupported performance warning.

Verification: 51 combined health/entry-control/backup/supervisor/load/learning regressions passed, exit 0, before the final additional failed-state pause regression (which passed in the four-test entry-control suite). Focused backup/health/entry-control run passed 23 tests before that addition. Ruff passed. Latest strict saturated load measures: four active/six queued, status p95 0.014281s, stop acknowledgement 0.000850s, owner release 0.006807s, crash detection 0.006974s, stale detection 14.013387s from freeze and 14.017524s from heartbeat. No installed service or production state was touched.

### Literal optimizer workload and final checks

The load fixture now runs actual bounded canonical M4 optimization in an isolated, explicitly registered ExperimentStore authority. It holds the shared optimizer lease and performs real canonical training cells and isolated resolver evaluation over numerical fixture recordings. Every attempt uses disjoint recorded fixture dates and the existing configuration/cell limits. Source evidence remains explicitly uncertified; no quality gate, proof, admission rule or temporal exposure is bypassed to keep the job active.

The final workload run passed in 16.114 seconds: four active paper workers and six queued; optimizer ownership remained held throughout. Four admitted attempts reserved 2465 cells and completed 2464 numerical cells at measurement time. Three finished attempts honestly retained the incumbent for uncertified_reference_evidence. The fourth was cooperatively cancelled after load measurement, retained the incumbent, spent no final and exited cleanly. The canonical exposure table was nonempty and verified zero overlaps between different attempts. No optimizer, recorder or training service was started outside the temporary fixture authority.

Under that actual workload: status p95 0.011897s; durable stop acknowledgement 0.000736s; owner release 0.006999s; crash detection 0.006520s; watchdog detection 14.017040s from freeze and 14.021062s from heartbeat. Every specified latency assertion passed. Financial checkpoint/fills and the saturated retry reservation assertions remain intact. Numerical fixtures do not establish a production trading edge or certified market evidence.

Final per-suite checks passed: 13 backup tests, nine health tests, four entry-control tests, 18 supervisor tests, nine learning tests and one actual-optimizer load test (54 total across these runs). The additional health test prevents a replacement claim's synthetic heartbeat from resolving a crash before an owned PID reports recovery. A nonempty current/archive/segment restore regression preserves exact segment bodies, archive bindings, accepted requests, entry-control receipts and pause rows. Ruff passed for all owned source/tests. Diagnostic rotation remains a bounded helper for the selected diagnostic filename; there is no new production log stream or claimed installed logging policy. Installed acceptance and remote delivery remain controller gates.
