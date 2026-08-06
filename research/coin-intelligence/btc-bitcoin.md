---
name: btc-bitcoin
description: Trader-facing reference on Bitcoin — mechanics, supply, price regimes, market structure, volatility/correlation, liquidity, and what a BTC backtest does and does not prove about SOL. Read before using BTC as a signal source, a benchmark, or a cross-asset generalisation test.
---
# Bitcoin (BTC)

> **Educational reference for a systematic backtesting project. NOT investment advice.**
> Nothing here is a recommendation to buy, sell, or hold. Simulated past performance does not
> predict future results.

**Attribution convention.** Every figure carries one of five tags:

- `[local]` — computed first-party from `data/BTC_1d.csv` in this repo (Coinbase BTC-USD daily,
  2021-06-17 → 2026-08-04, 1875 bars).
- `[repo]` — computed from a research artifact under `research/`, carrying that artifact's AS-OF stamp.
- `[corpus]` — from the local skill corpus, carrying its **original** verified-as-of stamp, not today's.
- `[web]` — verified against a live source on the date shown.
- `[web-derived]` — arithmetic on `[web]` figures; decays with the pull it came from.

Anything I could not land in one of those five is marked **unverified**.

> **On corpus stamps.** Most corpus facts here are stamped **2026-06-16** or **2026-06-21**. Three
> corpus files (`cross-asset-generalisation-testing`, `asset-specific-vs-universal-parameters`,
> `empirical-backtest-findings-log`) legitimately carry **2026-08-04** — they are built from this
> repo's own research, not from the web. Nothing is restamped to today that shouldn't be.

> **Two corpus corrections this document had to make.** Live sourcing on 2026-08-04 contradicted the
> corpus on two load-bearing points: **CME is no longer closed at weekends** (24/7 went live
> 2026-05-29), and the corpus's **2024/2025 ETF inflow figures cannot be reconciled** with the
> cumulative-since-launch total. Both are corrected in place below and flagged where they appear.

---

## Snapshot (AS OF 2026-08-04)

| Metric | Value | Source |
|---|---|---|
| Price | **$64,401** | `[web]` CoinGecko `/coins/markets`, 2026-08-05T02:15:22Z |
| Market cap | **$1,292.1B** | same call |
| 24h volume (all venues) | **$23.03B** | same call |
| **Turnover (24h vol ÷ mcap)** | **1.78%** — 6th of the ten coins here[^turnover-std] | `[web-derived]` from the two rows above |
| Rank | **#1** by market cap; ~5.7× #2 (ETH, $226.1B) | same call |
| Implied circulating supply | **~20.06M BTC** (= mcap ÷ price) = **95.5% of the 21M cap** | `[web-derived]` from the CoinGecko row above |
| All-time high | **$126,296 intraday / $124,720 close, 2025-10-06** | `[local]` Coinbase BTC-USD |
| Drawdown from ATH | **−49.4%** from the high (Coinbase close ÷ Coinbase high — **not** the composite price above, which gives −49.0%); −48.8% close-to-close | `[local]` |
| Trailing 30d realised vol | **29.4% annualised** — ~9th percentile of the 5-year distribution | `[local]` |
| Coinbase BTC-USD close, same day | **$63,882.61** — **0.8% below** the CoinGecko composite | `[local]` |

> **There is no single "BTC price."** The last row is not an error. CoinGecko's $64,401 is a
> volume-weighted composite across many venues; this repo's data is one venue's BTC-USD book. Part
> of the 0.8% gap is timing — the CoinGecko pull is stamped ~2h after the 2026-08-04 daily bar
> closes — and part is genuine cross-venue basis; **I have not decomposed the two.** The general
> point stands regardless: with no NBBO and no consolidated tape, every BTC figure is
> venue- and timestamp-specific, and 0.8% is larger than most strategies' per-trade edge. **Never
> mix a composite price with single-venue OHLC in the same calculation.**

> **On the two dates in this file.** The AS-OF date is **2026-08-04** — the last complete daily bar
> in `BTC_1d.csv` — while the CoinGecko composite pull is stamped **2026-08-05T02:15:22Z** and the
> Deribit/Coin Metrics pulls are stamped 2026-08-05. **The two differ by design**, and that ~2h
> offset is part of the price gap discussed above. Anywhere this document says "today," "current,"
> or "live," it means **2026-08-04/05 and nothing later** — re-date before reuse.

> **These figures decay, and the top three decay fastest.** Price, market cap, and volume are a
> snapshot of one API call at one instant; BTC has moved more than 10% in a day 16 times in this
> sample `[local]`. Treat price/mcap/volume as stale the moment you read them and re-pull before
> using them for anything sizing-related. The **structural** rows — the 21M cap, the halving
> schedule, the ~95.5%-issued figure — decay on a scale of years, not hours. The ATH and drawdown
> decay only when a new high is set.

**The one-line framing that matters more than the price:** BTC is not near its highs. It topped at
~$126K on 2025-10-06 and has roughly halved since `[local]`. Any intuition carried over from the
2024–25 bull market — about trend persistence, about ETF bid, about correlation — is intuition from
a regime this asset is no longer in.

---

## What it is, mechanically

**UTXO ledger, not an account ledger.** There is no stored "balance" on-chain. Value exists as
discrete **Unspent Transaction Outputs**; a wallet's balance is the sum of every UTXO its keys can
unlock. Spending consumes whole UTXOs as inputs and creates new outputs, with the remainder returned
as a **change output**. Anything not assigned to an output is the **fee** — fees are *implicit*
(`sum(inputs) − sum(outputs)`), there is no explicit fee field. `[corpus, verified 2026-06-16]`

**Why a trader should care about the UTXO model at all:** it is the reason Bitcoin has no native
smart-contract/DeFi layer worth trading, no staking yield, and no on-chain leverage. There is no
"BTC-native" carry. Every leveraged or yield-bearing BTC position is a *claim on a counterparty* —
an exchange, a custodian, a wrapped-BTC bridge, or an ETF issuer. That is a structural difference
from SOL/ETH, not a cosmetic one.

**Spending conditions are Bitcoin Script** — stack-based and deliberately **non-Turing-complete**
(no loops). Address/output types: **P2PKH** (`1…`), **P2SH** (`3…`), **P2WPKH/P2WSH** (`bc1q…`,
SegWit v0), **P2TR** (`bc1p…`, bech32m, Taproot/SegWit v1). `[corpus, verified 2026-06-16]`

**Proof-of-Work over an 80-byte header.** Miners double-SHA256 the header (version, prev-block-hash,
Merkle root, time, nBits/target, nonce) seeking a hash below target. `[corpus, verified 2026-06-16]`

**Difficulty adjustment: every 2016 blocks (~2 weeks), clamped to a 4× swing per period**, targeting
a 10-minute average block time. `[corpus, verified 2026-06-16]` The clamp is the load-bearing
detail traders miss: after a hashrate shock (China 2021, a grid event, a price crash forcing
capitulation), block intervals stay wrong for **up to two weeks** and the correction is capped at
4× in either direction. Bitcoin cannot re-price its security budget quickly.

**Halving: the block subsidy halves every 210,000 blocks (~4 years).**
50 → 25 → 12.5 → 6.25 → **3.125 BTC since the April 2024 halving (block 840,000)**.
`[corpus, verified 2026-06-16]`

**Next halving — block 1,050,000, subsidy 3.125 → 1.5625 BTC. Estimated ~April 2028.**

| | Value |
|---|---|
| Current block height | **961,040** `[web, 2026-08-04]` |
| Blocks remaining | **88,960** `[web]` |
| Estimated date | **~2028-04-18**, sources ranging **March–May 2028** `[web]` (CoinWarz "624 days"; NiceHash countdown 2028-04-10) |
| My independent derivation | height ≈960,384, ~622 days → 2028-04-17 `[local]` |

The `[local]` derivation (836 days × 144 blocks/day from the 2024-04-20 halving) lands within **656
blocks** of the live height and within **2 days** of the published countdown — the two agree, which
is the point of showing both. **It is still an estimate, not a date:** blocks arrive faster than 10
minutes while hashrate grows, so the date drifts earlier in expansion and later in contraction.
Treat **±1 month** as the honest error bar and re-derive from a live height before relying on it.

**Coinbase maturity: 100 blocks.** Newly mined BTC is unspendable for ~16.7 hours.
`[corpus, verified 2026-06-16]` Relevant only if you model miner sell-flow with daily precision.

**Two upgrades define the modern protocol.** **SegWit** (2017) moved the witness out of the txid
preimage — fixing third-party malleability (the Lightning prerequisite) and redefining the block
limit as **4,000,000 weight units**. **Taproot** (Nov 2021) added **Schnorr signatures**, P2TR
key-path vs script-path spends, and **MAST**. Both were soft forks. `[corpus, verified 2026-06-16]`

**Settlement finality is probabilistic, not absolute.** Exchanges typically require **3–6
confirmations (~30–60 min)** before crediting large BTC deposits, vs ~5 minutes for ETH and seconds
for SOL. `[corpus, verified 2026-06-21]` For a trader this is a real constraint: **you cannot move
BTC between venues fast enough to arbitrage an intraday dislocation.** Cross-venue arbitrage in BTC
is executed with pre-positioned inventory on both sides, not by moving coins.

---

## Supply and issuance

**Hard cap 21,000,000 — actually ~20,999,999.9769 BTC** because of integer-satoshi truncation in the
subsidy schedule. Issuance ends ~2140; miners earn fees only thereafter.
`[corpus, verified 2026-06-16]`

**Current state** `[web-derived]`, from the 2026-08-04 CoinGecko snapshot (mcap ÷ price) and the
known 3.125 BTC subsidy:

