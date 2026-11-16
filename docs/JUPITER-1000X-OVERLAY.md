# Jupiter 1000x indicator window

Version: 1.3.0. Delta: preserve temporal ordering between historical and streaming closes, 2026-11-16.

## Decision and scope

Extend the existing Chrome MV3 extension with a floating, extension-owned chart
on https://jup.ag/1000x?market=SOL&mode=classic . Use the locally vendored
Lightweight Charts 5.2.1 library and preserve its visible attribution. The page's
current live chart is a custom React canvas. A supported external chart-instance
API was not observed. Drawing over its pixels or modifying private React state
would depend on unverified coordinates and lifecycle details.

| Choice | Fit | Tradeoff |
| --- | --- | --- |
| Existing Chrome extension, selected | Existing tests, local chart library, isolated origin, explicit public-read host permissions | Requires loading/reloading the unpacked extension |
| Userscript | Easy single-file distribution | A second packaging/runtime path; page CSP, isolated-world imports and cross-origin reads need manager-specific treatment |
| Direct native-chart injection | Not selected | No verified supported chart handle; canvas pixel coordinates do not establish price/time alignment |

The window is read-only. It does not connect a wallet, access account endpoints,
sign, submit, arm trading, or change the existing grid engine. It adds no remote
runtime code or package dependencies. The existing command registry remains the
only route for operational extension actions; internal public data reads do not
add an alternative command handler.

## Engineering evidence and freshness

The current public market catalog includes SOL with oracle feed ID 6 and market
address `Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS`. The previous BTC/ZEC-only
observation in the older execution contract is historical. Market availability
does not extend the existing executor's supported asset list.

| Interface | Observed contract | Evidence boundary |
| --- | --- | --- |
| `GET https://yolo-api.jup.ag/markets` | Catalog, market symbol/address/feed ID, closed/close-only flags | Public frontend contract; fetch current values |
| `GET https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history` | `symbol=SOLUSD`, resolution in minutes, from/to in UTC seconds; `s,t,o,h,l,c,v` column arrays | Oracle candles, not executed trade OHLCV |
| `wss://perps-api.jup.ag/v1/pyth/stream` | Subscribe to `fixed_rate@200ms`, requested feed IDs and price/exponent/feedUpdateTimestamp properties | Feed identity comes from current catalog |
| Stream updates | `streamUpdated`, subscription ID 1, `parsed.priceFeeds`; integer decimal price scaled by exponent; microsecond exchange timestamp | Duplicate frames were observed; receipt time is a separate clock |
| Chart surface | Custom canvas with accessible name `Live market price chart` | Loaded TradingView namespace alone does not identify a usable chart instance |

These are observed application interfaces, not a published compatibility promise.
Unknown schemas and identities fail visibly. The full requested developer corpus
is archived at `/Users/mitch/.local/state/jup1000x-overlay-2348/jupiter-llms-full.txt`.
Its generic Perps and Trigger documentation must not be treated as a 1000x write
contract. The separate SDK report records the order lifecycle and exact limits.

## Plan and ownership

1. Archive the public app build using observed script URLs, HTML imports and the
   reachable module graph. Record URL, status, bytes, SHA-256 and pending frontier.
   Keep third-party bundles outside Git. Discovery stops after 20 minutes, 2,000
   assets or 250 MiB; a cutoff is recorded as incomplete coverage.
2. Implement a public-read feed that validates the market catalog, history and
   stream. Seed history, distinguish developing candles, ignore duplicate/older
   ticks, refresh overlapping history, detect gaps and invalidate stale signals.
   Bound reconnects and abort owned work on stop or navigation.
3. Implement five configurable causal indicators in a pure module. Use null for
   unavailable warm-up values, an explicit zero-range BOP rule, confirmed versus
   provisional ZigZag points, and closed-only explanatory signal readouts.
4. Mount a draggable, collapsible window in a shadow root. Put chart/network code
   in an extension-origin iframe. Restrict navigation input to a bounded market
   symbol. Tear down the old session on SPA market changes or leaving the route.
   Persist only local view settings. Keep the native trade controls usable.
5. Verify independent numerical vectors and prefix invariance, market/timeframe
   identity, history/stream merging, gaps, freshness, reconnect and teardown.
   Exercise the actual extension in Chrome under fixture and public-live data.
   Review and deliver through final-head CI and a merged PR.

Portal/feed and indicator workers own separate modules and tests. The SDK worker
owns the lifecycle report. The primary agent owns integration, UI, workflow
records, verification and delivery. Existing feed collectors, source-faithful
strategy research, wallets and other worktrees remain under their current owners.

## Indicator definitions

