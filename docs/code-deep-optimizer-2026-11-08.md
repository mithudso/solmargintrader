# Deep code optimizer — 2026-11-08

Status: **BLIND-AUDIT-DISSENT**. This is a capped review of **50 primary sources out of 261 candidates at audited base 2ca3041**, with 211 explicit deferred paths. Dependencies and added helper files received targeted checks. This report does not claim repository-wide cleanliness.

The run applied the default 18-pass standard profile. No advisory or feature phase ran. There is no separate held-out benchmark and no empirical champion was promoted. Trading defaults remain disarmed/dry-run; archived liquidity stays disabled. Manual Jupiter V2 submission refuses until an independent economic verifier exists.

After the bounded audit, concurrent deliveries https://github.com/mithudso/solmargintrader/pull/151 and https://github.com/mithudso/solmargintrader/pull/152 were integrated. Executor integrity and Signal Desk are preserved. PR151 independently closed2 of the original15 residuals;13 remain (7 High,6 Medium). The task repaired98 findings; the two upstream closures are reported separately. Extension version0.5.1 is checked in a fresh profile. No third optimizer iteration or blind gate ran.

## 1. Per-iteration severity

| Iteration / gate | Critical | High | Medium | Action |
| --- | ---: | ---: | ---: | --- |
| Initial diagnostics / repair 1 | 4 | 32 | 40 | 76 findings repaired |
| Blind gate 1 / repair 2 | 0 | 4 | 16 | 20 findings repaired |
| Related repair-time findings | 0 | 0 | 2 | Protected alias and deny-before-engine defects repaired |
| Original blind gate 2 | 0 | 9 | 6 | 15 retained before concurrent PR151 |
| After upstream integration | 0 | 7 | 6 | Residual findings retained; no third gate |

Counts identify diagnostic findings, not a claim that every row is a distinct root cause. Low/Nit taste changes were skipped.

## 2. Findings

