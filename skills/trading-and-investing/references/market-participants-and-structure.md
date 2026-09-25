<!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". -->

# Market Participants & Structure (foundation)

**Who** is in the market and the **primary-vs-secondary** structure they trade within. Order-routing internals (PFOF/NBBO) live in `order-lifecycle-and-execution.md`; deep execution mechanics → `market-microstructure-and-execution`.

> Educational information, not advice. Dated **as of 2026**; verify with the primary regulator.

## Contents

- [The cast of participants](#the-cast-of-participants)
- [What a clearinghouse does (and why it cuts counterparty risk)](#clearinghouses)
- [Settlement and the T+1 cycle](#settlement-and-the-t1-cycle)
- [Primary vs secondary markets](#primary-vs-secondary-markets)
- [Exchange vs OTC / dealer market](#exchange-vs-otc)
- [Market makers and the bid-ask spread](#market-makers-and-the-bid-ask-spread)
- [References](#references)

## The cast of participants

- **Retail investors/traders** — individuals investing their own money in their own accounts, usually through a broker.[^1][^2] Individually small, but in aggregate an important source of liquidity.[^1] Critically, retail does **not** trade directly on an exchange — orders go through a broker that routes them to a venue; direct-to-exchange access for an individual is the exception, not the norm (negation finding).[^2]
- **Institutional investors** — large professional organizations investing on others' behalf at high volume ("smart money"):[^1][^3] **mutual funds**/ETFs (pooled, SEC-registered, report holdings periodically), **pension funds**, **hedge funds** (private pools that may use leverage, derivatives, and short-selling), and **insurance companies** (invest premiums, heavily in bonds). Most must register with the SEC and file reports.[^3]
- **Broker-dealers** — the regulated "plumbing" between retail and the markets: custody, execution, routing, reporting, clearing.[^2][^4] The term spans two capacities:[^4]
  - **Agency broker** — acts as *agent*, matching your order to the market for a **commission**; doesn't take the other side.
  - **Principal dealer** — acts as *principal*, trading from its own inventory (buying from you marked-down, selling to you marked-up), bearing inventory risk and earning the spread/markup.
  - A firm **can't be both agent and principal in the same trade**, and must disclose its capacity and compensation.[^4]
- **Market makers / liquidity providers** — firms (or **wholesalers**) that continuously quote a **two-sided market** (bid and ask) and stand ready to trade, supplying immediate liquidity.[^4][^5] A specialized role a dealer plays, not a separate legal category.
- **Exchanges** — organized, centralized "lit" venues (NYSE, Nasdaq) that match many buyers and sellers and publicly display quotes; they are self-regulatory organizations.[^2][^6]
- **Clearinghouses / central counterparties (CCPs)** — step between the two sides *after* execution to manage credit risk and guarantee completion (next section).[^7][^8]

## Clearinghouses
<a id="clearinghouses"></a>

A **central counterparty (CCP)** inserts itself between buyer and seller and absorbs the trade's counterparty credit risk.[^7][^9] It reduces risk four ways:[^7][^9]

1. **Novation** — the CCP legally becomes "the buyer to every seller and the seller to every buyer," guaranteeing the contract if either side defaults; each side now faces a highly-capitalized, risk-managed CCP instead of an unknown counterparty.[^7][^9]
2. **Multilateral netting** — offsetting obligations net down so only net amounts move; for US equities, DTCC's NSCC reports netting reduces the value of payments to be exchanged by an average of ~98% each day (date as of 2026).[^8]
3. **Margin/collateral** — members post initial (and variation) margin; CCPs hold a guarantee/default fund.[^7][^9]
4. **Guaranteeing settlement** — by standing behind every trade, the CCP ensures completion even if a member fails.[^7][^9]

Named US CCPs (overview): **DTCC / NSCC** (National Securities Clearing Corporation) is the CCP for virtually all broker-to-broker **US equities** (and listed corporate/muni bond) trades;[^8] **OCC** (The Options Clearing Corporation) is the CCP for US exchange-listed **options**, buyer to every seller and seller to every buyer, under SEC (and CFTC) oversight.[^10]

## Settlement and the T+1 cycle

**Settlement** is the official transfer of securities to the buyer's account and cash to the seller's.[^11] (Trading sets *who owes what*; settlement is the actual delivery-versus-payment that finalizes it.)

**Current US standard cycle: T+1 (as of 2026).** US securities settle **one business day after trade date**. The SEC shortened the standard cycle from **T+2 to T+1 effective May 28, 2024**.[^11][^12] Sell Monday → settle (cash available) Tuesday.[^11] Covers stocks, most bonds, ETFs, certain mutual funds. SEC rationale: a shorter cycle reduces counterparty/credit risk.[^12]

*Trade-offs (negation finding):* T+1 compresses post-trade processing and strains securities lending, repo, and especially **cross-border FX** (time-zone mismatches), raising settlement-fail risk where automation is weak — but it remains the US standard.[^11][^12] (Magnitude figures come from industry sources — directional, not precise.)

## Primary vs secondary markets

- **Primary market** — where **new** securities are issued and sold for the **first time**, and where the **issuer actually raises capital**.[^13][^14] For stock this is the **IPO** (with underwriters); new bonds are issued the same way. **Underwriters** (investment banks) plan, price, and market the offering — in a firm-commitment deal an underwriting syndicate buys the entire issue from the issuer and resells it to investors.[^15]
- **Secondary market** — where investors trade **already-issued** securities **among themselves** (NYSE/Nasdaq).[^13][^14] The **issuer is not a party** and **raises no new money** here; the secondary market provides **liquidity** and **price discovery**.[^13][^14] *(This "issuer only raises money in the primary market" point is the core distinction, consistent across sources.)*

## Exchange vs OTC
<a id="exchange-vs-otc"></a>

- **Exchange ("lit" market)** — centralized venue matching buyers and sellers; quotes and trades publicly displayed → high transparency.[^6][^16]
- **OTC / dealer market** — a decentralized network of dealers quoting and trading **bilaterally** (dealer-to-dealer or dealer-to-customer) rather than via a central order book.[^16] Less transparent, fewer rules; in the US, OTC quoting is limited to SEC-registered FINRA-member broker-dealers, and platforms like OTC Link are registered as ATSs.[^16] The contrast: **centralized + transparent + publicly-quoted (exchange)** vs **decentralized + dealer-intermediated + bilaterally-negotiated (OTC)**.[^16]

## Market makers and the bid-ask spread

A market maker quotes a **bid** (price it will buy at) and an **ask/offer** (price it will sell at); the gap is the **bid-ask spread**.[^5][^11] It buys at the lower bid and sells at the higher ask, earning the spread as compensation for **providing immediacy, holding inventory, and bearing short-term price risk**.[^5] Any single spread is tiny; it accumulates across volume.[^5] **Liquidity** is the ease of buying/selling quickly without moving the price much — market makers are its primary suppliers.[^5]

*Negation finding:* the myth that market makers "hunt" retail or that market-making is risk-free is countered by the reality that in deep, competitive markets no single maker controls price, and makers face **inventory imbalance, adverse selection, and volatility** risk they must hedge.[^5] (Debunking specifics are tier-3; the risk-compensation principle is tier-1/2.) Order-routing internals (PFOF/NBBO) → `order-lifecycle-and-execution.md`.

## References

Tier-1 = regulator/SRO/official CCP; tier-2 = established reference; tier-3 = commercial/educational. Volatile claims dated *as of 2026*.

[^1]: FINRA — Institutional Investors and "Smart Money." https://www.finra.org/investors/insights/institutional-investors-and-smart-money (tier-1, SRO)
[^2]: FINRA — Where Do Stocks Trade? https://www.finra.org/investors/insights/where-do-stocks-trade (tier-1, SRO)
[^3]: SEC — institutional-investor reporting / 13F context. https://www.sec.gov/ (tier-1, regulator)
[^4]: SEC — Guide to Broker-Dealer Registration (agency vs principal capacity, disclosure). https://www.sec.gov/about/divisions-offices/division-trading-markets/ (tier-1, regulator)
[^5]: Citadel Securities — What Is a Market Maker? (two-sided quotes, inventory/adverse-selection risk). https://www.citadelsecurities.com/what-we-do/what-is-a-market-maker/ (tier-2, primary but interested party)
[^6]: FinanceTrain — Secondary Market: Exchanges vs OTC. https://financetrain.com/secondary-market-exchanges-vs-otc-market (tier-3, corroborated)
[^7]: Federal Reserve Bank of Chicago — Understanding Derivatives, Ch. 2: Central Counterparty Clearing (novation, margin, default fund). https://www.chicagofed.org/ (tier-1, Fed)
[^8]: DTCC — NSCC / Understanding Settlement (CCP for US equities; ~98% netting). https://www.dtcc.com/about/businesses-and-subsidiaries/nscc (tier-1, the US clearing utility) — netting figure as of 2026
[^9]: Wikipedia — Central counterparty clearing. https://en.wikipedia.org/wiki/Central_counterparty_clearing (tier-2)
[^10]: The Options Clearing Corporation — theocc.com (CCP for US listed options). https://www.theocc.com/ (tier-1, CCP)
[^11]: SEC / Investor.gov — New "T+1" Settlement Cycle Investor Bulletin (settlement definition, bid/ask/spread). https://www.investor.gov/ (tier-1, regulator)
[^12]: SEC — Press Release 2024-62: T+1 implementation (effective May 28, 2024). https://www.sec.gov/newsroom/press-releases/2024-62 (tier-1, regulator)
[^13]: Britannica Money — Primary Markets vs Secondary Markets. https://www.britannica.com/money/primary-vs-secondary-markets (tier-2)
[^14]: Motley Fool — Primary and secondary markets / capital markets. https://www.fool.com/investing/stock-market/market-sectors/financials/capital-markets (tier-3, corroborated)
[^15]: SEC / Investor.gov — Initial Public Offerings (underwriting syndicate buys from issuer, resells). https://www.investor.gov/introduction-investing/investing-basics/glossary/initial-public-offerings-why-individuals-have (tier-1, regulator)
[^16]: KeyDifferences — Difference Between OTC and Exchange. https://keydifferences.com/difference-between-otc-and-exchange.html (tier-3, corroborated)
