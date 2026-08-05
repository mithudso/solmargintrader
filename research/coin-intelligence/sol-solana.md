---
name: sol-solana
description: Solana (SOL) for a systematic trader — execution reality on a no-mempool chain, a 98.6%-volatility and −96.3%-drawdown record with a +1.31 beta to BTC, and what this project's own 1,287-configuration backtest measured, including that its five recommended configurations do not transfer off SOL. Read before designing or trusting any SOL strategy.
---

# Solana (SOL)

The asset `solmargintrader` trades. Uniquely among these ten spokes, most of what follows is
**measured on this project's own data** rather than read from a source — which makes it the
one file here that can say what worked and what did not.

**Not investment advice.** This is a reference document for research and backtesting. Every
Sharpe ratio and return below is a backtested figure on historical data, and the whole point of
the findings section is that most of them did not survive contact with a different asset,
timeframe, or evaluation geometry: probability of backtest overfitting reaches **0.700** at both
daily horizons against a 0.500 noise line, zero-parameter buy-and-hold ranked **2nd of 25**, and
**not one of the 25 strategies is positive on hourly bars**.

## Snapshot (AS OF 2026-08-05)

| Metric | Value |
|---|---|
| Price | **$73.81** |
| Market cap | **$42.92B** (rank 7) |
| 24h volume | **$1.585B** |
| Circulating supply | 581,306,965 |
| Total supply | 631,629,923 |
| All-time high | **$293.31** intraday, 2025-01-19 — **−74.8%** from it |

Source: CoinGecko API `/coins/solana`, 2026-08-05. **These decay.** The structural claims below —
supply mechanics, protocol constants, the measured backtest results — age far more slowly. Venue
and governance parameters do not: Jupiter's perp base fee was cut to 6 bps across all markets on
10 July 2024, having sat higher before, and the Jupiter fee figures below carry a
`verified-as-of 2026-08-03` stamp in their source. Read them live from the on-chain accounts before
trading on them. The $73.81 here is an intra-day quote at
pull time; the $73.89 the drawdown figures use later is the final *daily close* in `SOL_1d.csv` on
the same date. Same day, different objects.

Note the close/high distinction, because it matters for reproducing anything. CoinGecko's ATH of
$293.31 is intraday; this project's own series prints a slightly higher intraday high, **$295.00 on
2025-01-19** — the same day, from a different venue's tape, and the only bar in the file above
$293. Neither is the number a close-based backtest ever sees: the **highest daily close in the
1,875-bar series is $261.99**, on 2025-01-18.

## What it is, mechanically

A single-shard L1 optimising for throughput and latency rather than for node cheapness.

- **Proof of History** — a verifiable delay function giving a cryptographic clock, so
  validators can agree on ordering without round-tripping consensus messages for every batch.
  *(This one is this file's own summary; no reference in the hub backs it — see the unverified
  list at the end.)*
- **Sealevel** — parallel execution wherever a transaction's *write* set does not overlap
  another's read/write set. Read locks are shared, write locks exclusive, so many readers of one
  account run together while any writer serialises. Transactions must declare every account they
  touch up front, which is what makes the parallelism decidable — and it means a hot pool
  everyone writes to is a serialisation point no matter how much parallelism exists elsewhere.
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

## Turnover

**Turnover (24h volume ÷ market cap) is 3.32%, second of the ten coins in this
directory**[^turnover-std] — behind DOGE at 3.44%, ahead of ETH at 3.05%, and roughly **2× BTC**
(1.78%) and **14× RAIN** (0.24%). On CEX order books, thin liquidity is not SOL's problem, and a
cost model calibrated there will be *optimistic* if reused on the thin names. It says nothing about
capacity on the venue this file actually prescribes: Jupiter Perps has no book at all, and size
there is bounded by per-custody open interest and the impact fee's imbalance term. See "Market
structure".

**Dividing the snapshot table's own volume and market-cap rows will not reproduce that figure —
the `/coins/solana` pull yields 3.7%, not 3.3%.** The comparable figure divides **$1.432B of
volume by a $43.11B market cap**, both from the cross-coin `/coins/markets` pull, whose SOL volume
runs ~10% lower than the per-asset one. An earlier revision of this file divided the per-asset
rows and published 3.69% as the highest of the ten; it is not. Both terms move continuously, so
two figures pulled at different times cannot be ranked against each other, which is why every
comparative figure here comes from one call — `[^turnover-std]` is the single account of that
error and the single copy of the canonical table.

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

