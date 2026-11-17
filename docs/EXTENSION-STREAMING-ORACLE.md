# Streaming Oracle in the Jupiter indicator window

Version: 2.0.0. Delta: train all six horizons independently, preserve 0.9 evidence and fence latest shared-input eligibility.

The extension's existing public-read window now contains a streaming Oracle. It
reuses the validated Pyth stream and bounded one-minute history already owned by
that window. It creates no recorder, inference service, wallet connection or
order path. Existing trading defaults, risk rails and saved chart settings stay
under their existing owners. The Oracle learns from prices while the window is
open; collapsing, hiding or leaving the route stops its feed and controller.

## Target and timing

Six independent models predict **rolling 1m/5m/10m/15m/20m/1h close-to-close UP
versus NON-UP**. Each may issue once per fresh completed one-minute cutoff.
Each horizon owns its weights, immutable forecasts, outcomes, serving policy and
paired metrics. Chart selection changes the displayed detail; it does not choose
which models train. These targets remain separate from the DD/UU next-candle
pattern context. Overlapping targets within and across models are not independent
trials. A compact overview shows every horizon; selected detail shows all three
predictors' recent/cumulative metrics.

For the 10m horizon, if cutoff is 10:00 UTC, the known reference is the closed 09:59–10:00 one-minute
candle's close. The target is the close of 10:09–10:10. The forecast must be
stored within 15 seconds after 10:00, before that target exists. A mid-minute
startup waits for the next cutoff; it never backfills supposedly forward calls.

UP means target close is strictly greater than the stored reference. NON-UP
means target close is less than or equal to it. DOWN and exact FLAT remain
separate outcome counts. The complement of P(UP) is P(NON-UP), **not P(DOWN)**.
Binary accuracy includes both DOWN and FLAT as negative events. A probability
exactly 0.5 selects NON-UP for accuracy bookkeeping. Unknown labels are excluded.

Each label needs every actually completed, contiguous one-minute candle between
cutoff and its own target:1/5/10/15/20/60 rows respectively. A clock timeout,
later quote or developing candle cannot
prove a close. Missing or partial minutes leave the forecast pending. The
label may arrive at most 90 seconds after its target; otherwise it expires
without scoring or training. A late older pending forecast remains eligible
within that grace even if a newer forecast has already resolved. No maximum
resolution watermark discards a legitimate older pending ID.

Forecast creation and genuine label learning require the shared stream's fresh
public quote, healthy fixed minute arithmetic and complete
minute-history state. Both exchange and receipt ages must be within 3 seconds.
Seventy-eight contiguous completed minutes warm the fixed indicator features.
History warms features only. No historical labels, protected research holdouts,
TUI paper policies or execution ledgers train this model.

## Learner and fixed transforms

The candidate is an interpretable binary logistic model:

```text
p = sigmoid(b + sum(w[i] * x[i]))
w[i] = clip(w[i] - 0.05 * ((p - y) * x[i] + 0.001 * w[i]), -8, 8)
b = clip(b - 0.05 * (p - y), -8, 8)
```

The intercept is unregularized. The projection and fixed step bound the update;
they are engineering settings, not empirically optimized choices. Each new horizon model
starts with zero coefficients and p=0.5. Existing 10m weights retain their values. The stable sigmoid avoids overflow.

Twenty-two fixed, versioned features include 1/5/10-minute log returns, EMA9/21
gap, MACD histogram, BOP SMA3, normalized RSI, the latest completed candle body,
trailing absolute-return variation and DD/UU context. Each 5/10/15/20-minute shape
adds a descriptive signed group, an explicit known/unknown mask and observed
range position. Price returns and gaps use a fixed 1% scale. Values are bounded
to [-1,1]. Unknown shapes have zero values and a zero known mask.

There is no fitted scaler whose later statistics can change old coordinates.
Each forecast stores its exact transformed vector, cutoff, reference, issued
candidate probability, baseline probability, actually served probability,
serving mode and model sample count. The partition identity binds the feature,
model, target and horizon versions.

When a genuine outcome arrives, the system first scores the **stored issued
probabilities**. It then evaluates the **current** coefficients on the stored
features to compute the training gradient. The earlier forecast probability is
not reused as a stale gradient after intervening updates. A forecast's issued
probabilities and serving mode are never rewritten.

## Baseline, fallback and metrics

Every candidate forecast has a paired, fixed 0.5 no-learning baseline for the
same event. The existing 0–3 indicator alignment is not a probability baseline.
While fewer than 20 genuine outcomes have trained a horizon, each newly issued
forecast serves a labeled 0.5 baseline while the candidate continues collecting
labels and learning. This can span many more than 20 issued forecasts for long
horizons because their feedback is delayed. Cold start therefore
has a path to a trained model.

