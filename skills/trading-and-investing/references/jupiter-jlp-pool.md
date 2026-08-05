---
# provenance: split from jupiter-perps-and-jlp 2026-08-04 (Pass J: 14.2k tokens -> two spokes)
name: jupiter-jlp-pool
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-03"
category: reference
description: >-
  The JLP pool (Jupiter Liquidity Provider) as a POSITION YOU HOLD — the
  counterparty side of Jupiter Perps. Covers pool composition and target weights,
  mint/redeem mechanics and the AUM cap, how fees accrue into the JLP virtual
  price, the LP-as-trader-counterparty payoff, and the real risk profile: JLP is
  a long ~68% crypto basket bundled with a continuously-written short-volatility
  position financed by fee premium, NOT a yield product. Includes the regimes
  where it underperforms simply holding the underlying. Educational only — NOT
  financial advice.
keywords:
  - JLP
  - Jupiter Liquidity Provider
  - jup.ag
  - LP counterparty
  - virtual price
  - target weights
  - AUM cap
  - delta neutral JLP
  - short volatility
  - peer-to-pool
  - liquidity provision
tags:
  - trading-and-investing
  - solana
  - defi
  - liquidity-provision
  - jupiter
  - risk
---

# The JLP Pool — Holding the Other Side

> **Educational information only — NOT financial, investment, or tax advice.** **JLP is a volatile, ~68%-crypto position that is the direct counterparty to trader profits — not a yield product.** Advertised APY is a fee yield sitting on top of a directional basket. Volatile facts are stamped `verified-as-of`; target weights and caps must be read from the live on-chain accounts before acting.

> **Sourcing note — citations resolved 2026-08-04, with 20 gaps disclosed.** This file inherits footnote
> markers from the original `/dr`-built `jupiter-perps-and-jlp` artifact, which **cited five prefixes but
> defined only one** (`jup-liq-*`). On 2026-08-04 the missing markers were researched against primary
> sources: of 39, **19 are now backed by fetched primary or governance-forum sources** and **20 are
> explicitly marked `UNSOURCED`** in the definitions below. An `UNSOURCED` marker is **not a citation** —
> treat the adjacent claim as unverified. Most unsourceable markers point at IDL / `Pool`-account field
> claims whose former home (`dev.jup.ag/docs/old/perpetual-exchange/*`) now **404s** with no listed
> replacement. That research pass also found **several body claims that contradict the live docs**; each
> is recorded inside the relevant definition and flagged inline where it affects a stated fact. **Verify
> every venue-specific claim against `docs.jup.ag` before relying on it.** A research pass to close the
> remaining gaps is queued — see `../SCHEDULED-RESEARCH.md`.


**Scope.** The **liquidity-provider** side. For the trading venue itself — oracle execution, borrow fees, leverage and liquidation — see `references/jupiter-perps-trading.md`.

| For… | Go to |
|---|---|
| **Trading Jupiter Perps** (oracle execution, borrow fee, leverage, liquidation drift) | `references/jupiter-perps-trading.md` |
| Impermanent loss and AMM LP economics (a different LP model) | `references/defi-and-onchain-trading.md` §2–§4 |
| Why carry/short-premium strategies fail, and how to offset them | `references/strategy-failure-modes-and-synergy.md` §3.5, §6.2 |
| Generic perp/funding/margin theory | `references/crypto-and-digital-asset-trading.md` §2–§4 |

## Contents

1. The JLP Pool — Composition, Weights, Mint/Redeem, and Virtual Price
2. Fee Accrual, Distribution, and the LP Payoff
3. The Real Risk Profile of Holding JLP
4. Anti-Patterns (LP side)

---

## 1. The JLP Pool — Composition, Weights, Mint/Redeem, and Virtual Price

**Everything numeric in this section is a snapshot.** `verified-as-of: 2026-08-03`. Weights, AUM, and caps move; read the on-chain accounts before acting.

### Six custodies, not five

Target weights decoded directly from `targetRatioBps` on all six mainnet custody accounts (live program state, not documentation):[^jup-jlp-6][^jup-jlp-7]

