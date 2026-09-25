---
name: stock-and-equity-trading
# provenance: created 2026-06-16 via /dr deep-research as spoke #1 of the trading-and-investing hub; split 2026-08-04 (§2-§4 moved out). Frontmatter added at split time — this file previously carried only the HTML provenance comment below; its routing description lives in the hub SKILL.md.
hub: trading-and-investing
version: "1.1.0"
updated: "2026-08-04"
verified-as-of: "2026-06-16"
category: reference
metadata:
  changelog:
    - "2026-08-04 v1.1.0 — SPLIT FOR SIZE, nothing lost or reworded: §2 (fundamental analysis), §3 (dividends/buybacks/splits) and §4 (primary market) moved verbatim with footnotes 14-49 to references/equity-fundamentals-and-corporate-actions.md. This file keeps §1, §5, §6 and footnotes 1-13 and 50-69. Numbering unchanged on both sides; pointer rows sit where the moved sections were."
    - "2026-06-16 v1.0.0 — created via /dr deep-research (6 concepts; ~40 independent regulator/exchange/index-provider/peer-reviewed sources)."
---

<!-- Provenance: spoke reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research (6 concepts; ~40 independent sources, regulator/exchange/index-provider/peer-reviewed grade). Educational only — NOT financial/investment/tax advice. Volatile claims dated "as of 2026". -->

# Stock & Equity Trading (spoke)

The **equity** spoke of the `trading-and-investing` family: trading individual stocks (and equity ETFs as instruments) from a US retail participant's seat — what a share *is*, how equities trade and are priced, how to read a company's fundamentals, the corporate actions that move a stock, the primary market that creates new shares, the long/short mechanics specific to equities, and the central question of **active stock-picking vs passive index investing**.

> **Educational information only — NOT financial, investment, tax, or legal advice, and NOT a recommendation to buy, sell, or hold any security.** Equities carry **risk of loss**; a stock can fall to **$0** (you lose 100%), and **short selling can lose more than you invest** (losses are theoretically unlimited). The evidence below is blunt that **active stock-picking underperforms a low-cost index for the large majority of participants**. Rules, tax treatment, and the vendor/market landscape change — every volatile claim here is stamped **as of 2026**; verify current facts with the primary regulator (SEC/Investor.gov, FINRA) before acting. For a personal decision, consult a licensed professional.

**This spoke builds on the hub foundation — read those first, not re-derived here:** asset-class definition of equities → `references/asset-classes-and-instruments.md`; exchanges, clearing/settlement (T+1), bid-ask spread, primary vs secondary market → `references/market-participants-and-structure.md`; order types and routing (PFOF, NBBO) → `references/order-lifecycle-and-execution.md`; sessions/circuit breakers → `references/market-sessions-and-venues.md`; the investing-vs-trading distinction and the underperformance evidence overview → `references/investing-vs-trading.md`; margin, the Pattern-Day-Trader rule and its 2026 replacement, short-selling overview, SIPC → `references/trading-risks-and-protections.md`.

**Peer-spoke handoffs (SKIP edges — go there for depth):**
- Listed **options** on equities (calls/puts, the Greeks, spreads, the gamma squeeze mechanics) → `options-trading-and-strategies`.
- **Futures, forwards, swaps** and commodity-futures depth → `derivatives-futures-and-swaps`.
- **Chart-based** entry/exit timing, candlesticks, RSI/MACD, support/resistance → `technical-analysis`.
- **Order-routing / microstructure** depth (dark pools, Reg NMS internals, maker-taker, slippage, TWAP/VWAP) → `market-microstructure-and-execution`.
- **Long-term passive / retirement** investing — 401(k)/IRA/Roth, target-date funds, dollar-cost averaging for retirement, choosing a robo or fee-only fiduciary, picking a fund by expense ratio for a retirement portfolio → the peer skill `investing-and-retirement`. **This spoke owns the active side and the active-vs-passive evidence; it hands off the passive playbook.**
- Position sizing / stops / Kelly → `trading-risk-management`; the trader's tax detail (wash sales, trader-tax-status, capital-gains mechanics) → `trading-regulation-compliance-and-taxes`.
- **Fundamental analysis (§2), dividends/buybacks/splits (§3), and the primary market — IPOs, direct listings, SPACs, follow-ons, lockups (§4)** were split out of this file on **2026-08-04** and now live, verbatim and still numbered §2–§4, in `references/equity-fundamentals-and-corporate-actions.md`.

## Contents

