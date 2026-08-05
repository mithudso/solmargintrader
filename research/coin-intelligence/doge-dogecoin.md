---
name: doge-dogecoin
description: Trader-facing reference for Dogecoin (DOGE) — uncapped supply with fixed ~5.256B/yr issuance and therefore a declining inflation rate, merge-mined with Litecoin, and the purest sentiment/reflexivity asset in this set; a stable high-beta BTC proxy rather than a diversifier.
---

# Dogecoin (DOGE)

> Educational reference only. Nothing here is investment advice. DOGE has drawn down 85% from its recent high within the window studied below.

## Snapshot (AS OF 2026-08-04)

| Metric | Value | Source |
|---|---|---|
| Price | ~$0.0702 | CoinGecko, 2026-08-04[^doge-snapshot] |
| Market cap | ~$10.9B | CoinGecko, 2026-08-04[^doge-snapshot] |
| 24h volume | ~$0.38B | CoinGecko, 2026-08-04[^doge-snapshot] |
| Turnover (vol ÷ mcap) | **3.44%** | derived from the row above[^doge-snapshot] |
| Implied circulating supply (mcap ÷ price) | ~155.27B DOGE | derived[^doge-snapshot] |
| Reported circulating supply | ~154.9B DOGE (mid-2026) | secondary[^doge-supply] |
| Max supply | **None — uncapped** | protocol[^doge-supply] |
| Annual issuance | **~5.256B DOGE, fixed** | protocol[^doge-supply] |
| Implied inflation rate | **~3.39%/yr** | derived: 5.256B ÷ 155.27B[^doge-snapshot] |
| Annualized vol, trailing 365d | **73.9%** | derived, Coinbase DOGE-USD daily closes to 2026-08-05[^doge-vol] |
| Correlation to BTC, trailing 365d | **+0.77** | derived, same series[^doge-vol] |
| Coinbase listing | **Yes — DOGE-USD online, candles retrievable** | verified via Coinbase API, 2026-08-04[^doge-coinbase] |

Note the two volatility/correlation rows are computed on a series ending **2026-08-05**, one day after the price snapshot date in this section's heading.

**These figures decay.** The price, cap, volume and turnover are a one-day snapshot. The inflation rate declines every single year by construction (see below), so a quoted percentage is only correct for the supply it was computed against. The volatility and correlation figures are window-dependent. Re-derive before use.

Cross-check: implied supply from the snapshot (155.27B) agrees with the independently reported ~154.9B to within ~0.2%, so the snapshot is internally consistent.

## What it is, mechanically

Dogecoin is a **Scrypt proof-of-work** chain, forked from Litecoin's lineage (itself a Bitcoin derivative). It is a plain UTXO payment chain — no smart contract layer, no staking, no governance token mechanics. Mechanically it is one of the simplest assets in crypto, and that simplicity is the point: **almost none of DOGE's price behaviour is explained by protocol mechanics.**

Two structural facts do matter:

**1. Block schedule and reward.** ~1-minute target block time, with a **fixed reward of 10,000 DOGE per block**, permanently. There is no halving.[^doge-supply]

**2. Merge-mining with Litecoin (AuxPoW).** Since **August 2014**, Dogecoin has been merge-mined with Litecoin via Auxiliary Proof of Work.[^doge-merge] Both use Scrypt, so a Litecoin miner can secure Dogecoin with the same hardware and the same work, at no additional energy cost, collecting both rewards.

This is the single most important security fact about the chain, and it is widely misunderstood:

- Before AuxPoW, Dogecoin's standalone hashrate was small enough that 51% attacks were a live concern. Within roughly a month of the switch, **difficulty/hashrate rose by an order of magnitude** as Scrypt pools extended coverage.[^doge-merge]
- Post-AuxPoW, attacking Dogecoin means confronting **the aggregate Scrypt hashrate securing Litecoin**, not Dogecoin's own economically-justified hashrate.
- Dogecoin and Litecoin hashrate have since shown a **very high positive correlation (~0.95)**.[^doge-merge]
- The trade-off — and it is a genuine one that Dogecoin developers publicly dispute — is that DOGE's security is **coupled to Litecoin's miner economics**. Dogecoin's security budget is not independently set by DOGE's own price.[^doge-merge]

For a trader, the practical read: **DOGE's chain security is not a variable you need to model day to day, but it is not sovereign either.** It is a derived quantity that depends on the health of Scrypt mining generally.

*Unverified:* precise current Dogecoin hashrate. Secondary sources place it in the ~2.7–3.4 PH/s range as of mid-2026[^doge-merge], but this was not independently confirmed and moves constantly.

