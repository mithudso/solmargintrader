---
name: options-fundamentals
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  The contract layer of listed options — what you are actually buying or selling.
  Calls vs puts and the asymmetric buyer/writer relationship; strike, expiration,
  premium and the 100-share multiplier; adjusted contracts; intrinsic vs
  extrinsic value and moneyness; American vs European exercise and the share- vs
  cash-settlement consequence; the OCC as issuer and guarantor; exercise,
  assignment, OCC random allocation and exercise-by-exception (the $0.01-ITM
  auto-exercise that closes accounts by surprise); reading an options chain;
  open interest vs volume; LEAPS, weeklies and 0DTE. Educational only — NOT
  financial advice.
keywords:
  - call option
  - put option
  - strike price
  - expiration
  - premium
  - intrinsic value
  - extrinsic value
  - time value
  - moneyness
  - in the money
  - out of the money
  - American exercise
  - European exercise
  - cash settlement
  - physical settlement
  - OCC
  - assignment
  - exercise by exception
  - options chain
  - open interest
  - LEAPS
  - weeklies
  - 0DTE
  - contract multiplier
  - adjusted contract
---

# Options Fundamentals

Sub-reference of **`options-trading-and-strategies`**, itself a spoke of the **`trading-and-investing`** hub. This page owns the **contract**: its terms, its lifecycle, and the operational events that end it. The risk sensitivities are `the-greeks`; what the contract is worth and why is `volatility-and-pricing`; how contracts combine is `strategies-and-risk`.

> **Educational information only — NOT financial, investment, or tax advice.** **A long option can expire worthless: the buyer's maximum loss is 100% of premium paid — provided the
position is closed or expires out of the money — and that is the common outcome, not the rare one.
Left to expire even $0.01 in the money, a long option is auto-exercised (§8) into a stock position
that can lose far more than the premium.** A **writer** of an uncovered option faces losses that are large or, for a naked call, theoretically **unlimited**. Before trading options a broker must deliver the OCC's *Characteristics and Risks of Standardized Options*.[^occ-odd] Volatile facts stamped **as of 2026** — verify with OCC, OIC, Cboe, FINRA, SEC.

## Contents

1. The two contracts, and the asymmetry that defines them
2. The four contract terms
3. The multiplier, and adjusted contracts
4. Moneyness, intrinsic and extrinsic value
5. American vs European, and what settles
6. The OCC — issuer, guarantor, and why there is no counterparty to assess
7. Exercise and assignment
8. Exercise-by-exception — the $0.01 rule that surprises people
9. Reading a chain: bid/ask, volume, open interest
10. The expiry ladder: LEAPS, monthlies, weeklies, 0DTE
11. Anti-patterns

## 1. The two contracts, and the asymmetry that defines them

A **call** gives its **buyer** the *right, not the obligation*, to **buy** the underlying at the strike, on or before expiration. A **put** gives the right to **sell**.

Every contract has two sides, and they are **not mirror images in risk**:

| | Pays / receives | Holds | Maximum loss |
| --- | --- | --- | --- |
| **Buyer (long)** | pays premium | a **right** | the premium — 100%, and no more |
| **Writer (short)** | receives premium | an **obligation** | **large; theoretically unlimited on a naked call** |

This asymmetry is the whole subject in one table. The buyer's loss is bounded and their gain is not; the writer's gain is bounded (the premium) and their loss is not. Any claim that writing options is "safe income" is a claim about *probability*, never about *magnitude* — and the two are routinely conflated when these strategies are sold.

**A right is only exercised when it pays.** Nobody exercises a call to buy at $110 when the stock is $90; they let it expire. That is precisely why the payoff is bent, and the bend is what §4's extrinsic value is priced on.

## 2. The four contract terms

An option is fully specified by four things plus the underlying:

1. **Type** — call or put.
2. **Underlying** — a specific stock, ETF, or index. `AAPL` options and `SPY` options are unrelated instruments.
3. **Strike price** — the transaction price the right refers to.
4. **Expiration** — the date the right ends. US listed equity options expire at the close of the third Friday of the month for standard monthlies (technically expiring the following Saturday historically; now Friday), with weeklies and dailies alongside.

The **premium** is not a term — it is the *price*, discovered in the market, and it is what `volatility-and-pricing` explains.

Quoted premiums are **per share**. A $2.40 quote on a standard 100-share contract costs **$240**.

## 3. The multiplier, and adjusted contracts

