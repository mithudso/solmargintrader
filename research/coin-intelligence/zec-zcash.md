---
name: zec-zcash
description: Trader-facing reference for Zcash (ZEC) — $513/coin on a ~16.8M supply and an $8.6B cap, optional-privacy design with transparent and shielded pools, a 38x move dated to a 2025-10-01 breakout, and real venue-availability risk (Coinbase lists ZEC-USD but has delisted ZEC-BTC and ZEC-USDC).
---

# Zcash (ZEC)

> Educational reference only. Nothing here is investment advice. The regulatory material below describes the exchange-listing landscape as observed; it takes no position for or against privacy technology or its regulation.

## Snapshot (AS OF 2026-08-04)

| Metric | Value | Source |
|---|---|---|
| Price | ~$513.22 | CoinGecko, 2026-08-04[^zec-snapshot] |
| Market cap | ~$8.6B | CoinGecko, 2026-08-04[^zec-snapshot] |
| 24h volume | ~$0.20B | CoinGecko, 2026-08-04[^zec-snapshot] |
| Turnover (vol ÷ mcap) | **2.30%** | derived from the row above[^zec-snapshot] |
| Implied circulating supply (mcap ÷ price) | ~16.76M ZEC | derived[^zec-snapshot] |
| Reported circulating supply | ~16,804,278 ZEC (**80.0% of the 21M cap**) | secondary, Aug 2026[^zec-supply] |
| Max supply | **21,000,000 ZEC** (Bitcoin-derived) | protocol[^zec-supply] |
| Fully diluted value at snapshot price | ~$10.78B (FDV/mcap ≈ 1.25x) | derived[^zec-snapshot] |
| Annualized vol, trailing 365d | **151.6%** | derived, Coinbase ZEC-USD daily closes to 2026-08-05[^zec-vol] |
| Correlation to BTC, trailing 365d | **+0.43** (but +0.72 trailing 30d) | derived, same series[^zec-vol] |
| Coinbase listing | **ZEC-USD `online`; ZEC-BTC and ZEC-USDC `delisted`** | verified via Coinbase API, 2026-08-04[^zec-coinbase] |

Note the two volatility/correlation rows are computed on a series ending **2026-08-05**, one day after the price snapshot date in this section's heading.

**These figures decay,** and for ZEC they decay faster than for most assets — this is a 150%-annualized-volatility instrument that has moved more than 5x and then fallen more than 70% inside the window studied below. A price snapshot has a short shelf life here. The supply figures are the most durable items in the table; the volatility and correlation figures are strongly regime-dependent and should be re-derived, not carried forward.

**Why the price-per-coin is high and what it does and does not mean.** At $513/coin with an $8.6B cap, ZEC has by far the smallest coin count in this set — ~16.8M against DOGE's ~155B, a factor of ~9,250. **Price per coin carries no information about valuation**; it is purely an artifact of the supply schedule Zcash inherited from Bitcoin's design (21M cap, halvings). What the small supply *does* mean is mechanically real: because ~80% of the eventual supply is already issued, **FDV is only ~1.25x market cap**, so there is limited future-issuance overhang relative to assets with large unissued or unvested allocations.

Cross-check: implied supply from the snapshot (16.757M) agrees with the reported 16.804M to within ~0.3%.

## What it is, mechanically

Zcash is a **Bitcoin-derived UTXO chain with optional zero-knowledge privacy.** It forked Bitcoin's core design (21M cap, halvings, proof-of-work) and added zk-SNARK-based shielded transactions.

**The defining design decision is that privacy is optional, not mandatory.** ZEC exists in two pools:

- **Transparent pool (t-addresses).** Behaves exactly like Bitcoin. Balances and transaction graph are fully public and analysable with ordinary block-explorer tooling.
- **Shielded pool (z-addresses).** Amounts, sender, and recipient are cryptographically hidden. Validity is proven with zk-SNARKs without revealing the contents. Successive protocol versions (Sprout → Sapling → Orchard) improved performance and the trust model.

Funds move between the pools, and the movements themselves are visible even when the shielded balances are not.

