---
name: trading-regulation-compliance-and-taxes
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  The rulebook and the IRS for an active US trader. Who regulates what (SEC,
  FINRA, CFTC, NFA) and which protection covers you (SIPC, and what it does not
  cover); the Pattern Day Trader rule AND the risk-based intraday-margin
  framework replacing it effective 4 June 2026; Reg T margin and short-sale
  rules; then the tax half — short vs long-term capital gains, the WASH-SALE rule
  including the 30-day-either-side window and the substantially-identical test,
  Section 1256 60/40 mark-to-market and which instruments qualify, the
  constructive-sale and straddle rules, trader tax status and the §475(f)
  mark-to-market election with its deadline trap, and recordkeeping. Educational
  only — NOT tax, legal or financial advice.
keywords:
  - SEC
  - FINRA
  - CFTC
  - NFA
  - SIPC
  - pattern day trader
  - PDT
  - intraday margin
  - Regulation T
  - short selling
  - Regulation SHO
  - wash sale
  - substantially identical
  - capital gains
  - Section 1256
  - 60/40
  - mark to market
  - Section 475
  - trader tax status
  - constructive sale
  - straddle rules
  - Form 8949
  - Form 6781
  - Schedule D
  - cost basis
---

# Trading Regulation, Compliance & Taxes (spoke)

A spoke of the **`trading-and-investing`** hub. Three other references defer their tax detail here — `options-fundamentals` §5, `derivatives-futures-and-swaps` §12, and `strategies-and-risk`. Crypto-specific tax lots, token-to-token disposals and the crypto wash-sale question are owned by **`onchain-pnl-and-tax-accounting`**, not this page.

> **Educational information only — NOT tax, legal, investment or financial advice.** Tax law is fact-specific, changes annually, and the penalties for getting it wrong are real. **Nothing here is a substitute for a CPA or tax attorney who has seen your actual records**, and several items below (trader tax status, the §475(f) election, straddle rules) are areas where professional advice is close to mandatory rather than optional. Every figure and rule is stamped **as of 2026** and must be verified against the primary source — IRS publications and the regulator itself — before you file or act. Dollar thresholds, brackets and forms change every year.

## Contents

1. Who regulates what, and what each protects
2. SIPC — what it covers and the three things it does not
3. Pattern Day Trader, and the framework replacing it in 2026
4. Margin: Regulation T and the maintenance layer
5. Short selling: locate, close-out, and the borrow
6. Capital gains: the short/long split and why turnover is the tax problem
7. The wash-sale rule
8. Section 1256: mark-to-market and 60/40
9. Constructive sales and the straddle rules
10. Trader tax status and the §475(f) election
11. Recordkeeping, forms, and the 1099-B reconciliation
12. Anti-patterns

## 1. Who regulates what, and what each protects

| Body | Type | Covers | Check a firm/person at |
| --- | --- | --- | --- |
| **SEC** | federal agency | securities: stocks, bonds, ETFs, listed options, security-based swaps | Investor.gov / EDGAR |
| **FINRA** | SRO (not a government agency) | broker-dealers and registered reps; writes the PDT and margin rules | **BrokerCheck** |
| **CFTC** | federal agency | futures, most swaps, retail forex | CFTC.gov |
| **NFA** | SRO | FCMs, introducing brokers, CTAs, CPOs | **NFA BASIC** |
| **SIPC** | non-profit created by statute (SIPA) | *custody* failure of a member broker-dealer — see §2 | sipc.org member list |

**The distinction that matters operationally:** your equity broker is checked on **BrokerCheck**; your futures broker (FCM) is checked on **NFA BASIC**. Looking for a futures firm on BrokerCheck and finding nothing is not evidence of a problem — it is the wrong database.[^finra-bc][^cftc]

**FINRA is not a government agency.** It is a self-regulatory organisation overseen by the SEC. Its rules are enforceable against members, and it is where the day-trading and margin rules actually live.

## 2. SIPC — what it covers and the three things it does not