A standard US equity/ETF option covers **100 shares**.[^occ-spec] Every quoted price must be multiplied by 100 to get cash, and every strike must be multiplied by 100 to get the notional the contract controls: a $150 strike controls **$15,000** of stock.

**Adjusted contracts.** Corporate actions — splits, spin-offs, mergers, special dividends — cause the OCC to **adjust** outstanding contracts, changing the deliverable, the strike, or the multiplier. An adjusted contract may deliver an odd number of shares, cash, or a basket. They are a common source of "the maths on my position makes no sense": the ticker looks normal and the deliverable is not. The OCC publishes an information memo for every adjustment.[^occ-spec]

**Index options have no shares at all** — see §5.

## 4. Moneyness, intrinsic and extrinsic value

**Premium = intrinsic value + extrinsic value.**

**Intrinsic value** is what the right is worth if exercised immediately, floored at zero:
- Call: `max(0, spot − strike)`
- Put: `max(0, strike − spot)`

**Moneyness** names the relationship:
- **In the money (ITM)** — intrinsic value > 0.
- **At the money (ATM)** — spot ≈ strike.
- **Out of the money (OTM)** — intrinsic value is zero. **An OTM option is entirely extrinsic value**, which is why it can go to zero without the stock moving against you at all.

**Extrinsic (time) value** is everything else: what the market charges for the *possibility* of favourable movement before expiry. It is driven by time remaining and by **implied volatility**, and it **decays to exactly zero at expiration**. At expiry, every option is worth precisely its intrinsic value.

**The consequence that catches people:** you can be right about direction and still lose, because you paid for extrinsic value that decayed faster than the stock moved. That is not bad luck; it is the instrument working as designed. `the-greeks` quantifies it as theta, and `volatility-and-pricing` covers the IV-crush version.

## 5. American vs European, and what settles

Two independent properties that in US listed markets happen to correlate:

**Exercise style**
- **American** — exercisable **any time** before expiry. US equity and ETF options are American.[^oic-exercise]
- **European** — exercisable **only at expiration**. Most broad-based index options (SPX) are European.[^cboe-eu]

**Settlement**
- **Physical / share settlement** — exercise delivers 100 shares. Equity and ETF options.
- **Cash settlement** — exercise pays the cash difference against a settlement value. Index options.[^cboe-eu]

**Why this pairing matters more than it looks.** Consider two ways to trade "the S&P 500":

| | `SPY` options | `SPX` options |
| --- | --- | --- |
| Exercise | American | European |
| Settlement | 100 SPY shares | cash |
| Early-assignment risk | **yes** | **no** |
| Pin risk at expiry | **yes** | **no** |
| US tax treatment | equity option | **§1256 60/40** (broad-based index) |
| Settlement value | continuous, on the underlying | **standard 3rd-Friday SPX: AM-settled from the SOQ (ticker SET) on Friday's *open*, last trading day Thursday. SPXW weeklys, including all 0DTE: PM-settled on the close** |

**Cash settlement removes assignment and pin risk but substitutes settlement-value risk.** A standard
SPX position is struck against Friday's **opening** Special Opening Quotation, which you cannot trade
against — its last trading day is the Thursday before — and the SOQ can print away from Thursday's
close if component opens are imbalanced. Since a **June 2026 Cboe rule change permitting AM-settled
SPX options on any weekday, AM vs PM can no longer be inferred from the expiry day**; check the
series.[^cboe-am-settle]

Same market view, materially different operational and tax profile. The tax asymmetry is real and surprises people: **broad-based index options get §1256 60/40 treatment; ETF options on the same index do not.**[^tax-1256] Detail → `trading-regulation-compliance-and-taxes`, which is **declared in the hub routing table but not yet built** as of 2026 — go to IRS Topic 429 and Pub. 550 directly.

## 6. The OCC — issuer, guarantor, and why there is no counterparty to assess

The **Options Clearing Corporation** is the issuer of and guarantor for every listed US option.[^occ-spec] After a trade matches, the OCC interposes itself: it becomes buyer to every seller and seller to every buyer.

Two consequences:

1. **You never assess who is on the other side.** Unlike an OTC forward or swap (see `derivatives-futures-and-swaps` §8), there is no counterparty due diligence in listed options, because the counterparty is the clearing house.
2. **The obligation is enforced by margin, not goodwill.** A short option's risk is managed through the writer's broker and margin requirements. The guarantee is to the *market*, not to the writer's account.

## 7. Exercise and assignment

**Exercise** is what a *long* holder does — invoking the right. **Assignment** is what happens to a *short* — being required to perform.

