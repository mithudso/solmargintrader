<!-- Provenance: foundation reference under the `trading-and-investing` hub. Created 2026-06-16 via /dr deep-research. Educational only — NOT financial/investment advice. Volatile claims dated "as of 2026". -->

# Market Sessions & Venues (foundation)

Where things trade, when the market is open, how hours differ across asset classes, and the trading halts that protect markets. Overview depth for the hub.

> Educational information, not advice. Hours, sessions, and overnight-trading initiatives change fast — dated **as of 2026**; verify with the exchange/regulator.

## Contents

- [Major US venues — what trades where](#major-us-venues)
- [US equity sessions and hours](#us-equity-sessions)
- [Overnight / 24-hour equity trading (as of 2026)](#overnight-24-hour)
- [How other asset classes' hours differ](#other-asset-classes)
- [Market holidays](#market-holidays)
- [Circuit breakers and trading halts](#circuit-breakers)
- [International note](#international-note)
- [References](#references)

## Major US venues
<a id="major-us-venues"></a>

- **Equities (stocks/ETFs):** the two dominant US stock exchanges are the **NYSE** and **Nasdaq**.[^1][^2] Market-model difference: NYSE runs an **auction market** anchored by **Designated Market Makers** and keeps a physical floor (most volume electronic); Nasdaq is an all-electronic **dealer market** with competing market makers and no floor.[^3] Both serve the same regular hours. *(Real US equity trading is fragmented across many more venues — NYSE/Nasdaq are the primary listing exchanges; this is an overview, not a routing map.)*
- **Futures:** **CME Group** is the dominant US futures venue, via the **CME Globex** electronic platform (equity-index, rates, FX, energy, metals, agriculture futures + options on them).[^4]
- **Options:** **Cboe Global Markets** is the largest US options operator (options on thousands of stocks/ETPs; home of **SPX** index options and the **VIX** suite).[^5]
- **OTC / unlisted stocks:** securities not meeting listing standards trade **over-the-counter** via a dealer network; **OTC Markets Group** runs tiers of decreasing disclosure — **OTCQX** (highest), **OTCQB** (venture), **Pink** (no minimum requirements; can include distressed/non-reporting firms).[^6] OTC stocks carry elevated risk.[^6]

## US equity sessions
<a id="us-equity-sessions"></a>

- **Regular session:** NYSE and Nasdaq trade **9:30 a.m.–4:00 p.m. ET**, Monday–Friday, excluding holidays.[^7]
- **Pre-market & after-hours (extended hours):** brokers offer extended-hours trading electronically — a common **pre-market** ~**4:00–9:30 a.m. ET** and **after-hours** ~**4:00–8:00 p.m. ET**, though windows vary by broker.[^7] Extended hours have **thinner liquidity, wider spreads, more volatile/less-representative prices, possible non-execution/partial fills, and an informational disadvantage for retail** — explicitly warned by the SEC (negation finding).[^8]

## Overnight 24-hour
<a id="overnight-24-hour"></a>

**Overnight / near-24-hour equity trading (as of 2026 — rapidly evolving):**

- **Nasdaq:** on **April 10, 2026**, the SEC **approved** Nasdaq's expansion from 16 to **23 hours/day** — a Day Session (4:00 a.m.–8:00 p.m. ET) and a Night Session (9:00 p.m.–4:00 a.m. ET), with an 8:00–9:00 p.m. ET maintenance window; the Night Session would permit **limit orders only** with extra risk disclosures. Launch targeted **H2 2026**, pending readiness.[^9]
- **NYSE Arca** targets **Dec 6, 2026** for extended/overnight trading (~22–23-hour model).[^9]
- **24X National Exchange** received SEC approval (2024) for 23-hour capability, phasing in overnight in H2 2026.[^9]
- Brokers/ATSs already enable extended/overnight access today (e.g., Robinhood 24 Hour Market, Interactive Brokers, the Blue Ocean overnight ATS).[^9]
- Infrastructure: DTCC/NSCC has worked to support extended clearing hours around mid-2026.[^9]

*Contested (negation finding):* buy-side traders and firms (e.g., Citadel Securities) have flagged concerns; economists warn continuous hours can **dilute liquidity, weaken price discovery, widen spreads**, plus operational/settlement-mismatch and trader-burnout concerns. Retail appetite exceeds institutional comfort.[^10]

## Other asset classes
<a id="other-asset-classes"></a>

- **Forex:** ~**24 hours, 5 days/week** — opens **Sunday ~5:00 p.m. ET**, closes **Friday ~5:00 p.m. ET** — decentralized across **Sydney, Tokyo, London, New York** sessions, with London/New York carrying the most volume and the overlaps busiest.[^11]
- **Crypto:** **24/7/365**, including weekends/holidays, because it runs on distributed networks rather than a centralized exchange; only occasional scheduled maintenance interrupts it.[^11] *2026 development:* **CME launched 24/7 crypto futures and options on May 29, 2026**, narrowing the gap to always-on spot.[^4]
- **Futures:** **nearly 24 hours on weekdays** via CME Globex (Sunday 5:00 p.m. CT to Friday 4:00 p.m. CT) with a daily ~1-hour maintenance break (4:00–5:00 p.m. CT); specific contracts vary.[^4]

## Market holidays

US equity markets (NYSE/Nasdaq) **close fully on ~9–10 holidays/year** (New Year's Day, MLK Day, Washington's Birthday, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas) and observe a few **early closes (1:00 p.m. ET)**, typically the day after Thanksgiving and Christmas Eve.[^7] Exhaustive dated lists are published yearly by exchanges/brokers (omitted here by scope).

## Circuit breakers
<a id="circuit-breakers"></a>

- **Market-wide circuit breakers (MWCB):** a cross-market halt on intraday declines in the **S&P 500**, recalculated daily from the prior close:[^12]
  - **Level 1 = 7%** → 15-min halt if before 3:25 p.m. ET; none at/after 3:25 p.m.
  - **Level 2 = 13%** → 15-min halt if before 3:25 p.m. ET; none at/after 3:25 p.m.
  - **Level 3 = 20%** → halt for the **rest of the trading day**, any time.
  - Last notably triggered during the **March 2020** COVID sell-off (four Level-1 halts that month).[^12]
- **Single-stock Limit Up-Limit Down (LULD):** adopted after the **2010 Flash Crash** (SEC-approved 2012, phased in from 2013); constrains an individual stock's trades to bands a percentage above/below a **rolling 5-minute average**; hitting a band triggers a **15-second Limit State** and, if unresolved, a **5-minute pause** (extendable); band width varies by tier and time of day.[^13]

*Negation finding:* the academic **"magnet effect"** critique holds that an approaching limit can *induce* traders to rush, accelerating the move toward the threshold; evidence on breaker effectiveness remains mixed.[^14]

## International note

Other major markets run their own hours/sessions in local time, e.g.: **LSE** ~08:00–16:30; **Euronext** ~09:00–17:30 CET; **Tokyo (TSE)** 09:00–11:30 & 12:30–15:00 JST; **Hong Kong (HKEX)** 09:30–16:00 HKT; **Shanghai (SSE)** 09:30–11:30 & 13:00–15:00 local. A distinguishing feature of major Asian exchanges is a **midday lunch break**, which European and US exchanges lack.[^15] Verify exact times against each exchange.

## References

Tier-1 = regulator/exchange/peer-reviewed; tier-2 = industry/professional analysis; tier-3 = broker educational. Volatile claims dated *as of 2026*.

[^1]: Fidelity — Stock market hours (NYSE/Nasdaq regular session). https://www.fidelity.com/learning-center/smart-money/stock-market-hours (tier-1/2, major broker)
[^2]: Charles Schwab — Extended-hours trading. https://www.schwab.com/stocks/extended-hours-trading (tier-1/2, major broker)
[^3]: Carpenter Wellington / Lexology — NYSE vs Nasdaq market models. https://carpenterwellington.com/post/nyse-nasdaq-key-similarities-differences/ (tier-2)
[^4]: CME Group — Trading hours + "CME Group to Launch 24/7 Crypto Futures and Options on May 29" press release. https://www.cmegroup.com/trading-hours.html (tier-1, exchange) — May 29, 2026 launch as of 2026
[^5]: Cboe — Tradable products / US Options / VIX. https://www.cboe.com/tradable_products/ (tier-1, exchange)
[^6]: SoFi / FINRA SIE material — OTC Markets & tiers (OTCQX/OTCQB/Pink). https://www.sofi.com/learn/content/otc-stocks-explained/ (tier-2/educational)
[^7]: Fidelity / NYSE — stock-market hours, extended-hours windows, holidays. https://www.fidelity.com/learning-center/smart-money/stock-market-holidays (tier-1/2)
[^8]: SEC — After-Hours Trading: Understanding the Risks. https://www.sec.gov/about/reports-publications/investorpubsafterhourshtm (tier-1, regulator; negation/disconfirming)
[^9]: Arnold & Porter advisory + SIFMA + NYSE Extended-Hours FAQ — SEC approves Nasdaq 23-hour trading (Apr 10, 2026); NYSE Arca/24X timelines. https://www.arnoldporter.com/en/perspectives/advisories/2026/04/sec-approves-nasdaq-proposal-to-expand-trading-hours (tier-1/2, regulatory advisory) — dated as of 2026
[^10]: InvestmentNews / WEF / Kiplinger — buy-side concerns over 24-hour equity trading. (tier-1/2; negation/disconfirming)
[^11]: FOREX.com — Forex & cryptocurrency market hours; FXOpen — sessions/overlaps. https://www.forex.com/en/cryptocurrency-trading/cryptocurrency-market-hours/ (tier-2/3, broker educational)
[^12]: SEC / Investor.gov — Stock Market Circuit Breakers (7/13/20% thresholds, 3:25 p.m. rule). https://www.investor.gov/introduction-investing/investing-basics/glossary/stock-market-circuit-breakers (tier-1, regulator)
[^13]: Nasdaq Trader — LULD FAQ (bands, Limit State, 5-min pause). https://www.nasdaqtrader.com/content/MarketRegulation/LULD_FAQ.pdf (tier-1, SRO/exchange)
[^14]: "A survey on the magnet effect of circuit breakers" (Review of Economics & Finance, 2020); Oxford Review of Finance — "Circuit breakers and market runs." (tier-1, peer-reviewed; negation/disconfirming)
[^15]: EBC / CMC Markets — global market-hours guides (LSE/Euronext/TSE/HKEX/SSE; Asian lunch break). (tier-2/3) — verify exact times against each exchange