**This optionality is the whole trader-relevant story, and it cuts in two directions:**

1. **It is why ZEC survives on regulated venues where fully-private assets do not.** An exchange can support ZEC using only transparent addresses, preserving its ability to run the chain-analysis and Travel Rule compliance its regulators expect. Monero, which has no transparent mode, offers no such option. This distinction shows up directly in the verified listing data below.
2. **It makes the float partially unobservable.** Roughly **30% of ZEC supply now sits in the shielded pool (May 2026), up from ~8% in early 2024, ~18% by October 2025, and ~23% by November 2025.**[^zec-shielded] For the shielded portion, **standard on-chain holder analysis is not merely difficult, it is cryptographically impossible.** Any concentration, exchange-flow, or holder-cohort metric for ZEC is computed on a shrinking transparent subset and is silently unrepresentative of the whole.

That second point deserves emphasis because it is unique among the three assets in this set: **for ZEC, on-chain analytics degrade as adoption of the asset's core feature increases.** A strategy conditioned on ZEC exchange-flow or whale-wallet signals is conditioned on a sample that is both shrinking and non-randomly selected.

## Supply and issuance

- **21,000,000 ZEC hard cap**, inherited from Bitcoin's design.[^zec-supply]
- **~16.80M issued (80.0%) as of August 2026**; ~4.2M remain to be mined.[^zec-supply]
- **Halving schedule.** The **second halving occurred in November 2024** at block height **~2,726,400**, cutting the block reward from **3.125 ZEC to 1.5625 ZEC** and taking annual inflation from roughly 4% to roughly 2%.[^zec-supply] The **next halving is projected for late 2028** (reward → 0.78125 ZEC).
  - *Height caveat:* **~1,046,400 is the* first *halving (Canopy, November 2020)** and is widely misattributed to the second in secondary coverage. The post-Blossom halving interval is 1,680,000 blocks at a 75-second target, so 1,046,400 + 1,680,000 = **2,726,400** — consistent both with the November 2024 date and with Zcash's live block height of **3,436,819 observed 2026-08-04**. The height is derived and cross-checked here, not taken from a secondary source.[^zec-supply]
- **NU6 network upgrade (November 2024)** restructured the development-fund allocation of the block subsidy: **80% to miners, 8% to Zcash Community Grants, and 12% to an in-protocol "lockbox"** — a deferred pool whose disbursement is subject to later governance.[^zec-supply]

Two things follow for a trader. First, the **November 2024 halving preceded the major price move by roughly 11 months** — it is not a sufficient explanation for the October 2025 breakout, and treating it as the cause would be a post-hoc error. Second, the **lockbox is a governance-dependent supply overhang**: it is accruing protocol-controlled ZEC whose eventual release is a policy decision, not a fixed schedule.

*Unverified:* the current accumulated size of the NU6 lockbox and any adopted disbursement policy. This was not confirmed and should be checked before it is used in any supply model.

## Concentration, float and turnover

**Turnover 2.30%**[^turnover-std] ($0.199B against $8.6B) — 5th of the ten coins in this directory, between TRX (1.45%) and HYPE (2.52%), and well below DOGE's 3.44%.[^zec-vol] But the absolute figure is what matters here: **$200M of daily volume is small for an $8.6B asset, and it is spread across relatively few venues** (see below). Depth, not turnover ratio, is ZEC's liquidity constraint.

**Float observability is the distinctive issue**, as described above: ~30% of supply is shielded and cryptographically un-analysable.[^zec-shielded] There is no way to construct a reliable holder-concentration figure for ZEC, and **any published ZEC concentration statistic is necessarily computed on the transparent subset only.** This reference does not quote one, because a transparent-pool-only concentration number is not a concentration number for the asset.

Two second-order effects worth understanding:

- **Shielding withdraws coins from observable circulation.** Growth from 8% → 30% of supply shielded over roughly two years coincided with the price move. Whether shielding is a *cause* (a genuine supply sink) or an *effect* (holders who bought the privacy thesis also use the privacy feature) is **not established**, and the causal direction is easy to assert and hard to demonstrate. Treat "shielded pool growth is a supply squeeze" as an unverified narrative rather than a mechanism.
- **FDV/mcap ≈ 1.25x** means limited dilution ahead relative to most assets, but the NU6 lockbox is a partial offset.