## Supply and issuance

This is the section most often stated incorrectly, so the arithmetic is shown explicitly.

**There is no supply cap.** CoinMarketCap renders DOGE's max-supply field as the infinity symbol.[^doge-supply] Dogecoin briefly had a cap of 100B in its earliest design; that was removed, and issuance has been perpetual since.

**Issuance is a fixed absolute quantity, not a fixed percentage:**

```
10,000 DOGE/block × ~1 block/minute × 525,600 minutes/year ≈ 5.256B DOGE/year
```

**Therefore the inflation *rate* declines every year, even though the inflation *amount* never does.** The numerator is constant; the denominator grows by that same constant each year:

| Supply base | Implied annual inflation (5.256B ÷ supply) |
|---|---|
| 148B | 3.55% |
| **155.27B (implied, 2026-08-04)** | **3.39%** |
| 160B | 3.28% |
| 200B | 2.63% |
| 300B | 1.75% |

Secondary sources put DOGE's 2026 inflation at ~3.4%[^doge-supply], which matches the derived 3.39% above.

**Why this matters and why it is not the same as Bitcoin's disinflation.** Both assets have a falling percentage inflation rate, but for opposite reasons and with opposite terminal behaviour:

- Bitcoin's *absolute* issuance halves periodically and converges to zero; total supply is bounded at 21M.
- Dogecoin's *absolute* issuance is constant forever; total supply is unbounded and grows linearly without limit. The falling rate is purely an arithmetic artifact of a growing denominator.

The trader-relevant consequence: **DOGE has a permanent, price-insensitive supply of new coins hitting the market — roughly 5.256B DOGE/year, worth about $369M/year at the 2026-08-04 price of $0.0702** (derived). Miners have costs and are structurally net sellers, so this is the **upper bound** on issuance-driven sell pressure rather than a measured net-selling figure; miners need not liquidate all of it. This is a constant headwind that does not diminish in absolute terms, and it must be overcome by demand every year merely to hold price flat.

*Note:* a community proposal to cut the block reward to 1,000 DOGE (500M/yr) has been raised in the Dogecoin GitHub repository.[^doge-proposal] It is a **proposal under discussion, not adopted policy** — treat any issuance-reduction thesis as unverified and speculative.

## Concentration, float and turnover

**Turnover 3.44%**[^turnover-std] ($0.375B against a $10.9B cap) — the **highest of all ten coins in this directory**, ahead of SOL (3.32%) and ETH (3.05%), and the highest of the three assets in this set (TRX 1.45%, ZEC 2.30%). DOGE trades actively relative to its size, which is consistent with its retail-driven, high-participation holder base. Liquidity is not DOGE's problem.

**Float is effectively 100%.** There is no vesting, no lockup, no staking, no foundation treasury schedule of consequence. Every coin ever mined is liquid. This makes DOGE unusually clean from a float-analysis perspective — the awkward questions that dominate the TRX file simply do not arise here.

**Concentration:** DOGE has long been noted to have a small number of very large addresses, with the single largest widely believed to be a Robinhood omnibus custody wallet rather than an individual. **Specific top-holder percentages are marked UNVERIFIED** — this reference did not confirm any figure, and as with TRX, exchange-custody wallets make naive block-explorer top-holder tables misleading. Do not build a strategy on an unverified concentration number.

## What drives the price

DOGE is **the purest sentiment and reflexivity asset in this set.** It has no cash flows, no fee burn, no staking yield, no protocol revenue, and no utility demand that scales with anything measurable. What is left is attention and positioning.

Ranked by plausible explanatory power:

1. **Bitcoin beta.** Empirically the single largest driver. Correlation to BTC is **+0.76 to +0.78 across every window tested** (see below). DOGE is, first and foremost, a leveraged expression of the broad crypto risk cycle.
2. **Attention and personality-driven news flow.** Elon Musk references, corporate/payments integration rumours, and mainstream-media cycles. This is the residual after BTC beta, and it is the component that produces DOGE's idiosyncratic spikes.
3. **Reflexivity.** Price rises generate attention, attention generates inflows, inflows raise price. The loop runs in reverse just as efficiently, which is the mechanism behind the −85% drawdown documented below.
4. **Product/access catalysts.** New listings, ETF speculation, payment integrations. These act as step-changes in the addressable bid.
5. **Issuance drag.** A persistent, slow negative — see above.

**What does *not* drive it:** on-chain activity, developer activity, TVL, fee revenue. Attempting to value DOGE on fundamentals is a category error; the honest framing is that DOGE prices attention, and attention is not forecastable from chain data.

