---
name: jupiter-perps-leverage-and-liquidation
# provenance: split from jupiter-perps-trading.md on 2026-08-05 — Pass J ceiling; sections and footnote labels preserved
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-03"  # inherited; content NOT re-verified at split time
category: reference
description: >-
  How a Jupiter Perps position is margined and how it dies. Covers the leverage
  range and collateral rules, why the liquidation price DRIFTS as borrow fees
  accrue against the position rather than staying fixed, the full-collateral
  liquidation penalty, the stop-vs-liquidation race, and the trader-side
  anti-patterns. Split from jupiter-perps-trading with section numbers and
  footnote labels preserved. Educational only — NOT financial advice.
keywords:
  - liquidation price
  - leverage
  - margin
  - collateral
  - liquidation penalty
  - borrow fee drift
  - Jupiter Perps
  - perpetuals
tags:
  - trading-and-investing
  - crypto
  - solana
  - leverage
  - risk
---

# Jupiter Perps — Leverage, Margin, and Liquidation

> **Educational information only — NOT financial, investment, or tax advice.**

> **Split from `jupiter-perps-trading.md` on 2026-08-05** to stay under the ~10k-token reference ceiling. Section numbers and footnote labels are **unchanged**, so existing section and footnote-label citations still resolve.

**Scope.**

| For… | Go to |
|---|---|
| Oracle-priced execution and the borrow-fee model (§1–§2) | `references/jupiter-perps-trading.md` |
| The LP side of the same venue | `references/jupiter-jlp-pool.md` |
| Who actually executes a conditional order | `references/solana-execution-agents-keepers-and-rfq.md` |

## 3. Leverage, Margin, and Liquidation-Price Drift

`verified-as-of: 2026-08-03`

### Markets, limits, and margin model

Three markets only — **SOL, ETH, wBTC** — all against the shared JLP pool.[^jup-liq-3][^jup-liq-6][^jup-liq-7] Collateral is fixed per side: **longs post the underlying** (SOL/wETH/wBTC), **shorts post USDC**.

- **Leverage range 1.1×–250×.**[^jup-liq-3][^jup-liq-4] One independent explainer still says 100×[^jup-liq-6] — stale; the primary docs state 250× in three places.
- **Up to 6 positions per wallet** (one per asset per side). Opening a second position on the same asset *and* side **merges** into the existing one at a blended average entry price — it does not open a second.[^jup-liq-3]
- **Margin is isolated per position.** Each of the six carries its own collateral and own liquidation price; there is no cross-margin equity pool.
- Minimum position size and minimum collateral are **not published**.

### Maintenance margin is 0.2% — and the 250 vs 500 confusion resolved

The formula's `size / max_lev` term **is** the maintenance margin, and `max_lev` is a **protocol constant of 500**, distinct from the 250× user-facing trading cap. Since 1/500 = 0.002, **maintenance margin = 0.2% of position notional** — matching the historically documented figure.[^jup-liq-1] What changed over time is the leverage cap, not the margin floor.

### The liquidation price formula

Verbatim from the docs:[^jup-liq-1]

```
Liq Price (Long)  = price − ( |collateral_size − close_fee − borrow_fee − (size / max_lev)| × price ) / size
Liq Price (Short) = price + ( |collateral_size − close_fee − borrow_fee − (size / max_lev)| × price ) / size
```

`price` = average entry (USD) · `collateral_size` = current collateral (USD) · `close_fee` = 0.06% base + price impact · `borrow_fee` = accrued to date · `size` = notional (USD) · `max_lev` = **500**.

> **Caveat (preserved, not resolved):** the absolute-value bars are only safe while the bracket is positive. Once collateral falls below maintenance, `abs()` flips the sign and pushes a long's liquidation price *below* entry instead of above. The published formula is correct in its normal domain only.

Dividing through gives the more useful closed form — the **liquidation buffer as a fraction of entry price**:

```
buffer = 1/L − f_close − 0.002 − (borrow_fee / size)
```

| Leverage | Buffer at t = 0 |
|---|---|
| 10× | 9.74% |
| 100× | 0.74% |
| 250× | **0.14%** |

At the 250× cap a **0.14% adverse move** liquidates you, before a single hour of fees.

**Worked example (long).** SOL long, entry **$100**, size **$10,000** (100 SOL), collateral **$1,000** (10×), close fee $6, maintenance $10,000/500 = **$20**, borrow fee $0:

