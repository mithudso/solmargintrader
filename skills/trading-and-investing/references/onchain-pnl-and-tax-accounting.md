<!-- run closed 2026-08-04: 3 of 9 sections complete (§2 denominator problem, §7 taxable disposals, §8 per-wallet tax lots). Remaining sections are marked pending in-body and tabulated under "Coverage status — this run". Complete with: /dr --refresh onchain-pnl-and-tax-accounting -->
---
name: onchain-pnl-and-tax-accounting
# provenance: built by /dr 2026-08-04 — do NOT hand-edit the frontmatter block
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  Knowing what you actually made or lost trading on-chain. P&L ACCOUNTING and
  ATTRIBUTION: realized vs unrealized P&L, mark-to-market of open positions, the
  denominator/numeraire problem (a position can be up in SOL terms and down in
  USD terms), decomposing net result into price move vs fees vs borrow/funding
  vs slippage vs failed-transaction waste, gross vs net, and reconciling many
  swaps across a self-custody wallet. Plus CRYPTO TAX LOTS (US): token-to-token
  swaps as taxable disposals, FIFO vs specific identification, per-wallet lot
  tracking under Rev. Proc. 2024-28, crypto wash-sale status, and Form 1099-DA
  broker reporting. Educational only — NOT tax, legal, or financial advice.
whenToUse: >-
  Use when computing, explaining, or reconciling profit and loss for on-chain or
  crypto trading; choosing or applying a cost-basis method; tracking tax lots per
  wallet; determining whether a token-to-token swap is a taxable disposal; or
  attributing a net trading result to its cost components. NOT for risk or
  performance metrics (Sharpe, Sortino, Calmar, drawdown, expectancy,
  R-multiples) — those live in references/trading-risk-management.md.
keywords:
  - on-chain P&L
  - realized vs unrealized
  - cost basis
  - tax lots
  - specific identification
  - FIFO
  - HIFO
  - Rev. Proc. 2024-28
  - Form 1099-DA
  - wash sale crypto
  - P&L attribution
  - implementation shortfall
  - slippage cost
  - failed transaction
  - mark to market
  - numeraire
  - self-custody reconciliation
  - taxable disposal
tags:
  - trading-and-investing
  - crypto
  - on-chain
  - pnl
  - accounting
  - tax
  - cost-basis
  - attribution
---

# On-Chain P&L Accounting, Attribution & Crypto Tax Lots

> **Educational information only — NOT tax, legal, investment, or financial advice, and NOT a recommendation to buy, sell, or hold anything.** Tax rules are jurisdiction-bound and change. This reference defaults to **US federal** treatment and says so explicitly wherever it matters; treatment elsewhere differs materially. Volatile claims carry a `verified-as-of` stamp — **re-verify against the primary source before acting**, and consult a qualified tax professional about your own situation.

**Scope.** This spoke covers **accounting and attribution** — working out what you actually made or lost, and why. It is *not* about performance measurement.

## Contents

