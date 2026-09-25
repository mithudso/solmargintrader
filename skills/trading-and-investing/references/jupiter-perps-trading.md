---
# provenance: split from jupiter-perps-and-jlp 2026-08-04 (Pass J: 14.2k tokens -> two spokes)
name: jupiter-perps-trading
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-03"
category: reference
description: >-
  TRADER side of Jupiter Perps (jup.ag) on Solana — the oracle-priced,
  peer-to-pool perpetual futures venue. Covers the oracle execution model (no
  order book, no AMM curve; keeper request/fulfill flow; price-impact fee; why
  "zero slippage" does not mean no execution risk), the BORROW-FEE model and
  precisely how it differs from a funding rate (both sides always pay, the rate
  is never negative, utilization-driven, nobody is ever paid to wait), and
  leverage/margin plus how the liquidation price DRIFTS as borrow fees accrue.
  Plus trader-side anti-patterns. Educational only — NOT financial advice.
keywords:
  - Jupiter Perps
  - jup.ag
  - Solana perpetuals
  - borrow fee
  - funding rate
  - oracle-priced perps
  - peer-to-pool
  - liquidation price drift
  - price impact fee
  - perp DEX
  - keeper fulfillment
tags:
  - trading-and-investing
  - solana
  - perpetual-futures
  - defi
  - perp-dex
  - jupiter
---

# Jupiter Perps — Trading Side

> **Educational information only — NOT financial, investment, or tax advice.** Leveraged perpetual futures can lose your entire collateral. This protocol changes fast: volatile facts are stamped `verified-as-of` and several key values (borrow rates, caps) must be read from the live on-chain accounts before acting.

> **Sourcing note — citations resolved 2026-08-04, with 1 gap disclosed.** This file inherits footnote
> markers from the original `/dr`-built `jupiter-perps-and-jlp` artifact, which **cited five prefixes but
> defined only one** (`jup-liq-*`). On 2026-08-04 the missing markers were researched against primary
> sources: of 13, **12 are now backed by fetched primary or governance-forum sources** and **1 is
> explicitly marked `UNSOURCED`** in the definitions below. An `UNSOURCED` marker is **not a citation** —
> treat the adjacent claim as unverified. Most unsourceable markers point at IDL / `Pool`-account field
> claims whose former home (`dev.jup.ag/docs/old/perpetual-exchange/*`) now **404s** with no listed
> replacement. That research pass also found **several body claims that contradict the live docs**; each
> is recorded inside the relevant definition and flagged inline where it affects a stated fact. **Verify
> every venue-specific claim against `docs.jup.ag` before relying on it.** A research pass to close the
> remaining gaps is queued — see `../SCHEDULED-RESEARCH.md`.


**Scope.** The **trader** side only. For the pool you are trading against — JLP composition, fee accrual, LP payoff and LP risk — see `references/jupiter-jlp-pool.md`.

| For… | Go to |
|---|---|
| **JLP as a position you hold** (composition, weights, mint/redeem, fee accrual, LP payoff, LP risk) | `references/jupiter-jlp-pool.md` |
| Generic perpetual-futures theory, funding-rate mechanics, generic margin/liquidation-engine behavior | `references/crypto-and-digital-asset-trading.md` §2–§4 |
| Position sizing, Kelly, drawdown control, Sharpe/Sortino | `references/trading-risk-management.md` |
| The EVM perp-DEX landscape (GMX, dYdX, Hyperliquid) | `references/defi-and-onchain-trading.md` §8 |
| Jupiter's swap/router/Trigger/Recurring surface (not perps) | `references/jupiter-swap-routing-and-orders.md` |
| Priority fees, tx landing, Solana MEV | `~/.claude/skills/blockchain/references/solana-transaction-execution-and-mev.md` |

## Contents

1. Oracle-Priced Execution — What Price You Actually Get
2. The Borrow Fee Model — and Why It Is Not a Funding Rate
3. Leverage, Margin, and Liquidation-Price Drift
4. Anti-Patterns (trader side)

---

## 1. Oracle-Priced Execution — What Price You Actually Get

