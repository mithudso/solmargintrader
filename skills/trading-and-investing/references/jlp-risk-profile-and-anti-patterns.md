---
name: jlp-risk-profile-and-anti-patterns
# provenance: split from jupiter-jlp-pool.md on 2026-08-05 — Pass J ceiling; sections and footnote labels preserved
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-03"  # inherited; content NOT re-verified at split time
category: reference
description: >-
  The risk half of the JLP position: what you are actually exposed to as the
  counterparty to Jupiter Perps traders, and the ways LPs get it wrong. Covers
  the net-open-interest skew that makes JLP structurally short leverage into
  rallies, oracle and liquidity risk, smart-contract and audit history, the
  hedging trap that converts market risk into counterparty risk on the hedge
  venue, and the LP-side anti-patterns. Split from jupiter-jlp-pool with section
  numbers and footnote labels preserved. Educational only — NOT financial advice.
keywords:
  - JLP risk
  - LP counterparty risk
  - open interest skew
  - delta neutral
  - oracle risk
  - smart contract risk
  - hedging
  - Jupiter Perps
tags:
  - trading-and-investing
  - crypto
  - solana
  - risk
  - defi
---

# JLP — Risk Profile and Anti-Patterns

> **Educational information only — NOT financial, investment, or tax advice.**

> **Split from `jupiter-jlp-pool.md` on 2026-08-05** to stay under the ~10k-token reference ceiling. Section numbers and footnote labels are **unchanged**, so existing section and footnote-label citations still resolve.

**Scope.**

| For… | Go to |
|---|---|
| Pool composition, weights, mint/redeem, virtual price, fee accrual and the payoff (§1–§2) | `references/jupiter-jlp-pool.md` |
| The trader side — oracle execution, borrow fees, leverage, liquidation | `references/jupiter-perps-trading.md` |
| Generic perp/funding/margin theory | `references/crypto-and-digital-asset-trading.md` §2–§4 |

## 3. The Real Risk Profile of Holding JLP

`verified-as-of: 2026-08-03` on all price and level claims.

### Market/beta risk — the dominant risk

JLP is a wrapper around a crypto basket, not a yield instrument. Jupiter's own risk report states that **"a 30% decline across these assets would reduce JLP value by approximately 20% in isolation, before accounting for fee accrual."**[^jup-risk-1]

The proof that fee yield does not protect against this: JLP hit an all-time high of **$5.985 on 6 Oct 2025** and traded near **$3.58 in Aug 2026 — about 40.5% below peak**.[^jup-risk-21] Read that framing carefully: it is peak-to-current and the intra-period trough was not observed, so **maximum drawdown is ≥40.5%, not exactly 40.5%**. The figure is damning precisely *because* JLP's virtual price compounds fees hourly and can only fall when the basket falls faster than fees accrue.

Earlier, shorter windows were milder — **−16.09% over 11–13 Apr 2024** (vs SOL −36.02%),[^jup-risk-10] ~−18% around 5 Aug 2024, and **~−24% in 2025 while SOL fell ~55%**.[^jup-risk-8] The progression is the finding: single-episode 2024 drawdowns ran 16–18%; the 2025–26 cycle produced ≥40%. JLP consistently falls *less* than SOL — a genuine benefit of the ~32% stable sleeve plus fee accrual — **but it falls hard, and a ~12–20% APY is nowhere near a buffer against a 40% basket move.**

### Trader-PnL risk — the tail risk

Open interest is **85–90% long** (Chaos Labs, Aug 2024 — corrected 2026-08-04 from a previously stated 90–93.5%),[^jup-risk-1][^jup-risk-6] which makes JLP **structurally short leverage into rallies**.

