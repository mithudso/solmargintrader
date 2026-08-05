---
name: sol-solana
description: Solana (SOL) for a systematic trader — execution reality on a no-mempool chain, supply and staking, and what this project's own 1,287-configuration backtest actually measured on it. Read before designing or trusting any SOL strategy.
---

# Solana (SOL)

The asset `solmargintrader` trades. Uniquely among these ten spokes, most of what follows is
**measured on this project's own data** rather than read from a source — which makes it the
one file here that can say what worked and what did not.

**Not investment advice.** This is a reference document for research and backtesting. Every
Sharpe ratio and return below is a backtested figure on historical data, and the whole point of
the findings section is that most of them did not survive contact with a different asset,
timeframe, or evaluation geometry.

## Snapshot (AS OF 2026-08-05)

| | |
|---|---|
| Price | **$73.81** |
| Market cap | **$42.92B** (rank 7) |
| 24h volume | **$1.585B** |
| Circulating supply | 581,306,965 |
| Total supply | 631,629,923 |
| All-time high | **$293.31** intraday, 2025-01-19 — **−74.8%** from it |

Source: CoinGecko API, 2026-08-05. **These decay.** The structural claims below — supply
mechanics, execution model, the measured backtest results — age far more slowly.

**Turnover (24h volume ÷ market cap) is 3.69%**, the highest of the ten coins in this hub —
though the lead is narrow rather than categorical: DOGE is ~3.49% and ETH ~3.05%, while BTC is
~1.80% and RAIN ~0.24%. So SOL is roughly **2× BTC** and **15× RAIN**. Whatever else is true of
SOL, thin liquidity is not its problem, and a cost model calibrated on it will be *optimistic*
if reused on the thin names.

Note the close/high distinction, because it matters for reproducing anything: CoinGecko's ATH
of $293.31 is intraday, while the **highest daily close in this project's 1,875-bar series is
$261.99**. A backtest on closes never sees $293.

## What it is, mechanically

A single-shard L1 optimising for throughput and latency rather than for node cheapness.

- **Proof of History** — a verifiable delay function giving a cryptographic clock, so
  validators can agree on ordering without round-tripping consensus messages for every batch.
- **Sealevel** — parallel execution across transactions whose read/write account sets do not
  overlap. Transactions must declare every account they touch up front, which is what makes
  the parallelism decidable.
- **Slots and a public leader schedule.** Leaders are assigned per slot and **the schedule is
  deterministic and public for the whole epoch.** That single fact drives most of the
  execution reality below: anyone can know who will produce the next block and route to them.
- **No public mempool.** Transactions are forwarded to the current and next leaders directly.
  There is no shared pending pool to watch, which changes the entire MEV picture relative to
  Ethereum.

## Supply and issuance

Inflationary with a disinflationary schedule: an initial annual rate stepping down each epoch
by a fixed factor toward a long-run terminal rate. Emissions go to stakers, so the number
that matters to a holder is issuance *net of* the staking yield they are or are not earning —
an unstaked holder is diluted by the full rate.

Circulating 581.3M against a total of 631.6M implies roughly **50.3M SOL (~8%) not yet
circulating**. Treat vesting and unlock detail as something to verify against a current
source before sizing anything on it; this spoke does not have a dated schedule and will not
invent one.

## What drives the price

In rough order of what the 2021-2026 record supports:

1. **Beta to crypto risk appetite.** SOL is a high-beta expression of the same cycle BTC
   trades, not an independent asset. The 2021 run, the 2022 collapse, the 2023-24 recovery and
   the 2025-26 drawdown all line up with the broad cycle, amplified.
2. **Chain-activity narratives** — DeFi, then NFTs, then memecoins, then whatever is next.
   These drive fee revenue and attention, and they rotate.
3. **Reliability events.** Solana's outage history is part of its price history; each one
   was a repricing of the "does this chain stay up" question.
4. **Ecosystem-specific shocks.** The FTX/Alameda association in 2022 was an
   asset-specific drawdown that had nothing to do with the protocol.

## Market structure

- **CEX:** deep and broadly listed. `SOL-USD` on Coinbase is what this project fetches, and
  it yields 1,875 daily bars from 2021-06-17 and 8,823 hourly bars from 2025-08-01.
- **DEX:** fragmented across Raydium (CPMM and CLMM), Orca Whirlpools, Meteora DLMM, and
  order-book venues Phoenix and OpenBook. Liquidity for any given pair depends on which pools
  exist, and headline TVL is close to meaningless for execution — what matters is in-range
  liquidity or the active bin.
- **Aggregation:** Jupiter's router does multi-hop and split routing across many venues per
  quote, which means most simple cross-venue price differences a retail user can see have
  already been consumed.
