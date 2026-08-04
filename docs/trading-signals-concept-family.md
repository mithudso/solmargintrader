# Trading Signals → Signal Providers → jup.ag API/Webhook Integration

**Concept-family map.** As-of **2026-08-04**. Scope: the conceptual space around
automated trading signals and their execution on Jupiter (jup.ag) on Solana.
This is a *map*, not an implementation plan, and not financial advice.

Facts about Jupiter APIs were verified against live `developers.jup.ag`;
Solana/Helius facts against `docs.helius.dev`, `solana.com/docs`, and
`github.com/rpcpool/yellowstone-grpc`. Items marked **UNVERIFIED** were not
confirmed by a primary source — treat them as open questions, not knowledge.

---

## 0. Three corrections that reshape the map

Anything written about Jupiter's developer surface before ~2026 is likely stale.
Three corrections matter enough to state before the taxonomy:

1. **Ultra API is deprecated**, superseded by **Swap V2**
   (`api.jup.ag/swap/v2`). Migration guide: `/docs/swap/migration/ultra-to-order`.
   "Swap v6" does not appear in current docs at all.
2. **`lite-api.jup.ag` is being retired**; base URL is now `api.jup.ag` for
   every plan tier, keyless included. A separate **Recurring/DCA API**
   (`recurring/v1`) is Unmaintained — folded into **Trigger v2**.
3. **Jupiter offers no webhooks, event streams, or push notifications** for
   fills or orders. Fill detection is polling. This single fact determines the
   whole shape of axis 4 below.

---

## 1. Parent domain and siblings

**Parent domain:** algorithmic/systematic trading — the discipline of encoding a
trading decision as a rule and executing it without a human in the loop.

**Where "signals" sit in it:** a signal is the *decision* artifact — a
timestamped assertion that an instrument should be entered, exited, or sized
differently. Everything else in this map is either producing that artifact,
transporting it, or acting on it.

**Sibling concepts** (same level of abstraction, often confused with signals):

| Sibling | Distinction from a signal |
|---|---|
| **Strategy** | The whole rule system; a signal is one of its outputs. |
| **Alpha / factor** | A statistical edge; a signal is its discretized form. |
| **Order** | The exchange-facing instruction; a signal precedes and may not produce one. |
| **Alert** | A signal with no execution intent — human notification only. |
| **Indicator** | An input to signal generation, not a signal itself. |
| **Position / target weight** | State, versus the signal's delta. |
| **Copy-trade event** | A signal derived from another account's realized action. |

**Adjacent fields worth borrowing from:** event-driven systems design
(idempotency, exactly-once vs at-least-once), market microstructure (adverse
selection, price impact), and reliability engineering (retries, backpressure).

---

## 2. Axis A — Signal production

### 2.1 By generation method
- **Rule/indicator-based** — moving-average crossovers, RSI/MACD thresholds,
  breakout and range rules. Cheap to build, easy to overfit.
- **On-chain-flow-derived** — new-pool detection, whale-wallet transfers, LP
  add/remove, mint authority changes, holder-concentration shifts. Native to
  Solana and unavailable on centralized venues.
- **Statistical / ML** — supervised return prediction, regime classification,
  clustering for pair selection.
- **Sentiment / off-chain** — social velocity, mention counts, news events.
- **Copy / mirror** — another wallet's trade *is* the signal.
- **Market-structure** — funding-rate extremes, open-interest divergence,
  basis and perp-vs-spot spread. Directly relevant to Jupiter Perps.
- **Cross-venue** — CEX/DEX price dislocation.

### 2.2 Signal quality concepts (the part most bots skip)
- **Lookahead bias** — using data unavailable at the signal's timestamp.
- **Survivorship bias** — backtesting only tokens that still exist. Brutal on
  Solana, where most tokens die.
- **Signal decay / half-life** — how long the edge persists after emission.
  Determines the entire latency budget downstream.
- **Capacity** — the size at which price impact eats the edge.
- **Multiple-testing / p-hacking** — the more rules tried, the more spurious
  winners.
- **Regime dependence** — a signal that works in trend and dies in chop.
- **Turnover vs cost** — fees, spread, priority fees, and slippage compared
  against gross edge. On Solana, fixed per-tx costs punish small sizes.
- **Fill realism** — a backtest fills at mid; a router fills at a quote.

