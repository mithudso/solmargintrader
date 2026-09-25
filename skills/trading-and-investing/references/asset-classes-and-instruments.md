<!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". -->

# Asset Classes & Instruments (foundation)

What the major asset classes **are** and how a US retail participant **accesses** each. This is the "what can I trade or own" layer. Instrument-specific *trading* depth lives in the spokes (`stock-and-equity-trading`, `fixed-income-and-bond-markets`, `forex-and-currency-trading`, `options-trading-and-strategies`, `derivatives-futures-and-swaps`, `crypto-and-digital-asset-trading`).

> Educational information, not advice. All of these carry risk of loss. Figures and product availability change — dated **as of 2026**; verify with the primary regulator.

## Contents

- [Equities / stocks](#equities--stocks)
- [Fixed income / bonds](#fixed-income--bonds)
- [Currencies / forex](#currencies--forex)
- [Commodities](#commodities)
- [Crypto / digital assets](#crypto--digital-assets)
- [Pooled vehicles: ETFs vs mutual vs index vs target-date](#pooled-vehicles)
- [Derivatives (overview only)](#derivatives-overview-only)
- [References](#references)

## Equities / stocks

A **stock** (equity) is a security giving the holder a fractional **ownership** stake in a company.[^1] Owners hold it for three returns: **capital appreciation** (price rising), **dividends** (a distribution of earnings), and influence via **voting**.[^1]

- **Common vs preferred.** Common stock carries voting rights and a variable, non-guaranteed dividend.[^1][^2] **Preferred** stock usually has no vote but pays a typically *fixed* dividend **ahead of** common holders and ranks ahead of common in bankruptcy — so it behaves more like income with less price-growth potential.[^1][^2]
- **Dividends** are a distribution of company earnings; common dividends fluctuate with profitability, preferred are usually fixed.[^1][^2]
- **Market capitalization** = share price × shares outstanding.[^3] FINRA buckets companies as mega- (> $200B), large- ($10B–$200B), mid- ($2B–$10B), small- ($250M–$2B), and micro-cap (< $250M); larger caps tend to be less volatile.[^3]
- **Access:** through a brokerage account; shares trade on exchanges (NYSE, Nasdaq). Price falls as well as rises and principal can be lost.[^1]

## Fixed income / bonds

A **bond** is a **debt** security: the investor lends money to an issuer for **interest plus return of principal** at maturity. Issuers: the **US Treasury**, **corporations**, and **state/local governments** (municipal).[^4][^5]

- **Face/par value** — repaid at maturity (commonly $1,000); a bond "at 100" trades at 100% of par.[^4]
- **Coupon** — the fixed annual interest rate set at issuance ($1,000 par × 5% = $50/yr).[^4]
- **Yield** — *current yield* = coupon ÷ price; *yield to maturity (YTM)* = total return if bought at market and held to maturity.[^4]
- **Price–yield inverse relationship (load-bearing).** Per FINRA: "as the price of a bond goes up, its yield goes down, and vice versa."[^4] When market rates **rise**, an existing bond's fixed coupon is relatively less attractive, so its **price falls** (and vice versa).[^4] A bond trades **at par** when its coupon matches prevailing rates, at a **premium** above, at a **discount** below.[^4]
- **Treasuries:** bills (≤1 yr, zero-coupon), notes/bonds (longer, periodic interest), TIPS (inflation-adjusted principal); buy at TreasuryDirect.gov ($100 minimum) or via a broker.[^6]
- **Municipal vs corporate:** muni interest is typically federal-tax-exempt (and state-tax-exempt for in-state residents), so muni yields are usually **lower** than comparable taxable corporates; general-obligation munis are backed by taxing power, revenue bonds by a specific revenue stream.[^5]
- **Bonds are not risk-free** (negation finding): they carry **interest-rate risk** (price falls when rates rise), **credit/default risk**, and **inflation risk**.[^7] Holding an individual bond to maturity returns principal but does not erase the opportunity cost of rising rates; longer-duration bonds swing more.[^7]

Deeper bond mechanics (yield curve, duration/convexity, credit spreads, repo) → `fixed-income-and-bond-markets`.

## Currencies / forex

**Foreign exchange (forex/FX)** is trading one currency against another in **currency pairs** (e.g., EUR/USD). The first currency is the **base**, the second the **quote**; the price is how much quote currency buys one unit of base.[^8]

- **Largest market by volume.** FX is the largest, most liquid market in the world — BIS Triennial Survey turnover is in the multi-trillion-dollar-per-day range; **EUR/USD** is the single most-traded pair and a handful of "majors" dominate.[^8] *(Cite "per the latest BIS Triennial Survey" rather than a fixed daily figure — the number is survey-vintage-dependent.)*
- **Structure.** Retail spot FX is largely **over-the-counter** (through brokers/dealers, not a central exchange) and is typically **leveraged**.[^8]
- **US retail leverage caps (as of 2026).** The CFTC caps retail forex leverage at **~50:1 on major pairs** (2% min security deposit) and **~20:1 on others** (5%); the NFA sets the deposit levels and defines which currencies are "major."[^9] Verify the current major-currency list and caps at cftc.gov/nfa.futures.org — they are periodically reviewed.

Deeper FX (pips, lots, carry, sessions, exotics) → `forex-and-currency-trading`.

## Commodities

**Commodities** are basic goods — **energy** (crude, natural gas), **metals** (gold, silver, copper), **agriculture** (wheat, coffee, corn), **livestock**.[^10][^11] Federally regulated by the **CFTC**.[^10]

Three retail-access paths:[^10][^11]
1. **Physical/spot** — holding the commodity directly; uncommon for retail.
2. **Futures** — leveraged derivative contracts to buy/sell a set quantity at a set price on a future date; the CFTC warns the "high degree of leverage … can result in large and immediate" gains *and* losses.[^10][^11]
3. **Funds/ETPs** — commodity ETFs/ETNs/pools, or equities of commodity-related companies (miners, refiners).

**Key mechanic (negation finding):** most commodity ETPs are **futures-/derivatives-based, not physical**, and the CFTC warns a futures-based commodity ETP may **not track the spot price closely** because of the cost of rolling futures (e.g., contango).[^10] Assuming a commodity ETF moves one-for-one with the headline spot price is a common retail mistake.[^10]

## Crypto / digital assets

**Cryptocurrencies** (e.g., **Bitcoin/BTC**, **Ethereum/ETH**) are digital assets on a blockchain; **tokens** live on blockchains; **stablecoins** are designed to hold a stable value, typically pegged 1:1 to the US dollar.[^12][^13]

- **Spot vs derivatives.** On a **spot** exchange you trade the asset itself; **crypto derivatives** (futures, options, perpetual swaps) derive value from an underlying coin and let traders speculate without owning it.[^12]
- **Exchanges & custody.** Retail typically buys on an exchange after KYC, funded from a bank/card.[^12] The SEC frames **custody** as how/where you store and access assets via wallets holding **private keys** — a private key authorizes transactions and, if lost, access is **permanently** lost.[^14] Two models: **custodial** (an exchange/custodian holds your keys — risk: hack, shutdown, bankruptcy) and **self-custody** (you hold your keys — risk: loss, theft, device compromise).[^14]
- **Stablecoin regulation (as of 2026).** The **GENIUS Act** (enacted July 2025) set a federal framework: 100% liquid-asset reserves, monthly disclosures, a ban on paying yield to holders, and a federal-state licensing regime.[^13] USDT (Tether) and USDC (Circle) dominate issuance. *(Treat compliance specifics as evolving; verify against the enacted statute.)*
- **Spot crypto ETFs (as of 2026).** Spot **Bitcoin** ETFs were SEC-approved **Jan 10, 2024** (11 funds); spot **Ether** ETFs launched **July 2024** — giving exposure without a wallet or exchange account; both have grown large, and major brokerages have rolled out direct crypto access.[^15] The 2024 approval dates are firm; AUM/rollout figures are volatile, dated as of 2026.

Deeper centralized-crypto trading → `crypto-and-digital-asset-trading`; on-chain/DEX/DeFi → `defi-and-onchain-trading`.

## Pooled vehicles
<a id="pooled-vehicles"></a>

- **Mutual fund (open-end).** Per the SEC, an "SEC-registered **open-end investment company** that pools money from many investors."[^16] You buy/redeem **directly with the fund** at the **next end-of-day NAV** — priced once per business day, no bid/ask spread.[^16]
- **ETF (exchange-traded fund).** A fund whose shares **trade intraday on an exchange like a stock**, so price can differ slightly from NAV (the bid/ask spread).[^17] An ETF is a **structure, not a strategy** — it can be passive or active.[^17] Unlike **closed-end funds** (which can trade at large premiums/discounts), the ETF creation/redemption mechanism keeps price close to NAV.[^17]
- **Index fund vs active.** Per the SEC, index funds follow a **passive** strategy to approximate an index's return before fees; **actively managed** funds try to beat a stated objective.[^16] An index fund can be packaged as a mutual fund *or* an ETF.[^17]
- **Expense ratios (as of 2025–2026).** Passive funds are generally cheaper; in 2025 index mutual funds averaged ~0.05%/yr and index-equity ETFs ~0.14% asset-weighted, with some S&P 500 ETFs at ≤0.03%.[^17] Dated; verify annually.
- **Target-date funds (TDFs).** Typically a **fund-of-funds** that automatically shifts from more stocks to more bonds as a target year nears (the **glide path**); a common 401(k) default.[^18]
- **ETF/index myths (negation finding).** "ETFs are riskier than mutual funds" is unsupported — **risk comes from holdings, not the wrapper**.[^19] Legitimate *criticisms* of passive investing exist (mega-cap concentration, price-discovery and index-rebalancing concerns), counterweighted by the long-run finding that few active funds beat their benchmark.[^19] Presented as a live debate, not settled fact.

The *consumer how-to* of picking funds for retirement → `investing-and-retirement`; allocation **theory** → `portfolio-theory-and-asset-allocation`.

## Derivatives (overview only)

*A deeper family spoke owns the detail — this is intentionally high-level.*

Derivatives are **contracts whose value derives from an underlying** asset or benchmark; the four main types are **forwards, futures, options, and swaps**, used to **hedge** or **speculate**, and usually **leveraged** (amplifying risk and reward).[^20]

- **Futures** — standardized, exchange-traded, **binding on both sides** to transact a set quantity at a set price on a set date; speculators are drawn by leverage (only initial margin posted).[^20][^21]
- **Forwards** — like futures but **customized and OTC**.[^20]
- **Options** — the **right, not the obligation**, to buy (**call**) or sell (**put**) at a **strike** by an **expiration**; one listed equity-options contract typically represents **100 shares**.[^20][^21]
- **Swaps** — exchange of future cash flows (commonly fixed-for-floating).[^20]

Across all four, the **instrument is the contract**, not the underlying. Options depth → `options-trading-and-strategies`; futures/forwards/swaps depth → `derivatives-futures-and-swaps`.

## References

Primary regulators/SROs are tier-1; established references tier-2; broker/educational tier-3. Volatile claims dated *as of 2026*.

[^1]: SEC / Investor.gov — Stocks. https://www.investor.gov/introduction-investing/investing-basics/investment-products/stocks (tier-1, regulator)
[^2]: Corporate Finance Institute — Common vs Preferred Shares. https://corporatefinanceinstitute.com/resources/equities/common-vs-preferred-shares/ (tier-2)
[^3]: FINRA — Market Cap. https://www.finra.org/investors/insights/market-cap (tier-1, SRO)
[^4]: FINRA — Bond Yield and Return (price–yield inverse, coupon, par, premium/discount). https://www.finra.org/investors/insights/bond-yield-return (tier-1, SRO)
[^5]: SEC / Investor.gov — Municipal Bonds / Bonds. https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products-0 (tier-1, regulator)
[^6]: TreasuryDirect — Buying a marketable security. https://www.treasurydirect.gov/marketable-securities/buying-a-marketable-security/ (tier-1, US Treasury)
[^7]: Fidelity — Bond duration & risks (interest-rate/credit/inflation risk). https://www.fidelity.com/learning-center/investment-products/fixed-income-bonds/duration (tier-3, broker; negation/disconfirming)
[^8]: FOREX.com — Most-traded currencies / base & quote (BIS volume context). https://www.forex.com/en-us/trading-guides/the-top-10-most-traded-currencies/ (tier-3, broker)
[^9]: CFTC/NFA — Retail forex final rule fact sheet (50:1 majors / 20:1 others). https://www.cftc.gov/ (tier-1, regulator) — verify current caps at cftc.gov / nfa.futures.org
[^10]: CFTC — Customer Advisory: Commodity ETPs (futures-vs-physical; roll/contango tracking). https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/ (tier-1, regulator)
[^11]: FINRA — Futures and Commodities overview. https://www.finra.org/investors/investing/investment-products/futures-and-commodities/overview (tier-1, SRO)
[^12]: Coinbase Learn — Crypto basics (spot vs derivatives, exchanges/KYC). https://www.coinbase.com/learn/crypto-basics (tier-3, industry)
[^13]: Brookings — What are stablecoins and how are they regulated. https://www.brookings.edu/articles/what-are-stablecoins-and-how-are-they-regulated/ (tier-2, think tank) + GENIUS Act coverage (verify against statute)
[^14]: SEC / Investor.gov — Crypto Asset Custody Basics for Retail Investors (Investor Bulletin). https://www.investor.gov/ (tier-1, regulator)
[^15]: Congressional Research Service — SEC Approves Bitcoin ETPs (IF12573). https://www.congress.gov/crs-product/IF12573 (tier-1, govt) + industry AUM data (as of 2026)
[^16]: SEC / Investor.gov — Mutual Funds and ETFs (open-end, NAV, index vs active). https://www.investor.gov/introduction-investing/investing-basics/investment-products/mutual-funds-and-exchange-traded-1 (tier-1, regulator)
[^17]: Fidelity / Vanguard / Schwab — ETF vs index fund vs mutual fund (intraday vs NAV, expense ratios, structure-not-strategy). https://www.fidelity.com/learning-center/smart-money/etf-vs-index-fund (tier-3, broker)
[^18]: SEC / Investor.gov — Target-Date Funds Investor Bulletin (fund-of-funds, glide path). https://www.investor.gov/ (tier-1, regulator)
[^19]: State Street / Morningstar — Debunking ETF myths; arguments for/against index investing. https://www.ssga.com/ (tier-2/3; negation/disconfirming, contested)
[^20]: Investopedia / AnalystPrep — Derivatives (forwards/futures/options/swaps, leverage). https://www.investopedia.com/terms/d/derivative.asp (tier-2)
[^21]: Schwab — Options contracts (right-not-obligation, strike, 100 shares). https://www.schwab.com/options/options-contracts (tier-3, broker)