SIPC protects **custody**: if a member broker-dealer fails and customer assets are missing, SIPC covers up to **$500,000 per customer, of which $250,000 may be cash** (as of 2026 — verify).[^sipc]

**What SIPC does not cover, and this is where nearly all confusion sits:**

1. **Market losses.** SIPC is not insurance against being wrong. If your stock goes to zero, that is not a SIPC claim.
2. **Futures positions** in a commodity account. Futures are CFTC-regulated and fall outside SIPA (a narrow exception exists for futures carried in an SEC-approved portfolio-margining *securities* account). Futures customers rely on **segregation** requirements and, in an FCM failure, the CFTC's bankruptcy regime instead.[^sipc]
3. **Crypto held at most crypto platforms.** A platform that is not a SIPC-member broker-dealer carries no SIPC protection whatever its marketing implies; the assets may also not be legally segregated from the firm's own, which is the exposure the 2022 platform failures made concrete.

**"SIPC insured" is also not FDIC.** FDIC covers bank deposits; SIPC covers brokerage custody. Different statute, different failure mode, different limits.

## 3. Pattern Day Trader, and the framework replacing it in 2026

**This is the single most stale rule in retail trading commentary, and the change is imminent.**

**The legacy rule (FINRA 4210).** A **pattern day trader** is an account executing **four or more day trades within five business days**, where those day trades exceed 6% of total trading activity in that period. A flagged account must maintain **$25,000** minimum equity and may only day-trade in a **margin** account. Fall below $25,000 and day-trading is prohibited until it is restored.

**The replacement.** FINRA amended Rule 4210 to **eliminate the PDT designation and the $25,000 minimum**, substituting a **risk-based intraday-margin framework**, **effective 4 June 2026**, with a transition period running to **20 October 2027**.[^finra-pdt]

**What this means in practice, stated carefully:**

- Most third-party material — including a great deal of broker-published educational content — still describes the $25k rule as current. **As of 2026 it is being replaced, and during the transition period both frameworks may be encountered.**
- **Your broker's policy is the operative constraint, not the floor rule.** Brokers may impose stricter requirements than FINRA's minimum, and many will. Verify with yours.
- The change does not make day trading safer. It changes the *margin* requirement, not the [`investing-vs-trading`](investing-vs-trading.md) evidence that most active retail traders underperform.

**Cash accounts were never subject to PDT** — but they are subject to settlement. Buying with unsettled proceeds and selling before settlement is a **free-riding** violation, which triggers a 90-day restriction. T+1 settlement (since May 2024) shortened the window but did not remove the rule.

## 4. Margin: Regulation T and the maintenance layer

Three layers, commonly conflated:

1. **Reg T initial margin** (Federal Reserve): generally **50%** of the purchase price for a marginable equity — you may borrow up to half.
2. **FINRA/exchange maintenance margin**: generally **25%** minimum equity thereafter. Fall below and you get a **maintenance call**.
3. **House requirements**: whatever your broker sets, which is often higher — and can be raised **without notice**, including on a specific volatile security.

**Two properties of margin that surprise people, both of them structural:**

- **The broker may liquidate without contacting you** to meet a call. The account agreement grants that right; a "margin call" is not necessarily a request you get to answer.
- **Margin interest accrues on the debit balance** and is a real, compounding cost. It is also the point of contrast with futures margin, which is a performance bond and carries no interest — see `derivatives-futures-and-swaps` §3.

**Portfolio margin** is an alternative risk-based regime available to larger accounts, which can allow substantially more leverage. More leverage is not a benefit in itself.

## 5. Short selling: locate, close-out, and the borrow

Selling short requires a **margin account** and requires the broker to **locate** borrowable shares (Regulation SHO Rule 203). Mechanics and strategy → `stock-and-equity-trading`; here, the compliance layer:

- **Locate requirement.** A broker must have reasonable grounds to believe the security can be borrowed before accepting a short sale. This is why a short can be refused in a hard-to-borrow name.
- **Close-out / threshold securities.** Persistent fails-to-deliver put a security on a threshold list, forcing close-out.
- **Borrow cost is not fixed.** The rate can rise sharply, and shares can be **recalled** — forcing a buy-in at the worst possible moment. A short position's cost is path-dependent in a way a long's is not.
- **Short-sale price test (the "alternative uptick rule", Rule 201).** Triggered when a security falls 10% intraday, restricting short selling at or below the national best bid for the rest of that day and the next.
- **Dividends on borrowed shares are your obligation.** Short a stock through its ex-dividend date and you owe the dividend.

## 6. Capital gains: the short/long split and why turnover is the tax problem

- **Short-term** — held **one year or less**. Taxed at **ordinary income rates**.
- **Long-term** — held **more than one year**. Taxed at preferential rates (0/15/20% brackets as of 2026, plus the 3.8% net investment income tax above threshold — verify current figures).[^irs-topic409]

**The structural point for an active trader:** frequent trading makes essentially all gains short-term, so **an active strategy is taxed at ordinary rates while a buy-and-hold one is not.** That is a real, quantifiable drag which most backtests omit entirely — a strategy must clear its tax rate as well as its costs. See `investing-vs-trading` for the pre-tax evidence, which is already unfavourable before this is applied.