## What drives the price

1. **The privacy narrative as a sector trade.** ZEC trades as the liquid, regulated-venue-accessible expression of financial-privacy demand. When that theme is bid, ZEC is the instrument most institutions and US retail traders can actually buy — Monero largely is not (verified below). ZEC captures flow that the theme generates *because* of its listing survivability.
2. **Venue access events.** Listings, delistings, and pair removals move ZEC more than they move broadly-listed assets, because the accessible-venue set is small. This is a two-sided risk, not merely a downside one.
3. **Institutional access developments.** Grayscale filed to convert its Zcash Trust (ZCSH) into a spot ETF; Cypherpunk Technologies has been reported accumulating supply; Robinhood listing and THORChain integration have been cited as catalysts.[^zec-catalysts] **ETF conversion status is UNVERIFIED** — a filing is not an approval and should not be modelled as one.
4. **Regulatory clarity.** The SEC is **reported** to have closed its investigation into the Zcash Foundation on **2026-01-15** without recommending enforcement, reportedly producing a >3% same-day move.[^zec-catalysts] **Both the closure and the price reaction are secondary-sourced and UNVERIFIED here** — unlike the price and listing data in this file, neither was confirmed against a primary record.
5. **Shielded-pool growth as a sentiment proxy** — widely watched, causally ambiguous (see above).
6. **Bitcoin beta, regime-dependently.** Correlation to BTC ranges +0.41 to +0.72 depending on window. ZEC decoupled hard during its idiosyncratic run and has recoupled since.

### The 2025–26 move, dated from primary data

Dated directly from **Coinbase ZEC-USD daily candles** rather than from secondary reporting. All figures are daily closes unless noted.[^zec-move]

| Phase | Dates | Price action |
|---|---|---|
| Period low | **2024-07-05** | close **$18.32** |
| Long base | Jan–Aug 2025 | month-end closes range **$36.06 – $50.15**; no trend |
| Ramp begins | Sep 2025 | Aug 31 close $40.76 → **Sep 30 close $74.13** (+82% in the month) |
| **Breakout** | **2025-10-01** | close **$74.13 → $120.80 (+63% in one day)**, intraday high **$153.00**, volume **404,610 ZEC vs 78,696 the prior day (≈5.1x)** |
| Vertical phase | Oct 2025 | Oct 31 close **$405.48** — **~5.5x from the Sep-30 base of $74.13** (and ~3.4x measured from the Oct-1 close of $120.80) |
| **Intraday all-time high** | **2025-11-07** | high **$744.13** (close $644.17), volume 789,047 ZEC — the highest-volume day of the move |
| **Peak daily close** | **2025-11-16** | close **$698.99** |
| Unwind | Nov 2025 → Mar 2026 | max drawdown **−71.8%**, trough close **$197.30 on 2026-03-07** (197.30 ÷ 698.99 − 1); Feb-2026 month-end close $220.53 |
| Recovery | Apr–Aug 2026 | May 2026 month-end **$568.51**; Jun $398.93; Jul $457.55; **2026-08-05 close $513.66** |

**Summary of magnitude:** from the 2024-07-05 low of $18.32 to the 2025-11-16 peak close of $698.99 is **38.2x**. As of 2026-08-05, ZEC sits at **$513.66 — 28.0x off that low but still −26.5% below the peak close.**

The important structural observations for a trader:

- **The move had a clean, single-day ignition point (2025-10-01) accompanied by a ~5x volume expansion.** It was not a slow grind — it was a regime break, and the volume confirmed it on the day.
- **September 2025 was the tell.** The +82% ramp from $40.76 to $74.13 preceded the breakout and broke the eight-month January–August 2025 base.
- **The retrace was brutal and fast:** −71.8% in roughly four months from the November peak.
- **Secondary reporting on this move is imprecise.** Sources variously describe "$50 in early 2025 to nearly $700 by November 2025" and a "$748 record high."[^zec-catalysts] The primary Coinbase series gives $744.13 as the intraday high on 2025-11-07 and $698.99 as the peak daily close on 2025-11-16. Small discrepancies across venues are expected; the dated table above is preferred over the secondary figures.

