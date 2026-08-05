---
name: trx-tron
description: Trader-facing reference for TRON (TRX) — the dominant USDT settlement chain by transfer count, a low-turnover asset whose recent realized volatility runs below Bitcoin's despite a −51% historical drawdown, with contested holder concentration, and NOT listed on Coinbase (a hard blocker for this project's fetcher).
---

# TRON (TRX)

> Educational reference only. Nothing here is investment advice. Crypto trading can lose money, and the concentration, venue-access, and governance risks described below are real.

## Snapshot (AS OF 2026-08-04)

| Metric | Value | Source |
|---|---|---|
| Price | ~$0.3267 | CoinGecko, 2026-08-04[^trx-snapshot] |
| Market cap | ~$31.0B | CoinGecko, 2026-08-04[^trx-snapshot] |
| 24h volume | ~$0.45B | CoinGecko, 2026-08-04[^trx-snapshot] |
| Turnover (vol ÷ mcap) | **~1.45%** | derived from the row above[^trx-snapshot] |
| Implied circulating supply (mcap ÷ price) | ~94.89B TRX | derived[^trx-snapshot] |
| Reported circulating supply | ~94.86B TRX (~99.99% of a slightly larger total) | secondary, July 2026[^trx-supply] |
| Annualized vol, trailing 365d | **27.3%** | derived, Kraken TRXUSD daily closes to 2026-08-05[^trx-vol] |
| Annualized vol, trailing 30d | **15.3%** | derived, same series[^trx-vol] |
| Beta to BTC, trailing 365d | **+0.29** | derived, Kraken TRX vs Coinbase BTC-USD[^trx-vol] |
| Coinbase listing | **NONE — no product, no candles** | verified against Coinbase APIs, 2026-08-04[^trx-coinbase] |

Note the three volatility/beta rows are computed on a series ending **2026-08-05**, one day after the price snapshot date in this section's heading.

**These figures decay.** Price, market cap, volume, and turnover are a single-day snapshot and are stale the moment they are read. The volatility and beta numbers are window-dependent and will drift as the window rolls. Re-derive before relying on any of them. The one item here with real staying power is the Coinbase listing status — but even that should be re-checked with a single API call (given below) rather than assumed.

Cross-check: the implied supply derived from the CoinGecko snapshot (94.89B) matches the independently reported supply (~94.86B) to within 0.03%, so the snapshot's price and market cap are internally consistent.

## What it is, mechanically

TRON is a **delegated-proof-of-stake (DPoS)** layer-1 chain. Block production is handled by a small elected validator set (**Super Representatives**), elected by votes weighted by staked TRX. This is a materially different security and governance model from Bitcoin's or Ethereum's — the validator set is small, elected, and therefore concentrated by design.

TRX is not primarily a "smart contract platform" token in the way ETH is. In practice it is **the fee and resource token for a stablecoin settlement rail**:

- **Resource model.** Transactions consume **Bandwidth** (byte-size cost) and **Energy** (computation cost). You obtain these by **staking TRX** (which also yields TRON Power for governance voting), or, if you hold insufficient resources, the protocol **burns TRX** from your balance to pay for the transaction.[^trx-resources] So network usage creates a direct, mechanical TRX sink.
- **What actually uses it.** TRON is the leading settlement chain for **USDT (Tether)** by transfer count and by settled volume. Roughly **$86B of USDT sits on TRON — about half of all Tether supply** — and the network processed on the order of **$2.0 trillion in cumulative USDT transfers during Q1 2026**.[^trx-usdt] The same reporting separately cites a daily average near **$23B/day**; note these are independently rounded source figures and do not reconcile exactly ($2.0T ÷ 90 days ≈ $22.2B/day), so treat both as order-of-magnitude rather than re-derivable from one another. Reporting also places roughly **93% of TRON's stablecoin transfer volume as peer-to-peer as of Q2 2026**, the highest share among tracked chains[^trx-usdt] — i.e. payments and remittance-shaped flow, not exchange arbitrage.

The trader-relevant consequence: **TRX's demand driver is stablecoin payment throughput, not speculative DeFi activity or an app ecosystem.** That is an unusually utilitarian, unusually non-cyclical demand base for a crypto asset, and it shows up directly in the volatility profile below.

*Unverified:* the exact current split of TRX burned per day versus issued to Super Representatives. The burn mechanism is documented, but the claim frequently repeated in secondary sources that TRON is *net deflationary* at present is not verified here and should be checked against a live supply chart before it is relied on.

## Supply and issuance