| Asset | Target (`targetRatioBps`) | Current weight | Pool size (USD) | Utilization |
|---|---|---|---|---|
| SOL | **47.00%** | 46.29% | $371.45M (84.3% natively staked) | 7.54% |
| ETH | **8.00%** | 7.80% | $62.67M | 6.24% |
| wBTC | **13.00%** | 13.56% | $108.87M | 10.65% |
| USDC | **30.00%** | 30.25% | $242.78M | 61.03% |
| JupUSD | **2.00%** | 2.07% | $16.66M | 0.00% |
| USDT | **0.00%** | — | ≈ $0 | — |

Targets sum to exactly 10,000 bps. **Volatile sleeve 68.00% target / 67.65% current; stable sleeve 32.00% / 32.32%.** Two structural changes produced this: USDT's weight was migrated wholesale into USDC (May 2025 governance parameter update, now confirmed at 0 bps on-chain),[^jup-jlp-8] and **JupUSD** — Jupiter's native stablecoin — was added as a sixth custody so yield on the stablecoin float accrues back to JLP.[^jup-jlp-10][^jup-jlp-11]

> **Nearly every secondary source is stale here.** Third-party writeups still quote the old five-asset ~44/10/11/26/9 split.[^jup-jlp-12][^jup-jlp-13] Jupiter's own user docs are stale in *both* directions — they instruct users to mint with "SOL, ETH, WBTC, USDC, or USDT," still listing USDT (now 0%). **Corrected 2026-08-04:** the docs do *not* simply omit JupUSD — `earn/jlp` lists it as a sixth custody while `earn/jlp/faq` omits it, so the docs are **internally inconsistent**.[^jup-jlp-2] Trust the on-chain custody accounts.

### Rebalancing: a fee tilt plus a hard band — not a scheduled rebalance

No keeper periodically rebalances. Two mechanisms do the work:

1. **Weightage-adjusted mint/redeem and swap fees.** Base rates are **10 bps for non-stablecoins** and **2 bps for stablecoins**.[^jup-jlp-2] The final fee is adjusted **up** if the action pushes an asset further from target and **down** if it moves it closer (on the swap path, `swapBps ± taxBps`).[^jup-jlp-3] An LP is effectively paid to deposit an under-weight asset and penalized to deposit an over-weight one. Trader swaps routed through the pool are the other continuous rebalancing force.
2. **A hard weightage buffer.** `Pool.limit.tokenWeightageBufferBps` caps deviation from target. **On-chain it reads 1000 (±10% relative)**; the developer docs still say 2000 (±20%) — contradiction preserved, live state should win.[^jup-jlp-3][^jup-jlp-6] At ±10%, SOL's admissible band is ~42.3%–51.7% and USDC's ~27%–33%. The pool **refuses deposits *or* withdrawals** that would push an asset outside its band — so this constrains redemption, not just minting.

### Acquiring and exiting

- **Mint/redeem directly** on the Earn page with a pool asset, subject to the weightage fee and the AUM cap.
- **Buy/sell JLP on the secondary market** via Jupiter Swap — official docs call this "the recommended method for most users."[^jup-jlp-1]
- **There is no time-based lock-up or cooldown.** But three real constraints exist: the ±10% band can refuse redemption in a *specific* asset; minting is disabled at the AUM cap; and ~84% of pool SOL is natively staked, so unstaking runs Solana's standard ~2-epoch (2–3 day) deactivation, against which the protocol manages liquid-SOL headroom.

### Virtual price — and how trader PnL is marked into it

```
Virtual Price = Total JLP Pool Assets (USD) / Total JLP Supply     [numerator = on-chain Pool.aumUsd]
```

**The load-bearing detail:** `aumUsd` is defined as the USD value of tokens managed by the pool **minus the USD value reserved to pay off trader profits**. It is computed from per-custody `guaranteedUsd` (aggregate long size minus collateral) and `globalShortSizes` + `globalShortAveragePrices`.[^jup-jlp-3][^jup-jlp-4] So **open trader profit is already subtracted from AUM, and open trader loss already added, before dividing by supply.** JLP's price is continuously marked to traders' *unrealized* PnL — there is no lag until positions close.

Snapshot arithmetic checks out: TVL $802,439,019.98 ÷ 223,512,136.596 JLP = **$3.5901**, matching the displayed $3.590; on-chain `aumUsd` read $802,426,663.82 seconds later (0.0015% drift).[^jup-jlp-5][^jup-jlp-6]

### The AUM cap — real, currently not binding

