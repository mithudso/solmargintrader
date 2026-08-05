---
# provenance: skeleton by /dr 2026-08-04; sections completed in-thread after agent-layer failure
name: jupiter-swap-routing-and-orders
hub: trading-and-investing
version: "1.1.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"  # primary Jupiter dev-docs refresh
category: reference
description: >-
  Jupiter's swap/aggregation and order surface on Solana (jup.ag) — router,
  builder API, and the two on-chain order products. Covers price impact vs
  slippage vs minimum-received (the only real guarantee); RTSE order-time
  slippage and what managed execution does NOT promise; the four competing
  routers (Metis, JupiterZ RFQ, Dflow, OKX) and how `payer` narrows them; the
  per-pair platform-fee ladder (0/2/5/10 bps, 50 bps on tokens under 24h); the
  Order -> sign -> Execute flow and why signing is partial; versioned
  transactions and Address Lookup Tables against Solana's 1232-byte limit;
  Trigger limit orders as keeper-executed (a touch is not a fill); Recurring/DCA
  mechanics and per-execution cost; anti-patterns. Educational only — NOT
  financial advice.
keywords:
  - Jupiter swap
  - Jupiter aggregator
  - jup.ag
  - Solana DEX aggregator
  - swap routing
  - split route
  - Jupiter Ultra
  - MEV protection
  - slippage settings
  - price impact
  - minimum received
  - Jupiter Swap API
  - versioned transactions
  - Address Lookup Table
  - Jupiter Trigger
  - limit order Solana
  - keeper
  - Jupiter Recurring
  - DCA
  - Jupiter fees
tags:
  - trading-and-investing
  - solana
  - dex-aggregator
  - defi
  - jupiter
  - order-execution
  - mev
---

# Jupiter Swap, Routing, and On-Chain Orders

> **Educational information only — NOT financial, investment, or tax advice.** On-chain swaps can lose money to price impact, slippage, failed transactions, and adverse selection. Jupiter ships fast: **volatile facts are stamped `verified-as-of: 2026-08-04`** and fee schedules, API endpoints, and product names must be re-checked against the live Jupiter docs before you build on them.

**Scope.** This reference covers only the **swap / aggregation / order** surface of Jupiter. It deliberately does not re-derive:

| For… | Go to |
|---|---|
| Jupiter Perps — trading side (oracle execution, borrow fee, liquidation) | `references/jupiter-perps-trading.md` |
| The JLP pool as a position you hold (LP payoff, LP risk) | `references/jupiter-jlp-pool.md` |
| Priority fees, compute units, transaction landing, Jito bundles, Solana MEV mechanics | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |
| The Solana venue/DEX landscape itself (Orca, Raydium, Meteora, Phoenix) | `references/solana-dex-and-amm-landscape.md` |
| AMM / concentrated-liquidity math, impermanent loss, EVM intent protocols (CoW, UniswapX, 1inch) | `references/defi-and-onchain-trading.md` §2–§4, §7 |

## Contents

1. The Aggregator — How a Route Is Found
2. Route Quality and Its Limits — Price Impact, Slippage, Minimum Received
3. Execution Modes and MEV Protection — What Is and Is Not Guaranteed
4. The Builder API — Order → Sign → Execute
5. Versioned Transactions, Lookup Tables, and the Size Ceiling
6. Trigger / Limit Orders — Keeper-Executed On-Chain Orders
7. Recurring / DCA — Mechanics and Why It Is Not Repeated Market Orders
8. The Fee Model Across Swap, Trigger, and Recurring
9. Anti-Patterns and Failure Modes

---

## 1. The Aggregator — How a Route Is Found

Jupiter is the dominant **DEX aggregator** on Solana — reported at roughly **95% of Solana DEX-aggregator market share**. It is a *routing layer*, not a venue: for spot swaps it holds no liquidity of its own. It scans liquidity across the major Solana DEXs and AMMs — Raydium, Orca, Meteora, Phoenix and **50+ others** — and constructs an execution path.