- **Origin:** ~100B TRX from the 2017 ICO. At mainnet launch, **1B TRX was burned** in an "Independence Day" event.[^trx-supply]
- **No Bitcoin-style hard cap and no halving schedule.** Issuance is block rewards to Super Representatives; the offset is the resource-model burn described above.
- **Supply is effectively fully circulating.** Reported circulating supply is **~99.99% of total supply** (July 2026)[^trx-supply], and the derived figure above agrees. There is therefore **no meaningful unlock/vesting overhang** — which is a genuine structural difference from most large-cap alts, and removes one common source of forced supply.
- Net supply change is the difference between SR block rewards and resource burn. Because burn scales with USDT transfer count, **TRX's net issuance is a function of payment demand** — an unusual and worth-understanding coupling.

## Concentration, float and turnover

**Turnover is the headline number: ~1.45%** ($0.45B volume against a $31.0B cap, CoinGecko 2026-08-04). For scale, on the single-timestamp pull[^turnover-std] DOGE turns over 3.44% and ZEC 2.30%, and TRX is 7th of the ten coins in this directory. TRX is a **$31B asset that trades like a much smaller one.**

Low turnover on a large cap has a specific meaning for a trader: **the market cap is not a liquidity promise.** A large notional position is priced off a float that changes hands slowly. Exit slippage is the risk, not entry.

**Concentration is real but the numbers are genuinely contested, and this reference will not pick a side:**

- Arkham-sourced reporting puts **Justin Sun's *known, attributed* holdings at ~2% of TRX supply**, making him the largest identified individual holder and roughly the sixth-largest entity overall.[^trx-conc-arkham]
- Separately, a Bloomberg-sourced report has been cited as claiming **Sun controls approximately 63% of all TRX**.[^trx-conc-bloomberg]

These two figures differ by more than an order of magnitude and **cannot both be describing the same thing.** The plausible reconciliation is that the low figure counts only wallets positively attributed to Sun personally, while the high figure attributes foundation, exchange-custody, and affiliated-entity wallets to his control. **Both specific percentages are marked UNVERIFIED here.** Do not quote either as fact.

What *can* be stated without picking a side, because it follows from the chain's design rather than from wallet attribution:

- The DPoS model concentrates block production in a small elected validator set.
- Voting power is proportional to staked TRX, so **token concentration converts directly into governance control**.
- Staking for Energy/Bandwidth and for SR voting **immobilizes float**, which is part of why observed turnover is so low.
- A large share of visible supply sits in exchange-custody wallets, which makes naive block-explorer "top holder" tables misleading in both directions.

## What drives the price

Ranked roughly by how much of the observable variance they plausibly explain:

1. **USDT settlement throughput on TRON.** The clearest fundamental link: more transfers → more Energy/Bandwidth consumed → more TRX burned or staked. This is the reason TRX behaves less like a beta asset than its peers.
2. **Stablecoin competition and routing.** TRON's position is not guaranteed. Migration of USDT flow to other chains, or the growth of alternative settlement rails, is the primary structural threat to the demand story.
3. **Venue access and regulatory posture.** TRX's absence from the largest US-regulated retail venue (see below) caps the addressable US retail bid and is itself a persistent discount factor.
4. **Justin Sun headline and legal risk.** Founder-linked idiosyncratic risk is unusually high for an asset of this size, given the concentration questions above.
5. **Broad crypto beta — but weakly.** Beta to BTC is ~+0.29 to +0.35 across windows (derived, see below). TRX participates in market-wide moves far less than a typical large-cap alt.

## Market structure and liquidity

**Verified listing status (all checked live 2026-08-04, primary APIs).**[^trx-coinbase][^trx-venues]

| Venue | TRX pair | Status | 24h notional (verified) |
|---|---|---|---|
| **Coinbase Exchange** | TRX-USD, TRX-USDT | **NOT FOUND — does not exist** | n/a |
| **Coinbase Advanced Trade** | TRX-USD | **`NOT_FOUND: Product TRX-USD not supported`** | n/a |
| OKX | TRX-USDT | online | ~$5.56M |
| Kraken | TRXUSD | online | ~$1.45M |
| Binance | TRXUSDT | **could not verify — geo-restricted from this environment** | unverified |
| Bybit | TRXUSDT | **could not verify — geo-blocked (CloudFront country block)** | unverified |

