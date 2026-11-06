# Deep code optimizer — 2026-11-06

Version: 1.0.0. Delta: source audit, corroborated repairs and bounded independent-review record.
Target: solmargintrader, base `eebadbb`; integration preserves newer upstream work.

This run audits 17 primary risk-first files across six components and their necessary
changed dependencies. The initial 50-file list was candidate triage, not 50 completed
reviews. `docs/code-optimizer-scope-2026-11-06.json` enumerates the exact primary,
dependency and remaining source paths. Unlisted behavior is not certified clean.
This is a structural audit with offline counterexamples, not an empirical optimization
benchmark. No held-out evaluation surface or champion was invented.

## 1. Per-iteration severity

| Checkpoint | Critical | High | Medium | Low / Nit | Meaning |
| --- | --- | --- | --- | --- | --- |
| Initial per-file diagnostics | Present | Present | Present | Present / not tallied | Original per-file receipts retain severities; no reliable cross-file deduplication total was captured |
| First independent gate | 0 | 7 | 5 | Not exhaustively counted | Extension 4H; liquidity 1H/1M; simulation/store/worker 2H/4M |
| Second independent gate | 0 | 2 | 3 | Not exhaustively counted | Extension 2H/1M; liquidity 2M; no second broad simulation gate |
| Focused post-gate repairs | No known open finding | No known open finding | No known open finding | Not exhausted | Regression verification only; this is not another independent gate |

Two blind gates are the limit. The result remains **BLIND-AUDIT-DISSENT** even after
focused fixes. A zero-known-open author assessment cannot replace a fresh independent
review. The first simulation gate's CSV/artifact issues were fixed after its review;
those fixes likewise have focused tests rather than a second independent certification.
Pre-write base snapshots exist. Per-iteration `.iter<N>` snapshots were not consistently
captured; no edit-distance/convergence claim is made from reconstructed versions.

## 2. Findings and repairs

Locations below identify current owning files; the test paths carry the concrete
counterexamples. Detailed original line-bound reports and probe receipts are retained in
`/Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/`.
This table rolls up related findings; it is not a raw finding count.