| Pass | File:line | Severity | Finding | Correction | Status |
| --- | --- | --- | --- | --- | --- |
| C1,C3,S3,P2,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/engine.py:224 | High | Final RPC reads invalidate the last KILL and quote-age checks | Collect final RPC inputs first, then recheck quote age and KILL immediately before writing the intent/sending and calling send_transaction. Preserve the exit_only exemption. Add deterministic tests for KILL arrival and clock advance inside the final RPC read. | Repaired (E1) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/engine.py:265 | High | On-chain failures discard fees and bypass the daily loss stop | Read and persist exact fee metadata for failed on-chain transactions, value it using the recorded SOL price, and include fee-only failed outcomes in daily P&L without changing positions. If fee metadata is not readable, retain a blocking unresolved accounting state instead of clearing the send. | Repaired (E2) |
| C1,C2,C3,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/engine.py:454 | High | Closing an existing wrapped-SOL account corrupts actual SOL accounting | Compute actual SOL deltas from native and WSOL token balances with actual account rent creation/closure accounted separately. Do not reuse only predicted retained rent. Add post-trade and reconcile fixtures for zero-token WSOL rent refunds and existing WSOL token balances. Coordinate with the separate txverify conservation finding. | Repaired (E3) |
| C1,C3,S1,S3,M4,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/txverify.py:439 | Critical | Preexisting wrapped SOL bypasses input and output economic limits | Check conservation across native SOL and the pre/post wSOL account together. Exclude already-owned wSOL and refunded account rent from new swap output; account for both retained and closed-account rent consistently. Enforce exact total SOL input and minimum total new SOL output. Add fail-first cases with existing wSOL for both directions, including | Repaired (TV-01) |
| C1,C3,S2,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/journal.py:44 | High | A partial write is acknowledged as a durable journal record | While holding flock, loop over a memoryview until all bytes are written. Raise on a non-positive write count. Only fsync and return after the full newline-terminated record is persisted. Add a mocked short-write regression that verifies the record replays as sending, and a zero-write case that refuses before the caller sends. | Repaired (JOURNAL-01) |
| C1,C3,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/rails.py:124 | Medium | The pre-check blocks a SOL buy that restores the configured native reserve | For swaps that output native SOL, defer the reserve decision to the existing exact simulated post-balance verifier instead of rejecting solely on the starting balance. Preserve the post-state reserve check. Add a replenishment-buy regression while retaining SOL-spend and post-state-under-reserve refusals. | Repaired (RAILS-01) |
| C1,C2,C3,S1,S3,M4,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/config.py:233 | High | Public status exposes credentials from RPC URL userinfo | Parse and validate endpoint URLs centrally. Build the public host field from hostname and optional port only; exclude username/password and other credential-bearing URL fields. Add a status-envelope regression test with synthetic userinfo. | Repaired (CFG1) |
| C1,C3,S1,S3,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/config.py:187 | Medium | Loopback HTTP exception accepts remote plaintext endpoints | Parse the URL and compare scheme and hostname exactly. Permit HTTP only when hostname == "127.0.0.1"; require a valid nonempty host and valid port for all endpoints. Add userinfo/prefix-confusion fixtures. | Repaired (CFG2) |
| C1,C3,S2,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/config.py:199 | Medium | Creating a custom config changes an existing parent directory mode | Create new dedicated executor directories with mode 0700 without chmodding an already-existing arbitrary parent. Apply permission ownership checks or raise an explicit configuration error if the selected storage directory is unsuitable. Test that loading a custom config preserves the existing parent mode. | Repaired (CFG3) |
| C1,C2,C3,S1,S3,M4,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/quote.py:98 | High | Minimum output can bypass the slippage cap | Reject a quote whose min_out_raw is below the integer minimum allowed by out_raw and the echoed requested slippage_bps, allowing only the documented integer-rounding behavior. Keep the configured-cap check and honor tighter user-requested slippage. Add fail-first tests for threshold=1 and valid rounded boundary thresholds. Do not repair or silently | Repaired (QUOTE-01) |
| C1,C2,C3,S2,S3,M4,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/rpc.py:110 | High | Unrecognized RPC errors incorrectly clear the ambiguous-send block | Raise SendRejected only for explicitly recognized definite pre-submission failures with validated error structure. Raise RpcError for generic, unknown, contradictory or malformed error responses so Engine preserves the signature as unknown and requires reconciliation. Add direct Rpc seam tests for known preflight rejection and generic/malformed err | Repaired (RPC-01) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/gates.py:101 | High | Non-finite persisted numbers can satisfy both mandatory gates | Validate persisted gate schemas and per-strategy record shapes before using them. Require finite, nonnegative elapsed times and timestamps; require nonnegative integral dry-run counts excluding bool. Reject invalid records as unsatisfied rather than allowing them to hide a later failure. Prevent non-finite JSON writes and add malformed/non-finite r | Repaired (G1) |
| C1,C3,S2,P2,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/gates.py:128 | High | Concurrent research writes can erase a newer failed gate | Serialize the complete research read-validate-append-replace transaction with an interprocess lock shared by CLI/API writers, or use a durable append-only journal with locked append. Keep timestamps/outcome ordering explicit and test the delayed-pass/newer-fail interleaving. | Repaired (G2) |
| C1,C3,S2,S3,P2,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/signer.py:34 | Medium | Opening a FIFO key path hangs before regular-file validation | Include os.O_NONBLOCK in the initial open flags while retaining O_NOFOLLOW and the same-fd fstat check. Reject FIFO and other nonregular descriptors before any read. Add a bounded FIFO regression to the existing symlink/directory validation cases. | Repaired (SIGNER-01) |
| C1,C2,C3,S1,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:387 | Critical | Manual live signing skips the verifier economic layer | Require verified economic intent on the exact transaction before loading a key and again before send using fresh state, or explicitly refuse manual signing until that safety contract is available. Preserve quote previews and history. | Repaired (JM1) |
| C1,C2,C3,S4,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:472 | High | Version-0 messages are signed without their version prefix | Use the supported VersionedTransaction signer constructor or sign to_bytes_versioned(tx.message), then verify all signatures before persisting/sending. Add a v0 fixture; do not rely only on legacy Message tests. | Repaired (JM2) |
| C1,C2,C3,S2,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:605 | Critical | A 90-second timer clears ambiguous submits without chain evidence | Persist the exact signature before any send attempt. Retain unknown/submitting records until explicit chain evidence resolves them; elapsed wall time is insufficient. Use validated transaction expiry/blockhash and chain/history evidence for a dropped outcome, and preserve old unresolvable records as blocking. | Repaired (JM3) |
| C1,C2,C3,S2,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:543 | Critical | Execute responses that explicitly mean unknown become terminal failures | Classify documented unknown codes, unrecognized statuses, and incomplete response objects as unknown. Persist the locally computed and returned signatures for reconciliation. Mark definite failure only when the response/chain evidence proves no unresolved landing. | Repaired (JM4) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:313 | High | Missing input USD prices bypass the hard order-value cap | Require a finite positive independent input price before sizing/capping every supported pair, or restrict pairs to ones whose full USD valuation is available. Refuse unknown valuation and enforce the hard cap on actual input value; do not substitute zero/None or relax it to105. | Repaired (JM5) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:303 | High | Base-sized buys treat USD notional as units of any quote token | Restrict quote tokens to the supported stable unit contract, or require both token prices and convert base_units*base_usd_price/quote_usd_price before exact decimal conversion. Reject absent quote valuation. | Repaired (JM6) |
| C1,C2,C3,S2,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/coinbase_manual.py:319 | High | A timed-out submission cannot reconcile by its original client order ID | When an authenticated status result returns the exact saved client_order_id and the saved product and side match, bind the returned order_id to that unresolved record. Then persist pending or complete according to the verified status. Keep missing or mismatched client IDs blocked and never resend. Test matching terminal recovery, nonterminal recove | Repaired (CBM-01) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/native_host.py:97 | Medium | The oversized-reply fallback can itself exceed Chrome's message limit | Validate and bound request ids/echoed operation and command names before dispatch. Make the fallback use bounded metadata or null id if needed, and enforce the final serialized-byte cap before write_frame. Add a large-id and large-command regression next to the existing large-result case. | Repaired (NATIVE-01) |
| C1,C3,S2,S3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/native_host.py:94 | Medium | A valid JSON string with an unpaired surrogate kills the persistent request loop | Reject unpaired-surrogate strings or make response serialization produce valid UTF-8 for them. Also guard per-request parsing/serialization failures with a small safe error envelope so a bad request cannot terminate the connection. Add a surrogate request followed by a normal ping regression. | Repaired (NATIVE-02) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/commands.py:1780 | Medium | Current-configuration forward status ignores the selected coin overrides | Resolve asset = _compound_asset(ctx, p) once. When current_only is true, load_state(asset) and hash that effective configuration. Pass the same asset to forward_status. Add a regression with differing shared/coin configuration hashes, plus the omitted-asset Settings path. | Repaired (CMD-01) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/forwardtest.py:550 | Medium | Historical pooled ranking truncates current winners and returns unrelated settings | Select the current trial per label/horizon first and bind evidence, direction and settings to those same rows. Rank current evidence and apply LIMIT only after that selection. Preserve historical trial rows for inspection and preserve execution defaults. Add a two-revision/two-label regression fixture for ranking truncation and settings binding. | Repaired (FT1) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/bots.py:901 | Medium | Cutoff-excluded snapshots are permanently consumed | Retain valid decoded samples beyond the current cutoff and return them when a later cutoff permits them, or only commit storage offsets while preserving the unreturned portion of a gzip member. Add incremental-versus-fresh equivalence tests with members straddling advancing cutoffs and repeated same-cutoff calls. | Repaired (BOT-01) |
| C1,C3,S2,S3,S5,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/bots.py:439 | Medium | An empty hourly cache aborts all later coins in a backtest batch | Normalize empty sources as unavailable. If neither hourly nor minute source contains usable bars, raise BotError with the coin and missing/empty source. Preserve valid-source fallback and test that backtest_many returns the empty coin under errors while running a later valid coin. | Repaired (BOT-02) |
| C1,C3,P2,T1 | /Users/mitch/dev/solmargintrader/soltui/bots.py:1001 | High | Concurrent forward-state updates lose successfully started bots | Serialize every shared forward-state read/modify/write with a process-safe file lock, analogous to _config_lock. Coordinate the in-process session reset under the runtime lock. Keep atomic replacement and avoid a shared temporary filename for unrelated unprotected writers. Add concurrent different-bot start and start/stop regression cases. | Repaired (BOT-03) |
| C1,C3,S1,S3,P2,T1 | /Users/mitch/dev/solmargintrader/soltui/pricefeed.py:660 | High | A stale pid file can direct SIGTERM to an unrelated process | Use a cooperative stop request bound to a recorder-instance nonce or a private local control endpoint, as the existing bgcontrol instance-control design does. Do not signal a PID solely because an independent lock is busy. Add a stale-owner-record/startup-window regression and refuse invalid/nonpositive PIDs as defense in depth. | Repaired (PRICEFEED-01) |
| C1,C2,C3,S2,S4,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/pricefeed.py:815 | Medium | A missing launchctl aborts ensure_recorder before the detached fallback | Normalize expected launchctl OS/timeout failures to PriceFeedError or catch those specific failures in ensure_recorder, record agent_error, and continue to detached startup. Add a missing-launchctl regression without invoking the real service manager. | Repaired (PRICEFEED-02) |
| C1,C2,C3,S2,S3,S5,P2,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/pricefeed.py:450 | Medium | A silent connection keeps old order books labelled as current | Track connection-wide receipt liveness with Coinbase heartbeat messages or a bounded receive-idle deadline. Reconnect or invalidate books when that deadline expires. Preserve PR146 behavior for a quiet but demonstrably live book: do not merely switch back to stale ticker time or reject every unchanged book. | Repaired (PRICEFEED-03) |
| C1,C3,S2,P2,T1 | /Users/mitch/dev/solmargintrader/soltui/experiment_runner.py:385 | High | Unconditional lifecycle writes overwrite newer cancellation requests | Acknowledge control states through transition_run(expected=[observed_state]) and re-read/retry if a newer control state wins. Replace the exception handler unconditional status write with a conditional transition that cannot overwrite pause_requested, cancel_requested, paused, or cancelled; persist error text separately. Add deterministic interleav | Repaired (R19-1) |
| C3,S5,M4,T1 | /Users/mitch/dev/solmargintrader/extension/src/core/engine.js:384 | Medium | Safety holds and preparation failures have no durable tick event, and caught failures lose their historical cause | Finalize a durable bounded event for every tick outcome, including early safety holds and preparation failures. Preserve a redacted reason/error code and relevant intent identities rather than only counts. Keep latest-tick persistence, conservative refusal, and no-auto-retry behavior. Test recentEvents for each hold and failure, then run a later su | Repaired (ENG-OBS-01) |
| C1,C3,P1,P2,T1 | /Users/mitch/dev/solmargintrader/extension/src/core/commands.js:510 | Medium | Acknowledging alerts stalls the engine behind a network-bound scan | Give ackAlerts the same unlocked treatment as scanAlerts while retaining alertQueue serialization for acknowledgement/scan storage keys. Add an engine-lock progress assertion to the existing overlapping scan/ack regression. | Repaired (COMMANDS-01) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/extension/src/core/pnl.js:225 | Medium | Maximum percentage drawdown can be understated when the largest dollar decline occurs later | Track maximum dollar drawdown and maximum positive-peak percentage drawdown independently on every point. Preserve the documented zero/nonpositive-peak handling. Add a regression where their maxima occur at different times. | Repaired (PNL-01) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/extension/src/core/pnl.js:238 | Medium | Valid grid identifiers containing delimiters produce malformed financial CSV rows | Apply standard CSV field encoding: double embedded quotes and surround fields containing commas, quotes, CR or LF with quotes. Keep the current columns and numeric formatting. Add parsed round-trip tests for comma, quote and newline identifiers, plus existing ordinary identifiers. | Repaired (PNL-02) |
| C1,C3,P2,T1 | /Users/mitch/dev/solmargintrader/extension/src/ui/soltui-panel.js:591 | High | An in-flight save can validate one document and write a different document | Capture path, documentEpoch, base text and candidate text before awaiting. Abort if the active document/epoch changed before write. Send only the captured path/text, and apply editorBase/status/button updates only to the same document generation. Add a mounted deferred-read/navigation regression and a deferred-write/navigation regression. | Repaired (PANEL-01) |
| S5,T1 | /Users/mitch/dev/solmargintrader/extension/tools/api-server.js:229 | Medium | Production startup disables every API security/error diagnostic | Provide a production API logger that emits safe structured security/error events to stderr. Preserve the existing secret-free messages and do not enable arbitrary upstream exception/body printing. Add a startup-wiring logger assertion rather than testing injected logger callbacks alone. | Repaired (API1) |
| C1,C3,S4,T1 | /Users/mitch/dev/solmargintrader/extension/tools/api-server.js:257 | Medium | API silently skips startup from paths containing spaces or URL control characters | Use pathToFileURL(process.argv[1]).href (with appropriate direct-module path handling) for the comparison. Add a direct-entrypoint test for a URL-encoded pathname while retaining import-without-listen behavior. | Repaired (API2) |
| C1,C2,C3,T1 | /Users/mitch/dev/solmargintrader/backtester/core/engine.py:285 | High | Fee-bearing increases to full allocation are silently discarded | Scale an unaffordable same-side increase to the maximum delta supported by free cash after fees/collateral, as open already does. Recompute delta, fees and units consistently and retain realized-PnL cost accounting. Add partial-to-full allocation fixtures for spot and perp. | Repaired (BE1) |
| C1,C3,M4,T1 | /Users/mitch/dev/solmargintrader/backtester/core/engine.py:683 | High | Five-basis-point mismatch tolerance can erase a real coarse-bar liquidation | Separate the tolerance used to count feed mismatch diagnostics from liquidation enforcement. If the fine walk finds no liquidation, always honor a coarse-range touch under the documented conservative policy. Add near-threshold long and short fixtures within the5bps tolerance. | Repaired (BE2) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/backtester/core/engine.py:498 | High | Count-only fine coverage accepts shifted bars and leaks data beyond the coarse close | For every candidate coarse window, prove the exact expected fine timestamp grid and end boundaries before refining. Treat gaps, overlaps, shifts and a final fine candle extending beyond the coarse close as incomplete and fall back to the coarse bar (or refuse invalid layer cadence). Preserve support for genuinely gapped layers; they must not be mis | Repaired (BE3) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/backtester/core/gridsim.py:619 | High | The simulator and extension place different exits and entries after a midpoint-crossing fill | Use the same actual-fill anchor for Python exit selection and held-rung occupancy as current planGrid, retaining original rung data for correct gross/slippage attribution and lot matching. If original-rung anchoring is the intended policy, update both planners consistently instead. Add a full-plan cross-language parity fixture with midpoint-crossin | Repaired (GRIDSIM-01) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/backtester/core/compound.py:269 | Medium | Dataset fingerprint ignores price and volume inputs that change the result | Fingerprint every execution/signal bar field in a stable order (timestamp,open,high,low,close,volume, and any result-relevant quality metadata). Bind auxiliary reference/funding/event inputs separately when claiming complete run reproducibility. Add a regression that changing only low changes the bar-data fingerprint. | Repaired (CMP-01) |
| C1,C2,C3,T1 | /Users/mitch/dev/solmargintrader/backtester/core/scorecard.py:1959 | High | Horizon statistics discard the final fully resolved call | Skip only when len(b)<=h, use k=len(b)-h, and retain the existing aligned next-open/close slices and cost subtraction. Add exact h+1 length and terminal-winning/losing-outcome regressions. | Repaired (SCORECARD-01) |
| C1,C2,C3,S2,S3,T1 | /Users/mitch/dev/solmargintrader/backtester/core/scorecard.py:1758 | Medium | Accepted short adaptive windows crash when entry quantile is enabled | Validate the coupled quantile/window warm-up requirement during normalise_config, or define a documented min_periods value that never exceeds the accepted window. Add boundary tests at windows 12,19,20 with quantile on/off. | Repaired (SCORECARD-02) |
| C1,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py:272 | High | An internal multi-window outage is cached as the listing boundary | Do not use an arbitrary internal empty run as proof that all older history is absent. Keep unproven older windows in the fetch plan, or obtain/verify an authoritative boundary; record uncertain probe bounds separately from proven venue short history. Add an internal3+-window outage fixture reached during the binary search. | Repaired (FM1) |
| C1,C2,C3,S2,T1 | /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py:548 | High | Interrupted CSV append records an unfetched window as done | Mark a nonempty window done only after successful CSV append and flush/durability boundary. On interrupted/failed writes leave that window resumable; duplicate complete rows on a later retry can be safely deduplicated. Keep explicitly empty successful responses distinguishable. Add interruption-before/during-append fixtures. | Repaired (FM2) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py:465 | Medium | Invalid candle rows are cached and their windows permanently completed | Validate candle row shape, exact timestamps/cadence/window bounds and OHLCV domains before appending or marking completion. Raise FetchError for unusable responses so those windows stay in todo, while preserving genuine absent minutes instead of inventing bars. Add invalid OHLC/non-finite/fractional timestamp fixtures. | Repaired (FM3) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py:435 | Medium | Coverage-only reporting reuses shallow probe floors as proven short history | Apply the same probe-floor validity predicate in coverage as in effective_windows. For an unproven deeper request, count earlier windows as unattempted/unknown and do not label their absence as venue-limited history. Preserve recorded plan-end freshness behavior. Add coverage-only-after-short-run regression. | Repaired (FM4) |
| C1,C3,M4,T1 | /Users/mitch/dev/solmargintrader/research/decide.py:527 | Medium | Zero or equal readings are incorrectly assigned a bearish direction | Use an explicit three-way comparison for directional sign/comparison readers: positive/bullish, negative/bearish, equality/neutral (reverse positive and negative for reversion comparisons). Preserve existing nonfinite-unavailable handling. Add exact-equality and zero-momentum regressions. | Repaired (DEC-01) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/research/sweep.py:325 | High | The out-of-sample leg cannot fill at the split as documented | Include sufficient pre-split decision context for the configured fill_delay, so a decision made before the split first fills at k. Continue clipping metrics/trades to k onward and never expose future bars to the strategy. Add a first-OOS-open fill regression for default delay and verify other supported delays. | Repaired (SWEEP-01) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/research/sweep.py:603 | High | Full-history redundancy evidence leaks held-out data into candidate selection | Compute and freeze both member and combination redundancy using discovery bars only. Bind gate artifacts to source data, parameters and split/cutoff, and refuse legacy full-history artifacts for held-out model selection. Add a prefix-isolation test requiring identical candidate sets when only the held-out suffix changes. Do not silently regenerate  | Repaired (SWEEP-02) |
| C1,C2,C3,S5,M4,T1 | /Users/mitch/dev/solmargintrader/research/sweep.py:822 | Medium | Selecting only the triples stage silently evaluates nothing | Resolve the triples discovery prerequisite even when singles is not an output stage, or reject the unsupported stage combination explicitly before writing outputs. Preserve discovery-only selection and include prerequisite evaluations in the reported denominator. Add a mocked triples-only dispatch regression. | Repaired (SWEEP-03) |
| C1,C3,M4,T1 | /Users/mitch/dev/solmargintrader/research/cpcv_sweep.py:147 | Medium | Low positive share does not prove the selected winner loses | Warn that most tested configurations lose without asserting the selected winner loses. Require the selected winners actual held-out returns before making that profitability claim. Update low-PBO tests to distinguish an all-losing search from a sparse search with a consistently profitable winner. | Repaired (CPCV-01) |
| C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/research/cpcv_sweep.py:310 | Medium | Saved CPCV results lack the inputs and settings needed to identify the experiment | Persist a bound experiment manifest with source/data checksum, exact strategy parameters, engine cost/fill settings, n_groups, k_test, selected gate and candidate set. Reference its run identity from each CSV/PBO/Markdown artifact so alternate runs cannot silently lose provenance. | Repaired (CPCV-02) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/mongo/load.py:194 | Medium | Every bar source is labeled Coinbase, including alternate-venue USDT data | Resolve and validate source/venue/pair/quote metadata from the supported cache source contract. Bind sidecar provenance to its exact bytes and store it with bar series; retain Coinbase metadata only for genuinely Coinbase caches. Add an alternate-venue sidecar fixture. | Repaired (MG1) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/mongo/load.py:287 | High | Strategy-card body and hash come from separate source reads | Snapshot each card once and parse/build its fields from those exact bytes, carrying that snapshot hash into the document. Extend the existing changed-during-read tests to strategy cards. Do not merely reread for a checksum after parsing. | Repaired (MG2) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/mongo/load.py:397 | High | Missing manifest-declared artifacts silently become empty loaded results | Validate the expected selected artifact inventory before building a batch or dropping collections. Require every manifest-declared artifact needed by the selected loader to exist and hash-match; parse zero-row files normally. Preserve compatibility refusal for legacy artifacts without proof. | Repaired (MG3) |
| C1,C2,C3,S2,M4,T1 | /Users/mitch/dev/solmargintrader/mongo/load.py:807 | High | Ordinary reloads permanently erase observed test history | Exclude untouched test_results from destructive rebuilds when suites are not run. Persist new observed receipts by the existing commit/suite identity while retaining previous commits and skipped suites. Keep destructive rebuild behavior for collections actually regenerated from source files. | Repaired (MG4) |
| C1,C2,C3,M4,T1 | /Users/mitch/dev/solmargintrader/mongo/load.py:398 | Medium | Backtest documents omit the fields consumed by bundled queries | Restore the established document fields using the proven manifest/comparison snapshot, or update the schema/index/query contract coherently. Retain the new manifest hash identity and comparison provenance. Add a source-to-query shape regression. | Repaired (MG5) |
| C1,C2,C3,S2,S3,S5,T1 | /Users/mitch/dev/solmargintrader/mongo/schema.py:392 | Medium | Keep mode reports incompatible existing time-series collections as ready | On existing time-series collections, inspect the collection type/options and verify required timeField/metaField and supported bucketing configuration before reporting readiness. If incompatible, raise a clear schema mismatch and preserve the collection under --keep; require the explicit rebuild path to replace it. Cover compatible and incompatible | Repaired (SCH-01) |
| C1,C3,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/engine.py:146 | Medium | Recovered replacement mint preserves the previous rebalance cooldown and edge confirmations | When first applying a previously unbooked recovered mint to a slot, set last_rebalance_ts from the confirmed mint time (or conservative recovery time) and edge_checks=0. Keep replay idempotent: use the existing hash/history check so already-booked or replayed records do not restart cooldown indefinitely. | Repaired (ENGINE-01) |
| C1,C2,C3,S2,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/executor.py:638 | Medium | Confirmed collect and swap amounts disappear from partial results after a failed state read | Recover collect token deltas and exact-swap output from the matching confirmed receipts, using operation-local token identities or decoded intent. Keep unknown evidence distinct from confirmed zero. Add post-receipt-read failure regressions for both operations. Preserve durable submission blocking and do not retry an ambiguous transaction. | Repaired (LEX-01) |
| C1,C2,S2 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/gates.py:138 | High | Nonfinite persisted values satisfy live gates or hide a newer research failure | See the bound diagnostic and regression receipts. | Repaired (AG1) |
| C3,S2,M1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/gates.py:181 | High | Concurrent research writers can erase the newer failure and restore a passing gate | See the bound diagnostic and regression receipts. | Repaired (AG2) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/submissions.py:196 | Medium | Reconciliation consumes receipts without enforcing the journal ledger binding | Enforce explicit self.ledger_path against the stored ledger_path during _read (or before any reconciliation callback), using the same resolved-path comparison as before_submit. Retain the existing behavior when no explicit ledger_path is supplied, so CLI recovery can open the recorded ledger. | Repaired (SUBMISSIONS-01) |
| C1,C3,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/recovery.py:138 | Medium | AERO-pool unstake rewards are omitted when no successful removal represents them | Decide whether AERO is already represented using the actual successful receipt path and monetary flows, rather than pool membership alone. Book measured wallet rewards when removal fails or the reward stays outside the position. Preserve the existing successful rebalance/withdrawal double-count protection and receipt idempotency. | Repaired (REC-01) |
| C1,C2,C3,S3,S5,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/recovery.py:150 | Medium | Slot-bound conversion fees are permanently consumed as unallocated costs after a crash | Persist operation purpose and any originating slot with the intent before submission; bind slot-bound conversion groups before consuming monetary receipt effects. Explicitly distinguish legitimate wallet-wide gas operations from unresolved strategy attribution. Do not guess a slot from the route pool. Add crash-before-log and replay tests ensuring  | Repaired (REC-02) |
| C1,C2,S2,M2,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/config.py:211 | High | Strategy table accepts nonfinite numbers that disable economic, cooldown and confirmation decisions | See the bound diagnostic and regression receipts. | Repaired (AC1) |
| C1,C3,S1,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/native_host_install.py:62 | Medium | Wrapper expands shell syntax in repository and interpreter paths | Generate each path token with shlex.quote(str(path)) for the POSIX /bin/sh wrapper, without adding another pair of double quotes around the quoted result. Keep repository resolution and use the same treatment for both paths. | Repaired (INSTALLER-01) |
| C3,S4 | /Users/mitch/dev/solmargintrader/soltui/config.py:238 | Medium | A failed save destroys the previous configuration before the replacement is complete | See the bound diagnostic and regression receipts. | Repaired (SC1) |
| S2,S5 | /Users/mitch/dev/solmargintrader/soltui/config.py:238 | Medium | Saving into an existing loose file exposes full extended public keys before permissions tighten | See the bound diagnostic and regression receipts. | Repaired (SC2) |
| C1,C3,M1 | /Users/mitch/dev/solmargintrader/soltui/config.py:208 | Medium | An existing YAML file prevents the documented JSON fallback when PyYAML is unavailable | See the bound diagnostic and regression receipts. | Repaired (SC3) |
| C1,C2,M2,T1 | /Users/mitch/dev/solmargintrader/soltui/config.py:139 | Medium | Settings validation accepts unusable capital and noninteger execution geometry | See the bound diagnostic and regression receipts. | Repaired (SC4) |
| C1,C2,C3,S2,P2,T1 | /Users/mitch/dev/solmargintrader/extension/src/bg/soltui-transport.js:145 | Medium | Pending one-shot calls are invisible to the auto-reload activity guard | Track the count/lifetime of one-shot requests in createNativeTransport and include it in busy(). Increment before delegating and decrement in finally on success, rejection or timeout. Keep one-shot connection cleanup and the no-retry rule unchanged. | Repaired (TRANSPORT-01) |
| C1,C3,P2 | /Users/mitch/dev/solmargintrader/backtester/core/engine.py:513 | High | Queued opening fills rescue positions that the gap has already liquidated | Before applying queued fills, check the existing held position against the new bar's open with fees accrued only through the prior boundary. Liquidate a breached old position before an exit, collateral release or size change can act. Preserve later intrabar checks for newly opened or surviving positions. Add long/short gap tests for queued flat, ho | Repaired (BACKTESTER-B1) |
| C1,C3,M4 | /Users/mitch/dev/solmargintrader/backtester/core/scorecard.py:1788 | Medium | Opposite calls bypass the configured minimum holding period | Apply the minimum-hold decision before replacing an existing position with an opposite call, while retaining the documented gate override. If opposite-call exit is intentionally supported, expose and document it as an explicit exception instead of promising a minimum hold. Add alternating-call regression cases for both starting directions. | Repaired (BACKTESTER-B2) |
| C1,C3,M4 | /Users/mitch/dev/solmargintrader/backtester/core/scorecard.py:1949 | Medium | In-sample forecast statistics include outcomes from the held-out period | For bounded forecast statistics, exclude calls whose label or horizon exit resolves outside the requested interval. Apply a separate outcome-aware mask for each horizon. Add an invariance test that changing bars at or after the split cannot change reported IS statistics. | Repaired (BACKTESTER-B3) |
| C2,C3,S3 | /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py:142 | Medium | Malformed scalar JSON is permanently recorded as an empty fetched window | Require a list payload in get_candles before returning. Treat every other JSON type as a FetchError; only [] should represent an empty candle response. Add scalar/null response tests that verify the window is not added to the progress ledger. | Repaired (BACKTESTER-B4) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/executor/src/executor/txverify.py:216 | High | Jupiter instruction minimum output is never bound to the approved quote | Use schema-aware Borsh decoding for each actually supported Jupiter discriminator. Validate route-plan variants and lengths, derive the field offsets by consuming that schema, and reject trailing or otherwise undecoded bytes. Bind encoded exact input to Expectation.amount_in and the route enforced minimum output to at least Expectation.min_out; rej | Repaired (EXECUTOR-EX-G1-001) |
| C1,C2,C3,P2,T1 | /Users/mitch/dev/solmargintrader/extension/src/bg/service-worker.js:67 | Medium | Chrome discards simulated resting orders before the next dry-run tick | Persist and restore paper venue state under the execution context before reconciliation, so Chrome ticks and service-worker restarts retain orders/fills. At minimum retain one context-bound dry venue during a worker lifetime; durable restoration is needed for the documented MV3 termination model. Add a Chrome-dependency two-tick crossing-price regr | Repaired (EXTENSION-E1) |
| C2,C3,S3,P2,T1 | /Users/mitch/dev/solmargintrader/extension/src/ui/soltui-panel.js:598 | Medium | Document save precheck has no atomic write precondition | Return a document revision/hash from docs.read and require that precondition in docs.write. Compare it while holding a per-document write lock, then perform the replacement. Send the original editor base revision and keep the draft when the write rejects a conflict. Test two interleaved saves. | Repaired (EXTENSION-E2) |
| S1,S3,M2,T1 | /Users/mitch/dev/solmargintrader/extension/src/core/pnl.js:237 | Medium | Fill CSV exporter emits formula-prefixed external identities as spreadsheet formulas | Neutralize formula-leading text cells (including whitespace before =, +, -, @) before CSV quoting, while preserving numeric cells as numbers. Reuse or extract the safe string-cell policy already implemented by workspace-model.rowsToCsv. Test the actual ingest/export path with hostile identities. | Repaired (EXTENSION-E3) |
| C2,C3,S2,M3,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/safe_exit.py:264 | Medium | Safe-exit conversion starts before the withdrawal journal has been reconciled | Reconcile and durably account the completed withdrawal before starting each independent conversion group. Retain owner and ledger checks; do not bypass the journal barrier. Add a temp-journal handoff regression. | Repaired (LIQUIDITY-LQ-G1-01) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/safe_exit.py:313 | Medium | Conversion uses the dry-run withdrawal amount after the confirmed amount changes | After each live withdrawal, rebuild conversion steps from res.amounts_in_position and the measured non-pool AERO reward. Carry exact per-token remaining budgets into fresh planning and simulation. Add a regression where dry and live receipts differ and a pre-existing wallet balance exists. | Repaired (LIQUIDITY-LQ-G1-02) |
| C1,C2,C3,S3,T1 | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/daemon.py:542 | Medium | Initial position registration persists an incomplete USD deposit basis | Require finite positive prices for both pool tokens before any initial ledger writes, using _pool_prices(pos.pool, p). Leave unpriced positions unregistered until both quotes exist, and add a missing-one-quote registration regression. | Repaired (LIQUIDITY-LQ-G1-03) |
| C1,C2,C3,S3,M2,M4,T1 | /Users/mitch/dev/solmargintrader/research/signal_redundancy.py:129 | Medium | Redundancy proofs can bind exposure vectors that the engine never produces | Drive each measured single only from its declared warmup, and drive each composite only from its longest member warmup, while retaining original full arrays in BarWindow. Prefer the existing engine-parity replay_targets helper, with matching exposure clamp/mode, for both walks. Add the synthetic stateful regression and regenerate affected evidence  | Repaired (RESEARCH-MONGO-G1-RM-1) |
| C1,C2,C3,S2,M4,T1 | /Users/mitch/dev/solmargintrader/mongo/schema.py:379 | High | Default schema rebuild deletes original test receipts | Preserve test_results when rebuilding the default derived schema. Apply validator/index updates to that collection without dropping it. Reserve receipt deletion for an explicit dedicated reset selection/flag, and add a fake-database regression for the public schema CLI. | Repaired (RESEARCH-MONGO-G1-RM-2) |
| C1,C2,C3,S3,M3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:159 | Medium | Every nonstable input preview lacks a usable USD valuation path | Acquire and validate an independent USD price for the resolved mint, including SOL, before sizing/capping a nonstable input. Preserve refusal when no trustworthy positive finite price exists. Do not derive the cap valuation from the swap output. Add SOL and real resolver-shape regression cases. | Repaired (TUI-COMMANDS-G1-TUI-CMD-1) |
| C1,C3,P1,P2,T1 | /Users/mitch/dev/solmargintrader/soltui/commands.py:748 | Medium | Background Forwardtest overrides an active manual tick ownership flag | Acquire the busy slot atomically in both paths under rt.lock. The background path must skip/retry while another check owns it, and only the owner may clear it. Preserve the minute check for a retry after the current check ends. Add an Event-based race regression. | Repaired (TUI-COMMANDS-G1-TUI-CMD-2) |
| C1,C3,S3,M3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/config.py:214 | Medium | Restoring the optional YAML parser silently reverts newer JSON settings | Define one authoritative configuration across representation transitions. For example, select the newest valid supported file with a clear migration rule, or write JSON into the current canonical path and keep it readable with either parser. Add a YAML-unavailable-save/parser-restored round trip regression. | Repaired (TUI-COMMANDS-G1-TUI-CMD-3) |
| C1,C3,S2,S5,T1 | /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py:134 | Medium | Unreadable Jupiter records block ordering while state reports no unresolved order | Have the public state use the same unresolved predicate and expose a bounded secret-free unreadable-record diagnostic, such as the record ID and an unknown state. Keep unreadable evidence blocking; never auto-delete it. Add a malformed-record regression. | Repaired (TUI-COMMANDS-G1-TUI-CMD-4) |
| C1,C3,S2,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/pricefeed.py:500 | High | Restart appends remain unreadable behind a crash-truncated gzip member | While holding the recorder lock, recover an existing day file once before the first append: locate its last complete gzip-member boundary and truncate only an incomplete/corrupt tail. Preserve complete members. Add a restart regression proving that a later appended snapshot becomes readable. | Repaired (TUI-STATE-G1-TUI-1) |
| C1,C2,C3,S3,M4,T1 | /Users/mitch/dev/solmargintrader/soltui/bots.py:925 | Medium | Stale product quotes become undisclosed observed forward bars | Reject absent, invalid, future or stale parsed product quote timestamps before building a minute bar, using an explicit freshness bound. Let those missing minutes flow through the existing bridge/gap disclosure. Add a stale-product-with-live-other-products regression. | Repaired (TUI-STATE-G1-TUI-2) |
| C1,C3,S2,S3,T1 | /Users/mitch/dev/solmargintrader/soltui/forwardtest.py:356 | Medium | Invalid OHLC is committed before validation and poisons corrected settlement retries | Validate every OHLC row before persisting it, including rows outside the latest contiguous signal segment. Ensure an already retained invalid row can be repaired by validated data rather than remaining protected by INSERT OR IGNORE. Add invalid-first-reply/corrected-retry coverage. | Repaired (TUI-STATE-G1-TUI-3) |
|  | /Users/mitch/dev/solmargintrader/soltui/docs_browser.py:0 | Medium | Editable document aliases bypass protected research result prefix | Check NO_WRITE_PREFIXES on the canonical repository-relative target before opening the write path. Preserve existing lexical and catalogue guards. | Repaired (TUI-ITER2-ALIAS) |
|  | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/cli.py:0 | Medium | Liquidity run gate constructs a network engine before refusing live mode | Run the live gate before constructing Engine; test forbidden engine construction with sockets blocked. | Repaired (LQ-VERIFY-01) |
| C3, S1, S3 | /Users/mitch/dev/solmargintrader/executor/src/executor/rails.py:100 | High | With validation enabled, strategy path-validation, exit_only=true, an empty position and KILL present, a SOL-to-USDC sell passes the rails. The validation exception skips the quantity check, while exit_only skips the KILL check. | Require every exit, including path-validation, to sell no more than its tracked position before granting exit exemptions. | Unfixed final dissent (BLIND-G2-EXECUTOR-1) |
| ['S1', 'S3', 'S5'] | /Users/mitch/dev/solmargintrader/extension/src/core/engine.js:584 | High | An upstream venue operation throws an error whose message contains credential material. The engine copies the raw message into result.errors; the tick command persists that result as lastTick at /Users/mitch/dev/solmargintrader-wt-01a1be31/extension/src/core/commands.js:747 and returns it to callers. The submit failure path also stores and logs raw errors at /Users/mitch/dev/solmargintrader-wt-01a1be31/extension/src/core/engine.js:573. | Keep only allowlisted, secret-free diagnostic fields in returned results, intent records and logs; do not persist or return raw upstream exception messages. | Unfixed final dissent (BLIND-G2-EXTENSION-1) |
| ['C1', 'C3'] | /Users/mitch/dev/solmargintrader/extension/src/core/pnl.js:64 | Medium | A buy and its later sell have the same recorded timestamp and the sell's arbitrary ID sorts before the buy's ID. | Use a reliable execution sequence or higher-resolution ordering supplied by the venue. If ordering cannot be established for conflicting equal-time fills, surface the ambiguity and hold accounting rather than treating lexicographic IDs as chronology. | Unfixed final dissent (BLIND-G2-EXTENSION-2) |
| ['C1', 'C3', 'S3'] | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/daemon.py:1303 | High | Every dry-run tick records soak time before check_fresh and the rest of the tick. During a persistent RPC outage, run catches each tick failure and continues polling, so elapsed intervals can satisfy the pre-live soak even though no tick got past the freshness check. | Credit soak only after the required dry-run work succeeds; define and test which failures make an interval ineligible. | Unfixed final dissent (BLIND-G2-LIQUIDITY-1) |
| ['C2', 'C3', 'S5'] | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/safe_exit.py:88 | Medium | When conversion was requested but a conversion step is refused or fails, the position can still have status exited and report.ok remains true. The CLI maps that result to exit code 0 at /Users/mitch/dev/solmargintrader-wt-01a1be31/liquidity/src/aero_lp/cli.py:251, despite coins remaining unconverted. | Make the result and CLI status distinguish a completed withdrawal with incomplete requested conversion, and retain the per-step refusal reason. | Unfixed final dissent (BLIND-G2-LIQUIDITY-2) |
| ['C3', 'P2'] | /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/gates.py:145 | Medium | Concurrent grandfather calls can both read an absent entry and both succeed because the read-check-write sequence has no shared lock. A concurrent dry-run read-modify-write can also overwrite a newly recorded grandfather entry. | Serialize all soak-record read-modify-write operations, including grandfather and dry-run ticks, under the same stable lock. | Unfixed final dissent (BLIND-G2-LIQUIDITY-3) |
| ['C1', 'C2', 'M4'] | /Users/mitch/dev/solmargintrader/research/decide.py:314 | High | For fill_delay=2, a strategy whose targets end in 0, 1, 1 is reported as HOLD-LONG because previous always comes from the immediately preceding target. The engine fills the target from two bars earlier at the current open, so the simulated held target is 0. build_report accepts and displays fill_delay=2 but does not pass it into the decision calculation. | Make decision classification account for the requested fill delay and pending targets, or reject delays other than the one the calculation supports. Add a regression against engine timing. | Unfixed final dissent (BLIND-G2-RESEARCH-MONGO-1) |
| ['C1', 'C3', 'M4'] | /Users/mitch/dev/solmargintrader/research/cpcv_sweep.py:302 | High | The default measured gate selects combinations using redundancy evidence computed from the first discovery fraction of the same arrays, then CPCV evaluates and calculates PBO over blocks drawn from those arrays. Some CPCV test blocks therefore contributed to selecting the configurations being evaluated. | Freeze redundancy evidence on a separate earlier dataset, or compute selection within each training fold and evaluate it only on that fold's held-out blocks. Clearly label any existing same-sample results. | Unfixed final dissent (BLIND-G2-RESEARCH-MONGO-2) |
| ['C2', 'S2', 'C3'] | /Users/mitch/dev/solmargintrader/research/signal_redundancy.py:416 | Medium | When no twin groups exist, rows is empty and DataFrame(rows) has no columns. The CLI writes a newline-only CSV and a proof, but read_gate_table subsequently raises pandas EmptyDataError while loading that artifact. | Create the empty table with the expected column schema and ensure the consumer treats a header-only table as zero redundant pairs. Add an empty-result round-trip test. | Unfixed final dissent (BLIND-G2-RESEARCH-MONGO-3) |
| ['C1', 'M4'] | /Users/mitch/dev/solmargintrader/backtester/core/trianglesim.py:153 | High | For the forward cycle with A-USD ask 100, A-B bid 2, B-USD bid 60 and B-USD bid size 1, the function caps at 60 USD. That input produces 1.2 B before fees and exceeds the displayed one-B liquidity. The mocked replay reported 12 USD P&L on that oversized trade. | Convert each leg's displayed capacity back to starting quote notional using the actual preceding leg rates and fee deductions, then take the minimum. Add forward and reverse regression cases. | Unfixed final dissent (BLIND-G2-TUI-1) |
| ['C1', 'S3'] | /Users/mitch/dev/solmargintrader/backtester/core/trianglesim.py:127 | High | Quotes timestamped 99 are accepted by a replay at time 0 because now minus quote time is negative and therefore less than max_age. Historical parsing at line 366 only rejects future timestamps when require_quote_time is true; the historical file reader uses the default false. | Require finite quote timestamps and 0 <= now - quote_time <= max_age in the shared usability check. Reject future timestamps in historical parsing as well and test both replay entry points. | Unfixed final dissent (BLIND-G2-TUI-2) |
| ['C1', 'S3'] | /Users/mitch/dev/solmargintrader/backtester/core/trianglesim.py:361 | Medium | The parser accepts negative and non-finite displayed sizes. A mocked snapshot with an ask size of -1 produced a cycle with negative 100 USD notional and negative 20 USD P&L. | Reject invalid supplied sizes or reject the affected quote; require finite nonnegative sizes and do not record an execution with nonpositive capacity. | Unfixed final dissent (BLIND-G2-TUI-3) |
| ['C1', 'S2'] | /Users/mitch/dev/solmargintrader/soltui/pricefeed.py:578 | Medium | When pending snapshots span two UTC day files, the first append succeeds and the second raises OSError. The pending list remains intact, so a retry appends the already-written first-day lines again. A mocked retry produced writes to the first file twice. | Remove or checkpoint each successfully appended day's pending lines before proceeding to the next file, while retaining failed and unwritten lines for retry. Add a two-day partial-failure regression. | Unfixed final dissent (BLIND-G2-TUI-4) |