Jupiter Perps is a **peer-to-pool** venue. The JLP pool is the sole counterparty to every position: traders borrow notional from the pool, and JLP holders absorb trader PnL. There is **no order book to walk and no constant-product curve** — the execution price is the oracle price at the moment a keeper fulfills the request.[^jup-exec-1][^jup-exec-6]

### The oracle stack

Three independent on-chain oracles feed the program: **Edge by Chaos Labs** (primary), with **Chainlink** and **Pyth** used for verification and fallback. The documented selection logic: (1) if Edge is not stale *and* sits within a threshold of both Chainlink and Pyth, use Edge; (2) otherwise compare Chainlink against Pyth and, if they agree within threshold, use the more recent; (3) if two or more oracles fail, **no price update occurs** — trading stalls rather than executing on a bad print.[^jup-exec-2] `verified-as-of: 2026-08-03`

> **The numeric staleness window and deviation threshold are not published.** Treat oracle cadence as undocumented rather than assuming a figure. Integrators still reading the legacy `dovesOracle` custody field must migrate to `dovesAgOracle`.[^jup-exec-2]

### Two different things are called "slippage" — don't conflate them

| | At execution | Between request and fill |
|---|---|---|
| **Exists?** | No | Yes |
| **Why** | Size does not walk a book — a $2M order and a $2k order fill at the same oracle print | Keeper delay lets the oracle move |
| **Control** | n/a | `priceSlippage` on the `PositionRequest` account (UI default **2%**; presets 1/2/3%) |
| **On breach** | n/a | The request is **cancelled, not filled worse** |

The IDL's slippage semantics are direction-dependent: increasing a long or decreasing a short fails if the current price exceeds `priceSlippage`; decreasing a long or increasing a short fails if `priceSlippage` exceeds the current price. Collateral routed through a swap carries a second guard, `jupiterMinimumOut`.[^jup-exec-5]

### Price impact fee — the replacement for book slippage

Because there is no book, Jupiter charges an explicit **price impact fee** in two summed components, capped per asset:

```
Linear:   coefficient = TradeSize / scalar        fee = TradeSize × coefficient
Additive: bps         = factor × (newImbalance / Threshold) ^ exp
Total     = min(Linear + Additive, TradeSize × maxPriceImpactFee)
```

**Worked example — a $10,000 SOL long.** SOL's `tradeImpactFeeScalar` is 1.25e15 raw, i.e. **$1.25B** in USD terms.[^jup-exec-6] Coefficient = 10,000 / 1.25e9 = 8e-6, so the **linear impact fee is $0.08**. The base fee is 0.06% × $10,000 = **$6.00**. If the open-interest imbalance exceeds SOL's threshold, an additive penalty stacks on top, with the *total* capped by `maxPriceImpactFee` (50 bps = $50 on this size).

> **Documentation defect — trust the code, not the prose.** Jupiter's own fees page states this example as **$0.0008** (linear section) and **$0.00008** (additive section). Both are wrong: the page's own code snippet, run on the page's own inputs, yields **$0.08**, and converting the raw scalar to USD terms independently yields the same $0.08. The prose table divides by `BPS_POWER` where the code divides by `USDC_DECIMALS` — a 100× error, with the additive example separately 1000× low.[^jup-exec-3][^jup-exec-6] `verified-as-of: 2026-08-03`

Critically, `factor`, `exp`, and the imbalance threshold are **per-custody on-chain values the docs decline to print**. A trader therefore *cannot precompute total price impact from public documentation* — they get the oracle price plus a known 0.06% plus a computable linear term, and must otherwise read the custody account or trust the UI's "Price Impact" field, bounded by the per-asset cap.[^jup-exec-3]

### The two-step keeper flow

Every action is **two transactions**:

1. The trader submits a `PositionRequest` PDA (derived from the `Position` address, constant seeds, and a random `counter`) carrying size, collateral, direction, `priceSlippage`, `requestType` (`Market` or `Trigger`), and `triggerPrice`.
2. One of **two keepers running in parallel** detects, validates, and submits the fulfillment transaction.

**The trade is not live until that second transaction confirms.** Keepers handle opens, closes, size changes, collateral deposits/withdrawals, TP/SL, and limit orders. Non-TP/SL request accounts close as soon as the request executes *or is rejected*; TP/SL requests persist on-chain until triggered. No TTL field and no published latency figure exist — the docs say only "a short delay."[^jup-exec-2][^jup-exec-5]

