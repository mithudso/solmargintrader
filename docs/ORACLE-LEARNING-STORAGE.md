# Saved Oracle learning

Version: 1.0.0
Delta: preserve both browser learners and add complete local disk checkpoints.

The Live Oracle and minute-close Oracle remember their own results for each
coin and source across chart changes, coin changes, hiding the window and browser
restarts. Each learner keeps six independent horizons. Returning to SOL shows
SOL's saved results; another coin, source, target or horizon cannot supply them.
Changing the chart interval does not change these learning identities.

When a feed is stale or paused, saved counts remain historical. They do not imply
a fresh forecast, active learning or trading readiness. A new model can still
show zero genuine outcomes. The two learners use different targets and must not
share their sample counts or weights.

## Browser storage and local disk

IndexedDB remains the primary store. Each update commits weights, pending
forecasts, results, watermarks and checkpoint metadata atomically. Windows in
the same Chrome profile share it. A failed write cannot commit half a model.
Existing compatible records are preserved and receive backup metadata without
training on historical labels.

The existing native helper also saves complete checkpoints in a private SQLite
database. The default path is
`/Users/mitch/.local/state/oracle-learning/checkpoints.sqlite3`.
`ORACLE_LEARNING_HOME` can select a different directory for an explicitly
configured helper. The directory is private to the user and the database file
uses mode 0600. This requires no MongoDB server or new background service.

Open **Saved learning and disk backup** in the Jupiter window. Its per-partition
status distinguishes local data, a pending save, an acknowledged disk save,
verified recovery and unavailable or conflicting backups. Automatic saves
coalesce the latest state and normally run at most once per partition every
30 seconds while the panel is open. **Save now** requests the queued latest
checkpoints immediately. Only a successful helper acknowledgement reports a
disk save. Closing a panel does not promise that an unfinished upload completed.

If the helper is missing, slow or disconnected, browser learning continues.
The panel reports the backup as unavailable and retries while open. A helper
failure must not replace saved browser history with an empty model. A timed-out
save remains fenced until its underlying request settles; timeout does not
prove that a disk write was cancelled.

The disk checkpoint includes the full bounded learner state, not just displayed
totals. The native archive also retains resolved outcomes present in checkpoints.
It is not a complete raw quote or tick recorder. Existing quote-collector
retention and the separate Auto Long / Short journal remain independent.

## Recovery and conflicts

When an exact browser partition is absent, the panel may restore its matching
disk checkpoint. It verifies the complete model, identity and SHA-256 digest
before an atomic restore. It never overwrites a partition another window created
in the meantime. Local data takes precedence over a backup. Invalid checkpoints,
different model identities, counter regressions and competing lineages fail
visibly instead of resetting or merging evidence. An older queued upload cannot
replace a newer disk revision.

An independent profile identity lives in a separate IndexedDB database. Clearing
one learner database can therefore recover from disk if that identity remains.
Clearing all extension data, uninstalling the extension or changing its extension
ID can also remove access to that identity. The disk records remain, but the app
does not automatically choose another profile's history. The read-only native
command `oracle.learning.profiles` lists up to 32 saved profile namespaces for
explicit manual recovery; it does not select, import or combine them. Keep the
existing unpacked extension path and Chrome profile when updating.

Native reads do not create an absent learning directory. Backup and recovery
commands do not start a trading owner, arm the extension, obtain credentials or
submit orders. Advisory learning cannot satisfy current-policy exposure gates.

The native upload limit is 2 MiB per checkpoint. The separate HTTP interface has
a 1 MiB request-body limit. Reads return digest-pinned chunks of at most 128 KiB;
recovery refuses an incomplete or changing snapshot.

## Auto Long / Short and future history destinations

The native paper trader separately remembers compatible per-coin models and
resolved samples in its existing private `journal.sqlite3`. It isolates product,
execution, source, features and target. Changing collateral or advice settings
does not erase that memory. Current-policy qualification stays separate. See
[the auto-trading guide](ORACLE-AUTO-TRADING.md#learning-confidence-and-bounded-exposure).

MongoDB time series may be added as another history destination. It is not needed
for the current persistence path. The rebuildable `mongo/load.py` datastore must
never own, clear or overwrite these primary learning records. Remembered outcomes
and model scores do not establish future profitability or calibrated confidence.