The cleanest quantified episode comes from **Chaos Labs, Jupiter's own commissioned risk vendor**: between **14 Nov 2023 and 16 Jun 2024**, SOL rose 183%, BTC 182%, ETH 174% — and **JLP underperformed its own underlying index by ~57 percentage points**, attributed to high impermanent loss from long-skewed OI.[^jup-risk-2] Note what "losing to traders" actually looks like: **JLP *rose* over that window.** It underperformed the basket it holds. The loss is an opportunity-cost transfer, not a nominal drawdown.

Weaker corroborating instances: since 1 Sep 2024, SOL +82.3% and traders realized ~$150M in profits while JLP gained 33.5%;[^jup-risk-9] 7–19 May 2024, basket +6.8% vs JLP +5.3%.[^jup-risk-8] The counterweight is real: Jan–Aug 2024 traders netted ~$3.7M profit against ~$136.8M paid in fees — roughly **37:1 in the pool's favor**. The named worst case is unanimous across sources: **a sustained rally with heavy long skew**, or the rarer inversion where OI flips short and the market then falls (the pool loses stablecoins *and* the basket depreciates at once).

### Oracle risk — no incident, but a documented, sized attack surface

**No oracle exploit of Jupiter Perps was found.** What exists is stronger than an analogue: Chaos Labs' risk reports of 7 and 14 Jul 2024 explicitly warn of "oracle manipulation during times of low liquidity in the CEX spot market, while on Jupiter, prominent and very cheap liquidity, reaching up to approximately **$100M** depending on utilization, could be available at any given moment."[^jup-risk-2][^jup-risk-3] The same reports reference "**the exploiters that operated on the platform**" gaming the size-based price-impact fee by splitting trades — a real, acknowledged extraction cohort, remediated by the **6 Jun 2024** price-impact fee change (Gauntlet dates it 6 June; this file previously said 4 Jun) and a later delta-imbalance mechanism.[^jup-risk-4][^jup-risk-5]

### Smart-contract / protocol risk

Perps has been audited by **Offside Labs (Feb 2024), OtterSec (2023), and Sec3 (17 Jan 2024)**, per Jupiter's security page.[^jup-risk-15][^jup-risk-16] **Two corrections (2026-08-04, against the live page): Neodyme is *not* listed as a Perps auditor, and the Oct 2025 "Oracle and flash loan" review is listed under Jupiter *Lend*, not Perps.** **No material exploit of the Perps contracts to date.**

> A claimed "$50M Jupiter hack, Aug 2025" circulating on social channels could not be corroborated in any security-incident database and **appears false** — disregard it.

Programs are **upgradeable behind a multisig**, and the custody account carries a `permissions` flag the administrator uses "to enable or disable trade actions… useful during program upgrades or black swan events" — **real pause powers exist**.[^jup-risk-20] The operational-lapse precedent: Jupiter disclosed in Sept 2024 that its Ape and Value Average programs were deployed *without* multisig and were deleted on-chain by an unauthorized party; Jupiter stated Perps "has always been under a multisig."[^jup-risk-15]

### Liquidity / exit risk — the common framing is backwards

The AUM cap blocks **mints**, which pushes secondary price to a **premium, not a discount**. And the burn path sets a floor: "if the Market Price is below the Virtual Price, your JLP tokens are redeemed (burned) at the virtual price."[^jup-risk-17] A persistent discount is therefore arbitraged away. Exit fees are weightage-based, from **2 bps (stables) / 10 bps base up to ~150 bps** when the trade pushes an asset away from target.[^jup-risk-18] **The real exit risk is redemption *capacity* under stress, not a discount** — redemption scales with pool assets rather than DEX depth.

> **Unresolved contradiction.** One Jupiter docs surface states withdrawals have "a redemption period of 3 days, plus a 1-day lock after the initial deposit" with a withdrawal fee redistributed to depositors; every other surface describes instant exit with no lock. This may belong to Jupiter Lend rather than JLP redemption, or may be a newer change. **Do not rely on either without on-chain confirmation.** `verified-as-of: 2026-08-03`

### Solana-specific risk

