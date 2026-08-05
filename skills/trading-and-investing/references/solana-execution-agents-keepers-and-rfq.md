---
name: solana-execution-agents-keepers-and-rfq
# provenance: built in-thread 2026-08-04 — concept-family-explorer round-1 gaps CVS 4.05 + 3.40, clustered
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  Who actually executes your order on Solana when you do not. Covers the keeper
  model (off-chain agents that watch conditions and submit the transaction) and
  where it appears — Jupiter Perps request/fulfill, Trigger limit orders, Recurring
  DCA, liquidations; the economics that decide whether a keeper shows up for YOUR
  order; RFQ / market-maker order flow (JupiterZ, Dflow) and the partial-signing
  requirement it imposes; how RFQ differs from AMM routing and from a CLOB; the
  liquidator as an adversarial keeper; and the failure modes — no keeper, late
  keeper, keeper-vs-liquidation races, and parameters that silently disable
  routers. Educational only — NOT financial advice.
keywords:
  - keeper
  - keeper network
  - off-chain execution agent
  - crank
  - liquidator
  - RFQ
  - request for quote
  - JupiterZ
  - Dflow
  - market maker
  - partial signing
  - request fulfill
  - conditional order execution
  - Jito
tags:
  - trading-and-investing
  - solana
  - defi
  - execution
  - market-structure
---

# Solana Execution Agents — Keepers and RFQ

> **Educational information only — NOT financial, investment, or tax advice.**

A blockchain cannot act on its own. Nothing on Solana wakes up and decides your stop was hit. **Every
conditional action — a limit order, a DCA instalment, a liquidation, a perp fill — requires some
off-chain party to notice the condition and pay to submit a transaction.** Who that party is, and
whether they are motivated to act on *your* order specifically, determines whether your order works.

**Scope.**

| For… | Go to |
|---|---|
| Jupiter's Trigger and Recurring products, and the swap API surface | `references/jupiter-swap-routing-and-orders.md` §4, §6, §7 |
| Jupiter Perps request/fulfill and liquidation mechanics | `references/jupiter-perps-trading.md` §1, §3 |
| Priority fees, transaction landing, Jito bundles, Solana MEV | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |
| The venues an RFQ competes against | `references/solana-dex-and-amm-landscape.md` |
| Oracle prices that trigger many keeper actions | `references/solana-oracles-pyth-switchboard.md` |

## Contents

1. The keeper model
2. Keeper economics — will one show up for *your* order?
3. Where keepers appear on Solana
4. RFQ and market-maker order flow
5. Liquidators — the adversarial keeper
6. Failure modes
7. Anti-patterns

---

## 1. The keeper model

A **keeper** (also *crank*, *bot*, *executor*) is an off-chain agent that:

1. watches on-chain state and/or an oracle for a condition,
2. constructs a transaction when the condition is met,
3. **pays the fee** to submit it, and
4. is compensated — by protocol reward, fee share, or the profit in the action itself.

This is a **permissionless, incentive-driven** design, and both halves matter. Permissionless means
anyone can run one, so there is no single point of failure. Incentive-driven means **keepers act when
it pays them to**, not when it would help you.

**The consequence stated plainly:** an on-chain conditional order is a *standing invitation* for
someone to execute it, not a guarantee that anyone will.

## 2. Keeper economics — will one show up for *your* order?

A keeper executes when `expected reward > cost + risk`. Break that down and you can predict which
orders get neglected:

| Factor | Pushes toward execution | Pushes toward neglect |
|---|---|---|
| **Order size** | Large — reward scales with notional | Small — reward may not clear the fee |
| **Reward design** | Explicit protocol fee, or profitable liquidation | Nominal or no reward |
| **Congestion** | Cheap blockspace | Priority fees spike; marginal orders stop clearing |
| **Competition** | Many keepers → fast execution | Few or one → single-operator dependency |
| **Certainty** | Deterministic payoff | Race risk — losers pay fees for nothing |