After at least 30 recent outcomes, a declared heuristic serves the baseline if
the candidate's recent mean Brier score exceeds the baseline by 0.02 and mean
log loss exceeds it by 0.05. This is a recent-underperformance monitor, not a
validated statistical drift detector. It does not reset the model or stop
shadow learning. The candidate can recover as new genuine feedback arrives.
Invalid inputs abstain. Corrupt persisted state or unavailable storage pauses
learning visibly; the system does not silently replace evidence with a new
apparently trained model.

The interface separately names **candidate shadow**, **actually served** and
**fixed 0.5** metrics. It shows resolved, pending and expired counts, trained
samples, outcome counts, and recent/cumulative binary accuracy, Brier score and
log loss. All three predictors use the same resolved forecast cohort. With no
resolved outcomes, metrics are unavailable rather than fabricated 0% accuracy.

Brier is mean `(p-y)^2`. Log loss is mean `-[y*log(p)+(1-y)*log(1-p)]`, with a
numerical probability floor/ceiling of 1e-9 for scoring. Lower probability-quality
scores are better on this cohort. These scores combine several properties;
they are not pure calibration measures. Candidate probabilities are explicitly
uncalibrated shadow estimates. No measured improvement, profit, fill quality or
calibrated confidence is promised. Historical label-training count is always 0.

## Atomic persistence and lifecycle

A separate native IndexedDB database, `solmargintrader-streaming-oracle`, has
schema version 1 and one `partitions` object store. It does not alter the trading
journal. The partition key binds market symbol, catalog market address and feed
ID, Pyth stream/oracle price basis, horizon and feature/model/target versions.

One overlapping-scope readwrite transaction reads the partition, evaluates a
synchronous reducer, and commits model weights, pending forecasts, counters,
recent outcomes and issue/resolution watermarks together. It waits for the
transaction's completed result. There is no network request or asynchronous
control gap inside the transaction. Concurrent windows read the first window's
stored same-cutoff forecast instead of recomputing it under newer weights.

Each pending ledger is capped at 64 and each recent resolved ledger at 128. The
model and cumulative paired totals remain bounded-size records. Persistent
last-issued watermarks prevent replay after recent-history pruning. Resolution
watermarks describe completed work but do not reject older existing pending
forecasts. Sixty one-minute-spaced 1h targets plus 90s outcome lateness and an
issuance margin fit 64 pending records. The database allows 96 logical partitions,
room for 16 complete six-horizon source groups. Capacity is a global bound, not
a reservation per market; partial old groups can occupy slots. New-partition
capacity failures do not stop updates to existing healthy partitions. No evidence
is evicted to make room. These limits are engineering bounds, not measured
optimal settings. Browser data clearing or
storage eviction ends that local history; local browser storage is not an
external audit archive or a guarantee against every device failure.

The schema/model/feature/target version strings and exact 600-second key remain
unchanged. Genuine 0.9 ten-minute weights, pending IDs, probabilities and scores
remain usable without a schema migration or retrospective rewrite. New horizons
start prospectively with historicalTrainingSamples=0.

The controller coalesces existing feed snapshots and processes all six independent
transactions at most once per second. It creates no extra stream or timer owner. Session-generation fences
reject callbacks from replaced feeds. Collapse/route teardown closes the
controller and its store connection. Storage failures use bounded retry delay
and visible unavailable status. A source identity change immediately clears the
previous display while its new partition loads. Unknown identities, failed loads,
invalid shared-minute input and suspension cannot retain a prior active
prediction. Same-source historical metrics remain visible with explicit labels. Historical evidence appears only after the exact current partition has
loaded, and stale same-source predictions are explicitly labeled historical.
Fresh valid input reloads persisted learning; display invalidation does not
reset the learner. Reducers and delayed completions consult the latest shared
snapshot, so an older live completion cannot reactivate a same-source stale
view. A stale observation marks every row unavailable immediately, without
clearing verified same-source history.

The feed keeps one authoritative minute ledger across chart intervals. A 1m chart
reuses that exact history request. Larger selected charts have their own history;
changing them aborts obsolete chart reads without replacing the socket or shared
minute ledger. Chart loading/failure/indicator arithmetic cannot poison healthy
shared-minute learning. Invalid shared source/quote/minute arithmetic still
withholds all six. Per-horizon storage failures and fallback stay independent.
The minute-close Oracle and chart are read-only analysis. Separate controls in the panel can operate the shared paper session.

## Research provenance

The exact approved execution prompt is retained byte-for-byte in
`docs/EXTENSION-STREAMING-ORACLE-PROMPT.md`, SHA-256
`06d3ffc424af00824dd0ea27f0b1fff09e80b4b1dd15ac4bcafa00367623a0d6`.
Prompt optimization was structural-only; it established no benchmark gain.