Two original final-gate findings were closed by already-delivered upstream PR151 during integration: processed-status retention and KILL-before-terminal ordering. Source and seven integration regressions verify this; no third blind gate ran. The remaining13 are retained.

The final gate stops under the code-deep-optimizer 1.16.0 rule: “second dissent exits `BLIND-AUDIT-DISSENT`.” Residuals are listed, not applied. The applicable skill is /Users/mitch/.agents/skills/code-deep-optimizer/SKILL.md.

## 3. Verify gate

| Command / package | Baseline | Final result | Verdict |
| --- | --- | --- | --- |
| cd extension && node --test | 369 (372 after PR146) | 389 integrated Node tests pass | PASS |
| executor/.venv/bin/pytest -q; Ruff lint/format | 202 pass,5 network deselected | 429 pass,5 network deselected; integrated Ruff lint/format pass | PASS |
| liquidity offline pytest with socket connections blocked; Ruff lint/format | 473 pass,6 network deselected | 579 pass,6 network deselected; Ruff pass | PASS |
| backtester full unittest | 909; index becomes stale after workflow records | Final integration report/index refresh and rerun required | PENDING |
| Mongo fake-only unittest | 34 run,11 skipped | 46 run,11 skipped | PASS |
| SolTUI mapped and focused tests | 198 focused pass | 89 integration-focused pass; final mapped gate still running | PENDING |
| real Chrome + production native host in fresh isolated profile | 24/24 loading/dry-run checks | 26/26 integrated checks pass; version0.5.1 and12 source hashes match; SignalDesk behavior checked | PASS |
| offline 8-tick dryrun | closed net $0.3492 | closed net $0.3492; 1 closed round trip, no unknown fee | PASS |
| node tools/verify-endpoints.js | read-only reachability | keyless price and auth route reachable; keyed price skipped without API key | PASS (limited) |
| scripts/check_docs.py; offline index freshness | 2515 test census (2526 after PR146) | Final integration report/index refresh and rerun required | PENDING |