- **Perps:** Jupiter Perps executes **at the oracle price** against the JLP pool, with no
  spread and no book. This is the single most important fact for modelling fills here, and
  §"Execution reality" explains why.

## Execution reality for a trader

This section decides whether *any* strategy is executable, and it is where SOL differs most
from a CEX-traded asset.

- **Priority fee is a product, not a price.** The bid is
  `ceil(CU_price × CU_limit / 1e6)` lamports, and the auction ranks by fee-per-compute-unit.
  Over-requesting compute units costs money *and* priority simultaneously.
- **Fee markets are per-account, not global.** Congestion is local to the accounts a
  transaction writes. "The" Solana priority fee does not exist — price against the accounts
  *your* transaction touches, or you will underpay on the hot pool and overpay everywhere
  else.
- **Dropped costs nothing; reverted costs the full fee.** Silence is the default failure mode.
  A strategy that submits and never lands has a cost of zero and a fill rate of zero, which is
  a very different economics from one that lands and fails.
- **Stake-weighted ingress.** Leader ingress is allocated in proportion to the stake of the
  forwarding node, so *which RPC endpoint you submit through* changes your landing rate
  independent of what you pay. A public RPC is a structural disadvantage no fee fixes.
- **Atomicity is free within one transaction.** All instructions in a transaction either all
  execute or none do. A Jito bundle buys *ordering relative to other transactions*, not
  atomicity — conflating the two is the standard error.
- **Hard ceilings:** 1,232 bytes and 1.4M compute units per transaction, and a blockhash that
  expires after 150 blocks (**~60–90 s**; ~79 s at nominal slot times). A complex split route
  may simply not serialise;
  treat "the optimal route does not fit" as an expected case rather than an anomaly.
- **Oracle-priced perps invert the usual fill problem.** On a book you worry about spread and
  depth. Against JLP at the oracle price you do not — but the signal series and the fill
  series become *the same series*, which is a lookahead hazard rather than a convenience. A
  naive backtest trades on the print it also fills at, a zero-cost round trip that looks
  spectacular and is fiction.

Reported figure, single-sourced and directional rather than load-bearing: **75.7% of non-vote
transactions were reverted at the April 2024 peak**, largely MEV-bot competition (Helius).
Treat as an order of magnitude, not a constant.

## Volatility, drawdown and regimes

**Annualised volatility of daily log returns is 98.6% over the full sample**, and the trend is
down but **not monotone**: 2021 (from 06-17) **124.8%**, 2022 **123.6%**, 2023 **96.1%**, 2024
**82.1%**, then back **up** to **86.3%** in 2025, before **64.1%** for 2026 to date. The step-down
has already stalled and reversed once, so "vol keeps falling" is not a safe sizing assumption —
and a strategy sized on the 2026 number but backtested across 2022 is sized for the wrong asset.
Computed from `data/SOL_1d.csv`: sample standard deviation of daily log returns within each
calendar year, excluding each year's boundary-crossing first return, × √365.

**Maximum drawdown on closes is −96.3%** — peak $258.76 to trough **$9.64 on 2022-12-29**. The
current drawdown from the all-time-high close is −71.8%. That 24.5-point gap is not a small
difference, because drawdown recovery is multiplicative: getting back from −71.8% takes
**+254%**, getting back from −96.3% takes **+2,584%**. A risk model calibrated on the −71%
figure is an order of magnitude short of what this asset has already done.

The shape of the record matters more than any single volatility number:

| Leg | Window | Move |
|---|---|---|
| Daily, in-sample (bars 0–1311) | 2021-06-17 → 2025-01-18 | **$39.25 → $261.99 (+567%)** |
| Daily, out-of-sample (bars 1312–1874) | 2025-01-19 → 2026-08-04 | **$252.34 → $73.89 (−70.7%)** |
| Daily, peak to final bar | 2025-01-18 → 2026-08-04 | **$261.99 → $73.89 (−71.8%)** |
| Daily, peak to worst trough | 2021-11-06 → 2022-12-29 | **$258.76 → $9.64 (−96.3%)** |
| Hourly, first 70% (bars 0–6175) | 2025-08-01 → 2026-04-15 12:00 | $170.25 → $83.74 (−50.8%) |
| Hourly, last 30% (bars 6176–8822) | 2026-04-15 13:00 → 2026-08-04 | $83.66 → $73.00 (−12.7%) |

The hourly split is quoted to the bar because the two legs meet at adjacent bars, not at one
shared value: bar 6175 closes at $83.74 and bar 6176 at $83.66. And the hourly series' final
close ($73.00) differs from the daily's ($73.89) on the same calendar date because the hourly
record ends at the **00:00 bar** of 2026-08-04 while the daily bar covers the whole day.

## What this project has already measured on SOL