**Two asymmetries worth internalising.**

- **Small orders are structurally disadvantaged.** If executing costs more than it earns, a rational
  keeper skips it. Your dust limit order may never fill *even when the price condition is met*.
- **Congestion is correlated with the moments you care about.** Volatility drives both the conditions
  that trigger your order and the priority-fee spike that makes executing it less attractive. **Keeper
  reliability is worst exactly when you need it most** — the same correlated-failure logic as
  `solana-transaction-execution-and-mev.md`.

## 3. Where keepers appear on Solana

| Surface | What the keeper does | Documented behaviour |
|---|---|---|
| **Jupiter Perps** | Fulfils a two-step request/fulfill flow — you submit a request, a keeper executes it | The request→fill gap is real; a move beyond `priceSlippage` **cancels** rather than filling worse (`jupiter-perps-trading.md` §1) |
| **Jupiter Trigger** (limit orders) | Watches the price condition and executes the swap | Jupiter: *"When an order triggers, Jupiter handles the swap: conversion, routing, and execution."* Output amounts are **not guaranteed**; V2 triggers on USD price and executes at the market rate at that moment |
| **Jupiter Recurring / DCA** | Submits each scheduled instalment | Each interval is a separate transaction with its own cost and its own chance of poor execution |
| **Lending liquidations** | Repays undercollateralised debt, seizes collateral at a discount | The discount *is* the incentive (§5) |
| **Perp liquidations** | Closes positions past maintenance margin | Competitive and latency-sensitive |

**The pattern across all of them:** your condition being met is **necessary but not sufficient**. A
price touch is not a fill.

## 4. RFQ and market-maker order flow

**RFQ (request-for-quote)** inverts the AMM model. Instead of executing against a pool curve, you ask
market makers to quote your specific trade, and one fills it from their own inventory.

Jupiter's meta-aggregator runs **four routers competing on the same order — Metis, JupiterZ (RFQ),
Dflow, and OKX** (`verified-as-of: 2026-08-04`). JupiterZ is the RFQ path.

**Two documented mechanics with direct trader consequences:**

1. **RFQ requires partial signing.** JupiterZ quotes need **an additional market-maker signature**,
   added during `/execute`. A client that fully signs and broadcasts itself **breaks the RFQ path**
   entirely (`jupiter-swap-routing-and-orders.md` §4).
2. **Some parameters silently disable routers.** Supplying `payer` **disables JupiterZ and Dflow** —
   two of the four competitors. A convenience parameter can shrink your competitive set without any
   error being raised.

**How RFQ differs from the alternatives:**

| | Price formation | Counterparty | Slippage on size |
|---|---|---|---|
| **AMM** | Deterministic curve | The pool | Mechanical price impact |
| **CLOB** | Price-time priority | Resting orders | Walks the book |
| **RFQ** | Quoted by a market maker | That market maker | Quoted for *your* size — often better on large trades |

**The honest trade-off.** RFQ can beat pool execution on size because a market maker prices your trade
holistically instead of dragging you along a curve. In exchange you accept a **discretionary
counterparty**: they choose whether to quote, and they price in what they infer about your flow. RFQ
quotes also carry their own validity semantics — an `expireAt` timestamp rather than the aggregator
path's `lastValidBlockHeight`.

## 5. Liquidators — the adversarial keeper

A liquidator is a keeper whose reward comes **out of your position**. The structure is deliberate:
protocols pay a liquidation bonus precisely so that someone is always motivated to close bad debt
quickly. Solvency depends on liquidators being fast and numerous.

Two implications for a trader:

- **Liquidation is competitive and therefore fast.** Do not model it as a slow or forgiving process.
- **Your stop-loss and a liquidator are racing.** Jupiter states there is **no FIFO ordering** — a
  TP/SL transaction and a liquidation can land in the same block and "the outcome cannot be
  guaranteed" (`jupiter-perps-trading.md` §1). **Your protective order can lose the race to the thing
  it was placed to prevent.**