### Order types, and why TP/SL is not a guarantee

Jupiter states plainly that there is **no FIFO ordering**: a trigger transaction and a liquidation transaction can hit the chain simultaneously and "whichever is processed first by the network will execute. The outcome cannot be guaranteed."[^jup-exec-4] Additional documented gates:

- Above 150× leverage the UI warns that limit orders "may not execute as expected."
- **New limit orders are blocked when market utilization exceeds 80%.**
- The liquidation price shown on the limit-order form is a *simulation*, not the price that will apply at trigger time.

### Custody model and PnL denomination

A position is an on-chain `Position` account plus a `PositionRequest` PDA and its ATA; each asset has a **custody account** holding `assets.owned/locked/guaranteedUsd/globalShortSizes`, the `increasePositionBps`/`decreasePositionBps` fee fields, and `pricing.tradeImpactFeeScalar`.[^jup-exec-2]

**Longs are collateralized in the underlying** (SOL/wETH/wBTC); **shorts in stablecoin**. Collateral USD value is **fixed at deposit** and does not float with the token. Payout is `tokensReceived = closingValueUsd / tokenPriceAtClose` — so **a profitable SOL long paid in SOL receives fewer SOL the higher SOL goes**. The trader is long a USD-denominated PnL delivered in a token whose price just rose. Either side may elect the alternative token at close, subject to a swap fee (10 bps non-stables, 2 bps stables, weightage-adjusted).[^jup-exec-4]

> **Contradiction preserved:** Jupiter's user docs say shorts are collateralized in **USDC only**, while the developer `PositionRequest` doc says "**USDC / USDT**," and a USDT custody account exists on-chain. Verify against the live custody account before building on either.[^jup-exec-4][^jup-exec-5]

### Fees at open and close

Base fee is **0.06% each way**, read live from `increasePositionBps` / `decreasePositionBps`.[^jup-exec-3] Independent corroboration, **corrected 2026-08-04**: Gauntlet's fee review recommended **10 bps → 7 bps**, not 7→6; the **7→6 bps** cut was implemented on 10 Jul 2024 and reported by **Chaos Labs**, not Gauntlet.[^jup-exec-6] There is **no separate keeper/execution fee in SOL** — the trader pays the Solana network fee, an optional priority fee or Jito tip, and **refundable rent** for the position's escrow PDA (returned at close). Liquidation forfeits **all** remaining collateral. `verified-as-of: 2026-08-03`


## 2. The Borrow Fee Model — and Why It Is Not a Funding Rate

**This is the single most important thing to get right about this venue.** Jupiter Perps has **no funding rate**. It has a **borrow fee**, and the two are not variations on a theme — they are structurally different cash flows. A trader who ports funding-rate intuition here will mis-model their holding cost, in one direction: always too low.

### The exact formula

Jupiter's user docs state it as:[^jup-borrow-1]

```
Hourly Borrow Fee = (Total Tokens Locked / Total Tokens in Pool)
                  × Hourly Borrow Rate
                  × Position Size (USD)
```

Resolved to the on-chain fields you should actually model against:[^jup-borrow-1][^jup-borrow-2]

```
utilizationPct   = custody.assets.locked / custody.assets.owned
hourlyBorrowRate = (custody.fundingRateState.hourlyFundingDbps / 1000) × utilizationPct
hourlyBorrowFee  = hourlyBorrowRate × positionSizeUsd
```

Gauntlet's independent governance formulation — `hourlyBorrowRate_x = utilization_x × maxHourlyBorrowRate_x` — is the same equation.[^jup-borrow-3] Note the fee multiplies **position size in USD (notional)**, not the borrowed token amount, and that utilization uses `assets.locked / assets.owned` — tokens *reserved to pay potential profits*, not literally "tokens borrowed."