### 2.3 Signal representation
Timestamp, instrument (mint address, not ticker — tickers collide on Solana),
direction, conviction/size, validity window (TTL), and a **unique signal ID**.
That ID is not cosmetic: it is the idempotency key that prevents double-fills
downstream.

---

## 3. Axis B — Signal distribution and the provider ecosystem

### 3.1 Channels
- **Chat-channel signals** — Telegram/Discord groups, human- or bot-posted.
  Text parsing is the norm and it is fragile.
- **TradingView alerts → webhook** — the de facto retail standard: an alert
  fires a POST with a user-defined JSON body.
- **Relay/automation platforms** — 3Commas, Cornix and similar accept a webhook
  and place orders on a connected venue.
- **Marketplaces / subscriptions** — paid signal feeds, revenue share.
- **Copy-trading platforms** — provider action mirrored into follower accounts.
- **Self-hosted** — your own strategy process emitting to your own executor.
  Fewest trust problems; most engineering.

### 3.2 Trust and verification layer
- **Track-record attestation** — is the claimed history verifiable, or a
  screenshot? On-chain history is auditable; that's a genuine crypto advantage.
- **Selection bias in advertised results** — deleted losing calls.
- **Incentive misalignment** — provider paid on subscriptions, not on your P&L.
- **Front-running the followers** — the provider enters, then publishes.
- **Pump-and-dump structure** — the follower flow *is* the exit liquidity.
- **Capacity dilution** — a signal that worked for 10 followers fails for 10,000.
- **Custody model** — does following require handing over withdrawal rights?

### 3.3 A note on Jupiter's own stance
Jupiter's **Organic Score** (Tokens v2) is explicitly designed to filter out
"bots, snipers, and copy-trading tools." The platform treats this activity as
noise to be discounted — worth knowing if you plan to build on it.

---

## 4. Axis C — Signal → execution on jup.ag

This is where the map stops being generic. Jupiter's current surface:

| Product | Host / path | Notes |
|---|---|---|
| **Swap V2 (meta-aggregator)** | `api.jup.ag/swap/v2` — `GET /order`, `POST /execute` | Managed path. Routers (Metis/JupiterZ/Dflow/OKX) compete. Platform fee 0–50 bps in quote. |
| **Swap V2 (router)** | `api.jup.ag/swap/v2/build` | Raw instructions; **no Jupiter swap fee**. Self-managed. |
| **Transaction Landing** | `POST https://tx.jup.ag` (JSON-RPC `sendTransaction`) | Proprietary landing, SWQoS + Jito. |
| **Trigger v2** | `api.jup.ag/trigger/v2` — create/manage/cancel, `GET /orders/history`, `/orders/history/dca` | Limit orders **and** DCA. Needs `x-api-key` **plus** `Authorization: Bearer <JWT>` for user actions. |
| **Price v3** | `api.jup.ag/price/v3?ids=` | Max **50 ids**; token omitted if untraded 7d. |
| **Tokens v2** | `api.jup.ag/tokens/v2` — `/search`, `/tag`, `/{category}/{interval}`, `/recent` | Categories: `toporganicscore`, `toptraded`, `toptrending`. Organic Score 0–100. |
| **Perps** | **Program-level only** — "the Perps API is still a work in progress" | Anchor IDL parsing. Program ID has weak doc provenance — **UNVERIFIED**. |
| **Prediction (beta)** | `api.jup.ag/prediction/v1` — `/profiles/{pk}`, `/pnl-history`, `/trades`, `/leaderboards` | Beta; breaking changes expected. |
| **Portfolio (beta)** | positions across Jupiter products | Base host not stated on the index page — **UNVERIFIED**. |

**Rate-limit tiers** (one `x-api-key` works across all APIs):

| Plan | $/mo | RPS | RPM | Credits |
|---|---|---|---|---|
| Keyless | — | 0.5 | 30 | — |
| Free | 0 | 1 | 60 | unlimited |
| Developer | 25 | 10 | 600 | 25M |
| Launch | 100 | 50 | 3,000 | 100M |
| Pro | 500 | 150 | 9,000 | 500M |

`/swap/v2/execute` gets its own bucket — 20/50/100 RPS by tier — and costs
**zero credits**.

