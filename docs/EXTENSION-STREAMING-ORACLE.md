# Streaming Oracle in the Jupiter indicator window

Version: 1.0.0. Delta: implement a causal, bounded online learner and prospective feedback UI.

The extension's existing public-read window now contains a streaming Oracle. It
reuses the validated Pyth stream and bounded one-minute history already owned by
that window. It creates no recorder, inference service, wallet connection or
order path. Existing trading defaults, risk rails and saved chart settings stay
under their existing owners. The Oracle learns from prices while the window is
open; collapsing, hiding or leaving the route stops its feed and controller.

## Target and timing

The new target is **rolling ten-minute close-to-close UP versus NON-UP**, issued
at most once per completed one-minute cutoff. It is separate from the DD/UU
section's next-candle pattern context. Overlapping ten-minute targets are not
independent trials.

If cutoff is 10:00 UTC, the known reference is the closed 09:59–10:00 one-minute
candle's close. The target is the close of 10:09–10:10. The forecast must be
stored within 15 seconds after10:00, before that target exists. A mid-minute
startup waits for the next cutoff; it never backfills supposedly forward calls.

UP means target close is strictly greater than the stored reference. NON-UP
means target close is less than or equal to it. DOWN and exact FLAT remain
separate outcome counts. The complement of P(UP) is P(NON-UP), **not P(DOWN)**.
Binary accuracy includes both DOWN and FLAT as negative events. A probability
exactly 0.5 selects NON-UP for accuracy bookkeeping. Unknown labels are excluded.

A label needs all ten actually completed, contiguous one-minute candles between
cutoff and target. A clock timeout, later quote or developing candle cannot
prove a close. Missing or partial minutes leave the forecast pending. The
label may arrive at most 90 seconds after its target; otherwise it expires
without scoring or training. A late older pending forecast remains eligible
within that grace even if a newer forecast has already resolved. No maximum
resolution watermark discards a legitimate older pending ID.

Forecast creation requires the existing feed's fresh public quote and complete
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
they are engineering settings, not empirically optimized choices. The model
starts with zero coefficients and p=0.5. The stable sigmoid avoids overflow.

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
same event. The existing0–3 indicator alignment is not a probability baseline.
The first 20 resolved samples serve a labeled0.5 baseline while candidate
shadow forecasts continue to collect labels and learn. Cold start therefore
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

The pending ledger is capped at 32 and the recent resolved ledger at 128. The
model and cumulative paired totals remain bounded-size records. Persistent
last-issued watermarks prevent replay after recent-history pruning. Resolution
watermarks describe completed work but do not reject older existing pending
forecasts. The database allows at most 16 partitions and refuses excess capacity
rather than evicting duplicate-prevention history. Browser data clearing or
storage eviction ends that local history; local browser storage is not an
external audit archive or a guarantee against every device failure.

The controller coalesces existing feed snapshots and processes at most once per
second. It creates no extra stream or timer owner. Session-generation fences
reject callbacks from replaced feeds. Collapse/route teardown closes the
controller and its store connection. Storage failures use bounded retry delay
and visible unavailable status. Trading remains read only on this surface.

## Research provenance

The exact approved execution prompt is retained byte-for-byte in
`docs/EXTENSION-STREAMING-ORACLE-PROMPT.md`, SHA-256
`06d3ffc424af00824dd0ea27f0b1fff09e80b4b1dd15ac4bcafa00367623a0d6`.
Prompt optimization was structural-only; it established no benchmark gain.

The parent commissioned a distinct Mongo SK full-suite research run:
`a6585948d2fce4f576ddd5decff3a70908d912580dec95b766f2906dc7948bb4`.
At this implementation checkpoint it is partial: three leaf concepts have
23 draft claims and zero trusted accepted claims. Its failed early gate attempt
and uncertain dispatch/cost state remain parent/research-owned. These are draft
engineering leads, not qualified research or publication proof. Implementation
mathematics and observable browser behavior require their own tests.

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
