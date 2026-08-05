---
name: crypto-coin-intelligence
description: Per-asset intelligence on the largest crypto coins, for someone sizing, backtesting or trading them — not for learning how crypto works. TRIGGER: what drives BTC/ETH/SOL/BNB/XRP/TRX/HYPE/DOGE/ZEC/RAIN; is a coin's market cap real; float, unlocks and concentration; turnover and whether a position can be exited; which venues list an asset and whether its history is long enough to backtest; per-coin volatility, beta and correlation regimes; whether a result on one coin transfers to another. SKIP: how markets, order types or instruments work → trading-and-investing; protocol internals and consensus → blockchain; strategy design, backtest protocol or PBO → trading-and-investing/references/signal-backtest-protocol-and-regime-evidence.md; DeFi mechanics and AMM math → trading-and-investing/references/defi-and-onchain-trading.md.
---

# Crypto coin intelligence

Ten per-asset references, written for a systematic trading project rather than for a reader
learning what a blockchain is. Each spoke answers the questions that decide whether an asset
belongs in a universe at all: what the float really is, whether the market cap is backed by
tradeable supply, who can move it, which venue lists it, how much history exists, and what
its volatility and correlation actually did.

**Snapshot figures are AS OF 2026-08-04 and decay.** Prices, caps and turnover in these
files are dated and will be wrong soon; the structural claims — supply schedules,
concentration, venue availability, failure modes — age far more slowly. Re-pull the numbers
before relying on them.

**Not investment advice.** These are reference documents for research and backtesting.

## Routing

| Spoke | Asset | Read it for |
|---|---|---|
| `references/btc-bitcoin.md` | BTC | Halving schedule, ETF-era market structure, the correlation regime shift |
| `references/eth-ethereum.md` | ETH | Issuance vs burn, and the L2 value-accrual bear case — the central ETH question |
| `references/sol-solana.md` | SOL | Execution reality (per-account fees, dropped-vs-reverted), and what this project has already measured on it |
| `references/bnb-binance-coin.md` | BNB | Burn mechanism, exchange-fortune and regulatory exposure, thin turnover |
| `references/xrp-ripple.md` | XRP | Escrow releases, real float, the litigation history and its resolution |
| `references/trx-tron.md` | TRX | The USDT settlement rail; **not listed on Coinbase — a hard fetch blocker** |
| `references/hype-hyperliquid.md` | HYPE | On-chain CLOB versus Jupiter's oracle-priced pool; HLP versus JLP; the unlock overhang |
| `references/doge-dogecoin.md` | DOGE | Uncapped fixed issuance, merge-mining, and why it is a BTC proxy rather than a diversifier |
| `references/zec-zcash.md` | ZEC | The 2025-26 move, shielded-pool share, delisting risk; **USD-only on Coinbase** |
| `references/rain-rain.md` | RAIN | **Why its market-cap rank should not be believed.** Read before it enters any ranking |

## Five findings that cut across the set

**1. Market-cap rank is not a liquidity ranking, and for one asset it is not even a rank.**
RAIN is placed #14 by CoinGecko, #201 by CoinMarketCap and #16 by DefiLlama — on the same
day, at the same reported cap. Total bid depth within 2% of mid across every venue listing
it is about $294,000 against an $8.6B nominal cap. Rank the universe by turnover and
executable depth, not by cap.

**2. Turnover varies by two orders of magnitude across the top ten.** Roughly 1.8% for BTC,
~1.4% for XRP and TRX, ~0.7% for BNB, ~0.24% for RAIN. A position size that is unremarkable
in BTC is the entire visible book in the thin names, so one cost model across a universe is
wrong by construction.

**3. Listing is not availability, and availability is not sufficiency.** Coinbase does not
list TRX or RAIN at all. It lists HYPE only from 2026-02-05, so a fetch returns about six
months. It has delisted ZEC-BTC and ZEC-USDC, leaving ZEC USD-only. Each of these is a
different constraint and only the first is loud — a short-history file looks exactly like a
long-history one.

**4. Check the product catalogue, not a price endpoint.** Coinbase's v2 reference-price
endpoint still quotes TRX, which is why secondary sources claim Coinbase lists it. It does
not trade it. An availability check built on a price endpoint returns a false positive and
produces a file from a venue that will never fill an order.

**5. A result on one coin transfers less than it appears to.** The project these were
written for measured 25 of 25 configurations positive on BTC daily and 0 of 25 on SOL
hourly, and a top-ranked strategy falling from 1st to 23rd purely by changing timeframe.
DOGE correlates +0.76 to +0.78 with BTC in every window, so testing on both is closer to
testing twice than to testing two things.

## What these files deliberately do not do

They do not rate assets or recommend positions. Where a fact could not be established it is
marked unverified rather than filled in — the RAIN spoke's most useful section is the list of
what could not be confirmed, including an SEC-filed $860M monthly volume claim that the
independent on-chain record puts at $39.41M *cumulative since inception*. That contradiction
is recorded, not resolved.