```
Liq = 100 − (|1,000 − 6 − 0 − 20| × 100) / 10,000 = 100 − (974 × 100)/10,000 = $90.26
```

The mirror short (same size, $1,000 USDC) liquidates at **$109.74**.

### The drift — the part most traders miss

Borrow fees enter the formula directly, so **the liquidation price moves toward spot every hour a position stays open, with the market completely flat.** Differentiating: `Δliq per dollar of accrued borrow fee = borrow_fee × price / size`. Expressed as a fraction of entry price, **daily drift = effective hourly borrow rate × 24 — independent of leverage.**

Using the docs' own worked borrow-fee example (19.8% utilization, 0.012%/hr nominal, $10,000 size → **$0.238/hr**):

- **$5.71/day** of borrow fees → the liq price drifts **$0.0571/day** on a $100 entry = **0.0571% of entry per day**, flat spot.

Leverage doesn't change the drift *rate*; it changes how fast that drift eats the buffer:

| Leverage | Buffer | Buffer consumed/day | **Days to liquidation, flat spot** |
|---|---|---|---|
| 10× | 9.74% | 0.59% | ~171 days |
| 100× | 0.74% | 7.7% | **~13 days** |
| 250× | 0.14% | 41% | **~2.5 days** |

At **100% utilization** (0.288%/day) the 100× position dies in **~2.6 days** and even the 10× in **~34 days** — zero adverse price move required.

**The practical headline: on Jupiter Perps a leveraged position has a finite lifespan regardless of direction.** The *direction* of this effect is stated explicitly by Jupiter and is FACT; the specific day-counts above are computed from the docs' own worked example and are TENTATIVE, since they inherit the §2 utilization ambiguity (figures here apply utilization **once**, matching the docs' worked example).

### At liquidation

Triggered when the **oracle price** crosses the liquidation price. Execution is by **keepers** — the same two-keeper, two-transaction architecture as order fulfillment (§1).[^jup-liq-5]

**The penalty is 100% of remaining collateral.** The docs' example is unambiguous: $10,000 collateral, $1,000 remaining after losses and fees → **$1,000 liquidation penalty, $0 returned.**[^jup-liq-1][^jup-liq-2] There is no partial forfeit and no residual return. Traders never owe more than posted collateral.[^jup-liq-14]

**There is no insurance fund and no ADL analogue** anywhere in the Perps documentation — and structurally none is needed: the model is trader-to-LP, JLP is the direct counterparty on every position, and **100% of liquidated collateral flows to JLP**. (One third-party comparison table mentions an insurance fund; attribution is unreliable and it is treated as contradicted.)

### Collateral management and drifting displayed leverage

Traders **can** add collateral to an open position via **Edit**, pushing a long's liq price down and a short's up while lowering leverage; withdrawing does the reverse.[^jup-liq-4][^jup-liq-11] Because longs are collateralized in the underlying, **a long's collateral is worth less in USD exactly as the position loses** — a second-order effect that tightens longs relative to a stablecoin-margined venue.

**Displayed leverage drifts upward mechanically:** size is fixed at open while collateral is debited for borrow fees, so `leverage = size / collateral` rises every hour held, and further as unrealized losses accrue. (Derived from the fee mechanics; not stated as such in the docs.)

### On "it wicked to my liquidation and reversed"

The recurring community complaint.[^jup-liq-12][^jup-liq-13] The mechanical answer: liquidation triggers on the **oracle price**, not any single venue's last-traded price, so a wick on one exchange's chart and a liquidation are separately determined events. **No credible report of a liquidation-price calculation bug surfaced.**


## 4. Anti-Patterns — Trader Side

Venue-specific traps. Each is grounded in a mechanism documented above, not general trading advice.

### Trader-side

**1. Modelling holding cost as a funding rate.** The headline error. On a CEX, a well-timed short in a positive-funding regime is *paid* to wait. On Jupiter there is no such regime — **the rate is never negative and both sides always pay** (§2). Any strategy whose edge depends on receiving carry does not port to this venue.

**2. Reading the UI rate into the prose formula.** The trade form shows the **effective** (utilization-adjusted) rate; the docs' prose formula expects the **max** rate. Substituting one for the other multiplies by utilization twice and **understates carry by a factor of `utilization`** — at 20% utilization you budget one-fifth of your true cost (§2).

**3. Treating the published borrow-rate formula as authoritative at low utilization.** Governance proposed a dual-slope model with a **10% APR floor**, which is mathematically incompatible with the published `utilization × max` formula. Read the live custody account (§2).