## Market structure and liquidity

**Verified listing status (checked live 2026-08-04, primary APIs).**[^doge-coinbase][^doge-venues]

| Venue | Pairs | Status | 24h notional (verified) |
|---|---|---|---|
| **Coinbase Exchange** | **DOGE-USD, DOGE-USDT, DOGE-EUR, DOGE-GBP, DOGE-BTC** | **all `online`, `trading_disabled: false`** | ~$7.17M (USD pair) |
| OKX | DOGE-USDT | online | ~$16.04M |
| Kraken | XDGUSD | online | ~$1.46M |
| Binance | DOGEUSDT | could not verify — geo-restricted from this environment | unverified |
| Bybit | DOGEUSDT | could not verify — geo-blocked | unverified |

**DOGE has essentially no availability or delisting risk.** It is listed broadly across regulated and offshore venues, in multiple fiat quotes (USD, EUR, GBP) and against BTC. This is the opposite of the ZEC situation and a meaningful structural advantage: DOGE carries none of the venue-concentration risk that privacy assets do, and none of the access blocker that TRX does.

Note that Coinbase's USD pair is only ~1.9% of DOGE's reported ~$380M global 24h volume. The three venues verifiable from this environment (Coinbase USD $7.17M + OKX $16.04M + Kraken $1.46M) total only **~$24.7M, about 6.5% of the global figure** — so **~93% of DOGE's global volume sits on venues this research could not query, most likely Binance (unverified — geo-restricted from this environment).** For a bar-data consumer this does not matter (Coinbase's book is deep enough to produce clean candles). For a large-size execution study it would.

## Volatility and correlation

Derived from **Coinbase DOGE-USD and BTC-USD daily closes**, 948 daily bars, 2024-01-01 → 2026-08-05.[^doge-vol]

| Window | DOGE ann. vol | BTC ann. vol | corr(BTC) | beta(BTC) |
|---|---|---|---|---|
| Full (2024-01-02 → 2026-08-05) | **90.9%** | 47.5% | **+0.78** | +1.49 |
| Trailing 365d | **73.9%** | 43.4% | **+0.77** | +1.32 |
| Trailing 90d | **43.9%** | 34.6% | **+0.78** | +0.99 |
| Trailing 30d | **36.9%** | 29.0% | **+0.76** | +0.97 |

**The most trader-relevant finding in this file: DOGE's correlation to Bitcoin is extraordinarily stable — +0.76 to +0.78 across every window from 30 days to 2.5 years.** Compare ZEC over the same windows, where correlation to BTC swings from +0.41 to +0.72 depending on regime. DOGE does not decouple. It is a persistent, reliable BTC-beta instrument.

**Beta has compressed, though.** Full-window beta is +1.49 and trailing-365d is +1.32, but the trailing 90d and 30d readings are both ≈ +0.98. Over the recent window DOGE has been tracking BTC roughly one-for-one rather than amplifying it, while still carrying ~27% more realized volatility than BTC (36.9% vs 29.0%). That extra volatility is now largely *idiosyncratic* rather than amplified market beta — i.e. recently DOGE has offered BTC-like directional exposure plus uncompensated noise. Whether that persists is unknown; it is a two-window observation, not an established regime.

**Cross-asset:** DOGE–ZEC correlation +0.39 to +0.48 across windows; DOGE–TRX +0.23 (over the 720-return window the two series share). DOGE is the most crypto-correlated of the three.[^doge-vol]

**Drawdown — the number that matters most:**

- Period high close **$0.46682 on 2024-12-08**.
- Price on 2026-08-05: **$0.07018**.
- **That is −85.0%**, and the maximum drawdown over the window was **−85.2% (2026-08-01)** — i.e. the asset is sitting essentially at its worst point of the entire period studied.
- Over the full window, DOGE is **−23.7%** (2024-01-01 $0.09202 → 2026-08-05 $0.07018) while carrying 90.9% annualized volatility.

Compare: BTC's max drawdown over the same 948-bar window was −53.1%, ZEC's −71.8%.[^doge-vol] **DOGE had the deepest drawdown of the three** despite having neither the highest volatility (ZEC) nor the lowest liquidity (TRX).

## Known failure modes for traders