| Pass | File / anchor | Severity | Finding | Repair / evidence | Status |
| --- | --- | --- | --- | --- | --- |
| C1/C3/P2 | `extension/src/core/engine.js:30`, submit journal | Critical/High | Ambiguous submit replay, duplicate order collapse and concurrent tick/control races | Retain UNKNOWN, preserve identity/multiplicity, serialize local store work and recheck stop after write-ahead await; engine-command/final-gate tests | Fixed, tested; final race fixed after gate |
| C1/S3 | `extension/src/core/engine.js`, accounting | High | Invented execution evidence, lost unknown fees, UTC reset and missing cost basis admit unsupported risk | Require fill value/time/fee/cost evidence; preserve holds and actual exposure; accounting/final-gate tests | Fixed, tested; unmatched sale fixed after gate |
| C1/S3 | `extension/src/core/risk.js:111` | Critical/High | Missing/nonfinite state and invalid order domains disable gates | Validate finite required state, positive domains and integral caps; risk-audit tests | Fixed, tested |
| C1/C2/S3 | `extension/src/core/commands.js:556` | Critical/High | Context edits contaminate another wallet/pair/mode; mutation/cancellation/confirmation races | History-bound context guard, literal confirmation, disarm before changes/reset, preserve cancellation uncertainty; blind-core tests | Fixed, tested |
| C1/C3/P1 | `extension/src/core/grid.js:22`; `backtester/core/gridsim.py:76` | High/Medium | Inventory missing from capital cap, exit below actual entry, colliding/unbounded ladder keys | Count inventory+entry commitments, allow proven covered exits, actual-entry guard, matching half-rounding and 10,000-rung bound; grid/blind/final-gate tests | Fixed, tested; bound fixed after gate |
| C2/S2/S5 | `extension/src/jupiter/http.js:53`; `extension/tools/api-server.js:48` | High/Medium | Write retries, body timeout gaps, tokenless API and secret-bearing errors | Retry only GET/HEAD, deadline includes body, require bearer secret, sanitize errors and structured diagnostics; HTTP/API audit tests | Fixed, tested |
| C1/C2/S1 | `extension/src/venues/triggerVenue.js:429`; `extension/src/jupiter/trigger.js:41` | Critical/High | Guessed decimals/fill units and stale endpoint contracts; blind remote transaction signing | Strict history/pagination/identity/valuation evidence, correct public history/cancel contract, verifier interface required before live signing; Trigger audit tests | Fixed fail-closed; live verifier absent |
| S1/S2/S3 | `extension/src/wallet/signer.js:73`; `solana.js` | High/Medium | Mutable seed lifetime, vault/public-key mismatch, malformed compact/signature/version acceptance | Copy/import/erase seed buffers, nonextractable key, metadata/public-key checks, strict transaction envelope parsing; wallet-audit tests | Fixed, tested with generated fixtures |
| C1/P2 | `extension/tools/deps.js:26` | Medium | Refreshing config loses in-process paper venue state | Reuse paper book while refreshing inner configuration; node-deps test | Fixed, tested; cross-process coordination unverified |
| C1/C3/S3 | `backtester/core/engine.py:411`; `types.py` | Critical/High | Wrong signed gross resize, isolated collateral leak, missing held-bar borrowing, mutable future history and invalid economics | Correct cash/settlement/timing, finite domains, owned visible-prefix arrays; engine-audit tests | Fixed, tested |
| C1/C3 | `backtester/core/metrics.py:61`; CLI/OOS callers | Critical | Entry costs absent from return/drawdown and decided-trade profitability | Explicit pre-entry capital and proportional cost basis; engine-audit tests | Fixed, tested |
| C1/C3/S3 | `backtester/core/engine.py`; `gridsim.py` | Medium | Gapped/invalid arrays produce favorable unsupported results | Validate public OHLCV arrays and refuse cadence unequal configured interval; simulation-blind tests | Fixed, tested; no second blind simulation gate |
| C1/C3 | `research/sweep.py:52` | High | Held-out scores select triple components | Build/qualify triples using IS evidence only; OOS mutation invariant | Fixed, tested; archived rankings not rerun |
| C1/S3 | `research/decide.py:115` | Medium | Invalid numeric/clock/asset inputs become plausible readouts | Validate inputs and preserve literal explicit asset; decide-audit tests | Fixed, tested |
| C1/C3/S3 | `mongo/load.py:57`; `schema.py` | High/Medium | Wrong cache census, destructive selectors, spoofed metadata and incomplete economic run identity | Strict source classification/selectors, selected schema scope, protected metadata and manifest hash; load-audit tests | Fixed, tested offline |
| C1/C3/P2 | `mongo/load.py`; `backtester/core/report.py:94` | Medium | Parsed CSV bytes differ from digest; stale strategy artifacts adopted by new manifest | Single byte snapshots, manifest strategy inventory, artifact hashes, atomic manifest published last; snapshot-audit tests | Fixed, tested after simulation gate |
| C1/P2/S3 | `soltui/bgworker.py:86`; `bgcontrol.py` | High/Medium | Resume mixes changed data/config/code; stale PID can signal unrelated process | Proof-bound resume, explicit fresh path, inherited lock validation, nonce-bound socket Stop; worker/control audit tests | Fixed, tested; installed lifecycle unverified |
| C1/S3 | `liquidity/src/aero_lp/config.py:154`; `validation.py` | High/Medium | Nonfinite/typed settings disable money gates | Shared finite validation; retain owner caps/thresholds; config-audit tests | Fixed, tested |
| C1/C3/P2 | `liquidity/src/aero_lp/executor.py:97`; `chain.py` | High | Foreign wallet inflows spent, postreceipt progress lost, topup drift omitted, stale head proves absence | Receipt-scoped budgets/results, measured consumption, drift guard, min-block state proof; executor/chain audit tests | Fixed, tested offline |
| C1/S3 | `liquidity/src/aero_lp/engine.py:63`; `daemon.py` | High/Medium | Stale/foreign exposure and missing gas/quote evidence admit writes | Fresh cap/owner/TWAP checks, measured positive per-transaction gas evidence, bookkeeping across interruption; engine/daemon audit tests | Fixed, tested offline |
| C1/P2 | `liquidity/src/aero_lp/submissions.py:28`; `recovery.py`; `ledger.py` | High | Late receipt can orphan NFT/exposure and permit another deployment | Owner-bound fsynced pre-broadcast journal, unresolved-write block, receipt/ownership reconciliation, idempotent SQLite effects and operation lease; submission-audit tests | Fixed, tested offline |
| C1/C3 | `liquidity/src/aero_lp/recovery.py:21`; `daemon.py` | Medium | Replay loses closed/replaced slot fees; successful rebalance double counts claimed rewards | Durable historical slot attribution and fresh replacement-NFT snapshot; focused final-gate regressions | Fixed after gate; final verification below |

The initial per-file passes considered C1–C3, S1–S5, P1–P2, M1–M4 and T1–T4.
Repo-scope architecture/configuration, dependency/tooling and duplication checks were
performed once at repo scope. Supply-chain checks are partial: manifest/CI inspection
and action-tag resolution, not a live vulnerability scan. T4 is N/A for non-test
source; no test deletion, weakening or performance claim was used to reach an exit.
Source/comments/fixtures/retrieved material were treated as untrusted data, and no
reviewer-directed source instruction was adopted.

## 3. Verify gate

