# Task 3 — backup and health/load verification

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
