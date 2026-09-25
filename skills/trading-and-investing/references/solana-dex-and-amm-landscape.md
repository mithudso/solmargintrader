---
# provenance: authored in-thread 2026-08-04 after three agent-layer failures (see run report)
name: solana-dex-and-amm-landscape
hub: trading-and-investing
version: "1.1.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  The Solana venue layer a trader actually routes through — Raydium (CPMM + CLMM),
  Orca Whirlpools (CLMM), Meteora DLMM (bins + dynamic fees), and on-chain central
  limit order books (Phoenix, OpenBook). Covers what structurally distinguishes each
  pool type, how to pick a venue as a taker, why Solana's cheap compute and parallel
  execution make on-chain CLOBs and bin-based AMMs practical where Ethereum L1 largely
  cannot, why liquidity fragmentation makes aggregation near-mandatory, fee structures
  including volatility-adjusted dynamic fees, and trader-facing failure modes (thin
  pools, one-sided liquidity, pool-vs-oracle divergence). Educational only — NOT
  financial advice.
keywords:
  - Solana DEX
  - Raydium
  - Orca
  - Whirlpools
  - Meteora
  - DLMM
  - Phoenix
  - OpenBook
  - CLMM
  - CPMM
  - on-chain order book
  - liquidity fragmentation
  - dynamic fees
  - pool selection
tags:
  - trading-and-investing
  - solana
  - defi
  - dex
  - market-structure
---

# Solana DEX and AMM Landscape

> **Educational information only — NOT financial or investment advice.** Venue market share, fee
> schedules and pool parameters on Solana change fast. Everything here is stamped
> `verified-as-of: 2026-08-04`; re-verify before acting.

**Scope.** This is the **venue layer** — where liquidity lives and how to choose between pools. It
deliberately does not re-derive:

| For… | Go to |
|---|---|
| Concentrated-liquidity **math** — ticks, virtual reserves, out-of-range positions, x·y=k, impermanent-loss formula | `references/defi-and-onchain-trading.md` §2–§4 |
| Priority fees, compute units, transaction landing, Jito, Solana MEV mechanics | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |
| Jupiter's router, quote/swap API, Trigger and Recurring orders | `references/jupiter-swap-routing-and-orders.md` |
| Jupiter Perps (trading side) | `references/jupiter-perps-trading.md` |
| The JLP pool (LP side) | `references/jupiter-jlp-pool.md` |
| Solana account model, rent, PDAs, Sealevel/SVM | `~/.claude/skills/blockchain/references/solana-account-model-and-state.md`, `solana-sealevel-and-svm.md` |
| EVM intent protocols (CoW, UniswapX, 1inch Fusion) | `references/defi-and-onchain-trading.md` §7 |

## Contents

1. Why Solana's DEX design space differs from Ethereum's
2. The four liquidity models, and what each is actually for
3. The venues
4. Choosing a venue as a taker
5. Fragmentation and why aggregation is near-mandatory
6. Fees
7. Trader-facing failure modes

---

## 1. Why Solana's DEX design space differs from Ethereum's

On Ethereum L1, gas cost per operation forces AMM designs that are cheap to evaluate — a swap must be
a small number of arithmetic steps. That is *why* constant-product and tick-based concentrated
liquidity won there, and why fully on-chain order books largely did not: placing and cancelling
orders is unaffordable when every action is a gas-metered state write.

Solana changes the constraint. Transaction fees are orders of magnitude lower, compute is metered in
compute units rather than priced per storage write in the same way, and Sealevel executes
non-overlapping transactions in parallel because every instruction declares the accounts it touches
up front (`solana-account-model-and-state.md`, `solana-sealevel-and-svm.md`).

Two consequences that shape everything below:

1. **Fully on-chain central limit order books are practical.** Makers can post, amend and cancel at a
   cost that would be prohibitive on L1. This is why Phoenix and OpenBook exist as on-chain books
   rather than as hybrid off-chain-matching designs.
2. **Fine-grained, stateful AMM designs are practical.** Meteora's DLMM maintains discrete liquidity
   *bins* and adjusts fees dynamically with volatility — bookkeeping that is affordable per-swap here.

The trade-off Solana takes in exchange is a different execution model with its own failure surface —
no public mempool, leader-scheduled block production, and transactions that can be *dropped* rather
than reverted. That surface is covered in the blockchain-hub spoke, not here.

## 2. The four liquidity models

| Model | Mechanism | LP job | Best for takers when |
|---|---|---|---|
| **CPMM / standard AMM** | Constant product `x·y=k` across the full price range | Passive; deposit and forget | Long-tail and new pairs; often the only pool that exists |
| **CLMM** (concentrated) | LPs choose a price range; liquidity is dense inside it, zero outside | Active — ranges must be managed | Major pairs, where concentration gives materially better depth per dollar |
| **DLMM** (bins) | Liquidity sits in discrete price **bins**; zero slippage *within* a bin; fees can adjust with volatility | Active, plus bin-shape strategy | Volatile pairs where dynamic fees compensate LPs, and stable pairs where bin granularity is tight |
| **CLOB** (on-chain book) | Real limit orders with price-time priority | Market-making, quoting two-sided | You want a genuine limit order and precise control, not an AMM curve |

