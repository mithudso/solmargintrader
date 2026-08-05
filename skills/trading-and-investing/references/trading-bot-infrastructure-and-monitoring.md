---
name: trading-bot-infrastructure-and-monitoring
# provenance: built in-thread 2026-08-04 — concept-family-explorer gaps CVS 3.65 + 3.40, clustered
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  Running a strategy as software rather than describing one — the infrastructure
  and monitoring layer between a backtest and a live bot. Covers RPC/data access
  (public vs dedicated endpoints, rate limits, websockets vs polling, why your
  data source is a strategy parameter), state and idempotency (the restart problem,
  reconciling against on-chain truth as the single source of truth), the
  live-vs-backtest divergence checklist, position and P&L monitoring, alerting on
  the things that actually break (silent stalls, partial fills, drift), and
  operational security for a key that can move money. Educational only — NOT
  financial advice.
keywords:
  - trading bot infrastructure
  - RPC endpoint
  - websocket vs polling
  - rate limits
  - bot state management
  - idempotency
  - reconciliation
  - live vs backtest divergence
  - position monitoring
  - portfolio tracking
  - alerting
  - key management
  - hot wallet
  - operational risk
tags:
  - trading-and-investing
  - automation
  - infrastructure
  - monitoring
  - risk
---

# Trading Bot Infrastructure and Monitoring

> **Educational information only — NOT financial, investment, or tax advice.** A bot with a key can
> lose money faster than you can read about it. Nothing here makes an unprofitable strategy profitable;
> it stops an already-profitable one from being destroyed by its plumbing.

**The framing that matters:** a backtest is a pure function over historical data. A live bot is a
**stateful, long-running, adversarial-environment system holding a key that moves money.** Almost
everything that kills live bots is in the gap between those two sentences, not in the strategy.

**Scope.**

| For… | Go to |
|---|---|
| Priority fees, transaction landing, retries, `skipPreflight`, Solana MEV | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |
| Whether your conditional order gets executed at all | `references/solana-execution-agents-keepers-and-rfq.md` |
| Computing realized/unrealized P&L and cost basis correctly | `references/onchain-pnl-and-tax-accounting.md` |
| Backtesting methodology and the fill assumptions that mislead | `references/trading-strategies-and-styles.md` §5; `references/empirical-backtest-findings-log.md` §9 |
| Sampling frequency as a strategy parameter | `references/sampling-frequency-and-bar-aggregation.md` |
| Self-custody key handling and wallet models | `references/self-custody-wallets-and-key-security.md` |

## Contents

1. Data and RPC access
2. State, restarts, and idempotency
3. Live-vs-backtest divergence
4. Monitoring and position tracking
5. Alerting on what actually breaks
6. Operational security
7. Anti-patterns

---

## 1. Data and RPC access

**Your data source is a strategy parameter, not an implementation detail.** Two bots with identical
logic and different endpoints are different strategies.

- **Public vs dedicated endpoints.** Public RPCs are rate-limited, shared, and deprioritised. For
  anything that must act on a schedule, they are a liability — not because they fail loudly, but
  because they degrade quietly under exactly the load that accompanies volatility.
- **Websockets vs polling.** Subscriptions push updates and are lower-latency; polling is simpler and
  more predictable. **Websockets fail silently** — a dropped subscription looks identical to a quiet
  market. Any subscription needs a heartbeat and a reconnect path, or your bot will confidently trade
  on a frozen view of the world.
- **Rate limits shape behaviour.** Being throttled mid-decision is a failure mode you must design
  for, not an error to log.
- **Consistency.** Different endpoints can be at different slots. Reading position from one and price
  from another can produce a decision consistent with neither.

**The rule:** treat data-source degradation as a *first-class strategy state*, not an exception. A bot
that cannot tell "the market is quiet" from "my feed is dead" will eventually act on the wrong one.

## 2. State, restarts, and idempotency

**Every bot restarts.** Deploys, crashes, OOM kills, machine reboots. The question is only whether it
restarts *correctly*.

- **On-chain state is the single source of truth.** Local state is a cache and must be treated as
  possibly wrong. On startup, **reconcile against the chain** before acting — never resume from a
  local file alone.
- **The dangerous window is a submitted-but-unconfirmed transaction.** If a bot dies between submit
  and confirm, the naive restart resubmits, and you get a double order. Idempotency keys, client
  order IDs, or a pre-write intent log that survives the crash are the standard fixes.
- **Reconciliation must be able to say "I don't know."** A bot that resolves ambiguity by assuming the
  optimistic case will eventually double-spend its own position.
- **Grids are especially exposed**, because the whole strategy *is* state — a ladder of resting orders
  plus per-level inventory (`grid-trading-strategy.md`). Restarting a grid without reconstructing which
  levels are filled produces an inventory the strategy does not believe it has.

## 3. Live-vs-backtest divergence

Check these before blaming the strategy:

| Divergence | Cause |
|---|---|
| **Fills you did not get** | Backtest assumed a touch filled; live, queue position or a keeper decided otherwise (`solana-execution-agents-keepers-and-rfq.md`) |
| **Worse prices than modelled** | Slippage, price impact, quote-to-fill drift |
| **Missing trades entirely** | Failed/dropped transactions — **you paid and got nothing**, which most backtests never model |
| **Different timing** | Backtest acts at the bar boundary; live acts whenever the loop and the network allow |
| **Different data** | Backtest on clean historical bars; live on a possibly-degraded feed (§1) |
| **Costs** | Priority fees and failed-transaction waste are absent from most backtests |

**Run the same strategy in paper mode against the live feed before committing capital.** That isolates
infrastructure divergence from strategy error — it is the only way to tell "my strategy is wrong" from
"my plumbing is wrong", and they demand opposite fixes.

## 4. Monitoring and position tracking

**Monitor equity, not trades.** The single most important lesson from this skill family: a grid can log
a 100% win rate while the account falls 37.5% (`grid-trading-strategy.md` §5.3). **Closed-trade P&L is
a biased estimator by construction.** Your dashboard must show **total equity marked to market,
including open inventory**, or it will lie to you in exactly the situation you built it for.

Track, at minimum:

- **Total equity** = cash + positions marked to market.
- **Realized vs unrealized, separately** (`onchain-pnl-and-tax-accounting.md`).
- **Position vs intent** — what the strategy *believes* it holds vs what the chain says. Divergence
  here is the earliest signal of a state bug (§2).
- **Cost attribution** — fees, slippage, failed-transaction waste, borrow/funding. Without this you
  cannot tell an edge decaying from costs rising.
- **Fill rate** — of the orders you placed, how many executed? A falling fill rate is a keeper or
  liquidity problem, not a signal problem.

**On tooling:** third-party portfolio trackers are convenient and are *another* data source that can be
stale, mis-price illiquid assets, or mis-handle your cost basis. Use them for a view; use your own
reconciliation for truth.

## 5. Alerting on what actually breaks

Alert on **absence and divergence**, not just errors. The failures that cost the most are silent.

| Alert | Why |
|---|---|
| **No activity for N intervals** | The single most valuable alert. A crashed or wedged bot produces *no errors at all* |
| **Position ≠ intent** | State bug or missed fill (§2) |
| **Fill rate collapse** | Keeper, liquidity or fee problem |
| **Failed-transaction rate spike** | Fee/congestion problem burning money for nothing |
| **Feed staleness / last-update age** | Distinguishes a quiet market from a dead feed (§1) |
| **Equity drawdown threshold** | The backstop that does not depend on diagnosing the cause |
| **Approaching liquidation** | Leveraged positions, ahead of the fact |

**Include a kill switch, and test it.** A documented, rehearsed way to flatten and halt — and an
untested kill switch should be assumed broken.

## 6. Operational security

A trading bot is **a long-running process holding a key that can move funds**.

- **Hot keys are a standing risk.** Only what the bot needs to operate should be reachable by the
  bot's key; the rest belongs in cold storage it cannot touch.
- **Never commit keys.** Environment or a secret manager, never source control, never logs.
- **Scope permissions** where the venue supports it — trade-only API keys without withdrawal rights,
  and revoke unlimited token approvals you no longer need (`self-custody-wallets-and-key-security.md`).
- **Machine compromise is total compromise.** A key on a box is only as safe as that box.
- **Log deliberately.** Enough to reconstruct decisions; never enough to leak a key or seed.

## 7. Anti-patterns

1. **Monitoring closed-trade P&L instead of equity.** The illusion is measurable and documented (§4).
2. **Trusting local state across a restart** without reconciling on-chain (§2).
3. **Websockets with no heartbeat.** A dead feed reads as a quiet market (§1).
4. **No no-activity alert.** The most common way a bot fails is by silently stopping (§5).
5. **Public RPC for anything time-sensitive** (§1).
6. **No paper-mode run before live capital.** You cannot separate strategy error from plumbing error
   (§3).
7. **Backtest ignoring failed transactions.** You pay for those (§3).
8. **A hot key with more authority than the strategy needs** (§6).
9. **An untested kill switch.** Assume broken until rehearsed (§5).
10. **Treating a portfolio tracker as ground truth** rather than a convenience view (§4).

## References

Internal: `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md`;
`references/solana-execution-agents-keepers-and-rfq.md`;
`references/onchain-pnl-and-tax-accounting.md`; `references/grid-trading-strategy.md` §5.3;
`references/empirical-backtest-findings-log.md` §9;
`references/sampling-frequency-and-bar-aggregation.md`;
`references/self-custody-wallets-and-key-security.md`.

**Source-quality note.** This reference is **practice guidance synthesised from general distributed-
systems and operational-engineering practice** applied to on-chain trading — it is **not sourced from
a specific external authority**, and no external citations are claimed. Two classes of statement to
treat differently: the **cross-referenced claims** (the closed-trade illusion in §4, failed-transaction
cost, keeper non-guarantees) are grounded in measured or primary-sourced material in the linked spokes;
the **operational recommendations** (§1–§3, §5–§6) are conventional engineering judgement, not
empirical findings from this repo. Nothing here has been validated against a live deployment in this
session. Venue-specific mechanics — API key scoping, approval revocation, kill-switch facilities —
**must be read from the venue**, since they vary and change.