| | Value |
|---|---|
| Circulating supply (implied) | ~20,063,000 BTC — **95.5% of the cap already issued** |
| Issuance now | 3.125 BTC/block × ~144 blocks/day = **~450 BTC/day** ≈ 164,250 BTC/yr |
| Issuance rate | **~0.82%/yr** of float |
| Notional new supply/day at $64,401 | **~$29.0M/day** |
| After the ~2028 halving | 1.5625 BTC/block = ~225 BTC/day, ~0.4%/yr |

**What the halvings actually did — and the trap in reading them.** Each halving cut the *flow*, but
because the *stock* keeps growing, each successive halving is a smaller proportional shock. The
schedule is deterministic in block terms, so every row below is **derived, not estimated**: supply
at each halving is the cumulative subsidy of the prior 210,000-block eras, the rate is
`subsidy × 144 blocks/day × 365 ÷ supply`, and the cut is the pre-halving rate at that same supply
minus the post-halving rate.

| Halving (block) | Subsidy after | Supply at halving | **Issuance rate after** | **Instantaneous cut** |
|---|---|---|---|---|
| 2012 (210,000) | 25 BTC | 10,500,000 | **12.51%/yr** | **−12.5pp** |
| 2016 (420,000) | 12.5 BTC | 15,750,000 | **4.17%/yr** | **−4.2pp** |
| 2020 (630,000) | 6.25 BTC | 18,375,000 | **1.79%/yr** | **−1.8pp** |
| **2024 (840,000)** | **3.125 BTC** | 19,687,500 | **0.83%/yr** (1.67% → 0.83%) | **−0.8pp** |
| ~2028 (1,050,000) | 1.5625 BTC | ~20,343,750 | **0.40%/yr** | **−0.4pp** |

`[local]` derived. Today's rate, on ~20.06M actual float, is **0.82%/yr**.

**Read the last column.** The 2012 halving removed 12.5 percentage points of annual issuance; 2016
removed 4.2pp; 2020, 1.8pp; 2024, 0.8pp; 2028 will remove ~0.4pp. **Each halving is between a third
and a half the supply shock of the one before, and the 2028 event is ~31× smaller than 2012's.**
Any model that treats halvings as equivalent events across cycles is mis-specified by construction.

**The trader-relevant conclusion is the opposite of the popular one.** At ~$29M/day, miner issuance
is roughly **0.13% of the $23.03B daily traded volume**. New supply is no longer a material share of
flow. Halvings were a meaningful supply shock when issuance was 12%/yr; at 0.82%/yr the *mechanical*
effect on the supply/demand balance is close to noise. **The corpus documents this empirically: the
2024 cycle produced only ~31% gains in the year after the halving, versus 300%+ after 2020**
`[corpus, verified 2026-06-21]`. Extrapolating halving-cycle returns is explicitly listed as an
anti-pattern in the corpus, and this asset is now ~49% below its post-halving high `[local]`.

**Where the halving *does* still bite: miner economics, not price.** Cutting subsidy in half halves
the dominant revenue line for a capital-intensive industry with fixed energy contracts. That forces
either a hashprice recovery (higher BTC price), a fee-revenue recovery, or capitulation by
high-cost miners. At ~$64K — roughly half the October 2025 high `[local]` — post-halving miner
margin is compressed, which is a supply-of-sellers story rather than a supply-of-coins story.

---

## What actually drives the price

Be suspicious of any single-factor explanation. What the evidence supports is that **BTC trades in
regimes, and the dominant driver changes with the regime.** Naming the regime is more useful than
naming a driver.

**Regime 1 — retail/leverage-led momentum (2020–21, 2023–24).** Price is driven by reflexive
positioning: rising price → rising perp open interest and positive funding → more leveraged longs →
higher price, until a deleveraging event. Realised vol is high. In this repo's data, 2023 (+155.8%)
and 2024 (+120.8%) are this regime `[local]`. Diagnostic: sustained positive funding, rising OI,
altcoins outperforming BTC.

**Regime 2 — macro/liquidity beta (2022, and arguably 2026).** BTC trades as a long-duration
risk asset — a high-beta expression of global liquidity and real rates. 2022 was the clean case:
−64.2% `[local]`, coincident with Fed tightening, and the crypto-native credit chain
(Terra/LUNA → 3AC → Celsius/BlockFi/Voyager → FTX, ~$2T of market cap destroyed)
`[corpus, verified 2026-06-21]`. Diagnostic: correlation to Nasdaq rises; BTC stops responding to
crypto-specific news.

**Regime 3 — institutional allocation flow (2024–25).** The spot ETF complex made BTC purchasable in
ordinary brokerage and retirement accounts. Cumulative net inflows **peaked at roughly $57B before
the 2026 reversal and stand at ≈$51.6B as of 2026-08-04** `[web]` — a genuine, new, relatively
price-insensitive bid while it lasted. (The corpus's
*annual* figures for 2024/2025 do not reconcile with this total; see the correction in Market
structure. The cumulative figure is the sourced one.) Diagnostic: price responds to daily ETF
creation/redemption prints, and realised vol *compresses* — 2025 realised 41.9%, the lowest full
year in this sample `[local]`, with DVOL's annual mean falling 57.7 (2024) → 46.0 (2025) `[web]`.

**Regime 4 — the unwind (2025-10 → now).** This is where the asset currently sits. Monthly closes
from the top `[local]`:

| | 2025-10 | 2025-11 | 2025-12 | 2026-01 | 2026-02 | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 |
|---|---|---|---|---|---|---|---|---|---|---|
| Close | 109,555 | 90,370 | 87,498 | 78,648 | 66,968 | 68,222 | 76,306 | 73,575 | 58,524 | 62,826 |
| Return | −4.0% | **−17.5%** | −3.2% | −10.1% | **−14.9%** | +1.9% | +11.8% | −3.6% | **−20.5%** | +7.4% |

Three ~15–20% down months in ten, one sharp +11.8% bear rally in April 2026, and a −49% total
drawdown from the high. Note the shape: this is **not** a single capitulation, it is a stair-step —
which is the harder pattern for both trend-followers (whipsawed by the April bounce) and
mean-reverters (each "oversold" level kept going).

**The named events inside that path** `[web, 2026-08-04]`:

- **2025-10-06** — ATH. Prints vary: **$126,296** (this repo's Coinbase BTC-USD file `[local]`, and
  Galaxy's print), **$126,210** (a second Coinbase-sourced aggregator), **$126,198** (SoFi) intraday;
  daily close **$124,824** (Galaxy) vs **$124,720** `[local]`. **The same venue reads differently
  through different aggregators — this is a data-pipeline spread, not only a venue spread. Quote a
  range, not one number.**
- **2025-10-10/11** — the $19B liquidation (see driver 3). Four days after the top.
- **2026-02-05/06** — **−14.0% close-to-close on 02-05** `[local]` (−15.0% high-to-low intraday;
  reported as ~−15% by `[web]`), with the ~$60,000 print arriving on the **02-06 low of $60,001**
  `[local]`, the lowest since October 2024; >$1B liquidated. BTC posted a **−6.05σ** rate-of-change
  move and sat **−2.88σ below its 200-day MA, "a level not observed at any point in the past 10
  years"** `[web, VanEck]`. Trigger: a 15% global tariff pricing out rate cuts (March-cut odds
  20% → 6%).
- **2026-07-01 — cycle low to date: $57,717** `[local]`, then **+8.3%** to a $62,520 close by 07-03
  on a weak payroll print. *(Some `[web]` sources date this low 07-02; the repo's Coinbase series
  puts the $57,717.55 low on 07-01, with 07-02's low at $59,520.)*

**One widely-watched level.** As of 2026-06-24 BTC traded *below* its **200-week moving average
(≈$62,800)** `[web, CoinDesk 2026-06-24]` — and I can corroborate first-party: the 1400-day mean of
Coinbase closes was **$62,301** that day against a $60,983 close `[local]`, agreeing to 0.8%. **The
level rises as old bars roll off: on 2026-08-04 it reads $63,570 `[local]`, and today's $63,882.61
close sits 0.5% above it**, having crossed back up through the zone. Whatever you think of the
indicator, enough participants watch it to make the zone reflexive.

**One dated house view says the bottom is not in.** Galaxy Research (2026-06-12, data to 06-09)
found only **4 of 13** bottom indicators triggered, noted price never went below the on-chain cost
basis (~$53K, MVRV 1.14), and observed the −51% drawdown was shallow against −77/−84/−85% at prior
cycle lows; base case **$40–46K**, harsh case $30–37K, window **late 2026** `[web]`.
**This is one firm's model as of one date, not a forecast this document endorses or repeats as
likely** — it is recorded because a backtester should know that a dated analysis put the drawdown
as unfinished, i.e. that the sample may not yet contain this cycle's trough.

**Drivers with real evidence behind them:**

1. **Global liquidity / real rates.** The most defensible macro link. BTC has no cash flows, so its
   discount rate *is* its valuation. **Unverified** as to exact lag length — the popular "BTC follows
   global M2 with a 70–110 day lag" claim is widely circulated, is fitted on a short history, and I
   would not put a coefficient on it.
2. **ETF and allocator flow (2024→).** Documented and dated in Market structure
   `[web, 2026-08-04]`. This is the genuinely *new* driver of this cycle, and it is **bidirectional
   — the same channel that bid the asset up is now distributing it** (2026 YTD net outflow).
3. **Leverage and forced liquidation.** Not a driver of *level* but the dominant driver of *path*.
   **The defining event of this cycle was 2025-10-10/11, four days after the top: ~$19B liquidated
   across ~1.6 million traders — the largest liquidation event in crypto history, roughly 9× any
   prior single day.** Of the **~$9.89B captured in CoinDesk Research's venue subset** (the ~$19B is
   an all-venue total, so the two denominators differ), **70% happened in 40 minutes**, with a peak
   minute of **$3.21B** that was 93.5% forced selling. On this repo's Coinbase series 2025-10-10 ran
   **$122,600 high → $107,000 low, −12.7% intraday**, closing $112,980 `[local]`; other venues wicked
   lower. Total crypto market cap dropped ~$350B. The trigger was a US 100%-China-tariff
   announcement — a *macro* headline detonating a *crypto-leverage* structure.
   `[web, CoinDesk Research / Forbes 2025-10-13]`

   > **Note this supersedes a corpus figure.** The corpus records "~$3.21B liquidated in 60 seconds
   > (Oct 2025)" `[corpus, verified 2026-06-21]` — that is the **peak minute of this same event**,
   > not a standalone $3.21B cascade. The event total was ~$19B.

   Also documented: **~$1.9B in 4 hours, ~85% longs, BTC open interest −35% (Nov 2025)**
   `[corpus, verified 2026-06-21]`, sitting exactly at the start of the −17.5% month above; and
   **>$1B in 24h on 2026-02-05** `[web]`.
