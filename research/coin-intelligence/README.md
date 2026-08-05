---
name: crypto-coin-intelligence
version: "1.2.0"
updated: "2026-08-05"
category: custom
model: claude-sonnet-5
effort: medium
description: >-
  Per-asset intelligence on the largest crypto coins, for someone sizing, backtesting or trading them — not for learning how crypto works. TRIGGER: what drives BTC/ETH/SOL/BNB/XRP/TRX/HYPE/DOGE/ZEC/RAIN; is a coin's market cap real; float, unlocks and concentration; turnover and whether a position can be exited; which venues list an asset and whether its history is long enough to backtest; per-coin volatility, beta and correlation regimes; whether a result on one coin transfers to another. SKIP: how markets, order types or instruments work → trading-and-investing; protocol internals and consensus → blockchain; strategy design, backtest protocol or PBO → trading-and-investing/references/signal-backtest-protocol-and-regime-evidence.md; DeFi mechanics and AMM math → trading-and-investing/references/defi-and-onchain-trading.md.
tags:
  - crypto
  - per-asset-intelligence
  - float-and-unlocks
  - turnover-and-liquidity
  - backtest-universe-selection
related_skills:
  - trading-and-investing
  - blockchain
whenToUse:
  - "Is this coin's market cap real, or is the float wrong?"
  - "Can I actually exit a position this size in TRX / ZEC / RAIN?"
  - "Does Coinbase list HYPE or TRX, and is there enough history to backtest it?"
  - "Does a strategy result on SOL transfer to DOGE, ZEC or BTC?"
  - "What drives ETH's price, and what is the L2 value-accrual bear case?"
triggers:
  - is this coin's market cap real
  - float unlocks and concentration
  - turnover and exit liquidity
  - which venues list this coin
  - does this result transfer across coins
metadata:
  changelog:
    - "2026-08-05 sko iter2 v1.1.0 -> v1.2.0: blind re-audit closed 2 High + 3 Medium. Finding 5's transfer claims were wrong and are now re-verified against research/CROSS-ASSET-TRANSFER.md: EIGHT of 25 singles clear all five assets (not nine) and the correct characterisation is family-negative (none of the eight is from a reversion family; no reversion strategy clears all five) rather than 'all trend or breakout' -- three of the eight are regime-filter, momentum and volume-flow. SOL daily is 13/25, not 14 (the 14 came from a defective results file since deleted). Full per-asset row added (BTC 25, ZEC 24, ETH 18, DOGE 16, SOL daily 13, SOL hourly 0) and SOL hourly is now stated as a timeframe cut, not a sixth asset. Turnover-span decomposition corrected: the nine non-RAIN coins span ~5x with a further ~3x step to RAIN, replacing the backwards 'nearly all of the 15x is RAIN'. Snapshot provenance corrected to the measured 5/5 split (BTC/ETH/SOL/XRP/BNB carry 2026-08-05 pulls; the other five 2026-08-04). SOL routing row now names the cross-asset transfer question its whenToUse promises."
    - "2026-08-05 sko iter1: unversioned -> v1.1.0. Frontmatter now parses under a strict YAML parser (description moved to a >- block scalar; the plain scalar's inline TRIGGER:/SKIP: broke PyYAML/js-yaml and would fail Glean export). Finding 2 corrected: the stated two-orders-of-magnitude turnover spread is ~15x (one order) and the RAIN spoke already refuted that framing; the list now covers all ten coins and resolves BNB against its own spoke (0.76% headline is a denominator artifact, 1.11% on defensible float). AS-OF stamp now honest about the 2026-08-04/05 range. Finding 5 folded in the five-asset transfer matrix and the trend-vs-mean-reversion split. BNB routing row corrected. Four *.ddo-report.md optimizer scratch files moved out of references/. Added missing manifest keys."
---

# Crypto coin intelligence

Ten per-asset references, written for a systematic trading project rather than for a reader
learning what a blockchain is. Each spoke answers the questions that decide whether an asset
belongs in a universe at all: what the float really is, whether the market cap is backed by
tradeable supply, who can move it, which venue lists it, how much history exists, and what
its volatility and correlation actually did.

**Snapshot figures are AS OF 2026-08-04 or 2026-08-05 and decay.** Both stamps appear across
the set: five spokes (BTC, ETH, SOL, XRP, BNB) carry a CoinGecko pull timestamped 2026-08-05
and the other five a 2026-08-04 pull, while only the SOL spoke labels its heading 2026-08-05.
Each spoke stamps its own figures, and some carried corpus facts are older still, back to
2026-06-16. Prices, caps and turnover will be wrong soon; the structural claims — supply
schedules, concentration, venue availability, failure modes — age far more slowly. Re-pull the
numbers before relying on them.