1. **Treating DOGE as a diversifier.** With correlation to BTC pinned at ~+0.77 in every regime tested, DOGE adds almost no diversification to a portfolio that already holds BTC. It adds volatility, not independence. This is the most common and most costly misuse.
2. **Assuming high beta on the way up.** Beta has compressed to ~1.0 over the trailing 90d. A DOGE position sized as a "leveraged BTC bet" may currently deliver BTC-like upside with DOGE-like downside — the worst of both.
3. **Underestimating the drawdown envelope.** −85% peak-to-trough, and currently at the trough. Position sizing calibrated to 74% annualized volatility will still be wrong-footed by a move of that depth, because the drawdown is a path property, not a variance property.
4. **Modelling DOGE on fundamentals.** There are none to model. Chain-data features will have near-zero predictive power. Strategies that work on DOGE are sentiment, momentum, and flow strategies.
5. **Ignoring the perpetual issuance drag.** ~$369M/year of new supply at current prices (derived), permanent and price-insensitive. Long-horizon holds face a constant headwind.
6. **Reflexivity cuts both ways.** The attention loop that produces vertical rallies produces equally vertical unwinds, and liquidity thins exactly when it is needed.
7. **Confusing declining inflation *rate* with scarcity.** The absolute issuance never falls. Supply is unbounded. A falling percentage is not a supply squeeze.

## For this backtester

**DOGE is now held in the local cache.** `~/dev/solmargintrader/data/DOGE_1d.csv` was fetched 2026-08-05 — 1,890 daily bars, 2021-06-03 to 2026-08-05, 0 non-1d steps. Note the start: Coinbase's DOGE-USD listing begins 2021-06-03, so a request for earlier history is silently truncated rather than refused. ZEC was fetched the same day (2,043 bars from 2021-01-01). The rest of the set is still absent, and TRX cannot be fetched at all (not listed).[^doge-local]

**Coinbase lists DOGE, so this project's fetcher can retrieve it with no code changes.** Verified against the exact API `backtester/core/fetch.py` uses:[^doge-coinbase]

- `GET /products/DOGE-USD` → `{"id":"DOGE-USD", ..., "status":"online", "trading_disabled":false}`
- `GET /products/DOGE-USD/candles?granularity=86400` → returns data. Sample row for 2026-08-04: `[1785801600, 0.06972, 0.07062, 0.07012, 0.07, 93644118.3]`, i.e. `[time, low, high, open, close, volume]` — the non-OHLCV ordering the fetcher's docstring exists to handle.
- Backward pagination retrieved **948 daily bars from 2024-01-01 to 2026-08-05** in 4 requests (3 × 301 rows + 48), consistent with the module's 300-candle cap. History extends further back than tested here.

**Practical notes for wiring it up:**

- Use **`DOGE-USD`** as the `product` string. `DOGE-USDT` also exists and is online, but the USD pair matches the quote convention of the BTC/ETH/SOL series already cached.
- Cache path will be `data/DOGE_1d.csv` per `fetch.py`'s naming (`{asset.upper()}_{interval}.csv`).
- All six Coinbase granularities are available (60s → 86400s), so intraday DOGE bars are retrievable if a higher-frequency study is wanted — subject to the 300-candle-per-request cap making deep 1m history slow to paginate.
- `base_increment` is `0.1` and `quote_increment` is `0.00001`. At ~$0.0702 the price spans only ~7,020 ticks, so **one tick is ~1.4bp** of price. Any strategy whose per-trade edge is finer than ~1.4bp is measuring tick rounding, not alpha. For contrast, ZEC at ~$513 with a `0.01` tick resolves to ~0.2bp — **seven times finer**. This is a real and easily-missed backtest hazard at DOGE's price level and it does not arise for BTC or ETH.

**Analytical caution for cross-asset work.** Because DOGE's correlation to the already-cached BTC series is ~+0.77 and stable, **adding DOGE to a universe that already contains BTC adds much less independent information than it appears to.** Quantified: at r = +0.77, R² ≈ 0.59, so **only ~41% of DOGE's daily variance is independent of BTC** — BTC + DOGE is closer to ~1.4 effective bets than to 2. Any portfolio-level result, walk-forward study, or multiple-testing correction should be adjusted accordingly. Failing to do so will overstate diversification and understate the effective number of independent trials.

## Sources

[^doge-supply]: Dogecoin supply and issuance — 10,000 DOGE per block, no protocol-level max supply (CoinMarketCap renders max supply as ∞), ~5.256B DOGE/yr, ~3.4% inflation in 2026, circulating supply ~148B (early 2026) to ~154.9B (mid-2026). Aggregated from CoinMarketCap, KuCoin research, Margex and LiteFinance supply analyses. Tier-2/3. The per-block reward and the absence of a cap are protocol facts; the circulating-supply figures are point-in-time and decay. verified-as-of: 2026-08-04