*Bar counts are measured on this project's data. The venue taxonomy and the fee mechanics are read
from the sibling references in "Sources"; the borrow-rate reference point is the repo's own
`CostConfig`.*

- **CEX:** deep and broadly listed. `SOL-USD` on Coinbase is what this project fetches, and
  it yields 1,875 daily bars from 2021-06-17 and 8,823 hourly bars from 2025-08-01.
- **DEX:** fragmented across Raydium (CPMM and CLMM), Orca Whirlpools, Meteora DLMM, and
  order-book venues Phoenix and OpenBook. Liquidity for any given pair depends on which pools
  exist, and headline TVL is close to meaningless for execution — what matters is in-range
  liquidity or the active bin.
- **Aggregation:** Jupiter's router does multi-hop and split routing across many venues per
  quote, which means most simple cross-venue price differences a retail user can see have
  already been consumed.
- **Perps:** Jupiter Perps executes **at the oracle price** against the JLP pool, with no book
  and no bid/ask spread — but *not* for free. This is the canonical statement of the cost stack;
  three charges stack and they are separate things.
  - A flat **base fee of 0.06% each way** — `increasePositionBps` / `decreasePositionBps` — so
    **0.12% on a round trip**.
  - A **price impact fee** standing in for book slippage: a linear size term plus an
    open-interest imbalance term, the two of them bounded together by SOL's `maxPriceImpactFee`
    of **50 bps**. The cap applies **per position change**, not per round trip, and the base fee
    sits *outside* it.
  - A **borrow fee** to JLP that **every** open position pays, structurally non-negative — long
    or short, the trader always pays. Longs borrow the volatile custody and pay more; the repo's
    own SOL reference point is **up to 1.6 bps/hr (~140% APR)** at full utilisation.

  Opening and closing are each a position change, so both the base fee and the impact cap are
  charged twice: a bounded worst case on a round trip is **12 bps + up to 100 bps + carry**, and
  carry is the only term that scales with holding period. Rates, on-chain fields, and the
  utilisation double-count trap are in
  `~/.claude/skills/trading-and-investing/references/jupiter-perps-trading.md`.
  "Execution reality for a trader" covers why this decides whether a strategy is executable.

## Execution reality for a trader

This section decides whether *any* strategy is executable, and it is where SOL differs most
from a CEX-traded asset. *None of it is measured here — every claim is read from
`solana-transaction-execution-and-mev.md`, the Jupiter references, or the one blog cited at the
end of the section.*

- **Priority fee is a product, not a price.** The bid is
  `ceil(CU_price × CU_limit / 1e6)` lamports — CU price is quoted in **micro-lamports per CU**,
  which is where the 1e6 comes from — and the auction ranks by fee-per-compute-unit.
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
  independent of what you pay. A public RPC is a structural disadvantage no fee fixes — closing it
  means a staked endpoint or a validator relationship, and `solana-transaction-execution-and-mev.md`
  is where the endpoint-selection detail lives.
- **Atomicity is free within one transaction, and a Jito bundle extends it.** All instructions
  in a transaction either all execute or none do. A bundle extends all-or-nothing across **up to
  5 transactions executed sequentially within one slot**, and buys ordering along with it — which
  is why a route too large to serialise into one transaction is not automatically un-atomic. What
  a bundle does *not* buy is protection from the leader: it cannot stop a block producer wrapping
  your bundle in its own transactions.
- **Hard ceilings:** 1,232 bytes and 1.4M compute units per transaction, and a blockhash that
  expires after 150 blocks (**~60–90 s**; ~79 s at nominal slot times). A complex split route may
  simply not serialise; treat "the optimal route does not fit" as an expected case rather than an
  anomaly.
- **Oracle-priced perps invert the usual fill problem.** On a book you worry about spread and
  depth. Against JLP at the oracle price you worry instead about the signal series and the fill
  series becoming *the same series*, which is a lookahead hazard rather than a convenience. A
  naive backtest trades on the print it also fills at, a zero-cost round trip that looks
  spectacular and is fiction. Cost it with the stack from "Market structure" — 12 bps base, price
  impact bounded at 50 bps **per side**, plus carry — and note that the linear impact term is
  computable from published values while the imbalance term's `factor`, `exp` and threshold are
  per-custody on-chain values Jupiter does not publish. So **total price impact cannot be
  precomputed from public documentation**: read the custody account, or take the 50 bps cap per
  side as your worst case.