The path: long holder exercises → OCC → allocates to a clearing member holding short positions →
member allocates to a customer by a **fixed, FINRA-approved and customer-disclosed method — random
selection, FIFO, or another equally random basis** (FINRA Rule 2360; "random" is the common choice,
not the only permitted one).[^finra-alloc] So:

- **You cannot predict whether *you specifically* will be allocated**, and being picked is not a signal
  about anything.
- **You can, however, prevent assignment** — by closing the short before exercise occurs. That is the
  standard remedy, and it is why the ex-dividend calendar below is actionable rather than merely
  ominous.
- **What is substantially predictable is whether holders have an economic reason to exercise** (below).
  Do not confuse the randomness of *allocation* with unpredictability of *exercise*.
- **Early assignment is possible any time** on an American short.

**When early assignment is actually rational** (and therefore likely):
- **Short calls, just before ex-dividend.** If the dividend exceeds the call's remaining extrinsic value, exercising early to capture it is rational. **This is the single most predictable early-assignment event**, and it lands on covered-call and call-spread writers who were not watching the dividend calendar.
- **Deep-ITM short puts**, where remaining extrinsic value has collapsed and the holder prefers cash now.

**Assignment consequences to plan for:** you receive or deliver 100 shares per contract, which may create a stock position far larger than intended, a margin call over a weekend, or — on a spread — a position where one leg assigned and the other did not (**leg risk**).

## 8. Exercise-by-exception — the $0.01 rule that surprises people

At expiration the OCC **automatically exercises** long options that are in the money by **$0.01 or more**, unless the holder instructs otherwise. This is **exercise-by-exception**, sometimes "ex-by-ex".[^oic-exercise]

Why it matters, stated plainly: **a long call you had written off as worthless, sitting $0.01 ITM at the close, will be exercised into a 100-share purchase you did not intend and may not be able to fund.** The account is long stock on Monday with a margin call attached. The same applies to a short leg being assigned while your long leg expires just OTM, converting a defined-risk spread into a naked stock position over a weekend.

**Two operational habits follow:** close positions rather than letting them expire near the money, and know your broker's cut-off for contrary exercise instructions — brokers may auto-liquidate rather than fund an unwanted exercise.

## 9. Reading a chain: bid/ask, volume, open interest

An **options chain** lists, per expiry, every strike with quotes for calls and puts.

- **Bid/ask spread** is a real, recurring cost. Options are far less liquid than their underlying, and multi-leg strategies pay the spread on **every leg**. A four-leg iron condor crosses four spreads to open and four to close. In illiquid names this can exceed the strategy's theoretical edge outright — which is why liquidity is a *strategy selection criterion*, not a detail.
- **Volume** — contracts traded today. Resets daily.
- **Open interest** — contracts currently **outstanding** (opened and not yet closed, exercised, or expired). Persists.

**The distinction is the useful part.** High volume with low open interest means positions opening and
closing intraday. High open interest with low volume means a large established position that is not
currently being traded — **which is not the same as being easy to exit.** Open interest is a *stock*
and tells you how large the outstanding position base is; **whether you can get out today is a *flow*
question, answered by current volume, the bid/ask width and the displayed size.** High OI with no
volume and a wide market is the classic hard-to-exit series. Read them together.

Use limit orders and, for multi-leg positions, a **single net debit/credit order on the combination** rather than legging in — legging exposes you to the market moving between fills.

## 10. The expiry ladder: LEAPS, monthlies, weeklies, 0DTE

- **LEAPS** — long-dated, over a year to expiry. Dominated by extrinsic value; sensitive to volatility and to **rates** (the one place rho matters).
- **Monthlies** — the standard third-Friday cycle, historically the deepest liquidity.
- **Weeklies** — expiring most Fridays; on the most active underlyings, multiple expiries per week.
- **0DTE** — options on their expiration day. On SPX these have grown to a **majority** of that product's volume (**~59% of SPX volume in full-year
2025, up from ~47% in 2024 — verify current, this figure moves fast**).[^cboe-0dte] Note that **0DTE
SPX contracts are SPXW (PM-settled), not the AM-settled standard series** (§5).

**What changes as expiry shortens.** Extrinsic value is small, so the contract is cheap in dollar terms and **enormously sensitive in percentage terms**: gamma is at its maximum and theta is at its most brutal (`the-greeks` §3–§4). A 0DTE position can lose its entire value in minutes without any unusual move in the underlying. The low ticket price is what makes them feel low-risk; the gamma is what makes them not.

## 11. Anti-patterns