## 6. Failure modes

1. **No keeper.** Reward below cost → the order sits unexecuted with the condition met (§2).
2. **Late keeper.** Executed, but after the price moved. Your trigger gated *whether*, not *how well*.
3. **Congestion coupling.** Keeper reliability degrades exactly when volatility spikes (§2).
4. **Stop-vs-liquidation race.** No ordering guarantee (§5).
5. **Silently narrowed routing.** A parameter disables RFQ paths; you get a worse fill with no error.
6. **Broken RFQ integration.** Fully signing instead of partially signing kills the JupiterZ path.
7. **Single-operator dependency.** A "permissionless" keeper set with one real operator is a
   centralised dependency wearing decentralised language. **Check how many keepers actually run**, not
   whether the design permits many.
8. **Oracle-triggered cascades.** Many keeper actions key off an oracle, so an oracle move can trigger
   many keepers simultaneously — correlated action into contended blockspace
   (`solana-oracles-pyth-switchboard.md` §5).

## 7. Anti-patterns

1. **Treating an on-chain conditional order as a guarantee.** It is an invitation with an incentive
   attached (§1).
2. **Placing small conditional orders and assuming they behave like large ones.** Below the economic
   threshold they may never execute (§2).
3. **Assuming a price touch fills you.** Necessary, not sufficient (§3).
4. **Modelling liquidation as slow.** It is competitive and fast by design (§5).
5. **Relying on a stop to bound a leveraged loss without knowing the ordering rules.** No FIFO
   guarantee (§5).
6. **Passing convenience parameters without checking their routing side effects** (§4).
7. **Fully signing an RFQ transaction.** Breaks the market-maker co-signature (§4).
8. **Reading "permissionless" as "redundant"** without counting live operators (§6.7).

## References

Internal: `references/jupiter-swap-routing-and-orders.md` §4, §6, §7;
`references/jupiter-perps-trading.md` §1, §3; `references/solana-oracles-pyth-switchboard.md`;
`references/solana-dex-and-amm-landscape.md`;
`~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md`.

External — **primary** (Jupiter developer documentation, fetched 2026-08-04):
1. *Swap: Order & Execute* — the four competing routers, JupiterZ partial signing and market-maker
   co-signature, `payer` disabling JupiterZ/Dflow, `expireAt` vs `lastValidBlockHeight` validity. https://developers.jup.ag/docs/swap/order-and-execute.md
2. *Trigger API* — "Jupiter handles the swap: conversion, routing, and execution"; output not
   guaranteed; V2 USD-price triggers; partial fills. https://developers.jup.ag/docs/trigger/index.md

**Source-quality note.** The **Jupiter-specific mechanics** above are primary-sourced. The **general
keeper-economics framing** in §2 — the reward-vs-cost threshold, small-order disadvantage, and the
congestion/volatility correlation — is **reasoned from the mechanics, not quoted from a source**; it
is a model for predicting behaviour, and it has not been empirically measured here. Jupiter's docs
**reference "the keeper" without documenting keeper identity, count, or mechanics**, so operator
concentration (§6.7) is a question this reference raises rather than answers — **verify live operator
counts yourself before depending on any keeper-executed order.**

**This was checked, not assumed** (`verified-as-of: 2026-08-04`): a refresh pass against Jupiter's
developer documentation found **no perps-API keeper page** (`/docs/perp-api/` returns 404) and **no
keeper section in the published `llms.txt` documentation index**, which lists Swap, Trigger, Pricing
and Rate Limits only. So the gap is in the vendor's documentation, not in this reference's research —
**a verified negative.** If keeper mechanics matter to your risk model, that information is not
publicly documented and must be established empirically by observing on-chain execution. No claim here is made about
liquidator bonus sizes or specific protocols' reward parameters; those are per-protocol and must be
read from the protocol.