| Indicator | Definition and default | Interpretation |
| --- | --- | --- |
| ZigZag | Close-price reversal threshold 0.5%; confirm the previous extreme only after a threshold reversal | Confirmed points carry their later confirmation time; the last endpoint is provisional |
| RSI | Wilder smoothing of positive/negative close changes, SMA seed, length 14 | No value before 14 changes; flat=50, only gains=100, only losses=0 |
| Balance of Power | `(close-open)/(high-low)`, optional SMA smoothing, default length 1 | Zero-range candle=0; a candle measure, not order-book pressure |
| Volty Expan Close | Active bar-t stops are prior close ± `SMA(true range,5)*0.75`, computed through t-1 | Uses the repository's stop-entry definition, not Wilder ATR; displayed levels do not simulate fills |
| Parabolic SAR | Prior SAR + acceleration × (extreme−prior SAR), prior-two-bar clamps, reversal reset; start/step .02, cap .2 | Initial direction follows the first two closes; initialization can differ from vendor implementations |

The chart may show the developing candle and its developing indicator values.
History requests seed 502 completed candles and retention allows 503 including
the developing candle. This covers the largest accepted period of 500, including
Volty active levels that need 502 completed observations. A disconnect clears the
prior quote; history alone cannot restore live status before the replacement
stream provides a valid observation.
A cached stream close overrides a developing history close only when its exchange
timestamp follows that history request. Earlier observed extrema remain included;
closed history is authoritative. The cached quote keeps its own source timestamp.

Explanatory signal labels use completed, contiguous candles only and require a
fresh live feed. Indicator agreement is not a calibrated probability or a tested
trading strategy. No backtest return or execution performance is claimed.

## Public bundle archive

Run the checked-in capture tool with an output directory outside the checkout.
It downloads text as evidence and never evaluates vendor JavaScript. Available
source maps are attempted and status recorded. Absence of a source map is not
evidence that its underlying source was reviewed.

Snapshot directory: `/Users/mitch/.local/state/jup1000x-overlay-2348/public-site/`.
The archive manifest is the full asset inventory; it records exact build hashes,
failures, optional maps and coverage limits. The engineering snapshot is a
separate requested local output, not a new paid research run or library proof.

The completed finite census contains 1,176 asset URLs: 1,172 JavaScript responses
returned HTTP 200 and four literal `dist/` references returned 404. Response
bodies total 113,604,207 bytes. All 1,169 advertised/conventional map probes
returned 404. One throttled retry cleared initial rate limiting. The manifest
preserves the first attempts, retry hashes and remaining computed-import limits;
an empty literal frontier does not establish complete runtime branch coverage.

Exact current source bindings include:

| Public bundle | SHA-256 |
| --- | --- |
| `https://jup.ag/assets/index-BpHhYrTp.js` | `dcd23c37b132987c6b8382148978c75c3722bc2158a72afa4a9713cfad1f3c1b` |
| `https://jup.ag/assets/vendor-tanstack-runtime-D7h0586w.js` | `7aae8c8be98eb2ab5c3401f99be86fb9179c2b3d8a454e3b36dd36ab7c5794f9` |
| `https://jup.ag/assets/DegenWatchMobile-BA7LHJXD.js` | `0278a789efa82f2ba3b0b69a0c5dcb7ee3ca532ba17ad8644ce83d503b4d7e95` |

## Installation and verification

Load `/Users/mitch/dev/solmargintrader/extension` as an unpacked extension, then
open the 1000x route. The Indicators window opens automatically on that route.
Its header shows the extension version. A wallet is unnecessary for public data.
If an automation browser disables extension installation, use the normal Chrome
profile for wallet approval; do not change browser policies or copy wallet data.

Source tests, browser fixtures and actual public-live acceptance are separate
gates. A fixture proves the behavior under that fixture, not live venue support.
The final delivery receipt records the completed checks and remaining limits.

The independent candidate browser gate passed 18 fixture checks and seven
actual-public-portal checks. Both verified the loaded version and exact executed
module hashes. The live check bound history HTTP 200, SOL feed-6 subscription and
received price frames to the extension iframe's own CDP session. Fixture results
cover all five chart toggles, accepted/invalid settings, rendered RSI thresholds,
closed-only explanations, stale/lagging/malformed/gapped data, narrow layout,
market navigation and teardown. The reconnect regression kept all signals
unavailable with a 643 ms old quote, immediate history and a connected replacement
socket until a new frame arrived. The adopted deterministic gate is also in CI:

```sh
cd /Users/mitch/dev/solmargintrader/extension
npm run e2e:1000x -- --evidence /tmp/smt-1000x-fixture
npm run e2e:1000x -- --live --evidence /tmp/smt-1000x-public-live
```

The second command reads the real public site and may fail when that service is
unavailable. Neither command connects a wallet or permits an order request.
Candidate receipts are under
`/Users/mitch/.local/state/jup1000x-overlay-2348/acceptance/`. The prompt optimizer's
full audit and executed 8/8 self-check are under
`/Users/mitch/.local/state/jup1000x-overlay-2348/prompt-optimizer/`; two isolated
reviews and the applied discovery-budget repair precede execution. Its algorithm
is structural-only; no prompt-training or empirical quality gain is claimed.

Sources:

https://jup.ag/1000x?market=SOL&mode=classic

https://developers.jup.ag/docs/llms-full.txt

https://yolo-api.jup.ag/markets

https://perps-api.jup.ag/v1/pyth/fixed_rate%40200ms/history

https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts

https://developer.chrome.com/docs/extensions/reference/manifest/web-accessible-resources