Findings 1–8 come from `research/RANKED_LISTS.md`, which is machine-verified against its own
result CSVs by `research/verify_numbers.py`. **Finding 9 is outside that guarantee** — it cites
its own artifacts inline, and `verify_numbers.py` does not read them.

**Two different methods produced the findings below, and mixing them up matters.** The primary
method is combinatorial purged cross-validation — 8 blocks, k=2, **up to** 28 paths — over 25
registered strategies at 3 horizons, giving **75 singles** (25 × 3), 1,002 pairs and 210
triples, 1,287 configurations. Findings 3, 4, 5, 7 and 8 come from that. Findings **2 and 6
come from the superseded single 70/30 split** that CPCV replaced, and are retained because they
are the evidence *for* replacing it — not because that split is trusted. Each is labelled below.

**1. A single 70/30 split could not answer the question, and the reason is specific.** The
highest close in the series ($261.99, bar 1311 of 1875) falls on the *final bar of the in-sample
window* — verifiable in one line from `data/SOL_1d.csv` — and the series never sees that level
again. The split therefore put essentially the whole bull market in-sample and the whole bear leg
out, so any long-biased rule was **structurally required** to look excellent in-sample and
terrible out. That column measured one regime, not the future.

**2. In-sample rank does not predict out-of-sample rank, and at the medium horizon it
inverts.** *(single 70/30 split, n=164/109/38 configurations by horizon — not CPCV.)*
Spearman ρ(IS, OOS Sharpe): **−0.139** short, **−0.419** medium, +0.027 long. Mean
Sharpe fell from **+0.806 in-sample to −0.538 out-of-sample** at the medium horizon. Picking
the best-looking strategy was actively worse than choosing at random.

**3. PBO says selection is anti-informative at the daily horizons.** Probability of Backtest
Overfitting: **0.343** short, **0.700** medium, **0.700** long — against a measured pure-noise
line of **0.500** and 0.000 for a genuinely ordered signal set. Both daily horizons sit
*above* noise.

**4. Not one of the 25 singles has a positive median path Sharpe at the short horizon.** The
best, `stoch_14_3`, still loses at −0.341. PBO there is a comparatively encouraging 0.343 —
which means rank is *stable*, and what it stably predicts is losing.

**5. Buy-and-hold is hard to beat on this asset.** Median path Sharpe **+0.534**, 68% of paths
positive, +9.4% median return — **2nd of 25 at the medium horizon and 6th at long**, with zero
parameters. So exactly one single beat it at medium and five did at long: holding the asset was
not literally unbeatable, but it out-ranked 23 of 25 mechanisms at one horizon and 19 of 25 at
the other, for no parameters and no turnover. Read each rank against its field, though — **13 of
25 singles posted a positive median at medium but 22 of 25 did at long** — so 6th place in a
field where almost everything cleared zero is the weaker of the two results.

**6. "Beat the baseline" is nearly meaningless when the baseline lost 71%.** *(single 70/30
split — not CPCV.)* At the medium horizon 105 of 109 configurations beat buy-and-hold — by
losing less. **Five made money.** At the long horizon, one of 38.

**7. Combining signals raises fragility as well as performance.** Compared like with like —
the top pairs are long-horizon, so the comparison must be against long-horizon singles — the
median parameter-perturbation ratio goes from **0.171** for singles to **0.44** for the top
pairs, **2.6×** the parameter sensitivity. (Against the *pooled* singles median of 0.208 across
all three horizons the multiple is 2.1×; quoting 0.21 alongside "2.6×" mixes the two and is
the arithmetic slip to avoid.) PBO and perturbation are independent methods pointing the same
way.

**8. The largest single sensitivity was the evaluation geometry, not any strategy parameter.**
Changing CPCV from 8 blocks to 9 moved the best pair's median Sharpe by **−0.441**, more than
the worst parameter nudge (−0.392). The result depends more on how the data is sliced than on
the strategy's own settings.