## Market structure and liquidity

**This is where ZEC's genuine, structural risk lives.**

**Verified listing status (checked live 2026-08-04, primary APIs).**[^zec-coinbase][^zec-venues]

| Venue | Pair | Status | 24h notional (verified) |
|---|---|---|---|
| **Coinbase Exchange** | **ZEC-USD** | **`online`, `trading_disabled: false`** | **~$27.89M** |
| **Coinbase Exchange** | **ZEC-BTC** | **`delisted`, `trading_disabled: true`** | — |
| **Coinbase Exchange** | **ZEC-USDC** | **`delisted`, `trading_disabled: true`** | — |
| OKX | ZEC-USDT | online | ~$9.27M |
| Kraken | ZECUSD (`XZECZUSD`) | online | ~$6.50M |
| Binance | ZECUSDT | could not verify — geo-restricted from this environment | unverified |
| Bybit | ZECUSDT | could not verify — geo-blocked | unverified |

**The Coinbase pair-level delisting is directly observable and is the single most instructive data point in this file.** Coinbase has not delisted ZEC — but it *has* delisted two of its three ZEC pairs, retaining only the USD pair. That is what listing pressure looks like in practice on a regulated venue: not a binary removal, but **progressive narrowing of the tradable pair set**. A trader watching only "is ZEC listed?" would miss it entirely.

**The privacy-coin availability spectrum, verified on Coinbase (2026-08-04):**

| Asset | Coinbase status |
|---|---|
| **Monero (XMR)** | **zero products — entirely absent** from all 832 Coinbase products |
| **Zcash (ZEC)** | ZEC-USD online; **ZEC-BTC and ZEC-USDC delisted** |
| **Dash (DASH)** | DASH-USD and DASH-BTC both online |

This is the landscape stated neutrally: **exchanges have responded to privacy assets differently according to how those assets interact with compliance obligations, not uniformly.** Zcash's optional-transparency design lets a venue support it under a compliance regime that Monero's mandatory privacy cannot accommodate. Dash, whose privacy features are optional and comparatively weak, faces the least pressure.

**The broader delisting landscape (secondary sources, described without advocacy):** reporting indicates that in 2024 Binance, Kraken, OKX and others removed various privacy-asset pairs; OKX removed XMR/ZEC/DASH pairs on 2024-01-05; Binance delisted XMR globally on 2024-02-20; Kraken withdrew XMR in Ireland and Belgium in June 2024 and across the European Economic Area on 2024-10-31. Aggregate counts of 73 exchanges dropping privacy coins during 2025 have been reported.[^zec-delisting] The stated driver in each case is compliance with AML obligations, the FATF Travel Rule, and the EU's MiCA framework — **not a prohibition on holding or trading the assets, which remains legal in the US, EU, and most jurisdictions.**[^zec-delisting]

**One correction from primary verification:** despite reports that OKX removed ZEC pairs in January 2024, **OKX's ZEC-USDT market was live and quoting on 2026-08-04** (~$9.27M 24h notional, verified by direct API call). Either the removal was partial or it was subsequently reversed. **Prefer the live API check over the historical reporting.** This is a general lesson for this asset class: delisting coverage ages badly in both directions.

**Venue-concentration risk, quantified.** Coinbase's ZEC-USD pair alone is **~$27.9M of ZEC's ~$200M reported global 24h volume — roughly 14%.** By comparison, Coinbase's DOGE-USD pair is only ~1.9% of DOGE's global volume. **ZEC's liquidity is far more concentrated in a small number of venues, and Coinbase is one of the largest.** The three venues verifiable from this environment (Coinbase, OKX, Kraken) together account for ~$43.7M, or ~22% of global volume.

