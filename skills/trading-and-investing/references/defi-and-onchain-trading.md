---
# provenance: built by /dr 2026-06-21 — do NOT hand-edit the frontmatter block
# 2026-08-04: frontmatter edited under an explicit split instruction (size-cap remediation); see changelog
name: defi-and-onchain-trading
hub: trading-and-investing
version: "1.1.0"
updated: "2026-08-04"
verified-as-of: "2026-06-21"
category: reference
description: >-
  On-chain/decentralized trading for a retail participant: DEX/AMM mechanics
  (Uniswap v2/v3/v4 constant-product and concentrated liquidity), impermanent
  loss math, LP economics, price impact and slippage, MEV sandwich attacks and
  how to defend against them (private mempools, slippage tolerance, intent
  protocols), intent-based order flow (CoW Protocol, UniswapX, 1inch Fusion),
  perpetual DEXs (GMX, dYdX, Hyperliquid) vs CEX perps, cross-chain bridges
  (mechanics, risk tiers, selection). Self-custody wallets and key security
  (MetaMask, Rabby, Ledger, Trezor, seed and token-approval hygiene, ERC-4337)
  now live in self-custody-wallets-and-key-security.md. Educational only — NOT financial advice.
keywords:
  - DeFi
  - decentralized exchange
  - DEX
  - AMM
  - Uniswap
  - impermanent loss
  - liquidity pool
  - MEV
  - sandwich attack
  - CoW Protocol
  - UniswapX
  - perpetual DEX
  - GMX
  - dYdX
  - Hyperliquid
  - cross-chain bridge
  - on-chain trading
metadata:
  changelog:
    - "2026-08-04 v1.0.0->v1.1.0 SPLIT (was ~10,734 est. tokens, 1.07x over the ~10k cap) — §10 Self-Custody Wallets moved verbatim to references/self-custody-wallets-and-key-security.md, keeping its §10 numbering and footnotes ^29-^34. Pointer table left at the §10 slot; `self-custody wallet` keyword and `wallets` tag moved to the new file. Nothing condensed or deleted."
tags:
  - defi
  - trading-and-investing
  - amm
  - dex
  - mev
  - bridges
  - perp-dex
  - intent-trading
---

# DeFi and On-Chain Trading

> **Educational information only — NOT financial, investment, or legal advice, and NOT a recommendation to buy, sell, or hold anything.** DeFi protocols carry **smart contract risk**, **liquidity risk**, **oracle risk**, and **bridge risk** — you can lose your entire balance. Protocols change rapidly; verify current facts with official docs before acting. **Volatile facts stamped `verified-as-of: 2026-06-21`** — re-verify before use.

## Contents

