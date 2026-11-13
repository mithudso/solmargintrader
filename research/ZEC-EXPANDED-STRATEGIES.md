# Expanded ZEC strategies, chart shapes and price cycles

Version: 1.0.0

The complete executable expansion produced **85,312 rows** on the previously captured Coinbase ZEC-USD day, using **1m, 5m, 10m and 1h signal bars** and **0.25% or 0.15% per fill**, charged on entry and exit. Of these rows, 38,664 completed and 46,648 explicitly lack sufficient history. A bar interval determines the signal clock; it does not impose an equal trade holding period.

The broader search finds some profitable configurations on this day. **It does not establish a reliable forecasting rate or a persistent trading edge.** The day was already examined in earlier studies, and these maxima are selected from many related configurations. No configuration was selected prospectively for this capture.

## Expanded spot baseline

Best active spot return after modelled fees, spread, depth and latency:

| Signal bars | 0.25% per fill | Fills | 0.15% per fill | Fills | Positive / active at 0.25% | Positive / active at 0.15% |
|---|---:|---:|---:|---:|---:|---:|
| 1m | +0.9059% | 2 | +1.8654% | 16 | 8 / 1,623 | 22 / 1,623 |
| 5m | +1.0822% | 8 | +2.1075% | 18 | 81 / 789 | 101 / 789 |
| 10m | +2.2724% | 2 | +2.4771% | 2 | 85 / 385 | 89 / 385 |
| 1h | +0.3411% | 2 | +0.5420% | 2 | 1 / 35 | 1 / 35 |

The 1m leader at 0.25% is RSI(45), oversold 35, exit 55. At 0.15% it is RSI(22) with the same thresholds. The 5m leader at 0.25% is the earlier ADX switch between swing confluence and Bollinger reversion; at 0.15% it is Bollinger reversion with window 20 and one standard deviation. The 10m leader is Bollinger reversion with window 45 and two standard deviations. The hourly leader is RSI(7), oversold 30, exit 41.25. Two fills usually represent only one round trip.

These results expand the previous finite universe; they do not contradict the earlier, smaller-universe result. All **7,032 inherited baseline comparisons** reproduce the accepted 25/15 bps results exactly. Passive capture-start buy-and-hold remains -9.1542% and -8.9723%, respectively. Cash returns 0%.

## Chart-shape conditioning

Shapes use only the last **48 contiguous, completed bars**. The pinned detector labels range, trend up/down, V rebound/inverted V, bowl/cap and compression; unavailable history is explicit. Fixed family-specific rules gate the underlying strategy. No shape rule was tuned after inspecting this run's output. These are price-path context proxies: the windows span 48 minutes, 4 hours, 8 hours and 48 hours. They are not evidence about economic macro causes.

| Signal bars | Best active shape return, 0.25% | Best active shape return, 0.15% | Known shape bars / complete bars |
|---|---:|---:|---:|
| 1m | +0.0660% | +0.4669% | 1,029 / 1,439 |
| 5m | +1.7933% | +2.8159% | 75 / 287 |
| 10m | +2.2724% | +2.4771% | 14 / 143 |
| 1h | Insufficient history | Insufficient history | 0 / 23 |

The best 5m shape case is Bollinger(20, 1 standard deviation), with 10 fills. Its **same-configuration, matched-history control** returns +1.7071% and +2.5237% with 8 fills. The added return is therefore **+0.0862 and +0.2921 percentage points**, rather than the whole shape-case return. The 10m leader has exactly the same result with and without the shape filter on the matched history.

Across paired spot configurations with activity on either side, median shape-minus-matched-control returns are +1.1167/+0.9590 percentage points at 1m, and zero at both 5m and 10m (0.25%/0.15%). Many configurations still lose money. The corresponding medians after deduplicating pairs of replay IDs are +1.3078/+1.0939 at 1m, +0.0144/0 at 5m and 0/0 at 10m. Configurations and replay pairs share one market day and are not independent observations. Full counts and equality ties are in `paired-comparisons.json`.

## Frequency and recurring-cycle conditioning

Here, frequency means **recurring price cycles**, following the earlier spectral study. At fixed decision times, the model fits the last 64 valid observations using their actual timestamps, requires at least 95% clock coverage, and freezes the chosen harmonic for the next 16 decision slots. Missing prices are not interpolated. The gate uses the harmonic's predicted increment; the linear-only control is fitted separately. Shape and indicator histories still reset at detected gaps.