**It is not one router — it is four competing simultaneously.** Jupiter's docs name **Metis, JupiterZ (RFQ), Dflow, and OKX** as routers that compete on the same order (`verified-as-of: 2026-08-04`). That matters operationally: some request parameters **change which routers are eligible** — notably, supplying `payer` **disables JupiterZ and Dflow**. A parameter you set for convenience can silently shrink the competitive set and worsen your fill.

**Metis**, the classic aggregator router, does three things a naive router does not:

- **Splits one trade across multiple DEXs simultaneously.** Rather than picking a single venue, it sends fractions down several paths at once. This is how it beats any individual pool on size.
- **Routes through intermediate tokens (multi-hop).** A→C can be worse than A→B→C when the direct pool is thin.
- **Adapts to real-time liquidity.** It scans rates and pool health per quote, so the route for the same pair differs minute to minute.

**Two consequences.** First, the route is a *function of current pool state*, not a fixed path — two identical-looking swaps seconds apart can execute completely differently, and that is the router working correctly. Second, Metis optimizes across *available* liquidity; it cannot create depth that does not exist. On a thin pair the best route through four thin pools is still a bad fill. Aggregation solves **cross-venue price discovery**, not aggregate illiquidity.

**Keep the products separate.** The spot router, Perps, lending and the launchpad share a brand, not an architecture. Perps is oracle-priced and peer-to-pool with JLP as counterparty — a completely different risk surface (`jupiter-perps-trading.md`). Conflating them is a common and expensive mistake.

## 2. Route Quality and Its Limits — Price Impact, Slippage, Minimum Received

Three distinct things that get used interchangeably and should not be:

| Term | What it is | Who causes it |
|---|---|---|
| **Price impact** | The move *your own order* causes against the pool curve | You, mechanically — a function of your size vs depth in range |
| **Slippage tolerance** | A limit *you set* on how far execution may deviate before the transaction reverts | You, as a setting |
| **Minimum received** | The hard floor encoded in the transaction | The contract — this is the only real guarantee |

**A quote is a computation against pool state at time *t*; you land at *t+n*.** The gap between quoted and received output is usually not "slippage tolerance being too generous" — it is the pool having changed between quote and landing. On Solana that gap includes leader scheduling and any retry delay (`solana-transaction-execution-and-mev.md`).

**Design around minimum-received, not around the quote.** Treat quoted output as an estimate and minimum-received as the contract. A wide slippage tolerance does not get you a better price; it only widens the band within which a worse fill is still accepted.

Price impact is a function of **depth in range**, not headline TVL — a pool can show large TVL with almost nothing concentrated near the current price (`solana-dex-and-amm-landscape.md` §4).

## 3. Execution Modes and MEV Protection — What Is and Is Not Guaranteed

> **Naming has moved.** "Ultra mode" was the earlier branding. The current docs carry **no standalone Ultra API page** and publish an explicit **Ultra → Meta-Aggregator migration** path. Treat "Ultra" as legacy vocabulary; the behaviour below now lives in the Swap API V2 Meta-Aggregator (`verified-as-of: 2026-08-04`).

**Automatic slippage is a named mechanism, not a vibe.** Jupiter applies **RTSE — the Real-Time Slippage Estimator — at order time**, explicitly "to balance trade success and price protection." That is a genuine trade-off being made on your behalf: looser slippage buys fill probability at the cost of price protection, and tighter does the reverse. Managed slippage plus managed priority fees and routing is the right default for ordinary size, because those are precisely the parameters retail users most often set badly.

**What it does not promise:**

- It is **not** a best-execution warranty. It is automated parameter selection.
- It does **not** create liquidity, and it does not protect you from adverse price movement between quote and fill.
- Automatic priority-fee handling reacts to congestion; it does not exempt you from it.

**On MEV protection specifically:** Solana has no public mempool, so the EVM playbook ("use a private RPC") does not map cleanly — the threat model and the defenses are structurally different. Sandwiching still happens through privileged position in block construction. Treat product-level "MEV protection" as *reduced exposure*, not immunity, and read the mechanism in `solana-transaction-execution-and-mev.md` rather than trusting the label.

Configure manually when you have a reason: unusual size, a specific slippage discipline, or an automated strategy where deterministic behaviour beats adaptive behaviour.