- **The fill is not yours to time, and a miss is adversely selected.** Every action is **two
  transactions** — you submit a `PositionRequest`, then one of Jupiter's keepers fulfils it, and
  the trade is not live until that second transaction confirms. You fill at the oracle price *at
  fulfilment*, not at signal time. If price moves past `priceSlippage` (UI default **2%**) in
  between, the request is **cancelled, not filled worse**. Model that carefully: you lose the fill
  precisely when the oracle gapped, which is often the move the signal wanted, so it is a biased
  fill process rather than a flat fill-rate haircut a backtest can average away.

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

**Against BTC, correlation +0.709 and beta +1.314 over the full overlap** (1,874 aligned daily log
returns, `SOL_1d.csv` × `BTC_1d.csv`), tightening to **+0.850 / +1.375 over the trailing
365 days** and +0.840 / +1.277 over the trailing 90. So "high-beta BTC proxy" is roughly right
in magnitude, but the coupling is far stronger recently than the full-sample number implies: at
r = 0.85 only ~28% of SOL's daily variance is independent of BTC. A SOL-plus-BTC book is closer to
one bet than two, and any multiple-testing correction across both should say so.

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

**The hourly series is not a uniform clock.** It carries **two 6-hour gaps**, ending 2025-10-25
21:00 and 2026-05-08 07:00 UTC — disclosed in `research/sweep.py` and confirmed on the file. Each
omits 5 bars, so **10 bars are missing against the 8,823 present, 0.11%**. A small share, but
anything that treats bar index as elapsed time (an annualisation factor, a bar-count split, a
rolling window in hours) is working from a slightly wrong calendar.

## What this project has already measured on SOL

Findings 1–8 come from `research/RANKED_LISTS.md`, which is machine-verified against its own
result CSVs by `research/verify_numbers.py`. Two carve-outs, because that guarantee is narrower
than it sounds. **Finding 9 is outside it** — it cites its own artifacts inline, and
`verify_numbers.py` does not read them. And **finding 3's headline PBO figures are outside it
too**: they live in `research/results/cpcv_pbo.json`, which the verifier never opens — its only
PBO check is a lookup against the `geometry_*.json` sidecars, scoped to a different paragraph. The
verifier is also explicit that it covers *parsed* figures only and "does not prove completeness".
Verified means transcription-checked against a run, not independently recomputed.

**Every Sharpe below is net of one specific simulation contract, and it is a CEX one.** From
`research/sweep.py` and `research/cross_asset_cpcv.py`: `fee_bps=6.0`, `slippage_bps=2.0`,
`fill_delay=1` — 6 bps fee plus 2 bps slippage per fill on notional, and a signal on bar *t* fills
at **bar *t+1*'s open**, not at the close that produced it. Engine defaults carry the rest: **spot
mode, leverage 1.0, no shorting**, so every one of the 1,287 configurations is long-or-flat with
exposure in {0, 1}. Two consequences worth carrying. These figures do charge trading costs, but
they charge the *wrong* ones for any Jupiter route — nothing here pays the base fee, the impact
terms or borrow carry from "Market structure". And "beating buy-and-hold" through the bear leg
meant **being out of the market, not being short**, which is what findings 5 and 6 actually
measure.

**Two different methods produced the findings below, and mixing them up matters.** The primary
method is combinatorial purged cross-validation — 8 blocks, k=2, **up to** 28 paths — over 25
registered strategies at 3 horizons, giving **75 singles** (25 × 3), 1,002 pairs and 210
triples, 1,287 configurations. It is **purged in name only**, and the module says so: the
strategies fit nothing, so purge and embargo are degenerate, and the only leakage control is
warming each block from the bars immediately preceding it (`backtester/core/cpcv.py`). Add a
*fitted* strategy to this harness and nothing here protects you. Findings 3, 4, 5, 7 and 8 come
from that method. Findings **2 and 6 come from the superseded single 70/30 split** that CPCV
replaced, and are retained because they are the evidence *for* replacing it — not because that
split is trusted. Each is labelled below.

