# ZEC captured-event backtests

Version: 1.0.1

The full finite matrix finished on 2026-11-13: **10,576 rows**, including 4,878 completed strategy/benchmark rows, 5,670 insufficient-warm-up rows and 28 explicit exclusions. Results describe one captured day; they do not establish a durable edge or 70% next-minute accuracy.

At a 60 bps fee per fill, every active 1m spot policy lost money. The best active 5m and 10m cases made one round trip each. Those are descriptive maxima after many dependent trials, not independently selected winners.

| Signal bars | Valid / complete UTC bars | Longest valid history | Spot completed / active | Positive active spot policies | Best active spot net |
|---|---:|---:|---:|---:|---:|
| 1m | 1431 / 1439 | 617 bars | 827 / 786 | 0 | -1.0315% |
| 5m | 279 / 287 | 122 bars | 404 / 336 | 1 | +0.2022% |
| 10m | 135 / 143 | 61 bars | 189 / 117 | 11 | +1.1127% |
| 1h | 17 / 23 | 10 bars | 3 / 2 | 0 | -1.2393% |

The 60 bps best active policies are: 1m OBV trend gated by volatility regime (calm quantile 0.25, persistence 2); 5m RSI(period 28, oversold 35); 10m the OR/any vote of default swing-confluence and RSI; 1h DCA. Full defaults and overrides are in the frozen plan. The 11 positive 10m aliases have 6 distinct fill path(s); eleven positive policy rows are not eleven independent successes.

Cash returned 0%. A single capture-start buy held to the scheduled deadline exit returned **-9.7879%** after 60 bps fees, observed spread/depth and 2 bps residual slippage. The registry buy-and-hold policy instead exits/restarts around invalid indicator history, so it is labelled separately from this passive benchmark.

## Fee sensitivity

Each cell is the best *active* spot return at that cost, after observed spread/depth and another 2 bps adverse slippage on each fill. The best policy can differ between columns. Fees are scenarios; the owner's actual Coinbase tier was not recorded.

| Signal bars | 10 bps/fill | 25 bps/fill | 60 bps/fill |
|---|---:|---:|---:|
| 1m | +1.5392% | -0.3363% | -1.0315% |
| 5m | +2.3022% | +1.0822% | +0.2022% |
| 10m | +2.1289% | +1.8230% | +1.1127% |
| 1h | -0.6422% | -0.8216% | -1.2393% |

## Volty stop-order scenarios

The best active synthetic Volty return at each fee is below. These scenarios assume short exposure is available; the source venue is spot. They do not include a real perpetual venue's funding or liquidation oracle.

| Signal bars | 10 bps/fill | 25 bps/fill | 60 bps/fill |
|---|---:|---:|---:|
| 1m | -38.2733% | -58.1498% | -82.5366% |
| 5m | -10.5894% | -17.8288% | -29.4762% |
| 10m | -9.2816% | -12.2645% | -18.9044% |
| 1h | +0.5453% | +0.2466% | -0.4502% |

## Scope and interpretation

- The registry contains 34 factories. All 31 spot-capable defaults are included, together with the existing finite parameter/ensemble catalog: 827 spot templates total. Three perp wrappers remain explicit exclusions because a Coinbase spot tape cannot supply their actual venue funding, liquidation oracle or execution.
- The separate Volty grid covers 50 predefined (length 1–10 × multiplier 0.25/0.5/0.75/1/1.25) configurations per interval and fee. It uses observed received-trade stop crossings and delayed book fills. It is a hypothetical 1x long/short margin book on spot prices, with 0.1 bps/hour carry, not a Coinbase shorting or Jupiter-perp performance claim. Every active Volty case at 60 bps lost money.
- Resting ladder grid, paired/BTC-dependent compound, pairs and source-only strategy cards are not represented as completed tests. The registered exposure-staircase grid is included; it does not reproduce a resting ladder.
- The matrix includes 827 spot + 50 Volty configurations × 4 bar intervals × 3 fees = 10,524 strategy rows, 24 cash/passive-hold benchmark rows, and 7 unsupported-family entries × 4 intervals = 28 exclusion rows. A row with no eligible post-warm-up signal is excluded rather than celebrated as a flat profitable test.
- One-hour replay has only 23 complete UTC bars and at most 10 consecutive valid bars. Most hourly policies cannot warm up. Smaller bar size increases sample count, not the number of independent market days.

## Data and causal execution

Input: Coinbase Exchange ZEC-USD public WebSocket capture 50dbd4f31de24c36a30d8c3786495ad5, from 2026-11-12T04:56:27.224912Z to 2026-11-13T04:56:27.224912Z. There are 1,459,542 original records, including 134,746 match events, 1,238,392 L2 updates and 7 snapshots. Seven connections and six reconnects mean this was not uninterrupted exchange-internal coverage. Provider book updates are batched; the tape is not every internal exchange event.