- [1. Equity instruments & market structure](#instruments)
  - [Common vs preferred stock](#common-preferred)
  - [Share classes & dual-class structures](#share-classes)
  - [How shares trade: NYSE vs Nasdaq](#nyse-nasdaq)
  - [Major US indices & how they are weighted](#indices)
  - [Reading a stock quote](#quote)
  - [Market capitalization, tiers, float vs shares outstanding](#market-cap)
  - [GICS sectors & industries](#gics)
- **2. Fundamental equity analysis basics** — moved to `references/equity-fundamentals-and-corporate-actions.md`: multiples, EPS, P/B, margins, payout ratios, balance sheet, earnings season, styles.
- **3. Dividends, buybacks & stock splits (corporate actions)** — moved to `references/equity-fundamentals-and-corporate-actions.md`: the four dividend dates under T+1, DRIPs, buybacks, splits.
- **4. Corporate actions & the primary market** — moved to `references/equity-fundamentals-and-corporate-actions.md`: IPOs, direct listings, SPACs, follow-ons, lockups.
- [5. Equity-specific trading mechanics: long vs short](#long-short)
  - [Going long](#long)
  - [Short selling & the locate/borrow requirement](#short)
  - [Short interest & the short squeeze](#squeeze)
  - [Holding horizon: long-term vs active](#horizon)
- [6. Active equity trading vs passive index investing](#active-passive)
- [References](#references)

---

## 1. Equity instruments & market structure
<a id="instruments"></a>

### Common vs preferred stock
<a id="common-preferred"></a>

A **stock** is a security giving fractional **ownership** in a company. Two main classes:

- **Common stock** entitles the owner to **vote** at shareholder meetings (typically one vote per share) and to receive **dividends** when declared. In a liquidation, common holders are paid **last** — after creditors, bondholders, and preferred holders.[^1]
- **Preferred stock** usually carries **no voting rights**, receives its (typically fixed) dividend **before** common holders, and ranks **ahead of** common in bankruptcy/liquidation.[^1] It is a **hybrid** security — senior to common but **subordinate to bonds** — and because the dividend is usually fixed and the share often perpetual, its price behaves like a long-duration bond (it moves inversely with interest rates).[^2]

Preferred sub-types (combinable): **cumulative** (skipped dividends accrue and must be paid before any common dividend) vs **non-cumulative** (a skipped dividend is simply lost); **callable/redeemable** (issuer can buy it back, usually at a premium); **convertible** (holder can convert to common at a preset ratio); **participating** (can receive extra beyond the fixed rate).[^2] Most retail "stock trading" means **common** stock; preferred is closer to fixed income and is covered at overview depth in the asset-classes foundation.

### Share classes & dual-class structures
<a id="share-classes"></a>

A company can issue **multiple classes of common stock** with unequal voting power — a **dual-class** (or multi-class) structure that concentrates control with founders/insiders via "super-voting" shares.[^3]

- **Alphabet:** `GOOGL` = Class A (1 vote); `GOOG` = Class C (no vote); Class B (10 votes/share) is held by insiders and does not trade publicly.[^3]
- **Berkshire Hathaway:** `BRK.A` (full voting, very high price) vs `BRK.B` (created 1996, a small economic fraction of an A share with proportionally far less voting power).[^3]

**The governance debate:** critics (notably the Council of Institutional Investors) argue dual-class violates "one share, one vote," entrenches managers, and weakens takeover/activist discipline; proponents say it protects founder vision and long-term strategy.[^3]

**Index eligibility — a load-bearing, time-stamped reversal** *(as of 2026)*: in **July 2017** S&P Dow Jones Indices barred companies with multiple share classes from **new** addition to the S&P Composite 1500 (existing members like Alphabet were grandfathered); FTSE Russell set a free-float voting threshold the same year. In **April 2023, S&P Dow Jones Indices reversed the ban** — multi-class companies are again eligible for the S&P 500/1500 if they meet all other criteria.[^4] Re-verify before relying, as index policy changes.

### How shares trade: NYSE vs Nasdaq
<a id="nyse-nasdaq"></a>

The two dominant US listing venues run **different market models** (the deeper microstructure of *how* an order executes lives in `market-microstructure-and-execution`):

- **NYSE = an auction market with Designated Market Makers (DMMs).** Each listed stock is assigned to **one** DMM who manages the order book and runs the opening and closing auctions, with a formal obligation to maintain a "fair and orderly market" and supply liquidity to offset imbalances. NYSE is a **hybrid** model and retains a physical trading floor. (The DMM role was called the "specialist" before 2008.)[^5]
- **Nasdaq = a dealer/electronic market with multiple competing market makers.** No single specialist; many dealers post competing two-sided quotes and orders route to the best price. Liquidity comes from dealer competition.[^5]

**Listing requirements** differ — NYSE generally sets a higher bar; Nasdaq is tiered (Global Select / Global / Capital Market) and typically less costly — and the specific dollar thresholds change (the SEC approved new NYSE/Nasdaq **minimum-price** rules in 2025–2026), so treat any specific figure as volatile and check the current listing standards.[^5]

### Major US indices & how they are weighted
<a id="indices"></a>

The three headline US indices use **three different weighting methods** — a common point of confusion:

- **S&P 500 — float-adjusted market-cap weighted, committee-selected.** Weight ∝ float-adjusted market value (only publicly tradable shares count). It is **~500 companies but not simply "the 500 largest" and not purely rules-based** — S&P's Index Committee exercises **full discretion**; quantitative criteria only earn a place on an eligibility list.[^6] *(As of 2026)* it actually carries **~503 stock listings** because a few companies (e.g., Alphabet) have two included share classes; the count drifts.[^6]
- **Nasdaq-100 — modified market-cap weighted, the 100 largest non-financial Nasdaq companies.** Each constituent's share count is **capped at 3× its free-float** to limit low-float dominance, with capping rules that scale down the largest weights; reconstituted annually in **December** with quarterly rebalances, plus an off-cycle **"special rebalance"** if concentration thresholds are breached.[^7]
- **Dow Jones Industrial Average — PRICE-weighted, 30 stocks.** Higher-**priced** stocks have more influence regardless of company size; DJIA = (sum of the 30 share prices) ÷ the **Dow Divisor** (adjusted for splits/component changes; now <1, so it acts as a multiplier).[^8] Price-weighting is **widely criticized** as conceptually inferior — a stock split arbitrarily cuts a component's weight, and a high-priced mid-size company can outweigh a far larger low-priced one.[^8]

Briefly: the **Russell 2000** is the small-cap benchmark (the Russell 1000 large-cap, Russell 3000 ≈ the whole investable market), all float-cap weighted; **total-market** indices (CRSP US Total Market, Wilshire 5000) aim to capture the entire US market.[^9] *(As of 2026, FTSE Russell moved Russell reconstitution from annual to semi-annual — verify the effective schedule.)*[^9]

### Reading a stock quote
<a id="quote"></a>

A retail quote shows, at minimum:[^10]

- **Bid** — the highest price a buyer is currently willing to pay; **ask (offer)** — the lowest a seller will accept; the **bid-ask spread** (ask − bid) is **narrow** when liquidity is high and **wide** when it is low (the spread is a real round-trip cost — see the order-lifecycle foundation).
- **Last** — the price of the most recent executed trade.
- **Volume** — shares traded (today or average daily); a liquidity/interest gauge.
- **Day range** and **52-week range** — the low–high over the session and the trailing year.
- **Market cap** — current price × shares outstanding.

### Market capitalization, tiers, float vs shares outstanding
<a id="market-cap"></a>

**Market cap = current share price × shares outstanding.**[^11] Size **tiers are conventions, not an official standard** — providers differ — so treat thresholds as approximate *(as of 2026)*: FINRA-cited bands run **mega-cap > $200B, large $10B–$200B, mid $2B–$10B, small ~$250M–$2B, micro ~$50M–$250M, nano < $50M**; larger caps tend to be less volatile.[^11] Morningstar instead uses a **relative** method (top 70% of total US market cap = large, next 20% = mid, etc.).[^11]

**Float vs shares outstanding:** **shares outstanding** = all issued shares (including restricted insider/locked blocks); **public float** = the freely tradable subset (= outstanding − restricted/closely-held). Float ≤ shares outstanding always, and index providers weight on **float**, not total shares.[^12]

### GICS sectors & industries
<a id="gics"></a>

The **Global Industry Classification Standard (GICS)** — maintained jointly by **MSCI and S&P Dow Jones Indices** — sorts every public company by its principal business into a four-tier hierarchy: **Sector → Industry Group → Industry → Sub-Industry**.[^13] *(As of 2026, last revised March 2023)* the structure is **11 sectors, 25 industry groups, 74 industries, 163 sub-industries**.[^13] The **11 sectors:** Energy, Materials, Industrials, Consumer Discretionary, Consumer Staples, Health Care, Financials, Information Technology, Communication Services, Utilities, Real Estate.[^13] (Real Estate was split from Financials in 2016; Communication Services was created in 2018.)[^13] GICS is the standard vocabulary for "what sector is this stock in" and for sector ETFs/screens.

---

## 2–4. Fundamental analysis, corporate actions & the primary market — moved
<a id="fundamentals"></a><a id="corporate-actions"></a><a id="primary-market"></a>

Moved **verbatim** on 2026-08-04, with footnotes `[^14]`–`[^49]`, to `references/equity-fundamentals-and-corporate-actions.md` — same section numbers, same subsection anchors, nothing condensed.

| Section — now in that file | What is there | The claim it supports |
|---|---|---|
| **§2 Fundamental equity analysis basics** | P/E (trailing vs forward), earnings yield, PEG; basic vs diluted EPS; P/B and book value; the gross → operating → net margin ladder; dividend yield, payout ratio, coverage; the accounting identity, debt-to-equity, current ratio; 10-K/10-Q/8-K, EDGAR, guidance, analyst ratings; growth vs value vs dividend styles. | Multiples are **metrics, not a valuation method** — each has a failure mode (a low P/E can be a value trap, P/B understates intangible-heavy firms, a high yield is usually a warning) — and because price is the PV of *future* cash flows, **guidance often moves a stock more than the headline number**. |
| **§3 Dividends, buybacks & stock splits (corporate actions)** | The four dividend dates and the T+1 rule that ex-date and record date are now the **same** business day; DRIPs, special and stock dividends; buyback methods (Rule 10b-18, tender, ASR) and the 1% IRC §4501 excise tax; forward and reverse splits and the $1 minimum-bid cure. | Capital-return mechanics **create no value on their own** — the ex-date drop offsets the dividend (so "buy just before the ex-date" is a myth), buybacks lift EPS arithmetically with no operational improvement, and splits are value-neutral beyond a small signalling effect. |
| **§4 Corporate actions & the primary market** | IPOs (Form S-1, underwriting, book-building, the 15% greenshoe, quiet period); direct listings and the 2020–21 primary-issuance approvals; SPACs, the de-SPAC and the SEC's January 2024 rules; dilutive vs non-dilutive follow-ons, S-3 shelf and ATM offerings; lockups. | The **primary** market (shares created and sold) is a different thing from the **secondary** market (investor-to-investor trading) — and for retail, IPO access is ~90% institutional, first-day pops coexist with ~3-year underperformance, and de-SPACs have broadly underperformed. |

This file keeps the **market side** of the spoke: what a share is and where it trades (§1), long/short mechanics (§5), and whether to trade actively at all (§6).

---

## 5. Equity-specific trading mechanics: long vs short
<a id="long-short"></a>

Margin, the Pattern-Day-Trader rule, and the short-selling overview are in the `trading-risks-and-protections` foundation; this section is the **equity-specific** depth.

### Going long
<a id="long"></a>

**Going long** = buying shares to profit if the price rises (plus any dividends). **Maximum loss is limited to the amount invested** because a share price cannot fall below **$0** (a 100% loss at most).[^50] This is the default retail position and the symmetric counterpart to shorting.

### Short selling & the locate/borrow requirement
<a id="short"></a>

**Short selling** = selling shares you **borrow** (from your broker, sourced from its inventory, other clients' margin accounts, or another lender), hoping to **buy them back ("cover") lower** and return them — you profit from a **decline**.[^51] It **requires a margin account** (Regulation T sets a short's initial margin at **150%** of the position value — the proceeds plus 50% of the value from your own funds).[^51]

**The asymmetric risk is load-bearing:** a short's gains are **capped** (the stock can only fall to $0) but **losses are theoretically UNLIMITED** because the price can rise without bound — **you can lose more than the proceeds you received.**[^51] Short example: short 100 shares at $10 ($1,000 proceeds); if it rises to $100 you spend $10,000 to cover — a $9,000 loss, nine times the proceeds.[^51]

**The locate/borrow requirement (Regulation SHO):** **Rule 203(b)(1)** bars a broker from accepting a short-sale order unless it has borrowed the security or has **"reasonable grounds to believe the security can be borrowed"** and delivered by settlement — the **"locate,"** documented before the sale.[^52] Brokers keep an **"easy-to-borrow"** list (low/zero fee) vs **"hard-to-borrow" (HTB)** names that carry a **borrow fee / stock-loan rate** (dynamic; HTB names can run very high *(as of 2026, illustrative)* and reprice sharply).[^53] The lender can **recall** the shares anytime, forcing a **buy-in** at an unfavorable price.[^53] **Naked short selling** (selling without a locate) is **generally prohibited** and produces **failures to deliver (FTDs)**; Reg SHO's close-out rule (Rule 204) and the **threshold-securities** list address persistent fails — though not every transient FTD is itself a violation.[^52] Unique short costs also include **margin interest** and **paying the lender any dividends** ("in lieu of" payments) on the borrowed stock.[^51] **Rule 201 (the alternative uptick rule)** is a short-sale circuit breaker: if a stock falls **≥10% intraday from the prior close**, short sales for the rest of that day and all the next may only execute **above the national best bid**.[^52]

> **Disconfirming note:** despite its reputation, the academic consensus is that short selling **improves price discovery and market efficiency** (short-sale bans demonstrably hurt it); short sellers are often informed traders correcting overvaluation.[^54] Separately, short selling is **hard for retail** — you can be right on the thesis yet lose everything if you are early (borrow/margin costs accrue and a squeeze can force you out).[^51]

*(As of 2026)* the SEC's institutional short-position reporting regime (**Rule 13f-2 / Form SHO**, adopted 2023) has been **repeatedly delayed and is not yet in effect** (compliance extended to January 2028 after a 2025 court remand) — re-verify, as this is the most volatile fact in this section.[^55]

### Short interest & the short squeeze
<a id="squeeze"></a>

**Short interest** = shares currently sold short and not yet covered; often expressed as **% of float** (>20% is treated as very high) or as **days-to-cover / short-interest ratio** (short interest ÷ average daily volume).[^56] FINRA publishes aggregate short interest **twice monthly**.[^56] High short interest signals bearish sentiment **and** squeeze potential.

A **short squeeze** is a self-reinforcing loop: a heavily shorted stock rises, **forcing shorts to cover (buy back)** to limit losses or meet margin calls, which pushes the price **higher**, forcing more covering — intensified by rising borrow fees, recalls, and margin calls.[^57] The canonical retail example is **GameStop (GME), January 2021**: short interest reached **~140% of float** (possible because lent shares are re-lent in a chain), Reddit-driven retail buying drove GME from ~$17 to an intraday **~$483** on Jan 28, 2021, and the loop broke when brokers restricted buying; AMC ran in parallel.[^57] **Contested nuance:** the **SEC's 2021 staff report** concluded the GME rise was sustained mainly by **positive sentiment and direct buying — not primarily short-covering**, a finding some academics dispute — present it as a genuine debate.[^57] A **gamma squeeze** (options dealers delta-hedging short calls, amplifying the move) is **mechanically distinct** and co-occurred with GME — for the options mechanics see `options-trading-and-strategies`.[^57]

### Holding horizon: long-term vs active
<a id="horizon"></a>

Equity holding ranges from **buy-and-hold for years** (low turnover/cost; the default) to **frequent/active trading**.[^58] The **holding period sets the capital-gains line** at a high level: a gain on a position held **one year or less is short-term (ordinary income rates)**; held **more than one year it is long-term (preferential 0/15/20% rates)** — deep mechanics (wash sales, trader-tax-status) → `trading-regulation-compliance-and-taxes`.[^59] Frequent intraday trading triggers the **Pattern-Day-Trader rule** (and its 2026 replacement) — see `trading-risks-and-protections`, not re-derived here.[^58]

---

## 6. Active equity trading vs passive index investing
<a id="active-passive"></a>

This is the spoke's central decision, and the **seam** with the peer skill `investing-and-retirement`.

**The distinction:** **active** equity investing tries to **beat** the market through **security selection** (stock-picking) and **market timing**; **passive** investing buys a broad index fund/ETF and holds it to **match** the market at minimal cost.[^60] Per the SEC, passive "usually translates into less trading … more favorable income-tax consequences … and lower fees."[^60]

**The load-bearing evidence that active stock-picking underperforms** (educational, not advice — but central to this spoke):

- **SPIVA scorecards (S&P Dow Jones Indices)** — a large **majority of active US equity funds underperform their benchmark** over long horizons. *(As of 2026, SPIVA US Year-End 2025)* **~79% of active large-cap funds lagged the S&P 500 in 2025** (the 16th consecutive year the majority lagged), and over **15 years no US equity category had a majority of active managers beat** their benchmark; ~92% lagged over 20 years.[^61] These percentages update twice a year — re-verify against the current scorecard.
- **Morningstar Active/Passive Barometer** — an **independent** study with a different method reaches the same conclusion: only ~21% of active funds survived **and** beat comparable passive funds over the 10 years through 2025.[^62] (This is the strongest rebuttal to "SPIVA is rigged.")
- **Persistence** — top-performing funds rarely stay top: SPIVA's Persistence Scorecard finds top-quartile funds have little better than random odds of repeating, consistent with **luck over skill**.[^63]
- **Why (mechanism):** **Sharpe's "Arithmetic of Active Management"** — before costs the average active dollar earns the market return, so **after costs the average active dollar must underperform** the average passive dollar.[^64] **Bessembinder** — **most individual stocks underperform Treasury bills**, and a tiny fraction (~4% of companies) account for **all** net market wealth creation, so missing the few big winners (easy when stock-picking) badly lags the index that holds them all.[^65]
- **Retail day-trader evidence** — **Barber & Odean** ("Trading Is Hazardous to Your Wealth": the most active households earned ~11.4% vs ~17.9% for the market); **Taiwan** (>80% of day traders lose money, <1% consistently profitable) and **Brazil** (~97% of persistent day traders lost money) studies all converge.[^66]

**The cost angle:** active US-equity funds average ~**0.60%** expense ratio vs ~**0.11%** for passive (asset-weighted) — a structural headwind that **compounds** over decades — plus the **tax drag** of higher turnover (active mutual funds distribute far more capital gains than mostly-passive ETFs).[^67]

**The contrarian view (a genuine debate, not settled):** active can win in **less-efficient** segments — *(as of 2026)* in SPIVA YE-2025 a **majority of active small-cap and emerging-market-debt funds beat** their benchmarks — but the edge is **short-horizon and does not persist** (no category over 15 years).[^68] A separate, unresolved **"passive bubble" / price-discovery** debate (Michael Burry-style critiques vs rebuttals) concerns **second-order market-structure** effects of indexing — keep it separate from the individual-investor question, where the evidence favors low-cost passive.[^69] Rules-based **factor/smart-beta** sits between the two as a middle path.[^68]

**Where the boundary sits (the design rule):** the dividing line is **intent**, not asset class.
- **Stays in this spoke** (intent = actively trade / understand markets): stock selection and equity analysis; trading tactics, frequency, turnover; the **active-vs-passive debate and the underperformance evidence itself** (it explains why most active trading fails); the cost/fee/tax-drag argument as a reason active underperforms; the "passive bubble" market-structure debate.
- **Defers to `investing-and-retirement`** (intent = build long-term retirement wealth passively): **how** to pick/hold a broad index fund or ETF for the long run; **retirement accounts** (401(k)/403(b), Traditional/Roth IRA, contribution limits, vesting); **target-date funds**, dollar-cost averaging **for retirement**, glidepaths; choosing a **robo-advisor or fee-only fiduciary**; expense-ratio-driven **fund selection for a retirement portfolio**.

In one line: **active = trying to *beat* the market (this spoke explains the approach and the sobering evidence); passive buy-and-hold for retirement = *matching* the market cheaply (the peer skill owns the how-to).** This matches the hub's existing SKIP edge to `investing-and-retirement`.

---

## References

Sources are graded by tier: **regulator/SRO** (SEC/Investor.gov, FINRA, Congress.gov CRS, IRS, DTCC), **exchange/index-provider** (NYSE, Nasdaq, S&P Dow Jones Indices, MSCI, FTSE Russell), **peer-reviewed/academic**, and **reputable financial education** (corroborating). Volatile facts are dated *as of 2026* with a "verify current" pointer. The SEC's own pages (sec.gov) intermittently blocked automated fetch during research; in those cases the identical Investor.gov mirror and/or multiple tier-1 law-firm summaries were used and are cited.

**Split note (2026-08-04):** footnotes **`[^14]`–`[^49]`** support §2–§4 and moved with that text to `references/equity-fundamentals-and-corporate-actions.md`; the grading conventions above apply there unchanged. This file retains **`[^1]`–`[^13]`** (§1) and **`[^50]`–`[^69]`** (§5–§6). No footnote was cited from both halves, so none needed duplicating.

[^1]: SEC / Investor.gov — Stocks (common vs preferred, voting, dividend priority, liquidation order). https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks (regulator)
[^2]: S&P Global, "Practice Essentials: US Preferreds" https://www.spglobal.com/spdji/en/documents/education/practice-essentials-us-preferreds.pdf ; Fidelity, "Convertibles and preferreds" https://www.fidelity.com/learning-center/investment-products/fixed-income-bonds/convertibles-and-preferreds (index-provider; financial education)
[^3]: Council of Institutional Investors, "Dual-Class Stock" https://www.cii.org/dualclass_stock ; Harvard Law School Forum on Corporate Governance, dual-class analysis https://corpgov.law.harvard.edu/2024/10/16/re-thinking-the-hostility-towards-dual-class-share-structures-when-dual-class-shares-work-better/ ; U.S. News, "GOOG vs GOOGL" https://money.usnews.com/investing/articles/goog-vs-googl-stock-difference (institutional body; academic; financial education)
[^4]: Davis Polk, "S&P Dow Jones reopens its indices to companies with multiple share classes" (April 2023 reversal) https://www.davispolk.com/insights/client-update/sp-dow-jones-reopens-its-indices-companies-multiple-share-classes ; Wilson Sonsini, 2017 multi-class index limitation + grandfathering https://www.wsgr.com/en/insights/major-stock-index-providers-to-limit-inclusion-of-multi-class-companies-what-it-means-and-why-it-matters.html (law firm — primary analysis of index-provider policy) [verify as of 2026]
[^5]: NYSE Market Model (DMM/auction) https://www.nyse.com/market-model ; NYSE, "Market Making and the NYSE DMM Difference" https://www.nyse.com/data-insights/market-making-and-the-nyse-dmm-difference ; Akerman, "SEC Approves Changes to NYSE and Nasdaq Minimum Price Rules" (2025–2026) https://www.akerman.com/en/perspectives/sec-approves-changes-to-nyse-and-nasdaq-minimum-price-rules-what-public-companies-need-to-know.html (exchange; law firm) [thresholds volatile as of 2026]
[^6]: S&P Dow Jones Indices, US Indices Methodology (float-cap weighting; committee discretion) https://www.spglobal.com/spdji/en/methodology/article/sp-us-indices-methodology/ ; Corporate Finance Institute, "S&P 500 Index" (committee discretion) https://corporatefinanceinstitute.com/resources/equities/sp-500-index/ (index-provider; financial education) [~503 listings, as of 2026]
[^7]: Nasdaq, official Nasdaq-100 Index Methodology (modified cap weighting, 3× free-float cap, December reconstitution, special rebalance) https://indexes.nasdaq.com/docs/Methodology_NDX.pdf (index-provider, primary methodology)
[^8]: S&P Dow Jones Indices, Dow Jones Averages Methodology (price weighting; the divisor) https://www.spglobal.com/spdji/en/methodology/article/dow-jones-averages-methodology/ ; Stanford SIEPR, "The Dow Jones Average: The Impact of Fixing Its Flaws" (price-weighting criticism) https://siepr.stanford.edu/publications/working-paper/dow-jones-average-impact-fixing-its-flaws (index-provider; academic)
[^9]: FTSE Russell (LSEG), "Four Decades of the Russell Reconstitution" https://www.lseg.com/content/dam/ftse-russell/en_us/documents/research/four-decades-russell-reconstitution.pdf (index-provider) [annual→semi-annual reconstitution change, verify as of 2026]
[^10]: Charles Schwab, "How to read a stock quote" https://www.schwab.com/learn/story/learn-how-to-read-stock-quotes ; WallStreetZen, "How to Read a Stock Quote" https://www.wallstreetzen.com/blog/how-to-read-a-stock-quote/ (financial education)
[^11]: Schwab, "How well do you know market cap?" (FINRA-cited tiers) https://www.schwab.com/learn/story/how-well-do-you-know-market-cap ; Wikipedia, "Market capitalization" / small-cap (no-consensus caveat; Morningstar relative method) https://en.wikipedia.org/wiki/Market_capitalization (financial education; tertiary) [tier bands non-standard, as of 2026]
[^12]: Cornell Law (Wex), "public float" (SEC definition) https://www.law.cornell.edu/wex/public_float ; RBC Direct Investing, "Shares outstanding vs float" https://www.rbcdirectinvesting.com/learn/en/di/hubs/investing-academy/article/shares-outstanding-vs-float/jk0dlma0 (legal reference; financial education)
[^13]: MSCI, GICS https://www.msci.com/indexes/index-resources/gics ; S&P Dow Jones Indices, GICS Methodology https://www.spglobal.com/spdji/en/documents/methodologies/methodology-gics.pdf ; Wikipedia, GICS (11/25/74/163 structure, March 2023 revision) https://en.wikipedia.org/wiki/Global_Industry_Classification_Standard (index-providers; tertiary corroboration) [structure as of 2026]
[^50]: SEC / Investor.gov, "Introduction to Short Sales" (long-position loss limited to amount invested, contrast with unlimited short loss) https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-51 (regulator)
[^51]: SEC / Investor.gov, "Introduction to Short Sales" (borrow/cover mechanics, margin account, 150% Reg T, unlimited loss, dividends owed to lender) https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-51 ; Bankrate, "Short Selling: How To Short Sell Stocks" (worked loss example) https://www.bankrate.com/investing/short-selling-how-to-short-a-stock/ (regulator; financial education)
[^52]: SEC, Regulation SHO / short-sale rules (Rule 203(b)(1) locate; Rule 204 close-out; threshold securities; Rule 201 alternative uptick) https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions-7 ; Congressional Research Service, "Short Selling: Background and Policy Issues" (IF12400) https://www.congress.gov/crs-product/IF12400 (regulator; CRS — primary)
[^53]: Interactive Brokers Campus, "The Risks of Shorting: Borrow Fees" (ETB/HTB, stock-loan rate, recall/buy-in) https://www.interactivebrokers.com/campus/traders-insight/securities/short-selling/the-risks-of-shorting-series-part-ii-borrow-fees/ (broker/financial education) [borrow-fee levels illustrative, as of 2026]
[^54]: Managed Funds Association, "An Introduction to Short Selling" (price-discovery benefit; ban harms) https://www.mfaalts.org/wp-content/uploads/2025/04/MFA-Updated-Intro-to-Short-Selling-Research-Paper.pdf ; NBER, "Short-Sale Constraints and Overpricing" https://www.nber.org/reporter/spring05/short-sale-constraints-and-overpricing (industry body; academic)
[^55]: Morgan Lewis, "Short-Sale Reporting on Form SHO: Compliance Date Further Extended to 2028" (Rule 13f-2 not yet in effect) https://www.morganlewis.com/pubs/2025/12/short-sale-reporting-on-form-sho-compliance-date-further-extended-to-2028 (law firm) [13f-2/Form SHO delayed to Jan 2028; most volatile fact, verify as of 2026]
[^56]: FINRA, Short Interest Reporting (bi-monthly cadence) https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest ; Charles Schwab, short-interest / days-to-cover https://www.schwab.com/learn/story/what-is-short-interest (SRO — primary; financial education)
[^57]: SEC, "Staff Report on Equity and Options Market Structure Conditions in Early 2021" (GME; concluded sentiment/buying, not primarily short-covering) https://www.sec.gov/files/staff-report-equity-options-market-struction-conditions-early-2021.pdf ; Columbia Law School Blue Sky Blog, "An Academic Critique of the SEC's GameStop Report" https://clsbluesky.law.columbia.edu/2022/02/22/an-academic-critique-of-the-secs-gamestop-report/ (regulator — primary; academic critique) [GME attribution contested]
[^58]: Charles Schwab, buy-and-hold vs active trading https://www.schwab.com/learn/story/stock-trading-vs-investing-whats-difference ; FINRA, margin/pattern-day-trader key topic https://www.finra.org/rules-guidance/key-topics/margin-accounts (financial education; SRO)
[^59]: IRS Topic No. 409, "Capital Gains and Losses" (short-term ≤1 yr ordinary; long-term >1 yr preferential 0/15/20%) https://www.irs.gov/taxtopics/tc409 (IRS — primary)
[^60]: SEC / Investor.gov, "Mutual Funds and ETFs" (active vs passive definitions; passive = lower trading/tax/fees) https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-funds-etfs/mutual-funds (regulator)
[^61]: S&P Dow Jones Indices, SPIVA US Scorecard (Year-End 2025; majority of active large-cap funds lag the S&P 500; no category beats over 15 yr) https://www.spglobal.com/spdji/en/spiva/article/spiva-us/ (index-provider — primary) [percentages update twice yearly; as of 2026]
[^62]: Morningstar, "US Active/Passive Barometer" (independent; ~21% of active funds survived and beat passive over 10 yr through 2025) https://www.morningstar.com/business/insights/research/active-passive-barometer (independent benchmark study) [as of 2026]
[^63]: S&P Dow Jones Indices, "SPIVA US Persistence Scorecard" (top performers rarely persist; luck over skill) https://www.spglobal.com/spdji/en/spiva/article/us-persistence-scorecard/ (index-provider — primary)
[^64]: William F. Sharpe, "The Arithmetic of Active Management" (Financial Analysts Journal, 1991) https://web.stanford.edu/~wfsharpe/art/active/active.htm (peer-reviewed)
[^65]: Hendrik Bessembinder, "Do Stocks Outperform Treasury Bills?" (Journal of Financial Economics, 2018; most stocks lag T-bills; ~4% of firms create all net wealth) https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2900447 (peer-reviewed)
[^66]: Barber & Odean, "Trading Is Hazardous to Your Wealth" (Journal of Finance, 2000) http://faculty.haas.berkeley.edu/odean/papers/returns/individual_investor_performance_final.pdf ; Chague, De-Losso & Giovannetti, "Day Trading for a Living?" (Brazil; ~97% of persistent day traders lose) https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101 (peer-reviewed/academic)
[^67]: Morningstar, "US Fund Fee Study" (active ~0.59–0.60% vs passive ~0.11%, asset-weighted) https://www.morningstar.com/business/insights/blog/funds/us-fund-fee-study ; SEC, "How Fees and Expenses Affect Your Investment Portfolio" https://www.sec.gov/investor/alerts/ib_fees_expenses.pdf (research; regulator) [fee figures 2024 study; verify as of 2026]
[^68]: S&P Dow Jones Indices SPIVA US YE-2025 (active majority beat in small-cap & EM debt short-horizon; none over 15 yr) https://www.spglobal.com/spdji/en/spiva/article/spiva-us/ (index-provider — primary) [segment figures volatile, as of 2026]
[^69]: ETF Strategy, "Passive investing a 'bubble', says Michael Burry" https://www.etfstrategy.com/passive-investing-a-bubble-says-big-short-investor-michael-burry-10449/ ; Elm Wealth, "A Few Quick Responses to Michael Burry's Index-bubble Remarks" (rebuttal) https://elmwealth.com/michael-burry-index-bubble/ (reputable financial commentary — both sides of an unresolved debate)