**The three horizons are two datasets, not three timeframes.** Per `HORIZONS` in
`research/sweep.py`: **short** is `SOL_1h.csv` (8,823 hourly bars from 2025-08-01) on fast
parameters; **medium** and **long** are both the *same* `SOL_1d.csv` (1,875 daily bars from
2021-06-17), differing only in parameter scale — `ma_crossover` 20/50 against 50/200. So "short
horizon" below is a claim about a 12-month hourly window that fell almost entirely in a bear leg,
not about fast parameters on daily bars; and medium-versus-long is a parameter comparison on one
series, which is why finding 7 insists on comparing like with like.

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
the other, for no parameters and no turnover. Two discounts apply, though. Read each rank against
its field: **13 of 25 singles posted a positive median at medium but 22 of 25 did at long**, so
6th place in a field where almost everything cleared zero is the weaker of the two results. And
buy-and-hold is **measured on more paths than anything it is compared against** — it needs no
warm-up, so all 8 blocks stay usable and it gets the full 28 paths, while slower rivals forfeit
blocks to their own lookback and run on 21 or 15. Its interval is the tightest in the study by
construction, not by merit. (Its 16 CPCV trades do clear the 10-trade evidence floor discussed
below; the "1 trade" figure attaches only to the superseded 70/30 split.)

**6. "Beat the baseline" is nearly meaningless when the baseline lost 71%.** *(single 70/30
split — not CPCV.)* At the medium horizon 105 of 109 configurations beat buy-and-hold — by
losing less. **Five made money.** At the long horizon, one of 38.

**7. Combining signals raises fragility as well as performance.** Compared like with like —
the top pairs are long-horizon, so the comparison must be against long-horizon singles — the
median parameter-perturbation ratio goes from **0.171** for singles to **0.44** for the top
pairs, **2.6×** the parameter sensitivity. The ratio is `ratio_to_iqr`: the largest absolute
shift in median Sharpe from any single ±10% parameter nudge, divided by that configuration's own
path IQR — so 1.0 means one nudge moves the result by its whole interquartile spread. (Against
the *pooled* singles median of 0.208 across all three horizons the multiple is 2.1×; quoting
0.21 alongside "2.6×" mixes the two and is the arithmetic slip to avoid.) PBO and perturbation
are independent methods pointing the same way.

**8. The largest single sensitivity was the evaluation geometry, not any strategy parameter.**
Changing CPCV from 8 blocks to 9 moved the best pair's median Sharpe by **−0.441**, more than
the worst parameter nudge (−0.392). The result depends more on how the data is sliced than on
the strategy's own settings.

**9. The five recommended configurations do not transfer off SOL.** *(Measured 2026-08-05;
`research/CROSS-ASSET-TRANSFER.md`, `research/results/cpcv_top5_sol_doge_zec_1d.csv`.)* Run
unchanged — SOL-tuned parameters, deliberately not refitted — on DOGE and ZEC, **all ten transfers
degraded and not one improved**; median degradation −0.821 on DOGE and −0.753 on ZEC.

*The rank inverted again.* On the **same 15 paths**, the SOL-#2 configuration
`any(hurst_switch+ou_reversion)` is **100% positive on SOL and 0% positive on DOGE** — not one
path in fifteen — while the lower-ranked #3 and #4 are the only two positive on all three
assets.

*The path count is thinner than the headline.* These five configurations resolve to **15 or 21
paths, never the nominal 28**, because slow parameters leave only 6 or 7 of the 8 blocks usable.
The top-5 evidence is weaker than the geometry advertises.

*Across all 25 singles on five assets,* **eight
are positive everywhere and not one of the eight is from a reversion family** — equivalently, no
reversion-family strategy clears all five. Families come from the repo's own `FAMILY` dict
(`backtester/core/strategies/__init__.py`), which splits `mean-reversion` from
`oscillator-reversion`; "reversion family" here means both. And on
ZEC, zero-parameter buy-and-hold (+0.659) beat all five recommended configurations, the best of
which reached +0.492 — though that comparison crosses horizons, since the ZEC buy-and-hold run is
medium and four of the five configurations are long. Only #2, the +0.492, is strictly
horizon-matched.

That is the strongest available answer to "does a SOL result mean anything elsewhere", and the
answer is mostly no — with the qualification that a poor DOGE or ZEC number is evidence about
**SOL's parameters**, not about those coins, precisely because nothing was refitted.

## Known failure modes for traders

- **Fitting the cycle.** Five years of SOL is one bull and one bear. A strategy tuned across
  it is tuned to a single regime transition, and CPCV's paths resample that same history. They
  widen the estimate, they do not add a second cycle. The 28-path headline is close to fiction:
  of the 1,287 configurations, **3 ever ran on 28 paths (0.2%) and all three are `buy_and_hold`**;
  1,094 ran on 21 and 190 on 15.