4. **Reflexive treasury/corporate demand — now confirmed running backwards.** Corporate BTC-treasury
   vehicles (DATs) were a real marginal bid in 2024–25. The mechanism is reflexive: issue
   equity/converts *above* NAV to buy BTC, which only works while the premium holds. Below NAV the
   flywheel stops and can reverse. **It has reversed** `[web, 2026-08-04]`:

   - **Strategy (MSTR) holds 843,775 BTC at an average cost of ≈$75,476** (as of the 2026-07-06 8-K;
     **whether this is pre- or post- the 3,588 BTC sale disclosed in that same filing is
     unconfirmed** — a ~0.4% swing on the loss figure). At $64,401 that is **≈$9.35B unrealised
     loss, −14.7%**; BTC must rise **+17.2%** to reach break-even. `[web + web-derived]`
   - **mNAV 0.68× as of 2026-08-03** — the equity trades at a *discount* to its own coins, so the
     ATM issuance flywheel cannot run accretively.
   - **Strategy has begun selling.** Its **2026-07-06 8-K** disclosed selling **3,588 BTC for
     ≈$216M** under a stated **"BTC Monetization Program,"** citing a preferred-dividend obligation
     **exceeding $1.5B/year**.
   - The unwind is sector-wide: **Strategy, Satsuma, Smarter Web Company, Sequans, Nakamoto and
     Empery Digital have all sold BTC**, several pivoting to AI `[web, CoinDesk 2026-07-24]`.
     **Metaplanet** (40,177 BTC — holdings as-of date **unverified**, reported alongside Q1 2026
     purchases) saw its premium collapse from **+237% (Jul 2025) to −10% (early 2026)** with a
     **$665–680M write-down**.

   **For a modeller this is the cleanest example in the document of a demand source that is a
   function of price** — it bids when price is high and sells when price is low. Treating 2024–25
   treasury demand as a constant is a specification error.
5. **Miner sell-flow.** ~$29M/day `[local]`. Real but small relative to $23B/day of volume; matters
   at the margin in thin conditions, not as a primary driver.

**Drivers with weak or negative evidence — do not build a signal on these:**

- **The halving as a price event.** See above; the corpus flags extrapolation as an anti-pattern
  `[corpus, verified 2026-06-21]`.
- **Stock-to-flow.** A curve-fit on three cycles; it has failed out-of-sample. Treated as a
  valuation anti-pattern in the corpus, which warns generally against "treating tokenomics as price
  prediction" `[corpus, verified 2026-06-16]`.
- **Funding rate as a directional entry signal.** The corpus is explicit: funding is
  **coincident/lagging, not predictive**, and high funding can persist for weeks before a
  deleveraging event `[corpus, verified 2026-06-21]`.
- **"Digital gold" as a mechanical inflation hedge.** BTC fell 64.2% in 2022 `[local]`, the highest
  US inflation year in four decades. Whatever BTC is, it did not hedge that.

---

## Market structure

**Where it trades.** No Reg NMS, no NBBO, no consolidated tape, no industry-wide spot circuit
breakers, 24/7/365. BTC/USDT on Binance and BTC/USD on Coinbase are independent order books kept
close by arbitrageurs, not by regulation. `[corpus, verified 2026-06-21]`

| Venue | Jurisdiction | Spot maker/taker (base tier) | Max perp leverage | Note |
|---|---|---|---|---|
| Binance | Cayman Is. | 0.10% / 0.10% | 125× | Largest global volume; 2023 DOJ settlement $4.3B; SEC case dropped Feb 2025 |
| Coinbase | USA (COIN) | 0.40% / 0.60% | ~10× (Coinbase Intl) | Largest US retail; dominant ETF custodian; **source of this repo's BTC data** |
| Kraken | USA | 0.25% / 0.40% | limited for US | |
| OKX | Seychelles | 0.08% / 0.10% | 100× | Exited US |
| Bybit | Dubai | 0.10% / 0.10% | 100× | Major perps venue |
| BitMEX | Seychelles | −0.02% / 0.075% | 100× | Invented the perp (2016-05-13) |

`[corpus, verified 2026-06-21]`

**The venue landscape shifted materially in 2026** `[web, 2026-08-04]`: **Binance is still #1 in
spot but losing share — 27% (Q1 2026) → 24% (Q2 2026)**, on $731B Q2 spot volume. **Coinbase hit an
all-time-high 8.6% share in Q1 2026.** The structural gainer is **Hyperliquid**, an on-chain perp
venue now top-3 in derivatives (~$492.7B Q1 2026 volume, ~$6.0B average open interest). **A
liquidity or fee assumption calibrated on the 2021–24 venue mix is out of date.** *(2026 exchange
failures or insolvencies were not checked — treat as unknown, not as "none.")*

**Perpetual futures dominate.** Perps are ~**93% of all crypto futures volume**
`[corpus, verified 2026-06-21]`. Three prices matter and confusing them is a live risk:
**index** (cross-exchange composite, drives funding), **mark** (manipulation-resistant median,
**drives liquidations**), and **last** (drives displayed P&L). A wick in the last price that does not
move the mark will not liquidate you; a slow drift in the mark will, without a dramatic candle.
`[corpus, verified 2026-06-21]`

**Funding mechanics.** `F = average premium index + clamp(interest rate − P, −0.05%, +0.05%)`, with
the interest component fixed at 0.01%/8h. Standard interval is **8-hourly at 00:00/08:00/16:00 UTC**
on Binance/Bybit/OKX/BitMEX; Coinbase International and dYdX pay hourly. Funding accrues on
**notional, not margin** — at 10× leverage you pay funding on 10× your equity.
`[corpus, verified 2026-06-21]` This is a real, modellable cost that a naive backtest omits.

**The current funding regime is negative — a rare state.** BTC perps ran a **negative 30-day average
funding rate for 46 consecutive days as of 2026-04-15, the longest streak since November 2022**
(Binance BTC/USDT below zero since ~2026-03-01; Bybit and OKX similar)
`[web, ~2026-04, Phemex — tier 3 exchange blog, indicative only]`. Crucially,
open interest **rose ~12% month-on-month** into mid-April despite that — **a crowded short, not a
clean deleveraging.** *(These are April readings, ~4 months stale; the current level is
**unverified**.)*

**As of their last verified readings, funding and basis pointed the same way** — negative perp
funding and a collapsed CME basis, both **2026-04** and both ~4 months stale. They are **not
independent**: both are expressions of the same de-levering. The third leg, ETF flow, has since
turned marginally positive (Jul 17–31 +$104.7M; Aug 1–4 +$211.3M), so **the three do not currently
agree** — which is itself the useful observation. Positioning signals unwound before flow did.

**Spot ETFs — the structural change of this cycle, now running in reverse.**

**Dates (firm):** SEC approved 11 spot Bitcoin ETPs on **2024-01-10**; trading began
**2024-01-11**. Nine spot Ether ETFs followed **2024-07-22/23**. `[corpus, verified 2026-06-21]`
**SEC approved in-kind creations and redemptions on 2025-07-29** (accelerated approvals to Nasdaq,
NYSE Arca and Cboe BZX; the same action raised options position limits) `[web, 2026-08-04]`.
IBIT **options launched November 2024** `[web]` — exact day unverified.

**Current scale** `[web, 2026-08-04]`:

| | Value | As of |
|---|---|---|
| IBIT net assets | **$47.48B** | 2026-08-04 (BlackRock) |
| IBIT BTC held | **738,862 BTC** | 2026-08-03 (BlackRock) |
| IBIT NAV / 52-wk range | $36.40 / **$33.19–$71.32** | 2026-08-04 |
| **IBIT YTD NAV total return** | **−26.95%** | 2026-08-03 |
| Total US spot BTC ETP AUM | **≈$76.2B** across 11 products | 2026-08-04 (CoinGlass sum) |
| Total BTC held by US spot ETFs | **≈1.18–1.19M BTC** — **`[web-derived]`**, AUM ÷ price | 2026-08-04 |
| IBIT market share | **≈62%** (47.48 ÷ 76.2 by AUM; 62.5% by coins) | 2026-08-04 |

Note IBIT's 738,862 BTC is **below** the corpus's 757,130 as of 2026-02-23 — the vehicle has shed
coins, not just value.

**2026 flows turned negative — the driver reversed.** `[web, 2026-08-04]`