The practical consequence: **for ZEC, a single venue's listing decision is a material liquidity event, in a way that is simply not true for DOGE.** This is the concrete, quantified form of "delisting risk" — not an abstract regulatory worry but a measurable concentration of the book.

## Volatility and correlation

Derived from **Coinbase ZEC-USD and BTC-USD daily closes**, 948 daily bars, 2024-01-01 → 2026-08-05.[^zec-vol]

| Window | ZEC ann. vol | BTC ann. vol | corr(BTC) | beta(BTC) |
|---|---|---|---|---|
| Full (2024-01-02 → 2026-08-05) | **118.8%** | 47.5% | +0.41 | +1.04 |
| Trailing 365d | **151.6%** | 43.4% | +0.43 | +1.49 |
| Trailing 90d | **132.9%** | 34.6% | +0.48 | +1.82 |
| Trailing 30d | **85.1%** | 29.0% | **+0.72** | **+2.11** |

**ZEC is the most volatile asset in this set by a wide margin** — 151.6% annualized over the trailing year, roughly **3.5x Bitcoin's 43.4%**, and comfortably above DOGE's 73.9%.

**The correlation structure is the interesting part, and it is the mirror image of DOGE's.** Where DOGE's correlation to BTC is pinned at ~+0.77 in every window tested, ZEC's ranges from **+0.41 to +0.72**, rising monotonically as the window shortens. Read together with the price history, the interpretation is:

- During the idiosyncratic run (late 2025), ZEC **decoupled** — it was trading its own narrative, and full-window correlation of +0.41 reflects that.
- Over the trailing 30 days, correlation has risen to **+0.72** and beta to **+2.11** — ZEC has **recoupled to BTC and is now behaving as a very high-beta crypto instrument** rather than an independent one.

**This is a regime change, and it matters for anyone using ZEC as a diversifier.** ZEC's low full-window correlation is a historical average across two different regimes, not a stable property. Sizing a position on the +0.41 full-window figure while the asset is actually trading at +0.72 correlation and 2.11 beta will materially understate portfolio risk. Note also that beta rising while correlation rises *and* ZEC's own volatility falls (151.6% → 85.1%) means the recoupling is genuine, not an artifact of a volatility spike.

**Cross-asset:** ZEC–DOGE +0.39 to +0.48; ZEC–TRX +0.14 (over the 720-return window the two series share) rising to +0.47 (30d).[^zec-vol]

**Drawdown:** max **−71.8% on 2026-03-07** from the November 2025 peak. Current level is **−26.5% below the peak daily close.** For calibration: a −71.8% drawdown requires a +254% recovery to make new highs.

## Known failure modes for traders

1. **Sizing on the full-window correlation.** ZEC's +0.41 long-run correlation to BTC is an average of a decoupled regime and a coupled one. At the time of writing it is trading at +0.72 with beta +2.11. Using the long-run number is the most likely way to be quietly over-exposed.
2. **Treating venue availability as static.** Coinbase has already delisted two of three ZEC pairs. Delisting risk for this asset is not hypothetical, it is partially realized, and it is progressive rather than binary. Monitor the pair set, not just the asset.
3. **Underestimating venue concentration.** ~14% of global ZEC volume sits on a single Coinbase pair. A listing change at one venue is a liquidity event.
4. **Using on-chain analytics.** ~30% of supply is shielded and growing. Exchange-flow, whale-wallet, and holder-concentration signals are computed on a shrinking, non-random transparent subset. This failure mode is specific to ZEC among the three assets here and is easy to miss because the tooling returns a number regardless.
5. **Extrapolating the 38x.** The move had a specific catalyst structure and a −71.8% unwind. Momentum and trend models fitted across the October 2025 breakout will have absorbed an extreme, likely non-repeating regime; any walk-forward study spanning it should check whether results survive its exclusion.
6. **Assuming volatility is stable.** Trailing-30d vol (85.1%) is roughly half the trailing-365d figure (151.6%). Volatility-targeted position sizing will swing violently depending on lookback choice.
7. **Confusing price-per-coin with valuation.** $513/coin says nothing about whether ZEC is cheap or expensive. It is a supply-schedule artifact.
8. **Modelling an ETF as approved.** The Grayscale conversion is a filing. Its status is unverified here.

