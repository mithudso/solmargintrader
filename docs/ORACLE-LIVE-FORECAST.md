# Continuous Oracle strategy forecasts

Version: 1.0.1
Delta: v1.0.0 to v1.0.1; preserve retained horizons, isolate native qualification and harden preference/source/owner boundaries.

The Oracle shows a direction, indicative target price, strategy, evaluation time
and target time. The default predicts the next **10 seconds** and produces a new
forecast every **10 seconds**. The adjacent **Forecast + refresh (seconds)** field
accepts whole numbers from 5 through 300. Apply a value to save it for that coin.
The same value controls both the horizon and evaluation cadence. Preferences
survive browser and service restarts and are separate from research accounts.

While a change is pending, the previous forecast keeps its actual old horizon
and times. The page identifies that hold. It does not relabel an old forecast
as the newly requested horizon. Invalid input and revision conflicts preserve
the unsaved choice and do not overwrite a newer setting.

## Projection and ranking

The evaluator reads the existing Coinbase recorder; it does not start another
recorder or connect a wallet. Fourteen existing price-only strategy cards run
with their pinned card parameters on sampled ten-second reference OHLC bars.
These are separate from the hourly ZEC study and optimized F5 configurations.
A missing bar resets warm-up; no synthetic volume or missing price is inserted.

For the chosen horizon N, the evaluator uses actual one-second sample endpoints
N seconds apart. It takes the median absolute log move from the latest 120
available pairs. The indicative target is:

`observed_reference_price × exp(strategy_exposure_sign × median_absolute_log_move)`

This is a strategy-directed move sized from recent observations. It is not a
fitted expected return, calibrated probability, executable quote or profit claim.
If the measured distance is zero, the price projection is flat; the original
strategy direction remains separately recorded. Actual card parameters and
version accompany every candidate.

Auto ranks candidates using up to 100 recent, timely, prospectively resolved
calls at that exact horizon and instrument. Before outcomes exist it uses the
catalog's reference order and labels the ranking as warming up. Small samples
remain provisional. Picking a strategy displays that strategy even when it
does not qualify for the separate historical Oracle ensemble. Qualification
thresholds and existing research results remain unchanged.

## Continuity and evidence

The independent foreground LaunchAgent runs the evaluator at login and restarts
it after a crash. Fixed scheduled deadlines avoid adding calculation time to
each interval; missed deadlines are skipped without catch-up bursts. The page
reads the saved forecasts through its existing two-second owner refresh.

The last matching forecast survives source outages, gaps and restarts. It is
labelled retained with its original evaluation/target times and age. A healthy
long-interval forecast stays current while its independent source heartbeat
remains fresh. A dead evaluator or stale source cannot keep monitoring green.
Before the first valid source-bound output, the interface reports preparation
instead of manufacturing a price or direction.

State lives below the primary ecosystem home's `live-forecast/<policy-id>/`.
The policy binds the implementation and exact strategy versions/parameters.
The bounded display evaluator keeps issued numeric targets, recent outcomes,
per-strategy last output, and SHA256-bound input traces. Each trace contains
the exact reference OHLC bars, horizon endpoint pairs and entry quote. Private
`ecosystem.forecast.read_trace(home, input_trace_id)` validates the trace hash
for independent numerical replay. Referenced traces remain available when a
long-warm-up strategy retains an earlier output. These working display records
do not replace the immutable historical research or Oracle archives.

## Local API and controls

`GET /api/oracle?instrument=SOL%2FUSD&interval=17s&strategy=rsi` returns the
existing ensemble evidence plus a separate `live_forecast` object. It includes
the exact instrument, selected strategy/version/parameters, price target,
`issued_at`, `target_at`, `horizon_seconds`, `refresh_seconds`, source heartbeat,
`input_trace_id`, actual `source_observed_at`/`source_sampled_at`, and current preference revision. Monitoring recomputes both source ages against its probe-return clock, even for long-horizon frames. Status is `fresh`, `retained`
or `waiting`. Reads never create the evaluator or preferences.

The existing same-origin/CSRF-protected durable action registry accepts
`oracle.forecast.set` with `instrument`, integer `seconds` and
`expected_revision`. A successful action returns the new revision. This changes
only the shared primary market-display preference, even when the browser is
inspecting a different research run. A queued receipt is distinct from an
applied setting. The historical cohort, account strategies, capital, P&L,
activation and signing authority are not changed.

The separate `ecosystem.forecast_service` installer requires an owned macOS
home and an immutable installed environment. It refuses a conflicting service
definition. Uninstall verifies release and retains the display data.

Observer 1.2.1 includes `live_price_forecast` as a ninth required component. It
checks the primary instrument's actual configured cadence, current source and
numeric projection. Reports exclude older samples without that coverage.
Existing Alertlane/native/GitHub transports and their delivery limits remain
as documented in `docs/ORACLEBOT-OPERATIONS.md`.

Initial preference creation publishes a fully initialized private SQLite inode atomically without replacing a concurrent winner. Stale first revisions do not create a database. Existing incompatible stores remain refused. Recorder failures and recovery emit only deduplicated fixed diagnostic states, without source content or paths. Native ensemble evidence keeps its own interval identity; a ten-second provisional projection cannot qualify minute evidence. Persistent service installation requires a stable environment, canonical owner home and confirmed launchd registration.