All required check processes must finish successfully before commit. A running process, expected index failure or queued CI is not a pass. Full optional SolTUI tests and live orders were not run.

## 4. Activated reviewer skills

- /Users/mitch/.agents/skills/lang-python/SKILL.md — Python contracts, state, exceptions and typing.
- /Users/mitch/.agents/skills/lang-js-ts/SKILL.md — ESM, asynchronous ordering and tests.
- /Users/mitch/.agents/skills/security-review/SKILL.md — trust boundaries, secrets and financial controls.
- /Users/mitch/.agents/skills/chrome-extension-expert/SKILL.md — MV3 lifetime, storage and browser wiring.
- Language-map baseline, WebCrypto and testing references from /Users/mitch/.agents/skills/code-deep-optimizer/ — domain-specific passes.

## 5. Per-file diff preview

Each preview is capped at 12 patch lines. The merged Git diff is the complete change; these previews are intentionally truncated. Delivered PRs148–152 are preserved and excluded from the task diff. Post-audit integration changed some reviewed source; their before/after hashes are explicit in the scope JSON and affected checks were rerun.

### /Users/mitch/dev/solmargintrader/.github/copilot-instructions.md

```diff
diff --git a/.github/copilot-instructions.md b/.github/copilot-instructions.md
index 3087d76..d1a25bc 100644
--- a/.github/copilot-instructions.md
+++ b/.github/copilot-instructions.md
@@ -57,10 +57,10 @@ ## Non-negotiables — backtester
 ## Build, Test, and Validation Commands

 ```bash
-python3 -m unittest discover -s backtester/tests -t .   # 909 tests
-python3 -m unittest discover -s soltui/tests -t .       # 1221 tests (~840s, optional)
-python3 -m unittest discover -s mongo/tests -t .        # 34 tests
-cd extension && npm test                                # 377 tests
```
7 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/CLAUDE.md

```diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 7a87117..0cc1df0 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -114,10 +114,10 @@ ## Non-negotiables — backtester
 ## Before you claim a change works

 ```bash
-python3 -m unittest discover -s backtester/tests -t .   # 909 tests
-python3 -m unittest discover -s soltui/tests -t .       # 1221 tests (~840s, optional)
-python3 -m unittest discover -s mongo/tests -t .        # 34 tests
-cd extension && npm test                                # 377 tests
```
19 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/GEMINI.md

```diff
diff --git a/GEMINI.md b/GEMINI.md
index b5b9cd5..7953fe4 100644
--- a/GEMINI.md
+++ b/GEMINI.md
@@ -37,10 +37,10 @@ ## The rules most often broken here
 ## Before claiming a change works

 ```bash
-python3 -m unittest discover -s backtester/tests -t .   # 909 tests
-python3 -m unittest discover -s soltui/tests -t .       # 1221 tests (~840s, optional)
-python3 -m unittest discover -s mongo/tests -t .        # 34 tests
-cd extension && npm test                                # 377 tests
```
7 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/README.md

```diff
diff --git a/README.md b/README.md
index d839483..c2a1734 100644
--- a/README.md
+++ b/README.md
@@ -33,7 +33,7 @@ # Backtester — fetch once, then simulate offline

 # Extension — no install step, no dependencies
 cd extension
-npm test                                               # 377 tests
+npm test                                               # 389 tests
 node tools/dryrun.js --ticks 8 --osc 6 --offline 100   # end-to-end tick loop
 node tools/cli.js                                      # every available command
```
16 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/compound.py

```diff
diff --git a/backtester/core/compound.py b/backtester/core/compound.py
index 8d0d026..56fb78e 100644
--- a/backtester/core/compound.py
+++ b/backtester/core/compound.py
@@ -265,10 +265,26 @@ def _stitch(slices: Sequence[_Slice | None]) -> dict[str, Any]:


 def _hash_frame(df: pd.DataFrame) -> str:
-    h = hashlib.sha1()
-    h.update(df[["timestamp", "close"]].to_numpy(dtype="float64").tobytes())
-    return h.hexdigest()[:12]
-
```
41 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/engine.py

```diff
diff --git a/backtester/core/engine.py b/backtester/core/engine.py
index 567d94c..f082772 100644
--- a/backtester/core/engine.py
+++ b/backtester/core/engine.py
@@ -280,16 +280,20 @@ def resize(
         direction = 1.0 if side is Side.LONG else -1.0

         if delta_notional > 0:
-            # -- increase: merge at a blended average entry price ----------
+            # The target uses pre-fill equity. Reserve costs before spending the
+            # remaining cash, just as open() does for a full allocation.
+            collateral_rate = 1.0 if self.cfg.mode is Mode.SPOT else 1.0 / self.cfg.leverage
```
71 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/fetch_minutes.py

```diff
diff --git a/backtester/core/fetch_minutes.py b/backtester/core/fetch_minutes.py
index 84ab9b0..15560f9 100644
--- a/backtester/core/fetch_minutes.py
+++ b/backtester/core/fetch_minutes.py
@@ -86,9 +86,6 @@
 # raising --workers would walk straight past the venue's limit.
 RATE_LIMIT_PER_SECOND = 8.0

-# How many consecutive empty windows to believe as "before the listing". One is not
-# enough: this venue drops minutes routinely, and first_available's answer is cached.
-EMPTY_RUN_TO_BELIEVE = 3

```
188 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/gridsim.py

```diff
diff --git a/backtester/core/gridsim.py b/backtester/core/gridsim.py
index 8c43ff7..1dc79ef 100644
--- a/backtester/core/gridsim.py
+++ b/backtester/core/gridsim.py
@@ -612,19 +612,11 @@ def _plan(
     for lot in lots:
         if lot.qty <= 0:
             continue
-        # A lot's rung is known exactly — it is the level the bid rested at — so
-        # look it up rather than re-deriving it from the fill price. Besides being
-        # O(1) instead of O(rungs), it cannot mis-snap a lot to a neighbouring rung
-        # when slippage is a large fraction of the rung width.
```
16 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/scorecard.py

```diff
diff --git a/backtester/core/scorecard.py b/backtester/core/scorecard.py
index f66960a..740cc09 100644
--- a/backtester/core/scorecard.py
+++ b/backtester/core/scorecard.py
@@ -1755,7 +1755,7 @@ def mult(style: str) -> np.ndarray:
     if agg["entry_quantile"] > 0 and n:
         # Trailing quantile of |composite| through bar t: known at t, so the call stays causal.
         window = int(agg["adaptive_window"])
-        q = pd.Series(np.abs(composite)).rolling(window, min_periods=max(20, window // 4)).quantile(
+        q = pd.Series(np.abs(composite)).rolling(window, min_periods=min(window, max(20, window // 4))).quantile(
             agg["entry_quantile"]).to_numpy()
         threshold = np.where(np.isfinite(q), np.maximum(threshold, q), np.inf)
```
71 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/strategy_cards.py

```diff
diff --git a/backtester/core/strategy_cards.py b/backtester/core/strategy_cards.py
index d1981e1..0ca70ad 100644
--- a/backtester/core/strategy_cards.py
+++ b/backtester/core/strategy_cards.py
@@ -51,7 +51,7 @@
 import math
 from dataclasses import dataclass, field
 from pathlib import Path
-from typing import Any
+from typing import Any, Callable

 CARD_DIR = Path(__file__).resolve().parent.parent / "strategy_cards"
```
32 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/core/trianglesim.py

```diff
diff --git a/backtester/core/trianglesim.py b/backtester/core/trianglesim.py
index 039c441..b857202 100644
--- a/backtester/core/trianglesim.py
+++ b/backtester/core/trianglesim.py
@@ -339,8 +339,11 @@ def snapshots_from_closes(
 # reader keeps every complete line before the damage instead of discarding the day.


-def parse_snapshot_line(line: str) -> tuple[float, dict[str, Quote]] | None:
-    """One recorded line -> (time, {product: quote}); None for a line that is not usable."""
+def parse_snapshot_line(line: str, *, require_quote_time: bool = False) -> tuple[float, dict[str, Quote]] | None:
+    """Parse one snapshot. Forward replay requires measured product timestamps.
```
18 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_analysis_regressions.py

```diff
diff --git a/backtester/tests/test_analysis_regressions.py b/backtester/tests/test_analysis_regressions.py
new file mode 100644
index 0000000..0d782b8
--- /dev/null
+++ b/backtester/tests/test_analysis_regressions.py
@@ -0,0 +1,269 @@
+"""Offline counterexamples for allocation, causal intrabar data and research economics."""
+from __future__ import annotations
+
+from collections import Counter
+import io
+import json
```
263 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_compound_backtest.py

```diff
diff --git a/backtester/tests/test_compound_backtest.py b/backtester/tests/test_compound_backtest.py
index 90f4a26..3d0bd79 100644
--- a/backtester/tests/test_compound_backtest.py
+++ b/backtester/tests/test_compound_backtest.py
@@ -130,7 +130,8 @@ def test_report_shape_split_and_gap_handling(self) -> None:
             self.assertIn("hit_rate", r[part]["forecast"])
             self.assertIn("total_return", r[part]["pnl"])
             self.assertEqual(r[part]["forecast"]["round_trip_bps"], 13.0)
-        self.assertEqual(r["is"]["forecast"]["bars"] + r["oos"]["forecast"]["bars"], 2390 - 2)
+        # Two segment ends and the label crossing the IS/OOS boundary are excluded.
+        self.assertEqual(r["is"]["forecast"]["bars"] + r["oos"]["forecast"]["bars"], 2390 - 3)
         self.assertLess(r["oos"]["forecast"]["oracle_net_bps"], r["oos"]["forecast"]["mean_abs_move_bps"])
```
2 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_interpret.py

```diff
diff --git a/backtester/tests/test_interpret.py b/backtester/tests/test_interpret.py
index 10fc31f..c103c66 100644
--- a/backtester/tests/test_interpret.py
+++ b/backtester/tests/test_interpret.py
@@ -62,7 +62,9 @@ def test_flags_trap_on_real_short_triples_case(self) -> None:
         """PBO 0.086 with 6/61 positive is a trap, not a win."""
         text = joined(61, 70, 6, 0.086)
         self.assertIn("trap", text)
-        self.assertIn("generalises reliably as a loser", text)
+        self.assertIn("most tested configurations lose", text)
+        self.assertIn("selected winner's actual held-out returns", text)
+        self.assertNotIn("reliably as a loser", text)
```
3 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_research_regressions.py

```diff
diff --git a/backtester/tests/test_research_regressions.py b/backtester/tests/test_research_regressions.py
new file mode 100644
index 0000000..608bbac
--- /dev/null
+++ b/backtester/tests/test_research_regressions.py
@@ -0,0 +1,192 @@
+"""Bounded synthetic/mocked guards for research selection and experiment identity."""
+from __future__ import annotations
+
+import contextlib
+import hashlib
+import io
```
186 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_scorecard.py

```diff
diff --git a/backtester/tests/test_scorecard.py b/backtester/tests/test_scorecard.py
index c735bd6..eebe178 100644
--- a/backtester/tests/test_scorecard.py
+++ b/backtester/tests/test_scorecard.py
@@ -595,13 +595,13 @@ def test_a_perfect_call_scores_one_and_the_oracle_ceiling_is_net_of_cost(self) -
         self.assertAlmostEqual(s["oracle_net_bps"], round(float(np.abs(r).mean()) - rt, 3), places=3)
         self.assertAlmostEqual(s["gross_bps_per_call"], round(float(np.abs(r).mean()), 3), places=3)

-    def test_the_time_split_partitions_bars(self) -> None:
+    def test_the_time_split_excludes_boundary_crossing_outcomes(self) -> None:
         b = synthetic(400)
         ev = sc.evaluate(b, only(ema_cross=1))
```
23 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/backtester/tests/test_sweep_pair_gate.py

```diff
diff --git a/backtester/tests/test_sweep_pair_gate.py b/backtester/tests/test_sweep_pair_gate.py
index b2a84af..66115d7 100644
--- a/backtester/tests/test_sweep_pair_gate.py
+++ b/backtester/tests/test_sweep_pair_gate.py
@@ -52,6 +52,15 @@ def setUp(self) -> None:
         patcher.start()
         self.addCleanup(patcher.stop)
         self.addCleanup(self._tmp.cleanup)
+        from backtester.tests.test_engine_audit import bars
+        from backtester.core.engine import EngineConfig
+        from research.evidence import discovery_context, write_gate_proof
+        arrays = bars((100.,) * 100)
```
17 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/API.md

```diff
diff --git a/docs/API.md b/docs/API.md
index 228f08b..8f966bd 100644
--- a/docs/API.md
+++ b/docs/API.md
@@ -11,6 +11,11 @@ # API and CLI reference
 `test/surfaces.test.js` fails the build if any surface is missing a command, so the three cannot
 drift apart.

+SolTUI tools reached through `soltuiCall` retain their own safety gates. Manual Jupiter V2 preview
+results set `submission_available=false`; the dashboard offers no submit handoff for those results.
+Jupiter submit and quick-submit refuse before keys or network calls. History and chain reconciliation
+remain available, and uncertain historical submissions are never cleared solely by elapsed time.
```
26 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/ARCHITECTURE.md

```diff
diff --git a/docs/ARCHITECTURE.md b/docs/ARCHITECTURE.md
index c1842df..df50f12 100644
--- a/docs/ARCHITECTURE.md
+++ b/docs/ARCHITECTURE.md
@@ -121,7 +121,7 @@ ## Backtester
 folding the ladder into the exposure engine would imply the two are comparable on the same axis.

 Its correctness priorities — no lookahead, costs always applied, honest reporting of a losing
-strategy — are documented in `backtester/README.md` and enforced by 909 tests.
+strategy — are documented in `backtester/README.md` and enforced by 941 tests.


```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/DEVELOPMENT.md

```diff
diff --git a/docs/DEVELOPMENT.md b/docs/DEVELOPMENT.md
index d4d0f54..56413ee 100644
--- a/docs/DEVELOPMENT.md
+++ b/docs/DEVELOPMENT.md
@@ -66,7 +66,7 @@ ### Extension

 ```bash
 cd extension
-npm test                                              # 377 tests
+npm test                                              # 389 tests
 node tools/dryrun.js --ticks 8 --osc 6 --offline 100  # the integration gate
 node tools/cli.js                                     # lists every command in the registry
```
16 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/TESTING.md

```diff
diff --git a/docs/TESTING.md b/docs/TESTING.md
index 832f801..8bae03b 100644
--- a/docs/TESTING.md
+++ b/docs/TESTING.md
@@ -1,10 +1,10 @@
 # Testing

 ```bash
-python3 -m unittest discover -s backtester/tests -t .   # 909 tests
-python3 -m unittest discover -s soltui/tests -t .       # 1221 tests (~840s, optional)
-python3 -m unittest discover -s mongo/tests -t .        # 34 tests
-cd extension && npm test                                # 377 tests
```
51 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/known-issues.md

```diff
diff --git a/docs/known-issues.md b/docs/known-issues.md
index 5136ef0..f2e5507 100644
--- a/docs/known-issues.md
+++ b/docs/known-issues.md
@@ -6,6 +6,17 @@ # Known issues
 Source markers are not an exhaustive issue list. The dated bootstrap and optimizer
 reports record reviewed findings and residuals; this page records ongoing limitations.

+### 2026-11-08 optimizer residuals
+
+The bounded optimizer repaired 98 findings and stopped at `BLIND-AUDIT-DISSENT` with
+15 corroborated residuals (nine High, six Medium). These include executor reduce-only,
```
45 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/docs/logging.md

```diff
diff --git a/docs/logging.md b/docs/logging.md
index 5d79804..ba907c3 100644
--- a/docs/logging.md
+++ b/docs/logging.md
@@ -10,6 +10,7 @@ ## The surfaces
 | `extension/` | IndexedDB: the `events` store, the intent journal, the fill log (`src/storage/store.js`) | Yes |
 | `extension/` | `console.error` in the service worker | No — lost when the worker is evicted |
 | Jupiter transport | Structured attempt/outcome metadata on Node stderr or browser debug console | No shared persistent sink |
+| Local HTTP API | Structured, secret-free security/error events on stderr | Only when the operator captures stderr |
 | `backtester/` | The run manifest and report (`core/report.py`), written per run | Yes, as output files |
 | `research/` | stdout, plus written result files | Output files only |
 | `soltui/` | App stdout/stderr plus detached sweep/fetch logs | Yes, via launchd or worker files |
```
14 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/config.py

```diff
diff --git a/executor/src/executor/config.py b/executor/src/executor/config.py
index 9c858ea..f8cc5c5 100644
--- a/executor/src/executor/config.py
+++ b/executor/src/executor/config.py
@@ -16,6 +16,7 @@
 from dataclasses import asdict, dataclass, field, fields
 from pathlib import Path
 from typing import Any
+from urllib.parse import SplitResult, urlsplit

 from .errors import ExecutorError
 from .tokens import TOKENS, resolve
```
58 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/engine.py

```diff
diff --git a/executor/src/executor/engine.py b/executor/src/executor/engine.py
index 1d98cb2..6fa6206 100644
--- a/executor/src/executor/engine.py
+++ b/executor/src/executor/engine.py
@@ -21,7 +21,7 @@
 import time
 import uuid
 from contextlib import suppress
-from decimal import Decimal
+from decimal import Decimal, InvalidOperation
 from pathlib import Path
 from typing import Any
```
135 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/gates.py

```diff
diff --git a/executor/src/executor/gates.py b/executor/src/executor/gates.py
index cf4f8f8..b0a1b15 100644
--- a/executor/src/executor/gates.py
+++ b/executor/src/executor/gates.py
@@ -49,6 +49,7 @@ def _atomic_write(path: Path, doc: Any) -> None:
             json.dump(doc, fh, indent=2, sort_keys=True, allow_nan=False)
             fh.flush()
             os.fsync(fh.fileno())
+        os.chmod(tmp, 0o600)
         os.replace(tmp, path)
         # A recorded failure must remain the latest evidence after a power loss too.
         _sync_directory(path.parent)
```

### /Users/mitch/dev/solmargintrader/executor/src/executor/journal.py

```diff
diff --git a/executor/src/executor/journal.py b/executor/src/executor/journal.py
index 1993013..8844a55 100644
--- a/executor/src/executor/journal.py
+++ b/executor/src/executor/journal.py
@@ -22,6 +22,7 @@
 import os
 import time
 from collections.abc import Iterator
+from decimal import Decimal, InvalidOperation
 from pathlib import Path
 from typing import Any

```
49 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/jupiter_route.py

```diff
diff --git a/executor/src/executor/jupiter_route.py b/executor/src/executor/jupiter_route.py
new file mode 100644
index 0000000..99d0ee7
--- /dev/null
+++ b/executor/src/executor/jupiter_route.py
@@ -0,0 +1,208 @@
+"""Strict Borsh layout decoder for the two supported Jupiter V6 ExactIn routes.
+
+Layout source (pinned, not fetched at runtime):
+https://github.com/jup-ag/jupiter-amm-implementation/blob/cc068c9d1df0060c62f9a8a4fc37ea13ea7b9b39/idls/jupiter_aggregator_v6.json
+IDL blob f554d1c7635b3497c022109fca231a15cb3642bd.
+
```
202 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/quote.py

```diff
diff --git a/executor/src/executor/quote.py b/executor/src/executor/quote.py
index 039c6aa..617ea0d 100644
--- a/executor/src/executor/quote.py
+++ b/executor/src/executor/quote.py
@@ -97,6 +97,10 @@ def evaluate(
     problems = []
     if quote.slippage_bps > r.max_slippage_bps:
         problems.append(f"slippage {quote.slippage_bps} bps exceeds max_slippage_bps {r.max_slippage_bps}")
+    # Jupiter floors the integer ExactIn threshold after applying the requested tolerance.
+    minimum = quote.out_raw * (10_000 - quote.slippage_bps) // 10_000
+    if quote.min_out_raw < minimum:
+        problems.append(f"minimum output threshold {quote.min_out_raw} is below slippage minimum {minimum}")
```
3 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/rails.py

```diff
diff --git a/executor/src/executor/rails.py b/executor/src/executor/rails.py
index 8559737..5d6a38f 100644
--- a/executor/src/executor/rails.py
+++ b/executor/src/executor/rails.py
@@ -19,7 +19,7 @@
 from . import gates, ledger
 from .config import VALIDATION_MAX_DAILY_USD, VALIDATION_MAX_TRADE_USD, VALIDATION_STRATEGY, Config
 from .errors import Refused
-from .journal import Journal
+from .journal import TERMINAL, Journal, failed_accounting_missing
 from .quote import QuoteReport
 from .tokens import QUOTE_MINT, WSOL_MINT, raw_to_ui
```
31 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/rpc.py

```diff
diff --git a/executor/src/executor/rpc.py b/executor/src/executor/rpc.py
index 0f30902..9faf9a5 100644
--- a/executor/src/executor/rpc.py
+++ b/executor/src/executor/rpc.py
@@ -107,11 +107,23 @@ def send_transaction(self, tx_b64: str) -> str:
         resp = self.http.post_json(self.url, body)  # deliberately not wrapped: the caller treats any raise as unknown
         if not isinstance(resp, dict):
             raise RpcError("sendTransaction returned a non-object")
-        if resp.get("error"):
+        if "error" in resp:
             err = resp["error"]
-            raise SendRejected(
```
19 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/signer.py

```diff
diff --git a/executor/src/executor/signer.py b/executor/src/executor/signer.py
index 4b0c73e..3f4a13e 100644
--- a/executor/src/executor/signer.py
+++ b/executor/src/executor/signer.py
@@ -31,7 +31,7 @@ def check_key_file_mode(path: Path) -> None:

 def _open(path: Path) -> int:
     try:
-        return os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
+        return os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
     except OSError as exc:
         raise WalletError(f"key file {path} is not readable: {exc.strerror}") from None
```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/src/executor/txverify.py

```diff
diff --git a/executor/src/executor/txverify.py b/executor/src/executor/txverify.py
index 90d7ffb..91817e6 100644
--- a/executor/src/executor/txverify.py
+++ b/executor/src/executor/txverify.py
@@ -5,6 +5,7 @@

 Layer 1, `check_static` (pure, no network): reads the transaction itself.
   * the fee payer is the owner, and the owner is the only signer;
+  * the fully decoded ExactIn route spends the approved input and enforces at least the approved minimum output;
   * every program id is on PROGRAM_ALLOWLIST, and each allowed program may run only the instructions listed for it;
   * compute-budget instructions are present and bound the priority fee;
   * SOL leaving the owner through System instructions is bounded by the input amount plus token-account rent;
```
114 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/conftest.py

```diff
diff --git a/executor/tests/conftest.py b/executor/tests/conftest.py
index 20bf4e3..ef884ae 100644
--- a/executor/tests/conftest.py
+++ b/executor/tests/conftest.py
@@ -90,7 +90,24 @@ def sys_transfer(src: str, dst: str, lamports: int) -> Instruction:
     return ix(SYSTEM, struct.pack("<IQ", 2, lamports), meta(src, True, True), meta(dst, False, True))


-def jupiter_ix(owner: str, mint_in: str, mint_out: str, data: bytes = SHARED_ROUTE + b"\x00" * 28) -> Instruction:
+def jupiter_ix(
+    owner: str,
+    mint_in: str,
```
66 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/test_engine.py

```diff
diff --git a/executor/tests/test_engine.py b/executor/tests/test_engine.py
index e7a3d52..9cdb743 100644
--- a/executor/tests/test_engine.py
+++ b/executor/tests/test_engine.py
@@ -231,6 +231,7 @@ def test_reconcile_failed_on_chain(cfg, chain, owner):
     with pytest.raises(Ambiguous):
         swap(engine, live=True, reason="t")
     chain.default_status = {"confirmationStatus": "confirmed", "err": {"InstructionError": [4, {"Custom": 1}]}}
+    chain.tx_meta["meta"]["err"] = chain.default_status["err"]
     assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"
     assert not engine.journal.unresolved()

```
17 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/test_engine_integrity.py

```diff
diff --git a/executor/tests/test_engine_integrity.py b/executor/tests/test_engine_integrity.py
index 7812639..0ff53c9 100644
--- a/executor/tests/test_engine_integrity.py
+++ b/executor/tests/test_engine_integrity.py
@@ -37,6 +37,7 @@ def test_processed_error_remains_unknown_until_confirmed(cfg, chain, owner):
     chain.default_status = {"confirmationStatus": "processed", "err": {"InstructionError": [0, "failure"]}}
     assert engine.reconcile()["still_blocking"] == 1
     chain.default_status["confirmationStatus"] = "confirmed"
+    chain.tx_meta["meta"]["err"] = chain.default_status["err"]
     assert engine.reconcile()["results"][0]["outcome"] == "failed_on_chain"


```
13 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/test_failed_fees.py

```diff
diff --git a/executor/tests/test_failed_fees.py b/executor/tests/test_failed_fees.py
index 96e05e8..e572b90 100644
--- a/executor/tests/test_failed_fees.py
+++ b/executor/tests/test_failed_fees.py
@@ -23,7 +23,9 @@
 def failed_attempt(journal, *, strategy="regular", fee="1.25", ts=NOW, iid="failed"):
     journal.append("intent", iid, ts=ts, strategy=strategy, side="buy", base_mint=WSOL_MINT, in_usd="1")
     journal.append("sending", iid, ts=ts, signature=f"sig-{iid}")
-    fields = {} if fee is MISSING else {"fee_usd": fee}
+    fields = {"fee_lamports": FEE}
+    if fee is not MISSING:
+        fields["fee_usd"] = fee
```
27 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/test_optimizer_regressions.py

```diff
diff --git a/executor/tests/test_optimizer_regressions.py b/executor/tests/test_optimizer_regressions.py
new file mode 100644
index 0000000..0314598
--- /dev/null
+++ b/executor/tests/test_optimizer_regressions.py
@@ -0,0 +1,696 @@
+"""Offline regression coverage for reviewed safety boundaries."""
+
+import copy
+import json
+import os
+import stat
```
690 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/executor/tests/test_txverify.py

```diff
diff --git a/executor/tests/test_txverify.py b/executor/tests/test_txverify.py
index 5a001e8..af908ba 100644
--- a/executor/tests/test_txverify.py
+++ b/executor/tests/test_txverify.py
@@ -335,7 +335,7 @@ def test_third_party_wallet_lamports_moving_refuses(owner):
     honest_sell_mods(chain, owner)
     bad_ix = list(swap_instructions(owner, WSOL_MINT, USDC_MINT, AMOUNT))
     bad_ix[-2] = ix(
-        tv.JUPITER_V6, bytes.fromhex("c1209b3341d69c81") + bytes(28),
+        tv.JUPITER_V6, jupiter_ix(owner, WSOL_MINT, USDC_MINT).data,
         meta(owner, True, False), meta(ATTACKER, False, True),
     )  # fmt: skip
```
10 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/README.md

```diff
diff --git a/extension/README.md b/extension/README.md
index d3961f6..ec0f342 100644
--- a/extension/README.md
+++ b/extension/README.md
@@ -7,7 +7,7 @@ # SolMarginTrader
 change the mode and type a confirmation. The grid lost to buy-and-hold walk-forward on 9 of 9 coins,
 which is why 0.3.0 moved it off the front page.

-## Signal Desk workspace (0.5.0)
+## Signal Desk workspace (0.5.1)

 The full dashboard opens a focused **Live signals**, **Backtesting**, **Forward testing**, or
```
23 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/e2e/lib/dashboard-workspace.mjs

```diff
diff --git a/extension/e2e/lib/dashboard-workspace.mjs b/extension/e2e/lib/dashboard-workspace.mjs
index f1ccde4..28a7415 100644
--- a/extension/e2e/lib/dashboard-workspace.mjs
+++ b/extension/e2e/lib/dashboard-workspace.mjs
@@ -10,25 +10,28 @@ export async function verifyDashboardWorkflows(page, browser) {
   };
 await ev(`(async()=>{
  const r=document.createElement('div');r.id='independent-fixture';r.append(document.querySelector('#view-soltui').cloneNode(true));document.body.append(r);window.r=r;window.calls=[];window.preview=0;window.fixtureDoc='  original\\n';
+ window.interleaveDocWrite=false;window.fixtureDocs=null;window.holdDocRead=false;window.holdDocWrite=false;window.docHeldRead=null;window.docHeldWrite=null;window.previewAvailable=true;
  window.liveClock=Date.now()-2000;window.liveDirection='UP';window.liveAccuracy=80;window.liveSamples=40;window.liveVoting={min_accuracy:60,min_resolved:20};window.liveHeld=null;window.liveHoldAsset=null;window.liveFailNext=false;
+
  const spec=[
```
65 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/manifest.json

```diff
diff --git a/extension/manifest.json b/extension/manifest.json
index 20320b2..476c955 100644
--- a/extension/manifest.json
+++ b/extension/manifest.json
@@ -1,7 +1,7 @@
 {
   "manifest_version": 3,
   "name": "SolMarginTrader",
-  "version": "0.5.0",
+  "version": "0.5.1",
   "description": "Signal Desk: live signals, backtests, paper forward tests and bot monitoring. Experimental grid installs disarmed in dry-run.",
   "minimum_chrome_version": "120",
```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/package.json

```diff
diff --git a/extension/package.json b/extension/package.json
index 31dce2c..119763f 100644
--- a/extension/package.json
+++ b/extension/package.json
@@ -1,6 +1,6 @@
 {
   "name": "solmargintrader",
-  "version": "0.5.0",
+  "version": "0.5.1",
   "private": true,
   "type": "module",
   "description": "Signal Desk: live signals, backtests, paper forward tests and bot monitoring. Experimental grid installs disarmed in dry-run.",
```

### /Users/mitch/dev/solmargintrader/extension/src/bg/paper-venue.js

```diff
diff --git a/extension/src/bg/paper-venue.js b/extension/src/bg/paper-venue.js
new file mode 100644
index 0000000..996b77e
--- /dev/null
+++ b/extension/src/bg/paper-venue.js
@@ -0,0 +1,39 @@
+/** Durable simulated venue state. Called inside the command's store lock. */
+export async function restorePaperVenue(venue, config, state) {
+  const key = `paperVenue:${JSON.stringify([config.venue, config.baseMint, config.quoteMint,
+    config.userPubkey, config.gridId])}`;
+  const saved = await state.get(key, null);
+  if (saved !== null) {
```
33 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/bg/service-worker.js

```diff
diff --git a/extension/src/bg/service-worker.js b/extension/src/bg/service-worker.js
index 223aae8..292f829 100644
--- a/extension/src/bg/service-worker.js
+++ b/extension/src/bg/service-worker.js
@@ -25,6 +25,7 @@ import { createNativeTransport } from './soltui-transport.js';
 import { DEFAULT_LIMITS } from '../core/risk.js';
 import { RequestBudget } from '../jupiter/http.js';
 import { makeSigner } from '../wallet/signer.js';
+import { restorePaperVenue } from './paper-venue.js';

 const ALARM = 'solmargintrader-tick';

```
19 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/bg/soltui-transport.js

```diff
diff --git a/extension/src/bg/soltui-transport.js b/extension/src/bg/soltui-transport.js
index ebb7a66..45ab9eb 100644
--- a/extension/src/bg/soltui-transport.js
+++ b/extension/src/bg/soltui-transport.js
@@ -94,6 +94,7 @@ export function createNativeTransport({
   const pending = new Map();
   let port = null;
   let generation = 0;
+  let oneShotPending = 0;

   function closeIfIdle() {
     if (leases.size || pending.size || !port) return;
```
21 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/core/commands.js

```diff
diff --git a/extension/src/core/commands.js b/extension/src/core/commands.js
index 7be01ce..0659a50 100644
--- a/extension/src/core/commands.js
+++ b/extension/src/core/commands.js
@@ -503,6 +503,9 @@ export const COMMANDS = {

   ackAlerts: {
     describe: 'Acknowledge one alert by id, or all current alerts, so it stops showing as new.',
+    // alertQueue already serializes these keys. Waiting for a scan must not
+    // prevent the engine from reconciling or applying new safety limits.
+    unlocked: true,
     params: [
```
2 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/core/csv.js

```diff
diff --git a/extension/src/core/csv.js b/extension/src/core/csv.js
new file mode 100644
index 0000000..dc87e7d
--- /dev/null
+++ b/extension/src/core/csv.js
@@ -0,0 +1,10 @@
+/** Render external text as text in spreadsheets; numeric cells remain numeric. */
+export function spreadsheetText(value) {
+  const text = String(value ?? '');
+  return typeof value === 'string' && /^[\s\x00-\x1f]*[=+@-]/.test(text) ? `'${text}` : text;
+}
+
```
4 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/core/engine.js

```diff
diff --git a/extension/src/core/engine.js b/extension/src/core/engine.js
index 1559fce..d5dfb57 100644
--- a/extension/src/core/engine.js
+++ b/extension/src/core/engine.js
@@ -282,11 +282,36 @@ async function ingestFillsUnlocked({ venue, store, config, log = () => {} }) {
  *
  * @returns a summary the popup and dashboard render directly.
  */
+const DIAGNOSTIC_KINDS = new Set(['Error', 'TypeError', 'RangeError', 'SyntaxError',
+  'HttpError', 'TimeoutError', 'AbortError', 'CommandError']);
+
+function diagnosticError(error, stage) {
```
113 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/core/pnl.js

```diff
diff --git a/extension/src/core/pnl.js b/extension/src/core/pnl.js
index 3d3ce59..b967142 100644
--- a/extension/src/core/pnl.js
+++ b/extension/src/core/pnl.js
@@ -1,3 +1,5 @@
+import { csvCell } from './csv.js';
+
 /**
  * P&L accounting.
  *
@@ -222,12 +224,10 @@ export function maxDrawdown(points) {
   for (const p of points) {
```
24 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/ui/soltui-panel.js

```diff
diff --git a/extension/src/ui/soltui-panel.js b/extension/src/ui/soltui-panel.js
index 10ed146..e3dd426 100644
--- a/extension/src/ui/soltui-panel.js
+++ b/extension/src/ui/soltui-panel.js
@@ -188,6 +188,7 @@ export function mountSoltuiPanel(root = document, transport = send) {
   let runButton = null;
   let editor = null;
   let editorBase = null;
+  let editorRevision = null;
   let documentPath = null;
   let documentEpoch = 0;
   let lastEnvelope = null;
```
57 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/src/ui/workspace-model.js

```diff
diff --git a/extension/src/ui/workspace-model.js b/extension/src/ui/workspace-model.js
index ed3cfa3..3fd796e 100644
--- a/extension/src/ui/workspace-model.js
+++ b/extension/src/ui/workspace-model.js
@@ -1,3 +1,5 @@
+import { spreadsheetText } from '../core/csv.js';
+
 /** Registry-derived navigation and result adapters shared by the dashboard and tests. */
 export const WORKSPACES = [
   { id: 'now', title: 'Now', detail: 'Processes, prices, current recommendations and saved results.', tools: ['prices.status', 'backtest.status', 'queue.progress', 'forwardtest.state', 'compound.autopilot_status', 'bots.schedule_status', 'portfolio.last'] },
@@ -37,9 +39,7 @@ export function columnsFor(rows) {
 export function rowsToCsv(rows) {
```
9 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/test/cdo-regressions.test.js

```diff
diff --git a/extension/test/cdo-regressions.test.js b/extension/test/cdo-regressions.test.js
new file mode 100644
index 0000000..0ac551c
--- /dev/null
+++ b/extension/test/cdo-regressions.test.js
@@ -0,0 +1,205 @@
+import test from 'node:test';
+import assert from 'node:assert/strict';
+import { mkdtempSync, cpSync, rmSync } from 'node:fs';
+import { tmpdir } from 'node:os';
+import { join, dirname } from 'node:path';
+import { fileURLToPath } from 'node:url';
```
199 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/test/service-worker.test.js

```diff
diff --git a/extension/test/service-worker.test.js b/extension/test/service-worker.test.js
index c4ec9c0..b683901 100644
--- a/extension/test/service-worker.test.js
+++ b/extension/test/service-worker.test.js
@@ -253,3 +253,23 @@ test('runBuildCheck preserves dashboard session state until its lease ends', asy
   assert.equal(await runBuildCheck({ ...common, soltui: host }), 'reloaded');
   assert.equal(reloads.length, 1);
 });
+
+
+test('Chrome paper orders and fills survive dependency and worker recreation', async () => {
+  reset();
```
16 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/test/wallet-pubkey.test.js

```diff
diff --git a/extension/test/wallet-pubkey.test.js b/extension/test/wallet-pubkey.test.js
index ff869bc..adda7ea 100644
--- a/extension/test/wallet-pubkey.test.js
+++ b/extension/test/wallet-pubkey.test.js
@@ -125,9 +125,9 @@ test('the dashboard has the button, loads the module, and the module uses textCo
   assert.ok(!/wallet\.private|solana\.private|xpub/i.test(code.replace(/the extension|never an extended/g, '')), 'no key material handling');
 });

-test('the manifest and package agree on the version (0.5.0, Signal Desk)', async () => {
+test('the manifest and package agree on the version (0.5.1, Signal Desk)', async () => {
   const manifest = JSON.parse(await readFile(join(ROOT, 'manifest.json'), 'utf8'));
   const pkg = JSON.parse(await readFile(join(ROOT, 'package.json'), 'utf8'));
```
4 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/tools/api-server.js

```diff
diff --git a/extension/tools/api-server.js b/extension/tools/api-server.js
index d5c2b71..236d68c 100644
--- a/extension/tools/api-server.js
+++ b/extension/tools/api-server.js
@@ -29,6 +29,8 @@

 import { createServer } from 'node:http';
 import { timingSafeEqual } from 'node:crypto';
+import { fileURLToPath } from 'node:url';
+import { realpathSync } from 'node:fs';
 import { runCommand, describeCommands, COMMANDS, CommandError } from '../src/core/commands.js';
 import { createNodeDeps } from './deps.js';
```
43 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/extension/tools/e2e.mjs

```diff
diff --git a/extension/tools/e2e.mjs b/extension/tools/e2e.mjs
index ebb0324..cc0ebad 100644
--- a/extension/tools/e2e.mjs
+++ b/extension/tools/e2e.mjs
@@ -26,6 +26,7 @@

 import fs from 'node:fs';
 import path from 'node:path';
+import { createHash } from 'node:crypto';
 import { fileURLToPath } from 'node:url';
 import { findChromeForTesting, launch } from '../e2e/lib/cdp.mjs';
 import { execFile } from 'node:child_process';
```
22 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/cli.py

```diff
diff --git a/liquidity/src/aero_lp/cli.py b/liquidity/src/aero_lp/cli.py
index b88e29a..acaf9c2 100644
--- a/liquidity/src/aero_lp/cli.py
+++ b/liquidity/src/aero_lp/cli.py
@@ -379,13 +379,16 @@ def cmd_pnl(a: argparse.Namespace) -> int:


 def cmd_run(a: argparse.Namespace) -> int:
-    cfg, eng = _engine(a)
+    cfg = load(a.config)
+    # Engine construction reads the chain. Refuse from the same loaded config
+    # before any RPC or signer access, as the daemon entry point does.
```
12 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/daemon.py

```diff
diff --git a/liquidity/src/aero_lp/daemon.py b/liquidity/src/aero_lp/daemon.py
index b64aa1f..043be9d 100644
--- a/liquidity/src/aero_lp/daemon.py
+++ b/liquidity/src/aero_lp/daemon.py
@@ -198,10 +198,28 @@ def known_prices(self) -> dict[str, float]:
     def eth_usd(self) -> float:
         return self.known_prices().get(addresses.WETH.lower(), 0.0)

-    def runner(self, tokens: list[str], pool: str | None) -> Any:
+    def runner(
+        self,
+        tokens: list[str],
```
114 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/engine.py

```diff
diff --git a/liquidity/src/aero_lp/engine.py b/liquidity/src/aero_lp/engine.py
index 74b4558..63b9035 100644
--- a/liquidity/src/aero_lp/engine.py
+++ b/liquidity/src/aero_lp/engine.py
@@ -143,9 +143,13 @@ def recover_submission(self, record: dict[str, Any], group: list[dict[str, Any]]
         for slot in self.state.slots.values():
             if slot.current_token_id in old_ids or slot.current_token_id == token_id:
                 slot.current_token_id = token_id
-                slot.last_rebalance_ts = slot.last_rebalance_ts or time.time()
                 if not any(record["hash"] in h.get("tx", []) for h in slot.history):
-                    slot.history.append({"ts": time.time(), "new": token_id, "tx": [record["hash"]], "recovered": True})
+                    recovered_at = time.time()
```
22 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/executor.py

```diff
diff --git a/liquidity/src/aero_lp/executor.py b/liquidity/src/aero_lp/executor.py
index 0999267..e2cde24 100644
--- a/liquidity/src/aero_lp/executor.py
+++ b/liquidity/src/aero_lp/executor.py
@@ -207,10 +207,12 @@ def __init__(
         pool: str | None = None,
         *,
         journal: SubmissionJournal | None = None,
+        accounting: dict[str, str] | None = None,
     ):
         self.chain, self.acct, self.tokens, self.cfg, self.pool = chain, account, tokens, cfg, pool
         self.w3 = chain.w3
```
70 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/gates.py

```diff
diff --git a/liquidity/src/aero_lp/gates.py b/liquidity/src/aero_lp/gates.py
index f7c76a6..ca9df5f 100644
--- a/liquidity/src/aero_lp/gates.py
+++ b/liquidity/src/aero_lp/gates.py
@@ -17,15 +17,18 @@

 from __future__ import annotations

+import fcntl
 import hashlib
 import json
 import time
```
143 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/recovery.py

```diff
diff --git a/liquidity/src/aero_lp/recovery.py b/liquidity/src/aero_lp/recovery.py
index aaee5ac..6026b29 100644
--- a/liquidity/src/aero_lp/recovery.py
+++ b/liquidity/src/aero_lp/recovery.py
@@ -49,6 +49,19 @@ def _pool_has_aero(pool: PoolState | None) -> bool:
     def _group_slot(self, group: list[dict[str, Any]]) -> str | None:
         """Resolve once from durable identities, then persist before closing/replacing an NFT."""
         slots = {s for r in group if (s := self.ledger.transaction_slot(r["hash"])) is not None}
+        wallet_scope = False
+        for record in group:
+            context = record.get("accounting")
+            if context is None:
```
37 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/safe_exit.py

```diff
diff --git a/liquidity/src/aero_lp/safe_exit.py b/liquidity/src/aero_lp/safe_exit.py
index 8e5e47b..d1f5079 100644
--- a/liquidity/src/aero_lp/safe_exit.py
+++ b/liquidity/src/aero_lp/safe_exit.py
@@ -153,6 +153,22 @@ def _value_usd(pos: PositionState, prices: dict[str, float], amounts: tuple[int,
     return amounts[0] / 10**pos.pool.token0.decimals * p0 + amounts[1] / 10**pos.pool.token1.decimals * p1


+def _conversion_steps(
+    pos: PositionState, amounts: tuple[int, int], aero_claimed: int, target: str
+) -> list[ConvertStep]:
+    """Separate exact receipt proceeds from every pre-existing wallet balance."""
```
67 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/strategy.py

```diff
diff --git a/liquidity/src/aero_lp/strategy.py b/liquidity/src/aero_lp/strategy.py
index 0b1af42..6c54e54 100644
--- a/liquidity/src/aero_lp/strategy.py
+++ b/liquidity/src/aero_lp/strategy.py
@@ -23,6 +23,7 @@
 from enum import StrEnum

 from . import clmath
+from .validation import finite_number


 class Action(StrEnum):
```
18 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/src/aero_lp/submissions.py

```diff
diff --git a/liquidity/src/aero_lp/submissions.py b/liquidity/src/aero_lp/submissions.py
index ebabd85..0d59a76 100644
--- a/liquidity/src/aero_lp/submissions.py
+++ b/liquidity/src/aero_lp/submissions.py
@@ -119,6 +119,10 @@ def _read(self) -> dict[str, Any]:
         doc = json.loads(self.path.read_text())
         if doc.get("version") != 1 or doc.get("owner", "").lower() != self.owner.lower():
             raise PendingSubmission("submission journal owner or version does not match")
+        if not isinstance(doc.get("ledger_path"), str) or not doc["ledger_path"]:
+            raise PendingSubmission("submission journal has no valid ledger binding")
+        if self.ledger_path is not None and Path(doc["ledger_path"]).resolve() != self.ledger_path:
+            raise PendingSubmission("submission journal is bound to a different ledger")
```
31 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_cdo_execution.py

```diff
diff --git a/liquidity/tests/test_cdo_execution.py b/liquidity/tests/test_cdo_execution.py
new file mode 100644
index 0000000..2949ec0
--- /dev/null
+++ b/liquidity/tests/test_cdo_execution.py
@@ -0,0 +1,52 @@
+"""Mock-only confirmed outcome and cooldown regressions."""
+
+from types import SimpleNamespace
+
+import pytest
+from test_engine import make_engine
```
46 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_cdo_gates.py

```diff
diff --git a/liquidity/tests/test_cdo_gates.py b/liquidity/tests/test_cdo_gates.py
new file mode 100644
index 0000000..e56a8f5
--- /dev/null
+++ b/liquidity/tests/test_cdo_gates.py
@@ -0,0 +1,108 @@
+"""Offline regressions for finite, durable pre-live evidence."""
+
+from __future__ import annotations
+
+import json
+from concurrent.futures import ThreadPoolExecutor
```
102 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_cdo_recovery.py

```diff
diff --git a/liquidity/tests/test_cdo_recovery.py b/liquidity/tests/test_cdo_recovery.py
new file mode 100644
index 0000000..80a0880
--- /dev/null
+++ b/liquidity/tests/test_cdo_recovery.py
@@ -0,0 +1,252 @@
+"""Synthetic receipt groups and isolated ledgers; no chain or keys."""
+
+from types import SimpleNamespace
+
+import pytest
+from test_daemon import AERO, GAUGE, MAIN_TICK, OWNER, USDC, WETH, make_pool, make_pos, tick_for
```
246 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_daemon.py

```diff
diff --git a/liquidity/tests/test_daemon.py b/liquidity/tests/test_daemon.py
index d05e2af..7b516d2 100644
--- a/liquidity/tests/test_daemon.py
+++ b/liquidity/tests/test_daemon.py
@@ -255,7 +255,7 @@ def sim(chain_, owner, tokens, pool=None):
         constructed.append(("sim", chain_, owner, tokens, pool))
         return ("sim", (chain_, owner, tokens, pool))

-    def live(chain_, signer, tokens, cfg, pool=None, *, journal=None):
+    def live(chain_, signer, tokens, cfg, pool=None, *, journal=None, accounting=None):
         constructed.append(("live", chain_, signer, tokens, pool))
         return ("live", (chain_, signer, tokens, pool))
```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_gates.py

```diff
diff --git a/liquidity/tests/test_gates.py b/liquidity/tests/test_gates.py
index 8c190bf..2a4f46f 100644
--- a/liquidity/tests/test_gates.py
+++ b/liquidity/tests/test_gates.py
@@ -183,6 +183,7 @@ def test_cli_refuses_live_daemon_before_touching_the_signer(tmp_path, monkeypatc
     cfgfile.write_text(f'owner = "{OWNER}"\n')
     monkeypatch.setattr("aero_lp.wallet.load_signer", lambda *a, **k: pytest.fail("signer must not load"))
     monkeypatch.setattr(cli, "AeroChain", lambda *a, **k: pytest.fail("no chain access before the gate"))
+    monkeypatch.setattr(cli, "Engine", lambda *a, **k: pytest.fail("no engine construction before the gate"))
     assert cli.main(["daemon", "-c", str(cfgfile), "--live"]) == 3
     assert "refusing live mode" in capsys.readouterr().err
     assert cli.main(["run", "-c", str(cfgfile), "--live", "--once"]) == 3
```

### /Users/mitch/dev/solmargintrader/liquidity/tests/test_safe_exit.py

```diff
diff --git a/liquidity/tests/test_safe_exit.py b/liquidity/tests/test_safe_exit.py
index 960b0dd..cc61ce3 100644
--- a/liquidity/tests/test_safe_exit.py
+++ b/liquidity/tests/test_safe_exit.py
@@ -57,6 +57,9 @@ def pool_blocks(self, pool, live):
     def _gate(self):
         self.gated += 1

+    def reconcile_submissions(self):
+        pass
+

```
183 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/memory.md

```diff
diff --git a/memory.md b/memory.md
index 95f3e94..f8c2344 100644
--- a/memory.md
+++ b/memory.md
@@ -1,7 +1,77 @@
 # Work continuation

-Version: 256
-Delta: v255 to v256; preserve concurrent executor and Signal Desk histories and integration checkpoint.
+Version: 266
+Delta: v265 to v266; preserve all upstream and optimizer workflow histories.
+
```
72 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/mongo/README.md

```diff
diff --git a/mongo/README.md b/mongo/README.md
index ef9818a..b524a1f 100644
--- a/mongo/README.md
+++ b/mongo/README.md
@@ -179,3 +179,11 @@ ## Scope
 reaches no network, and touches no database other than `solmargintrader`. Nothing
 in `backtester/`, `research/`, `extension/` or `soltui/` imports it, so the store
 can be rebuilt or dropped without affecting any of them.
+
+## Rebuilding without deleting test receipts
+
+`python3 mongo/schema.py --create` rebuilds derived collections, but retains `test_results`
```
4 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/mongo/load.py

```diff
diff --git a/mongo/load.py b/mongo/load.py
index 522a8b9..889e38a 100644
--- a/mongo/load.py
+++ b/mongo/load.py
@@ -5,14 +5,10 @@
     python3 mongo/load.py --only bars,strategies
     python3 mongo/load.py --dry-run        # count what would load, write nothing

-**This loader is destructive by design and idempotent by consequence.** It drops
-and recreates every collection it writes. That is not laziness: a time series
-collection accepts no unique index, so there is no upsert key and no database-level
-guard against loading the same series twice -- a second run would silently double
```
162 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/mongo/schema.py

```diff
diff --git a/mongo/schema.py b/mongo/schema.py
index 8aee860..5987280 100644
--- a/mongo/schema.py
+++ b/mongo/schema.py
@@ -1,6 +1,6 @@
 """Collection layout for the local research store: specs, validators, indexes.

-    python3 mongo/schema.py --create      # create everything (drops first)
+    python3 mongo/schema.py --create      # rebuild derived data; retain test receipts
     python3 mongo/schema.py --describe    # print the layout, touch nothing

 Design notes, because the shape is the part worth arguing about:
```
70 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/mongo/tests/test_analysis_regressions.py

```diff
diff --git a/mongo/tests/test_analysis_regressions.py b/mongo/tests/test_analysis_regressions.py
new file mode 100644
index 0000000..0608b19
--- /dev/null
+++ b/mongo/tests/test_analysis_regressions.py
@@ -0,0 +1,198 @@
+"""Mongo contracts tested with byte snapshots and fake collections only."""
+from __future__ import annotations
+
+import contextlib
+import hashlib
+import io
```
192 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/prompts.md

```diff
diff --git a/prompts.md b/prompts.md
index eb7ef64..b66f9da 100644
--- a/prompts.md
+++ b/prompts.md
@@ -1,7 +1,13 @@
 # Prompt history

-Version: 136
-Delta: v135 to v136; preserve repository review and approved Signal Desk implementation requests.
+Version: 137
+Delta: v136 to v137; preserve all upstream and optimizer workflow histories.
+
```
8 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/research/cpcv_sweep.py

```diff
diff --git a/research/cpcv_sweep.py b/research/cpcv_sweep.py
index 9816a1e..052b672 100644
--- a/research/cpcv_sweep.py
+++ b/research/cpcv_sweep.py
@@ -21,6 +21,7 @@
 import json
 import sys
 from pathlib import Path
+from typing import Any, Sequence

 import numpy as np
 import pandas as pd
```
117 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/research/decide.py

```diff
diff --git a/research/decide.py b/research/decide.py
index 988b68a..967ffd7 100644
--- a/research/decide.py
+++ b/research/decide.py
@@ -409,6 +409,12 @@ def _threshold_reading(
     return NEUTRAL


+
+def _comparison_reading(left: float, right: float) -> str:
+    if not (np.isfinite(left) and np.isfinite(right)):
+        return UNAVAILABLE
```
103 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/research/evidence.py

```diff
diff --git a/research/evidence.py b/research/evidence.py
new file mode 100644
index 0000000..2b00368
--- /dev/null
+++ b/research/evidence.py
@@ -0,0 +1,69 @@
+"""Stable experiment identities and byte-bound discovery gate evidence."""
+from __future__ import annotations
+
+import hashlib
+import io
+import json
```
63 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/research/signal_redundancy.py

```diff
diff --git a/research/signal_redundancy.py b/research/signal_redundancy.py
index 0f81ba4..1c04ecb 100644
--- a/research/signal_redundancy.py
+++ b/research/signal_redundancy.py
@@ -28,11 +28,11 @@

 Four design rules, each guarding a specific way this measurement can lie:

-  * **The walk starts at bar 0, always.** Several strategies are stateful (a
-    `_holding` flag derived from past decisions). Their exposure at bar k
-    depends on every bar before k, so the walk cannot be started at the burn-in
-    boundary -- doing so would fabricate an entry state. Burn-in is removed
```
181 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/research/sweep.py

```diff
diff --git a/research/sweep.py b/research/sweep.py
index f6ff6f1..278b1a2 100644
--- a/research/sweep.py
+++ b/research/sweep.py
@@ -304,7 +304,7 @@ def walk_forward(
 ) -> tuple[Metrics, Metrics | None, Metrics | None]:
     """Run full-sample, in-sample, and out-of-sample legs.

-    The out-of-sample slice deliberately starts `warmup` bars BEFORE the split
+    The out-of-sample slice starts `warmup + fill_delay` bars BEFORE the split
     so indicators warm from trailing in-sample bars; trading therefore begins
     exactly at the split. Reading earlier history is not look-ahead, and
```
163 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/README.md

```diff
diff --git a/soltui/README.md b/soltui/README.md
index a5e15f3..c35530f 100644
--- a/soltui/README.md
+++ b/soltui/README.md
@@ -562,6 +562,11 @@ ## Safety
   by `validate()` with an explanatory error.
 - **Manual order arming is session-only.** The Wallet form starts disarmed each time the
   console starts; the simulation setting `armed` does not arm Coinbase orders.
+- **Manual Jupiter V2 submission is unavailable.** The app retains unsigned previews with
+  structural checks, history and chain reconciliation. Submit and quick-submit refuse before
+  key loading, signing or sending because independent economic verification is incomplete.
+  Missing input valuation refuses the preview. Historical unknown submissions remain blocking;
```
4 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/bots.py

```diff
diff --git a/soltui/bots.py b/soltui/bots.py
index 0777c0c..2b920d9 100644
--- a/soltui/bots.py
+++ b/soltui/bots.py
@@ -110,6 +110,7 @@
 MIN_BACKTEST_BARS = 24
 MIN_HOUR_MINUTES = 30  # an hour resampled from 1m needs this many minutes, or it counts as missing
 MAX_FORWARD_GAP_MIN = 2
+MAX_FORWARD_QUOTE_AGE_S = 5.0
 OPTIMIZE_WINDOWS = 6
 PER_COIN_OPTIMIZE_WINDOWS = 6  # half are holdout; incremental decisions are labeled tentative
 PER_COIN_MIN_DECIDED_CELLS = 3
```
152 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/coinbase_manual.py

```diff
diff --git a/soltui/coinbase_manual.py b/soltui/coinbase_manual.py
index f8c1c2c..4a38d13 100644
--- a/soltui/coinbase_manual.py
+++ b/soltui/coinbase_manual.py
@@ -316,10 +316,22 @@ def status(order_id: str, call: Callable[[list[str]], dict[str, Any]] | None = N
             raise ValueError('Coinbase returned a different order')
         for p in _dir().glob('*.json'):
             record = _read(p)
-            if record.get('order_id') == order_id:
-                if result.get('product_id') != record.get('product_id') or result.get('side') != record.get('side'):
+            known_order = record.get('order_id') == order_id
+            recovered_order = (not record.get('order_id')
```
20 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/commands.py

```diff
diff --git a/soltui/commands.py b/soltui/commands.py
index c22bafa..b920629 100644
--- a/soltui/commands.py
+++ b/soltui/commands.py
@@ -746,19 +746,22 @@ def _forward_runner(rt: "Runtime") -> None:
             now = time.time()
             minute = int(now // 60)
             if minute != checked_minute and now % 60 >= FORWARD_GRACE_S:
-                checked_minute = minute
                 with rt.lock:
-                    rt.forward_busy = True
-                try:
```
107 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/config.py

```diff
diff --git a/soltui/config.py b/soltui/config.py
index 24fc069..8e07604 100644
--- a/soltui/config.py
+++ b/soltui/config.py
@@ -20,6 +20,7 @@
 import json
 import math
 import os
+import tempfile
 from dataclasses import asdict, dataclass, field, fields
 from pathlib import Path
 from typing import Any
```
84 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/docs_browser.py

```diff
diff --git a/soltui/docs_browser.py b/soltui/docs_browser.py
index cfc14e4..b8953cb 100644
--- a/soltui/docs_browser.py
+++ b/soltui/docs_browser.py
@@ -1,7 +1,7 @@
 """Read-only catalogue and file reader behind the Docs tab.

-Pure logic: no Textual import, no widget, no I/O beyond reading files the
-catalogue already lists. That split is what lets this be tested without driving a
+No Textual import or widgets. Reads are limited to catalogued files; guarded
+saves use content revisions, per-document locks, and atomic replacements. That split is what lets this be tested without driving a
 terminal, and it matches `config.py`, `roster.py` and the other modules the TUI
```
111 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/experiment_jobs.py

```diff
diff --git a/soltui/experiment_jobs.py b/soltui/experiment_jobs.py
index 2581e8a..b797213 100644
--- a/soltui/experiment_jobs.py
+++ b/soltui/experiment_jobs.py
@@ -73,7 +73,8 @@ def status(store: ExperimentStore, run_id: str) -> dict[str, Any]:
                     with log.open("rb") as output:
                         output.seek(max(0, log.stat().st_size - 2000))
                         message += "\n" + output.read().decode("utf-8", errors="replace").strip()
-                run = store.update_run(run_id, status=state, error=message if state == "interrupted" else None)
+                run = store.settle_run(run_id, status=state, expected=[run["status"]],
+                                       error=message if state == "interrupted" else None)
             fcntl.flock(fh, fcntl.LOCK_UN)
```
22 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/experiment_runner.py

```diff
diff --git a/soltui/experiment_runner.py b/soltui/experiment_runner.py
index c9ece6b..34e42fb 100644
--- a/soltui/experiment_runner.py
+++ b/soltui/experiment_runner.py
@@ -30,7 +30,6 @@

 SCHEMA_VERSION = 1
 MAX_EVALUATIONS = 20_000
-_CONTROL = {"pause_requested": "paused", "cancel_requested": "cancelled"}


 def _canonical(value: Any) -> str:
```
26 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/experiments.py

```diff
diff --git a/soltui/experiments.py b/soltui/experiments.py
index 7ebe802..523770a 100644
--- a/soltui/experiments.py
+++ b/soltui/experiments.py
@@ -206,6 +206,32 @@ def transition_run(self, run_id: str, status: str, *, expected: list[str] | tupl
                 db.execute("UPDATE runs SET status=?,updated_at=? WHERE id=?", (status, time.time(), run_id))
         return {**self.get_run(run_id), "transition_applied": applied}

+    def settle_run(self, run_id: str, *, status: str | None = None,
+                   expected: list[str] | tuple[str, ...] = (), error: Any = _UNSET) -> dict[str, Any]:
+        """Acknowledge control or conditionally settle an exit in one transaction.
+
```
25 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/forwardtest.py

```diff
diff --git a/soltui/forwardtest.py b/soltui/forwardtest.py
index 1893f7f..6acb0fa 100644
--- a/soltui/forwardtest.py
+++ b/soltui/forwardtest.py
@@ -353,14 +353,30 @@ def get(url: str):
     ts = raw["ts"]
     if len(ts) == 0 or np.any(np.diff(ts) <= 0) or np.any(ts % 60):
         raise ValueError("No ordered closed one-minute candles")
-    # Save received closed candles before strategy calculation or a later fetch can fail.
-    with closing(_db(db_path)) as db, db:
-        db.executemany("INSERT OR IGNORE INTO candle VALUES (?,?,?,?,?,?,?)", (
-            (asset, int(t), float(o), float(h), float(l), float(c), float(v))
```
86 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/jupiter_manual.py

```diff
diff --git a/soltui/jupiter_manual.py b/soltui/jupiter_manual.py
index 54bfd24..6fd8186 100644
--- a/soltui/jupiter_manual.py
+++ b/soltui/jupiter_manual.py
@@ -1,15 +1,14 @@
-"""Explicitly reviewed Jupiter Swap API v2 spot orders with semantic verification and disk locking.
+"""Unsigned Jupiter Swap API v2 previews with structural checks and disk locking.

-Never retries an ambiguous submission.
-Enforces $100 MAX_QUOTE cap.
-Requires verified token metadata, positive price valuation, and semantic transaction verification.
+Enforces the $100 input-value cap using positive independent USD valuation.
```
330 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/jupiter_tokens.py

```diff
diff --git a/soltui/jupiter_tokens.py b/soltui/jupiter_tokens.py
index 5c72b86..b5ca15d 100644
--- a/soltui/jupiter_tokens.py
+++ b/soltui/jupiter_tokens.py
@@ -2,6 +2,7 @@
 from __future__ import annotations

 import json
+import math
 import os
 import re
 import urllib.parse
```
16 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/native_host.py

```diff
diff --git a/soltui/native_host.py b/soltui/native_host.py
index 5897ff9..b07cf0b 100644
--- a/soltui/native_host.py
+++ b/soltui/native_host.py
@@ -91,15 +91,31 @@ def build_hash(root: Path | None = None) -> dict[str, Any]:


 def _reply(request_id: Any, envelope: dict[str, Any]) -> bytes:
-    body = ('{"id":%s,"response":%s}' % (json.dumps(request_id), commands.dumps(envelope))).encode()
+    encoded_id = json.dumps(request_id)
+    if len(encoded_id) > 4096:
+        encoded_id = "null"
```
53 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/native_host_install.py

```diff
diff --git a/soltui/native_host_install.py b/soltui/native_host_install.py
index 20c2f10..6ac19a7 100644
--- a/soltui/native_host_install.py
+++ b/soltui/native_host_install.py
@@ -16,6 +16,7 @@
 import argparse
 import json
 import os
+import shlex
 import stat
 import sys
 from pathlib import Path
```
9 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/pricefeed.py

```diff
diff --git a/soltui/pricefeed.py b/soltui/pricefeed.py
index 39ae4de..17018cf 100644
--- a/soltui/pricefeed.py
+++ b/soltui/pricefeed.py
@@ -12,7 +12,7 @@

 * **Subscribes** to `wss://ws-feed.exchange.coinbase.com` for every USD market of the cached
   coins that Coinbase lists plus every cross pair among them (`stream_products`), on two
-  public channels. `level2_batch` sends a book snapshot and then batched changes every 50 ms;
+  public channels plus a heartbeat. `level2_batch` sends a book snapshot and then batched changes every 50 ms;
   `Book` keeps each product's book, which gives the true best bid and ask with their sizes.
   `ticker` arrives on each trade and gives the last price.
```
473 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/bridge_support.py

```diff
diff --git a/soltui/tests/bridge_support.py b/soltui/tests/bridge_support.py
index ab18877..6688825 100644
--- a/soltui/tests/bridge_support.py
+++ b/soltui/tests/bridge_support.py
@@ -153,7 +153,7 @@ def default_params() -> dict[str, dict]:
         "live.spawn_dryrun": {"strategy": "buy_and_hold"},
         "analyze.run": {"asset": "SOL"},
         "docs.read": {"path": "soltui/commands.py"},
-        "docs.write": {"path": "scratch.txt", "text": "x"},
+        "docs.write": {"path": "scratch.txt", "text": "x", "expected_revision": "a" * 64},
         "liquidity.resume": {"confirm": True},
         "queue.backtest": {"scope": "all"},
```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_bots.py

```diff
diff --git a/soltui/tests/test_bots.py b/soltui/tests/test_bots.py
index ac158c2..b172cee 100644
--- a/soltui/tests/test_bots.py
+++ b/soltui/tests/test_bots.py
@@ -332,7 +332,7 @@ def test_minute_bars_bridge_short_gaps_and_stop_at_long_ones(self) -> None:
         for minute in (0, 1, 3, 4, 10):  # minute 2 missing (bridged), 5..9 missing (gap)
             for sec in (0, 30):
                 mid = 100.0 + minute
-                mb.feed(t0 + minute * 60 + sec, {"SOL-USD": [mid - 0.01, mid + 0.01, mid, 1, 1, 0]})
+                mb.feed(t0 + minute * 60 + sec, {"SOL-USD": (mid - 0.01, mid + 0.01, 1, 1, t0 + minute * 60 + sec)})
         arrays, gap, bridged = mb.arrays(before=t0 + 11 * 60)
         self.assertEqual(list((arrays["ts"] - t0) // 60), [0, 1, 2, 3, 4])
```
1 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_bridge_surfaces.py

```diff
diff --git a/soltui/tests/test_bridge_surfaces.py b/soltui/tests/test_bridge_surfaces.py
index d36aff3..a4fa2db 100644
--- a/soltui/tests/test_bridge_surfaces.py
+++ b/soltui/tests/test_bridge_surfaces.py
@@ -352,8 +352,8 @@ def test_install_status_uninstall_roundtrip(self) -> None:
             self.assertEqual(len(result["manifests"]), 2)
             self.assertTrue(os.access(wrapper, os.X_OK))
             text = wrapper.read_text()
-            self.assertIn('exec "/venv/bin/python" -m soltui.native_host', text)
-            self.assertIn('cd "/repo/x"', text)
+            self.assertIn('/venv/bin/python', text)
+            self.assertIn('/repo/x', text)
```
3 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_cdo_tui_regressions.py

```diff
diff --git a/soltui/tests/test_cdo_tui_regressions.py b/soltui/tests/test_cdo_tui_regressions.py
new file mode 100644
index 0000000..1466b22
--- /dev/null
+++ b/soltui/tests/test_cdo_tui_regressions.py
@@ -0,0 +1,585 @@
+"""Offline safety regressions for the reviewed manual paths and paper state."""
+from __future__ import annotations
+
+import io
+import json
+import os
```
579 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_docs_browser.py

```diff
diff --git a/soltui/tests/test_docs_browser.py b/soltui/tests/test_docs_browser.py
index ca68d2c..5320bdb 100644
--- a/soltui/tests/test_docs_browser.py
+++ b/soltui/tests/test_docs_browser.py
@@ -67,7 +67,8 @@ def test_writes_and_round_trips_through_read_document(self) -> None:
         target.write_text("old\n", encoding="utf-8")
         entries = [_entry("soltui/app.py")]

-        written = docs_browser.write_document("soltui/app.py", "new\n", entries)
+        written = docs_browser.write_document("soltui/app.py", "new\n", entries,
+                                             expected_revision=docs_browser.document_revision("old\n"))

```
2 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_jupiter_manual.py

```diff
diff --git a/soltui/tests/test_jupiter_manual.py b/soltui/tests/test_jupiter_manual.py
index 56eb11d..9fec42f 100644
--- a/soltui/tests/test_jupiter_manual.py
+++ b/soltui/tests/test_jupiter_manual.py
@@ -1,4 +1,4 @@
-"""Tests for explicit Jupiter manual orders: fail closed, semantic verification, disk locking."""
+"""Unsigned Jupiter previews, structural checks and conservative historic recovery."""
 from __future__ import annotations

 import base64
@@ -50,7 +50,8 @@ def valid_swap_ixs(owner: str, mint_in: str, mint_out: str, amount_in: int) -> l
         ]
```
118 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_lifecycle_regressions.py

```diff
diff --git a/soltui/tests/test_lifecycle_regressions.py b/soltui/tests/test_lifecycle_regressions.py
new file mode 100644
index 0000000..410e6b9
--- /dev/null
+++ b/soltui/tests/test_lifecycle_regressions.py
@@ -0,0 +1,303 @@
+"""Control identities, feed silence and experiment races, isolated from owner state."""
+from __future__ import annotations
+
+import gzip
+import json
+import os
```
297 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tests/test_pricefeed.py

```diff
diff --git a/soltui/tests/test_pricefeed.py b/soltui/tests/test_pricefeed.py
index 0f46583..574ffc6 100644
--- a/soltui/tests/test_pricefeed.py
+++ b/soltui/tests/test_pricefeed.py
@@ -246,7 +246,7 @@ def close(self) -> None:
                               flush_s=0.0)
             rec.run_once(max_seconds=5)
             sub = json.loads(FakeWS.sent[0])
-            self.assertEqual(sub["channels"], ["level2_batch", "ticker"])
+            self.assertEqual(sub["channels"], ["level2_batch", "ticker", "heartbeat"])
             self.assertGreater(rec.snapshots, 0)
             self.assertTrue(pf.recorded_files(Path(tmp)))
```
11 further patch lines omitted.

### /Users/mitch/dev/solmargintrader/soltui/tui.py

```diff
diff --git a/soltui/tui.py b/soltui/tui.py
index ac1f512..95b7cf0 100644
--- a/soltui/tui.py
+++ b/soltui/tui.py
@@ -1061,6 +1061,7 @@ def __init__(self, settings: Settings | None = None, *, ui_state_path: Path | No
         self._docs_highlighted_path: str | None = None
         # The text as it was on disk when _docs_current_path was loaded, to detect unsaved edits.
         self._docs_loaded_text = ""
+        self._docs_revision: str | None = None
         self._forward_running = False
         self._forward_busy = False
         self._forward_seen: dict[str, Any] = {}
```
23 further patch lines omitted.

## 6. Blind re-audit

The original gate2 retained15 corroborated findings. Already-delivered PR151 closed2 during source integration, leaving13. Integration is covered by source preservation checks,429 executor tests and application acceptance; it is not a third blind optimization gate. Some final-gate file coverage was partial.
One suggested backtester trend-exit finding was rejected: the documented filter constrains entry calls, not held positions. Changing that policy would invent behavior. Raw reviewer packets and the source-based triage are preserved.

Fresh contexts received final source and the pass rubric without author findings or diffs. The native agent API reached its thread limit; the final gate used ephemeral read-only Codex CLI contexts. Their JSON and process exit receipts are under /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-cdo. A non-clean exit has no CLEAN-gate claim.

## 7. Recommendations

N/A — `--suggest` was not requested. The deferred source inventory is scope accounting, not an advisory feature list.

## 8. Implemented features

N/A — `--implement-features` was not requested. Changes repair corroborated defects and their documented contracts.

## 9. Summary

2 iterations · 18 active passes · profile: standard · Final C/H/M/L: 0/7/6/0 · Verify: PENDING · Status: BLIND-AUDIT-DISSENT

## 10. Snapshot and rollback

Pre-write snapshots, hashes, original absence records and red/green logs are stored in /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-cdo. The rollback helper checks final hashes before restoring only this task’s files to the integrated remote base; it refuses changed files. It does not rewrite Git history.

```bash
python3 /Users/mitch/.codex/skill-consolidation/backups/solmargintrader-20261108-cdo/rollback.py --target /Users/mitch/dev/solmargintrader --apply
```

## 11. Index

index: n/a (outside skill corpus roots). Repository offline metadata/text/concept indexes refreshed; freshness and documentation gates passed. No semantic embeddings or paused indexer started.

## 12. Memory-central and remaining limits

memory-central: 2 lessons · 10 conventions consulted. Prior audit status and safety constraints were verified against current source. No global memory-central compilation or embedding service ran. New graph writes are queued in the Stele outbox because its write MCP was unavailable; queue receipts are not server acknowledgements.

- The primary review cap covers50of261 sources at base2ca3041;211 paths remain explicitly deferred.
- Final gate2 extension and TUI reviewers disclose partial examination of several hashed files; hashing is not review. No repository-wide or complete final-gate cleanliness claim is made.
- No full optional SolTUI suite, historical sweep regeneration, owner service restart, live order, real owner signing or authenticated wallet acceptance.
- Final browser acceptance uses a temporary Chrome profile and production host from the task checkout. Existing owner-installed surfaces stay unchanged.
- Mongo integration cases require a database and remain skipped locally; CI provides an ephemeral MongoDB server.
- A preliminary liquidity suite unexpectedly performed one public eth_chainId read. The pre-gate Engine construction is now fixed; the final579 tests passed with socket connections blocked.
- Stele writes are queued locally; no server acknowledgment was available.
- Post-audit integration of already-delivered executor integrity and SignalDesk changes altered some reviewed sources; the scope JSON preserves audit-candidate and integrated hashes. Integration verification is separate from a fresh blind audit.