## 4. The Builder API — Order → Sign → Execute

**This surface changed.** The current Swap API V2 flow is the **Meta-Aggregator's three-step Order & Execute**, not the older `/quote` → `/swap` pair. Jupiter publishes an explicit *Ultra → Meta-Aggregator* migration path, and there is **no standalone Ultra API page in the current docs** (`verified-as-of: 2026-08-04`).

| Step | Call | You send | You get back |
|---|---|---|---|
| 1 | **GET `/order`** | `inputMint`, `outputMint`, `amount`, `taker` (wallet) | a **base64 unsigned v0 transaction** plus the quote |
| 2 | *(your client)* | — | **partially** sign the versioned transaction |
| 3 | **POST `/execute`** | `signedTransaction` (base64), `requestId` | status, signature, and detailed in/out amounts |

**Why signing is *partial*.** JupiterZ (RFQ) quotes require an **additional market-maker signature**, which Jupiter adds during `/execute`. A client that fully signs and broadcasts itself breaks that path.

**Read the amount fields carefully.** `/execute` returns `totalInputAmount`, `inputAmountResult`, `outputAmountResult`, and `totalOutputAmount` specifically so you can distinguish **amounts after fees** from **amounts inside the swap route**. Conflating them misstates realized cost — see `onchain-pnl-and-tax-accounting.md`.

**Validity differs by router type**: aggregator routes expire at `lastValidBlockHeight`; RFQ quotes carry an `expireAt` timestamp. Jupiter states plainly these are **"guidelines, not guarantees"** and price can move inside the validity window.

Landing is still your problem — retry policy, `skipPreflight`, blockhash expiry are Solana-level concerns (`~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md`). A correct `/order` response you fail to land is still a failed trade.

## 5. Versioned Transactions, Lookup Tables, and the Size Ceiling

Metis's strength is also its structural constraint. Split, multi-hop routes touch **many accounts**, and a Solana transaction has a hard size limit of **1232 bytes**. A complex route can simply not fit.

**Address Lookup Tables (ALTs) plus versioned transactions are what make these routes viable at all** — ALTs let a transaction reference accounts by compact index instead of full 32-byte pubkeys, which is the difference between a route serializing and not.

If you are building: treat "the optimal route cannot be serialized into a sendable transaction" as a real, expected case, not an edge case. Handle it — fall back to a simpler route rather than failing the trade.

## 6. Trigger / Limit Orders — Keeper-Executed On-Chain Orders

Jupiter's Trigger product sets a buy or sell at a target price that executes automatically when the market reaches it — CEX-style semantics, executed **directly from your wallet with no custodial risk**.

**How it actually works, and why the distinction matters.** There is no matching engine holding your order. An order is placed on-chain, and **keepers** execute it when conditions are met. Therefore:

- Execution depends on a keeper acting. It is neither instantaneous nor guaranteed at the instant your price prints — **a wick through your level may not fill you.**
- At execution it is still a routed swap, subject to whatever liquidity exists at that moment. Your limit price gates *whether* it executes, not *how well*. Jupiter states this outright: **output amounts are not guaranteed**, and "the actual output depends on liquidity and slippage at execution time."
- **Limit Order V2 added privacy features intended to prevent front-running of pending orders** — a real concern, because a visible resting on-chain order is information others can trade against.

**Three V2 mechanics from Jupiter's own docs** (`verified-as-of: 2026-08-04`):

1. **V2 triggers on USD price, not pool rate.** The condition is evaluated against a USD price, then the swap executes at the *current market rate* via Jupiter routing. Your trigger and your fill are two different prices decided at two different moments.
2. **Partial fills are supported** — "orders fill partially for optimal execution prices." Do not model a Trigger order as all-or-nothing; a strategy that assumes a single atomic fill will mis-track inventory.
3. **Stop-loss orders default to 20% slippage (2000 bps).** This is the sharpest trap on the whole surface. A stop-loss is exactly the order you place to *bound* a loss — and its default tolerance permits a fill up to 20% away from the trigger. **Check and tighten this before relying on a stop.** A 20% slippage cap on a stop is not risk control; it is an acknowledgement that the fill could be far worse than the level you chose.