The important taker-facing distinction is **not** which is philosophically better — it is where the
depth is for *your* size, in *this* pair, *right now*. That varies pair by pair and changes over time.

## 3. The venues

Solana's DEX ecosystem is **distributed rather than winner-take-all** — unlike Ethereum, where a
single AMM dominates. Reported activity runs on the order of **$2B+ in daily DEX volume across dozens
of venues** as of 2026.

- **Raydium** — offers both a standard AMM and CLMM pools. Generally cited as leading on **raw
  liquidity depth**, and historically significant as the launch venue for a large share of new
  Solana tokens.
- **Orca (Whirlpools)** — Solana's flagship **CLMM**. Commonly described as the most
  capital-efficient concentrated liquidity on the chain for major pairs, and the most approachable
  UI for LPs.
- **Meteora (DLMM)** — **bin-based** liquidity with **dynamic fees that adjust with volatility**. Confirmed against Meteora's own documentation (`verified-as-of: 2026-08-04`): liquidity sits in **discrete price bins**; a swap **entirely inside one bin incurs zero slippage/price impact**, because every token in that bin trades at that bin's single defined price. **Bin step** is the price gap between consecutive bins — smaller step means a more continuous curve, larger step means wider price jumps and higher fee tiers. The **base fee is a function of the base factor (B) and the bin step (s)**, with a **volatility-driven variable fee** ("surge pricing") stacked on top.
  The fastest-growing venue of the group: reported at **over 22% of Solana DEX volume share as of
  early 2025** (CoinGecko, via secondary reporting). Heavily used for volatile and newly-launched
  pairs, where the dynamic fee is doing real work.
- **Phoenix / OpenBook** — **fully on-chain central limit order books**. Price-time priority, real
  limit orders, maker control. Depth is concentrated in a smaller set of pairs than the AMMs, but for
  those pairs it offers execution semantics no AMM can.

**Treat all share and depth figures as perishable.** These move quickly, and secondary sources lag.
Read current depth from an aggregator or the pools themselves before sizing a trade.

## 4. Choosing a venue as a taker

For most retail-size swaps the honest answer is: **route through an aggregator and let it choose**
(§5). Manual venue selection matters when your size is large enough to move a pool, or when you want
order semantics an AMM cannot give you.

Decision order that actually works:

1. **Do you want a limit order with real price control, or immediate execution?** Real limit order →
   CLOB (Phoenix/OpenBook), or an aggregator's trigger-order product. Immediate → AMM route.
2. **Is your size material relative to pool depth?** If your trade is a meaningful fraction of the
   pool, price impact dominates every other consideration. Check depth first; split the order or use
   a venue with a real book.
3. **Major pair or long tail?** Major pairs will usually have deep CLMM/DLMM liquidity. Long-tail
   tokens may only exist in a CPMM pool — in which case the choice is made for you, and the risk is
   thin-pool impact (§7).
4. **Is volatility elevated right now?** DLMM dynamic fees rise with volatility. That is *correct*
   design — it compensates LPs for adverse selection — but as a taker it means your cost is higher
   precisely when you most want to trade. Compare against alternatives rather than assuming a fixed
   fee tier.

**A rule worth internalizing:** for an AMM, price impact is a function of your size against *the
liquidity in range*, not against headline TVL. A pool can show large TVL while having almost nothing
concentrated near the current price. Headline TVL is close to meaningless for execution.

## 5. Fragmentation and why aggregation is near-mandatory

Because no single venue dominates, the same pair's liquidity is spread across Raydium, Orca, Meteora
and the books simultaneously. A trader hitting one venue directly is, in the general case, taking a
worse price than the market offers.

This is why **aggregation is the default on Solana rather than an optimization**: aggregators split
and route orders across venues so users get execution that no individual venue could provide. The
practical upshot is that fragmentation, which would be a serious market-structure defect on a chain
with expensive computation, is largely absorbed by the routing layer here — routing across many
venues is cheap enough to do per-trade.

Two caveats worth holding:

- Aggregation solves *price discovery across venues*. It does not solve thin aggregate liquidity — if
  the total depth is small, splitting the order across four thin pools still moves the price.
- Routing complexity has a cost: multi-hop, multi-venue routes are larger transactions with more
  accounts, more compute, and more ways to fail. See the routing spoke and the transaction-execution
  spoke.

## 6. Fees

Three layers stack on every on-chain swap, and traders routinely model only the first:

1. **Pool/LP fee** — the venue's swap fee, paid to LPs. Fixed-tier on CPMM/CLMM pools; **volatility-
   adjusted on Meteora's DLMM**.
2. **Protocol/aggregator fee** — where applicable.
3. **Network cost** — the base fee plus any **priority fee**, *plus the cost of transactions that
   fail and land nothing*. On a high-frequency strategy this is a first-order cost, not a rounding
   error. Details in `solana-transaction-execution-and-mev.md`.

For any strategy that trades often — a grid especially — layer 3 is the one that quietly decides
viability. `references/grid-trading-strategy.md` §4 treats this directly.

## 7. Trader-facing failure modes

- **Thin pools and headline-TVL illusion.** Depth near the current price is what determines your
  fill, not TVL. Long-tail pairs can show respectable TVL and still have severe impact at modest size.
- **One-sided / stale liquidity.** In a CLMM or DLMM, price can move out of the range where liquidity
  actually sits. The pool still exists; the depth does not. This is the taker-side mirror of the LP's
  out-of-range problem (`defi-and-onchain-trading.md` §3).
- **Pool-vs-oracle divergence.** A pool's price is whatever the last trade made it. When a pool is
  thin, that can diverge sharply from a broader reference price — dangerous both for taking and for
  anything that consumes the pool as a price source. Oracle-priced venues behave differently by
  design (`jupiter-perps-trading.md` §1).
- **LP-vs-taker interest conflict.** Dynamic fees, concentrated ranges and bin shapes exist to protect
  LPs from adverse selection. They work by making your trade more expensive exactly when you are most
  likely to be right. This is not a defect — but do not read "dynamic fee" as a feature for takers.
- **Quote-to-fill drift.** A quote is computed against pool state at time *t*; you land at *t+n*. On a
  fast-moving pair, the difference is real and is not slippage tolerance being generous — it is the
  pool having changed. Covered mechanically in the transaction-execution spoke.

## References

Internal: `references/defi-and-onchain-trading.md` §2–§4 (AMM/CLMM math, impermanent loss),
`references/jupiter-swap-routing-and-orders.md` (routing/aggregation surface),
`references/jupiter-perps-trading.md` (oracle-priced venue contrast),
`references/grid-trading-strategy.md` §4 (fee drag on high-frequency strategies),
`~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` (priority fees,
landing, MEV), `solana-account-model-and-state.md`, `solana-sealevel-and-svm.md`.

External — **primary** (fetched 2026-08-04):
0. Meteora Documentation — *What is DLMM* / *Dynamic Fees* / *DLMM Fee Calculation*. Discrete price bins, zero-slippage-within-bin, bin step, base factor and volatility surge pricing. https://docs.meteora.ag/overview/products/dlmm/what-is-dlmm · https://docs.meteora.ag/product-overview/dlmm-overview/dynamic-fees

External — secondary (venue rankings and share figures; directional only):
1. Coin Bureau — *Top Solana DEX Platforms*. Venue roles and relative positioning. https://coinbureau.com/analysis/top-solana-dex-platforms
2. OpenLiquid — *Best Solana DEXs in 2026: Ranked and Compared*. Venue-by-venue liquidity-model breakdown and daily-volume scale. https://openliquid.io/blog/best-solana-dexs-2026/
3. MadeOnSol — *Solana DEX Comparison — AMM Types, Fees, Features & TVL (2026)*. CPMM / CLMM / DLMM / CLOB taxonomy and price-time priority on the books. https://madeonsol.com/compare-dex
4. Panda Academy — *Raydium vs Orca vs Meteora*. Comparative venue characteristics. https://academy.pandatool.org/en_US/solana/361
5. deBridge — *Best Solana DEXs for Low Fees*. Meteora DLMM dynamic-fee mechanism and the ~22% early-2025 volume-share figure (attributed to CoinGecko). https://debridge.com/learn/guides/best-solana-dexs-for-low-fees/

**Source-quality note — partially refreshed against primary docs 2026-08-04.**

**Primary-sourced:** Meteora's DLMM mechanics — discrete price bins, zero slippage for a swap
contained within one bin, bin step as the inter-bin price gap, and base fee as a function of base
factor and bin step with a volatility-driven variable fee on top (Meteora documentation, fetched
directly).

**Secondary, and treat as directional only:** the venue *rankings* and every **market-share, TVL and
daily-volume figure** — including Meteora's reported ~22% share and the ~$2B/day ecosystem number.
These come from DEX-comparison sites, exchange education pages and wallet blogs, several of which
have a commercial interest in the venues they rank. They are single-sourced, lagging, and were
already dated when published. **Verify any number you intend to act on against the pools themselves
or a live aggregator.**

Structural claims not yet fetched from each venue's own docs — Orca Whirlpools' and Raydium's exact
pool-type mechanics — are corroborated across multiple secondary sources and are stable properties of
those designs, but have not been primary-verified in this pass.