## For this backtester

**ZEC is now held in the local cache.** `~/dev/solmargintrader/data/ZEC_1d.csv` was fetched 2026-08-05 — 2,043 daily bars, 2021-01-01 to 2026-08-05, 0 non-1d steps, and it has since been run through the full 25-strategy CPCV sweep (24 of 25 configurations positive, the highest of the five assets tested). DOGE was fetched the same day. The recommendation below to persist ZEC history promptly has therefore been acted on.[^zec-local]

**Coinbase lists ZEC, so this project's fetcher can retrieve it — but only via the USD pair.** Verified against the exact API `backtester/core/fetch.py` uses:[^zec-coinbase]

- `GET /products/ZEC-USD` → `{"id":"ZEC-USD", ..., "status":"online", "trading_disabled":false}`
- `GET /products/ZEC-USD/candles?granularity=86400` → returns data. Sample row for 2026-08-04: `[1785801600, 477.48, 511.85, 482.76, 506.44, 47859.77]` = `[time, low, high, open, close, volume]`. Note this Coinbase 2026-08-04 close of **$506.44** sits ~1.3% below the **$513.22** CoinGecko snapshot in the Snapshot section: CoinGecko reports a cross-venue volume-weighted average, Coinbase reports its own book. A gap of this size is ordinary venue spread, not a data error — but it is a reminder that **a backtest run on Coinbase bars is a backtest of Coinbase prices**, not of the global composite.
- Backward pagination retrieved **948 daily bars from 2024-01-01 to 2026-08-05** in 4 requests, consistent with the module's 300-candle cap.
- `GET /currencies/ZEC` → `status: online`, 110 network confirmations for deposits.

**Practical notes for wiring it up:**

- Use **`ZEC-USD`**. **`ZEC-USDC` and `ZEC-BTC` will fail** — both return `status: delisted`, `trading_disabled: true`. A cross-rate study that assumes a ZEC-BTC series exists on Coinbase will break, and this is a realistic mistake to make since ZEC-BTC is the natural pair for a crypto-relative study.
- Cache path will be `data/ZEC_1d.csv` per `fetch.py`'s naming.
- `base_increment` is `1e-8` and `quote_increment` is `0.01`. At ~$513 the tick is ~0.2bp — **far finer resolution than DOGE's**, so tick-rounding is not a hazard here.
- All six granularities are available. Note ZEC's daily base volume is small in coin terms (~27k–54k ZEC/day observed), so **intraday bars will contain thin and occasionally gappy periods** — validate bar completeness before running anything at 1m or 5m.

**Analytical cautions specific to ZEC, and they are stronger than for the other two assets:**

1. **The October 2025 breakout will dominate any fitted model.** A +63% single day and a subsequent 5.5x month inside a 948-bar sample is a single observation with enormous leverage over parameter estimates. Any strategy that looks good on 2024–2026 ZEC should be re-run excluding 2025-10-01 → 2025-11-30 to see what survives. If the edge disappears, the strategy found one event, not a signal.
2. **Volatility scaling across the universe.** ZEC at 151.6% annualized against BTC at 43.4% means equal-notional positions are not remotely equal-risk. Any multi-asset study mixing ZEC with the cached BTC/ETH/SOL series must volatility-normalize or ZEC will dominate the portfolio's risk contribution.
3. **ZEC is the genuine diversifier of the three — conditionally.** At +0.41 full-window correlation to BTC it carries real independent information, unlike DOGE at +0.77. But at +0.72 over the trailing 30d that benefit is currently much reduced. If the study's value rests on ZEC's low correlation, that assumption needs to be tested per-regime rather than assumed across the sample.
4. **Listing risk is a live data-continuity risk, not just a trading risk.** Coinbase has already delisted two ZEC pairs. If ZEC-USD were ever to follow, the fetcher would lose the series entirely — the same failure mode TRX already exhibits. Consider persisting fetched ZEC history to the local cache promptly rather than assuming it will remain retrievable on demand.