| Signal bars | Best active frequency return, 0.25% | Best active frequency return, 0.15% | Frozen fits | Known forecast bars |
|---|---:|---:|---:|---:|
| 1m | -0.1403% | -0.0101% | 86 | 1,368 |
| 5m | +0.1379% | +0.3384% | 13 | 200 |
| 10m | +0.0303% | +0.2305% | 1 | 15 |
| 1h | Insufficient history | Insufficient history | 0 | 0 |

There are **zero profitable active 1m frequency-gated spot configurations** at either fee rate. Paired median frequency-minus-availability-control returns are -1.3257/-0.7755 percentage points at 1m, -0.8538/-0.8588 at 5m and -0.1260/-0.1262 at 10m. Deduplicating replay pairs also leaves each of these medians negative. Linear-only and availability-only controls are retained for every comparable row; the full data show inactive and equal cases rather than discarding them.

Every fit tests log prices and log returns against both random-sign and block-permutation nulls. Each null replicate repeats the complete frequency search. **All 200 tests use 4,999 replicates per null model.** The conservative raw p-value takes the worse of the two null results. Holm correction is applied across all 200 tests for reporting only, never as a retrospective trading gate. The minimum raw conservative p-value is 0.0042; the minimum adjusted p-value is **0.84**. **No cycle survives the correction.** One day provides limited power and regime coverage; this result neither establishes cycles nor rules out every possible cycle model.

## Finite universe and explicit exclusions

The historical frozen census covers all **1,478 strategy-card/document paths**, the active registry, and all **1,059** ZEC tier-0/1/2 background-queue jobs. There are 983 executable queue jobs, 46 invalid declared parameter combinations and 30 actual-perp jobs without required venue inputs. All reasons are retained. Of the card/document paths, 34 are active registry cards, 764 are spec-only cards, 678 are publication/profile documents without executable registry entries, and two are navigation documents. A publication profile is not broken executable code.

During publication, upstream queue validation changed the current scheduled census to 1,011 jobs: the same 983 executable jobs and 28 unsupported perp jobs. It separately records 50 distinct prospective exclusion IDs. Of these, 48 correspond to jobs removed from the historical census: the original 46 factory-invalid jobs and two unsupported leverage jobs. The other two are medium-horizon aliases of rejected long-horizon cases; validation now records exclusions before cross-horizon deduplication. Independent comparison and regression tests confirm that **all 1,707 executable candidate rows, parameters, families and provenance remain exactly equal**. The current CLI retains all 50 exclusions separately. This changes diagnostics, not the accepted numerical matrix.

Normalizing actual factory defaults and deduplicating the earlier 827 templates together with the executable queue yields **1,707 spot templates**, including **880 additional unique templates**. The study also evaluates 50 Volty configurations and 20 separately labelled lifecycle reference configurations. Six modes—baseline, shape, matched shape history, frequency, matched frequency availability and linear-only—run at four cadences and two fees. This gives 85,296 strategy rows plus 16 cash/passive-hold benchmark rows. Unsupported items remain in the complete plan census; they are not silently counted as tested strategies.

The 20 lifecycle configurations cover eight grids (five/nine rungs, geometric/arithmetic spacing, a causal 48-bar training range or a fixed ±5% band) and 12 safety-order DCA configurations (nominal $100/$1,000 base and safety sizing, three/five safety orders and 1/2/4% take profit). Their **observed-cross, delayed limit-guard reference model** requires a strict received-trade crossing for resting grid, safety and take-profit orders. DCA base orders and risk-off/terminal exits are market-style. Both paths require a single pending intent and a fresh executable book after latency. The model accounts for cash, capacity, paired-rung exits, safety buys and updated deal basis. A safety buy cancels a stale take-profit order until the next closed-bar replan. This is a disclosed reference variant, not exact parity with the original OHLC runner or a passive maker queue.

Best active baseline grid returns at 0.25%/0.15% are +0.1843/+0.3059% at 1m, -0.1971/-0.1568% at 5m and +0.1169/+0.2263% at 10m. Hourly grids lack training history. Every active baseline safety-order DCA case loses at both fees. All six-mode special-runner results and configurations are retained in the archive.