- **Trusting a rank.** With PBO at 0.700, being top of the table is not evidence. Rank by how
  many independent checks a configuration clears — see the checklist under "For this backtester",
  which is the canonical one — not by Sharpe.
- **The evidence floor is 10 out-of-sample trades** (`MIN_OOS_TRADES`, `research/sweep.py`).
  Slow parameters on this series generate single-digit trade counts. A Q1 path Sharpe of exactly
  0.000 usually means most paths took no trade at all.
- **Assuming a CEX fill model.** A backtest priced on Coinbase closes describes a Coinbase
  execution, long-only and unlevered at 8 bps a side. Routing the same strategy through Jupiter
  changes the fill mechanism entirely — oracle pricing, keeper latency, cancellation instead of a
  worse fill, and three fee terms none of these numbers pay.

## For this backtester

**SOL is the primary asset and the only one with both daily and hourly history**: `SOL_1d.csv`
(1,875 bars, 2021-06-17 →) and `SOL_1h.csv` (8,823 bars, 2025-08-01 →).

What the measured PBO implies for any *new* SOL result: **a good number is not evidence until
it has cleared something other than the ranking that produced it.** Four checks, and this is the
canonical list — the "Trusting a rank" bullet above points here:

1. Perturb the parameters ±10% and re-run.
2. Check the fraction of paths positive, not the median alone.
3. Compare against buy-and-hold on the same bars.
4. Test whether the result survives a change of asset or timeframe — the check finding 9 above
   now actually performs.

Only checks 1 and 4 have a command. **None of the four has an established reject line**: 0.171
versus 0.44 on perturbation, and buy-and-hold's 68% of paths, are reference points rather than
thresholds, and the file will not invent a pass mark. Read them comparatively.

*The five-asset picture.* At the **medium** horizon the same 25 strategies range from 25-of-25
positive on BTC daily down to 13-of-25 on SOL daily (24/25 ZEC, 18/25 ETH, 16/25 DOGE) — **but
those raw counts read high, and after the 10-trade evidence floor BTC is 24 of 24 and ETH is 18 of
24.** `cpcv_evaluate` flags an under-10-trade configuration `insufficient`; `cross_asset_cpcv.py`
prints it DROPPED yet still counts it in the headline, unlike `sweep.py` and `cpcv_sweep.py`, which
drop such rows from their rankings. BTC's below-floor row is its rank-1 `ou_reversion` on 6 trades;
ETH's is `hurst_switch` on 4, whose median is exactly 0.000. The SOL, DOGE and ZEC counts stand as
quoted — all 25 clear the floor on each.

*The timeframe contrast.* On SOL's *hourly* bars **not one of the 25 is positive** — though hourly
**is** the short horizon here, so that is finding 4 restated, not a sixth independent asset. And
`hurst_switch`, 1st of 25 on SOL daily, is **23rd of 25 on SOL hourly**: same strategy set, one
timeframe change. That pair of ranks is written down in neither results doc; it comes from joining
`cpcv_all25_sol_doge_zec_1d.csv` to `cpcv_all25_1h.csv` on the strategy name. On this dataset the
*data* has repeatedly explained more than the strategy.

**Run the commands in this order — the last two overwrite results the citations above depend on.**
`verify_numbers.py` picks up `perturb_*.csv` by glob, so running `perturb.py` first makes the
verification validate this document against your own fresh output with the baseline already gone.
`cross_asset_cpcv.py --top5` leaves the verifier alone — it reads CPCV results by fixed filename,
`cpcv_results.csv` and `cpcv_combos_results.csv` — but it overwrites the exact CSV finding 9 cites:

```bash
python3 research/verify_numbers.py                    # FIRST: baseline gate, reads only
python3 research/perturb.py --horizon long --all-singles
#   writes research/results/perturb_all_singles_long.{txt,csv,json}
python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC --skip-self-test
#   writes research/results/cpcv_top5_sol_doge_zec_1d.csv — the artifact finding 9 cites.
#   Without --skip-self-test it first reproduces the BTC/ETH reference run as a gate, which
#   needs cpcv_all25_btc_eth_1d.csv plus data/BTC_1d.csv and data/ETH_1d.csv, and refuses to
#   report new assets if that reference does not reproduce.
```

Commit or copy `research/results/` before running the last two. On a disagreement, the authority
order is the result CSVs, then `RANKED_LISTS.md` (AS OF 2026-08-04), then this file.