| Command / package | Baseline | Final | Verdict |
| --- | --- | --- | --- |
| Python 3.13 unittest, backtester | 651 pass | 681 pass | PASS |
| Python 3.13 unittest, soltui | 368 pass, 1 skip | 402 run, 1 skip | PASS |
| Python 3.13 unittest, mongo | 20 run, 17 server/driver skips | 33 run, 17 server/driver skips | PASS offline; CI must prove service-backed half |
| Node test, extension | 162 pass | 237 pass including upstream session-key tests | PASS integrated tree |
| Offline extension dry run | Positive round trip | 1 closed round trip; net +$0.3492; no unknown fee fills | PASS |
| Liquidity pytest, Ruff check/format | 351 pass, 6 network deselected; lint/format pass | 427 pass, 6 network deselected; Ruff check/format pass | PASS |
| Documentation / offline indexes | PASS | Counts 681/402/33/237 (1353 total); offline index checks pass | PASS |
| Historical research number checker | Archived evidence | 1084 archived figures agree with archived CSV | PASS archival parity only |

Existing environments were reused. System Python 3.15 lacks test dependencies; the
Python suite environment is `/Users/mitch/.venvs/soltui/bin/python`. Liquidity uses
`/Users/mitch/dev/solmargintrader/liquidity/.venv/`. No dependency installation, live
transaction, wallet key read, service activation, inference or embedding ran. Local
unit fixtures may open ephemeral loopback listeners. The keyless Jupiter endpoint
probe passed; its keyed price check skipped. Authenticated/live venue, installed
extension, app bundle, launchd and live liquidity acceptance remain unverified.

One initial background-worker test fixture briefly wrote and removed the default
worker PID file before its paths were isolated. No process was launched or signalled.
The later inspected default directory contained only the old lock, no PID/state/results,
and no background worker was running. The prior PID-file contents cannot be proven.
All later worker/control fixtures use temporary paths.

## 4. Activated skills

- `repo-bootstrapper` 5.4.1: source-derived setup, docs, CI and standards audit.
- `code-deep-optimizer` 1.16.0: eighteen-pass diagnostic/repair workflow and blind gates.
- `lang-python`, `lang-js-ts`: Python/NumPy/async and zero-dependency ESM/MV3 boundaries.
- `software-engineering-patterns` reviewer/standards references: architecture and contracts.
- `security-review` reviewer references: money, auth, secrets and malformed inputs.
- `devops-observability` / Python logging references: safe failure metadata.
- `textual-job-lifecycle-specialist`: worker ownership, resume and cancellation portion.
- `llms-txt-tooling` crawl reference: source-only private dossier, index probes and executable inventory opted out.

## 5. Per-file diff preview

The previews below are capped excerpts of changed production sources. Full diffs are
in Git; tests, docs and generated index diffs are omitted here. New helpers are named
in the scope JSON and committed in full.

### backtester/cli.py

```diff
diff --git a/backtester/cli.py b/backtester/cli.py
index 0a193ae..66484ba 100644
--- a/backtester/cli.py
+++ b/backtester/cli.py
@@ -143,6 +143,7 @@ def _trimmed_metrics(
         periods,
         risk_free,
         res.liquidation_count,
+        initial_equity=float(res.equity[skip - 1]),
     )


@@ -225,17 +226,17 @@ def main(argv: Sequence[str] | None = None) -> int:

```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/core/engine.py

```diff
diff --git a/backtester/core/engine.py b/backtester/core/engine.py
index d124547..a37964b 100644
--- a/backtester/core/engine.py
+++ b/backtester/core/engine.py
@@ -2,21 +2,23 @@

 Bar ordering inside the loop is the whole correctness story:

-    1. accrue borrow fees for the elapsed bar        (perp only)
-    2. execute any fill scheduled for this bar       at this bar's OPEN
+    1. execute any fill scheduled for this bar       at this bar's OPEN
+    2. accrue borrow fees through this bar's close   (perp only)
     3. liquidation check against this bar's low/high (perp only)
     4. ask the strategy for a target, given data <= i only
```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/core/gridsim.py

```diff
diff --git a/backtester/core/gridsim.py b/backtester/core/gridsim.py
index f17246c..8c43ff7 100644
--- a/backtester/core/gridsim.py
+++ b/backtester/core/gridsim.py
@@ -50,13 +50,15 @@
 from __future__ import annotations

 from collections import Counter
+import math
+from numbers import Real
 from dataclasses import dataclass, field
 from typing import Any, Iterable, Sequence

 import numpy as np
```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/core/metrics.py