### 4.1 The two execution paths
**Managed:** `GET /order` (inputMint, outputMint, amount, taker) → base64 v0
versioned tx + `requestId` → sign (partial-sign for JupiterZ, where a market
maker adds signatures) → `POST /execute` with the signed tx + requestId.
Jupiter handles slippage, priority fee, landing, and confirmation polling, and
returns `status` plus `signature`.

**Self-managed:** `GET /build` → returns `computeBudgetInstructions`,
`setupInstructions`, `swapInstruction`, `cleanupInstruction`, `tipInstruction`,
`addressesByLookupTableAddress` (the ALTs), and `blockhashWithMetadata` (with
`lastValidBlockHeight`) → simulate at max CU, apply a **1.2× buffer capped at
1,400,000** → assemble the v0 transaction with those ALTs → sign → send via your
own RPC or `tx.jup.ag`.

### 4.2 Execution concepts that bite
- **Slippage:** `slippageBps`. **RTSE** (Real-Time Slippage Estimator) is
  Jupiter's dynamic slippage — automatic on `/order`, opt-in on `/build` via the
  literal string `slippageBps=rtse`. `/build` defaults to `50`. Passing a fixed
  `slippageBps` to `/order` overrides RTSE.
- **Priority fees / tips:** `/build` accepts `computeUnitPricePercentile`,
  `tipAmount`, `forJitoBundle`, and `blockhashSlotsToExpiry` (default **150
  slots**).
- **`tx.jup.ag` constraints:** SOL tip **≥ 1,000,000 lamports (0.001 SOL)** to
  one of 16 tip accounts; tx ≤ 1232 bytes; `encoding` must be `base64`;
  `skipPreflight` defaults true and an explicit `false` errors `-1015`;
  `maxRetries` must be `0`; `swqosOnly` toggles SWQoS-only vs SWQoS+Jito.
- **Blockhash expiry:** 150 blocks ≈ **1m19s**. RPC rebroadcasts every ~2s.
- **Double-fill — the sharpest risk in the whole map.** Solana's own docs:
  *"only re-sign a transaction when the blockhash is no longer valid, or else it
  is possible for both transactions to be accepted by the network."* A naive
  retry-on-timeout can fill twice.
- **`skipPreflight` disagreement:** Solana recommends `false`, Helius
  recommends `true` for latency, `tx.jup.ag` forces `true`. Choose per path.
- **MEV / sandwiching:** `/build` exposes `forJitoBundle`; Helius Sender offers
  `?mev-protect=true` and `sendBundle` (≤4 txs, atomic), requires **both** a tip
  and a priority fee, and defaults to 50 TPS. All Jito facts here are
  Helius-sourced — native Jito tip accounts and auction semantics are
  **UNVERIFIED**.
- **Referral / platform fees:** `/order` takes `referralAccount` +
  `referralFee` (50–255 bps); `/build` takes `platformFeeBps` + `feeAccount`.
  You must pre-create a **referral token account per mint**, or fees silently
  fail to collect.
- **Gasless trade-off:** setting `payer` disables JupiterZ RFQ, which worsens
  prices on major pairs.

---

## 5. Axis D — Event/webhook integration

### 5.1 Inbound: signal → your executor
The TradingView-style pattern: alert → HTTPS POST to your relay → validate →
place the Jupiter order. Concepts that matter regardless of source:

- **Authenticity** — HMAC signature over the raw body, verified before parsing.
- **Replay protection** — timestamp window plus a nonce/event-ID cache.
- **Idempotency** — dedupe on a signal ID; a duplicate POST must not double-fill.
- **Ordering** — HTTP delivery is unordered; a stale "exit" arriving after a
  fresh "enter" must be rejected by sequence or timestamp, not by arrival order.
- **At-least-once semantics** — assume duplicates as the normal case.
- **Backpressure and TTL** — a signal older than its validity window is not a
  trade, it's a liability. Drop it.
- **Fail-closed** — on ambiguity, do not trade.

### 5.2 Outbound: chain/venue state → you
Solana has **no native webhooks**, and Jupiter adds none. Options:

| Mechanism | Shape | Key caveats |
|---|---|---|
| **Helius webhooks** | Enhanced (parsed, 100+ tx types), Raw (lower latency, includes failed txs), Discord. Trigger = `accountAddresses` × `transactionTypes`, fires after **confirmed**. Up to 100k addresses/webhook. | **No HMAC.** Only a static echoed `authHeader` value — anyone who learns it can forge a fill event. Must return 200 within **1s**; retries **3× at 1s**, then *"permanently lost — there is no re-queue."* Duplicates explicitly expected; dedupe on tx signature. |
| **LaserStream gRPC** (Helius) | Yellowstone-wire-compatible; txs/slots/blocks/accounts/entries; **historical replay up to 216,000 slots (~24h)** by start slot. | Mainnet needs Business/Professional. Docs contradict themselves on at-least-once vs exactly-once — **UNVERIFIED**; assume at-least-once. At `processed`, slots can fork and *"Geyser does not send explicit rollback notifications."* LaserStream WebSocket has **no replay**. |
| **Yellowstone gRPC (Dragon's Mouth)** | `rpcpool/yellowstone-grpc`, AGPL-3.0, Agave Geyser plugin; Rust/Go/Node clients; filters on accounts/txs/blocks/entries; 15s server pings. | `SubscribeDeshred` is Triton-only (OSS returns UNIMPLEMENTED). |
| **RPC WebSockets** | `logsSubscribe`, `accountSubscribe`, `programSubscribe`, `signatureSubscribe` (one-shot). | `logsSubscribe` `mentions` accepts **exactly one** address. Default commitment **finalized**. `blockSubscribe`/`voteSubscribe` are UNSTABLE and disabled by default. No missed-log guarantee, no replay on reconnect. Provider caps apply (Helius: 5–1,000 concurrent by plan, 10-min inactivity timeout). |
| **Polling Jupiter** | `GET /trigger/v2/orders/history` and `/orders/history/dca`; read `orderState`, `rawState`, `events`. | The only Jupiter-native fill signal. |

**A structural consequence for Trigger v2:** orders are *"stored off-chain and
private by default"* and deposits sit in **Privy custodial vault accounts**, one
per wallet — v1's per-order on-chain PDAs are gone. There is no program to
subscribe to for *pending* orders; a fill becomes observable only at keeper
execution. Trigger v1/v2 and Recurring v1 program addresses are **UNVERIFIED**
in Jupiter's own docs.

---

## 6. Cross-cutting concerns

- **Latency budget** — measure end to end: signal timestamp → your ingest →
  quote → sign → submit → *landed*. Compare against the signal's half-life. On
  Solana the landing step, not the HTTP round-trip, usually dominates.
- **Key custody** — a signal-driven bot holds a hot signing key. Concepts:
  hardware/KMS signing, per-strategy sub-wallets to cap blast radius, spend
  caps, allowlisted mints, withdrawal-address allowlists, and never letting the
  webhook handler touch the key directly.
- **Custodial vs non-custodial copy-trade shapes** — mirroring into a wallet you
  control versus depositing into someone else's program. Radically different
  risk, near-identical marketing.
- **Risk layer independent of the signal** — position caps, per-token exposure
  caps, daily loss limits, a kill switch, and a circuit breaker on repeated
  failed sends.
- **Observability** — reconcile intended signals against on-chain fills. If you
  cannot answer "which signals never became trades, and why," you are flying
  blind.
- **Accounting** — cost basis and tax lots per fill; realized vs unrealized P&L
  including fees, tips, and slippage.
- **Legal / ToS** — the Jupiter Terms of Use prohibit reverse-engineering the
  Interface, IP-disguising, and circumventing the Terms, but contain **no
  explicit clause on bots, automated trading, or scraping**, and state no
  effective date. A separate `/docs/legal/sdk-api-license-agreement` exists and
  was **not read** — programmatic-use permission is **UNVERIFIED**. Read it
  before shipping. Rate-limit guidance: exponential backoff on 429; bursting can
  yield 429s even after the refill period.

---

## 7. jup.ag surfaces that are themselves signal-like

| Surface | Public API? |
|---|---|
| Prediction leaderboards, global trade feed, per-wallet P&L history | **Yes** — `prediction/v1/leaderboards`, `/trades`, `/profiles/{pk}/pnl-history` (beta) |
| Tokens `toptrending` / `toptraded` / `toporganicscore` + Organic Score | **Yes** — `tokens/v2/{category}/{interval}` |
| Smart-money / influencer feeds (`jup.ag/spot/smart-money/influencers` exists in the UI) | **No public API found** |
| Perps leaderboard (`jup.ag/perps-leaderboard` exists in the UI) | **No API.** UI-only status **UNVERIFIED** |
| Copy trading | **No** |

Prediction `/trades` + `/leaderboards` is the closest thing to a native signal
feed Jupiter ships — but it is prediction markets, not spot or perps.

---

## 8. Frontier / open edges

- **Perps API maturing** — currently program-level only; a first-class API would
  change what's buildable for funding-rate and basis signals.
- **Trigger v2's off-chain, Privy-custodial design** — moves order state out of
  public view, which removes an on-chain signal source others were mining.
- **Intent/RFQ routing (JupiterZ)** — market-maker signatures in the signing
  path change the bot's state machine, and `payer`-based gasless flows disable
  it.
- **Deshredding / sub-slot data feeds** — Triton-only today; the latency frontier.
- **Organic Score as an adversarial game** — a published bot-filtering score
  invites gaming.
- **On-chain verifiable track records** — the credible answer to signal-provider
  trust, largely unbuilt.
- **Agent/LLM-generated signals** — new failure modes: prompt injection through
  ingested social content reaching a component that can sign transactions.

---

## 9. Decisions to make before building anything

1. **Signal source** — self-generated, purchased feed, or copy-trade mirror?
   Determines whether the trust layer (§3.2) is your problem at all.
2. **Execution path** — managed `/order` + `/execute`, or `/build` +
   `tx.jup.ag` for bundle/ALT/CU control? Managed is fewer moving parts; the fee
   and control trade-offs differ.
3. **Ingestion spine** — Helius webhooks are the easy path but carry static-secret
   auth and a documented permanent-loss window; gRPC with slot replay survives
   both. For money-moving triggers, the webhook weaknesses are hard to accept.
4. **Fill detection** — poll Trigger order-history, watch the chain, or both?
   There is no push option.
5. **Idempotency key** — decide it now (signal ID *and* tx signature), because
   retrofitting it after a double-fill is expensive.
6. **Custody and key handling** — where the signing key lives, and what caps
   bound it.
7. **Plan tier** — the RPS ceiling has to fit the strategy's quote frequency.
8. **Read the SDK/API license agreement** before relying on programmatic access.

---

## 10. Method, sources, and coverage limits

**Sources.** Jupiter claims come from the live developer docs at
`developers.jup.ag` — note that `dev.jup.ag` now 301-redirects there, so older
bookmarks and code comments pointing at `dev.jup.ag` still resolve but no longer
name the canonical host. Doc paths cited above (`/docs/swap`, `/docs/trigger`,
`/docs/portal/rate-limits`, `/docs/portal/plans`, `/docs/perps`,
`/docs/prediction/social-features`, `/docs/transaction/submit`,
`/docs/swap/migration/ultra-to-order`, `/docs/legal/sdk-api-license-agreement`)
are relative to that host. Solana and Helius claims come from `solana.com/docs`,
`docs.helius.dev`, and `github.com/rpcpool/yellowstone-grpc`.

**Local evidence.** The repository holds a static mirror of the jup.ag front end
(`jup.ag/`, ~29 MB). It confirmed which product surfaces exist in the UI —
including `/spot/smart-money/influencers` and `/perps-leaderboard`, the two
signal-like pages with no public API — plus the hosts `remote-api.jup.ag`,
`wallet-api.jup.ag`, `offerbook.jup.ag`, and `privy.jup.ag`. The mirror contains
HTML only; its JavaScript bundles were not downloaded, so it is evidence of
*which pages exist*, never of what any endpoint returns.

**Coverage limits.**
- The three `*-api.jup.ag` hosts found in the mirror are undocumented internal
  surfaces. They are **not** part of the developer platform and should not be
  treated as an API contract.
- Perps, Portfolio, and the two leaderboard/smart-money surfaces carry
  **UNVERIFIED** tags above; each is a question to close before it becomes a
  dependency.
- Jito's native tip accounts and auction semantics were read only through
  Helius's docs, not Jito's own.
- The SDK/API license agreement was not read, so programmatic-use permission
  remains open.
- API surfaces at Jupiter have churned hard (Ultra deprecated, `lite-api` host
  retiring, Recurring folded into Trigger). Re-verify anything here against the
  live docs before writing code against it.

---

## 11. What this map deliberately excludes

Implementation. No service scaffolded, no code written, no endpoint asserted
that a primary source didn't confirm.