**4. Holding a leveraged position "for the trade to work out."** Borrow fees compound their damage through collateral erosion. A one-month 10× position at moderate utilization burns **~44% of collateral in fees alone** before any price move (§2). This venue is built for short holding periods.

**5. Assuming a stop-loss is a guarantee.** Jupiter states there is **no FIFO ordering** — a TP/SL transaction and a liquidation transaction can land in the same block, and "the outcome cannot be guaranteed." Your stop can lose the race to your liquidation (§1).

**6. Assuming "zero slippage" means no execution risk.** There is no slippage *at execution*, but the request→fill keeper gap is real, and a move beyond `priceSlippage` **cancels the request** rather than filling it worse. In fast tape you get no fill, not a bad fill — a different failure mode that breaks stop-and-reverse logic (§1).

**7. Trying to precompute the price impact fee from the docs.** `factor`, `exp`, and the imbalance threshold are per-custody on-chain values Jupiter does not publish; the docs' own worked examples are arithmetically wrong by 100×–1000×. Trust the code snippet, the on-chain scalar, and the UI's bounded estimate (§1).

**8. Ignoring the utilization gate.** New limit orders are **blocked above 80% market utilization** — precisely the crowded conditions in which you most want to queue an order (§1).

**9. Forgetting that a winning long is paid in the asset that just rose.** Payout is `closingValueUsd / tokenPriceAtClose`, so a profitable SOL long receives **fewer SOL the higher SOL goes**. If you are trying to accumulate the token rather than USD, this silently works against you (§1).

## References

[^jup-liq-1]: Jupiter user docs — Perps Liquidations. https://docs.jup.ag/user-docs/trade/perps/liquidation — Primary: liquidation trigger, long/short liq-price formulas, `max_lev = 500` vs the 250x trading cap, the borrow-fee drift statement, and the 100%-of-remaining-collateral penalty example.
[^jup-liq-11]: Jupiter support hub — Collateral Management. https://support.jup.ag/hc/en-us/articles/18735419447452-Collateral-Management — Add/withdraw collateral mechanics and their effect on liquidation price.
[^jup-liq-12]: r/solana — "Perp liquidation issue or is it just me?" https://www.reddit.com/r/solana/comments/1he1wq1/perp_liquidation_issue_or_is_it_just_me/ — NEGATION source: the "wicks to my liquidation then reverses" complaint pattern.
[^jup-liq-13]: r/solana — "Don't use perp trading Jupiter". https://www.reddit.com/r/solana/comments/1b78qki/dont_use_perp_trading_jupiter/ — NEGATION source: mass-liquidation complaint and alleged price suppression.
[^jup-liq-14]: r/jupiterexchange — "Can someone explain Jupiter leverage trading". https://www.reddit.com/r/jupiterexchange/comments/1hjasz7/can_someone_explain_jupiter_leverage_trading_in/ — Confirms losses are capped at posted collateral (no negative balance).
[^jup-liq-2]: Jupiter user docs — Perps Fees. https://docs.jup.ag/user-docs/trade/perps/fees — Primary: 0.06% base fee, price-impact fee (linear + additive), hourly borrow-fee formula and worked example, liquidation penalty.
[^jup-liq-3]: Jupiter user docs — Perpetual Exchange overview. https://docs.jup.ag/user-docs/trade/perps — Primary: key-parameters table (250x max, 6 positions max) and the supported-markets table with per-side collateral rules.
[^jup-liq-4]: Jupiter user docs — Positions and Collateral. https://docs.jup.ag/user-docs/trade/perps/positions-and-collateral — Primary: 1.1x-250x range, deposit/withdraw effects on liquidation price, collateral rules.
[^jup-liq-5]: Jupiter user docs — Perps technical reference. https://docs.jup.ag/user-docs/trade/perps/technical-reference — Primary: keeper architecture (two keepers, two-transaction model), custody and oracle accounts.
[^jup-liq-6]: eco.com — Jupiter Perps fees, leverage, and how JLP works. https://eco.com/support/en/articles/15083164-jupiter-perps-fees-leverage-how-jlp-works — Independent; confirms the three-market list and the LP-backed model, but still states 100x (stale vs primary docs).
[^jup-liq-7]: Decentral Park Capital — A deep dive into the Jupiter Perpetual exchange. https://decentralparkcapital.substack.com/p/a-deep-dive-into-the-jupiter-perpetual-0d2 — Independent deep dive; confirms SOL/wBTC/ETH-only and the oracle-priced, zero-slippage design.