[^doge-merge]: Dogecoin–Litecoin merge mining (AuxPoW) — introduced August 2014; shared Scrypt algorithm; hashrate/difficulty rose sharply (~+1500% reported) within a month; Dogecoin–Litecoin hashrate correlation ~0.95; near-all DOGE blocks now merge-mined; hashrate ~2.7–3.4 PH/s mid-2026 (**unverified**); Dogecoin developers publicly dispute the "dependence on Litecoin" framing. Binance Research "Case Study: Merged Mining in Dogecoin & Litecoin" [https://www.binance.com/en/research/analysis/merged-mining](https://www.binance.com/en/research/analysis/merged-mining); CoinDesk (2014-08-04) [https://www.coindesk.com/markets/2014/08/04/dogecoin-to-allow-litecoin-merge-mining-in-network-security-bid](https://www.coindesk.com/markets/2014/08/04/dogecoin-to-allow-litecoin-merge-mining-in-network-security-bid); litecoin.com; Digital Today (developer rebuttal). Tier-2. verified-as-of: 2026-08-04

[^doge-proposal]: Proposal to reduce the Dogecoin block reward to 1,000 DOGE (500M/yr) — GitHub issue #3776 and discussion #3777 on `dogecoin/dogecoin`, [https://github.com/dogecoin/dogecoin/issues/3776](https://github.com/dogecoin/dogecoin/issues/3776). **A community proposal under discussion, not adopted protocol policy.** Tier-1 (source repository) for the existence of the proposal; adoption status UNVERIFIED and presumed not adopted. verified-as-of: 2026-08-04

[^doge-coinbase]: Coinbase listing status — **primary-source verification by direct API call, 2026-08-04.** `api.exchange.coinbase.com/products/DOGE-USD` → `status: online`, `trading_disabled: false`, `base_increment: 0.1`, `quote_increment: 0.00001`. `/products` enumeration returned DOGE-EUR, DOGE-USDT, DOGE-USD, DOGE-GBP, DOGE-BTC, all `online`. `/products/DOGE-USD/candles?granularity=86400` returned data; 948 daily bars retrieved 2024-01-01 → 2026-08-05. `api.coinbase.com/api/v3/brokerage/market/products/DOGE-USD` → live, 24h volume 102,226,401.9 DOGE. Tier-1 (primary). verified-as-of: 2026-08-04

[^doge-venues]: Venue verification by direct public API call, 2026-08-04. OKX `/api/v5/market/ticker?instId=DOGE-USDT` → live, ~$16.04M 24h notional. Kraken `/0/public/Ticker?pair=XDGUSD` → live, ~$1.46M 24h notional. Binance and Bybit geo-restricted from this environment (**unverified**). Tier-1 (primary). verified-as-of: 2026-08-04

[^doge-vol]: Volatility, correlation, beta, drawdown **and all cross-asset comparatives** — **derived** by this reference from Coinbase daily candles for **DOGE-USD, BTC-USD and ZEC-USD** (948 bars each, 2024-01-01 → 2026-08-05) plus **Kraken TRXUSD** daily OHLC (`https://api.kraken.com/0/public/OHLC?pair=TRXUSD&interval=1440`, 721 bars from 2024-08-15), all retrieved 2026-08-05. TRX is sourced from Kraken because **Coinbase does not list it** — see the TRX reference in this directory. DOGE–TRX and any TRX-involving comparative is computed on the 720-return intersection of all four series (2024-08-16 → 2026-08-05); DOGE/BTC/ZEC comparatives use the full 948-bar window. Annualized vol = population stdev of daily log returns × √365. Beta and correlation on aligned daily log returns. Drawdown computed on daily closes from running peak. Reproducible from `api.exchange.coinbase.com/products/{DOGE-USD,BTC-USD,ZEC-USD}/candles` plus the Kraken endpoint above. **Cross-asset turnover figures now come from the single-timestamp pull described in [^turnover-std], not from per-coin snapshots.** verified-as-of: 2026-08-05

[^doge-snapshot]: Price, market cap and 24h volume snapshot — CoinGecko, 2026-08-04, as supplied to this research. Turnover, implied supply, implied inflation rate and annual issuance notional are **derived** from those figures. Cross-checked: Coinbase DOGE-USD close 2026-08-05 was $0.07018 and the retail reference endpoint returned $0.0701, both consistent with the $0.0702 snapshot. verified-as-of: 2026-08-04

[^doge-local]: Local bar cache contents — direct filesystem check of `~/dev/solmargintrader/data/` and read of `~/dev/solmargintrader/backtester/core/fetch.py`. Tier-1 (primary). verified-as-of: 2026-08-04

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