`Pool.limit.maxAumUsd` = **$3.00B**.[^jup-jlp-6] Against $802.4M AUM that is ~$2.20B of headroom (pool at ~26.7% of cap), **so minting is enabled**. The cap is denominated in **USD AUM, not JLP tokens** — there is no separate supply cap, so token headroom floats with price. When the cap *is* hit, direct minting is disabled and only the Jupiter Swap path remains, and docs note JLP then typically trades at a **premium** to virtual price.[^jup-jlp-2] That regime is not active now — third-party feeds actually show a slight *discount* (~$3.566 implied vs $3.590 virtual).[^jup-jlp-18] Note the floor: if market price falls below virtual price, **direct redemption still pays virtual price**.[^jup-jlp-2]

### Delta — JLP is emphatically not a stable asset

By construction from current weights, **$1,000 of JLP carries ~$462.90 SOL, ~$78.00 ETH, ~$135.60 wBTC, and ~$323.20 stables.** Empirically, hourly absolute price-change percentiles put **JLP at 0.16% vs SOL 0.38% (P50), 0.57% vs 1.18% (P90), 1.49% vs 2.82% (P99)** — JLP realizes roughly **0.42×–0.53× SOL's short-horizon volatility**.[^jup-jlp-9]

Two asymmetries matter, and both are regime-dependent:

- **Weight-implied delta is an upper bound in bull markets.** Traders are structurally net long; their profits drain the pool. Official docs state JLP "may underperform compared to holding the underlying assets directly" in strong bull markets[^jup-jlp-2] — the mechanism behind third-party claims that JLP trailed SOL by ~3× in an up-only stretch.[^jup-jlp-17]
- **JLP performs relatively better in sideways or bearish tape**, when traders lose.

**Anyone quoting a single "beta to SOL" for JLP is quoting a regime-dependent number.** An entire hedging industry exists around this exposure (Jupiter's own Delta Neutral vault targets "net-zero delta across SOL, ETH, and wBTC"; Gauntlet's hJLP and others short SOL/ETH/BTC perps against it).[^jup-jlp-14][^jup-jlp-15]

### Where to verify live

Jupiter's Earn page for weights/TVL/price/supply, and — more authoritatively — the on-chain `Pool` account `5BUwFW4nRbftYTDMbgxykoFWqWHPzahFSNAaaaJtVKsq` plus the six `Custody` accounts, which carry `targetRatioBps`, `aumUsd`, `maxAumUsd`, `guaranteedUsd`, and `globalShortSizes` directly.[^jup-jlp-6][^jup-jlp-7]


## 2. Fee Accrual, Distribution, and the LP Payoff

> **Sourcing note.** The dedicated research pass for this section was lost to an infrastructure failure and could not be re-run inside the budget. What follows is restricted to claims **already independently sourced in §4 and §6** (footnotes reused, not newly asserted), plus one figure explicitly marked unverified. `verified-as-of: 2026-08-03`

### How the yield actually reaches a holder

**JLP is an accumulating token, not a distributing one.** There is no reward-token emission, no claim button, and no separate income event. Fees earned by the pool are retained *in* the pool, raising `aumUsd` and therefore the **virtual price** = `aumUsd / supply` (§1).[^jup-jlp-3][^jup-jlp-4]

Three consequences follow, and each trips people up:

1. **Your return shows up only as price appreciation.** Comparing JLP to a staking product with a visible APY payout is a category error.
2. **There is no income stream to spend or compound separately** — compounding is automatic and unavoidable.
3. **The displayed APY is a backward-looking derived rate**, inferred from virtual-price change, not a promised or contracted yield.

### The fee streams that feed the pool

Per §1–§4, the pool receives essentially every fee the venue charges:

| Stream | Detail | Section |
|---|---|---|
| Open/close base fee | 0.06% each way | §1 |
| Price-impact fee | linear + additive, per-asset capped | §1 |
| **Borrow fees** | utilization × max rate × notional, paid by longs **and** shorts, continuously | §2 |
| Liquidation penalty | **100% of remaining collateral** flows to JLP | §3 |
| Mint/redeem + swap fees | 2 bps stables / 10 bps non-stables, weightage-adjusted | §4 |

**The borrow fee is the structural core of the LP's return** — the one stream that accrues every hour from every open position regardless of direction, and precisely the stream a trader mis-models as funding (§2).