**Holding period counts from the day after acquisition through the disposal date**, and specific rules can suspend it (§9's straddle rules do exactly that).

## 7. The wash-sale rule

**The rule (IRC §1091).** If you sell a security at a **loss** and buy a **substantially identical** security within **30 days before or after** the sale, the loss is **disallowed** for that year. The disallowed loss is added to the basis of the replacement position and its holding period is adjusted.[^irs-pub550]

Four features that generate almost all real-world errors:

1. **The window is 61 days, not 30** — thirty days before, the sale day, and thirty days after. Buying *first* and then selling the older lot at a loss triggers it just as well.
2. **Losses only.** Gains are never washed.
3. **"Substantially identical" is not defined by a bright line.** The same stock plainly is. Options on it can be. Two different ETFs tracking the same index are a genuinely uncertain area. **Bonds and options both have their own case-specific treatment, and this is where a professional earns their fee.**
4. **It applies across your accounts, including your IRA.** Repurchasing in an IRA after a taxable-account loss disallows the loss **permanently** — there is no basis to add it to. This is the most expensive version of the mistake.

**Why it bites active traders hardest:** a strategy that re-enters the same instrument repeatedly can generate a long chain of disallowed losses, deferring recognition to the final closing trade. If that trade falls in the next tax year, you can owe tax on a year you lost money in. The §475(f) election in §10 is the standard structural answer.

## 8. Section 1256: mark-to-market and 60/40

**Section 1256 contracts** receive two distinctive treatments:[^irs-1256]

1. **Marked to market at year end** — open positions are treated as sold at fair value on the last business day, whether or not you closed them.
2. **60/40** — gains and losses are **60% long-term / 40% short-term regardless of holding period.** A contract held ten minutes gets 60% long-term treatment.

**What qualifies (as of 2026 — verify):** regulated futures contracts, foreign currency contracts, non-equity options, dealer equity options, and **broad-based stock index options**.

**What does not:** **equity and ETF options.** This is the asymmetry that catches people, and it is worth stating as a pair:

- **SPX** options — broad-based index → **§1256, 60/40**.
- **SPY** options — options on an ETF → **not §1256**; ordinary equity-option treatment.

Same underlying exposure, different tax regime. See `options-fundamentals` §5, where the operational differences (early assignment, pin risk, settlement) line up alongside this one.

**Crypto perpetuals are generally not §1256 contracts** — do not assume 60/40. A perpetual listed on a US DCM may be a different case, and that classification is itself contested; see `derivatives-futures-and-swaps` §10 and §12. Crypto P&L → `onchain-pnl-and-tax-accounting`.

**60/40 is not automatically favourable.** Year-end mark-to-market removes your ability to defer a gain by not selling. Losses have a limited three-year carryback election against prior §1256 gains (Form 6781).

## 9. Constructive sales and the straddle rules

Two anti-abuse regimes that exist to stop you locking in a gain or a loss without a taxable event. Both are easy to trip accidentally with options.

**Constructive sale (§1259).** Entering an offsetting position against an **appreciated** holding — a short against the box, certain forward contracts, some offsetting options — can be treated as a **sale of the appreciated position**, triggering gain now. The naive "I'll hedge instead of selling, to defer the tax" plan is precisely what this targets.

**Straddle rules (§1092).** Where you hold **offsetting positions** in personal property, losses on one leg are **deferred** to the extent of unrecognised gain on the other, the **holding period can be suspended** (killing long-term treatment), and certain carrying costs must be capitalised. A protective put against a stock position can create a straddle. There are identified-straddle and qualified-covered-call exceptions with specific conditions.

**Honest statement of scope:** these two areas are more complex than a reference page can responsibly resolve, and the interactions with covered calls and collars are fact-specific. If you hedge appreciated positions with options, **get advice before the trade, not at filing time.**[^irs-pub550]

## 10. Trader tax status and the §475(f) election

**Trader tax status (TTS)** is not an election or a checkbox — it is a **facts-and-circumstances determination** that your activity rises to a trade or business: substantial, frequent, regular and continuous, seeking profit from short-term swings rather than dividends or appreciation. There is **no statutory bright line** on trade count or dollar volume; the standard comes from case law.[^irs-topic429]

If you qualify, trading expenses become business expenses rather than (largely non-deductible) investment expenses.

**The §475(f) mark-to-market election** is separate and is the structural fix for §7:

- **Wash-sale rules no longer apply** to the electing activity.
- Gains and losses become **ordinary**, and the **$3,000 capital-loss limitation no longer applies** — a large trading loss becomes fully deductible against ordinary income.
- The cost: you forfeit long-term capital-gain treatment on trading positions, and all open positions are marked at year end.

**The deadline trap, which is the single most consequential item in this section.** For an existing individual taxpayer the election must generally be made by the **due date of the prior year's return, without extensions** — i.e. you elect *in advance* of the year it applies to. **You cannot decide in January that last year's losses should have been ordinary.** Missing the date is not curable by amending. New taxpayers and entities follow different timing.

**Consequence for anyone reading this after a losing year:** the relief you want may already be unavailable for that year, and available for the next one only if you act by the deadline. This is the clearest case on the page for talking to a CPA now rather than at filing.

## 11. Recordkeeping, forms, and the 1099-B reconciliation

**Forms you will meet:**

| Form | Carries |
| --- | --- |
| **1099-B** | broker-reported proceeds and, for covered securities, basis |
| **Form 8949** → **Schedule D** | per-disposal capital gains and losses |
| **Form 6781** | §1256 contracts (60/40) and straddles |
| **Form 4797** | §475(f) mark-to-market gains and losses (not Schedule D) |
| **1099-DA** | digital-asset broker reporting → `onchain-pnl-and-tax-accounting` |

**Reconcile the 1099-B rather than trusting it.** Broker basis reporting is frequently incomplete or adjusted in ways that will not match your own records — wash-sale adjustments are reported per-account and per-security and will not capture activity across brokers or into an IRA, options basis adjustments from exercise and assignment are a common gap, and **transfers between brokers routinely lose basis**. The reconciliation is your responsibility.

**Keep, per trade:** date acquired, date sold, proceeds, basis, fees, and enough identification to support your **cost-basis method**. Specific-lot identification must be made at or before the sale to be respected; the default is FIFO. Method mechanics → `onchain-pnl-and-tax-accounting`, which covers them in depth for the crypto case.

## 12. Anti-patterns

1. **Quoting the $25,000 PDT rule as current.** It is being replaced by a risk-based intraday-margin framework effective 4 June 2026 (§3).
2. **Treating SIPC as protection against losses.** It covers custody failure, not being wrong (§2).
3. **Expecting SIPC to cover futures or a crypto platform.** It generally does not (§2).
4. **Thinking the wash-sale window is 30 days.** It is 61 — thirty each side plus the sale day (§7).
5. **Repurchasing in an IRA after a taxable loss.** The loss is disallowed **permanently** (§7).
6. **Assuming SPY options get 60/40 because SPX does.** Broad-based index options qualify; ETF options do not (§8).
7. **Assuming crypto perps are §1256.** Generally not (§8).
8. **Hedging an appreciated position to defer tax.** That is what the constructive-sale rule targets (§9).
9. **Deciding on §475(f) after the loss year.** The election generally had to be filed by the prior year's due date without extensions (§10).
10. **Filing straight from the 1099-B.** Wash-sale and options-basis adjustments will not reconcile across accounts (§11).
11. **Backtesting a high-turnover strategy without a tax rate.** Short-term gains are taxed as ordinary income; the strategy must clear that too (§6).
12. **Using this page instead of a professional** on trader tax status, the §475 election, or straddles. Those three are where the money and the risk are.

## References (sources)

[^finra-bc]: FINRA — BrokerCheck, and FINRA's description of its own status as an SRO overseen by the SEC. https://brokercheck.finra.org/ — tier-1 (SRO). Supports §1. verified-as-of: 2026-08-05
[^cftc]: CFTC — regulatory scope over futures, most swaps and retail forex; NFA BASIC for FCM/IB/CTA/CPO background checks. https://www.cftc.gov/ and https://www.nfa.futures.org/basicnet/ — tier-1 (regulator + SRO). Supports §1. verified-as-of: 2026-08-05
[^sipc]: SIPC — what SIPC protects, the $500,000 / $250,000-cash limits, and the exclusions including commodity-account futures. https://www.sipc.org/for-investors/what-sipc-protects — tier-1 (the statutory protection corporation). Supports §2. **Volatile: limits change by statute — verify.** verified-as-of: 2026-08-05
[^finra-pdt]: FINRA — "Intraday Margin Requirements" investor insight and the Rule 4210 amendments: the PDT designation and $25,000 minimum are replaced by a risk-based intraday-margin framework **effective 4 June 2026**, with a transition period through **20 October 2027**. https://www.finra.org/investors/insights/intraday-margin-requirements — tier-1 (SRO, and the rule's author). Supports §3. **The highest-stakes volatile fact on this page — verify both the rule and your broker's policy.** verified-as-of: 2026-08-05
[^irs-topic409]: IRS — Topic No. 409, Capital Gains and Losses (holding-period split, preferential long-term rates, the $3,000 capital-loss limitation). https://www.irs.gov/taxtopics/tc409 — tier-1 (tax authority). Supports §6. **Brackets and thresholds change annually.** verified-as-of: 2026-08-05
[^irs-pub550]: IRS — Publication 550, *Investment Income and Expenses*: the §1091 wash-sale rule including the 30-day-either-side window and substantially-identical treatment, the §1092 straddle rules, and the §1259 constructive-sale rules. https://www.irs.gov/publications/p550 — tier-1 (tax authority). Supports §7 and §9. verified-as-of: 2026-08-05
[^irs-1256]: IRS — Topic No. 429 and Publication 550 on Section 1256 contracts: year-end mark-to-market, 60/40 treatment regardless of holding period, the qualifying instrument list, and Form 6781 including the three-year loss carryback election. https://www.irs.gov/taxtopics/tc429 — tier-1 (tax authority). Supports §8. verified-as-of: 2026-08-05
[^irs-topic429]: IRS — Topic No. 429, *Traders in Securities (Information for Form 1040 Filers)*: trader-vs-investor as a facts-and-circumstances determination with no statutory bright line, and the §475(f) mark-to-market election including its timing requirement. https://www.irs.gov/taxtopics/tc429 — tier-1 (tax authority). Supports §10. **The election deadline is unforgiving; confirm current-year timing with a professional.** verified-as-of: 2026-08-05