Volty remains a separate synthetic 1x long/short scenario on spot prices with 0.1 bps/hour carry. Its baseline reproduces the previous study: every active 1m/5m/10m case loses at both fees; the best hourly case makes +0.2466/+0.4457% with one round trip. It does not prove actual short, perp funding, margin or liquidation execution. Pairs, triangle, missing-context compound strategies and non-executable cards remain explicit unsupported work; the one-coin tape cannot supply their missing inputs.

## Execution, provenance and verification

The immutable capture spans 2026-11-12T04:56:27.224912Z to 2026-11-13T04:56:27.224912Z. WAL SHA256: `eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31`. The exact accepted tape, capture metadata and parent manifest match the earlier granular study. All 1,535 pinned simulation/card source hashes and runtime identity remain unchanged across this run.

The $10,000 reference account uses receipt-time bars, prefix-only signals, observed book depth, 2 bps adverse residual slippage, at least one second latency, at most two seconds book wait, 40-level capacity and fixed-deadline liquidation. The requested fee rates are conditional scenarios: this crossing-book simulator does **not** establish maker classification or queue priority. Earlier capture audit measured exchange-message lag up to 13.266 seconds; receipt-time quotes are reference prices. Sampled decision/fill drawdown can miss intrabar extremes.

Independent audits verified every expected row key/status, all 20 run-artifact hashes, 7,032 baseline aliases, **1,563,853 emitted fills**, all 2,334 limit-guarded fills, every saved shape/context, all 100 frozen fits, and exact reproduction of all 200 null rows. Separate arithmetic reproduced 68 complete strategy/control cases. All positions closed; maximum cash discrepancy was 9.76e-11 USD. All 16,260 lifecycle fills obeyed single-flight accounting and execution rules. The author's 60-test focused preflight and Ruff passed with exit 0; the auditor's separate 54-test scope passed with exit 0.

**Telemetry limit:** the original full matrix process's OS exit receipt was unavailable after its tool session closed. It remains unknown. The finished manifest and independently reconstructed outputs establish artifact correctness within the stated model; they are not substituted for an invented process exit code. The independent audit receipt is partial only for this missing telemetry and reports no remaining material artifact finding.

## Shared evidence and reproduction

The complete results, frozen parameters/census, source and input identities, cycle tests, comparison summaries and five independent audit receipts live in `research/zec-expanded-20261113.llms/`. Start at its `llms.txt`; `archive-manifest.json` binds the published bytes. `simulation-source.zip` preserves all **1,535 exact experiment source/card files**, individually matched to `identity.json`. The current delivery source additionally records planning exclusions and removes whitespace; the archived source pins the historical experiment. Rows join to saved fills through `replay_id`; identical cached fill paths are not separate discoveries. The complete 82 MB compressed fill ledger remains private at `/Users/mitch/.local/state/solmargintrader/zec-expanded-20261113/attempt-01/fills.jsonl.gz`, bound by the run manifest. The original event dataset is already stored in the native MongoDB time-series collection documented by the earlier capture audit.

Mongo empirical run `run:a45e0c626343173bade6f4696c6c885427a1ff274c8b2c4c857978b43857405f` stores the full CSV in hash-bound artifact/versioned-ledger transport fragments, the complete frozen census, summary and report. A deduplicated native proof stores all fits, null tests, audit receipts, input bindings and non-card source hashes. Joining the census card hashes reconstructs all 1,535 source hashes; its saved plan delta reconstructs the actual run plan exactly. Full CSV, census and proof readback passed. `mongo-artifacts.json` declares the selected reconstruction and receipt; partial transport experiments are unselected drafts. Client-authored empirical artifacts do not qualify literature claims through trusted research gates. No paid research, inference, embeddings, live orders or service changes were needed.

To reproduce, use a new empty output directory; finished run directories are immutable:

```sh
python -m research.zec_expanded --parent /Users/mitch/.local/state/solmargintrader/zec-granular-backtests-20261113/attempt-03 --output /Users/mitch/.local/state/solmargintrader/zec-expanded-20261113/reproduction --replicates 4999
python -m unittest research.tests.test_zec_expanded -v
```

The environment needs the repository's simulation dependencies. The complete matrix is expected to produce 85,312 rows, including explicit insufficient-history rows. The current generator has the same executable configurations but newer queue diagnostics. For exact historical source and metadata replay, create an isolated checkout at base commit `f67ded65d30c6b78026e1ad625dec70748923807`, extract `simulation-source.zip` into that checkout, and run the command there. Do not extract it over a running checkout. Reproduction does not require collecting another day or changing the accepted capture.