> **Two naming traps, both of which cause under-modeling.**
>
> **Trap 1 — "Hourly Borrow Rate" is overloaded.** In the prose formula it means the *max* rate (`hourlyFundingDbps / 1000`); in the code block it names the *already-utilization-adjusted* product. The trade form displays the **effective** rate. A trader who reads the UI rate and substitutes it into the prose formula **multiplies by utilization twice and understates carry by a factor of `utilization`** — at 20% utilization, they budget one-fifth of the true cost.
>
> **Trap 2 — field-name drift.** **Corrected 2026-08-04 — this file previously had the two surfaces
> reversed.** Live: the **Technical Reference (custody account) *and* the fees page's prose table** both
> write `hourlyFundingBps`; only the fees page's **code block** writes `hourlyFundingDbps` (deci-bps,
> ÷1000). The drift is real and **the ÷1000 deci-bps reading is the correct one** — but it is the code
> block, not the custody-account page, that carries it.

### Who pays: both sides, always, no exceptions

**Every open position on Jupiter pays borrow fees to the JLP pool. There is no long-vs-short transfer, no negative rate, and no mechanism by which any trader is ever paid to hold.** The rate is the product of two non-negative quantities, so it is structurally floor-bounded at zero.

Gauntlet states it in protocol terms: "Unlike traditional venues where funding payments are exchanged between long and shorts, Jupiter's funding mechanism exchanges capital between traders and JLP holders."[^jup-borrow-3] A governance participant states the trader-side consequence: "jup-perps always charges borrow fee, which can be high or low, but **trader always pays. This difference is unavoidable by design**."[^jup-borrow-5] An independent trader analysis concurs: "traders always borrow from the JLP hence the borrow rate always stays positive whether you are long or short."[^jup-borrow-7]

**But "both pay" is asymmetric.** Longs borrow the *volatile* custody (SOL/ETH/BTC); shorts borrow the *stable* custody (USDC/USDT, and now JupUSD). Those custodies carry different utilizations and different max rates — Gauntlet's May 2024 table recommended SOL at .016%/hr (140% APR) against USDC/USDT at .003%/hr (23% APR).[^jup-borrow-3] The precise statement: **both sides always pay, but shorts typically pay far less, and each side's cost is driven by a different custody's utilization.**

### Accrual and settlement

Fees accrue **continuously as unrealized debt**, not as an hourly on-chain transfer. Each custody carries `fundingRateState.cumulativeInterestRate`; each position stores `cumulativeInterestSnapshot`. **The difference between them × position size is the fee owed.**[^jup-borrow-2] The UI's "Borrow Fees Due" is that accrued-unsettled balance. Settlement is realized whenever the position account is touched — close, liquidation, collateral change, or size change.

> **On "compounding":** the docs say fees "compound hourly," but an index *difference* × fixed notional is **additive/linear**, not fee-on-fee. What a trader experiences as compounding is second-order: fees erode collateral → effective leverage rises → the liquidation price drifts toward spot (see §3). Contradiction preserved — the program source could not be read to settle it.[^jup-borrow-1]

### Borrow fee vs funding rate — the contrast that matters

| Dimension | **Jupiter Perps (borrow fee)** | **CEX / EVM perps (funding rate)** |
|---|---|---|
| **Direction of payment** | Trader → JLP pool, always | Long ↔ Short, peer-to-peer |
| **Sign** | **Always positive** — structurally cannot be negative | Can be **negative**; one side *receives* |
| **Rate driver** | Pool **utilization** (`locked/owned`) × governance-set max | Perp-spot **basis / premium index** + interest component |
| **Interval** | Hourly rate, continuous index accrual | Discrete: 8h (typical) or 1h |
| **Settlement** | Unrealized debt, realized on close/liq/collateral change | Discrete transfer at each funding timestamp |
| **Can you be paid to hold?** | **Never** | **Yes**, routinely |
| **Cap** | Governance-set max rate at 100% utilization | Clamped, but sign-symmetric |

For the funding-rate side of this table (premium index, the interest component, the clamp, and funding as a sentiment signal), see `references/crypto-and-digital-asset-trading.md` §3 — it is not re-derived here.

**Strategic consequence.** Cash-and-carry and funding-harvest strategies **do not work on Jupiter in the same form**, because there is no perp leg that ever receives. Long spot + short perp pays borrow fees on the hedge as well — it is a pure cost structure. On Jupiter the carry is harvestable only from the *other* side of the trade: JLP takes ~75% of borrow fees, so to earn it you must become the pool and accept its directional exposure (§5, §6).

### Quantifying the drag

Assume a max rate of **0.012%/hr** at **50% utilization** → effective **0.006%/hr**:

| Holding period | Cost as % of position size | % of collateral @ 10× | % of collateral @ 25× |
|---|---|---|---|
| 1 day (24h) | 0.144% | 1.44% | 3.60% |
| 1 week (168h) | 1.008% | 10.08% | 25.2% |
| 1 month (720h) | **4.32%** | **43.2%** | **108%** |

Add the round-trip base fee (0.06% × 2 = 0.12% of size). **A one-month 10× position at moderate utilization burns ~44% of posted collateral in fees alone, before any price move.** At 25×, borrow fees alone exceed the entire collateral inside a month. Jupiter Perps is a venue for short holding periods; the fee structure actively penalizes carrying a position.

### The ceiling, and why it is reachable

Because the rate is **linear in utilization**, the ceiling is exactly `hourlyFundingDbps` at 100% utilization — ~105% APR at 0.012%/hr (Gauntlet labels .01%/hr as 88% APR and .016%/hr as 140% APR).[^jup-borrow-3] **Claim withdrawn 2026-08-04.** This file previously asserted "this is not theoretical: governance discussion documents SOL utilization sitting at 100% for a sustained period." The cited thread documents the **opposite** — utilization judged far too *low*, with ETH shorts exceeding longs.[^jup-borrow-5] Treat the ceiling as **an arithmetic bound, not an observed regime**: *if* utilization were pinned at 100% for 30 days that would be 8.64% of position size — **86.4% of collateral at 10×** — but no such sustained period is evidenced here.

Unlike funding, the rate cannot go negative and cannot exceed the governance-set cap. It is a **bounded, one-directional tax**.

### Rate values are the volatile part — read them live

The mechanism, field names, and formula above were re-read from live official docs on 2026-08-03. **The rate VALUES could not be verified for that date** — no 2026 rate publication exists; the most recent is Feb 2025. Observed values, with true observation dates:

| Observed | Asset | Max hourly rate | Labeled APR |
|---|---|---|---|
| May 2024 (Gauntlet, then-current) | all | .01%/hr | 88% |
| May 2024 (Gauntlet, recommended) | SOL / ETH / BTC / USDC / USDT | .016 / .010 / .012 / .003 / .003 %/hr | 140 / 88 / 104 / 23 / 23 % |
| Feb 2025 (governance, observed live) | SOL | .003%/hr | ~30% |
| Undated (docs example) | SOL | .012%/hr | ~105% |

> **Unresolved contradiction — flat linear vs. dual-slope curve.** The official docs (read 2026-08-03) publish a **flat linear** model with no kink and no floor, so the rate → 0 as utilization → 0. But Gauntlet (Dec 2024) proposed moving "from the current single linear rate curve to a **dual slope (jump rate) model**" with a **kink at 80% utilization and a 10% APR minimum across all assets**,[^jup-borrow-4] and Chaos Labs filed a parallel jump-rate recommendation the same month.[^jup-borrow-10] A 10% APR floor is **mathematically incompatible** with `utilization × max`. Either the docs are stale or the dual-slope was never implemented (or was reverted). **Anyone modeling holding cost must read the live custody account rather than trusting the published formula at low utilization.** `verified-as-of: 2026-08-03`

## Moved sections

The sections below were split out on 2026-08-05 to stay under the reference size ceiling. Numbering is preserved.

| Section | Now lives in | Covers |
|---|---|---|
| **§3 Leverage, Margin, and Liquidation-Price Drift** | `references/jupiter-perps-leverage-and-liquidation.md` | 1.1x–250x range, collateral rules, the liquidation-price drift as borrow fees accrue, and the 100%-of-remaining-collateral penalty. |
| **§4 Anti-Patterns — Trader Side** | `references/jupiter-perps-leverage-and-liquidation.md` | The trader-side mistakes, including treating the borrow fee as a funding rate. |

## References