The parent commissioned a distinct Mongo SK full-suite research run:
`a6585948d2fce4f576ddd5decff3a70908d912580dec95b766f2906dc7948bb4`.
The probability/scoring leaf now has 16/16 SUPPORTED source-method claims under
trusted completed job`pub:1062e08eeed03535f5fa9af230e37e23`. The concept
`c:ten-minute-market-probability-scoring-calibration-and-baselines`, revision 50,
records verified completion SHA-256
`def78224c361cd7de96ab44da2fe5df40e9f8c7c78027d62edf53c5924de5520`.
Its gate-v4 receipt is
`art:4103e5f516ac34787bb21e96a5743c35aeb13b69dd8015ba0abc423f8f06e4a0`.
The actual gate used gpt-6.1-sol at medium effort. The full suite remains partial;
pack compilation returned HTTP 524 and its outcome requires reconciliation.
Accepted source-method claims support scoring/calibration methodology and its
limits. They do not validate this application's accuracy, calibration,
profitability or full-suite completion. Application mathematics and observable
browser behavior have separate engineering tests.

Primary references consulted for the design:

- https://riverml.xyz/latest/api/evaluate/progressive-val-score/
- https://moa.cms.waikato.ac.nz/prequential-cross-validation-evaluation/
- https://scikit-learn.org/stable/modules/linear_model.html#logistic-regression
- https://scikit-learn.org/stable/modules/sgd.html
- https://scikit-learn.org/stable/modules/model_evaluation.html
- https://scikit-learn.org/stable/modules/calibration
- https://scikit-learn.org/stable/common_pitfalls.html
- https://developer.mozilla.org/en-US/docs/Web/API/IDBTransaction
- https://w3c.github.io/IndexedDB/

The River/MOA references describe delayed/prospective test-before-train ordering.
The sklearn references define logistic SGD and probability-quality metrics.
The IndexedDB specification describes atomic commits and serialization of
readwrite transactions with overlapping scopes. None establishes a profitable
market model or validates this feed's parameter/drift thresholds.

## Verification and remaining acceptance

The owning Node tests check analytical sigmoid/gradient/score values, delayed
current-weight updates, flat/unknown denominators, immutable issued records,
older pending gap fill, prefix/future mutation, cold start/fallback, pruning,
source isolation and controller/restart/duplicate behavior. The native Chrome
gate separately exercises actual IndexedDB, two extension contexts, visible
learning/metrics, abort and collapse/reopen recovery. Its accelerated synthetic
clock and market are explicitly fixture evidence, not public-market accuracy.
The public gate may legitimately show zero trained/resolved forecasts during
its bounded run. Source tests, fixture behavior, public reads and later canonical
loaded acceptance are distinct gates.

Candidate counts, completed checks, exact loaded module hashes and final
delivery limitations belong in the delivery receipt. A pushed draft or passing
source tests alone is not canonical installation or a merged release.

The 0.10 candidate passed 598/598 extension tests and root JavaScript checks.
Its direct tests cover all six exact target windows, causal-prefix/future
mutation, gaps/partials/expiry, trained 0.9 key/weights/pending/score compatibility,
1h pending beyond 32, all-six deselected learning, independent fallback/capacity
and both sides of the same-source completion race. Independent read-only review
found no corroborated Medium-or-higher issue across all ten runtime files,
passed 65 focused cases and exactly matched 121 complete old/new ten-minute
state transitions (121 issued,111 trained,10 pending).

The complete native Chrome fixture passed 27/27 and actual public gate passed 8/8
with exact loaded 0.10.0 asset hashes. Two actual contexts produced 82 immutable
forecasts per horizon; observed trained counts were 81/77/72/67/62/22 for
1m/5m/10m/15m/20m/1h, with 60 genuine pending 1h forecasts. Selected-chart
failure left all six learning on the same sockets. Native abort/reopen and
unknown outcomes preserve each model's separate evidence. A quarantined native
store refused partition 97 without evicting records or blocking existing updates.

A separate quarantined native test executes the frozen 0.9 model source inside
Chrome, preserves its 21-sample ten-minute weights/pending/scores exactly, and
resumes to 22 samples. Its actual DOM retains historical counts immediately on
stale input and after all six earlier commits complete. The original Node-made
golden JSON had one score-field difference under Chrome's math and was correctly
refused. The browser reference therefore uses the original model in its own
engine; no validation threshold, stored score or production equation was relaxed.
Earlier 25/27 and 6/7 harness receipts remain preserved. The first chart-refusal
assertion incorrectly required a fixed error label while fresh quotes can change
that withheld chart status to backfilling; the final assertion checks non-live
chart status and unavailable signals while all six models remain independent.

Receipts are under
`/Users/mitch/.local/state/oracle-all-timeframes-2414/browser-fixture-final/` and
`/Users/mitch/.local/state/oracle-all-timeframes-2414/browser-public-first/`.
The real public fresh profile shows six initialized models with zero trained/
resolved outcomes, without fabricated accuracy. Synthetic counts and scores
prove implementation/accounting, not market accuracy, calibration or profit.
Parent final-head CI, merge and canonical installed-profile migration remain
separate gates. The historical approved prompt remains byte-identical.