**An important trap, and the reason secondary sources get this wrong.** Coinbase *does* publish a TRON price page and *does* return a TRX price from its retail reference-price endpoint (`api.coinbase.com/v2/prices/TRX-USD/spot` returned `0.3150` on 2026-08-04). Several third-party articles read that as "Coinbase supports TRX." **It does not mean that.** That endpoint is an indexed reference price, not a Coinbase order book. There is no TRX order book, no TRX product, and no TRX candle history on Coinbase. Note also that the reference price ($0.3150) sits ~3.5% below the CoinGecko consensus price ($0.3267) — consistent with an indexed quote rather than a venue print.

**Liquidity is concentrated offshore.** The two Western venues that can be verified from here (OKX, Kraken) together show only **~$7.0M of 24h notional** against a reported global **~$450M**.[^trx-venues] The overwhelming majority of TRX liquidity therefore sits on venues that are geo-restricted from this environment — principally Binance. For a US-accessible trader this is a meaningful access constraint, not a trivia point: **the ~$7.0M figure, not the ~$450M global figure, is the one that bounds a position that has to be entered and exited from here.**

## Volatility and correlation

Derived from **Kraken TRXUSD daily closes** (the highest-quality TRX series retrievable from this environment) against **Coinbase BTC-USD daily closes**, window ending 2026-08-05. Overlap: 721 daily bars from 2024-08-15.[^trx-vol]

| Window | TRX ann. vol | BTC ann. vol | TRX corr(BTC) | TRX beta(BTC) |
|---|---|---|---|---|
| Full (2024-08-16 → 2026-08-05) | **65.4%** | 44.5% | +0.23 | +0.34 |
| Trailing 365d | **27.3%** | 43.4% | +0.46 | +0.29 |
| Trailing 90d | **22.2%** | 34.6% | +0.55 | +0.35 |
| Trailing 30d | **15.3%** | 29.0% | +0.59 | +0.31 |

**The standout result: over the trailing year, TRX has been materially *less* volatile than Bitcoin** — 27.3% against BTC's 43.4%, and 15.3% against 29.0% over the last 30 days. That is a rare profile in crypto and it is consistent with the mechanical story: a payments-utility token with a slow-moving, heavily-staked float and a demand base tied to stablecoin throughput rather than risk appetite.

Note the full-window vol (65.4%) is much higher than the trailing-year vol (27.3%). The volatility regime **changed** — the earlier part of the window contains the 2024-12 to 2025-03 episode. Do not use the full-window number as a forward estimate without acknowledging that break.

**Cross-asset comparison.** Computed over the **identical** 720-return window (2024-08-16 → 2026-08-05) so the three are directly comparable:[^trx-vol]

| Asset | beta(BTC) | corr(BTC) | ann. vol |
|---|---|---|---|
| **TRX** | **+0.34** | +0.23 | 65.4% |
| DOGE | +1.53 | +0.78 | 87.3% |
| ZEC | +1.19 | +0.41 | 127.5% |
| BTC | 1.00 (by definition) | 1.00 | 44.5% |

TRX carries roughly **one-quarter of DOGE's market beta and under a third of ZEC's** — the least "crypto-beta" of the three by a wide margin, and the only one of the three with a beta below 1. Pairwise, TRX–DOGE correlation is +0.23 and TRX–ZEC is +0.14 over the same window.

**Drawdown:** max drawdown over the observed window **−51.0%, trough 2025-03-16**, from a high of **$0.4329 on 2024-12-03**. Low realized volatility has *not* meant absence of large drawdowns. This is the single most important caveat to the low-vol finding.

## Known failure modes for traders

1. **Mistaking a $31B cap for $31B of liquidity.** At ~1.45% turnover, TRX is the least liquid-per-unit-of-cap asset in this set. Size positions against *volume*, not market cap — and specifically against **the ~$7.0M of 24h notional reachable from the venues you can actually trade** (OKX + Kraken, verified), not the ~$450M global figure that includes geo-restricted venues.
2. **Treating low realized vol as low risk.** The trailing-30d vol of 15.3% sits alongside a −51.0% historical drawdown. The distribution has thin shoulders and a fat left tail — a low standard deviation is not a small worst case.
3. **Using it as a crypto-beta expression.** With beta ~+0.3, TRX will badly under-track a broad crypto rally. If the thesis is "crypto goes up," TRX is a poor instrument for it.
4. **Building a holder-concentration thesis on block-explorer data.** Exchange-custody and contract addresses dominate top-holder tables. The two published concentration figures differ by >30x. Any strategy conditioned on a specific concentration number is conditioned on an unverified input.
5. **Single-founder headline risk.** Idiosyncratic, hard to hedge, and not correlated with anything you can offset with a market instrument.
6. **Assuming Coinbase access.** The most common practical error, and the most consequential for this project. See below.
7. **Stablecoin-rail displacement.** The demand story rests on TRON retaining USDT flow. That is a competitive position, not a moat.