1. **Reading the premium as the position size.** A $2.40 premium controls $15,000 of stock at a $150 strike. Size on notional and on maximum loss, not on ticket cost.
2. **Letting a near-the-money long expire.** Exercise-by-exception (§8) turns $0.01 of intrinsic value into an unfunded 100-share purchase.
3. **Writing covered calls through an ex-dividend date** without checking whether the dividend exceeds remaining extrinsic value (§7).
4. **Treating an OTM option as "cheap".** It is 100% extrinsic value; its most likely terminal value is zero.
5. **Assuming a spread cannot become a naked position.** One leg assigned and the other expiring worthless does exactly that.
6. **Trading SPY options while quoting SPX tax treatment.** §1256 applies to broad-based index options, not ETF options (§5).
7. **Ignoring the multiplier on adjusted contracts.** After a corporate action the deliverable may not be 100 shares (§3).
8. **Legging into a multi-leg position.** Use one net-debit/credit combination order (§9).
9. **Judging liquidity by either volume or open interest alone.** OI shows the outstanding position base; current volume and quoted width show whether you can actually trade out of it (§9).
10. **Confusing delta with the probability of profit.** That is a `the-greeks` §2 error, and it is the most common one in this family.

## References (sources)

[^occ-odd]: Options Clearing Corporation — *Characteristics and Risks of Standardized Options* (the Options Disclosure Document; mandatory pre-trade risk disclosure). https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document — tier-1 (clearing house / regulator-mandated disclosure). verified-as-of: 2026-08-05
[^occ-spec]: OCC — Equity Options Product Specifications (the 100-share contract unit, physical settlement, and that corporate actions can produce adjusted contracts of other than 100 shares). https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications — tier-1 (clearing house). Supports **§3 only**. Per-adjustment detail is published separately as OCC **Information Memos**; the issuer/guarantor role in §6 rests on OCC's By-Laws and the ODD (`[^occ-odd]`), not on this page. verified-as-of: 2026-08-05
[^finra-alloc]: FINRA — Rule 2360(b)(23)(C) and the Options Allocation/Exercise & Assignment guidance: a member must use a fixed, disclosed allocation method — random selection, FIFO, or another equally random basis. https://www.finra.org/filing-reporting/regulatory-filing-systems/options-allocation-exercise-assignment-notices — tier-1 (SRO). Supports §7; corrects the earlier "exchange-approved procedure that is typically random". verified-as-of: 2026-08-05
[^cboe-am-settle]: Cboe — *Settlement of Standard AM-Settled S&P 500 Index Options* (the SOQ / ticker SET mechanism, Thursday last-trading-day for the standard series) and the June 2026 SEC-approved rule change permitting AM-settled SPX options on any weekday. https://www.cboe.com/tradable_products/sp_500/spx_options/specifications/ — tier-1 (exchange). Supports §5's settlement-value row. **Volatile — the AM/PM listing rules changed in 2026; verify the specific series.** verified-as-of: 2026-08-05
[^oic-exercise]: Options Industry Council — Options Exercise & Assignment FAQ (American vs European, OCC allocation to clearing members and typically random customer allocation, exercise-by-exception at $0.01 ITM, early-assignment economics around ex-dividend). https://www.optionseducation.org/referencelibrary/faq/options-exercise — tier-1 (authoritative industry education, OCC-sponsored). Supports §5, §7, §8. verified-as-of: 2026-08-05
[^cboe-eu]: Cboe — SPX / Mini-SPX (XSP) product pages (European-style exercise, cash settlement, broad-based index). https://www.cboe.com/tradable_products/sp_500/ — tier-1 (exchange). Supports §5. verified-as-of: 2026-08-05
[^cboe-0dte]: Cboe — "The State of the Options Industry" quarterly posts and the full-year volume releases carrying the SPX 0DTE share (~47% in 2024, ~59% in full-year 2025). https://www.cboe.com/insights/posts/the-state-of-the-options-industry-quarter-three-2025/ and https://ir.cboe.com/news — tier-1 (exchange / investor relations). Supports §10. **Volatile — this figure has risen every year recently; re-verify rather than quoting it forward.** verified-as-of: 2026-08-05
[^tax-1256]: Cboe — "Index Options Benefits & Tax Treatment" (§1256 60/40 applies to broad-based index options, not equity/ETF options); corroborated by IRS Topic No. 429. https://www.cboe.com/tradable_products/index-options-benefits-tax-treatment/ — tier-1 (exchange) + tier-1 (IRS). Pointer only; detail → `trading-regulation-compliance-and-taxes`. verified-as-of: 2026-08-05