| Period | Net flow |
|---|---|
| Jan 2026 | −$1.61B |
| Feb 2026 | −$207M |
| Mar 2026 | +$1.32B (first positive since Oct 2025) |
| Apr 2026 | +$1.97B (best of 2026) |
| May 2026 | negative; 13 straight outflow days 05-15→06-03, ≈−$4.3B, longest streak since launch |
| **Jun 2026** | **−$4.06B to −$4.5B — worst month on record**, beating −$3.56B (Feb 2025) |
| Jul 17–31 + Aug 1–4 | +$104.7M, then +$211.3M |
| **H1 2026** | **−$5.4B — the first negative half-year since the 2024 launch** *(KuCoin — tier-3 exchange blog, single-source, not cross-checked against Farside/SoSoValue)* |
| **2026 YTD (est.)** | **≈−$4.5B to −$5.0B net OUTFLOW** |

**Cumulative since launch: ≈$51.6–52.0B** (Farside $51,589M; CoinGlass +$51.98B / 644.14K BTC, both
2026-08-04).

> **⚠️ Corpus correction.** The corpus's 2024 (+$48.7B) and 2025 (+$46.3B) inflow figures sum to
> **$95.0B**, which cannot be reconciled with a **$51.6B** cumulative total against a verified
> −$5.4B H1 2026 — that would require −$43B in 2026. The $46.3B figure closely matches CoinShares'
> **$46.7B for all *global digital-asset investment products* in 2025**, so the likely error is a
> methodology conflation. **Treat the corpus's annual ETF inflow figures as unreliable; the
> cumulative $51.6B and the 2026 monthly series above are the sourced numbers.**

**Other structural facts** `[corpus, verified 2026-06-21]`: **GBTC** converted from a trust that
traded at a **~50% NAV discount in Dec 2022**, collapsing to ~1.18% within days of approval; it
carries a **1.50%** expense ratio against 0.15–0.25% for most competitors and has bled assets since.
Expense ratios span **0.15%–1.50%**. **BITO** (futures-based, Oct 2021, 0.95%) suffers persistent
**negative roll yield** in contango and is *not* spot-equivalent over any long horizon.

**The ETF options market has displaced the crypto-native venue.** IBIT options open interest reached
**≈$33B — 52% of the entire bitcoin options market — as of 2026-01-13**, against Deribit's ≈$26B
`[web]`. Nasdaq ISE sought a position-limit increase from 250,000 to 1,000,000 contracts
*(filing date and status unverified)*. **BTC
options price discovery now substantially sits in a US-hours, SEC-regulated venue**, which is a
different market from the one a pre-2024 backtest was fitted on.

**Why the ETF complex changed the market's shape, not just its size.** Three mechanical
consequences a trader should hold: (1) a large share of the marginal bid now arrives **only during
US equity market hours**, so BTC has acquired an equity-market session rhythm it did not have
before 2024; (2) ETF creations/redemptions concentrate custody — **Coinbase Custody is the dominant
custodian across multiple issuers** `[corpus, verified 2026-06-21]`, a concentration risk that did
not exist in 2021; (3) flow is now *reported daily and publicly*, which makes it a widely-watched
coincident signal and therefore partially priced.

**CME, and the weekend gap that just stopped existing.** CME Bitcoin futures are the regulated US
venue and carry **±10% price limits per 60-minute window** `[corpus, verified 2026-06-21]` — a
circuit breaker spot markets do not have.

> **⚠️ Corpus correction — this is the single most important structural change in this document.**
> **CME launched 24/7 crypto futures and options trading on Friday, 2026-05-29** (announced
> 2025-10-02 for "early 2026," slipped to Q2). Its first weekend traded >7,200 contracts, ~$50M
> notional. Weekend and holiday trades take the **next business day** as their official trade date
> for clearing and settlement. `[web, CME Group press release, 2026-06-01]`
> **The weekend closure is gone, and with it the structural origin of the "CME gap."**

This matters for anyone porting a strategy across the boundary: **a weekend-gap or Monday-open
effect fitted on data before 2026-05-29 is fitted on a market structure that no longer exists.** Any
such rule needs re-testing on post-May-2026 data alone, where the sample is currently ~2 months.

The historical gap distribution, measured on this repo's data over the full span `[local]`: the
Friday-close → Sunday-close move has a **median absolute size of 1.21%, with 34% of weekends
exceeding 2%, 7.5% exceeding 5%, and a maximum of 11.82%** (n=268). Those moves were real, and for
most of the sample CME had to absorb them at Monday's reopen. The folk claim that such gaps reliably
"fill" is **unverified** and is not asserted here.

**Cash-and-carry — the mechanism, then the current state.** Long spot + short perp is the
delta-neutral funding harvest: **~5–8% APY** in normal conditions, **25–50%+** during bull-market
funding spikes. Risks are funding reversal, liquidation on the short leg, exchange counterparty
risk, and fee drag. `[corpus, verified 2026-06-21]` **The basis is a regime indicator in its own
right** — a rich, positive basis means leveraged longs are paying up; a flat or inverted basis means
that bid is gone.

**That trade is largely dead as of its last verified reading.** The annualised CME basis compressed
from **15–20% to ~5%**, and CME BTC futures open interest fell to **$8.41B on 2026-04-11, a 14-month
low**, with daily volume below $3B `[web, ~2026-04, KuCoin — tier-3 exchange blog]`. **These are ~4
months stale — do not quote them as the current basis.** Directionally the message is unambiguous:
the leveraged long bid that paid for that carry is gone.

---

## Volatility and correlation

All figures in this section are `[local]` — computed from Coinbase BTC-USD daily closes,
2021-06-17 → 2026-08-04 (1875 bars), annualising daily log-return stdev by √365 (crypto trades every
day; applying the equity convention √252 to a 365-bar year **understates** vol by ~17% —
equivalently, √365 runs ~20% higher than √252 — a common and silent error).

**Realised volatility by calendar year:**

| Year | n (days) | BTC vol | ETH vol | SOL vol | BTC return |
|---|---|---|---|---|---|
| 2021 (from 06-17) | 197 | 68.8% | 86.0% | 124.8% | +21.3% |
| 2022 | 365 | 64.6% | 87.7% | 123.6% | **−64.2%** |
| 2023 | 365 | 43.6% | 46.6% | 95.9% | **+155.8%** |
| 2024 | 366 | 53.0% | 64.4% | 82.3% | **+120.8%** |
| 2025 | 365 | **41.9%** | 74.6% | 86.2% | −6.3% |
| 2026 YTD | 216 | 46.9% | 63.1% | 64.0% | **−27.0%** |
| **Full span** | 1874 | **53.2%** | **71.1%** | **98.6%** | — |

The 53.2% full-span figure agrees with the corpus's "~54% recent realised vol vs ~13–15% for the
S&P 500" `[corpus, verified 2026-06-21]` — two independent measurements landing in the same place.

**Rolling 30-day vol** ranges from **17.0% (2023-08-13)** to **96.5% (2022-06-26)**, with
p10 = 30.3%, median = 47.4%, p90 = 74.8%. **Today it reads 29.4%** — near the 10th percentile of its
own five-year history, *while the asset is 49% off its high*. That combination (deep drawdown, quiet
tape) is worth flagging: **a vol-scaled position sizer will size up right now**, and a vol-targeting
strategy fitted on this sample will be at close to maximum leverage.

**Realised-vol term structure, independently sourced.** Coin Metrics' CMBI Bitcoin index page,
retrieved 2026-08-05 `[web]`: **3-month 36.37% · 6-month 44.81% · 1-year 44.88% · 2-year 47.15%.**
Plus **30-day 30.4%** as of 2026-07-14 `[web, VanEck]` and 7-day 26% in May 2026 `[web]`. My local
2026-YTD figure (46.9%) and full-span figure (53.2%) bracket these sensibly, and the **upward-sloping
term structure — short vol well below long vol — is the quantitative statement of "quiet tape inside
a deep drawdown."**

**Implied volatility (Deribit DVOL), from Deribit's own API** `[web, retrieved 2026-08-05]`:

| DVOL | Value | Date |
|---|---|---|
| Live | **34.23** | 2026-08-05 03:13 UTC |
| Last daily close | **34.04** | 2026-08-04 |
| All-time high (close) | **156.20** (intraday 167.83) | 2021-05-23 |
| All-time low (close) | **32.38** | 2023-08-12 |
| 2026 YTD range (close) | **34.04 – 82.62** (intraday high 90.33) | 2026 |
| **Annual mean of daily closes** | **57.71 → 46.04 → 44.39** | 2024 → 2025 → 2026 YTD |

**Today's 34.04 is the lowest close since 2025-09-18 — low, but not an all-time low.** Two
corrections worth carrying: the widely-repeated claim that DVOL "mostly ranges 50–80 post-2024" is
**false** — only 49% of 2024–26 closes sit in that band and just 28% of 2025 closes; **the accurate
band is 35–60, capturing 86%.** And a circulating "nine-month low of 36.11 in May 2026" is
**mis-dated** — 36.11 is the close on 2026-07-19.

**The single most violent repricing in the sample: 2026-02-05.** DVOL closed **82.62, up +29.15
points (+54.5%) in one day**, intraday peak 90.33; 7-day ATM IV exceeded **100%**, the highest since
FTX, then more than halved to 49% `[web]`. That is the shape of crypto vol — it does not drift up,
it gaps.

> **Is the vol decline structural or just the regime?** Genuinely contested, and the popular
> "ETFs caused it" story is the weakest part. Block Scholes explicitly disclaims causality; Kang &
> Lee's placebo tests place the structural break in **2023, before the ETF**; and one analyst
> (Ferrante, 2026-04-21) argues 30d RV averaged ~58% across 2024–25 vs ~62% in 2020–23 —
> "statistically indistinguishable" — though that figure is uncited, and it does not match this
> document's own matched-window measurement: **BTC realised 53.0% in 2024 and 41.9% in 2025**
> `[local]`, a ~47% two-year mean, not ~58%. **The level decline is well-evidenced; the ETF-caused
> framing is not.** *(Kang & Lee and the Block Scholes report are cited second-hand via a research
> summary; I did not read either primary source — see open item 15.)*