## For this backtester

**None of the assets in this reference set are held in the local cache.** `~/dev/solmargintrader/data/` currently contains only `BTC_1d.csv`, `ETH_1d.csv`, `SOL_1d.csv`, `SOL_1h.csv`, and `JLP_spot.csv` (checked 2026-08-04).[^trx-local]

**TRX is a hard blocker. Coinbase does not list it, so this project's fetcher cannot retrieve it at all.**

This is verified, not assumed.[^trx-coinbase] `backtester/core/fetch.py` fetches exclusively from `https://api.exchange.coinbase.com/products/{product}/candles`. Against that exact API on 2026-08-04:

- `GET /products` returned **832 products; zero contain TRX** (checked by both `id` and `base_currency`).
- `GET /products/TRX-USD` → `{"message":"NotFound"}`
- `GET /products/TRX-USDT` → `{"message":"NotFound"}`
- `GET /products/TRX-USD/candles?granularity=86400` → `{"message":"NotFound"}` — **this is literally the call the fetcher would make, and it fails.**
- `GET /currencies/TRX` → **empty** (TRX is not a supported currency on Coinbase Exchange at all, not merely an unlisted pair).
- Coinbase Advanced Trade, independently: `GET /api/v3/brokerage/market/products/TRX-USD` → `{"error":"NOT_FOUND","message":"Product TRX-USD not supported"}`.

So the blocker is confirmed on **two independent Coinbase trading APIs**, and at the currency level rather than just the pair level.

**No workaround exists inside the current fetcher.** The module's docstring states that Binance is deliberately unsupported because it returns *"Service unavailable from a restricted location"* from this environment — which this research independently reproduced (`api.binance.com` returned exactly that error on 2026-08-04). There is no second venue wired into `fetch.py`.

**If TRX coverage is ever wanted, it requires new fetcher code, not new configuration.** The realistic candidates, both verified reachable from this environment on 2026-08-04:

- **Kraken** — `https://api.kraken.com/0/public/OHLC?pair=TRXUSD&interval=1440`. Returned 721 daily bars back to 2024-08-15. Note the row layout is `[time, open, high, low, close, vwap, volume, count]` — **a different order from Coinbase's `[time, low, high, open, close, volume]`**, and Coinbase's non-OHLCV ordering is precisely the hazard `fetch.py`'s docstring exists to warn about. Any Kraken adapter must map columns explicitly by name, or it will silently corrupt every backtest downstream in exactly the way the existing module was written to prevent.
- **CoinGecko** — `/api/v3/coins/tron/market_chart` returned daily closes, but **closes only, no OHLC and no per-venue volume**, so it cannot populate a bar schema that expects `BAR_COLUMNS`.

**Kraken's usable history depth is ~2 years, and this was probed rather than assumed.** A default call returned 721 daily bars (earliest 2024-08-15). Re-requesting with `since=2023-01-01` returned **the same 721 bars with the same 2024-08-15 earliest date** — so the endpoint serves a fixed rolling window and `since` does not page further back.[^trx-vol] Deeper TRX history would require a different Kraken endpoint or a different provider entirely. Since the already-cached BTC/ETH/SOL series run longer, **a Kraken-sourced TRX series would truncate the usable window of any cross-asset study that includes it.**

**Recommendation for this project as it stands: treat TRX as out of universe.** It cannot be fetched, it cannot be validated against the existing bar pipeline without new column-mapping code, and its low beta (~+0.3) means it would not behave like the assets the current strategies are tuned on anyway.

## Sources