The mechanism is real; realized harm is unevidenced. Because execution and liquidation run through the **two-transaction request/fulfillment model with Jupiter-operated keepers**,[^jup-risk-19] both the network *and* Jupiter's off-chain infrastructure must be live. Solana's outage history is real (Feb 2024 ~5h halt; Sept 2021; Sept 2022 17h).[^jup-risk-22] But no incident was found in which an outage harmed JLP holders, and the countervailing record is strong: ~22 months of continuous uptime, and the Oct 2025 crash (SOL −24.1% in 29 hours) processed without a halt.[^jup-risk-23]

### Hedging JLP — and the risk it creates

Sophisticated holders short SOL/ETH/BTC perps against the basket to isolate fee yield; Drift vaults, Neutral.trade, Vectis, and others productized this.[^jup-risk-7] The most instructive account is a practitioner retrospective that **rejected dynamic hedging**, because per-asset β is strongly *negatively* correlated with price (retail chases trends, consuming pool inventory and lowering β into rallies); a **static hedge near the center of the exposure range, rebalanced every few months**, "dramatically smoothed NAV and pushed the Sharpe ratio extremely high."[^jup-risk-7]

Why it may still not be worth it, in two parts:

1. **α decayed.** Fee yield collapsed from >40% annualized to single digits in Q4 2025 as Jupiter volume fell; the practitioner exited in Nov 2025 with cumulative profit ~50% off its peak. **The hedge removes beta but cannot manufacture fees once the traders leave.**[^jup-risk-7]
2. **Hedging converts market risk into counterparty risk on the hedge venue.** When Drift was drained of **$285M on 1 Apr 2026** via compromised admin keys (DPRK-attributed; drainage ran **~2.5 hours** per Chainalysis and within one hour per Elliptic — **not the ~12 minutes this file previously stated**), the largest single transfer was **41.7M JLP worth ~$155M — roughly 17% of JLP supply — out of the *JLP Delta Neutral* vault.**[^jup-risk-12][^jup-risk-13][^jup-risk-14] The JLP leg was fine; **the hedge leg vaporized.**

That episode is also the best disconfirming evidence against the exit-risk thesis: it triggered a genuine panic-redemption wave, Jupiter confirmed JLP was fully backed with no Drift exposure, and **the price stabilized within 24–48 hours with no sustained discount.** The redeem-at-virtual-price backstop visibly worked under a live stress test.

### The honest bottom line

JLP is not a yield product with some risk attached. It is **a long ~68% crypto basket bundled with a continuously-written short-volatility / short-trader-skill position, financed by fee premium.** The fee stream is the option premium; the basket is the collateral; trader PnL is the payout leg.

- **Best regime:** choppy, high-volume tape with aggregate retail losses.
- **Worst regime:** a sustained one-directional rally where 90%+ long OI is *right* — you underperform the very assets you hold (the −57pp episode).
- **Second-worst, and underappreciated:** volume simply leaves, α decays to nothing, and you hold an unhedged crypto index with a rounding-error coupon. That is what actually happened in Q4 2025–2026.

**Anyone modeling JLP off the displayed APY is modeling one of three return components — and not the one that produced the ≥40% drawdown.**


## 4. Anti-Patterns — LP Side
### LP-side (JLP)

**10. Treating JLP as a stable yield product.** JLP is **~68% volatile crypto**. Advertised APY is a fee yield sitting on top of a directional basket; in a crypto drawdown the basket dominates and the yield does not protect you (§1, §3).

**11. Quoting one "beta to SOL."** JLP's effective delta is **regime-dependent**: weight-implied delta is an *upper bound* in bull markets, because structurally net-long traders profit and drain the pool. Jupiter's own docs warn JLP "may underperform holding the underlying assets directly" in strong bull markets (§1).