**Tails.** 141 of 1874 days (**7.5%**) moved more than ±5%; 16 days (**0.9%**) moved more than ±10%.
Worst days: **2022-06-13 −15.4%**, 2022-11-09 −14.3%, **2026-02-05 −14.0%**. Best days:
2022-02-28 +14.5%, **2026-02-06 +12.3%**, 2024-08-08 +11.9%. Note 2026-02-05/06: a −14.0% day
immediately followed by +12.3%. **The largest up-days cluster inside the worst drawdowns** — which
is why short-side strategies get stopped out at the bottom and why "avoid the worst N days" and
"miss the best N days" are the same days.

**Maximum drawdown in-sample: −76.7%**, peak 2021-11-08 → trough 2022-11-21 (close $15,760).
Any risk model whose worst case is smaller than −76.7% is not calibrated to this asset's own
recent history.

**Day-of-week structure — the strongest clean effect in this dataset:**

| | Mon | Tue | Wed | Thu | Fri | **Sat** | **Sun** |
|---|---|---|---|---|---|---|---|
| Ann. vol | 65.6% | 54.5% | 57.8% | 54.8% | 60.7% | **28.1%** | **41.2%** |

**Weekend vol (Sat+Sun) is 35.3% vs 58.9% on weekdays — a ratio of 0.60.** Saturday at 28.1% is less
than half of Monday's 65.6%. BTC is nominally 24/7, but its *effective* trading week looks
increasingly like a traditional one. Mean daily returns by weekday are **not** reliably different
from zero and I would not trade the direction — the vol result is the robust one.

**Correlation to other crypto majors:**

| Pair | Full span (n=1874) | 2025 | **2026 YTD** |
|---|---|---|---|
| corr(BTC, ETH) | 0.844 | 0.822 | **0.919** |
| corr(BTC, SOL) | **0.709** | 0.804 | **0.893** |

**Correlation is rising, and it rises specifically in drawdowns.** Splitting by BTC's monthly
direction: corr(BTC, SOL) = **0.646 in BTC-up months** vs **0.755 in BTC-down months**. And 2026 YTD
— the deepest part of the drawdown — is the highest reading in the sample at 0.893.
**Crypto diversification fails precisely when it is needed.** In R² terms: BTC explains **50%** of
SOL's daily variance over the full span but **80%** in 2026.

**Beta.** β(SOL | BTC) = **1.31** full span, 1.65 in 2025, 1.22 in 2026 YTD. β(ETH | BTC) = 1.13
full span. The beta shows up in the damage: from each asset's own all-time high,
**BTC −48.8%, ETH −61.3%, SOL −71.8%** as of 2026-08-04. Also note the *timing* divergence — SOL
topped **2025-01-18**, ETH **2025-08-22**, BTC **2025-10-06**. The alts topped first, by up to nine
months. Correlated daily returns did not mean synchronised cycle peaks.

**Correlation to equities.** This repo holds no equity series, so the following is `[web]`, not
first-party. **The headline finding is that the correlation is not a parameter — it is a fast-moving
state variable, and two readings four months apart in 2026 disagree in sign:**