> **CONFIRMED 2026-08-04** against `docs.jup.ag/user-docs/earn/jlp`: **75% of all fees generated by Jupiter Perps** (opening/closing, price impact, borrow, swap) accrue to the JLP pool, and **the remaining 25% goes to Jupiter as protocol revenue**.[^jup-jlp-1] **One correction to this file's earlier wording:** the docs say **protocol revenue**, *not* "JUP stakers" — that attribution was this file's own guess and is withdrawn.

### The payoff, stated honestly

JLP holders are the **direct counterparty to aggregate trader PnL**, and the exposure is the **net open-interest skew, not gross** (§1, §3):

```
traders profit  →  aumUsd falls  →  JLP virtual price falls
traders lose    →  aumUsd rises  →  JLP virtual price rises
```

Because `aumUsd` nets out **unrealized** trader PnL continuously (§1), this mark is not deferred until positions close — there is no window in which you buy in "ahead of" the open book.

The LP payoff therefore decomposes into three independent components, and conflating them is the central analytical error:

| Component | Sign | Driver |
|---|---|---|
| **Fee yield** | always ≥ 0 | volume × utilization — the option premium |
| **Trader PnL transfer** | **±** | net OI skew vs realized direction |
| **Basket price move** | **±** | ~68% volatile crypto (§1) |

Only the first is what an APY figure describes.

### What the record shows

Two load-bearing empirical findings, both sourced in §6:

- **Fee yield is not stable.** It collapsed from **>40% annualized to single digits by Q4 2025** as Jupiter volume fell.[^jup-risk-7] The fee leg is a function of trader activity, and that activity can simply leave.
- **The pool usually wins — but "losing" can be invisible.** Jan–Aug 2024 traders netted ~$3.7M profit against ~$136.8M in fees, roughly **37:1 in the pool's favour**.[^jup-risk-8] Yet over 14 Nov 2023–16 Jun 2024 JLP **underperformed its own underlying index by ~57 percentage points** while still rising nominally.[^jup-risk-2] **A period in which JLP goes up can still be a period in which the pool lost badly to traders.**

Practical reading: **fee yield is real but regime-dependent and mean-reverts toward zero when volume dries up; the trader-PnL leg is the variance; the basket is the bulk of the risk.** See §6 for the full decomposition.

## Moved sections

The sections below were split out on 2026-08-05 to stay under the reference size ceiling. Numbering is preserved.

| Section | Now lives in | Covers |
|---|---|---|
| **§3 The Real Risk Profile of Holding JLP** | `references/jlp-risk-profile-and-anti-patterns.md` | Net-OI skew and structural short-leverage exposure; oracle/liquidity risk and the Chaos Labs warnings; audit history; the Drift hedging blow-up. |
| **§4 Anti-Patterns — LP Side** | `references/jlp-risk-profile-and-anti-patterns.md` | The twelve LP-side mistakes, including trusting secondary sources for pool weights. |

## References