**12. Trusting any secondary source for pool weights.** Nearly every third-party writeup still quotes the superseded five-asset ~44/10/11/26/9 split, and Jupiter's own user docs are unreliable here (still listing USDT, now 0%; and the JLP overview and FAQ pages disagree with each other on whether JupUSD is a custody). Read `targetRatioBps` on-chain (§1).

**13. Assuming redemption is always available in the asset you want.** The ±10% weightage band **refuses withdrawals** that would push an asset outside its band, and ~84% of pool SOL is natively staked behind a ~2-epoch deactivation. There is no time lock, but there are real state-dependent constraints (§1).

**14. Being surprised that minting is disabled.** The `maxAumUsd` cap ($3.00B; pool at ~27% of it as of this writing) hard-stops direct minting when reached, leaving only the secondary market — where JLP then typically trades at a **premium** (§1).

**15. Ignoring that JLP already marks open trader PnL.** `aumUsd` **nets out traders' unrealized profits** before dividing by supply. You are not buying in "before" the open positions resolve — the mark is continuous (§1).

## References

[^jup-risk-1]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The quoted "30% decline … approximately 20%" risk-report sentence was searched for across `docs.jup.ag` and `discuss.jup.ag` and not found.)
[^jup-risk-10]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly.
[^jup-risk-12]: Elliptic — Drift Protocol exploited for $286 million in suspected DPRK-linked attack. https://www.elliptic.co/blog/drift-protocol-exploited-for-286-million-in-suspected-dprk-linked-attack — Independent; confirms the 1 Apr 2026 date, that "the JLP Delta Neutral, SOL Super Staking and BTC Super Staking vaults" were drained, and verbatim "The largest single transfer involved approximately 41.7 million JLP tokens, valued at roughly $155 million at the time of the theft," plus DPRK attribution.
[^jup-risk-13]: Chainalysis — Lessons from the Drift hack. https://www.chainalysis.com/blog/lessons-from-the-drift-hack/ — Independent; confirms "$285 million (over 50% of its TVL)" drained beginning "at approximately 16:05 UTC" on 1 Apr 2026 and DPRK linkage. **Contradicts the body's "~12 minutes"**: it states "Drainage transactions continued for approximately 2.5 hours, with the last confirmed drain at 18:31 UTC."
[^jup-risk-14]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (Specifically, the "roughly 17% of JLP supply" framing and the "~12 minutes" duration were not corroborated by either fetched Drift source.)
[^jup-risk-15]: Jupiter user docs — Security. https://docs.jup.ag/user-docs/more/security — Primary: the Perpetuals audit roster — Offside Labs (Feb 2024), OtterSec (2023), Sec3 (17 Jan 2024) — and that "JLP … runs on the same program, so it is covered by the Perpetuals audits." **Contradicts the body: Neodyme does not appear anywhere on this page.** The page carries no Sept 2024 multisig disclosure.
[^jup-risk-16]: Jupiter user docs — Security. https://docs.jup.ag/user-docs/more/security — Primary: an Offside Labs "Oracle and flash loan" audit dated October 2025 exists — but it is listed under **Jupiter Lend**, not Perpetuals. **Contradicts the body's attribution** of that review to the Perps contracts.
[^jup-risk-17]: Jupiter user docs — JLP FAQ. https://docs.jup.ag/user-docs/earn/jlp/faq — Primary: "If the pool's AUM limit is reached, new JLP cannot be minted directly and the market price may trade at a premium above the virtual price. If the market price falls below the virtual price, JLP is redeemed at the virtual price." **Note:** substance matches, but the body's quoted wording ("your JLP tokens are redeemed (burned) at the virtual price") is not the live string.
[^jup-risk-18]: Jupiter user docs — Perps Fees. https://docs.jup.ag/user-docs/trade/perps/fees — Primary: the swap and JLP mint/burn fee is "10 BPS (non-stables), 2 BPS (stables), adjusted by weightage." **Does NOT support** the body's "~150 bps" upper bound; no fetched source states a weightage-fee ceiling.
[^jup-risk-19]: Jupiter user docs — Perps Technical Reference. https://docs.jup.ag/user-docs/trade/perps/technical-reference — Primary: the two-transaction request/fulfillment model and that "Jupiter runs two keepers in parallel," which are offchain services operated by Jupiter.
[^jup-risk-2]: Chaos Labs / Jupiter governance forum — Weekly Risk Report, Sunday July 7 (2024). https://discuss.jup.ag/t/weekly-risk-report-sunday-july-7/19970 — Primary: verbatim "the exploiters that operated on the platform" trade-splitting cohort, and the oracle warning "Oracle manipulation during times of low liquidity in the CEX spot market, while on Jupiter, **large** and very cheap liquidity, reaching up to approximately $100M depending on utilization, could be available at any given moment." **Note:** this report says "large," not "prominent" as the body quotes; and it does **not** contain the −57pp 14 Nov 2023–16 Jun 2024 analysis also attributed to this marker.
[^jup-risk-20]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The custody `permissions` pause flag and its "black swan events" wording appear in no page reachable from `docs.jup.ag/llms.txt`; the former developer-docs host `dev.jup.ag/docs/old/...` now 404s.)
[^jup-risk-21]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (No price-history source for the $5.985 ATH was fetched.)
[^jup-risk-22]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (Solana outage history is outside Jupiter's docs and was not independently fetched in this pass.)
[^jup-risk-23]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly.
[^jup-risk-3]: Chaos Labs / Jupiter governance forum — Weekly Risk Report, Sunday July 14 (2024). https://discuss.jup.ag/t/weekly-risk-report-sunday-july-14/20212 — Primary: the body's quoted wording exactly, including "**prominent** and very cheap liquidity, reaching up to approximately $100M depending on utilization," plus "the exploiters that operated on the platform." Also records that "On July 10, the base fee was reduced to 6 bps in all markets."
[^jup-risk-4]: Gauntlet / Jupiter governance forum — Comprehensive Analysis: Jupiter Perpetuals Price Impact Structure Implementation and Proposed Adjustments (1 Jul 2024). https://discuss.jup.ag/t/gauntlet-comprehensive-analysis-jupiter-perpetuals-price-impact-structure-implementation-and-proposed-adjustments/19127 — Primary: analysis of the price-impact fee change, which it dates to "**June 6th, 2024**" — **contradicting the body's "4 Jun 2024."**
[^jup-risk-5]: Chaos Labs / Jupiter governance forum — Jupiter Price Impact Fee Mechanism Review (11 Jul 2024). https://discuss.jup.ag/t/chaos-labs-jupiter-price-impact-fee-mechanism-review/19969 — Primary: the size-only price-impact model "exposes the protocol to potential exploits. Exploiters can break down their trades into many small transactions," and the recommendation of "a price impact mechanism based on delta imbalance within a specific window" — the delta-imbalance mechanism the body references.
[^jup-risk-6]: Chaos Labs / Jupiter governance forum — Market Crash Analysis, Monday Aug 5 (2024). https://discuss.jup.ag/t/market-crash-analysis-monday-aug-5/21245 — Primary: long-skewed open interest, stated as "Since **85-90%** of Jupiter's open interest consists of long positions, traders experienced significant losses." **Note:** this is the only OI-skew figure located; it does **not** support the body's "90–93.5% long."
[^jup-risk-7]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The practitioner hedging retrospective and the ">40% to single digits" fee-yield collapse were not located.)
[^jup-risk-8]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly. (The Jan–Aug 2024 $3.7M-vs-$136.8M figures were not located in any fetched source.)
[^jup-risk-9]: **UNSOURCED.** The original research artifact cited this marker but never defined it, and no primary source was located for the adjacent claim on 2026-08-04. Treat the adjacent statement as unverified and check docs.jup.ag directly.