Jupiter's docs do **not** publish a fee figure for Trigger orders, and do not define a formal order-state machine — orders are referred to as open / filled / expired / cancelled without documented transition rules. Treat both as unverified.

Contrast with a true on-chain CLOB (Phoenix/OpenBook), which gives genuine **price-time priority** rather than keeper-triggered execution. Different guarantees — choose deliberately (`solana-dex-and-amm-landscape.md` §4).

## 7. Recurring / DCA — Mechanics and Why It Is Not Repeated Market Orders

Set a total amount, a token pair, and a frequency — **minute, hour, day, week, or month** — and Jupiter executes a swap at each interval through the same aggregation engine.

**What it actually gives you is automation and discipline, not better pricing.** Each execution is an ordinary routed swap at the prevailing price. The differences from manually placing repeated market orders are:

- **Each interval is a separate on-chain transaction** with its own network cost and its own chance of poor execution or failure. High frequency against small notional multiplies fee drag with no offsetting benefit.
- **Every execution is a taxable disposal** when swapping token-to-token. A daily DCA generates ~365 lots per year to track (`references/onchain-pnl-and-tax-accounting.md`).
- Removing the manual step is the actual product — it defeats the behavioural failure of not executing the plan, which is a real edge, just not a pricing one.

## 8. The Fee Model Across Swap, Trigger, and Recurring

Three layers stack on every execution; traders routinely count only one.

1. **Jupiter platform fee — a per-pair basis-point ladder, not a flat rate** (Jupiter developer docs, `verified-as-of: 2026-08-04`):

   | Pair type | Platform fee |
   |---|---|
   | Buying Jupiter tokens (SOL/stable → JUP / JLP / jupSOL); pegged pairs (LST-LST, stable-stable) | **0 bps** |
   | SOL ↔ stable | **2 bps** (0.02%) |
   | LST ↔ stable | **5 bps** (0.05%) |
   | All other pairs | **10 bps** (0.10%) |
   | **New tokens within 24h of creation** | **50 bps (0.50%)** |

   The response separates **total fee (`feeBps`)** from **Jupiter's platform fee (`platformFee.feeBps`)** — additional charges such as gasless-support costs can sit between them, so do not read `feeBps` as the platform's take.

   **The new-token tier is the trap.** Anyone trading launches pays **5× the standard rate**, and it is the single largest Jupiter-side cost on this surface. An earlier version of this reference stated "0–0.1%", which understated the worst case by a factor of five.
2. **Underlying DEX fees** — paid to the pools the route touches; varies by venue and pool type, and on Meteora DLMM rises with volatility (`solana-dex-and-amm-landscape.md` §6). **Often the largest component.**
3. **Solana network cost** — base fee plus priority fee, individually small, **plus the cost of transactions that fail and land nothing.** For anything high-frequency this is first-order, not a rounding error (`grid-trading-strategy.md` §4).

For Trigger and Recurring the same three layers apply *per execution*, which is why frequency is a cost parameter and not just a schedule.

## 9. Anti-Patterns and Failure Modes

1. **Treating the quote as the fill.** It is a computation against pool state you will not execute against. Design around minimum-received.
2. **Widening slippage tolerance to "make trades go through."** It does not improve price; it widens the band in which a worse fill is accepted.
3. **Assuming managed execution is best execution.** RTSE and managed routing/fees automate three parameters well. That is not a warranty, and it does not create liquidity.
3b. **Passing `payer` without realising it narrows routing.** It disables JupiterZ and Dflow — two of the four competing routers — so a convenience parameter can quietly cost you the best quote.
3c. **Assuming the Jupiter fee is ~10 bps.** On a token less than 24 hours old it is **50 bps**. If you trade launches, that is your dominant Jupiter-side cost.
4. **Reading "MEV protection" as immunity.** Reduced exposure, different threat model from EVM, not a guarantee.
5. **Confusing the router with Perps.** Spot router holds no inventory; Perps has JLP as counterparty and a borrow-fee carry model.
6. **Expecting a Trigger order to behave like an exchange limit order.** Keeper-executed, not matching-engine-executed — a touch is not a fill.
7. **Running high-frequency DCA on small notional.** Per-execution network cost and taxable-lot count scale with frequency; the benefit does not.
8. **Ignoring the 1232-byte ceiling when building.** The best route is sometimes not a route you can send.
9. **Reading a good quote on a thin pair as good liquidity.** Aggregation across four thin pools is still thin.