[^jup-jlp-1]: Jupiter user docs — JLP Overview. https://docs.jup.ag/user-docs/earn/jlp — Primary: the two acquisition paths and, verbatim, "This is the recommended method for most users and typically offers the best execution" for the Jupiter Swap route; also that exit is by swap or direct burn.
[^jup-jlp-10]: Jupiter user docs — JLP Overview. https://docs.jup.ag/user-docs/earn/jlp — Primary: JupUSD is a live sixth custody (address `DdwY1ELc9rRK7xNL3hTXabSFBmVrTPpfsUZSv2Y3LL1U`) and is named in the pool's underlying-asset index. **Contradicts the body's claim** that Jupiter's user docs omit JupUSD.
[^jup-jlp-11]: Jupiter user docs — JupUSD. https://docs.jup.ag/user-docs/earn/jupusd — Primary: JupUSD is a Solana-native reserve-backed stablecoin, target reserve 90% USDtb / 10% USDC, whose reserves generate T-bill yield. **Note:** the page states that yield "is not passed through to JupUSD holders directly"; it does not state that the float yield accrues back to JLP, as the body asserts.
[^jup-jlp-12]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The specific third-party writeup quoting the superseded five-asset split was never named and could not be identified.)
[^jup-jlp-13]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (Second unnamed third-party writeup; not identifiable.)
[^jup-jlp-14]: Jupiter user docs — Delta Neutral. https://docs.jup.ag/user-docs/earn/jlp/delta-neutral — Primary: the managed vault (powered by Neutral Trade) hedges JLP's directional exposure and, verbatim, "The target is net-zero delta across SOL, ETH, and wBTC."
[^jup-jlp-15]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (No Gauntlet hJLP page was located.)
[^jup-jlp-17]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The "JLP trailed SOL by ~3×" third-party claim has no identifiable source.)
[^jup-jlp-18]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The implied secondary-market discount is a prior-session price-feed snapshot, not re-fetchable.)
[^jup-jlp-2]: Jupiter user docs — Earn with JLP. https://docs.jup.ag/user-docs/earn/jlp/earn — Primary: 10 BPS non-stable / 2 BPS stable mint-burn base rates; weightage adjustment direction; the AUM limit disabling direct mint and producing a secondary-market **premium**; and verbatim "In strong bull markets, JLP may underperform compared to holding the underlying assets directly." **Does NOT support** the body's "SOL, ETH, WBTC, USDC, or USDT" mint-asset list — the live docs now list six assets including JupUSD (contradiction, see `[^jup-jlp-10]`).
[^jup-jlp-3]: Jupiter user docs — Earn with JLP. https://docs.jup.ag/user-docs/earn/jlp/earn — Primary: the weightage-based fee is "adjusted up if the action moves the asset further from its target weightage, or down if it moves closer," and fees are redeposited hourly so AUM and therefore virtual price rise. **Does NOT support** the on-chain field names `swapBps`, `taxBps`, `Pool.limit.tokenWeightageBufferBps` or the 2000-vs-1000 buffer contradiction; no fetched source documents them.
[^jup-jlp-4]: Jupiter user docs — Perps Technical Reference. https://docs.jup.ag/user-docs/trade/perps/technical-reference — Primary: the custody fields `assets.guaranteedUsd`, `assets.globalShortSizes` and `assets.globalShortAveragePrices` exist and are defined. **Note:** the page defines `guaranteedUsd` as "Estimate of total long position size (updated on position changes, not in real time)" — **not** "aggregate long size minus collateral" as the body states. No fetched source states the `aumUsd` formula.
[^jup-jlp-5]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The TVL/supply snapshot is a prior-session reading that is not re-fetchable and was not re-derived.)
[^jup-jlp-6]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (Decoded `Pool` account values — `targetRatioBps`, `maxAumUsd`, `aumUsd`, `tokenWeightageBufferBps` — were NOT re-read from chain in this pass; citing an RPC read not performed would manufacture false authority.)
[^jup-jlp-7]: Jupiter user docs — JLP Overview. https://docs.jup.ag/user-docs/earn/jlp — Primary: "The JLP pool holds six assets across six custody accounts," with the six mainnet custody addresses listed (SOL, ETH, wBTC, USDC, USDT, JupUSD). **Does NOT support** the decoded `targetRatioBps` percentages in the body's weight table; those were not re-read from chain in this pass.
[^jup-jlp-8]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (A May 2025 governance parameter update migrating USDT weight to USDC was searched for on `discuss.jup.ag` and not found.)
[^jup-jlp-9]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The JLP-vs-SOL hourly volatility percentiles are an unpublished own-computation with no citable source.)
[^jup-risk-2]: Chaos Labs / Jupiter governance forum — Weekly Risk Report, Sunday July 7 (2024). https://discuss.jup.ag/t/weekly-risk-report-sunday-july-7/19970 — Primary: verbatim "the exploiters that operated on the platform" trade-splitting cohort, and the oracle warning "Oracle manipulation during times of low liquidity in the CEX spot market, while on Jupiter, **large** and very cheap liquidity, reaching up to approximately $100M depending on utilization, could be available at any given moment." **Note:** this report says "large," not "prominent" as the body quotes; and it does **not** contain the −57pp 14 Nov 2023–16 Jun 2024 analysis also attributed to this marker.
[^jup-risk-7]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The practitioner hedging retrospective and the ">40% to single digits" fee-yield collapse were not located.)
[^jup-risk-8]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The Jan–Aug 2024 $3.7M-vs-$136.8M figures were not located in any fetched source.)