## Sources

[^zec-supply]: Zcash supply, halving and NU6 — 21M cap; ~16,804,278 ZEC circulating (~80.0%) as of August 2026; second halving November 2024 at block ~1,046,400 cutting the reward 3.125 → 1.5625 ZEC and inflation ~4% → ~2%; next halving projected late 2028 (→ 0.78125 ZEC); NU6 (November 2024) split the block subsidy 80% miners / 8% Zcash Community Grants / 12% in-protocol lockbox. Aggregated from CoinGecko/CoinMarketCap supply pages, CoinDesk Research "Inside Zcash: Encrypted Money at Planetary Scale" [https://www.coindesk.com/research/inside-zcash-encrypted-money-at-planetary-scale](https://www.coindesk.com/research/inside-zcash-encrypted-money-at-planetary-scale), and Zcash upgrade coverage. Tier-2. Current lockbox balance and disbursement policy **UNVERIFIED**. verified-as-of: 2026-08-04

[^zec-shielded]: Shielded-pool share of supply — ~8% early 2024 → ~18% October 2025 → ~23% November 2025 → **~30% by May 2026**. crypto.news, "Why 30% of Zcash supply is now in the shielded pool" [https://crypto.news/why-30-of-zcash-supply-is-now-in-the-shielded-pool/](https://crypto.news/why-30-of-zcash-supply-is-now-in-the-shielded-pool/); Coin Metrics State of the Network issue 338 [https://coinmetrics.substack.com/p/state-of-the-network-issue-338](https://coinmetrics.substack.com/p/state-of-the-network-issue-338). Tier-2. The **causal claim** that shielding growth drove price is **UNVERIFIED** and is presented here only as an unresolved question. verified-as-of: 2026-08-04

[^zec-catalysts]: Catalysts — Grayscale filing to convert the Zcash Trust (ZCSH) to a spot ETF (**filing only; approval status UNVERIFIED**); Cypherpunk Technologies reported accumulation; Robinhood listing and THORChain integration; **SEC closed its Zcash Foundation investigation on 2026-01-15 without recommending enforcement**, reportedly a >3% same-day move. Secondary reporting also cites a "$748 record high" and a "~$50 early 2025 → ~$700 November 2025" path, and a 2026-05-06 ~30% single-day surge to ~$543. CoinDesk (2026-05-06) [https://www.coindesk.com/markets/2026/05/06/zcash-bets-turn-into-second-largest-liquidations-behind-bitcoin-as-zec-rockets-30](https://www.coindesk.com/markets/2026/05/06/zcash-bets-turn-into-second-largest-liquidations-behind-bitcoin-as-zec-rockets-30); KuCoin and crypto.news coverage. Tier-2/3. **Where these conflict with the primary Coinbase series in the dated table above, prefer the primary series.** verified-as-of: 2026-08-04

[^zec-move]: The 2025–26 move — **derived** by this reference from Coinbase ZEC-USD daily candles (948 bars, 2024-01-01 → 2026-08-05), retrieved 2026-08-05. Key dated values: period low close $18.32 (2024-07-05); Sep-2025 month-end $74.13; **2025-10-01 close $120.80 from $74.13, intraday high $153.00, volume 404,610 ZEC vs 78,696 prior day**; Oct-2025 month-end $405.48; **intraday high $744.13 on 2025-11-07** (volume 789,047); **peak close $698.99 on 2025-11-16**; max drawdown −71.8% trough 2026-03-07; 2026-08-05 close $513.66. Reproducible from `api.exchange.coinbase.com/products/ZEC-USD/candles`. Tier-1 (primary venue data). verified-as-of: 2026-08-05

[^zec-coinbase]: Coinbase listing status — **primary-source verification by direct API call, 2026-08-04.** `/products/ZEC-USD` → `status: online`, `trading_disabled: false`, `base_increment: 0.00000001`, `quote_increment: 0.01`. `/products` enumeration returned exactly three ZEC products: **ZEC-BTC `delisted`/`trading_disabled: true`, ZEC-USDC `delisted`/`trading_disabled: true`, ZEC-USD `online`**. `/products/ZEC-USDT` → NotFound. `/currencies/ZEC` → `status: online`, 110 network confirmations. `api.coinbase.com/api/v3/brokerage/market/products/ZEC-USD` → live, 24h volume 54,254.98 ZEC. **Monero: zero products among all 832. Dash: DASH-USD and DASH-BTC both online.** Tier-1 (primary). verified-as-of: 2026-08-04

[^zec-venues]: Venue verification by direct public API call, 2026-08-04. OKX `/api/v5/market/ticker?instId=ZEC-USDT` → live, ~$9.27M 24h notional (**contradicts reports of a January 2024 OKX ZEC delisting; prefer the live check**). Kraken `/0/public/Ticker?pair=ZECUSD` → live as `XZECZUSD`, ~$6.50M 24h notional. Binance and Bybit geo-restricted from this environment (**unverified**). Coinbase ZEC-USD ~$27.89M. Venue-share percentages **derived** against the ~$0.20B CoinGecko global volume figure. Tier-1 (primary). verified-as-of: 2026-08-04

[^zec-delisting]: Privacy-asset delisting landscape (secondary, described without advocacy) — OKX removed XMR/ZEC/DASH pairs 2024-01-05; Binance delisted XMR globally 2024-02-20; Kraken withdrew XMR in Ireland and Belgium June 2024 and across the EEA 2024-10-31; reports of 73 exchanges dropping privacy coins during 2025; stated drivers are AML obligations, the FATF Travel Rule and EU MiCA; holding and trading XMR/ZEC/DASH remains legal in the US, EU and most jurisdictions. Blockworks [https://blockworks.com/news/crypto-exchanges-delisting-privacy-coins](https://blockworks.com/news/crypto-exchanges-delisting-privacy-coins); TradingView/Crypto Briefing (Kraken EEA); CoinTelegraph (OKX). Tier-2/3, and **ages badly in both directions** — the OKX ZEC case above is a verified counter-example. verified-as-of: 2026-08-04

[^zec-vol]: Volatility, correlation, beta, drawdown **and all cross-asset comparatives** — **derived** by this reference from Coinbase daily candles for **ZEC-USD, BTC-USD and DOGE-USD** (948 bars each, 2024-01-01 → 2026-08-05) plus **Kraken TRXUSD** daily OHLC (`https://api.kraken.com/0/public/OHLC?pair=TRXUSD&interval=1440`, 721 bars from 2024-08-15), all retrieved 2026-08-05. TRX is sourced from Kraken because **Coinbase does not list it** — see the TRX reference in this directory. Any TRX-involving comparative is computed on the 720-return intersection of all four series (2024-08-16 → 2026-08-05); ZEC/BTC/DOGE comparatives use the full 948-bar window. Annualized vol = population stdev of daily log returns × √365. Beta and correlation on aligned daily log returns. Drawdown computed on daily closes from running peak. Reproducible from `api.exchange.coinbase.com/products/{ZEC-USD,BTC-USD,DOGE-USD}/candles` plus the Kraken endpoint above. **Cross-asset turnover figures now come from the single-timestamp pull described in [^turnover-std], not from per-coin snapshots; the DOGE venue-share figure (~1.9%) derives from the same primary venue APIs cited in [^zec-venues].** verified-as-of: 2026-08-05

[^zec-snapshot]: Price, market cap and 24h volume snapshot — CoinGecko, 2026-08-04, as supplied to this research. Turnover, implied supply, FDV and FDV/mcap are **derived** from those figures. Cross-checked: Coinbase ZEC-USD close 2026-08-05 was $513.66 and the retail reference endpoint returned $514.10, both consistent with the $513.22 snapshot. verified-as-of: 2026-08-04

[^zec-local]: Local bar cache contents — direct filesystem check of `~/dev/solmargintrader/data/` and read of `~/dev/solmargintrader/backtester/core/fetch.py`. Tier-1 (primary). verified-as-of: 2026-08-04

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
