<!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". -->

# Order Lifecycle & Execution (foundation)

How a retail order travels from the broker app to the market, the order types every participant should know, and the routing concepts (PFOF, NBBO, best execution). This is the overview; deep microstructure (maker-taker, Reg NMS internals, dark-pool detail, sub-penny price improvement, SIP vs direct feeds) → `market-microstructure-and-execution`.

> Educational information, not advice. Dated **as of 2026**; verify with the primary regulator.

## Contents

- [The end-to-end order path](#the-end-to-end-order-path)
- [Order types every retail participant should know](#order-types)
- [Payment for order flow (PFOF) and best execution](#pfof-and-best-execution)
- [The NBBO](#the-nbbo)
- [Bid, ask, spread, and quoted price vs fill](#bid-ask-spread-and-fill)
- [The $0-commission landscape](#the-0-commission-landscape)
- [References](#references)

## The end-to-end order path

The chain in one line: **app order → broker routes (best-execution duty) → execution venue (exchange / market-maker–wholesaler / internalizer / ATS-dark-pool / ECN) → execution → clearing (CCP guarantees & nets) → settlement (T+1)**.[^1][^2][^3]

1. **You place the order** in the broker app; the broker must decide how to handle it (it usually does not match your trade itself on a public exchange).[^1][^2]
2. **The broker routes** the order — deciding *where* to find the other side; the venue where it executes is the **execution venue**.[^3][^1] Routing is governed by the broker's **duty of best execution** (below).[^1]
3. **The order reaches a venue:**[^1][^3]
   - **Exchanges** (NYSE, Nasdaq) — lit markets, quotes publicly displayed.
   - **Market makers / wholesalers** — a wholesaler is a broker-dealer acting as market maker for *other* broker-dealers; many retail brokers route significant flow to one or more wholesalers.
   - **Internalization** — the broker fills from its own (or an affiliate's) inventory.
   - **ATS / dark pools** — an Alternative Trading System acts like an exchange but isn't an SRO; a dark pool doesn't publicly display quotes (designed for large institutional orders), though trades are still reported to FINRA. *(Depth → microstructure spoke.)*
   - **ECNs** — electronic networks that auto-match orders at specified prices; brokers often route *limit* orders here.
4. **Execution** — the fill price may differ from the price you saw (see slippage below).[^4]
5. **Clearing** — confirms details and, via a CCP, guarantees settlement; for US equities the CCP is **NSCC** (a DTCC subsidiary), which nets trades.[^5]
6. **Settlement (T+1, as of 2026)** — securities to the buyer, cash to the seller, **the next business day** since the **May 28, 2024** move from T+2.[^6]

## Order types
<a id="order-types"></a>

| Order type | Definition | Key risk |
| --- | --- | --- |
| **Market order** | Buy/sell **immediately**; guarantees execution but **not price**.[^7][^8] | **Price uncertainty / slippage** — "you might not get the price you saw," especially in fast markets; large orders can fill in pieces at different prices.[^8][^4] |
| **Limit order** | Buy/sell at a **specified price or better**.[^8][^7] | **Fill uncertainty** — may **not execute at all** if the market never reaches the limit.[^8] |
| **Stop (stop-loss) order** | Becomes a **market order** once the **stop price** is reached.[^8][^7] | **Price uncertainty once triggered** — in volatile markets may fill far from the stop price (inherits market-order risk).[^9][^8] |
| **Stop-limit order** | Once the stop is reached, triggers a **limit** order (not a market order).[^8][^9] | **Fill uncertainty** — like any limit, may not fill if price gaps past the limit.[^9][^8] |

## PFOF and best execution
<a id="pfof-and-best-execution"></a>

- **What PFOF is.** Per the SEC, payment for order flow is "compensation a broker may receive for directing its customers' orders to a particular broker-dealer or trading venue" — most commonly **retail brokers receiving cash from wholesale market makers** for their order flow, typically a fraction of a cent per share.[^10] Rule 10b-10 requires disclosure that PFOF was received.[^10]
- **Best-execution duty.** Brokers "have a duty to seek the best execution that is reasonably available," evaluating orders in aggregate and periodically assessing competing venues.[^1][^11] The SEC's longstanding position: routing partly based on PFOF is **not in itself a violation** — but PFOF **may not interfere** with best execution.[^10][^11]
- **The controversy.** PFOF creates a **potential conflict of interest** (route to the payer vs the best price).[^10] In 2020 the SEC charged **Robinhood** with misleading customers and failing best execution; it paid **$65 million** to settle.[^12]
- **Regulatory status (as of 2026 — flagged volatile).** In Dec 2022 the SEC proposed reforms (the Order Competition Rule, a codified Best-Execution standard, Rule 605 amendments). **In June 2025 the SEC formally withdrew the Order Competition Rule and the best-execution proposal**, stating it did not intend to issue final rules.[^13] **So as of 2026: PFOF remains legal and widely used; it was NOT banned; the marquee reform proposals were withdrawn.**[^13] *(A recent policy reversal — verify on SEC.gov before relying on it.)*
- **Does PFOF cost retail? (negation finding — contested.)** Critics: investors could be disadvantaged if a broker picks the higher-paying wholesaler.[^10][^12] Mitigating view: payments are tiny per share, PFOF is credited with enabling **$0 commissions**, and some studies found retail orders received better price improvement than institutions on small lots.[^14] Genuinely two-sided; presented as such.

## The NBBO
<a id="the-nbbo"></a>

The **National Best Bid and Offer** is the highest displayed **bid** and lowest displayed **offer** for a security **across all venues** at a moment — the best available national prices, calculated by the **Securities Information Processor (SIP)** and central to **Regulation NMS**.[^15] Under Reg NMS's **Order Protection Rule (Rule 611)** — in force as of 2026, though the SEC has floated narrowing it for tokenized equities — trading centers must avoid executing at prices inferior to a protected (NBBO) quote displayed elsewhere; the NBBO is therefore the **benchmark brokers consider for best execution**.[^15][^11] *Definitional limits:* the NBBO is built only from **displayed, round-lot** quotes in penny increments — excluding odd lots and non-displayed orders, while wholesalers can transact sub-penny. *(Sub-penny price improvement and SIP-vs-direct-feed latency → microstructure spoke.)*

## Bid, ask, spread, and fill
<a id="bid-ask-spread-and-fill"></a>

- **Bid** = highest price a buyer will pay; **ask/offer** = lowest a seller will accept (almost always higher than the bid); **spread** = the difference, which a market maker earns.[^16]
- **Quoted vs fill price.** The price quoted when you place an order "may not exactly match the price you pay" — quotes can be delayed, trades take time, and in volatile markets millions of shares trade in microseconds causing swings.[^4] A market buy hits the ask, a market sell hits the bid, but the last-traded price is not guaranteed to be your fill; large orders fill in pieces at multiple prices. This gap is **slippage**.[^4][^8]

## The $0-commission landscape

Major US online brokers eliminated commissions on online stock/ETF trades in an October 2019 pricing war (Schwab → $0 on Oct 1, 2019; TD Ameritrade same day; E*TRADE next day; Fidelity Oct 10, 2019).[^17] **As of 2026, $0 commissions on stocks and ETFs are the standard** across most major online brokers; revenue shifted to **PFOF, securities lending, interest on idle cash, margin lending, and fees**.[^18] Note **not all brokers use PFOF** (e.g., Fidelity does not on stock orders).[^18] (Broker roster illustrative, not exhaustive.)

## References

Tier-1 = US regulator/SRO/clearing utility; tier-2 = established secondary/contemporaneous reporting; tier-3 = reputable financial explainer. Volatile claims dated *as of 2026*.

[^1]: SEC — Trade Execution: What Every Investor Should Know (routing, best execution, venues). https://www.sec.gov/about/reports-publications/investorpubstradexec (tier-1, regulator)
[^2]: SEC — Disclosure of Order Execution and Routing Practices. https://www.sec.gov/rules-regulations/2001/03/disclosure-order-execution-routing-practices (tier-1, regulator)
[^3]: FINRA — Where Do Stocks Trade? (exchanges, wholesalers, internalization, ATS/dark pools, ECNs). https://www.finra.org/investors/insights/where-do-stocks-trade (tier-1, SRO)
[^4]: SEC / Investor.gov — Executing an Order / quoted-vs-fill, slippage. https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/executing-order (tier-1, regulator)
[^5]: DTCC — Understanding Settlement / NSCC (clearing, CNS netting). https://www.dtcc.com/understanding-settlement/index.html (tier-1, clearing utility)
[^6]: SEC / Investor.gov — New "T+1" Settlement Cycle Investor Bulletin (effective May 28, 2024). https://www.investor.gov/ (tier-1, regulator)
[^7]: SEC / Investor.gov — Types of Orders. https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders (tier-1, regulator)
[^8]: FINRA — Order Types (market/limit/stop definitions and risks). https://www.finra.org/investors/investing/investment-products/stocks/order-types (tier-1, SRO)
[^9]: SEC — Investor Bulletin: Stop, Stop-Limit, and Trailing Stop Orders. https://www.sec.gov/oiea/investor-alerts-bulletins/ib-stoporders (tier-1, regulator)
[^10]: SEC — Payment for Order Flow Q&A (definition, Rule 10b-10, best-execution stance). https://www.sec.gov/answers/payordf.htm (tier-1, regulator)
[^11]: FINRA — Best Execution (2022 exam & risk-monitoring report). https://www.finra.org/rules-guidance/guidance/reports/2022-finras-examination-and-risk-monitoring-program/best-execution (tier-1, SRO)
[^12]: SEC — Press Release 2020-321: SEC Charges Robinhood ($65M). https://www.sec.gov/newsroom/press-releases/2020-321 (tier-1, regulator)
[^13]: SEC — Order Competition Rule withdrawal (June 2025). https://www.sec.gov/rules-regulations/2025/06/order-competition-rule (tier-1, regulator) — verify current status; corroborated by Congressional Research Service IF12332.
[^14]: SmartAsset / Britannica Money — How PFOF works (cost-to-retail framing, price improvement). https://www.britannica.com/money/payment-for-order-flow-explained (tier-3, reputable explainer; negation/disconfirming)
[^15]: SEC — Final Rule: Regulation NMS (NBBO, SIP, Rule 611). https://www.sec.gov/files/rules/final/34-51808.pdf (tier-1, regulator)
[^16]: SEC / Investor.gov — Bid/Ask/Spread glossary. https://www.investor.gov/introduction-investing/investing-basics/glossary/ask-price (tier-1, regulator)
[^17]: CNBC / Kiplinger — Oct 2019 move to $0 commissions (contemporaneous record). https://www.cnbc.com/2019/10/02/the-end-of-commissions-for-stock-trading-is-near-as-td-ameritrade-cuts-to-zero-matching-schwab.html (tier-2)
[^18]: CNBC Select / NerdWallet / StockBrokers.com — commission-free trading as of 2026; how brokers make money; Fidelity no-PFOF. https://www.cnbc.com/select/best-brokerage-free-stock-trading/ (tier-3, reputable current)
