# Task 4 report — bounded canonical continuation

Version: 1.2.0
Delta: 1.1.0 to 1.2.0; also validate continued data-check reads through the pinned account without replay and refuse account-less continued registration.

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


## Independent review P1 remediation

The Grid constructor now reads `origin_close` explicitly and reads the first active bar only when the origin is absent. If both are unavailable it returns the recoverable `input_unavailable` error. A worker/ledger regression reaches 512 real completed bars, performs the next poll with no new completed bin, commits an empty active segment, verifies the immutable predecessor and unchanged economic account, restarts, and resumes at bar 513 with exact canonical fills, lots and equity.

Manager runtime support now has a finite parameter budget: `MAX_RUNTIME_LOOKBACK_BARS = 2048` for Trend `slow_period` and Momentum `window`. The maximum retained signal history is 2,050 observations because canonical Momentum warmup requires `window + 2`. Editable draft validation remains unchanged: larger settings can be saved and inspected, but execution returns `resource_limit`. No parameter, indicator history or timeframe is clamped. Shared offline canonical backtester behavior is unchanged.

`validate_runtime_config(spec)` executes before reference input validation or NumPy array creation. Registration, direct evaluation/research evaluation and flat rebind consume this guard. Input preparation/data checks run it before source selection or capture. Direct runtime start validates the pinned active specification before admission or accepting a request receipt; stop remains usable for legacy unsupported configurations. Research candidate construction, candidate enumeration and execution reject unsupported incumbent/proposal settings before planning or reserving attempts. The independent headless owner repeats that validation before client discovery, temporal pre-read exposure and source capture. Learned-spec construction and shadow-pair preparation reject unsupported proposals before selecting a prospective source. Rebind and adoption refusal preserve the incumbent account.

The controller exposes the same exported constants in the schema and guards registry input/research routes before source capture. Draft schema fields retain their original editing behavior.

New boundary checks include 2,049 and one-billion-bar drafts, exact-at-limit 2,048-bar settings, 4,353 observed bars over 35 segments with tail length at most 2,050 and checkpoints below 400 KB, unchanged incumbent checkpoints after extreme proposed adoption, rejected direct start of an older unsupported registration without a new request receipt, usable stop, and direct owner refusal before temporal exposure/attempt creation.

Completed verification, all final exit codes 0:

- `PYTHONPATH=botmanager/src:botmanager:. /Users/mitch/.venvs/solbot/bin/python -m unittest tests.test_continuation tests.test_strategy_parity tests.test_research tests.test_learning tests.test_oracle_data`: **44 tests passed**, log `/tmp/task4-p1-final-manager.log`.
- `PYTHONPATH=botmanager/src:botmanager:. /Users/mitch/.venvs/solbot/bin/python -m unittest soltui.tests.test_research_owner backtester.tests.test_engine backtester.tests.test_engine_audit backtester.tests.test_gridsim backtester.tests.test_dcasim backtester.tests.test_open_prefix`: **135 tests passed**, log `/tmp/task4-p1-canonical-owner-correct-env.log`.
- Ruff passed for all remediation-owned Python paths. `git diff --check` passed. Tests used the existing solbot interpreter with the worktree on PYTHONPATH; no packages, production state or services were modified.

An earlier native-owner test invocation under the existing soltui interpreter lacked `solmargintrader-research-runtime` distribution metadata. That failed invocation is not an acceptance receipt; the successful existing solbot environment above supplies the required metadata.

Resource claim clarification from the independent review: active input and checkpoint memory are bounded. Immutable attributed history intentionally grows linearly. Current ledger reads still verify prior segment hashes and historical fill ranges, so verification work grows with the amount of preserved history. This change does not claim constant total storage or constant history-verification time.


## Continued public data-check correction

The public `data-check` runtime path now selects the pinned active specification rather than a conflicting saved draft. It validates the existing source snapshot, compatible engine and retained checkpoint without invoking a fresh registration replay at cursor 1. Explicit descriptor checks still use fresh-registration validation. Fresh registration rejects continued input with a prior segment or nonzero bar offset because that input cannot initialize an attributed account by itself.

The 512-bar regression now also saves a conflicting $2,000 draft while the active account retains $1,000. It invokes the actual public registry `data-check` at the empty rollover boundary and again after bar 513. Both reads remain compatible, never invoke strategy evaluation, preserve the complete runtime row, and leave both manager/runtime database bytes unchanged. Attempting to register the continued source into another home returns `reconciliation_required` before creating that runtime database. The targeted public regression passed independently (1 test, exit 0), and the complete 44-test focused command above was rerun on this final source into `/tmp/task4-p1-public-final-manager.log`.
