---
name: equity-fundamentals-and-corporate-actions
# provenance: split verbatim out of references/stock-and-equity-trading.md on 2026-08-04 to hold both files under the reference token ceiling. Content researched and source-verified 2026-06-16 via /dr deep-research (~40 independent regulator/exchange/index-provider/peer-reviewed sources); NOT re-verified at split time — volatile claims remain dated "as of 2026".
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-06-16"  # content split from stock-and-equity-trading.md on 2026-08-04; NOT re-verified at split time
category: reference
description: >-
  ISSUER side of the trading-and-investing equity spoke — the company behind the
  share, what it does with its capital, and how its shares are first created and
  sold. Split verbatim from stock-and-equity-trading (§2-§4, footnotes 14-49,
  numbering preserved). Educational ONLY, NOT financial/investment/tax advice
  (2026). TRIGGER: P/E, earnings yield, PEG and their limits; basic vs diluted
  EPS; P/B and book value; the margin ladder; dividend yield, payout ratio,
  coverage, the high-yield dividend trap; balance-sheet basics; 10-K/10-Q/8-K,
  EDGAR, earnings season, guidance, analyst ratings; growth vs value vs dividend
  styles; the four dividend dates under T+1; DRIPs; buybacks (Rule 10b-18, ASR,
  the excise tax); forward and reverse splits; IPOs (S-1, greenshoe, retail
  allocation odds, first-day pop vs 3-year underperformance); direct listings;
  SPACs and the de-SPAC; follow-on offerings and the "secondary" terminology
  trap; lockups. SKIP: what a share is, share classes, NYSE vs Nasdaq, index
  weighting, market cap, GICS -> stock-and-equity-trading.md §1; long/short
  mechanics and squeezes -> same file §5; active vs passive and the
  underperformance evidence -> same file §6; options ->
  options-trading-and-strategies; charting -> technical-analysis; wash sales and
  trader-tax-status -> trading-regulation-compliance-and-taxes; retirement
  investing -> investing-and-retirement.
keywords:
  - fundamental analysis
  - P/E ratio
  - diluted EPS
  - price to book
  - dividend yield
  - payout ratio
  - dividend trap
  - earnings season
  - forward guidance
  - growth vs value
  - ex-dividend date
  - share buyback
  - stock split
  - reverse split
  - IPO
  - greenshoe
  - direct listing
  - SPAC
  - follow-on offering
  - lockup period
tags:
  - trading-and-investing
  - equities
  - fundamental-analysis
  - corporate-actions
  - primary-market
  - ipo
---

<!-- Provenance: spoke reference under the `trading-and-investing` hub. Split verbatim from `references/stock-and-equity-trading.md` on 2026-08-04 (size split — nothing condensed, reworded, or dropped). Original research 2026-06-16 via /dr deep-research; ~40 independent sources, regulator/exchange/index-provider/peer-reviewed grade. Educational only — NOT financial/investment/tax advice. Volatile claims dated "as of 2026". -->

# Equity Fundamentals & Corporate Actions (spoke reference)

> **Educational information only — NOT financial, investment, or tax advice.**

The **issuer-side** half of the equity spoke: how to read the **company** behind the share (§2), how that company **returns capital or restructures its share count** (§3), and how shares are **first created and sold** in the primary market (§4). The sibling `references/stock-and-equity-trading.md` keeps the **market side** — what a share is and where it trades (§1), long/short mechanics (§5), and the active-vs-passive decision (§6). Equities carry **risk of loss**; a stock can fall to **$0**. Verify volatile facts with the primary regulator (SEC/Investor.gov, FINRA, IRS) before acting.

**Numbering is inherited, deliberately.** Section numbers **§2–§4** and footnote labels **`[^14]`–`[^49]`** carry over unchanged from the parent file so existing cross-references keep resolving.

**Scope.**

| For… | Go to |
|---|---|
| What a share **is** — common vs preferred, dual-class classes, NYSE vs Nasdaq models, index weighting, quotes, market cap & float, GICS | `references/stock-and-equity-trading.md` §1 |
| **Long/short mechanics** — Reg T margin, the Reg SHO locate/borrow rule, borrow fees, short interest, squeezes | `references/stock-and-equity-trading.md` §5 |
| **Active stock-picking vs passive indexing** — SPIVA, Sharpe's arithmetic, Bessembinder, Barber & Odean | `references/stock-and-equity-trading.md` §6 |
| Asset-class definition of equities; exchanges, clearing & settlement (T+1), primary vs secondary market | `references/asset-classes-and-instruments.md`; `references/market-participants-and-structure.md` |
| Order types and routing (PFOF, NBBO); chart-based entry/exit timing | `references/order-lifecycle-and-execution.md`; `references/technical-analysis.md` |
| Listed **options** on equities — calls/puts, the Greeks, spreads | `references/options-trading-and-strategies.md` |
| Wash sales and trader-tax-status; long-term passive/retirement investing | the peer skills `trading-regulation-compliance-and-taxes`; `investing-and-retirement` |