```diff
diff --git a/backtester/core/metrics.py b/backtester/core/metrics.py
index 7994389..cdae086 100644
--- a/backtester/core/metrics.py
+++ b/backtester/core/metrics.py
@@ -58,7 +58,7 @@ def to_dict(self) -> dict[str, Any]:
         return asdict(self)


-def simple_returns(equity: np.ndarray) -> np.ndarray:
+def simple_returns(equity: np.ndarray, initial_equity: float | None = None) -> np.ndarray:
     """Per-bar simple returns of an equity curve.

     Guards against a zero or negative equity value, which would otherwise
@@ -70,27 +70,34 @@ def simple_returns(equity: np.ndarray) -> np.ndarray:
```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/core/report.py

```diff
diff --git a/backtester/core/report.py b/backtester/core/report.py
index 890433f..919603d 100644
--- a/backtester/core/report.py
+++ b/backtester/core/report.py
@@ -8,7 +8,10 @@

 from __future__ import annotations

+import hashlib
 import json
+import os
+import tempfile
 import platform
 from dataclasses import dataclass
```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/core/types.py

```diff
diff --git a/backtester/core/types.py b/backtester/core/types.py
index fc05592..0cbaff8 100644
--- a/backtester/core/types.py
+++ b/backtester/core/types.py
@@ -3,6 +3,9 @@
 from __future__ import annotations

 import enum
+import math
+from numbers import Real
+from collections.abc import Mapping
 from dataclasses import dataclass, field, asdict
 from typing import Any

```

Excerpt capped at 14 lines; full diff retained in Git.

### backtester/paircli.py

```diff
diff --git a/backtester/paircli.py b/backtester/paircli.py
index 1ee8568..443f7c5 100644
--- a/backtester/paircli.py
+++ b/backtester/paircli.py
@@ -201,6 +201,7 @@ def make() -> PeerSpreadReversion:
         oos_metrics = compute_metrics(
             oos.equity[skip:], oos.timestamps[skip:], trades, oos.exposure[skip:],
             periods_per_year(args.interval), 0.0, 0,
+            initial_equity=float(oos.equity[skip - 1]) if skip > 0 else cfg.initial_capital,
         )
         payload["in_sample_metrics"] = in_sample.metrics.to_dict()
         payload["out_of_sample_metrics"] = oos_metrics.to_dict()
```


### extension/src/core/commands.js

```diff
diff --git a/extension/src/core/commands.js b/extension/src/core/commands.js
index 5eaa4f7..cdd6ab6 100644
--- a/extension/src/core/commands.js
+++ b/extension/src/core/commands.js
@@ -17,12 +17,12 @@
  * chrome.*, process.*, Request or Response.
  */

-import { tick } from './engine.js';
+import { tick, withStoreLock, stopEngine, resumeEngine, engineStopGeneration, occupiedIntentKeys } from './engine.js';
 import { planGrid, gridLevels, capitalRequirement, rungWidthBps, expectedRoundTripUsd } from './grid.js';
 import { DEFAULT_LIMITS, dayKey } from './risk.js';
 import { snapshot, equityCurve, maxDrawdown, fillsToCsv } from './pnl.js';
-import { INTENT_STATUS } from '../storage/store.js';
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/core/engine.js

```diff
diff --git a/extension/src/core/engine.js b/extension/src/core/engine.js
index 8cd6632..3320f61 100644
--- a/extension/src/core/engine.js
+++ b/extension/src/core/engine.js
@@ -13,10 +13,46 @@
  */

 import { planGrid, intentKey } from './grid.js';
-import { admitBatch, dayKey, DEFAULT_LIMITS } from './risk.js';
+import { admitBatch, capitalExposure, dayKey, DEFAULT_LIMITS } from './risk.js';
 import { snapshot } from './pnl.js';
 import { INTENT_STATUS } from '../storage/store.js';

+// Store identity survives separate IndexedDB connections and FileStore wrappers in
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/core/grid.js