**9. The five recommended configurations do not transfer off SOL.** *(Measured 2026-08-05;
`research/CROSS-ASSET-TRANSFER.md`, `research/results/cpcv_top5_sol_doge_zec_1d.csv`.)* Run
unchanged —
SOL-tuned parameters, deliberately not refitted — on DOGE and ZEC, **all ten transfers
degraded and not one improved**; median degradation −0.821 on DOGE and −0.753 on ZEC. The rank
inverted again: on the **same 15 paths**, the SOL-#2 configuration
`any(hurst_switch+ou_reversion)` is **100% positive on SOL and 0% positive on DOGE** — not one
path in fifteen — while the lower-ranked #3 and #4 are the only two positive on all three
assets. (Note the path count: these five configurations resolve to **15 or 21 paths, never the
headline 28**, because slow parameters leave only 6 or 7 of the 8 blocks usable — the top-5
evidence is thinner than the geometry advertises.) Across all 25 singles on five assets, **eight
are positive everywhere and not one of the eight is from a reversion family** — equivalently, no
reversion-family strategy clears all five (families per the repo's own `FAMILY` dict). And on
ZEC, zero-parameter buy-and-hold (+0.659) beat all five recommended configurations, the best of
which reached +0.492.

That is the strongest available answer to "does a SOL result mean anything elsewhere", and the
answer is mostly no — with the qualification that a poor DOGE or ZEC number is evidence about
**SOL's parameters**, not about those coins, precisely because nothing was refitted.

## Known failure modes for traders

- **Fitting the cycle.** Five years of SOL is one bull and one bear. A strategy tuned across
  it is tuned to a single regime transition, and CPCV's 28 paths resample that same history —
  they widen the estimate, they do not add a second cycle.
- **Trusting a rank.** With PBO at 0.700, being top of the table is not evidence. Rank by how
  many independent checks a configuration clears — median, path fraction, IQR, perturbation,
  trade count — not by Sharpe.
- **The evidence floor.** Slow parameters on this series generate single-digit trade counts.
  A Q1 path Sharpe of exactly 0.000 usually means most paths took no trade at all.
- **Assuming a CEX fill model.** A backtest priced on Coinbase closes describes a Coinbase
  execution. Routing the same strategy through Jupiter changes the fill mechanism entirely.

## For this backtester

**SOL is the primary asset and the only one with both daily and hourly history**: `SOL_1d.csv`
(1,875 bars, 2021-06-17 →) and `SOL_1h.csv` (8,823 bars, 2025-08-01 →).

What the measured PBO implies for any *new* SOL result: **a good number is not evidence until
it has cleared something other than the ranking that produced it.** The project's own
convention is the right one — perturb the parameters ±10% and re-run, check the fraction of
paths positive rather than the median alone, compare against buy-and-hold on the same bars,
and test whether the result survives a change of asset or timeframe — the check that finding 9
above now actually performs, via `research/cross_asset_cpcv.py`. At the **medium** horizon the
same 25 strategies range from **25-of-25 positive on BTC daily down to 13-of-25 on SOL daily** (24/25
ZEC, 18/25 ETH, 16/25 DOGE). On SOL's *hourly* bars **not one of the 25 is positive** — but note
that hourly **is** the short horizon in this project's configuration, so that figure is finding 4
restated as a timeframe contrast, not a sixth independent asset. A top-ranked configuration fell
from 1st to 23rd on that same timeframe change. On this dataset the *data* has repeatedly
explained more than the strategy.

## Sources

- CoinGecko API `/coins/solana`, 2026-08-05 — price, cap, volume, supply, ATH.
- `~/dev/solmargintrader/research/RANKED_LISTS.md` (AS OF 2026-08-04) — every measured figure
  in "What this project has already measured", machine-verified by `research/verify_numbers.py`
  against `research/results/cpcv_*.csv` and `perturb_*.csv`.
- `~/dev/solmargintrader/data/SOL_1d.csv`, `SOL_1h.csv` — bar counts, date ranges, closes.
- `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` — leader
  schedule, stake-weighted ingress, priority-fee arithmetic, dropped-vs-reverted, local fee
  markets, blockhash expiry, and the 1.4M-CU per-transaction ceiling.
- `~/.claude/skills/trading-and-investing/references/jupiter-swap-routing-and-orders.md` — the
  1,232-byte transaction-size ceiling and route serialisation.
- `~/dev/solmargintrader/research/CROSS-ASSET-TRANSFER.md` and
  `research/results/cpcv_all25_btc_eth_1d.csv`, `cpcv_all25_sol_doge_zec_1d.csv` and
  `cpcv_all25_1h.csv` — the five-asset positive counts, the SOL-hourly 0-of-25, and the
  1st-to-23rd timeframe figure. That results directory is regenerated in place, so prefer
  matching on the `cpcv_all25_*` prefix over any one filename.
- Each other coin's own spoke in this directory — the comparative turnover figures (DOGE
  ~3.49%, ETH ~3.05%, BTC ~1.80%, RAIN ~0.24%) come from those files' own dated snapshots, not
  from a single call, so they are comparable only to within a day.
- `~/.claude/skills/trading-and-investing/references/solana-dex-and-amm-landscape.md`,
  `jupiter-perps-trading.md`, `jupiter-jlp-pool.md` — venue taxonomy, oracle-priced perps, JLP.
- Helius MEV research — the 75.7% revert figure, flagged single-source above.

Unverified and deliberately not asserted: a dated SOL unlock/vesting schedule; current
inflation rate and terminal rate as of 2026; outage dates and counts; staking participation
share. Each would need a current primary source, and none is load-bearing for the backtest
findings above.