Original SHA256: `eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31`. The full original WAL was rehashed and sequence/window checked. It was already independently verified against the native MongoDB time-series collection; this replay reads that same immutable local spool without changing it.

Only received `match` events form OHLCV; `last_match` subscription references are not duplicate volume. Bars align to UTC and use receipt time, so late exchange messages do not get retroactively inserted into an already-closed signal. Partial boundary bars and bars without trades are excluded. Known gaps reset indicators in the bar containing their detection time; they do not erase earlier emitted decisions.

Fresh strategy state advances through each contiguous valid history. Volatility targets receive the actual cadence scaling, including 600 seconds for 10m. Signals use prefix-only history and become eligible at closed-bar time plus 1 second. The simulation uses the first received book update sampled in each UTC second, then chooses the first sample at/after order eligibility (maximum 2 seconds wait). Stop triggers therefore incur 1–approximately 2 seconds of receipt-time latency. Independent timestamp sampling measured median exchange-message lag of 30.7 ms and a maximum of 13.266 seconds at silence recovery. Thus these are receive-time reference prices; the study does not establish executable live-exchange prices during delayed backlog. Real-world order latency remains unmeasured.

Books reconstruct ordered L2 deltas from each connection's snapshot. Actual connection loss/change invalidates the book until another snapshot. Same-connection silence waits for a new update without discarding already-received state. Attempt 03 has 86,352 book samples, fresh books at every scheduled signal-bar decision time, and a terminal book 0.220432 seconds before the fixed deadline. All simulated positions finish closed within 1e-8 ZEC.

Each independent account starts with $10,000. Market fills consume up to 40 displayed price levels; insufficient displayed capacity refuses the order. Fees and the cash cap use the final affordable quantity. Depth is visible liquidity, not a market-impact guarantee. Different strategies do not compete with each other for the same historical liquidity.

A missing/invalid signal can request an unwind only when that invalidity is known; it bypasses rebalance deadbands. Existing exposure can remain until the next fresh book. Volty stops use previous closed-bar levels, cancel after observed gaps and follow received trade order, rather than assuming a candle high/low path. Rejected orders do not change logical position state.

Weighted policies train only on a fixed first 256 bars of each valid segment, or warmup+64 if greater, and score the later suffix. The segment's future length does not choose training duration. Other configurations are predefined; this study does not reserve a separate market-day holdout. Drawdown is sampled at decisions/fills, so it can miss intrabar extremes; no annualized Sharpe or confidence claim is made.

## Verification and artifacts

Attempt 01 failed coverage JSON serialization (exit 1). A small end-to-end matrix regression now covers that boundary. Attempt 02 completed (exit 0) but over-invalidated same-connection silence and left stale terminal marks; it is preserved as unqualified. Only attempt 03 is reported here. Attempt 03 completed (exit 0), checksummed all result artifacts, recorded interpreter/dependency/source-file identities, and refused publication if imported source changed during execution.

The local targeted gate passed 39 tests (exit 0), including 22 new replay regressions and existing ensemble/Volty contracts. Independent acceptance passed: all 1,459,542 WAL records and 134,746 trades; 100 books rebuilt with a separate sorted-dictionary implementation; all 326,173 fills with independent cash/fee/depth/timing checks; and 21 complete SMA/hold cases reproduced with direct arithmetic and a separate ledger. Maximum cash discrepancy was 9.37e-11 USD. The final receipt is retained with this family.

Shared machine-readable results and their original run hashes live in `research/zec-granular-20261113.llms/`: `results.csv`, `summary.json`, `coverage.json`, `identity.json`, `plan.json.gz`, `manifest.json`, and the independent audit receipt. The inherited candidate IDs identify parameter templates originally catalogued at 1m. The execution key is `(interval,candidate_id,fee_bps)`; the row interval selects the actual 1m/5m/10m/1h bars. These template IDs must not be loaded as interval-qualified Oracle policies.

Private full replay evidence is at `/Users/mitch/.local/state/solmargintrader/zec-granular-backtests-20261113/attempt-03/`, including 326,173 fill records and the prepared depth tape. The original run manifest binds those bytes. Full public results and frozen parameters also persist as immutable empirical artifacts in Mongo research run `run:55f2cb71690fb0115c42324012967ff835eb3137e4a7f3cd6a80522a335123d0`; client CRUD persistence does not certify literature support.

Reproduce from the original WAL with `/Users/mitch/.venvs/soltui/bin/python -m research.zec_granular --wal /Users/mitch/.local/state/solmargintrader/market-captures/zec-usd-20261112T045627Z/events.jsonl --output NEW_OUTPUT_DIRECTORY` from `/Users/mitch/dev/solmargintrader`. Finished output directories are immutable. No network, inference, embedding, new capture or live order is needed.