## References

Internal: `references/jupiter-perps-trading.md`, `references/jupiter-jlp-pool.md`, `references/solana-dex-and-amm-landscape.md`, `references/defi-and-onchain-trading.md` §2–§4 §7, `references/onchain-pnl-and-tax-accounting.md`, `references/grid-trading-strategy.md` §4, `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md`.

External — **primary** (Jupiter developer documentation, fetched 2026-08-04):
0a. Jupiter Docs — *Swap: Order & Execute (Meta-Aggregator)*. Platform-fee ladder by pair type, `feeBps` vs `platformFee.feeBps`, the `/order` → sign → `/execute` flow, partial signing for JupiterZ, RTSE, validity semantics, the four competing routers, `payer` routing restriction. https://developers.jup.ag/docs/swap/order-and-execute.md
0b. Jupiter Docs — *Ultra → Meta-Aggregator migration*. Confirms Ultra is superseded. https://developers.jup.ag/docs/swap/migration/ultra-to-meta-aggregator.md
0c. Jupiter Docs — *Trigger API / DCA*. https://developers.jup.ag/docs/trigger/index.md · https://developers.jup.ag/docs/trigger/dca.md

External — secondary (retained for context; superseded where they conflict with the primary docs above):
1. Portals.fi — *Jupiter: How Solana's Leading DEX Aggregator Works*. Metis routing, split and multi-hop paths, `/quote` and `/swap` endpoint semantics, versioned transactions. https://blog.portals.fi/jupiter-how-solanas-leading-dex-aggregator-works/
2. Eco — *Jupiter Aggregator: How Solana's DEX Router Works*. Router role and venue coverage. https://eco.com/support/en/articles/14801182-jupiter-aggregator-how-solana-s-dex-router-works
3. MEXC — *Jupiter Exchange Review 2026*. Ultra-mode parameter handling and product surface. https://www.mexc.com/news/985802
4. BlockchainReporter — *Jupiter Exchange Review 2026*. Aggregator market-share figure; Limit Order V2 front-running protection. https://blockchainreporter.net/exchanges/jupiter/
5. Coinspot.io — *Jupiter Review 2026: Features, Fees, and How It Works*. Fee layering and DCA frequency options. https://coinspot.io/en/reviews/jupiter/

**Source-quality note — refreshed against primary docs 2026-08-04.**

**Primary-sourced** (Jupiter developer documentation, fetched directly): the per-pair platform-fee ladder (0/2/5/10 bps, 50 bps for tokens under 24h); the `feeBps` vs `platformFee.feeBps` distinction; the **Order → sign → Execute** flow and its parameters; partial signing for JupiterZ market-maker co-signature; the four competing routers (Metis, JupiterZ RFQ, Dflow, OKX) and `payer` disabling JupiterZ/Dflow; **RTSE** for order-time slippage; the `lastValidBlockHeight` vs `expireAt` validity split and Jupiter's own "guidelines, not guarantees" wording; the absence of a standalone Ultra API page and the published Ultra → Meta-Aggregator migration.

**What this refresh corrected.** The prior version stated a **"0–0.1% Ultra fee"** — wrong, and wrong in the dangerous direction: the real ceiling is **50 bps (0.50%) on tokens under 24 hours old**, five times the stated maximum. It also documented a **`/quote` → `/swap`** flow that the current Swap API V2 has superseded, and described "Ultra mode" as current product naming.

**Still secondary or unverified**, and carried at lower confidence: the **~95% aggregator-share** figure, the **"50+ venues"** count, and the **0.05–0.30% DEX-fee band** (venue-side, not Jupiter's to publish). Treat all three as perishable and directional only. Trigger/Recurring mechanics are documented by Jupiter at `/docs/trigger/*` but were not fetched page-by-page in this pass — the keeper-execution model is corroborated, the fee specifics for those two products are not.