## Sources

- CoinGecko API `/coins/solana`, 2026-08-05 — price, cap, volume, supply, ATH.
- `~/dev/solmargintrader/research/RANKED_LISTS.md` (AS OF 2026-08-04) — every measured figure
  in "What this project has already measured". `research/verify_numbers.py` checks it against
  `sweep_results.csv`, `cpcv_results.csv`, `cpcv_combos_results.csv`, `perturb_*.csv`,
  `geometry_*.csv` and `geometry_*.json`. It does **not** read `cpcv_pbo.json`, `cpcv_all25_*` or
  `cpcv_top5_*`, which is why finding 3's PBO figures and all of finding 9 fall outside the
  guarantee; and it checks only figures it can parse, so it prevents regression rather than
  proving completeness.
- `~/dev/solmargintrader/data/SOL_1d.csv`, `SOL_1h.csv`, `BTC_1d.csv` — bar counts, date ranges
  and closes, plus the annualised volatility, drawdown, and correlation/beta figures computed from
  them. The Coinbase `SOL-USD` provenance is the repo's own fetch convention, not a cited source.
- `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` — leader
  schedule, stake-weighted ingress, priority-fee arithmetic, dropped-vs-reverted, local fee
  markets, blockhash expiry, and the 1.4M-CU per-transaction ceiling.
- `~/.claude/skills/blockchain/references/solana-sealevel-and-svm.md` and
  `solana-account-model-and-state.md` — up-front account declaration, shared read locks against
  exclusive write locks, and why a single writable pool serialises. **Proof of History is this
  file's own one-line summary and is not backed by any reference in the hub** — treat the
  verifiable-delay-function framing as unverified.
- `~/.claude/skills/trading-and-investing/references/jupiter-swap-routing-and-orders.md` — the
  1,232-byte transaction-size ceiling and route serialisation.
- `~/dev/solmargintrader/research/CROSS-ASSET-TRANSFER.md` and
  `research/results/cpcv_all25_btc_eth_1d.csv`, `cpcv_all25_sol_doge_zec_1d.csv` and
  `cpcv_all25_1h.csv` — the five-asset positive counts and the SOL-hourly 0-of-25 from the prose,
  the `hurst_switch` 1st-to-23rd rank pair computed from the two CSVs rather than quoted from the
  prose. That results directory is regenerated in place and several filenames are derived from the
  flags that produced them, so match on a prefix rather than a filename: `cpcv_all25_*`,
  `cpcv_top5_*`, `perturb_all_singles_*`.
- `~/dev/solmargintrader/research/results/top_coins.csv` (CoinGecko `/coins/markets`,
  2026-08-05T02:15:22Z) — every cross-coin comparison in this file, for all ten spokes at one
  timestamp. The canonical ten-coin table lives in `[^turnover-std]` below and nowhere else; a
  second copy of it is how the earlier drift happened. Verify with
  `python3 research/turnover_table.py --check`; nothing in the repo re-pulls the CSV, so a refresh
  means a fresh `/coins/markets` call written to that path.
- `~/.claude/skills/trading-and-investing/references/jupiter-perps-trading.md` — oracle execution,
  the two-step keeper flow and `priceSlippage` cancellation, and the whole fee model: the 0.06%
  each-way base fee, the linear-plus-imbalance price impact fee, what `maxPriceImpactFee` bounds,
  and the borrow fee's non-negativity and SOL rate reference.
- `~/.claude/skills/trading-and-investing/references/solana-dex-and-amm-landscape.md` — venue
  taxonomy and in-range liquidity against headline TVL. `jupiter-jlp-pool.md` — the JLP side of
  the same venue.
- Helius *MEV Report*, `https://www.helius.dev/blog/solana-mev-report` — the 75.7% revert figure,
  flagged single-source above; reached via the `solana-transaction-execution-and-mev.md` citation
  rather than read directly.

Unverified and deliberately not asserted: a dated SOL unlock/vesting schedule; current
inflation rate and terminal rate as of 2026; outage dates and counts; staking participation
share; spot-ETF and wrapper access and any flow it carries — two sibling spokes cover this for
their asset and this one does not; the Proof of History framing above; and **holder and
validator-stake concentration** — who could actually move the float. That last one is also a
question the other spokes in this directory answer and this one does not; it is a gap, not a
non-issue. Each would need a current primary source, and none is load-bearing for the backtest
findings above.

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