[^jup-borrow-1]: Jupiter user docs — Perps Fees. https://docs.jup.ag/user-docs/trade/perps/fees — Primary: the prose borrow-fee formula verbatim ("Hourly Borrow Fee = (Total Tokens Locked / Total Tokens in Pool) * Hourly Borrow Rate * Position Size (USD)"), the worked example (100 SOL / $10,000, 200 locked of 1,010 pooled, 19.8% utilization, 0.012%/hr → **$0.238/hr**), and verbatim "Borrow fees compound **hourly**." **Note:** the same sentence continues "and are deducted from the position's collateral," which sits in tension with the body's "accrue as unrealized debt, not an hourly transfer."
[^jup-borrow-10]: Chaos Labs / Jupiter governance forum — Borrowing Rate Jump Rate Model Recommendations (23 Dec 2024). https://discuss.jup.ag/t/chaos-labs-borrowing-rate-jump-rate-model-recommendations/29203 — Primary: the parallel jump-rate filing four days after Gauntlet's, giving the piecewise `lower_slope`/`upper_slope` formulas around a target utilization, confirming the body's "Chaos Labs filed a parallel jump-rate recommendation the same month."
[^jup-borrow-2]: Jupiter user docs — Perps Fees (code block) and Perps Technical Reference. https://docs.jup.ag/user-docs/trade/perps/fees and https://docs.jup.ag/user-docs/trade/perps/technical-reference — Primary: the resolved on-chain formulation `utilizationPct = custody.assets.locked / custody.assets.owned` and `hourlyBorrowRate = (custody.fundingRateState.hourlyFundingDbps / 1000) * utilizationPct`, plus the `assets.owned` / `assets.locked` field definitions. **Does NOT support** `fundingRateState.cumulativeInterestRate` or a position's `cumulativeInterestSnapshot` — neither field name appears in any page reachable from `docs.jup.ag/llms.txt`. **Contradicts the body's Trap 2 attribution:** the *custody-account page* (Technical Reference) writes `fundingRateState.hourlyFundingBps`, and so does the fees page's prose table; only the fees page's **code block** writes `hourlyFundingDbps`. The drift is real and ÷1000 is right, but the body has the two surfaces reversed.
[^jup-borrow-3]: Gauntlet / Jupiter governance forum — Jupiter Perpetuals Trading Fee & Borrowing Rate Recommendations (3 May 2024). https://discuss.jup.ag/t/jupiter-perpetuals-trading-fee-borrowing-rate-recommendations/16122 — Primary: the formulation `hourlyBorrowRate_x = utilization_x * maxHourlyBorrowRate_x`; the quote verbatim "Unlike traditional venues where funding payments are exchanged between long and shorts, Jupiter's funding mechanism exchanges capital between traders and JLP holders."; and the May 2024 per-custody table (then-current .01%/hr / 88% APR across all assets; recommended SOL .016%/hr 140%, ETH .010%/hr 88%, BTC .012%/hr 104%, USDC and USDT .003%/hr 23%) — matching the body's rate table exactly.
[^jup-borrow-4]: Gauntlet / Jupiter governance forum — Dual Slope Borrowing Rate Model Implementation and Recommendations (19 Dec 2024). https://discuss.jup.ag/t/gauntlet-dual-slope-borrowing-rate-model-implementation-and-recommendations-12-19-24/29072 — Primary: verbatim "transitioning from the current single linear rate curve to a dual slope (jump rate) model," the "kink at 80% utilization," and verbatim "A minimum borrowing rate of 10% annually has been implemented across all assets" — the 10% APR floor the body flags as incompatible with `utilization × max`. The recommended-parameter tables list Min Rate APR 10% for every asset.
[^jup-borrow-5]: Jupiter governance forum — Dynamic borrow fees adjustment proposal, user DimOK (20 Feb 2025). https://discuss.jup.ag/t/dynamic-borrow-fees-adjustment-proposal/35464 — Primary: the quote verbatim "jup-perps always charges borrow fee, which can be high or low, but trader always pays. This difference is unavoidable by design of jup-perps," and the observed live rate "(0.003%/hour, around 30% apr)" supporting the body's Feb 2025 table row. **Contradicts the body's other use of this marker:** the thread documents utilization that is far **too low** (ETH shorts exceeding longs), not "SOL utilization sitting at 100% for a sustained period."
[^jup-borrow-7]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The quoted "independent trader analysis" was never named; the substance — that both sides always pay — is independently supported by `[^jup-borrow-3]` and `[^jup-borrow-5]`.)
[^jup-exec-1]: Jupiter user docs — Perpetual Exchange overview. https://docs.jup.ag/user-docs/trade/perps — Primary: the venue "operates as a **trader-to-LP model**: traders borrow assets from the Jupiter Liquidity Pool (JLP) to open leveraged positions," JLP holders "act as the counterparty to all trades," and the three markets are SOL, ETH and wBTC. Confirms there is no order book and no AMM curve.
[^jup-exec-2]: Jupiter user docs — Perps Technical Reference. https://docs.jup.ag/user-docs/trade/perps/technical-reference — Primary: the three-oracle stack (Edge by Chaos Labs primary; Chainlink and Pyth for verification/fallback), the three-step selection logic including "If two or more oracles fail, **no price update occurs**," the `dovesOracle`→`dovesAgOracle` migration note, the two-transaction request/fulfillment model with two parallel Jupiter-operated keepers and "a short delay," and the custody-account field roster. Confirms the staleness window and deviation threshold are **not** published.
[^jup-exec-3]: Jupiter user docs — Perps Fees. https://docs.jup.ag/user-docs/trade/perps/fees — Primary: the flat 0.06% open/close fee read from `increasePositionBps`/`decreasePositionBps`; the two-part price-impact fee with the `min(Linear + Additive, Max Fee)` cap; and that `factor`, `exp` and `deltaImbalanceThreshold` are per-custody onchain values the page declines to print ("The exact values can be read from the custody accounts").
[^jup-exec-4]: Jupiter user docs — Positions and Collateral. https://docs.jup.ag/user-docs/trade/perps/positions-and-collateral — Primary: verbatim "Jupiter Perps does not enforce FIFO (First-in, First-out) execution ordering… Whichever is processed first by the network will execute. The outcome cannot be guaranteed."; the >150× in-app warning that "limit orders may not execute as expected"; that "Limit orders cannot be created when the selected market's utilization exceeds 80%"; and the payout rule `closingValueUsd / tokenPriceAtClose`. The per-side collateral table (long: SOL/wETH/wBTC; short: **USDC** for all three) is on https://docs.jup.ag/user-docs/trade/perps — supporting the user-docs half of the body's USDC-vs-USDC/USDT contradiction. The developer-docs half could not be re-checked (see `[^jup-exec-5]`).
[^jup-exec-5]: Jupiter user docs — Positions and Collateral. https://docs.jup.ag/user-docs/trade/perps/positions-and-collateral — Primary: slippage tolerance is user-configurable with presets **1%, 2%, 3%** and a **2% default**, and "If the price moves beyond this tolerance, the trade is cancelled" — i.e. cancelled, not filled worse. **Does NOT support** the IDL-level details also attributed to this marker (`PositionRequest` PDA seeds, the direction-dependent `priceSlippage` semantics, `jupiterMinimumOut`, `requestType`/`triggerPrice`, TP/SL account persistence); the former developer-docs host `dev.jup.ag/docs/old/perpetual-exchange/*` now 404s and no replacement page is listed in `docs.jup.ag/llms.txt`. Treat those specifics as unverified.
[^jup-exec-6]: Jupiter user docs — Perps Fees. https://docs.jup.ag/user-docs/trade/perps/fees — Primary: SOL's raw `tradeImpactFeeScalar` is **1,250,000,000,000,000** and the page's own TypeScript snippet, run on the page's own inputs, yields **$0.08** while its prose tables state **$0.0008** (linear) and **$0.00008** (additive) — the 100×/1000× documentation defect described in the body is **confirmed against the live page**. **Contradicts the body's Gauntlet attribution:** Gauntlet's fee review recommended **10 bps → 7 bps**, not 7→6 (https://discuss.jup.ag/t/jupiter-perpetuals-trading-fee-borrowing-rate-recommendations/16122); the 7→6 bps cut was implemented on 10 Jul 2024 and reported by **Chaos Labs** ("On July 10, the base fee was reduced to 6 bps in all markets," https://discuss.jup.ag/t/weekly-risk-report-sunday-july-14/20212). **Also note:** the additive example labels the scalar "1,250,000,000 (USD terms)" while the linear example derives 125,000,000,000 from the same raw value — the docs are internally inconsistent, so the body's "1.25e15 raw, i.e. $1.25B in USD terms" reconciles only against the additive table.