**Not investment advice.** These are reference documents for research and backtesting.

## Routing

| Spoke | Asset | Read it for |
|---|---|---|
| `references/btc-bitcoin.md` | BTC | Halving schedule, ETF-era market structure, the correlation regime shift |
| `references/eth-ethereum.md` | ETH | Issuance vs burn, and the L2 value-accrual bear case — the central ETH question |
| `references/sol-solana.md` | SOL | Execution reality (per-account fees, dropped-vs-reverted), what this project measured on it, and whether those results transfer to other coins |
| `references/bnb-binance-coin.md` | BNB | Burn mechanism, exchange-fortune and regulatory exposure, and why its thin headline turnover is a denominator artifact |
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

**2. Turnover spans 14.4× across the ten coins here: one order of magnitude, not the two this
set is sometimes said to span.** 24h volume ÷ market cap, **all ten from a single CoinGecko
`/coins/markets` call at 2026-08-05T02:15:22Z** — DOGE **3.44%**, SOL **3.32%**, ETH **3.05%**,
HYPE **2.52%**, ZEC **2.30%**, BTC **1.78%**, TRX **1.45%**, XRP **1.37%**, BNB **0.73%**, RAIN
**0.24%**. The nine non-RAIN coins span about 4.9× on their own, with a further 3.2× step down to
RAIN. BNB's 0.73% is a denominator artifact: its spoke recomputes 1.11% once the burn address and
bridge contract come out of the float, which puts it beside BTC. A position size that is
unremarkable in BTC is the entire visible book in the thin names, so one cost model across a
universe is wrong by construction.

**One timestamp, on purpose.** Turnover has a moving numerator *and* a moving denominator, so
figures pulled at different times cannot be ranked against each other. Mixing them produced a
real error here: the SOL spoke claimed the highest turnover of the ten at 3.69%, from a per-asset
`/coins/solana` call, when the single-timestamp pull puts **DOGE ahead**. Regenerate the table and
verify all ten spokes against it with `python3 research/turnover_table.py [--check]` in
`solmargintrader`.

**3. Listing is not availability, and availability is not sufficiency.** Coinbase does not
list TRX or RAIN at all. It lists HYPE only from 2026-02-05, so a fetch returns about six
months. It has delisted ZEC-BTC and ZEC-USDC, leaving ZEC USD-only. Each of these is a
different constraint and only the first is loud — a short-history file looks exactly like a
long-history one.

**4. Check the product catalogue, not a price endpoint.** Coinbase's v2 reference-price
endpoint still quotes TRX, which is why secondary sources claim Coinbase lists it. It does
not trade it. An availability check built on a price endpoint returns a false positive and
produces a file from a venue that will never fill an order.

**5. A result on one coin transfers less than it appears to, and what survives is a class of
strategy rather than a coin.** The project these were written for ran the same 25 singles
across five assets, plus an hourly cut on SOL: BTC 25 of 25 positive, ZEC 24, ETH 18, DOGE 16,
SOL daily 13, SOL hourly 0, with a top-ranked configuration falling from 1st to 23rd on the
timeframe change alone. Eight of the 25 cleared all five assets, not one of them from a
reversion family, and no reversion strategy cleared all five. Carrying the five SOL-tuned top
configurations to DOGE and ZEC unchanged degraded all ten and improved none. DOGE correlates
+0.76 to +0.78 with BTC in every window, so testing on both is closer to testing twice than to
testing two things.

## What these files deliberately do not do

They do not rate assets or recommend positions. Where a fact could not be established it is
marked unverified rather than filled in — the RAIN spoke's most useful section is the list of
what could not be confirmed, including an SEC-filed $860M monthly volume claim that the
independent on-chain record puts at $39.41M *cumulative since inception*. That contradiction
is recorded, not resolved.

---

## About this copy

Mirrors the user-level skill `crypto-coin-intelligence`
(`~/.claude/skills/crypto-coin-intelligence/`) so the research this repo's findings rest on travels
with the repo. This file is that skill's `SKILL.md`; the ten spokes sit beside it as flat files,
matching the `references/<name>.md` paths in the routing table above. The skill is canonical.

```bash
cp ~/.claude/skills/crypto-coin-intelligence/SKILL.md research/coin-intelligence/README.md
cp ~/.claude/skills/crypto-coin-intelligence/references/*.md research/coin-intelligence/
python3 research/turnover_table.py --check    # all ten turnover figures must agree
```