**Part A — P&L accounting and attribution**
1. [Realized vs Unrealized P&L](#1-realized-vs-unrealized-pl)
2. [The Denominator Problem](#2-the-denominator-problem)
3. [Cost-Basis Methods](#3-cost-basis-methods)
4. [P&L Attribution](#4-pl-attribution)
5. [Gross vs Net On-Chain P&L](#5-gross-vs-net-on-chain-pl)
6. [Reconciling a Self-Custody Wallet](#6-reconciling-a-self-custody-wallet)

**Part B — Crypto tax lots and reporting (US federal)**
7. [Token-to-Token Swaps as Taxable Disposals](#7-token-to-token-swaps-as-taxable-disposals)
8. [Per-Wallet / Per-Account Tax-Lot Tracking](#8-per-wallet--per-account-tax-lot-tracking)
9. [Wash Sales and Broker Reporting](#9-wash-sales-and-broker-reporting)

[Scope boundaries and cross-references](#scope-boundaries-and-cross-references) · [Coverage status](#coverage-status--this-run) · [References](#references)

---

## 1. Realized vs Unrealized P&L

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

## 2. The Denominator Problem

### The concept

A **numéraire** is the unit in which all other values are expressed — the standard by which value is computed.[^den-1] Its defining property is trivial but load-bearing: **the price of the numéraire in its own terms is always exactly 1.0**, so the numéraire itself is by construction incapable of showing a gain or loss. Every P&L figure is therefore a statement about *something else moving relative to the chosen unit* — never about the unit itself.

FX makes this explicit. Every exchange rate is quoted as *price (quote) currency per one unit of base currency*; the base currency is the denominator and always takes the value 1.[^den-2][^den-3] A **cross rate** is the rate between two currencies where neither is USD, derived from their respective USD quotes.[^den-4] In finance theory the same idea is **change of numéraire** — switching the pricing unit is a well-defined operation, and prices are martingales only under the measure associated with a specific numéraire.[^den-1] *(Qualified — secondary summary of the primary literature.)*

The operational consequence: **a return without a stated numéraire is not a number, it is an ambiguity.** For asset A measured in unit N:

> **(1 + r<sup>USD</sup><sub>A</sub>) = (1 + r<sup>N</sup><sub>A</sub>) × (1 + r<sup>USD</sup><sub>N</sub>)**

Your USD return equals your return measured in SOL, compounded with SOL's own return against USD. Both factors move independently, so their product can land on either side of 1.0 regardless of the sign of either factor alone. **The sign inversion is arithmetic, not an accounting convention.**

### Worked example — the inversion

A trader buys token **TKN** with SOL.

**Day 0** — SOL/USD $200.00; TKN/SOL 0.020 → TKN/USD $4.00. Spend **100 SOL** ($20,000) → receive **5,000 TKN**.

**Day 30** — TKN/SOL 0.025 (**TKN +25% against SOL**); SOL/USD $140.00 (**SOL −30% against USD**) → TKN/USD $3.50.

| Numéraire | Cost basis | Current value | P&L | Return |
| --- | --- | --- | --- | --- |
| **SOL** | 100 SOL | 5,000 × 0.025 = **125 SOL** | **+25 SOL** | **+25.0%** |
| **USD** | $20,000 | 5,000 × $3.50 = **$17,500** | **−$2,500** | **−12.5%** |

Check: (1 + 0.25) × (1 − 0.30) = 0.875 → −12.5%. ✓

Same position, same 5,000 tokens, same 30 days: **up a quarter and down an eighth simultaneously.** Neither figure is wrong — they answer different questions.

**The HODL baseline sharpens it.** Holding the original 100 SOL would leave 100 SOL worth $14,000 at Day 30. So the trade is **+25.0% versus holding SOL**, and **+25.0% versus the HODL baseline in USD too** ($17,500 vs $14,000) — while still **−12.5% in absolute USD**. This is the crypto-native case where *a losing USD position is a good trade.*

The reverse case is more dangerous: a token flat against SOL while SOL rallies 50% against USD reports **+50% in USD and exactly 0% in SOL** — a gain produced entirely by the denominator, with no contribution from the trade itself.

### Stablecoin denominators are not USD

Denominating in USDC or USDT smuggles in an assumption: **1 stablecoin = exactly $1.00, always**. That assumption fails at exactly the moments it matters. Even fully fiat-backed stablecoins inherit the credit risk of the banks and instruments holding their reserves, and peg stability is contingent on confidence in reserve quality.[^den-5][^den-6]

**USDC, March 2023 (Silicon Valley Bank).** Late on **10 March 2023** Circle disclosed that **$3.3 billion** of USDC's cash reserves — roughly 8% of its dollar backing — was stuck at the failed Silicon Valley Bank.[^den-7][^den-8] **By 02:00 on 11 March 2023 USDC had fallen to $0.87.**[^den-9][^den-10] The depeg propagated to DAI, USDD and USDP; parity was restored after the FDIC waived the $250,000 insurance cap on SVB deposits. *(Qualified — venue-by-venue lows varied in the $0.87–$0.885 range within the same hour.)*

A book showing "10,000 USDC, flat" at that moment reported **0% return in USDC terms** while its true USD mark was **≈$8,700 — a −13% unrealized loss the USDC-denominated view was structurally blind to.** Symmetrically, buying USDC at $0.87 and holding to repeg earned **+14.9% in USD** while the USDC balance never changed and USDC-denominated P&L read exactly **0%**.

**TerraUSD (UST), May 2022** is the case where the peg never returned: UST first broke its dollar peg on **9 May 2022** and traded at **11 cents by 16 May 2022**.[^den-11][^den-12] A UST-denominated book would have reported a flat 0% while losing the overwhelming majority of its USD value. *(A widely circulated $0.0449 all-time low on 13 May 2022 appears in secondary sources only — **TENTATIVE**, not verified against a primary feed or tier-1 wire; prefer the two dated figures above.)*

**Rule:** treat a stablecoin numéraire as a *pegged instrument carrying credit risk*, not as USD. Where precision matters, mark stablecoin balances at observed market price rather than at 1.00.

### Tax forces a USD numéraire

US tax reporting requires transactions to be reported in US dollars regardless of the trader's preferred unit (see §7). A trader whose economic objective is *accumulating more SOL or ETH* will therefore routinely report taxable USD gains in periods when their SOL stack shrank, and USD losses in periods when it grew.

### The practical rule

1. **State the numéraire explicitly, always.** "+25%" is not a number; "+25% in SOL terms" is. Treat the unit as a first-class field, not a footnote.
2. **Report both when they diverge** in sign or materially in magnitude. The two-row table above is the deliverable, not a choice between rows — divergence isolates how much of the outcome came from the position versus the denominator.
3. **Benchmark against a HODL baseline in the same numéraire.** The operative question is *"did trading beat simply holding SOL?"* — the crypto analogue of benchmark-relative (active) return, which is what performance attribution decomposes rather than absolute return.[^den-13][^den-14]
4. **Never let the stablecoin leg silently assert 1.00.**

## 3. Cost-Basis Methods

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

## 4. P&L Attribution

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

## 5. Gross vs Net On-Chain P&L

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

## 6. Reconciling a Self-Custody Wallet

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

---

## 7. Token-to-Token Swaps as Taxable Disposals

**US federal treatment.** `verified-as-of: 2026-08-04`

### Digital assets are property, not currency

IRS **Notice 2014-21** (March 25, 2014; 2014-16 I.R.B. 938) holds: *"For federal tax purposes, virtual currency is treated as **property**. General tax principles applicable to property transactions apply to transactions using virtual currency"* (Q&A-1).[^disp-1] Q&A-2 forecloses the currency argument: virtual currency *"is not treated as currency that could generate foreign currency gain or loss."*[^disp-1]

**Notice 2023-34 modified Notice 2014-21**, removing the outdated statement that virtual currency has no legal-tender status anywhere (some jurisdictions have since adopted Bitcoin as legal tender). Critically, it preserves the operative holdings: the change *"does not affect the answers to the FAQs set forth in section 4 of Notice 2014-21."*[^disp-2] So Q&A-1, -5, -6 remain quotable as current law.

**Rev. Rul. 2023-14** restates the framing and supplies the modern §6045(g)(3)(D) definition of "digital asset."[^disp-3]

### Why a token-to-token swap is a disposal

The mechanism is not crypto-specific. Treas. Reg. §1.1001-1(a) makes an exchange of property a realization event: gain or loss is realized *"from the exchange of property for other property **differing materially either in kind or in extent**."*[^disp-4] Because a token is property, giving up Token A for Token B is an exchange of materially different property. **No fiat leg is required** — cash is only one form the amount realized may take.

Notice 2014-21 Q&A-6 is direct: *"Does a taxpayer have gain or loss upon an exchange of virtual currency for other property? **Yes.**"*[^disp-1] The IRS FAQ removes any doubt that "other property" includes another token: *"If you exchange virtual currency held as a capital asset for other property, **including for goods or for another virtual currency**, you will recognize a capital gain or loss"* (Q16).[^disp-5]

So **SOL → USDC and ETH → altcoin are each a disposal of the outbound token** at its then-current USD value.

> *Weight note:* IRS FAQs are sub-regulatory guidance, not published authority. The conclusion does not depend on the FAQ — Notice 2014-21 Q&A-6 and Treas. Reg. §1.1001-1(a) carry it independently.

### §1031 like-kind exchange does not apply

The TCJA (Pub. L. 115-97) rewrote §1031, which is now captioned *"Exchange of **real property** held for productive use or investment"* and applies only where real property is exchanged for like-kind real property.[^disp-6] IRS Chief Counsel Advice **ILM 202124008** (June 8, 2021) states it plainly: *"The Tax Cuts and Jobs Act… amended § 1031 to limit like-kind exchange treatment after December 31, 2017, to exchanges of real property."*[^disp-7] Independent confirmation from DLA Piper.[^disp-8]

**Pre-2018 claims are contested — do not overstate.** ILM 202124008 concluded "No" for BTC↔ETH, BTC↔LTC and ETH↔LTC completed before 2018, reasoning that BTC and ETH acted as on/off-ramps and so differed in "nature and character" from Litecoin. But the memo limits itself: it *"is limited to the exchanges involving Bitcoin, Ether, or Litecoin discussed above… no inferences should be made"* and *"may not be used or cited as precedent."*[^disp-7] Secondary reporting indicates an IRS official allowed that pre-2018 eligibility would be evaluated case-by-case — **TENTATIVE**, unverified against a transcript.[^disp-9] **Net: post-2017 swaps have no §1031 route as a matter of statutory text; the pre-2018 general case is unresolved.**

### Computing gain or loss

The ordinary §1001 formula: **amount realized − adjusted basis**, where amount realized = money received + FMV of property received.[^disp-4]

- **On a swap:** *"Your gain or loss is the difference between the fair market value of the property you received and your adjusted basis in the virtual currency exchanged"* (FAQ Q17).[^disp-5] For SOL → USDC, the amount realized is the **USD FMV of the USDC received at the moment of the swap**. The disposal is measured on the **outbound** leg; the inbound token takes a fresh basis equal to its FMV at exchange (FAQ Q18).[^disp-5]
- **Basis on purchased tokens:** *"the amount you spent to acquire the virtual currency, **including fees, commissions and other acquisition costs** in U.S. dollars"* (FAQ Q8).[^disp-5]
- **Basis on received (non-purchased) tokens** = the amount included in gross income.[^disp-10]

**Determining FMV with no direct USD pair.** Notice 2014-21 Q&A-5: transactions must be reported in USD, and *"If a virtual currency is listed on an exchange and the exchange rate is established by market supply and demand, the fair market value… is determined by converting the virtual currency into U.S. dollars (**or into another real currency which in turn can be converted into U.S. dollars**) at the exchange rate, **in a reasonable manner that is consistently applied**."*[^disp-1] Two operative phrases: a **chained conversion** is authorized, and the governing standard is *reasonable and consistently applied* — the IRS names no mandatory price oracle. Where nothing is priced at all, FAQ Q28 substitutes the FMV of the property or services exchanged.[^disp-5] *(Qualified — Q28 is FAQ-level and framed for property/services received, not squarely for two illiquid tokens; the extension is inference.)*

**Character.** Capital gain or loss where the token is a capital asset; ordinary where it is not (e.g. inventory held for sale to customers) — Notice 2014-21 Q&A-7.[^disp-1]

### Holding period

*"If you held the virtual currency for one year or less… short-term capital gain or loss. …more than one year… long-term. The holding period **begins on the day after you acquired** the virtual currency and ends on the day you sell or exchange it"* (FAQ Q6; Q29 repeats the day-after rule).[^disp-5] This is the ordinary §1222 "more than 1 year" threshold.

**Per lot.** Each acquisition is a separate purchase of property, so **each lot carries its own adjusted basis and its own acquisition date**. A single swap consuming tokens acquired on several dates therefore produces a mix of short-term and long-term results across the consumed lots. *(Which lot you are deemed to dispose of is §3's subject.)*

### Other on-chain events

| Event | Status | Authority |
| --- | --- | --- |
| **Spending crypto on goods/services** | **Settled — taxable.** Exchanging a capital asset for services yields capital gain/loss | Notice 2014-21 §3; FAQ Q14/Q15[^disp-1][^disp-5] |
| **Paying gas/network fees in crypto** | **Qualified — a disposal of the fee tokens** by direct application of Q&A-1 + Q&A-6 and §1.1001-1(a). **No notice, ruling, or regulation addresses gas specifically**; Rev. Rul. 2023-14 fn.2 expressly declines to | [^disp-1][^disp-4][^disp-11] |
| **Whether a fee adds to basis / reduces proceeds** | **Acquisition side supported** (FAQ Q8 includes acquisition costs). **Disposition side has no digital-asset authority** — it rests on general §1001(b) selling-expense doctrine. Every source surfaced for the popular formulation was crypto-tax content-farm material and is deliberately not cited. **TENTATIVE** | [^disp-5] |
| **Wrapping / unwrapping (ETH↔WETH, LSTs)** | **Genuinely unsettled** | [^disp-12] |
| **Liquidity-pool deposit / withdrawal** | **Genuinely unsettled** | [^disp-12] |
| **Staking, lending, short sales, NPCs** | **Genuinely unsettled** | [^disp-12] |
| **Bridging** | **No guidance at all** — not a listed category, though some designs fall inside the cross-chain wrapping description | [^disp-12] |

**The unsettled list is the IRS's own.** **Notice 2024-57** identifies six transaction classes that *"require further study to determine how to facilitate appropriate reporting"* — wrapping/unwrapping (§3.02), liquidity provider transactions (§3.03), staking (§3.04), lending (§3.05), short sales (§3.06), notional principal contracts (§3.07) — and relieves brokers from §6045(a) reporting on them meanwhile. Its disclaimer is unusually blunt:[^disp-12]

> *"The description of the transactions… **does not constitute or reflect a substantive analysis** for Federal income tax purposes… and **no inference is intended** as to how an identified transaction, or its component steps, is treated… The inclusion of a transaction… **is not intended to create an inference that the identified transaction is or is not a sale** of a digital asset."*

> **Read this correctly: Notice 2024-57 is *reporting* relief, not substantive relief. It does not say wrapping is tax-free — it says Treasury has not decided and has told brokers not to guess.** That is the cleanest primary evidence these are open questions.

The doctrinal battleground for wrapping is §1.1001-1(a)'s "differing materially," as construed in *Cottage Savings Ass'n v. Commissioner*, 499 U.S. 554 (1991) (properties differ materially if they "embody legally distinct entitlements"). The professional literature is divided — most practitioners reportedly view wrapping as *not* a sale or exchange, while a *Cottage Savings* argument holds WETH embodies materially different smart-contract functionality.[^disp-13] **Preserve the tension; it is not resolved.** The AICPA has pressed Treasury for guidance including under §1001,[^disp-14] and Treasury's 2025-2026 Priority Guidance Plan lists digital-asset transaction treatment as an active project.[^disp-15]

### Related income rulings (they set basis and start the clock)

- **Rev. Rul. 2019-24** — no gross income from a hard fork *without* receipt of new units; **ordinary income** where an airdrop following a hard fork delivers units. Receipt turns on **dominion and control**, not the ledger entry. Basis in the received coin = the amount of income recognized.[^disp-10] A *soft* fork produces no income (FAQ Q30).[^disp-5]
- **Rev. Rul. 2023-14** (released July 31, 2023) — staking rewards are included in gross income when the taxpayer *"gains dominion and control,"* valued at that date and time, including when staking through an exchange.[^disp-11] Express carve-outs: it does not address gas or transaction fees (fn.2), nor §83 issues (fn.3).

Neither ruling is about a swap. They matter here because they set the **basis** and **acquisition date** of tokens that are later swapped.

## 8. Per-Wallet / Per-Account Tax-Lot Tracking

**US federal treatment.** IRC §1012(c)(1) requires basis conventions for a "specified security" to be applied **on an account-by-account basis**. Section 80603 of the Infrastructure Investment and Jobs Act (Pub. L. 117-58, 2021) expanded "specified security" in §6045(g)(3) to include digital assets.[^lot-1][^lot-2] T.D. 10000 (89 FR 56480, July 9, 2024) finalized Treas. Reg. §1.1012-1(j), which **applies to all acquisitions and dispositions of digital assets on or after January 1, 2025**.[^lot-2][^lot-1] `verified-as-of: 2026-08-04`

**What broke.** The 2019 Virtual Currency FAQs let taxpayers substantiate specific identification by "records of the units held within a single account, wallet, or address," which practitioners and tax software widely read as permitting a **universal / multi-wallet pooled basis** — treating every unit of an asset across all venues as one lot pool. The IRS itself describes Rev. Proc. 2024-28 as guidance on *"how to transition from a universal or multi-wallet basis allocation methodology to a wallet-by-wallet or account-by-account basis allocation methodology."*[^lot-3][^lot-2]

### The Rev. Proc. 2024-28 safe harbor

Rev. Proc. 2024-28, 2024-31 I.R.B. 326, **effective June 28, 2024**, lets taxpayers allocate **unused basis** to assets held in each wallet/account **as of January 1, 2025** (defined as immediately after the close of December 31, 2024).[^lot-1]

§3.09 defines a "unit of unused basis" so that **all** units of basis held on January 1, 2025 are treated as unused *"even if the taxpayer is able to factually attribute some units of basis to specific units of digital assets."* Even perfect records land in the allocation regime.[^lot-1]

**Two allocation methods — and only two:**[^lot-1][^lot-3][^lot-2]

| Method | Mechanic | Timing |
| --- | --- | --- |
| **Specific unit allocation** (§5.02(2)(a)) | Allocate specifically identified units of unused basis, by distinguishing characteristics, to a pool (or specific units) in each wallet. Complete when books first record those characteristics per wallet. | **Earlier of** first post-2024 sale/disposition/transfer of that asset type, **or** the due date (with extensions) of the 2025 return (§5.02(4)) |
| **Global allocation** (§5.02(2)(b)) | A pre-committed **rule** ordering all units of unused basis by distinguishing characteristics and allocating them mechanically across wallets. *"An allocation that permits the taxpayer to exercise discretion on or after January 1, 2025 … is **not** a global allocation."* | Ordering rule must be **written before January 1, 2025**; allocations completed by the **later of** those same two dates (§5.02(5)) |

> **The deadline is widely misstated.** January 1, 2025 is the **snapshot date**, not a general allocation deadline. The only thing that had to exist before that date is the *written global-allocation ordering rule*, and only if that method was chosen. Specific-unit allocation runs on an **earlier-of** test; global allocation on a **later-of** test — the global method deliberately buys time past the first 2025 sale, at the price of surrendering all discretion.[^lot-1] For a calendar-year individual on extension the practical outer bound is the extended 2025 return due date (**October 15, 2026**) — arithmetic from the rule, not an IRS-quoted date, and only where no earlier sale controls. *(Qualified — derived.)* `verified-as-of: 2026-08-04`

**Scope limits (§4).** Available only to a taxpayer holding remaining units **and** having unused basis as of Jan 1, 2025; unavailable for assets acquired or transferred in on or after Jan 1, 2025; applied **separately per asset type** (*"Bitcoin is one type… Ether is another"*), so clean BTC records earn the harbor for BTC even if ETH records fail; and **any allocation is irrevocable** (§4.02(6)).[^lot-1]

**Two hard bars on a "reasonable" allocation:** you may not allocate *previously identified and used* basis (§5.02(7)), and you cannot allocate more basis units into a wallet than it holds remaining units (§5.01). The harbor also **does not cover the *amount* of basis** — that must still be substantiated under §6001 (§5.04).[^lot-1]

### Why universal-basis assumptions break

- **The low-basis lot is stranded.** Under pooling, a trader selling from Wallet A could designate a lot sitting in Wallet B. Post-2025 that is disallowed; allocation is capped at the units each wallet actually holds.[^lot-1]
- **Basis and units get decoupled by pre-2025 history.** §3.08 illustrates a unit bought for $15 sold using $10 of basis borrowed from another lot — leaving orphaned basis with no home. That orphaned inventory *is* the "unused basis" the safe harbor re-homes.[^lot-1]
- **Holding period travels with the basis, not the wallet.** §3.03–§3.04: *"The acquisition date of a digital asset unit must remain with the original basis of that unit."* A careless allocation can convert assumed long-term gain into short-term.[^lot-1]
- **Sold everything before the snapshot = no harbor.** With no remaining units on January 1, 2025, no allocation is possible for that asset type (Example 1, §6.01).[^lot-1]
- **Failing §4.02 forfeits the harbor** and *"may result in the assessment of additional tax, penalties, and interest"* (§5.03). The safe harbor is elective with no filing step — but **Treas. Reg. §1.1012-1(j) is not elective**, so a taxpayer who did nothing must still produce a per-wallet basis position on audit, without the "any reasonable allocation" protection. *(Qualified — synthesis of §4.01(2) and §1.1012-1(j)(6), not an IRS quote.)*[^lot-1]

### Subsequent guidance — what changed, and what did not

**Notice 2025-7** (2025-5 I.R.B. 524, Jan 27, 2025) gave temporary relief allowing alternative methods of **adequate identification for units held in a broker's custody** under §1.1012-1(j)(3)(ii), because brokers lacked the technology to accept standing orders by January 1, 2025.[^lot-3] **Notice 2026-20 extended that relief through December 31, 2026** and modified Notice 2025-7.[^lot-2] `verified-as-of: 2026-08-04`

> **Do not conflate the two reliefs.** Both notices state explicitly that they **do not affect how the Rev. Proc. 2024-28 safe harbor applies**, and Notice 2025-7 §4.04 conditions its relief on the Rev. Proc.'s requirements *already being satisfied*. The extended relief concerns broker-custody identification, not the per-wallet allocation deadline. As of **2026-08-04**, no located guidance extends or postpones Rev. Proc. 2024-28, and none reinstates universal basis.[^lot-3][^lot-2]

**Self-transfers between your own wallets.** Rev. Proc. 2024-28 §3.11 defines "Transfer" as a conveyance *"by one taxpayer to **another** taxpayer,"* which on its face excludes a move between two wallets the same person owns — so it arguably should not trip the §5.02(4)(a) clock. **TENTATIVE:** a textual inference; no IRS statement squarely confirms the self-transfer case, and the Rev. Proc.'s own transfer example involves a different person. Confirm before relying on it.[^lot-1]

### What to maintain, per wallet

1. Total remaining units per wallet/account as of the snapshot (§4.02(4)).
2. Per unit of unused basis: count, original per-unit cost, and the acquisition date of the unit it was attached to (§4.02(5), §3.03–§3.04).
3. The allocation record itself — recording it *is* the completion event for both methods.
4. For global allocation: the written ordering rule, dated before January 1, 2025 (§5.02(5)(a)).
5. Segregated tracking of post-2024 acquisitions held in the same wallet until allocation completes (§5.02(3)).
6. Independent §6001 substantiation of the basis *amount* (§5.04).
7. Pre-2025 disposition history, to exclude already-used basis (§3.08, §5.02(7)).

## 9. Wash Sales and Broker Reporting

*(pending — research incomplete this run; see [Coverage status](#coverage-status--this-run))*

---

## Scope boundaries and cross-references

**This spoke does NOT cover — route elsewhere:**

| Topic | Owner |
| --- | --- |
| Risk & performance **metrics** — Sharpe, Sortino, Calmar, maximum drawdown, expectancy, R-multiples, risk of ruin | `references/trading-risk-management.md` **§4** (R-Multiples and Expectancy), **§6** (Drawdown Control), **§10** (Performance Metrics). This spoke is accounting and attribution, **not** performance measurement. |
| AMM math, price-impact/slippage **mechanism**, MEV sandwich-attack mechanics, LP impermanent-loss derivation | `references/defi-and-onchain-trading.md` §4–§6. This spoke quantifies those as **P&L line items**; it does not re-derive them. |
| General (non-crypto) US trading taxation — §1091 wash-sale **mechanics** for securities generally, the 30-day window arithmetic, substantially-identical analysis, trader tax status, PDT rules, margin regulation | The **`trading-regulation-compliance-and-taxes`** spoke (declared in the hub routing table, **not yet built**). This spoke deliberately does **not** claim that scope. |
| Ordinary individual income-tax filing, brackets, forms | `personal-income-taxes` (consumer-finance family) |

**The wash-sale seam, stated explicitly.** This spoke owns only **whether §1091 reaches digital assets given property treatment, stated with a date**, plus the status of proposals to extend it (§9, pending). The general §1091 mechanics belong to `trading-regulation-compliance-and-taxes` when that spoke is built.

## Coverage status — this run

This reference was produced by a budgeted `/dr` run interrupted by environment-wide API instability; several research agents were lost mid-flight.

| § | Topic | State |
| --- | --- | --- |
| 1 | Realized vs unrealized P&L | **Pending** |
| 2 | The denominator problem | **Complete** — 14 sources |
| 3 | Cost-basis methods | **Pending** |
| 4 | P&L attribution | **Pending** |
| 5 | Gross vs net | **Pending** |
| 6 | Wallet reconciliation | **Pending** |
| 7 | Taxable disposals | **Complete** — 15 sources |
| 8 | Per-wallet tax lots | **Complete** — 4 sources |
| 9 | Wash sales & broker reporting | **Pending** |

Pending sections are marked rather than filled with unsourced prose, because this file's synthesis rule is to assert only what cited sources support. Complete them with `/dr --refresh onchain-pnl-and-tax-accounting`.

## References

**Part A — denominator / numéraire**

[^den-1]: *Numéraire* — Wikipedia (definitional; change-of-numéraire theory, Jamshidian 1989; Geman, El Karoui & Rochet 1995). <https://en.wikipedia.org/wiki/Num%C3%A9raire>
[^den-2]: AnalystPrep — *CFA Level I: Exchange Rates*. <https://analystprep.com/cfa-level-1-exam/economics/exchange-rates/>
[^den-3]: AnalystPrep — *CFA Level I: Foreign Exchange Market*. <https://analystprep.com/cfa-level-1-exam/economics/foreign-exchange-market-2/>
[^den-4]: Corporate Finance Institute — *Cross Rates*. <https://corporatefinanceinstitute.com/resources/foreign-exchange/cross-rates>
[^den-5]: BIS Working Paper No. 905 — *Stablecoins: risks, potential and regulation*. <https://www.bis.org/publ/work905.pdf>
[^den-6]: BIS Working Paper No. 1164 — *Public information and stablecoin runs*. <https://bis.org/publ/work1164.htm>
[^den-7]: CoinDesk (11 Mar 2023) — *Circle Confirms $3.3B of USDC's Cash Reserves Stuck at Failed Silicon Valley Bank*. <https://www.coindesk.com/business/2023/03/11/circle-confirms-33b-of-usdcs-cash-reserves-stuck-at-failed-silicon-valley-bank>
[^den-8]: CNBC (11 Mar 2023) — *Stablecoin USDC breaks dollar peg after firm reveals it has $3.3 billion in SVB exposure*. <https://www.cnbc.com/2023/03/11/stablecoin-usdc-breaks-dollar-peg-after-firm-reveals-it-has-3point3-billion-in-svb-exposure.html>
[^den-9]: Chainalysis — *Crypto Market Reaction to Silicon Valley Bank and USDC Depeg*. <https://www.chainalysis.com/blog/crypto-market-usdc-silicon-valley-bank/>
[^den-10]: Decrypt — *USDC Stablecoin Falls to 87 Cents After Circle Discloses Exposure to Silicon Valley Bank*. <https://decrypt.co/123211/usdc-stablecoin-depegs-90-cents-circle-exposure-silicon-valley-bank>
[^den-11]: Thomson Reuters Practical Law — *Stablecoins Tether and TerraUSD Break Dollar Pegs Attracting Regulatory Scrutiny*. <https://uk.practicallaw.thomsonreuters.com/w-035-5760>
[^den-12]: Harvard Law School Forum on Corporate Governance (22 May 2023) — *Anatomy of a Run: The Terra Luna Crash*. <https://corpgov.law.harvard.edu/2023/05/22/anatomy-of-a-run-the-terra-luna-crash/>
[^den-13]: Bacon, C. (2019) — *Performance Attribution: History and Progress*, CFA Institute Research Foundation. <https://rpc.cfainstitute.org/sites/default/files/-/media/documents/book/rf-lit-review/2019/rflr-performance-attribution.pdf>
[^den-14]: AnalystPrep — *CFA Level III: Active Management and Active Return*. <https://analystprep.com/study-notes/cfa-level-iii/active-management-2/>

**Part B — disposals**

[^disp-1]: IRS **Notice 2014-21** (Mar. 25, 2014; 2014-16 I.R.B. 938) — virtual currency treated as property; Q&A-1, -2, -5, -6, -7. <https://www.irs.gov/pub/irs-drop/n-14-21.pdf> `verified-as-of: 2026-08-04`
[^disp-2]: IRS **Notice 2023-34** — modification of Notice 2014-21; expressly preserves the §4 FAQ answers. <https://www.irs.gov/pub/irs-drop/n-23-34.pdf>
[^disp-3]: IRS **Rev. Rul. 2023-14** — restates property framing; §6045(g)(3)(D) "digital asset" definition. <https://www.irs.gov/pub/irs-drop/rr-23-14.pdf>
[^disp-4]: 26 C.F.R. **§1.1001-1(a)** — realization on exchange of property "differing materially either in kind or in extent." <https://www.law.cornell.edu/cfr/text/26/1.1001-1>
[^disp-5]: IRS — *Frequently Asked Questions on Virtual Currency Transactions* (Q6, Q8, Q14–Q18, Q28–Q30; page last reviewed/updated 30-Jun-2026). <https://www.irs.gov/individuals/international-taxpayers/frequently-asked-questions-on-virtual-currency-transactions> `verified-as-of: 2026-08-04`
[^disp-6]: 26 U.S.C. **§1031** as amended by Pub. L. 115-97 — limited to real property. <https://www.law.cornell.edu/uscode/text/26/1031>
[^disp-7]: IRS Chief Counsel Advice **ILM 202124008** (June 8, 2021) — pre-2018 BTC/ETH/LTC swaps not like-kind; expressly non-precedential. <https://www.irs.gov/pub/irs-wd/202124008.pdf>
[^disp-8]: DLA Piper — *IRS concludes Section 1031 tax-deferred "like-kind" exchange treatment is not available for cryptocurrency trades* (2021). <https://www.dlapiper.com/en/insights/publications/2021/07/irs-concludes-section-1031-tax-deferred-like-kind-exchange-treatment>
[^disp-9]: Lexology — summary reporting an IRS official on case-by-case pre-2018 like-kind evaluation. **TENTATIVE — unverified against a transcript.** <https://www.lexology.com/library/detail.aspx?g=ef6625af-28d5-4985-8dbb-2ebac748323d>
[^disp-10]: IRS **Rev. Rul. 2019-24** (2019-44 I.R.B. 1004) — hard forks and airdrops; dominion and control; basis = amount of income recognized. <https://www.irs.gov/pub/irs-drop/rr-19-24.pdf>
[^disp-11]: IRS **Rev. Rul. 2023-14** (rel. July 31, 2023) — staking rewards included on dominion and control; fn.2 declines to address gas fees. <https://www.irs.gov/pub/irs-drop/rr-23-14.pdf>
[^disp-12]: IRS **Notice 2024-57** (June 2024) — six transaction classes requiring further study (wrapping §3.02, LP §3.03, staking §3.04, lending §3.05, short sales §3.06, NPCs §3.07); express no-inference disclaimer. <https://www.irs.gov/pub/irs-drop/n-24-57.pdf> `verified-as-of: 2026-08-04`
[^disp-13]: Rappaport — *The Taxation of Staking and Wrapping Tokens: Taking the Contrarian View*, Journal of Taxation of Investments. *(Excerpt-level review only.)* <https://www.civicresearchinstitute.com/online/PDF/JTI-3903-01-Rappaport-Tokens.pdf>
[^disp-14]: AICPA — *AICPA tax advocacy on digital assets*, The Tax Adviser (Jan. 2024). <https://www.thetaxadviser.com/issues/2024/jan/aicpa-tax-advocacy-on-digital-assets/>
[^disp-15]: Treasury/IRS **2025-2026 Priority Guidance Plan** — digital-asset transaction treatment listed as an active project. <https://www.irs.gov/pub/irs-counsel/2025-2026-initial-pgp.pdf> `verified-as-of: 2026-08-04`

**Part B — per-wallet tax lots**

[^lot-1]: IRS **Rev. Proc. 2024-28**, 2024-31 I.R.B. 326 (July 29, 2024; effective June 28, 2024) — safe harbor for allocating unused basis of digital assets wallet-by-wallet. <https://www.irs.gov/pub/irs-drop/rp-24-28.pdf> `verified-as-of: 2026-08-04`
[^lot-2]: IRS **Notice 2026-20** — extends Notice 2025-7 relief through December 31, 2026; recites that §1.1012-1(j) applies to acquisitions and dispositions on or after January 1, 2025. <https://www.irs.gov/pub/irs-drop/n-26-20.pdf> `verified-as-of: 2026-08-04`
[^lot-3]: IRS **Notice 2025-7**, 2025-5 I.R.B. 524 (January 27, 2025) — temporary relief for adequate identification of digital-asset units held in a broker's custody under Treas. Reg. §1.1012-1(j)(3)(ii). <https://www.irs.gov/pub/irs-drop/n-25-07.pdf> `verified-as-of: 2026-08-04`
[^lot-4]: The Tax Adviser (AICPA) — *Universal accounting for digital assets concludes, but safe harbor available* (October 2024). <https://www.thetaxadviser.com/news/2024/oct/universal-accounting-for-digital-assets-concludes-but-safe-harbor-available/>