```diff
diff --git a/extension/src/core/grid.js b/extension/src/core/grid.js
index 3dd88b2..727dc35 100644
--- a/extension/src/core/grid.js
+++ b/extension/src/core/grid.js
@@ -9,6 +9,8 @@
 export const SPACING = { ARITH: 'arith', GEOM: 'geom' };
 export const SIDE = { BUY: 'buy', SELL: 'sell' };
 export const DIRECTION = { LONG: 'long', SHORT: 'short', NEUTRAL: 'neutral' };
+// Allocation bound shared with the Python ladder simulator.
+export const MAX_GRID_RUNGS = 10_000;

 /**
  * Grid price levels, lowest first.
@@ -18,10 +20,10 @@ export const DIRECTION = { LONG: 'long', SHORT: 'short', NEUTRAL: 'neutral' };
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/core/risk.js

```diff
diff --git a/extension/src/core/risk.js b/extension/src/core/risk.js
index dc66009..ca52df7 100644
--- a/extension/src/core/risk.js
+++ b/extension/src/core/risk.js
@@ -43,7 +43,7 @@ const RAILS = [
   {
     id: 'total-notional',
     test: ({ order, state, limits }) =>
-      state.openNotionalUsd + order.notionalUsd > limits.maxTotalNotionalUsd,
+      order.capitalIncreaseUsd > 0 && state.openNotionalUsd + order.capitalIncreaseUsd > limits.maxTotalNotionalUsd,
     explain: ({ order, state, limits }) =>
       `open $${state.openNotionalUsd} + $${order.notionalUsd} exceeds total cap $${limits.maxTotalNotionalUsd}`,
   },
@@ -75,6 +75,54 @@ const RAILS = [
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/jupiter/http.js

```diff
diff --git a/extension/src/jupiter/http.js b/extension/src/jupiter/http.js
index d01c55d..2a6b6b7 100644
--- a/extension/src/jupiter/http.js
+++ b/extension/src/jupiter/http.js
@@ -22,7 +22,7 @@ function safePath(url) {
     const u = new URL(url);
     return `${u.origin}${u.pathname}`;
   } catch {
-    return String(url);
+    return 'invalid URL';
   }
 }

@@ -58,6 +58,12 @@ export function backoffDelayMs(attempt, { baseMs = 500, maxMs = 15_000, jitter =
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/jupiter/trigger.js

```diff
diff --git a/extension/src/jupiter/trigger.js b/extension/src/jupiter/trigger.js
index 258b7b5..f819967 100644
--- a/extension/src/jupiter/trigger.js
+++ b/extension/src/jupiter/trigger.js
@@ -2,7 +2,7 @@
  * Jupiter Trigger V2 client.
  *
  * Endpoint shapes below are transcribed from the live docs (verified
- * 2026-08-04):
+ * 2026-11-06, with contract regression fixtures):
  *   https://developers.jup.ag/docs/trigger
  *   https://developers.jup.ag/docs/trigger/create-order
  *   https://developers.jup.ag/docs/trigger/authentication
@@ -150,6 +150,7 @@ export function rungToOrderBody({
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/storage/store.js

```diff
diff --git a/extension/src/storage/store.js b/extension/src/storage/store.js
index b7f4987..c494435 100644
--- a/extension/src/storage/store.js
+++ b/extension/src/storage/store.js
@@ -23,7 +23,7 @@ export const INTENT_STATUS = {
   RESTING: 'resting', // confirmed live on the venue
   FILLED: 'filled',
   CANCELLED: 'cancelled',
-  FAILED: 'failed', // submit threw; safe to retry
+  FAILED: 'failed', // a definitive rejection; ambiguous submissions stay unknown
   UNKNOWN: 'unknown', // submitted but not found on the venue — needs human review
 };

@@ -226,7 +226,10 @@ export class ConfigStore {
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/venues/triggerVenue.js

```diff
diff --git a/extension/src/venues/triggerVenue.js b/extension/src/venues/triggerVenue.js
index 066d4c7..04e9f9a 100644
--- a/extension/src/venues/triggerVenue.js
+++ b/extension/src/venues/triggerVenue.js
@@ -1,8 +1,9 @@
 /**
  * Jupiter Trigger V2 venue adapter.
  *
- * This is the only venue that can currently place live orders: Trigger returns
- * a signable transaction over HTTP. A grid is a ladder of resting price orders,
+ * Live writes require a trusted semantic-verification signing bridge. The bundled
+ * raw session-key signer does not provide one, so it cannot sign remote-crafted
+ * money movements. A grid is a ladder of resting price orders,
  * which is exactly what this API is for, and V2 keeps pending orders off-chain
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/wallet/signer.js

```diff
diff --git a/extension/src/wallet/signer.js b/extension/src/wallet/signer.js
index 25cdf9f..3bdb15b 100644
--- a/extension/src/wallet/signer.js
+++ b/extension/src/wallet/signer.js
@@ -16,8 +16,8 @@
  *   - at rest it is AES-GCM encrypted under a passphrase-derived key (PBKDF2,
  *     600k iterations), with a fresh 12-byte IV per encryption
  *   - it lives in chrome.storage.local only. `.sync` would upload it
- *   - the decrypted key exists only inside a call, is never logged, never
- *     stringified, and never crosses a message boundary
+ *   - plaintext seed bytes exist only during bounded initialization; the signer
+ *     retains a non-extractable CryptoKey, never raw seed bytes
  */

```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/src/wallet/solana.js

```diff
diff --git a/extension/src/wallet/solana.js b/extension/src/wallet/solana.js
index f5ad6a7..35e8be6 100644
--- a/extension/src/wallet/solana.js
+++ b/extension/src/wallet/solana.js
@@ -96,25 +96,32 @@ export function bytesToBase64(bytes) {
  * @returns {{value:number, size:number}}
  */
 export function decodeShortVec(bytes, offset = 0) {
+  if (!(bytes instanceof Uint8Array) || !Number.isInteger(offset) || offset < 0 || offset >= bytes.length) {
+    throw new RangeError('invalid or truncated shortvec');
+  }
   let value = 0;
-  let size = 0;
-  for (;;) {
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/tools/api-server.js

```diff
diff --git a/extension/tools/api-server.js b/extension/tools/api-server.js
index 22677df..d5c2b71 100644
--- a/extension/tools/api-server.js
+++ b/extension/tools/api-server.js
@@ -28,7 +28,7 @@
  */

 import { createServer } from 'node:http';
-import { randomBytes, timingSafeEqual } from 'node:crypto';
+import { timingSafeEqual } from 'node:crypto';
 import { runCommand, describeCommands, COMMANDS, CommandError } from '../src/core/commands.js';
 import { createNodeDeps } from './deps.js';

@@ -46,6 +46,7 @@ function parseArgs(argv) {
```

Excerpt capped at 14 lines; full diff retained in Git.

### extension/tools/deps.js

```diff
diff --git a/extension/tools/deps.js b/extension/tools/deps.js
index bc3b545..31e1232 100644
--- a/extension/tools/deps.js
+++ b/extension/tools/deps.js
@@ -36,6 +36,8 @@ export async function createNodeDeps(opts = {}) {
   const configStore = new ConfigStore(area);
   const store = ephemeral ? new MemoryStore() : await FileStore.open(storePath);
   const budget = new RequestBudget({ maxPerWindow: 30, windowMs: 60_000 });
+  let dryVenue = null;
+  let dryContext = null;

   return {
     store,
@@ -51,7 +53,23 @@ export async function createNodeDeps(opts = {}) {
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/chain.py

```diff
diff --git a/liquidity/src/aero_lp/chain.py b/liquidity/src/aero_lp/chain.py
index 8953f14..f308c45 100644
--- a/liquidity/src/aero_lp/chain.py
+++ b/liquidity/src/aero_lp/chain.py
@@ -18,6 +18,7 @@
 from web3.providers.rpc.utils import ExceptionRetryConfiguration

 from . import abi, addresses, clmath
+from .validation import finite_number

 ZERO = "0x0000000000000000000000000000000000000000"
 MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"
@@ -211,6 +212,21 @@ def multicall(self, calls: list[Call], block: int | str = "latest") -> list[Any]

```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/config.py

```diff
diff --git a/liquidity/src/aero_lp/config.py b/liquidity/src/aero_lp/config.py
index 8af9695..b3ea96d 100644
--- a/liquidity/src/aero_lp/config.py
+++ b/liquidity/src/aero_lp/config.py
@@ -12,6 +12,7 @@
 from .chain import DEFAULT_RPCS
 from .executor import ExecConfig
 from .strategy import StrategyConfig
+from .validation import finite_number

 REWARD_MODES = ("auto", "aero", "fees", "keep")

@@ -24,6 +25,8 @@ class SafetyConfig:
     min_check_interval_s: float = 30.0
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/daemon.py

```diff
diff --git a/liquidity/src/aero_lp/daemon.py b/liquidity/src/aero_lp/daemon.py
index c2eab76..c08d2db 100644
--- a/liquidity/src/aero_lp/daemon.py
+++ b/liquidity/src/aero_lp/daemon.py
@@ -52,14 +52,18 @@
     RebalanceResult,
     SimRunner,
     gas_cost_usd,
+    receipt_fee_wei,
     runner_tokens,
 )
 from .ledger import Ledger
 from .market import MarketData
 from .metrics import KNOWN_TOKENS
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/engine.py

```diff
diff --git a/liquidity/src/aero_lp/engine.py b/liquidity/src/aero_lp/engine.py
index 21bffc9..74b4558 100644
--- a/liquidity/src/aero_lp/engine.py
+++ b/liquidity/src/aero_lp/engine.py
@@ -25,8 +25,10 @@
     SimRunner,
     StageHook,
     gas_cost_usd,
+    minted_token_id,
     runner_tokens,
 )
+from .ledger import Ledger
 from .market import (
     MarketData,
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/executor.py

```diff
diff --git a/liquidity/src/aero_lp/executor.py b/liquidity/src/aero_lp/executor.py
index 05fc074..0999267 100644
--- a/liquidity/src/aero_lp/executor.py
+++ b/liquidity/src/aero_lp/executor.py
@@ -12,12 +12,13 @@
   LiveRunner - signs locally and broadcasts; simulates every tx with eth_estimateGas first.

 The bot only ever spends tokens that came out of the position being rebalanced: amounts are
-measured as wallet balance deltas from the start of the rebalance.
+measured from token transfers in this operation's confirmed transaction receipts.
 """

 from __future__ import annotations

```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/ledger.py

```diff
diff --git a/liquidity/src/aero_lp/ledger.py b/liquidity/src/aero_lp/ledger.py
index 33758a7..17607c1 100644
--- a/liquidity/src/aero_lp/ledger.py
+++ b/liquidity/src/aero_lp/ledger.py
@@ -82,6 +82,21 @@
     token TEXT NOT NULL,
     amount REAL NOT NULL
 );
+CREATE TABLE IF NOT EXISTS transaction_effects (
+    tx_hash TEXT NOT NULL,
+    effect TEXT NOT NULL,
+    PRIMARY KEY(tx_hash, effect)
+);
+CREATE TABLE IF NOT EXISTS slot_tokens (
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/recovery.py

```diff
diff --git a/liquidity/src/aero_lp/recovery.py b/liquidity/src/aero_lp/recovery.py
new file mode 100644
index 0000000..aaee5ac
--- /dev/null
+++ b/liquidity/src/aero_lp/recovery.py
@@ -0,0 +1,159 @@
+"""Shared, idempotent ledger recovery for daemon and CLI submission journals.
+
+Construct LedgerRecovery with the recorded ledger and a fresh-price callback, then pass apply
+as the journal's reconciliation callback. It never broadcasts or retries a transaction.
+"""
+
+from __future__ import annotations
+
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/state.py

```diff
diff --git a/liquidity/src/aero_lp/state.py b/liquidity/src/aero_lp/state.py
index 7b3c6e3..3235374 100644
--- a/liquidity/src/aero_lp/state.py
+++ b/liquidity/src/aero_lp/state.py
@@ -39,7 +39,18 @@ def atomic_write_json(path: Path, doc: Any) -> None:
     fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
     with os.fdopen(fd, "w") as f:
         json.dump(doc, f, indent=2, default=str)
+        f.flush()
+        os.fsync(f.fileno())
     os.replace(tmp, path)
+    _sync_directory(path.parent)
+
+
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/submissions.py

```diff
diff --git a/liquidity/src/aero_lp/submissions.py b/liquidity/src/aero_lp/submissions.py
new file mode 100644
index 0000000..ebabd85
--- /dev/null
+++ b/liquidity/src/aero_lp/submissions.py
@@ -0,0 +1,223 @@
+"""Durable public transaction intents. Unknown outcomes block another live runner.
+
+The journal stores hashes and decoded intent metadata, never calldata, signed payloads or keys.
+A receipt is retained until the caller applies its state/accounting effects idempotently.
+"""
+
+from __future__ import annotations
+
```

Excerpt capped at 14 lines; full diff retained in Git.

### liquidity/src/aero_lp/validation.py

```diff
diff --git a/liquidity/src/aero_lp/validation.py b/liquidity/src/aero_lp/validation.py
new file mode 100644
index 0000000..0900dc9
--- /dev/null
+++ b/liquidity/src/aero_lp/validation.py
@@ -0,0 +1,31 @@
+"""Shared numeric validation for safety settings. Never coerce TOML strings or booleans."""
+
+from __future__ import annotations
+
+import math
+
+
+def finite_number(value: object, name: str, *, positive: bool = False, integer: bool = False) -> None:
```

Excerpt capped at 14 lines; full diff retained in Git.

### mongo/load.py

```diff
diff --git a/mongo/load.py b/mongo/load.py
index 9f4a80b..522a8b9 100644
--- a/mongo/load.py
+++ b/mongo/load.py
@@ -30,6 +30,7 @@
 import argparse
 import csv
 import hashlib
+import io
 import json
 import math
 import re
@@ -62,15 +63,21 @@ def sha256(path: Path) -> str:
     return digest.hexdigest()
```

Excerpt capped at 14 lines; full diff retained in Git.

### mongo/schema.py

```diff
diff --git a/mongo/schema.py b/mongo/schema.py
index 5eda148..2961bcb 100644
--- a/mongo/schema.py
+++ b/mongo/schema.py
@@ -368,18 +368,23 @@ def connect(uri: str = "mongodb://localhost:27017"):
     return MongoClient(uri, serverSelectionTimeoutMS=3000)


-def create(db, *, drop: bool = True) -> list[str]:
-    """Create every collection with its validator and indexes.
+def create(db, *, drop: bool = True, only: set[str] | None = None) -> list[str]:
+    """Create selected collections with their validators and indexes (all by default).

     Drops first by default: this store is derived from files in the repo, so
```

Excerpt capped at 14 lines; full diff retained in Git.

### research/decide.py

```diff
diff --git a/research/decide.py b/research/decide.py
index 150896d..c9e0f95 100644
--- a/research/decide.py
+++ b/research/decide.py
@@ -44,10 +44,12 @@

 import argparse
 import json
+import math
 import sys
 import time
 from dataclasses import dataclass, field
 from datetime import datetime, timezone
+from numbers import Integral, Real
```

Excerpt capped at 14 lines; full diff retained in Git.

### research/sweep.py

```diff
diff --git a/research/sweep.py b/research/sweep.py
index df6865a..f6ff6f1 100644
--- a/research/sweep.py
+++ b/research/sweep.py
@@ -82,6 +82,9 @@ def set_data_dir(path: str | Path) -> None:
 # merely listed. Three lucky trades can produce any Sharpe you like.
 MIN_OOS_TRADES = 10

+# Constituent eligibility is a discovery decision, independent of held-out data.
+MIN_DISCOVERY_TRADES = 10
+
 # Walk-forward in-sample fraction.
 SPLIT = 0.70

```

Excerpt capped at 14 lines; full diff retained in Git.

### soltui/bgcontrol.py

```diff
diff --git a/soltui/bgcontrol.py b/soltui/bgcontrol.py
index 7d9efd0..5c7d603 100644
--- a/soltui/bgcontrol.py
+++ b/soltui/bgcontrol.py
@@ -24,7 +24,8 @@
 constraints (a flag file as the real on/off switch, and a refusal to run from a
 worktree path). A second agent competing for that surface would be a second
 source of truth for "is soltui running". This module spawns a plain child
-process instead: it lives as long as it is useful, and stopping it is a signal.
+process instead: it lives as long as it is useful. Stop queues a request on that
+worker instance's private local control socket.

 ## Liveness is a lock, not a pid

```

Excerpt capped at 14 lines; full diff retained in Git.

### soltui/bgworker.py

```diff
diff --git a/soltui/bgworker.py b/soltui/bgworker.py
index 6924f53..183363a 100644
--- a/soltui/bgworker.py
+++ b/soltui/bgworker.py
@@ -20,7 +20,8 @@

 A background job is never "finished", it is interrupted -- by a reboot, by a
 laptop lid, by the user. So every job's result is flushed to disk the moment it
-is computed, and startup skips ids already present. Batching writes would be
+is computed. Startup skips existing ids only when their settings, price files,
+and evaluation code still match the persisted proof. Batching writes would be
 faster and would throw away an hour of work on a power cut.

 ## What this deliberately does not do
```

Excerpt capped at 14 lines; full diff retained in Git.


## 6. Blind re-audit result

First independent review: extension 4 High; liquidity 1 High/1 Medium;
simulation/worker/store 2 High/4 Medium. Second independent review: extension
2 High/1 Medium and liquidity 2 Medium. Each reviewer received source/tests and
pass instructions, not the author's earlier reports. No cross-model comparison ran.
Focused regression fixes followed the second dissent. There is no third gate.
Final status: **BLIND-AUDIT-DISSENT**, not CLEAN.

## 7. Recommendations

N/A: `--suggest` was not requested. Bootstrap standards/license gaps remain explicit
in the bootstrap ledger; they are not invented product features.

## 8. Implemented features

N/A: `--implement-features` was not requested. Added helpers enforce existing safety,
accounting, evidence and interruption contracts.

## 9. Summary

2 diagnostic/remediation checkpoints plus focused post-gate fixes · 18 passes considered, applicability/partial limits above · repo profile, 17 primary sources plus dependencies · final independent C/H/M/L: 0/2/3/not-exhausted · Verify: PASS offline; service-backed MongoDB and full CI receipt external · Status: BLIND-AUDIT-DISSENT.

## 10. Snapshot and rollback

Original owned files, diagnostic receipts, scope and run stub are in
`/Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/`.
`restore-owned-paths.sh` contains a literal `cp` for every original and `rm` for each
created file. Review it before use: it overwrites later edits and restores base
`eebadbb`, so a Git revert of the delivered change is preferable after integration.
No rollback command was executed. Source rollback cannot undo transactions; preserve
runtime journals, ledgers and receipts. To review and execute the recorded restoration:

```sh
cat /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/restore-owned-paths.sh
sh /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/restore-owned-paths.sh
```

## 11. Index

index: n/a (outside optimizer semantic corpus roots). Repository offline metadata,
text, concepts and high-signal indexes are regenerated with existing tools after final
content. Semantic embeddings remain opt-in and were not run. Private source-only
dossier delivery is recorded by the external receipt after final Git delivery.

## 12. Memory-central

memory-central: 1 unrelated lesson and 12 convention rows consulted; source commands
verified against current instructions · 0 prior regression checks fired. No central
memory files were changed. Repo `prompts.md` and `memory.md` preserve continuation.
Stele transport closed during the run; task completion is pending MCP recovery and
must not be inferred from local code/test completion. Final delivery receipt lives at
`/Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261106-bootstrap-cdo/delivery-receipt.json`.
