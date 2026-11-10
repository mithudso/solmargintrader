# Task 4 report — bounded canonical continuation

Version: 1.0.0
Delta: initial implementation and verification receipt.

Implemented versioned continuation directly in canonical `backtester.core.engine`, `gridsim`, and `dcasim`. The existing loops still own decisions, costs and fills. Grid preserves fixed original geometry, resting intent, lot basis and carry. DCA preserves deal/safety/TP/cooldown state and pending next-open intent. Trend and Momentum retain bounded observed indicator tails, global warmup indices, position/account state and pending targets. Trend owns its hysteresis checkpoint hook. Other signal strategies do not advertise resumable state.

The manager dispatcher accepts an optional prior checkpoint. Workers pass it instead of replaying the entire prefix. Prospective inputs roll over at 512 completed bars (a fetched page may cross that threshold). The ledger atomically archives the immutable prior input/checkpoint, chains its digest into the next segment, and retains every attributed fill. Checkpoints and active input stay bounded; total immutable evidence storage intentionally grows with genuine history. Reads verify segment hashes, cursor continuity and attributed fill ranges. Missing predecessors refuse decoding. Source observation cursors and cross-segment observed cadence survive the transition; gaps remain held, never interpolated or re-timed.

Runtime journal writers migrate schema 4 to schema 5. Schema 5 requires the `segments(runtime_id,digest,body,fill_end)` table. Read-only access supports schemas 1–5 without initializing or migrating them. Older schema-4 code rejects schema 5, preventing an old writer from overwriting the new contract. Existing pre-continuation accounts cannot silently reset: checkpoints without compatible canonical state refuse continuation.

Grid/DCA entry pause suppresses entry fills while retaining original pending/resting intent; exits continue. Worker commits remain generation-fenced. Admission now allows up to the existing 100-instance bound; the supervisor retains its separate four-process pool.

Added pure `botmanager.strategies.rebind_checkpoint(spec,data,checkpoint,*,entries_paused)` for Task 5. It requires paused entries, a flat attributed account and compatible canonical engine/source identity. Family-owned rebind hooks retain cash, realized P&L, fees, fills, cursor and starting capital. DCA requires no pending market intent. Signal rebind refuses a lookback requiring observations beyond the retained tail. The caller must archive and publish the rebound specification/account atomically; this helper performs no persistence.

Verification (Python `/Users/mitch/.venvs/solbot/bin/python`, source PYTHONPATH, no installation or production-home writes):

- 45 focused manager continuation/source/parity/paper/recovery tests passed; exit 0. Log `/tmp/task4-final-focused.log`.
- 116 canonical engine/audit/grid/DCA/open-prefix economic tests passed; exit 0. Log `/tmp/task4-final-economic.log`.
- 19 supervisor/load tests passed; exit 0. Log `/tmp/task4-supervisor-repeat.log`. The ten-bot fixture maintained four active and six queued workers.
- All owned Python paths passed Ruff; exit 0.
- New continuation tests compare exact decisions/trades/fill times, equity, account cash/lots, fees and realized P&L over 2,307 bars for all four supported families. Every 127-bar canonical boundary undergoes JSON restart. Dispatcher tests also cross 2,048 bars for all families without prefix replay.
- A prospective 2,307-bar ledger test crosses multiple immutable segments, injects a pre-commit crash at transition, restarts after commits, verifies bounded active input/checkpoint sizes, matches the uninterrupted canonical fill history and equity exactly, and refuses a missing prior segment.
- Gap, duplicate observation, configuration-binding tampering, pause/exits and flat-rebind/history-bound refusal tests passed.

Earlier full-suite attempts are not acceptance receipts: using the wrong manager discovery top directory caused spawned-worker import failures. The controller owns the correctly rooted final full manager run. An earlier 996-test backtester run found only Finder metadata in a frozen snapshot and stale index failures; the controller owns those integration fixes and the final full suite. Package versions/pins, indexes, external delivery and independent installed acceptance remain controller-owned. No claim of seven days of measured live evidence is made; tests prove the runtime can continue beyond the old bound while preserving the account.