[^trx-supply]: TRON supply and ICO history — ~94.86B circulating, reported as ~99.99% of total supply (the two figures round to the same 4 significant figures; the residual unissued amount is below that rounding precision) as of July 2026; 100B ICO 2017; 1B burned at mainnet "Independence Day". Aggregated from CoinGecko/CoinMarketCap/CryptoQuant supply pages and TRON developer docs, [https://developers.tron.network/docs/tron-economic-model](https://developers.tron.network/docs/tron-economic-model). Tier-2/3. verified-as-of: 2026-08-04

[^trx-resources]: TRON resource model — Bandwidth and Energy, staking for TRON Power, automatic TRX burn when resources are insufficient. TRON developer documentation, [https://developers.tron.network/docs/resource-model](https://developers.tron.network/docs/resource-model) and [https://tronprotocol.github.io/documentation-en/mechanism-algorithm/resource/](https://tronprotocol.github.io/documentation-en/mechanism-algorithm/resource/). Tier-1 (protocol docs). verified-as-of: 2026-08-04

[^trx-usdt]: TRON USDT settlement scale — ~$86B USDT on TRON (~half of Tether supply); ~$2.0T cumulative USDT transfers in Q1 2026; ~$23B/day average; ~93% of stablecoin transfer volume P2P as of Q2 2026. Messari "State of TRON Q1 2026" [https://messari.io/report/state-of-tron-q1-2026](https://messari.io/report/state-of-tron-q1-2026); CoinDesk Research "Tron Network Q1 2026" [https://www.coindesk.com/research/tron-network-q1-2026](https://www.coindesk.com/research/tron-network-q1-2026); FXStreet (2026-03-12). Tier-2. verified-as-of: 2026-08-04

[^trx-conc-arkham]: Justin Sun attributed holdings ~2% of TRX supply, largest identified individual holder, ~6th largest entity. Arkham Intelligence research, [https://info.arkm.com/research/justin-sun-net-worth-2026](https://info.arkm.com/research/justin-sun-net-worth-2026). **Conflicts with the Bloomberg-sourced figure below; both marked UNVERIFIED.** verified-as-of: 2026-08-04

[^trx-conc-bloomberg]: Claim that Justin Sun controls ~63% of all TRX, attributed to a Bloomberg report and repeated in secondary coverage (e.g. Protos, BTCC). **Not independently verified; conflicts by >30x with the Arkham attributed-holdings figure. Marked UNVERIFIED — do not quote as fact.** verified-as-of: 2026-08-04

[^trx-coinbase]: Coinbase listing status — **primary-source verification by direct API call, 2026-08-04.** `api.exchange.coinbase.com`: `/products` (832 products, zero TRX), `/products/TRX-USD` → NotFound, `/products/TRX-USDT` → NotFound, `/products/TRX-USD/candles?granularity=86400` → NotFound, `/currencies/TRX` → empty. `api.coinbase.com/api/v3/brokerage/market/products/TRX-USD` → `NOT_FOUND: Product TRX-USD not supported`. Contrast: `api.coinbase.com/v2/prices/TRX-USD/spot` → `0.3150` (indexed reference price, **not** a tradable order book). Tier-1 (primary). verified-as-of: 2026-08-04

[^trx-venues]: Venue verification by direct public API call, 2026-08-04. OKX `/api/v5/market/ticker?instId=TRX-USDT` → live, ~$5.56M 24h notional. Kraken `/0/public/Ticker?pair=TRXUSD` → live, ~$1.45M 24h notional. Binance `/api/v3/ticker/24hr?symbol=TRXUSDT` → "Service unavailable from a restricted location" (geo-restricted, **unverified**). Bybit `/v5/market/tickers` → CloudFront country block (**unverified**). Tier-1 (primary). verified-as-of: 2026-08-04

[^trx-vol]: Volatility, correlation, beta, drawdown and the cross-asset comparison table — **derived** by this reference from **four** series, all retrieved 2026-08-05: Kraken TRXUSD daily OHLC (`https://api.kraken.com/0/public/OHLC?pair=TRXUSD&interval=1440`, 721 bars from 2024-08-15) and Coinbase daily candles for **BTC-USD, DOGE-USD and ZEC-USD** (`https://api.exchange.coinbase.com/products/{id}/candles?granularity=86400`). The cross-asset table is computed on the 720-return intersection of all four series (2024-08-16 → 2026-08-05) so the assets are directly comparable; the TRX-only windows use the TRX/BTC pair. Annualized vol = population stdev of daily log returns × √365. Beta and correlation computed on aligned daily log returns. Reproducible from those four endpoints. **History-depth probe:** re-requesting the Kraken endpoint with `since=1672531200` (2023-01-01) returned the same 721 bars and the same 2024-08-15 earliest date, establishing that the endpoint serves a fixed rolling window rather than paging further back. verified-as-of: 2026-08-05

[^trx-snapshot]: Price, market cap and 24h volume snapshot — CoinGecko, 2026-08-04, as supplied to this research. Turnover and implied supply are **derived** from those figures. Cross-checked: Kraken TRXUSD last close 2026-08-05 was $0.326363, consistent with the $0.3267 snapshot. verified-as-of: 2026-08-04

[^trx-local]: Local bar cache contents — direct filesystem check of `~/dev/solmargintrader/data/` and read of `~/dev/solmargintrader/backtester/core/fetch.py`. Tier-1 (primary). verified-as-of: 2026-08-04

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