## Contents

- [2. Fundamental equity analysis basics](#fundamentals)
  - [Valuation multiples (P/E, earnings yield, PEG)](#multiples)
  - [EPS — basic vs diluted](#eps)
  - [P/B and book value](#pb)
  - [Revenue vs earnings, margins](#revenue-earnings)
  - [Dividend yield, payout ratio, coverage](#yield-payout)
  - [Balance-sheet basics](#balance-sheet)
  - [Earnings season, guidance & analyst ratings](#earnings-season)
  - [Investing styles: growth, value, dividend](#styles)
- [3. Dividends, buybacks & stock splits (corporate actions)](#corporate-actions)
  - [Cash-dividend mechanics & the four dates](#dividend-dates)
  - [DRIPs, special & stock dividends](#drips)
  - [Share buybacks](#buybacks)
  - [Stock splits & reverse splits](#splits)
- [4. Corporate actions & the primary market](#primary-market)
  - [IPOs](#ipos)
  - [Direct listings](#direct-listings)
  - [SPACs](#spacs)
  - [Follow-on offerings & the "secondary" terminology trap](#followon)
  - [Lockup periods](#lockups)
- [References](#references)

---

## 2. Fundamental equity analysis basics
<a id="fundamentals"></a>

Fundamental analysis values a company from its business and financial statements — distinct from **technical analysis** (price/volume charts → `technical-analysis`). The basics below are analytical *metrics*; they are not a valuation method on their own and every multiple has limits.

### Valuation multiples (P/E, earnings yield, PEG)
<a id="multiples"></a>

- **P/E ratio** = share price ÷ EPS (equivalently market cap ÷ net earnings) — "how much you pay per $1 of earnings."[^14] **Trailing** P/E uses actual last-twelve-months EPS (hard data); **forward** P/E uses projected next-12-month EPS (depends on estimates that can be wrong).[^14] A **high** P/E signals high growth expectations (or overvaluation and more volatility); a **low** P/E signals a perceived value play (or trouble).[^14]
- **Earnings yield** = EPS ÷ price = 1 ÷ P/E, as a percentage — lets you compare a stock's earnings return against bond yields.[^15]
- **PEG** = P/E ÷ earnings growth rate; a rule of thumb treats **PEG < 1** as cheap relative to growth.[^15]
- **Limits (load-bearing):** P/E is **negative/meaningless for unprofitable companies** (analysts fall back on price-to-sales); it uses accounting earnings that one-offs can distort; it ignores balance-sheet leverage and growth; and a **low P/E can be a "value trap"** — cheap for a deteriorating reason.[^16]

### EPS — basic vs diluted
<a id="eps"></a>

**EPS** = (net income − preferred dividends) ÷ shares outstanding — earnings available to **common** holders.[^17] **Basic EPS** uses actual common shares; **diluted EPS** adds all dilutive potential shares (options, warrants, convertible debt/preferred) as if issued, so **diluted EPS ≤ basic EPS**.[^17] US GAAP (ASC 260) requires public companies to present both with equal prominence.[^17] Dilution matters because option/convertible-heavy companies report a meaningfully lower diluted number.

### P/B and book value
<a id="pb"></a>

**P/B** = price ÷ book value per share, where **book value = shareholders' equity (assets − liabilities)**.[^18] P/B is most meaningful for **asset-heavy** businesses (banks, insurers, real estate, manufacturers) and **understates** value for **intangible-heavy / asset-light** firms (tech, pharma, services) because R&D, brands, and software are mostly **expensed, not capitalized** — so book value is understated and P/B looks very high.[^18] Buybacks above book value, and even negative book equity (e.g., long-time repurchasers), further distort P/B.[^18]

### Revenue vs earnings, margins
<a id="revenue-earnings"></a>

**Top line** = total **revenue**; **bottom line** = **net income** (after all costs, interest, taxes).[^19] Strong revenue doesn't guarantee profit if costs rise in step. The **margin** ladder strips successive cost layers: **gross margin** (revenue − COGS), **operating margin** (after SG&A and R&D), **net margin** (after interest, taxes, one-offs).[^19] Both revenue growth (demand/scale) and earnings growth (cost discipline → shareholder returns) matter; profitless revenue and margin-only growth are each incomplete signals.[^19]

### Dividend yield, payout ratio, coverage
<a id="yield-payout"></a>

- **Dividend yield** = annual dividend per share ÷ price (the cash return on the price paid).[^20]
- **Payout ratio** = dividends ÷ earnings (the share of earnings paid out vs retained). Commonly cited as **sustainable ~30–60%** (conventions, not hard rules; stable sectors like utilities run higher), **caution 60–80%**, **danger > 80%**, and **> 100% = paying out more than it earns** (a red flag).[^20]
- **Dividend coverage ratio** = earnings ÷ dividends (the inverse); > 1 means the dividend is earned.[^20]
- **Disconfirming — the high-yield "dividend trap":** a yield far above peers is usually a warning that the **price has fallen** on deteriorating fundamentals and the market expects a **cut** (which typically drops the price further). A high yield is not free income.[^21]

### Balance-sheet basics
<a id="balance-sheet"></a>

The accounting identity is **Assets = Liabilities + Equity**; equity is the **residual** owners' claim after liabilities.[^22] Equity holders are paid **last**, after creditors — the conceptual reason equity is riskier than debt. Two everyday gauges: **debt-to-equity** (total liabilities ÷ equity; higher = more borrowed-capital reliance) and the **current ratio** (current assets ÷ current liabilities; > 1 covers near-term obligations).[^22] Higher leverage magnifies losses to equity in downturns because debt's fixed claims rank ahead of the residual equity claim.[^22]

### Earnings season, guidance & analyst ratings
<a id="earnings-season"></a>

Public companies file an **annual Form 10-K** (audited) and **quarterly Form 10-Q** (generally unaudited) with the SEC, with material events on **Form 8-K**; all are public on **EDGAR**.[^23] Around each quarter-end ("earnings season") a company releases results and hosts an **earnings call**. Analysts publish **consensus estimates**; results above are **beats**, below are **misses**.[^24]

**Load-bearing nuance:** because a stock's value is the present value of **future** cash flows, the market prices on **changes in expectations** — so **forward guidance often moves a stock more than the headline number**. A company can beat on earnings yet fall sharply if it cuts guidance, and high-multiple stocks swing violently when guidance resets the earnings their valuation was built on.[^24] **Analyst ratings** (Buy/Outperform, Hold/Neutral, Sell/Underperform) express **expectations, not guarantees**; a consensus rating averaging many analysts is more reliable than any single call (note many scales count **1 = Strong Buy** up to 5 = Strong Sell).[^24]

### Investing styles: growth, value, dividend
<a id="styles"></a>

Three analytical lenses — not mutually exclusive:[^25]

- **Growth:** high revenue/earnings growth, **high multiples** (P/E 30–50+; unprofitable names judged on price-to-sales), little/no dividend (profits reinvested), concentrated in tech/innovation, higher volatility.
- **Value (Graham/Buffett):** buy below estimated **intrinsic value** with a **margin of safety** (the cushion against estimation error); **low multiples**; Buffett evolved toward "high-quality businesses at fair prices" with durable moats.
- **Dividend / income:** companies that pay and ideally **grow** dividends; favors dividend **growth** over chasing the highest (possibly trap) yield; **Dividend Aristocrats** = S&P 500 members that have raised dividends for **≥25 consecutive years** *(as of 2026, a record ~69 companies — re-verify the count, which changes yearly)*.[^25]

**Cyclicality** *(as of 2026, volatile)*: **growth outperformed value for much of the 2010s–early 2020s** (low rates, tech leadership), but leadership rotates (value led in 2022; growth led 2023–24; a value rotation began in 2025). Value's worst stretches have historically preceded its best — frame style leadership as cyclical, not permanent.[^26] Buffett himself rejects a rigid growth-vs-value split, calling growth a component of value.[^25]

---

## 3. Dividends, buybacks & stock splits (corporate actions)
<a id="corporate-actions"></a>

How a company returns capital or restructures its shares — the *mechanics* (the yield/payout *metrics* are in §2).

### Cash-dividend mechanics & the four dates
<a id="dividend-dates"></a>

A cash dividend runs through four dates:[^27]

1. **Declaration date** — the board announces the dividend, amount, record date, and payment date.
2. **Ex-dividend date (ex-date)** — the day the stock starts trading **without** the right to the upcoming dividend. **Buy before the ex-date → you get the dividend; buy on/after → the seller keeps it.**[^27]
3. **Record date** — you must be on the company's books as a holder to receive the dividend.
4. **Payment date** — the dividend is actually paid.

**Load-bearing, T+1-dependent fact** *(as of 2026)*: since the US moved to **T+1 settlement (May 28, 2024)**, the **ex-dividend date and record date are generally the SAME business day** for regular-way dividends (under the old T+2 the ex-date was one business day before the record date). The clearing utility **DTCC** confirms this directly; the ex-date shifts one business day earlier only if the record date is not a business day.[^28] On the ex-date the share price typically opens **lower by approximately the dividend** (the cash will leave the company), though the real move is only approximate (taxes, ticks, and ordinary movement intervene) — so **"buy just before the ex-date for free money" is a myth**: the price drop offsets the dividend (often with a tax cost).[^28] In theory (Modigliani–Miller, frictionless markets) dividend policy is value-neutral; real-world frictions (taxes, signaling) are why dividends matter in practice.[^29] **Qualified** dividends are taxed at lower long-term-gains rates if an IRS holding-period test is met; **ordinary** dividends at ordinary rates — deep tax → `trading-regulation-compliance-and-taxes` / the consumer-finance `personal-income-taxes` skill.[^27]

### DRIPs, special & stock dividends
<a id="drips"></a>

- **DRIP (dividend reinvestment plan):** automatically reinvests cash dividends into more (often fractional) shares, usually commission-free, compounding the share count over time. Company-sponsored DRIPs may offer a small discount; brokerage "synthetic" DRIPs reinvest even without a formal company plan.[^30]
- **Special dividend:** a **one-time** payment (often large) after an unusually profitable period or asset sale — not part of the regular cadence.[^31]
- **Stock dividend:** paid in **additional shares** rather than cash; raises share count and is economically similar to a small split (generally not immediately taxable, with exceptions).[^31]

### Share buybacks
<a id="buybacks"></a>

A **buyback (repurchase)** returns capital by **reducing shares outstanding** — remaining holders own a larger slice, and **EPS rises mechanically** (same earnings ÷ fewer shares) even with no operational improvement.[^32] Three methods: **open-market repurchase** (most common, ~95%, under the SEC **Rule 10b-18** safe harbor that limits daily volume/price), **tender offer** (buy a set block at a stated price, usually at a premium), and **accelerated share repurchase (ASR)** (a bank delivers a large block upfront for immediate share-count reduction).[^32]

**Buybacks vs dividends:** buybacks are **flexible** (pause/resize without the penalty markets attach to a dividend cut); they create **no immediate shareholder tax** (deferred to sale) vs dividends taxed when paid; dividends **signal** stable recurring earnings while buybacks often signal management thinks shares are **undervalued**.[^32] *(As of 2026)* a **1% excise tax** on net stock buybacks by public companies (IRC §4501, Inflation Reduction Act) applies to repurchases after **Dec 31, 2022**, with the taxable amount **netted** against new stock issued the same year; Treasury/IRS **finalized the regulations in November 2025 at the 1% rate**.[^33] A **proposal to raise it to 4%** (the Stock Buyback Accountability Act of 2026) exists but is **not enacted** — treat as tentative and re-verify.[^33] **Criticism** is real and widely held (EPS/financial engineering, executive-comp incentives tied to EPS, opportunity cost vs R&D/wages, leveraged-buyback fragility), though defenders rebut it.[^34]

### Stock splits & reverse splits
<a id="splits"></a>

- **Forward split** (e.g., 2-for-1, 10-for-1): multiplies share count and divides price proportionally — **no change to market cap, ownership %, voting, or fundamental value.**[^35] Companies split to lower the **nominal** price for accessibility/liquidity, but **fractional shares** (now standard at major brokers) largely remove that rationale.[^35] Recent high-profile splits: **NVIDIA 10-for-1**, **Chipotle 50-for-1**, **Broadcom 10-for-1** (all 2024).[^35] **Disconfirming:** splits **do not create value**; there is a small positive **announcement effect** (~2–4% abnormal return) attributed to **signaling**, not value creation, with mixed long-term evidence.[^36]
- **Reverse split** (e.g., 1-for-10): consolidates shares into fewer at a proportionally higher price; **no value change.** The usual purpose is to lift the price back above the **$1.00 minimum bid** for continued NYSE/Nasdaq listing (Nasdaq triggers a deficiency below $1 for 30 consecutive business days; cure by trading ≥ $1 for 10 consecutive days).[^37] *(As of 2026)* the SEC approved **2024–2025 Nasdaq/NYSE rule changes restricting reverse-split abuse** — a company that recently reverse-split (within the prior year) is **not** eligible for a new bid-price cure period.[^37] Reverse splits carry a **distress stigma** and often see continued selling pressure.[^37]

---

## 4. Corporate actions & the primary market
<a id="primary-market"></a>

How shares are **first created and sold** (the **primary** market) — distinct from the **secondary** market where investors trade existing shares (see the market-participants foundation).

### IPOs
<a id="ipos"></a>

An **initial public offering** is a company's first sale of shares to the public.[^38] In a **firm-commitment** underwriting, investment-bank **underwriters** (a lead **bookrunner** plus a **syndicate**) buy the shares from the issuer and resell them, bearing inventory risk. The process: file a **Form S-1** registration statement with the SEC (which reviews **disclosure adequacy**, not merits), run a **roadshow**, **build a book** of indications of interest, set the **offer price**, and typically go effective the morning of pricing.[^38] A **greenshoe / over-allotment** option lets underwriters sell **up to 15% more shares** and buy them back at the offer price for **price stabilization**.[^39]

**Disconfirming, load-bearing for retail:** IPO shares **skew heavily institutional** — roughly **~90% to institutions, ~10% to individuals** — and brokerages that offer retail IPO access impose asset minimums (often **$100k–$500k**) with **no guarantee** of an allocation.[^40] FINRA **Rules 5130/5131** bar selling new issues to "restricted persons" (industry insiders) and bar "spinning" (rewarding executives with allocations).[^41] First-day **"pops"** are well documented (long-run US average first-day return **~19%**), but studies find IPOs tend to **underperform the broad market over ~3 years**, with the effect partly shrinking against size/style-matched benchmarks.[^42] A **quiet period** and **gun-jumping** rules (Securities Act §5) restrict promotional communication around the filing.[^38]

### Direct listings
<a id="direct-listings"></a>

In a (traditional) **direct listing**, **no new shares are created and no capital is raised** — **existing** shares are sold directly on the exchange with **no underwriter**; a financial advisor and the exchange facilitate **price discovery via an opening auction** (a published **reference price** is an indication, not an offer price).[^43] The company still files an S-1 and clears SEC review. **The SEC approved primary (capital-raising) direct listings** — NYSE in **December 2020**, Nasdaq in **May 2021** — letting a company issue new shares without a firm-commitment underwriting.[^44] **Pros:** avoids the ~6–7% underwriting spread and the IPO-pop "money left on the table," immediate holder liquidity, and **often no lockup**. **Cons:** no capital raised (classic version), more **price volatility** without underwriter stabilization, and no built-in institutional demand book — suited mainly to large, well-known brands (Spotify 2018, Slack 2019, Coinbase 2021).[^43] *(As of 2026)* despite the 2020–21 rule approvals, the **primary capital-raising direct listing has seen essentially no adoption** — verify against current data before stating definitively.[^44]

### SPACs
<a id="spacs"></a>

A **SPAC (special-purpose acquisition company / "blank-check" company)** is a shell that **IPOs to raise cash into a trust** (usually $10/unit), then has roughly **two years (up to three)** to find and merge with a private target (the **de-SPAC**); if no deal closes it liquidates and returns trust cash.[^45] Public holders get **redemption rights** (redeem for the pro-rata trust ≈ $10) at the vote — but the SEC cautions that if you bought above $10 you only get the **pro-rata trust amount, not your purchase price**.[^45] The sponsor typically takes a **~20% "promote"** (founder shares for nominal cost) plus warrants — a dilution and **incentive-misalignment** source (the promote can reward closing **any** deal).[^45]

*(As of 2026, historical)* SPACs boomed in **2020–2021** (2021 alone: ~613 SPAC IPOs, >$160B, over half of US listings) then **busted in 2022+** (a large share of 2021 SPACs liquidated).[^46] **Post-merger de-SPAC stocks have broadly underperformed**, with most falling below the $10 redemption value — directly answering "are SPACs a bad investment": on average, poorly.[^46] The SEC **adopted final SPAC rules in January 2024**: enhanced disclosure of sponsor compensation/conflicts/dilution, **de-SPAC↔IPO alignment** (the target becomes a co-registrant with **Section 11 liability**), required disclosure of **projections** and removal of the **PSLRA safe harbor** for them; notably, the SEC **did not adopt a specific underwriter-liability rule**, instead issuing **guidance** that it reads "underwriter" broadly in a de-SPAC.[^47]

### Follow-on offerings & the "secondary" terminology trap
<a id="followon"></a>

An **already-public** company can issue/sell more shares in a **follow-on offering**:[^48]

- **Dilutive (primary) follow-on:** the company creates and sells **new** shares; proceeds go **to the company**; existing holders are **diluted** (lower EPS).
- **Non-dilutive (secondary) follow-on:** **existing** shares (held by insiders/large holders) are sold; **no new shares**, proceeds go **to the sellers**.

Either way the price tends to fall, via **mechanical dilution** and **negative signaling** (issuing equity can imply management thinks shares are fully valued); seasoned-equity-offering announcement returns are typically **negative**.[^48] **Shelf registration (Form S-3)** lets a qualified company pre-register and sell shares "off the shelf" over a 3-year window; an **at-the-market (ATM)** offering dribbles shares into the market at prevailing prices.[^48]

**The terminology trap (clarify explicitly):** the **"secondary market"** is where investors trade **already-issued** shares among themselves (everyday NYSE/Nasdaq trading) — no money to the issuer. A **"secondary offering"** is a **primary-market event** — a registered sale of a large block of **existing** stock by big holders. Worse, people loosely call a **dilutive follow-on** a "secondary offering" even though a strict *secondary* offering sells **existing** (non-dilutive) shares. Prefer the precise phrasing: **"dilutive follow-on (new shares)"** vs **"non-dilutive secondary (insiders sell existing shares)"**, and reserve **"secondary market"** for investor-to-investor trading.[^48]

### Lockup periods
<a id="lockups"></a>

A **lockup** is a **contractual** restriction (imposed by underwriters, not an SEC mandate) barring insiders/early investors from selling for a set window after the IPO — **commonly 90–180 days (180 is standard)**.[^49] Its purpose is to prevent a post-IPO **supply shock** and to **signal** insider confidence. When the lockup **expires**, the tradable float can jump sharply and the stock often sees **price pressure** around the expiration. **Direct listings frequently have no traditional lockup** (no underwriter to impose one), letting insiders sell from day one.[^49]

---

## References

Footnote labels **`[^14]`–`[^49]`** are inherited from `references/stock-and-equity-trading.md` and intentionally **not** renumbered, so any existing citation of those labels still resolves. The source-tier grading conventions that govern them — **regulator/SRO**, **exchange/index-provider**, **peer-reviewed/academic**, and **reputable financial education** (corroborating), with volatile facts dated *as of 2026* — are stated in full in that file's References section and apply identically here.

[^14]: Britannica Money, "P/E ratio" (trailing vs forward) https://www.britannica.com/money/price-to-earnings-ratio ; Corporate Finance Institute, "Price Earnings Ratio" https://corporatefinanceinstitute.com/resources/valuation/price-earnings-ratio/ (financial education)
[^15]: Nasdaq glossary, "earnings yield" https://www.nasdaq.com/glossary/e/earnings-yield ; Corporate Finance Institute, "Earnings Yield" / PEG https://corporatefinanceinstitute.com/resources/valuation/earnings-yield/ (exchange; financial education)
[^16]: Finance Strategists, "Limitations of the P/E Ratio" (value trap, leverage-blind, accounting distortions) https://www.financestrategists.com/wealth-management/fundamental-vs-technical-analysis/limitations-of-the-price-earnings-ratio/ ; New Constructs, "P/E Ratios Are Misleading" https://www.newconstructs.com/why-pe-ratios-are-misleading/ (financial education; research firm)
[^17]: Deloitte, "Roadmap: Earnings per Share" (basic vs diluted, ASC 260 equal prominence) https://dart.deloitte.com/USDART/home/publications/roadmap/earnings-per-share ; Wall Street Prep, "Diluted EPS" https://www.wallstreetprep.com/knowledge/diluted-eps/ (Big-Four accounting authority; financial education)
[^18]: Corporate Finance Institute, "Price to Book Ratio" https://corporatefinanceinstitute.com/resources/valuation/price-to-book-ratio/ ; O'Shaughnessy Asset Management, "Negative Equity, Veiled Value, and the Erosion of Price-to-Book" (intangibles/buyback distortion) https://www.osam.com/Commentary/negative-equity-veiled-value-and-the-erosion-of-price-to-book (financial education; quant research)
[^19]: Harvard Business School Online, "How to Read & Understand a Profit and Loss Statement" (margin ladder) https://online.hbs.edu/blog/post/income-statement-analysis ; Corporate Finance Institute, "Revenue vs Income" https://corporatefinanceinstitute.com/resources/accounting/revenue-vs-income/ (academic; financial education)
[^20]: SmartAsset, "What Is a Good Dividend Payout Ratio?" https://smartasset.com/financial-advisor/dividend-payout-ratio ; Investing.com Academy, "Dividend Coverage Ratio" https://www.investing.com/academy/stock-picking/dividend-coverage-ratio/ (financial education)
[^21]: Morningstar, "How to Avoid Dividend Traps" https://www.morningstar.com/stocks/how-avoid-dividend-traps ; Motley Fool, "Dividend Yield Trap" https://www.fool.com/investing/how-to-invest/dividend-stocks/dividend-yield-trap/ (financial education)
[^22]: Corporate Finance Institute, "Debt to Equity Ratio" + "Balance Sheet" (accounting identity, residual equity, current ratio) https://corporatefinanceinstitute.com/resources/accounting/debt-to-equity-ratio-formula/ ; SEC / Investor.gov, "Beginners' Guide to Financial Statements" https://www.sec.gov/reportspubs/investor-publications/investorpubsbegfinstmtguide (financial education; regulator)
[^23]: SEC / Investor.gov — Form 10-K / Form 10-Q (filing cadence, audited vs unaudited, EDGAR) https://www.investor.gov/introduction-investing/investing-basics/glossary/form-10-k (regulator)
[^24]: Charles Schwab, "Forward Guidance" / earnings https://www.schwab.com/learn/story/what-to-know-earnings-season ; Britannica Money, "forward guidance" https://www.britannica.com/money/forward-guidance ; TipRanks, "Analyst ratings" glossary https://www.tipranks.com/glossary/a/analyst-ratings (financial education) [guidance-move magnitudes illustrative]
[^25]: Ryan O'Connell (CFA), "Growth vs Value Investing" + "Value Investing" https://www.ryanoconnellfinance.com/ ; VanEck, "Dividend investing" https://www.vaneck.com/us/en/blogs/income-investing/ ; S&P Dow Jones Indices, Dividend Aristocrats methodology (25-year criterion) https://www.spglobal.com/spdji/en/indices/dividends-factors/sp-500-dividend-aristocrats/ (CFA practitioner; asset manager; index-provider) [Aristocrat count ~69, as of 2026]
[^26]: Vanguard, value-vs-growth research https://corporate.vanguard.com/content/corporatesite/us/en/corp/articles/value-vs-growth-stocks.html ; J.P. Morgan Asset Management, "Guide to the Markets" value/growth https://am.jpmorgan.com/us/en/asset-management/adv/insights/market-insights/guide-to-the-markets/ ; Morningstar, value/growth rotation https://www.morningstar.com/markets (asset-manager research; financial education) [year-by-year leadership volatile, as of 2026]
[^27]: SEC / Investor.gov — "Ex-Dividend Dates: When Are You Entitled to Stock and Cash Dividends" (the four dates; buy-before-ex rule) https://www.investor.gov/introduction-investing/investing-basics/glossary/ex-dividend-dates-when-are-you-entitled-stock-and ; IRS Topic No. 404, Dividends (qualified vs ordinary, holding-period test) https://www.irs.gov/taxtopics/tc404 (regulator; IRS)
[^28]: DTCC, "T+1 Dividend Processing FAQ" (ex-date = record date under T+1) https://www.dtcc.com/-/media/Files/PDFs/T2/T1-Dividend-Processing-FAQ.pdf ; Charles Schwab, "Ex-Dividend Dates and Dividend Risk" (approximate price drop) https://www.schwab.com/learn/story/ex-dividend-dates-understanding-dividend-risk (clearing utility — primary; financial education) [T+1 effective May 28, 2024; as of 2026]
[^29]: NYU Stern / Damodaran, "Dividend Irrelevance" (Modigliani–Miller) https://pages.stern.nyu.edu/~adamodar/New_Home_Page/invfables/dividirrelevance.htm (academic)
[^30]: Charles Schwab, "How a Dividend Reinvestment Plan (DRIP) Works" https://www.schwab.com/learn/story/how-dividend-reinvestment-plan-works ; Motley Fool, "Dividend Reinvestment" https://www.fool.com/investing/stock-market/types-of-stocks/dividend-stocks/dividend-reinvestment/ (financial education)
[^31]: Interactive Brokers, "Dividend Types" (special, stock vs cash) https://www.interactivebrokers.com/campus/trading-lessons/dividend-types/ ; SmartAsset, "Stock Dividend vs Cash Dividend" https://smartasset.com/financial-advisor/stock-dividend-vs-cash-dividend (broker; financial education)
[^32]: Skadden, "Revisiting Share Repurchases" (OMR/tender/ASR; Rule 10b-18) https://www.skadden.com/insights/publications/2022/03/revisiting-share-repurchases-in-volatile-times ; CFA Institute Research Foundation, "Stock Buybacks" literature review (buybacks vs dividends; EPS mechanics; signaling) https://rpc.cfainstitute.org/sites/default/files/-/media/documents/book/rf-lit-review/2022/rflr-stock-buybacks.pdf (law firm; academic/industry body)
[^33]: Congressional Research Service (Congress.gov), Report R47397, "The 1% Excise Tax on Stock Repurchases" (rate, netting, non-deductibility, Jan 1 2023 effective) https://www.congress.gov/crs-product/R47397 ; Sullivan & Cromwell, "Stock Buyback Tax" final regulations (finalized Nov 21, 2025 at 1%) https://www.sullcrom.com/insights/memo/2025/November/Stock-Buyback-Tax (CRS — primary/non-partisan; law firm) [1% confirmed; 4% proposal tentative; as of 2026]
[^34]: Harvard Law School Forum on Corporate Governance, "Share Buybacks and Executive Compensation: Assessing Key Criticisms" https://corpgov.law.harvard.edu/2023/07/16/share-buybacks-and-executive-compensation-assessing-key-criticisms/ (academic)
[^35]: SoFi, "What Is a Stock Split?" https://www.sofi.com/learn/content/what-is-a-stock-split/ ; Britannica Money, "Fractional share investing" (undercuts split rationale) https://www.britannica.com/money/fractional-share-investing ; Bloomberg, "What is a stock split" (NVDA/AVGO/CMG 2024) https://www.bloomberg.com/news/articles/2024-06-01/what-is-a-stock-split-what-to-know-about-nvidia-s-nvda-split (financial education; reputable media)
[^36]: ScienceDirect, "Do stock splits signal undervaluation?" (announcement effect = signaling, not value) https://www.sciencedirect.com/science/article/abs/pii/S2214635016000113 (peer-reviewed)
[^37]: Skadden, "SEC Approves Nasdaq Rule Change" (2024–2025 reverse-split restrictions; $1 min bid, 30-day trigger, 10-day cure) https://www.skadden.com/insights/publications/2024/11/sec-approves-nasdaq-rule-change ; K&L Gates, "The State of Play for Reverse Stock Splits by Nasdaq- and NYSE-Listed Issuers" https://www.klgates.com/The-State-of-Play-for-Reverse-Stock-Splits-by-Nasdaq-and-NYSE-Listed-Issuers-1-23-2025 (law firms) [2025 rule change; as of 2026]
[^38]: SEC / Investor.gov — IPO glossary; gun-jumping/quiet period (Securities Act §5) https://www.investor.gov/introduction-investing/investing-basics/glossary/initial-public-offering-ipo ; Cornell Law (Wex), "gun jumping" https://www.law.cornell.edu/wex/gun_jumping (regulator; legal reference)
[^39]: Corporate Finance Institute, "Over-Allotment (Greenshoe) Option" (up to 15%, stabilization) https://corporatefinanceinstitute.com/resources/equities/overallotment-greenshoe-option-ipo/ (financial education)
[^40]: Fidelity, "IPO share allocation process" (~90% institutional / ~10% retail; asset minimums; no guarantee) https://www.fidelity.com/learning-center/trading-investing/trading/ipo-share-allocation-process ; Charles Schwab, "How IPO Shares Are Priced and Allotted" https://www.schwab.com/learn/story/getting-slice-how-ipo-shares-are-priced-and-allotted (broker/financial education)
[^41]: FINRA Rule 5131 (new-issue allocations, anti-spinning) https://www.finra.org/rules-guidance/rulebooks/finra-rules/5131 ; InnReg, "FINRA Rule 5130 Explained" (restricted persons) https://www.innreg.com/resources/finra-rules/5130-restrictions-on-the-purchase-and-sale-of-initial-equity-public-offerings (SRO — primary; financial education) [Apr 2026 FINRA 5130/5131 amendments proposed — verify]
[^42]: Jay R. Ritter (University of Florida), IPO Data / "Initial Public Offerings: Underpricing" (long-run ~19% first-day average; 3-year underperformance) https://site.warrington.ufl.edu/ritter/ipo-data/ (academic — authoritative IPO dataset) [first-day-return figures volatile, as of 2026]
[^43]: Corporate Finance Institute, "Direct Listing — Overview, Pros/Cons" https://corporatefinanceinstitute.com/resources/equities/direct-listing/ ; Fenwick, "SEC Approves Nasdaq Rule Change Allowing Direct Listings with a Capital Raise" https://www.fenwick.com/insights/publications/sec-approves-nasdaq-rule-change-allowing-direct-listings-with-a-capital-raise (financial education; law firm)
[^44]: Covington, "SEC Approves NYSE Rule Allowing Primary Issuances In Direct Listings" (NYSE Dec 2020) https://www.cov.com/en/news-and-insights/insights/2021/01/sec-approves-nyse-rule-allowing-primary-issuances-in-direct-listings ; Paul Weiss, "SEC Approves Nasdaq Rule Change Permitting Primary Direct Floor Listings" (Nasdaq May 2021) https://www.paulweiss.com/practices/transactional/capital-markets/publications/sec-approves-nasdaq-rule-change-permitting-primary-direct-floor-listings?id=40140 (law firms) [primary-DL low adoption, verify as of 2026]
[^45]: SEC / Investor.gov, "What You Need to Know About SPACs — Updated Investor Bulletin" (lifecycle, trust, redemption, ~20% promote, warrants, sponsor-conflict caution) https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/what-you (regulator)
[^46]: Yale Journal on Regulation, "Was the SPAC Crash Predictable?" (boom/bust, post-merger underperformance, dilution) https://www.yalejreg.com/bulletin/was-the-spac-crash-predictable/ ; Morgan Lewis, "A Look at the SPAC Market in 2022" https://www.morganlewis.com/pubs/2022/04/a-look-at-the-spac-market-in-2022 (academic; law firm) [2020-22 figures historical, as of 2026]
[^47]: Davis Polk, "SEC adopts final SPAC rules" (Jan 2024: disclosure, co-registrant/§11 liability, projections, PSLRA safe-harbor removed, underwriter-liability guidance not a rule) https://www.davispolk.com/insights/client-update/sec-adopts-final-spac-rules ; Ropes & Gray, "SEC Adopts New Rules Regarding SPAC Transactions" https://www.ropesgray.com/en/insights/alerts/2024/02/sec-adopts-new-rules-regarding-spac-transactions (law firms) [SEC 2024 SPAC rules; verify effective dates as of 2026]
[^48]: Cornell Law (Wex), "follow-on offering," "secondary offering," "secondary market" (dilutive vs non-dilutive; terminology trap) https://www.law.cornell.edu/wex/follow-on_offering ; Perkins Coie, "Public Company Handbook Ch.12: Follow-On Offerings and Shelf Registrations" (S-3 shelf, ATM) https://perkinscoie.com/public-company-handbook-chapter-12-follow-offerings-and-shelf-registrations (legal reference; law firm)
[^49]: Wikipedia, "Lock-up period" (90–180 days, 180 standard, contractual not statutory) https://en.wikipedia.org/wiki/Lock-up_period ; SoFi, "Navigating the IPO Lock-Up Period" (expiration supply event) https://www.sofi.com/learn/content/navigating-ipo-lock-up-period/ (tertiary; financial education)