| Reading | 30-day BTC–S&P 500 correlation | Source |
|---|---|---|
| Early March 2026 | **≈ +0.74** (year's high; some intraday windows ≈ +0.94) | `[web]` Phemex research blog — **tier 3, treat as indicative** |
| **2026-07-13** | **−0.17** | `[web]` newhedge.io BTC-vs-US-equities correlation tracker |
| 5-year context | 30-day correlation "often exceeding 70%" | `[web]` newhedge.io, same page |

**Do not hard-code a BTC-equity correlation into a risk model.** Anything between −0.2 and +0.9 has
printed inside the last twelve months. The stable claims are the *volatility ratio* — BTC realised
~53% against the S&P 500's ~13–15%, roughly **3.5–4×** `[corpus, verified 2026-06-21]` + `[local]` —
and the *conditional* pattern: BTC's correlation to equities spikes in risk-off (2022, early 2026)
and decays in quiet periods. The 2022 co-crash and the 2023–24 "decoupling" narrative are the same
asset in two regimes, not two different assets.

**Correlation to gold — and the "digital gold" thesis failing a live test.** The most useful dated
datapoint I could verify `[web, CoinDesk 2026-06-24]`:

- **Gold peaked ≈$5,600/oz in January and was down ~28%, below $4,000/oz, by 2026-06-24.**
- **BTC was below $62,000 — described as "a 50% correction from its October all-time high."** That
  independently confirms the October-2025 top and a drawdown of this order — but **compare like
  dates**: on 2026-06-24 this repo's Coinbase close was $60,983.13, **−51.7%** from the $126,296
  high `[local]`, agreeing with CoinDesk to within 2pp *on the same day*. The Snapshot's −49.4% is
  the **2026-08-04** reading; the drawdown has narrowed ~2pp since.
- BTC was **below its 200-week moving average of ≈$62,800** — a level it had historically held.
- Since the ratios bottomed in **February 2026**, BTC had *outperformed* gold by ~30% and silver by
  ~55%. **All three lagged US equities in 2026.**
- JPMorgan's framing: the "debasement trade" retreat has **accelerated** for bitcoin
  `[web, The Block, 2026]`.

> **A conflict I am flagging rather than resolving.** A lower-tier source claims gold *surged 51%*
> while BTC halved — the clean "digital gold split" story. **CoinDesk's dated reporting contradicts
> it**: gold had itself fallen ~28% from a January peak by late June 2026. The likely reconciliation
> is that the +51% describes gold's earlier run *into* the January high, not the 2026 path. **I have
> not resolved this, and no gold-vs-BTC correlation coefficient appears in this document.** What the
> better-sourced version supports is narrower and still damning for the thesis: **BTC did not act as
> a safe haven in this drawdown — it fell ~50% while equities outperformed everything.**

---

## Liquidity

**BTC is the most liquid crypto asset by a wide margin, and this is its main structural advantage
over SOL for strategy work.** $23.03B of reported 24h volume `[web, CoinGecko 2026-08-05T02:15Z]`
against SOL's $1.43B — roughly **16×** `[web, same call, via research/TOP_COINS.md]`. Depth,
not market cap, is what determines whether a backtested fill was real.

**Three cautions on the volume number itself:**

1. **Reported volume is not executable volume.** Bitwise (2019) estimated **95% of reported spot
   volume on unregulated exchanges was fake**, with 26 exchanges faking up to 70%; Chainalysis
   (2025) estimated ~$2.57B of suspected wash trading on DEX in 2024 alone.
   `[corpus, verified 2026-06-21]` The aggregate $23B figure includes venues you would never route to.
2. **Volume is fragmented across independent books with no consolidated tape.**
   `[corpus, verified 2026-06-21]` There is no single "the market" to size against.
3. **The volume column in this repo's `BTC_1d.csv` is one venue's pair.** Coinbase BTC-USD 30-day
   average is **5,964 BTC/day ≈ $0.38B/day — about 1.7% of the reported global $23.03B** `[local]`.
   **Do not use the CSV volume column as a proxy for *global* liquidity.** A volume-based signal
   (OBV, volume-confirmed breakouts, VWAP) computed on this file is computed on 1.7% of the market.
   *Within-venue* ratios built from it (weekend vs weekday, below) remain valid.

**What size moves it.** I could not verify a current, sourced order-book depth figure (Kaiko's 1%
market-depth series is the standard reference) to today's date, so I will not state one —
**unverified**. What can be said with the data at hand: over the full span BTC's realised vol is
**53.2% against SOL's 98.6% — SOL is 1.85× as volatile** `[local]` — while BTC trades ~16× the
notional. So **per unit of notional traded, BTC absorbs order flow far better than any other crypto
asset.** For strategy design the implication is directional and safe: **a size that is negligible in
BTC can be a material fraction of SOL's book**, and a strategy that only works at BTC's depth is not
transportable down the cap table.

> **A useful cross-check.** My full-span daily-bar ratio (σ_SOL/σ_BTC = **1.85**) lands within 3% of
> the corpus's independently-measured **1.91**, computed from *hourly* bars over a *different*
> 48-month window `[corpus, asset-specific-vs-universal-parameters §4.1, verified 2026-08-04]`. Two different samples at
> two different frequencies agreeing this closely is reasonable evidence that ~1.85–1.9× is a
> structural property of the pair rather than a sample artifact — which is what makes it usable as a
> scaling factor when porting risk parameters.

**Weekend liquidity is materially thinner — and here the CSV volume column *is* usable.** The 0.60
weekend/weekday vol ratio `[local]` is a volatility observation, but the same file measures
participation directly and agrees: Coinbase BTC-USD trades **7,051 BTC/day on Sat+Sun against 16,493
Mon–Fri — a ratio of 0.43** (0.42 over the last 365 days) `[local]`. This is a *within-venue* ratio,
holding the venue constant, so the caution above about the volume column as a *global* proxy does
not apply to it.

Combined with the absence of the ETF/institutional bid on Saturdays and Sundays, **weekend fills are
worse than a backtest with flat slippage assumes.** As a first pass, assume at least **2× weekday
slippage** on weekend fills and re-derive from your own fill data before sizing on it.
**Caveat:** CME's move to 24/7 on 2026-05-29 may compress this weekend thinness going forward — the
0.43 ratio is measured overwhelmingly on pre-change data.

**Confirmation latency is a liquidity constraint too.** 3–6 confirmations (~30–60 min) to move BTC
between venues `[corpus, verified 2026-06-21]` means inventory cannot be rebalanced intraday.
This is a hard limit on any multi-venue strategy.

---

## Known failure modes for traders

1. **Assuming the current regime is the regime.** The single largest error available. This asset
   returned +155.8% (2023), +120.8% (2024), −6.3% (2025), and −27.0% YTD (2026) `[local]`. A
   strategy fitted on 2023–24 is fitted on a regime that ended.
2. **Vol-targeting into a quiet drawdown.** See *Volatility and correlation* for today's readings:
   inverse-vol sizing levers up hardest exactly here. Low realised vol in a downtrend is not safety;
   it is the calm part of the stair-step.
3. **Weekend gaps — and a structural break that just invalidated the classic version.** 34% of
   weekends moved more than 2%, 7.5% more than 5%, max 11.82% (n=268) `[local]`, against weekend
   volume at 0.43× weekday `[local]`. **But CME went 24/7 on 2026-05-29** `[web]`, removing the
   closure that created the Monday-reopen gap. **Any weekend-gap or Monday-open rule fitted on
   pre-June-2026 data is fitted on a market structure that no longer exists** — and the
   post-change sample is only ~2 months long, which is not enough to refit on. This is the clearest
   live example in this document of regime change invalidating a backtested effect.
4. **Leverage cascades.** ~$19B liquidated across ~1.6M traders on 2025-10-10/11, of which ~$3.21B
   in the peak minute `[web]`; ~$1.9B in 4 hours with ~85%
   longs and BTC OI −35% (Nov 2025) `[corpus, verified 2026-06-21]`. These events do not respect
   stop-losses, and slippage in them is unbounded. A backtest with fixed slippage systematically
   under-prices exactly the days that matter.
5. **Mark price vs last price.** Liquidations trigger off the mark, not the chart. Planning a
   liquidation level from the visible candle is the single most common leveraged-trading error.
   `[corpus, verified 2026-06-21]`
6. **Funding as a signal rather than a cost.** Funding is coincident/lagging
   `[corpus, verified 2026-06-21]`; as a *cost* on notional it is real and modellable, and omitting
   it inflates any long-biased perp backtest.
7. **ETF-flow-driven regime dependence.** Since 2024, a large part of the marginal bid arrives only
   in US market hours through a handful of issuers with a concentrated custodian
   `[corpus, verified 2026-06-21]`. A strategy calibrated on that flow is calibrated on a channel
   that is only ~4 years old, is bidirectional, and did not exist for two-thirds of your sample.
8. **Halving-cycle extrapolation.** Explicitly an anti-pattern in the corpus
   `[corpus, verified 2026-06-21]`; the 2024 cycle already broke the pattern (~31% vs 300%+), and
   the asset is now below its post-halving mid-cycle levels `[local]`.
9. **Correlation collapse when you need diversification.** corr(BTC, SOL) is 0.646 in up months,
   0.755 in down months, and 0.893 in 2026 `[local]`. A "diversified" crypto book is one bet.
10. **Reported volume as a liquidity assumption.** See Liquidity. And specifically: **this repo's
    CSV volume column is 1.7% of global** `[local]`.
11. **Exchange counterparty risk.** A CEX balance is a claim on the exchange's balance sheet. FTX:
    ~$8B of customer assets misappropriated, $12.7B CFTC judgment, SBF sentenced to 25 years
    `[corpus, verified 2026-06-21]`. Proof-of-Reserves proves assets, **not liabilities** — it is not
    a solvency proof.
12. **Survivorship in the price series itself.** BTC is the asset that *won*. Every conclusion drawn
    from a BTC-only backtest inherits that selection, and generalising it to "crypto" is unjustified.

---

## For this backtester

**BTC data is held locally: `data/BTC_1d.csv`.** Know exactly what it is before using it.

| Property | Value |
|---|---|
| Venue / product | **Coinbase Exchange, BTC-USD** (`api.exchange.coinbase.com`, per `backtester/core/fetch.py`) |
| Interval / span | 1d, **2021-06-17 → 2026-08-04**, **1875 bars** |
| Columns | `timestamp, open, high, low, close, volume` (volume in **BTC**, Coinbase BTC-USD only) |
| Last close | $63,882.61 on 2026-08-04 |
| Sibling series | `ETH_1d.csv`, `SOL_1d.csv` (same 1875-bar span), `SOL_1h.csv` (8823 bars) |

**Four data caveats before you run anything:**

1. **It is Coinbase BTC-USD, not Binance BTCUSDT.** The corpus's own cross-asset BTC test was run on
   **BTCUSDT** `[corpus, verified 2026-08-04]`. Different venue, different quote asset, different fee tier, slightly
   different prints. Do not silently compare results across the two.
2. **Volume is ~1.7% of global** `[local]`. Volume-derived signals are on a thin slice.
3. **The final bar may be partial** — 2026-08-04 shows 4,078 BTC against a 30-day mean of 5,964
   `[local]`. Drop the last bar or the most recent return is not a full day.
4. **1875 daily bars ≈ 5.1 years is a small sample for a 4-year cycle asset.** It contains roughly
   one full cycle. That is one observation of the thing you are trying to model.

### What a strategy tested on BTC tells you about SOL

This is the question this file exists to answer, and the repo has already run the experiment.

**Rung 3 on the generalisation ladder.** Out-of-sample on one series is rung 1; a correlated second
asset is rung 3; an uncorrelated asset is rung 4 `[corpus, cross-asset-generalisation-testing.md, verified 2026-08-04]`.
BTC→SOL is **rung 3 — and rung 3 is asymmetric evidence**: a correlated second asset
**falsifies well and confirms poorly**. If a strategy *breaks* on BTC, that is strong evidence of
overfitting. If it *holds*, that is weak evidence of generality, because BTC and SOL over 2021–2026
are two views of **one macro path**, closer to "one and a bit" independent observations than two.
`[corpus, verified 2026-08-04]` My own measurement backs this: corr(BTC, SOL) = 0.709 full span, **0.893 in 2026**
`[local]`.

### The decisive measurement — this repo already ran 25 strategies on both assets

`research/results/cpcv_all25_btc_eth_1d.csv` and `cpcv_all25_sol_doge_zec_1d.csv` hold CPCV results for the
**same 25 strategies** on BTC, ETH and SOL. **The windows match exactly** — every one of the 25
strategies reports an identical (paths, usable-blocks) pair on both assets: 21/7 for 21 strategies,
15/6 for `hurst_switch`, `ou_reversion` and `vol_regime`, and 28/8 for `buy_and_hold`, which also
executes an identical 16 trades with an identical 0.678571 positive-path fraction on both. The
underlying CSVs are the same 1875 bars over the same span. This is a genuine matched-window rung-3
comparison, and it is the single most important table in this document.

| Measure across the 25 strategies | Result |
|---|---|
| Median Sharpe **positive** on BTC | **25 of 25** |
| Median Sharpe **positive** on SOL | **13 of 25** (ETH: 18 of 25) |
| **Median Sharpe flips sign** BTC ↔ SOL | **12 of 25 — 48%** |
| Cross-asset correlation of median Sharpe | **+0.263** |
| **Spearman rank correlation of the strategy ranking** | **+0.159** |
| BTC median Sharpe range | +0.035 to +1.657 |
| SOL median Sharpe range | −0.336 to +0.699 |

`[repo, computed from research/results/cpcv_all25_sol_doge_zec_1d.csv +
cpcv_all25_btc_eth_1d.csv, SOL column corrected 2026-08-05]`

> **Corrected 2026-08-05.** The SOL column previously came from
> `results/cpcv_all25_1d.csv`, which was a medium-horizon file with the long-horizon
> `sma_regime_200` row spliced in where medium's `sma_regime_100` belonged. That one row moved
> four figures in the table above — SOL positives 14→13, sign flips 11→12, Pearson +0.303→+0.263,
> Spearman **+0.245→+0.159** (exactly 0.1585, average-rank ties) — and `sma_regime`'s own SOL
> rank from 7 to 18. The defective file has been deleted; diagnosis in
> `research/CROSS-ASSET-TRANSFER.md`. **Every correction cuts the same way: the ranking
> transfers even less than this document previously claimed.**

**Every single strategy tested produced a positive median Sharpe on BTC.** That is the finding to
absorb first, and it is not good news — **it means a BTC pass has essentially no discriminating
power on this sample.** A validation test with a 100% pass rate does not separate good strategies
from bad ones; it tells you the asset had a positive drift at low volatility (BTC realised 53.2% vol
over the span vs SOL's 98.6% `[local]`), which flatters any long-biased rule on a Sharpe basis.
**On BTC, "it worked" is the base rate, not evidence.**

**The ranking barely transfers.** Spearman ρ = +0.159 across 25 strategies. Concretely:

| BTC top 5 | BTC Sharpe (rank) | → SOL Sharpe (rank) |
|---|---|---|
| `ou_reversion` | +1.657 (1) | +0.412 (**4**) |
| `sma_regime` | +0.835 (2) | **−0.066 (18)** |
| `garch_voltarget` | +0.834 (3) | **−0.028 (15)** |
| `voltarget` | +0.829 (4) | **−0.021 (14)** |
| `ichimoku` | +0.825 (5) | +0.023 (13) |

**Three of BTC's top five are below the median on SOL, and all three of those lose money there**
(`sma_regime`, `garch_voltarget`, `voltarget` — the SOL median is +0.023). BTC's **2nd**-best
strategy is SOL's **18th of 25**. Running it the other way is no kinder: SOL's #3
(`bb_breakout`, +0.481) ranks **22nd of 25** on BTC. Only `ou_reversion` is top-5 on both.

**And the benchmark inverts.** `buy_and_hold` ranks **11th of 25 on BTC** — 10 strategies beat it —
but **2nd of 25 on SOL**, where only one did. A researcher who calibrated "can I beat buy-and-hold?"
on BTC would carry a badly wrong prior to SOL.

**The honest one-line reading:** on this data, a strategy's BTC result predicts its SOL result about
as well as a coin flip predicts a rank. **Use BTC to falsify, never to confirm.**

### What travelled at the parameter level

Measured on matched 48-month OOS windows (2022-08 → 2026-07), identical protocol and identical
selection procedure on both assets `[corpus, empirical-backtest-findings-log §9.7, verified 2026-08-04]`:

| | SOL | BTC | Verdict |
|---|---|---|---|
| Modal grid level count | **10** (35/48 windows) | **10** (**48/48 windows**) | **Travelled — structural** |
| Modal trend sampling | **4-hourly** (26/48) | **4-hourly** (30/48) | **Travelled — structural** |
| Sleeve correlation | −0.107 | −0.131 | Travelled |
| Blend beats both sleeves | ✅ | ✅ | Travelled |
| Best blend weight | 0.65 | 0.75 | Near-agreement |
| **Trend standalone mean** | **+4.49%** | **−1.00%** | **DID NOT TRAVEL — sign flips** |

**Read the failure first, it is the informative half.** Trend-following's standalone edge was
**+4.49% on SOL and −1.00% on BTC**. Anyone concluding "trend-following works" from the SOL result
would have been wrong on BTC. That is not a scaling artifact and no normalisation fixes it — **a
strategy's profitability can be asset-specific even when its selected parameters agree.** The
settings transferred; the edge did not.

**And note the asymmetry that makes the finding useful:** the *pairing* survived on both assets
while one *component's* profitability did not. That is a direct argument for holding a book of
sleeves rather than a single sleeve.

**Tails are mostly — but not purely — a scale effect.** Over the same 48 months,
**σ_SOL/σ_BTC = 1.91** (mean monthly realised vol 25.03% vs 13.13%). Dividing SOL's tails by 1.91
leaves residuals **in opposite directions**: grid worst month is 5.01pp *worse* than scale predicts,
trend worst month 4.69pp *better* (raw ratios 2.39 and 1.55, straddling the 1.91 vol ratio)
`[corpus, asset-specific-vs-universal-parameters §4.1, verified 2026-08-04]`. **Run the normalisation, do not assert it.**

**The truncated-sample trap — a live example from this repo.** Run on only the **31 months** of BTC
available at the time, the sleeve correlation read **+0.198**; on the full **48 months** it read
**−0.131**. *The sign flipped.* The 31-month result was written up as a genuine cross-asset
divergence and it was an artifact of the missing 17 months `[corpus, verified 2026-08-04]`. **A truncated sample does not
merely add noise — it can produce a confident, coherent, wrong conclusion that survives sanity
checks.** **Where this does and does not bite here:** `BTC_1d.csv` and `SOL_1d.csv` are the same
1875 bars over the same 2021-06-17 → 2026-08-04 span, so the CPCV comparison above is already
matched — that is precisely why it is quotable. The trap returns the moment the spans diverge:
pulling BTC back to 2017 while SOL starts 2020, or comparing anything against `SOL_1h.csv`'s
8823-bar window. **Match the OOS windows exactly before comparing anything** — a comparison across
different spans is a comparison of assets *and* periods, and you cannot tell which produced the
difference.

**What to hold fixed and what to re-fit when porting BTC↔SOL** `[corpus, verified 2026-08-04]`:

| Element | Action |
|---|---|
| Signal rule / logic | **Hold fixed** — it is the hypothesis |
| Protocol (train window, selection rule, fill model, costs) | **Hold fixed** — else "out-of-sample" means two things |
| Parameters (periods, thresholds) | **Re-fit via the identical procedure** — never hand-pick |
| **Price-scale params (grid range, tick size)** | **Must be re-derived.** A $60–$83 SOL grid is meaningless on a **$64,000** asset — a ~870× price ratio |
| Costs | **Re-fit to the venue** |

**Practical summary — what a BTC result does and does not license you to say:**

- ✅ **Does tell you:** whether the strategy survives a **1.85× lower-volatility**, ~16× deeper,
  more institutionally-owned version of the same macro exposure. Whether its *selected parameters*
  land in the same place (the more informative signal than returns). Whether it **breaks** — which
  is the only strong result available at this rung.
- ✅ **Does tell you** that a BTC-only backtest is running on an asset that explains **50% of SOL's
  daily variance over the full span, and 80% in 2026** `[local]` — so a BTC pass is substantially a
  re-test on correlated data, not fresh evidence.
- ❌ **Does not tell you** that the strategy is profitable on SOL. Measured in this repo: **48% of
  25 strategies flip the sign of their median Sharpe** (12 of 25), and the trend sleeve's standalone
  edge flips +4.49% → −1.00%.
- ❌ **Does not tell you** where a strategy will *rank* on SOL. Spearman ρ = **+0.159**; three of
  BTC's top five are sub-median on SOL and all three lose money there.
- ❌ **Does not discriminate at all on this sample**, because **all 25 strategies pass on BTC**. A
  BTC-only screen would have rejected nothing.
- ❌ **Does not tell you** anything about SOL-specific microstructure: priority fees, transaction
  landing, Jito bundles, DEX/AMM slippage, JLP/perp funding mechanics, validator outages. BTC has no
  analogue for any of these.
- ❌ **Does not rule out era dependence.** Both series cover the same 2021–2026 macro path — rung 4
  and rung 5 are untested `[corpus, verified 2026-08-04]`.
- ❌ **Does not transfer price-scale parameters.** Re-derive, never port.

**Finally, two floors that must stay in view before any BTC result is believed.**

1. **The buy-and-hold floor is higher on BTC than on SOL.** `buy_and_hold` — zero parameters —
   returns a median Sharpe of **+0.619 on BTC** against **+0.534 on SOL**, and on BTC it beat 14 of
   the 24 alternatives `[repo, cpcv results, 2026-08-04]`. A BTC strategy must clear a *higher* bar
   to be worth its complexity, not a lower one.
2. **Selection by in-sample rank is worse than random on this dataset.** PBO for singles is
   **0.700** against a pure-noise line of 0.500, and Spearman ρ(in-sample, out-of-sample Sharpe) is
   **−0.419** at the medium horizon `[repo, research/TOP5-RECOMMENDATION.md, AS OF 2026-08-04]`.
   Combine that with the +0.159 cross-asset rank correlation above and the conclusion is blunt:
   **neither in-sample rank nor BTC rank is a trustworthy way to choose a SOL strategy.**

---

## Sources

**First-party `[local]` — computed for this document, reproducible:**
- `/Users/mitch.hudson/dev/solmargintrader/data/BTC_1d.csv` (also `ETH_1d.csv`, `SOL_1d.csv`) —
  Coinbase Exchange BTC-USD/ETH-USD/SOL-USD daily, 2021-06-17 → 2026-08-04, 1875 bars each.
  Fetched by `backtester/core/fetch.py` (`COINBASE_BASE = "https://api.exchange.coinbase.com"`).
- Method: daily log returns; annualisation ×√365; correlations and betas on timestamp-aligned bars;
  drawdowns close-to-close unless stated; weekend gap = Friday close → Sunday close.

**Repo research artifacts:**
- `research/TOP_COINS.md` — the snapshot table. **AS OF 2026-08-05T02:15:22Z**, CoinGecko
  `/coins/markets`. Regenerate: `curl -s 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=15&page=1&sparkline=false'`
- `research/TOP5-RECOMMENDATION.md` — PBO 0.700, ρ = −0.419, `buy_and_hold` median Sharpe +0.534.
  **AS OF 2026-08-04.**
- `research/results/cpcv_all25_btc_eth_1d.csv` (BTC + ETH) and
  `research/results/cpcv_all25_sol_doge_zec_1d.csv` (SOL, DOGE, ZEC) — 25 strategies × CPCV on
  matched windows: 21 paths / 7 usable blocks for 21 strategies, 15/6 for `hurst_switch`,
  `ou_reversion` and `vol_regime`, 28/8 for `buy_and_hold`. The 48% sign-flip rate,
  ρ_Spearman = +0.159, the 25-of-25-positive BTC result, and the rank tables are computed from
  these two files. **SOL column regenerated 2026-08-05**, replacing the deleted
  `cpcv_all25_1d.csv`. Reproduce with
  `python3 research/cross_asset_cpcv.py --assets SOL,DOGE,ZEC` and join on `strategy`.

**Local skill corpus — original stamps carried through, NOT restamped to today:**
- `~/.claude/skills/blockchain/references/bitcoin-protocol-expert.md` — **verified-as-of 2026-06-16.**
  UTXO model, Script/addresses, PoW header, 2016-block retarget with 4× clamp, halving schedule,
  ~20,999,999.9769 BTC asymptote, SegWit/Taproot.
- `~/.claude/skills/blockchain/references/blockchain-economics.md` — **verified-as-of 2026-06-16.**
  Security budget, issuance-vs-valuation anti-patterns, "treating tokenomics as price prediction."
- `~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md` —
  **verified-as-of 2026-06-21.** Perp/funding/mark-price mechanics, exchange table, ETF facts
  (2024-01-10 approval; IBIT ~757,130 BTC **as of 2026-02-23**; 2024 inflows ~$48.7B, 2025 ~$46.3B),
  liquidation cascades (Oct 2025 ~$3.21B/60s; Nov 2025 ~$1.9B/4h), ATH ~$126,000 Oct 2025,
  BTC vol ~54% vs S&P 500 ~13–15%, wash-trading estimates, FTX, CME ±10% limits, halving-return
  anti-pattern.
- `~/.claude/skills/trading-and-investing/references/asset-classes-and-instruments.md` and
  `market-participants-and-structure.md` — **as of 2026** (foundation refs, 2026-06-16).
- `~/.claude/skills/trading-and-investing/references/cross-asset-generalisation-testing.md` —
  **2026-08-04.** The generalisation ladder, rung-3 BTC/SOL table, the 31-vs-48-month truncated-
  sample correction.
- `~/.claude/skills/trading-and-investing/references/asset-specific-vs-universal-parameters.md`
  §4/§4.1 — **verified-as-of 2026-08-04.** σ_SOL/σ_BTC = 1.91 and the opposite-signed tail residuals.
- `~/.claude/skills/trading-and-investing/references/empirical-backtest-findings-log.md` §9.7 —
  **verified-as-of 2026-08-04.** The underlying 48-month OOS measurements (venue: Binance).

**Web sources verified 2026-08-04/05 for this document:**

*Protocol & supply*
- Halving countdown / block height — CoinWarz `coinwarz.com/bitcoin-halving`, NiceHash, Bitbo
  `bitbo.io/halving/`, BitRef. Height **961,040**, **88,960** blocks to go, est. **2028-04-18**
  (range March–May 2028).

*Market structure*
- **CME 24/7 launch, 2026-05-29** — CME Group press release,
  `cmegroup.com/media-room/press-releases/2026/6/01/...`; Markets Media.
- **SEC in-kind creation/redemption approval, 2025-07-29** — CoinDesk; Morrison Foerster; Dechert;
  The Block.
- **IBIT** — BlackRock product page `blackrock.com/us/individual/products/333011`: net assets
  $47,479,779,868 (2026-08-04), 738,862.4242 BTC (2026-08-03), YTD NAV return −26.95%.
- **ETF flows** — Farside `farside.co.uk/btc/` (cumulative $51,589M, 2026-08-04); CoinGlass
  `coinglass.com/etf/bitcoin` (+$51.98B / 644.14K BTC); CoinDesk 2026-06-29 (record June outflow);
  KuCoin (H1 2026 −$5.4B); CoinMarketCap (April +$1.97B).
- **Oct 10–11 2025 liquidation, ~$19B / 1.6M traders** — CoinDesk Research market spotlight;
  Forbes 2025-10-13; CoinGecko.
- **Feb 5 2026 crash** — Forbes 2026-02-05; VanEck (−6.05σ, −2.88σ vs 200dma); Coin Metrics SOTN
  #352; Bitcoin Magazine.
- **Cycle low $57,717 (2026-07-02)** — CryptoQuant 2026-07-08; IG.
- **Galaxy Research** — ATH prints and the 2026-06-12 cycle-bottom analysis (4 of 13 indicators,
  base case $40–46K).
- **CME basis/OI** — KuCoin (OI $8.41B, 14-month low, 2026-04-11).
- **Perp funding** — Phemex (46 consecutive negative days as of 2026-04-15).
- **Exchange share** — CryptoRank Q2 2026; CoinGlass Q1 2026.
- **Strategy/MSTR** — bitcointreasuries.net (843,775 BTC, cost ≈$75,476, 2026-07-06 8-K, mNAV 0.68×
  2026-08-03); CoinDesk 2026-07-24 (sector-wide DAT unwind).

*Volatility*
- **Deribit DVOL** — `deribit.com/api/v2/public/get_volatility_index_data?currency=BTC&resolution=1D`,
  1,961 daily rows from inception 2021-03-24, retrieved 2026-08-05 ~03:14 UTC. **Primary source.**
- **Coin Metrics CMBI** — `indexes.coinmetrics.io/cmbibtc`, realised-vol term structure, 2026-08-05.
- VanEck (30d RV 30.4%, 2026-07-14); Block Scholes; Ferrante Capital Advisers 2026-04-21 (the
  dissent); Kang & Lee, "Institutionalization without integration" (placebo break in 2023).
- BTC vs US equities 30-day rolling correlation — newhedge.io `newhedge.io/bitcoin/us-equities-correlation`.
  **−0.17 as of 2026-07-13**; 5-year context "often exceeding 70%."
- BTC–S&P 500 ≈**+0.74** early March 2026 (intraday ≈0.94) — Phemex blog
  `phemex.com/blogs/bitcoin-correlation-with-sp500`. **Tier 3 — indicative only.**
- Gold/BTC divergence — CoinDesk, **2026-06-24**, `coindesk.com/markets/2026/06/24/gold-silver-and-bitcoin-tumble-as-debasement-trade-unwinds`.
  Gold −28% from a ≈$5,600 January peak to below $4,000/oz; BTC below $62,000 = "a 50% correction
  from its October all-time high"; BTC below its 200-week MA ≈$62,800; BTC +30% vs gold and +55% vs
  silver since the ratios bottomed in Feb 2026; all three lagged US equities in 2026.
- JPMorgan "debasement trade retreat has accelerated for bitcoin" — The Block
  `theblock.co/post/404471/jpmorgan-debasement-trade-retreat-bitcoin-gold`.
- Grayscale Research, "January 2026: Bitcoin and the Debasement Trade" —
  `research.grayscale.com/market-commentary/january-2026-bitcoin-and-the-debasement-trade`.

**Primary external anchors (named in the corpus, not re-fetched for this document):**
CoinGecko · Coinglass (funding, OI, liquidations) · Kaiko (depth, spreads) · CoinMetrics/Glassnode
(realised vol, on-chain) · Farside/SoSoValue (ETF flows) · CME Group (contract specs, limits) ·
SEC ETP approval orders (2024-01-10) · Bitwise 2019 and Chainalysis 2025 (wash trading).

### Could not verify — treat as open

These were sought and are **not** stated as fact anywhere above:

1. **A stable BTC-vs-equities correlation.** Two 2026 readings disagree in sign (+0.74 in March,
   −0.17 on 2026-07-13) and one of them is tier-3. The *instability* is the verified finding; **no
   single coefficient here should be treated as current.** Re-pull before using one. **The 2022 peak
   BTC-equity correlation — window length and value — is also unverified.**
2. **A BTC-vs-gold correlation coefficient.** Gold's 2026 *path* is sourced (CoinDesk, 2026-06-24);
   the correlation itself is not, and two sources conflict on gold's direction (see the flag in
   Volatility and correlation). **Unresolved.**
3. **Order-book depth in dollars** (Kaiko-style 1% market depth), current bid-ask spreads, and a
   Coinbase-vs-Binance spread comparison — and therefore any concrete "$X moves the market by Y bps"
   claim. **Kaiko's 2026 depth data sits behind a paid seat.** Direction (thinner) is supported;
   magnitude is not, and no depth number is asserted above.
4. **Current CME basis / term structure and CME open interest.** Only **2026-04** readings exist
   above (~5% basis, $8.41B OI) and they are explicitly labelled ~4 months stale.
5. **Current perp funding level and total perp open interest.** Only the **2026-04** regime reading
   (negative, 46-day streak). CoinGlass's OI page exceeded parse limits.
6. **Operational in-kind usage.** The **approval** date (2025-07-29) is solid, but whether APs
   actually create/redeem in-kind day-to-day in 2026 is unconfirmed — so the corpus's "cash-based"
   note may still be correct **as a description of practice**. Do not mark the corpus stale on the
   approval date alone.
7. **Total BTC held by US spot ETFs (~1.18–1.20M)** is `[web-derived]` from AUM ÷ price, not read
   from a single authoritative page.
8. **Exact 2026 YTD ETF flow.** Jul 1–16 daily rows were not captured, so the −$4.5B to −$5.0B
   figure is a **bounded estimate**; the monthly rows and the H1 −$5.4B are directly sourced.
9. **Fee share of miner revenue, current hashrate and hashprice**, and whether miners are
   capitulating at ~$64K. The miner-margin argument in "Supply and issuance" is a **mechanism**, not
   a measured condition. One dated datapoint suggests stress: network difficulty printed its
   **second-ever negative year-on-year reading on 2026-08-01** as miners pivoted to AI — the first
   since China's mining ban `[web]` — but I did not verify hashrate or hashprice levels.
10. **Post-May-2026 protocol news** (Bitcoin Core releases, the OP_RETURN policy dispute, covenant
    proposals such as CTV/CSFS). Nothing after the corpus's 2026-06-16 stamp is reflected.
11. **2026 exchange failures or insolvencies** — not searched. Unknown, not "none."
12. **Whether CME gaps "fill."** Widely-repeated folk claim, not verified, not asserted. Moot going
    forward given CME's 2026-05-29 move to 24/7.
13. **A 30-day realised-vol print within a week of today.** None exists in published research; the
    freshest is 2026-07-14. Today's 29.4% is `[local]`.
14. **The 0.8% Coinbase-vs-composite price gap is not decomposed** into venue basis vs the ~2h
    timestamp offset.
15. **The primary sources behind the vol-decline dispute.** Kang & Lee, "Institutionalization
    without integration" (no year, venue or link captured) and the Block Scholes report are both
    cited **second-hand via a research summary**. They are the entire evidence for "the ETF-caused
    framing is not well-evidenced," so treat that specific conclusion as **single-source and
    unverified at the primary level.** (Cross-referenced as "open item 15" in Volatility and
    correlation.)

**Two source-data anomalies worth chasing, flagged not resolved:**

- In `cpcv_all25_btc_eth_1d.csv`, the **BTC rows for `bb_reversion` and `zscore` are byte-identical
  across all seven result columns**. On ETH and SOL they differ. If the BTC run aliased two
  strategies, effective n on BTC is **24**, and "25 of 25 positive" needs a footnote. **Check
  upstream before quoting that statistic in isolation.**
- The reported Spearman ρ of **+0.159** is already the average-rank-tie figure (0.1585 exactly).
  The superseded +0.245/+0.242 pair came from the defective `cpcv_all25_1d.csv` SOL column, not
  from a tie-handling choice.

**Why the remaining items stayed open:** the session's web-search budget (200 calls) was exhausted
and Kaiko/Farside partially blocked automated access. Everything above that *is* sourced was
verified on 2026-08-04/05; everything else is marked open rather than filled from recall.

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