1. [Foundations: How DEXs Differ from CEXs](#1-foundations-how-dexs-differ-from-cexs)
2. [AMM Mechanics: Constant Product Formula (Uniswap v2)](#2-amm-mechanics-constant-product-formula-uniswap-v2)
3. [Concentrated Liquidity (Uniswap v3)](#3-concentrated-liquidity-uniswap-v3)
4. [Liquidity Provision Economics and Impermanent Loss](#4-liquidity-provision-economics-and-impermanent-loss)
5. [Price Impact and Slippage](#5-price-impact-and-slippage)
6. [MEV: Sandwich Attacks and Defense](#6-mev-sandwich-attacks-and-defense)
7. [Intent-Based Order Flow (CoW Protocol, UniswapX, 1inch Fusion)](#7-intent-based-order-flow-cow-protocol-uniswapx-1inch-fusion)
8. [Perpetual DEXs: GMX, dYdX, Hyperliquid](#8-perpetual-dexs-gmx-dydx-hyperliquid)
9. [Cross-Chain Bridges](#9-cross-chain-bridges)
10. [Self-Custody Wallets — moved](#10-self-custody-wallets--see-the-dedicated-reference)
11. [References](#references)

---

## 1. Foundations: How DEXs Differ from CEXs

A **centralized exchange (CEX)** — Coinbase, Binance, Kraken — holds your assets, runs a private order book on its own servers, and matches buyers with sellers internally. A **decentralized exchange (DEX)** runs on a public blockchain: every trade is a transaction, every rule is code in a smart contract, and you hold your own keys throughout.

| Dimension | CEX | DEX (AMM) |
|---|---|---|
| Custody | Exchange holds assets | User holds assets in own wallet |
| Order matching | Private server order book | On-chain smart contract (AMM formula) |
| KYC | Required | Usually none |
| Settlement | Internal ledger (instant) | On-chain transaction (seconds to minutes) |
| Trading hours | 24/7 | 24/7 |
| Counterparty risk | Exchange default/hack | Smart contract bug; bridge risk |
| Gas costs | None (internal) | User pays gas per transaction |
| MEV exposure | None (private) | Exposed via public mempool |

**Scope:** this reference covers the on-chain side — DEXs, AMMs, and on-chain perpetuals. Centralized crypto trading is in `references/crypto-and-digital-asset-trading.md`.

---

## 2. AMM Mechanics: Constant Product Formula (Uniswap v2)

### The x·y = k Invariant

Uniswap v2 (and most AMMs) replace a traditional order book with a **constant product market maker**. A liquidity pool holds two tokens — call them X and Y. The protocol enforces the invariant:

```
x · y = k
```

where `x` and `y` are the reserve quantities and `k` is constant after each swap (ignoring fees). Every trade moves along this curve.[^1][^2]

**Price discovery:** the current spot price of X in terms of Y is simply `y / x` — the ratio of reserves. There is no order book; price is determined entirely by reserve ratios.

### How a Swap Executes

A trader sends Δx tokens of X and receives Δy tokens of Y such that `k` is preserved:

```
(x + Δx)(y − Δy) = k = x · y
⟹ Δy = y − (x · y) / (x + Δx)
     = y · Δx / (x + Δx)
```

The trader receives *less* than the spot price would imply — the denominator grows. This is **price impact**: larger trades relative to pool size receive progressively worse execution.

**Worked example.** Pool: 100 ETH / 100,000 USDC. Spot price: 1,000 USDC/ETH. Trader sells 10 ETH:

```
Δy = 100,000 · 10 / (100 + 10) = 9,090.9 USDC
Effective price: 9,090.9 / 10 = 909.09 USDC/ETH
Price impact: (1,000 − 909.09) / 1,000 ≈ 9.1%
```

A 10% trade-to-pool-size ratio produces ~9.1% price impact.[^3]

### Trading Fees

Uniswap v2 applies a **0.3% fee** deducted from the input before the formula runs. The input seen by the formula is `Δx · (1 − 0.003)`. This means `k` grows fractionally with each trade — that growth is LP income, accumulated in the reserves and claimable proportionally by LPs.[^1]

Uniswap v3 and v4 introduced multiple fee tiers: 0.01% (stablecoins), 0.05% (correlated assets), 0.3% (standard), 1% (exotic pairs). Fee tier selection affects LP economics significantly.

### Uniswap v4 (2024)

Uniswap v4 introduced **hooks** — smart contracts that can execute custom logic before/after swaps or liquidity changes — and **singleton architecture** (all pools in one contract). This enables dynamic fees, on-chain limit orders, and other extensions without forking the core AMM math. The x·y=k formula is unchanged at the core.[^4] `verified-as-of: 2026-06-21`

---

## 3. Concentrated Liquidity (Uniswap v3)

### The v2 Capital Efficiency Problem

In v2, LP capital is deployed uniformly across `(0, ∞)`. For a stablecoin pair (USDC/DAI always near $1.00), roughly **99.5%** of the LP's capital sits unused outside any realistic trading range. That capital earns zero fees.

### Ticks and Virtual Reserves

Uniswap v3 partitions the price axis into discrete **ticks**, each representing a 0.01% (1 basis point) price increment: `price_i = 1.0001^i`. LPs choose a lower tick `a` and upper tick `b`, concentrating their capital into `[P_a, P_b]`.[^5][^6]

Inside the range, v3 behaves as if it were a v2 pool with **virtual reserves** — much larger than the actual tokens deposited. The math replaces the real reserves with:

```
x_virtual = L / √P
y_virtual = L · √P
```

where `L` is the liquidity parameter (a function of the actual tokens deposited and the range chosen). Capital efficiency scales inversely with range width — a narrow range provides much more liquidity per dollar.

**Efficiency gains (Uniswap's figures, `verified-as-of: 2026-06-21`):**[^5]

| LP range | Capital efficiency vs v2 |
|---|---|
| Full range [0, ∞) | 1× (identical to v2) |
| ETH ±50% range | ~4× |
| Stablecoin ±0.5% range | ~4,000× |

### Out-of-Range Positions

When price exits the LP's chosen range:
- The position converts to **100% of the underperforming asset** (e.g., ETH if price fell below the range).
- **Fee accrual stops** — the LP is no longer providing active liquidity.
- The position is equivalent to a **limit order** that has fully filled into the weaker asset.

This creates an active management burden: LPs must monitor and reposition ranges, or use "auto-compounding" protocols (e.g., Arrakis Finance, Gamma) that rebalance on their behalf.

### v3 vs v2: LP Risk Profile

v3 concentrated LPs face:
- **Higher IL exposure per dollar**: the position behaves more like holding the two assets at specific ratios — narrower ranges amplify impermanent loss when price moves.
- **Range-drift risk**: active management is needed; a static v3 LP in a volatile pool will quickly go out of range.
- **Higher fee income per dollar (when in range)**: this partially offsets the IL and management cost.

---

## 4. Liquidity Provision Economics and Impermanent Loss

### What Is Impermanent Loss?

**Impermanent loss (IL)** — more accurately called **divergence loss** — is the difference between the value of an LP position and the value of simply holding the same tokens outside the pool.[^7][^8]

It arises because the AMM rebalances continuously: as one token appreciates, the pool automatically sells it and buys more of the depreciating token. The LP ends up holding relatively less of the winning asset and more of the losing one versus a passive hold.

### The IL Formula

Let `r` = the ratio of the new price to the entry price (for one asset, denominated in the other). Then:

```
IL(r) = 2√r / (1 + r) − 1
```

This is symmetric: a 2× move and a 0.5× move produce the same IL magnitude.

**IL table** (widely reproduced and confirmed by 5+ independent sources):[^7][^8][^9]

| Price change (r) | Impermanent Loss |
|---|---|
| 1× (no change) | 0% |
| 1.25× (+25%) | −0.6% |
| 1.5× (+50%) | −2.0% |
| 2× (2×) | −5.7% |
| 3× (3×) | −13.4% |
| 5× (5×) | −25.5% |
| 10× (10×) | −42.5% |

**"Impermanent" is a misnomer.** IL only reverses if price returns to the exact entry ratio before withdrawal. If you withdraw at a different price, the loss is permanent. "Divergence loss" is more accurate.

### Worked Example

Entry: ETH = $1,000. Deposit 1 ETH + 1,000 USDC. Pool value: $2,000.

After ETH doubles to $2,000:
- **Hold:** 1 ETH + 1,000 USDC = $3,000
- **LP position:** the pool rebalances to ~0.707 ETH + ~1,414 USDC = $2,828
- **IL:** $2,828 / $3,000 − 1 = **−5.7%** (matches the formula: 2√2/(1+2)−1 ≈ −5.7%)

The LP earned fees on top of this — those must exceed the $172 divergence loss for the LP position to outperform the hold.

### Fee Income vs. IL: The Trade-Off

IL is offset by trading fee income. Whether LPs profit depends on:
- **Volume / TVL ratio**: high-volume pools in proportion to locked liquidity generate more fee income.
- **Volatility**: more price movement → more IL, but also often more volume.
- **Range tightness (v3)**: tighter ranges → more fees per dollar when in range, but faster IL accumulation and more active management.

**Research finding (contested, `verified-as-of: 2026-06-21`):** A 2022 academic study found ~50% of v3 LPs were net-negative after IL; Uniswap has disputed this methodology. Both findings directionally agree that IL is material in volatile pools; precise numbers should not be quoted as forward-looking statistics.[^9]

---

## 5. Price Impact and Slippage

### Price Impact

**Price impact** is how much your trade moves the pool's price. For the constant product AMM:

```
Price impact ≈ 2 × (trade size / pool TVL)   [Paradigm rule of thumb]
```

This approximation holds for small trades; large trades diverge upward as the curve steepens.[^3]

**Implication:** a $10,000 swap in a $100,000 pool has ~20% price impact. The same swap in a $10,000,000 pool has ~0.2% impact. Larger pools absorb trades with less slippage.

### Slippage Tolerance

Every DEX frontend asks for a **slippage tolerance** — the maximum price deviation (%) you will accept. If the actual fill price is worse, the transaction reverts on-chain.

```
Min received = expected output × (1 − slippage_tolerance%)
```

Setting tolerance too high → susceptible to sandwich attacks (MEV bots exploit the gap). Setting too low → transaction fails frequently in volatile markets.

**Recommended defaults (practitioner guidelines; not empirically derived):**

| Scenario | Slippage Tolerance |
|---|---|
| Stablecoin pairs (deep pools) | 0.01%–0.05% |
| ETH/USDC stable conditions | 0.3%–0.5% |
| Major pairs, volatile market | 0.5%–1.0% |
| Low-cap / memecoin pools | Use intent-based DEX; see §7 |

If a transaction fails, increment tolerance by 0.1% at a time — never jump to 2%+ (gives bots maximum room to sandwich).

### Gas Costs

Every on-chain swap requires gas (ETH on Ethereum L1, or the L2 equivalent). Gas costs:
- **Ethereum L1:** variable; $5–$50+ per swap during congestion. L1 swaps are impractical for small trades.
- **Ethereum L2s (Arbitrum, Optimism, Base):** $0.01–$0.50 per swap. Most retail DeFi activity has migrated to L2s.
- **Gas is paid in ETH** — you must hold ETH (or the native token on other L1s) regardless of what you're trading.

---

## 6. MEV: Sandwich Attacks and Defense

### What Is MEV?

**MEV (Maximal Extractable Value)** is value extracted by block producers or specialized bots by reordering, inserting, or censoring transactions. From a retail trader's perspective, the most impactful form is the **sandwich attack**.[^10]

> **Note:** MEV *protocol economics* (PBS, validator incentives, Flashbots infrastructure) are covered in `blockchain-economics` hub. This reference covers only the **trader-facing mechanics** — what happens to your swap and how to protect it.

### Sandwich Attack Mechanics

1. **Detection:** A bot monitors the public mempool (pending but unconfirmed transactions). It parses your swap: which pool, which tokens, trade size, and — critically — your **slippage tolerance** (the maximum fill-price deviation you will accept).
2. **Front-run:** The bot submits a buy transaction with a higher gas price, ensuring it executes *before* yours. This pushes the pool price up to just within your slippage window.
3. **Your trade executes:** At the now-inflated price, receiving fewer tokens than expected.
4. **Back-run:** The bot immediately sells into the liquidity your trade added, pocketing the spread.

**What the bot optimizes:** "Can I move price within this user's slippage tolerance, profit after gas, and exit cleanly?" Solved in milliseconds.

**Real cost (2024 data, `verified-as-of: 2026-06-21`):**[^10][^11]

| Swap size | Estimated loss range |
|---|---|
| $5,000 | $15–$40 |
| $50,000 | $150–$400 |
| $500,000 | $1,500–$4,000 |

The loss is silent — your swap succeeds, but you receive fewer tokens than you should have. Aggregate cost: ~$60M/year across Ethereum, ~60,000–90,000 attacks/month.

### Defense 1: Slippage Tolerance

Slippage tolerance **limits but does not prevent** sandwich attacks. A bot can still extract up to your full tolerance. On a $100k trade at 0.5% tolerance, up to $500 is extractable. Slippage tolerance must be paired with structural defenses.

### Defense 2: Private RPC Endpoints / Protected Mempools

Instead of broadcasting your transaction to the public mempool where every bot can see it, private RPCs route directly to block builders who have agreed not to frontrun or sandwich. Bots can only backrun (arbitrage after your trade settles) — and some services share that profit with you.[^12][^13]

**MEV Blocker (recommended, `verified-as-of: 2026-06-21`):**
- RPC: `https://rpc.mevblocker.io/fast`
- Endpoints: `/fast` (best UX), `/fullprivacy` (maximum protection), `/noreverts`
- Rebates 90% of backrun profits back to the user in the same block

**Flashbots Protect:**
- RPC: `https://rpc.flashbots.net/fast`
- MetaMask setup: Add Network → enter RPC URL
- ~25% block inclusion per block (slightly slower than public mempool)
- No failed-transaction gas cost

**Benchmark study (273 transactions, Dec 2024–Jan 2025):[^13]**

| RPC | Inclusion speed | Success rate | Price outcome |
|---|---|---|---|
| MEV Blocker | 1.34 blocks (fastest) | ~84% | +21 bp better than public |
| Flashbots Protect | Fast | ~84% | Baseline |
| Blink | Slower | ~84% | Worse |
| Merkle | Slowest | ~70% | Worse |

MEV Blocker was the best performer across all metrics in this study.

**Setup in MetaMask (Ethereum mainnet):**
1. Settings → Networks → Add Network
2. RPC URL: `https://rpc.mevblocker.io/fast`, Chain ID: 1, Symbol: ETH
3. Set as default for mainnet swaps

**Warning:** Do not switch RPCs while a transaction is pending — MetaMask may rebroadcast to the public mempool.

### Defense 3: Intent-Based Protocols

The strongest protection: **no public mempool transaction at all**. Intent-based protocols (CoW Protocol, UniswapX, 1inch Fusion — see §7) submit only a signed intent off-chain; solvers/fillers compete to fill it privately. Sandwich attacks are architecturally impossible when no transaction is broadcast until after execution.[^14] Trade-off: 15–60 second execution delay.

### Defense 4: Trade Splitting and Timing

- **Split large swaps:** break $50k+ swaps into 3–4 smaller transactions 10–15 minutes apart. Each smaller trade creates less price impact → may fall below bots' gas-cost breakeven threshold.
- **Stablecoin pairs with tight slippage (0.01%–0.05%)** can make sandwich attacks gas-negative even in low-fee environments.

### L2 MEV Caveat

MEV has not disappeared on L2s — it has evolved. Arbitrum uses FCFS sequencing but proximity to the sequencer enables latency-based frontrunning. Base/Optimism permit sequencer-level reordering. Use the same private RPC or intent-based defenses on L2s. `verified-as-of: 2026-06-21`

---

## 7. Intent-Based Order Flow (CoW Protocol, UniswapX, 1inch Fusion)

All three protocols share the same core shift: instead of signing and broadcasting an AMM swap transaction yourself, you sign an **intent** — a statement of what you want — and a competitive network of third parties (solvers, fillers, resolvers) executes it on your behalf. This eliminates mempool exposure and often delivers better prices through solver competition.

**Aggregate scale (`verified-as-of: 2026-06-21`):** Intent-based protocols processed $10.5B in January 2025, approximately 12% of total Ethereum DEX volume.[^15]

### CoW Protocol (Coincidence of Wants)

**How it works:** CoW collects orders into a **batch auction** every ~15–30 seconds. Multiple solver algorithms compete to settle the entire batch optimally. The key innovation: when multiple orders in the same batch are complementary (one user wants ETH for DAI, another wants DAI for ETH), they can be matched peer-to-peer — **no AMM needed, no pool fees paid**. Unmatched orders route through AMMs.[^16]

**Uniform clearing price:** all orders in the same batch receive the same price, set at or better than the worst-acceptable limit price. This structurally eliminates sandwich attacks — there is no "pending transaction to front-run."

**For the user:**
- No gas payment (solvers pay gas, baked into pricing)
- MEV protection is strongest of the three (batch settlement + no public pending tx)
- Available on Ethereum, Gnosis Chain, Arbitrum, Base
- Slowest to fill (must wait for batch window)

### UniswapX

**How it works:** Each order is auctioned via a **Dutch auction** — the offered price starts favorable and decays linearly over ~30–60 seconds until a **filler** takes the order.[^17]

**For the user:**
- Gas-free (fillers pay gas)
- Typically faster fills than CoW (~10–30 seconds)
- Cross-chain swaps supported natively
- 80% of UniswapX swaps settled at or better than the initial quoted price (Uniswap's figure; `verified-as-of: 2026-06-21`)
- No peer-to-peer matching (orders always route to external liquidity)

### 1inch Fusion

**How it works:** A staked resolver whitelist (~10 entities) competes via Dutch auction on individual orders. Resolvers absorb gas costs.[^18]

**Key differences from CoW:** no batch peer-to-peer matching; orders always route to external liquidity. Key difference from classic 1inch aggregator mode: gas-free, MEV-protected, but fill not guaranteed (order expires if no resolver accepts it).

**For the user:**
- Fast fills (faster than CoW in most conditions)
- No gas cost
- Available via the 1inch dApp in "Fusion" mode (default in many jurisdictions)

### Comparison

| Protocol | Execution Model | Approx. Fill Time | MEV Protection | Gas for User |
|---|---|---|---|---|
| CoW Protocol | Batch auction, peer-to-peer first | 15–60s | Strongest (no mempool tx) | None |
| UniswapX | Per-order Dutch auction | 10–30s | Strong (private fillers) | None |
| 1inch Fusion | Dutch auction, resolver whitelist | 5–20s | Strong (private resolvers) | None |

**Trade-off:** all intent-based protocols introduce execution latency. During that window, price can move against you. For very volatile markets or small swaps, a direct AMM swap with low slippage + MEV Blocker RPC may execute faster with acceptable risk.

---

## 8. Perpetual DEXs: GMX, dYdX, Hyperliquid

Perpetual futures (perps) — no-expiry derivative contracts that track an asset's spot price via **funding rates** — are now available on decentralized venues. The three dominant approaches differ fundamentally in architecture.

> **CEX perps vs DEX perps:** CEX perps (Binance, OKX, Bybit) run private order books with off-chain matching. DEX perps bring the same leveraged exposure on-chain with varying degrees of decentralization. See `references/crypto-and-digital-asset-trading.md` for CEX perp mechanics (funding rates, liquidation, margin types).

### GMX (Pool-Based, Peer-to-Pool)

**Model:** Traders open leveraged positions against **GM/GLV liquidity pools** — the pool is the counterparty to all trades. No order book.[^19][^20]

**Oracle pricing:** GMX uses Chainlink oracles to determine mark price, not its own order flow. This means:
- Effectively zero slippage for small trades (priced at oracle, not AMM curve)
- No price manipulation via large trades
- Oracle dependency risk: if oracle fails or is manipulated, positions are marked incorrectly

**Price impact for large trades:** GMX V2 introduced price impact based on open-interest imbalance — large positions that increase one-sided OI pay a skew fee; positions that reduce imbalance receive a rebate. "Zero slippage" applies only for balanced OI; large one-sided trades are penalized. `verified-as-of: 2026-06-21`

**Leverage:** up to 100× on major pairs (GMX V2, `verified-as-of: 2026-06-21`)

**For LPs (GM pool depositors):** LPs earn ~63% of protocol fees but act as the counterparty — when traders profit, LPs lose, and vice versa. LP returns are highly path-dependent on trader performance aggregate, not just market direction.

**GMX V1 (GLP) is deprecated — all trading now on V2 (GM/GLV pools).** `verified-as-of: 2026-06-21`

### dYdX (Order Book, Dedicated L1)

**Model:** dYdX v4 is a **standalone Cosmos SDK L1 chain** running a traditional **central limit order book (CLOB)** — the same familiar model as CEX order books.[^21]

**Matching architecture:** Orders are matched off-chain in-memory at each validator node using price-time priority. Only trade fills are committed on-chain. This means:
- No gas on order submission or cancellation — gas only on fills
- Users can place precise limit orders at any price
- Familiar CEX-like UX: order book depth visible, bids/asks, partial fills

**Margin:** isolated or cross-margin; USDC collateral

**Taker fee:** 0.05% → 0.025% tiered by volume (`verified-as-of: 2026-06-21`)

**Friction for new users:** funding requires bridging USDC via IBC/Noble — not a one-click experience from an Ethereum wallet

**Decentralization trade-off:** the in-memory matching is controlled by validator nodes, not fully on-chain. More decentralized than a CEX but less than a fully on-chain order book.

### Hyperliquid (Fully On-Chain CLOB)

**Model:** The only major venue running a **fully on-chain CLOB** — all orders, matches, and fills settle on its purpose-built L1 (HyperCore).[^22][^23]

**Performance:** HyperBFT consensus delivers ~200ms finality and 100,000+ operations/second (OPS) — CEX-competitive latency on a decentralized system. `verified-as-of: 2026-06-21`

**HLP Vault:** The protocol-owned HLP (Hyperliquidity Provider) vault actively market-makes across 130+ perpetual markets, earning spreads, funding income, and liquidation fees. 100% of profits distributed to USDC depositors. Historical stable-period APY ~17%; 450% lifetime since May 2023 (highly variable, not a forward guarantee; verify current rates). `verified-as-of: 2026-06-21`

**Fees:** Taker 0.035%–0.045% (cheaper than dYdX and GMX at most volumes). Gas-free on HyperCore.

**Volume (`verified-as-of: 2026-06-21`):** $180B+ 30-day volume as of April 2026 — more than all other on-chain derivatives venues combined.[^22]

### Comparison Table

| Venue | Architecture | Slippage | Leverage | Gas | Decentralization |
|---|---|---|---|---|---|
| GMX (V2) | Peer-to-pool (oracle price) | Low for small trades; OI-skew fee for large | Up to 100× | ETH (Arbitrum/Avalanche) | Smart contracts on L2/L1 |
| dYdX (v4) | Order book (Cosmos L1) | Order book spread | Up to 20× | Gas on fills only | Validator network |
| Hyperliquid | Order book (HyperCore L1) | Order book spread | Up to 50× | Gas-free | HyperBFT validators |

---

## 9. Cross-Chain Bridges

### Bridge Architectures

Three models dominate cross-chain asset transfers:[^24][^25]

**Lock-and-Mint:** Tokens are locked in a custody contract on the source chain. Validators confirm the deposit and a destination contract mints a wrapped representation (e.g., wETH). The wrapped token is a 1:1 IOU backed by locked supply. Fragments liquidity via non-native wrapped tokens the user often must swap out of.

**Burn-and-Mint:** Tokens are burned on the source; the same native tokens are re-issued on the destination. Most capital-efficient — no liquidity pools needed — but only possible when the bridge operator holds official minting rights. **Circle CCTP** uses this for USDC: burn on source, mint native USDC on destination. 13–20 minute settlement, gas-only cost, no bridge wrapper.

**Lock-and-Unlock (Liquidity Pool / Intent Model):** Pre-funded liquidity pools sit on both chains. User locks on source; bridge releases from destination pool. Intent-based variants (Across) use a relayer to front destination funds instantly, then recover via the canonical bridge later (the 7-day wait is the relayer's problem, not the user's).

**Canonical vs. Third-Party Bridges:**

Every major L2 ships with an official **canonical bridge** (Arbitrum Bridge, Optimism Portal, Base Bridge) that is part of the rollup's security model — same trust as the chain itself. Canonical bridges are the most secure option but:
- Optimistic rollup withdrawals take **7 days** (the fraud proof window — see below)
- L2-to-L2 via canonical paths routes L2 → L1 → L2: two sets of L1 gas costs

Third-party bridges (Across, Stargate, Hop, Li.Fi) solve the speed/cost problem but introduce additional smart contract and trust risks.

### The 7-Day Optimistic Rollup Withdrawal

Optimistic rollups (Arbitrum, Optimism, Base) use fraud proofs. The 7-day delay gives honest validators time to challenge a fraudulent state root: "Seven days gives enough time for honest validators to pop out of the woodwork."[^26]

**ZK-rollups** (zkSync, Starknet, Linea) use validity proofs instead — withdrawals finalize once the proof is verified on Ethereum: typically minutes to a few hours.

**Fast withdrawal services** (Across, Hop, Stargate) bypass the 7-day delay by having a relayer front destination-chain funds immediately. The relayer waits the 7 days and is repaid via the canonical bridge. The user's fee compensates the relayer's capital lockup.

### Bridge Security: The Highest-Risk DeFi Infrastructure

Bridge hacks have accounted for **over 69% of funds stolen in DeFi since 2022** — cumulative losses exceeding $2.8B.[^27][^28]

**Major incidents:**

| Bridge | Date | Loss | Root Cause |
|---|---|---|---|
| Ronin (Axie Infinity) | March 2022 | $625M | Compromised validator keys (5 of 9) |
| Wormhole | February 2022 | $320M | Signature verification bypass |
| Nomad | August 2022 | $190M | Upgrade made all messages appear pre-validated |

**Why bridges concentrate risk:** bridges hold or control enormous locked value in a single contract. A bug in the bridge contract — even a post-audit upgrade — can drain the entire locked supply instantly. Wrapped tokens (e.g., Wormhole wETH) are only as valuable as the security of the locking contract.

**Risk factors for traders:**
- **Smart contract risk:** all three hacked bridges above had been audited. An audit is a point-in-time review.
- **Validator centralization:** Ronin required only 5 of 9 validators; the attacker controlled 5.
- **Admin key risk:** many bridges have admin keys that can pause/change contracts.
- **Wrapped token risk:** if the bridge is exploited, wrapped tokens backed by locked liquidity are worthless.

### Practical Bridge Selection

**Decision framework:**

1. **Moving to an L2 for the first time (small amount)?** Use the canonical bridge. Slowest and gas-costly, but maximum security.
2. **Moving between two L2s frequently?** Use a third-party bridge or aggregator (canonical L2→L1→L2 is impractical).
3. **Moving USDC specifically?** Use Circle CCTP directly (or a bridge that routes through it). Native USDC, no wrapper.
4. **Need speed (under 60 seconds)?** Across (intent-based, 15–60 seconds); Stargate 2–4 min; Hop 3–6 min.
5. **Unsure which bridge?** Use an aggregator: **Bungee** (Socket-powered, integrated into MetaMask Bridge) or **Li.Fi / Jumper** (32 bridges, 60+ chains).

| Bridge | Type | Speed | Best For |
|---|---|---|---|
| Canonical (Arbitrum/Optimism) | Lock-and-unlock | 7 days (withdrawal to L1) | Maximum security |
| Across | Intent/relayer | 15–60 seconds | Speed |
| Stargate | Liquidity pool | 2–4 minutes | High-volume, stablecoins |
| Hop | AMM + canonical | 3–6 minutes | L2-to-L2 ETH/stablecoins |
| Circle CCTP | Burn-and-mint | 13–20 minutes | Native USDC only |

**Verification before bridging:** check **L2Beat** (`l2beat.com/scaling/risk`) for a bridge's trust model, admin key exposure, and security stage.

---

## 10. Self-Custody Wallets — see the dedicated reference

The wallet and key-custody material now lives in **`references/self-custody-wallets-and-key-security.md`**, keeping its §10 numbering and footnote labels. Everything in this file assumes you already hold your own keys; that reference is where the holding is covered.

| What is there | Which claim here it supports |
|---|---|
| Hot wallets — MetaMask vs Rabby, BIP-39 seed derivation, pre-transaction simulation | §1 "user holds assets in own wallet" — the mechanism that makes a DEX non-custodial |
| Hardware wallets — Ledger Secure Element vs Trezor open source, blind-signing risk | §6 and §9 — you approve MEV-protected swaps and bridge transactions from these devices |
| Seed-phrase practice, metal backup, phishing | The seed-phrase risk named in Cross-Cutting Notes below |
| Token-approval management and revocation (Revoke.cash) | §9 — protocol and bridge approvals persist indefinitely after you stop using a protocol |
| Safe multisig and ERC-4337 account abstraction (paymasters, batching, social recovery) | §7 gas abstraction — intent protocols and AA solve overlapping UX problems |

---

## Cross-Cutting Notes

**The DeFi onboarding stack:** CEX or fiat on-ramp → self-custody wallet (`references/self-custody-wallets-and-key-security.md`) → bridge to L2 → DEX swap or LP. Each step has distinct risk: exchange counterparty risk at the on-ramp, seed phrase risk in the wallet, bridge smart contract risk in transit, and protocol/IL risk in the pool. Compartmentalize each step.

**L2 vs L1 for DeFi:** Ethereum mainnet gas costs ($5–$50+/swap) make small DeFi trades impractical on L1. Most retail DeFi activity has migrated to L2s (Arbitrum, Base, Optimism). Same protocols, same AMM math, ~100× cheaper gas. Use a bridge (see §9) to move assets from L1 to L2.

**DeFi + tax:** On-chain swaps are taxable events in the US (each swap = a disposition of the sold asset). LPs adding/removing liquidity may be taxable events. Token rewards (yield farming, staking) may be ordinary income when received. This spoke does not cover tax detail — see `references/trading-regulation-compliance-and-taxes.md` for the trader tax reference.

**Smart contract risk disclaimer:** all DeFi protocols carry smart contract risk regardless of audit status. The largest hacks in DeFi history (Ronin $625M, Wormhole $320M) occurred in audited contracts. Never deposit more than you can afford to lose; start with small amounts on any new protocol.

---

## References

[^1]: Uniswap. "Uniswap v2 Core." Uniswap Docs. https://docs.uniswap.org/contracts/v2/concepts/core-concepts/swaps — The x·y=k invariant, fee mechanics, and LP share math.

[^2]: Hayden Adams, Noah Zinsmeister, Dan Robinson. "Uniswap v2 Core." Uniswap Whitepaper, 2020. https://uniswap.org/whitepaper.pdf — Primary source for the constant product formula and v2 protocol design.

[^3]: Dan Robinson. "Price Impact." Paradigm Research. https://www.paradigm.xyz/2021/04/understanding-automated-market-makers — Price impact approximation (2× trade/TVL rule of thumb) and AMM curve analysis.

[^4]: Uniswap. "Uniswap v4 Overview." Uniswap Docs, 2024. https://docs.uniswap.org/contracts/v4/overview — Hooks architecture, singleton design, and v4 protocol changes.

[^5]: Hayden Adams et al. "Uniswap v3 Core." Uniswap Whitepaper, 2021. https://uniswap.org/whitepaper-v3.pdf — Concentrated liquidity, tick architecture, and capital efficiency calculations.

[^6]: Uniswap. "Concentrated Liquidity." Uniswap v3 Docs. https://docs.uniswap.org/concepts/protocol/concentrated-liquidity — LP range mechanics, virtual reserves, out-of-range behavior.

[^7]: Pintail. "Uniswap: A Good Deal for Liquidity Providers?" Medium, 2019. https://pintail.medium.com/uniswap-a-good-deal-for-liquidity-providers-104c0b6816f2 — Original impermanent loss analysis with the IL formula and quantification.

[^8]: CoinGecko Learn. "What Is Impermanent Loss?" https://www.coingecko.com/learn/impermanent-loss — Widely reproduced IL table; independent confirmation of formula and examples.

[^9]: Loesch, Stefan, et al. "Impermanent Loss in Uniswap v3." arXiv:2111.09192, 2021. https://arxiv.org/abs/2111.09192 — Academic study finding ~50% of v3 LPs net-negative after IL; note Uniswap disputed methodology.

[^10]: CoinMarketCap Academy. "What Are Sandwich Attacks in DeFi?" https://coinmarketcap.com/academy/article/what-are-sandwich-attacks-in-defi-and-how-can-you-avoid-them — Sandwich attack mechanics and estimated cost ranges for retail traders.

[^11]: arXiv:2511.15245. "MEV Extraction in DeFi: Patterns and Quantification." 2025. https://arxiv.org/html/2511.15245v1 — Empirical quantification of sandwich attack frequency (~60k–90k/month) and aggregate loss.

[^12]: Flashbots. "Flashbots Protect: Quick Start." Flashbots Documentation. https://docs.flashbots.net/flashbots-protect/quick-start — RPC configuration, block inclusion mechanics, and MEV rebate details.

[^13]: arXiv:2505.19708. "A Comparative Evaluation of MEV-Protection RPC Endpoints." 2025. https://arxiv.org/html/2505.19708v1 — Controlled benchmark of MEV Blocker, Flashbots Protect, Blink, and Merkle across 273 transactions.

[^14]: MEV Blocker. "MEV Blocker." https://mevblocker.io/ — Endpoint documentation, rebate mechanism, and integration guide.

[^15]: Dune Analytics / DeFiLlama. "DEX Volume by Protocol." https://defillama.com/dexs — Intent-based protocol volume data; $10.5B January 2025 figure.

[^16]: CoW Protocol. "How CoW Protocol Works." CoW Protocol Docs. https://docs.cow.fi/overview/introduction — Batch auction mechanics, solver competition, coincidence-of-wants matching.

[^17]: Uniswap. "UniswapX Overview." Uniswap Developer Docs. https://docs.uniswap.org/contracts/uniswapx/overview — Dutch auction mechanism, filler competition, cross-chain swaps, gas abstraction.

[^18]: 1inch. "1inch Fusion Mode." 1inch Help Center. https://help.1inch.io/en/articles/6783812-what-is-fusion-mode — Resolver model, staked whitelist, and differences from classic aggregator mode.

[^19]: GMX. "GMX V2 Documentation." GMX Docs. https://docs.gmx.io/docs/trading/v2 — GM/GLV pool mechanics, oracle pricing, price impact and OI skew fees, leverage limits.

[^20]: Coin Bureau. "GMX Review 2026." https://coinbureau.com/review/gmx — Independent review covering GMX V2 architecture, LP economics, and risk factors; confirms V1 deprecation.

[^21]: dYdX. "dYdX v4 Architecture." dYdX Documentation. https://docs.dydx.exchange/ — Cosmos L1 design, in-memory order book matching, settlement architecture, fee tiers.

[^22]: Hyperliquid. "HLP Vault Overview." Hyperliquid Docs. https://hyperliquid.gitbook.io/hyperliquid-docs/trading/hlp — HyperBFT consensus specs, HLP vault mechanics, fee structure, and volume data.

[^23]: Pantera Capital. "Hyperliquid: The On-Chain Order Book." Pantera Research, 2025. https://panteracapital.com/blog/hyperliquid — Independent analysis of Hyperliquid's architecture and competitive positioning.

[^24]: Chainlink. "What Is a Cross-Chain Bridge?" Chainlink Education Hub. https://chain.link/education-hub/cross-chain-bridge — Lock-and-mint, burn-and-mint, and liquidity pool bridge architectures.

[^25]: L2Beat. "Bridges Risk Analysis." https://l2beat.com/scaling/risk — Trust model classification (trust-minimized / external validation / under review) for all major bridges.

[^26]: Kelvin Fichter. "Why Is the Optimistic Rollup Challenge Period 7 Days?" 2022. https://kelvinfichter.com/pages/thoughts/challenge-periods/ — Canonical explanation of the 7-day window from an Optimism core developer.

[^27]: Yellow Research. "Cross-Chain Bridge Exploits and Security Risks 2026." https://yellow.com/research/cross-chain-bridge-exploits-security-risks-2026 — Aggregate hack statistics; 69% of DeFi losses from bridges.

[^28]: Google Cloud / Mandiant. "Dissecting the Nomad Bridge Hack." https://cloud.google.com/blog/topics/threat-intelligence/dissecting-nomad-bridge-hack — Technical root cause of the $190M Nomad exploit.

