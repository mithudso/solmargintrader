<!-- hub-reference-banner -->
> **Reference file — part of the `trading-and-investing` hub.** Formerly the standalone `options-trading-and-strategies` skill.
> Sibling topics in this family are now reference files under the hubs (`trading-and-investing`) — **not** standalone
> skills. Ignore any "use the X skill" / `related_skills` / SKIP pointers below that name a bare sibling
> skill; load that topic's `references/<name>.md` from the owning hub (see the hub's "Cross-hub map").

---

---
name: options-trading-and-strategies
version: "1.0.0"
updated: "2026-06-16"
category: custom
metadata:
  changelog:
    - "2026-06-16 created via /dr deep-research — SPOKE of the trading-and-investing hub family. 5 researched concepts (fundamentals, the Greeks, volatility & conceptual pricing, core strategies, practical/operational), 40+ independent sources (regulator/exchange-grade: SEC/Investor.gov, FINRA, OCC, OIC/optionseducation.org, Cboe, CME). Parent-linked to trading-and-investing root; SKIP edges to derivatives-futures-and-swaps, trading-risk-management, technical-analysis, trading-regulation-compliance-and-taxes."
description: >-
  SPOKE of trading-and-investing — listed equity/ETF & index OPTIONS for a US retail participant. Educational ONLY, NOT financial/investment/tax advice; a long option can lose 100% of its premium and short (naked) options carry large or unlimited risk (2026). TRIGGER: calls vs puts, strike/expiration/premium, the 100-share multiplier, intrinsic vs extrinsic value, moneyness (ITM/ATM/OTM), American vs European, exercise & assignment, the options chain, open interest vs volume, LEAPS/weeklies/0DTE; the Greeks (delta/gamma/theta/vega/rho); implied vs realized volatility, IV rank/percentile, vol smile/skew, VIX, conceptual Black-Scholes; strategies (long call/put, covered call, cash-secured put, protective put, vertical/credit/debit spreads, straddle/strangle, iron condor, butterfly, calendar/diagonal); defined- vs undefined-risk; assignment, pin & ex-dividend early-assignment risk; options approval levels & margin; bid/ask & liquidity. SKIP: futures/forwards/swaps → derivatives-futures-and-swaps; position sizing/stops/Kelly → trading-risk-management; charting/indicators/entry timing → technical-analysis; wash-sale/Section-1256/trader-tax detail → trading-regulation-compliance-and-taxes; long-term passive/retirement investing → investing-and-retirement.
tags:
  - options
  - options-trading
  - calls-and-puts
  - the-greeks
  - implied-volatility
  - options-strategies
  - covered-call
  - vertical-spread
  - iron-condor
  - assignment-risk
  - black-scholes
  - trading-and-investing
whenToUse:
  - "what is a call vs a put, and what does the buyer vs the seller (writer) get and owe"
  - "what do strike, expiration, premium, and the 100-share contract multiplier mean"
  - "what is intrinsic vs extrinsic (time) value and moneyness (ITM/ATM/OTM)"
  - "what is the difference between American and European exercise; how do exercise and assignment work"
  - "what are open interest and volume, and what are LEAPS, weeklies, and 0DTE options"
  - "what do the Greeks (delta, gamma, theta, vega, rho) measure and how is my position exposed"
  - "what is implied volatility, IV rank vs percentile, the volatility smile/skew, and the VIX"
  - "explain Black-Scholes intuition and why it struggles with the skew and American options"
  - "how do covered calls, cash-secured puts, protective puts, spreads, straddles, iron condors, and butterflies work"
  - "what is defined-risk vs undefined-risk, and which short strategies can lose a lot or be unlimited"
  - "what is pin risk and why might a short ITM call be assigned early around an ex-dividend date"
  - "what options approval level or margin do I need, and how do options bid/ask spreads and liquidity work"
keywords:
  - options
  - call option
  - put option
  - strike price
  - expiration
  - premium
  - option moneyness
  - in the money
  - intrinsic value
  - extrinsic value
  - options chain
  - open interest
  - LEAPS
  - weeklies
  - 0DTE
  - the Greeks
  - delta
  - gamma
  - theta
  - vega
  - rho
  - implied volatility
  - IV rank
  - IV percentile
  - volatility skew
  - volatility smile
  - VIX
  - Black-Scholes
  - put-call parity
  - covered call
  - cash-secured put
  - protective put
  - vertical spread
  - credit spread
  - debit spread
  - straddle
  - strangle
  - iron condor
  - butterfly spread
  - calendar spread
  - diagonal spread
  - defined risk
  - naked option
  - assignment
  - pin risk
  - early assignment
  - ex-dividend
  - options approval levels
  - options margin
  - bid ask spread
triggers:
  - "options"
  - "call option"
  - "put option"
  - "strike price"
  - "option premium"
  - "moneyness"
  - "in the money"
  - "intrinsic value"
  - "options chain"
  - "open interest"
  - "LEAPS"
  - "weeklies"
  - "0DTE"
  - "the greeks"
  - "delta"
  - "gamma"
  - "theta"
  - "vega"
  - "implied volatility"
  - "IV rank"
  - "volatility skew"
  - "VIX"
  - "black-scholes"
  - "put-call parity"
  - "covered call"
  - "cash-secured put"
  - "protective put"
  - "vertical spread"
  - "credit spread"
  - "iron condor"
  - "butterfly spread"
  - "calendar spread"
  - "straddle"
  - "strangle"
  - "naked option"
  - "assignment"
  - "pin risk"
  - "early assignment"
  - "ex-dividend"
  - "options approval level"
whenNotToUse: "Non-options derivatives — futures, forwards, swaps (incl. commodity/rate/FX/credit) → derivatives-futures-and-swaps. Position sizing, stop placement, risk-per-trade, R-multiples, Kelly, portfolio heat, margin/leverage as a DISCIPLINE → trading-risk-management. Chart patterns, candlesticks, indicators (RSI/MACD/moving averages), support/resistance, entry/exit TIMING → technical-analysis. Wash-sale mechanics, Section 1256 60/40 detail, trader-tax status, capital-gains reporting → trading-regulation-compliance-and-taxes. Long-term passive/retirement investing (index buy-and-hold, 401k/IRA/Roth) → investing-and-retirement. Market structure, order routing, sessions, what a clearinghouse is at foundation depth → the trading-and-investing hub and its references."
related_skills:
  - trading-and-investing
  - derivatives-futures-and-swaps
  - trading-risk-management
  - technical-analysis
  - trading-regulation-compliance-and-taxes
---

# Options Trading & Strategies (spoke)

A spoke of the **`trading-and-investing`** hub. It covers **listed options** — the contracts, the risk sensitivities (the Greeks), volatility and conceptual pricing, the core single- and multi-leg strategies, and the practical/operational realities — for a **US retail participant**.

> **Educational information only — NOT financial, investment, or tax advice, and NOT a recommendation to buy, sell, or hold any option or security.** Options are leveraged and can expire worthless: **the buyer of an option can lose 100% of the premium paid**, and **a seller (writer) of an uncovered/naked option can face large or theoretically unlimited losses**. Options are not suitable for every investor; before trading, a broker requires you to receive the OCC disclosure document *Characteristics and Risks of Standardized Options*.[^occ-odd] Rules, products, broker policies, and tax treatment change — every volatile claim here is stamped **as of 2026**; verify current facts with the primary source (OCC, OIC/optionseducation.org, Cboe, FINRA, SEC) before acting.

## Scope & where this sits in the family

This spoke owns **options** end-to-end. It assumes the hub's foundation (asset classes, market participants, the order lifecycle, clearing/settlement, the brokerage account). Read the hub first if you need that base. Route OUT to siblings for the adjacent topics:

| If the question is about… | Go to |
| --- | --- |
| Futures, forwards, or swaps (non-options derivatives), incl. commodity/rate/FX/credit | **`derivatives-futures-and-swaps`** |
| Position sizing, stop placement, risk-per-trade, R-multiples, Kelly, portfolio heat, leverage as a discipline | **`trading-risk-management`** |
| Chart patterns, candlesticks, indicators (RSI/MACD), support/resistance, **when** to enter/exit | **`technical-analysis`** |
| Wash-sale mechanics, Section 1256 60/40 detail, trader-tax status, capital-gains reporting | **`trading-regulation-compliance-and-taxes`** |
| Long-term passive / retirement investing (index buy-and-hold, 401(k)/IRA/Roth) | **`investing-and-retirement`** (consumer-finance family) |

The **Greeks** quantify how an option's value reacts to the underlying, time, volatility, and rates; **volatility** is the single input traders most disagree on and the one that pricing models can't observe directly; **strategy** is how you assemble legs into a defined- or undefined-risk position that expresses a view. Those three plus the **practical** layer are the four *planned* sub-references below — none of which are built yet.

## The one-paragraph foundation (if you only read this page)

A **call** gives its **buyer** the *right, not the obligation,* to **buy** 100 shares of the underlying at the **strike** price by **expiration**; a **put** gives the right to **sell**. The buyer pays a **premium** (the most a long can lose); the **seller/writer** receives the premium and takes on the **obligation** to deliver (short call) or take delivery of (short put) shares if **assigned**. One standard US equity/ETF contract controls **100 shares**, is **American-style** (exercisable any time before expiry), and **settles in shares**; most broad-based **index** options (e.g., SPX) are **European-style** and **cash-settled**.[^occ-spec][^oic-exercise][^cboe-eu] Premium = **intrinsic value** (how far in-the-money) + **extrinsic/time value** (what you pay for time and implied volatility). The **Greeks** measure the position's exposure — **delta** (direction), **gamma** (how fast delta moves), **theta** (time decay), **vega** (implied-volatility sensitivity), **rho** (rates). Whether an option is "cheap" or "rich" is largely a question of **implied volatility**. You combine legs into **strategies** that are either **defined-risk** (loss capped at entry — long options, spreads, iron condors) or **undefined-risk** (a naked short call is theoretically *unlimited*; a naked short put can lose down to a zero stock price). Clearing and the guarantee of every contract run through the **OCC**. **Nothing here is advice, and options can expire worthless.**

## Sub-references (ALL FOUR BUILT)

> **Read this before routing.** All four sub-references now exist in `references/`. `Read` the one
> that owns the question rather than answering from this page — this page is the map, they are the
> territory. Answer from this page only for orientation, or when a question genuinely spans all
> four.

| Sub-reference | Build state | Covers |
| --- | --- | --- |
| `references/options-fundamentals.md` | **Built** | Calls vs puts; long/short and the buyer/writer obligation; strike, expiration, premium, the 100-share multiplier and adjusted contracts; intrinsic vs extrinsic value; moneyness (ITM/ATM/OTM); American vs European; the OCC, exercise & assignment, random assignment, exercise-by-exception (the $0.01 ITM auto-exercise); the options chain; open interest vs volume; LEAPS, weeklies, 0DTE (with the as-of-2026 growth figures); share vs cash settlement. |
| `references/the-greeks.md` | **Built** | Delta (direction, hedge ratio, the "approximate probability of finishing ITM" caveat), gamma (convexity, short-gamma risk), theta (non-linear time decay), vega (IV sensitivity), rho (rates, LEAPS); the long-vs-short sign conventions; position/portfolio Greeks; second-order Greeks (vanna/charm/vomma) at naming depth; the long-premium-vs-short-premium tradeoff ("pennies in front of a steamroller"). |
| `references/volatility-and-pricing.md` | **Built** | Implied vs historical/realized volatility and the IV–HV gap; IV rank vs IV percentile (and how they diverge); the volatility smile and equity skew (and that the skew appeared after the 1987 crash); term structure & the volatility surface; the IV-crush / "right on direction, still lost" lesson; the VIX; **conceptual** Black-Scholes-Merton (the six inputs, the assumptions, the well-known failures), binomial/lattice models for American exercise, and put-call parity — all as intuition, not derivations. |
| `references/strategies-and-risk.md` | **Built** | Each core strategy with construction / outlook / max profit / max loss / breakeven / defined-or-undefined risk: long call & put; covered call; cash-secured put; protective put; collar; the four vertical spreads (bull/bear × debit/credit); straddle & strangle (long and the undefined-risk short); iron condor; iron butterfly; long butterfly; calendar & diagonal. The defined- vs undefined-risk organizing principle; assignment, **pin risk**, and **early assignment around ex-dividend**; options approval levels & margin; bid/ask spreads, liquidity, and the multi-leg net debit/credit order; a brief tax **pointer** (detail → `trading-regulation-compliance-and-taxes`). |

## How to answer from this spoke (output contract)

1. For any advice-seeking question, **lead with the educational-only / not-advice framing** and the core risk: a long option can lose 100% of premium; a naked short can lose large/unlimited amounts.
2. **Distinguish defined- from undefined-risk** whenever a strategy is discussed — it is the single most decision-relevant property, and "income" strategies (covered calls, short puts) are routinely mis-sold as "safe".
3. **Cite the authority** (OCC/OIC, Cboe, FINRA, SEC) for load-bearing facts; **stamp volatile facts as of 2026** with a "verify current" pointer — especially 0DTE growth, the PDT-rule replacement, and broker-specific approval-tier names/margin.
4. **Route DOWN before answering.** Contract mechanics → `options-fundamentals`; sensitivities →
   `the-greeks`; IV, skew, VIX or pricing → `volatility-and-pricing`; any named strategy, max
   loss/breakeven, or assignment/pin risk → `strategies-and-risk`. Route OUT to a sibling spoke when
   the question is really about futures/swaps (`derivatives-futures-and-swaps` — now built), position
   sizing, charting, or tax mechanics — name the destination.
5. Keep **US-centric**; flag where a fact (OCC, Section 1256, the PDT change, American-style settlement) is US-specific and would differ abroad.

## Cross-cutting notes & seams

- **Risk-management seam.** This spoke explains what each strategy's max loss *is* and the defined/undefined distinction. **How much to risk** — position sizing, stops, R-multiples, Kelly, portfolio heat, managing margin as a discipline — is **`trading-risk-management`**.
- **Tax seam (pointer only).** Options have specific US tax treatment — short- vs long-term gains, the wash-sale rule can apply, **Section 1256 60/40** treatment applies to broad-based **index** options but **not** equity/ETF options, and exercise/assignment adjusts the stock's cost basis. Detail lives in **`trading-regulation-compliance-and-taxes`**; this spoke states only the pointer.[^tax-1256]
- **Derivatives seam.** Options are one kind of derivative. Futures, forwards, and swaps — including
  options *on* futures' underlyings and the broader derivatives landscape — are
  **`derivatives-futures-and-swaps`** (`references/derivatives-futures-and-swaps.md`, built). That
  spoke also owns the **crypto perpetual**, which the classical four-primitive taxonomy has no slot
  for, and the futures-margin-is-not-a-loan distinction that catches everyone arriving from equities.
- **PDT / day-trading seam (volatile, as of 2026).** Frequent intraday options trading historically triggered the **Pattern Day Trader** rule ($25k minimum). FINRA **replaced** the PDT framework with a risk-based **intraday-margin** approach **effective June 4, 2026** (transition through Oct 20, 2027); pre-2026 "$25k to day-trade" guidance is outdated — verify your broker's current policy. Treated at pointer depth here; depth → the hub's `trading-risks-and-protections` reference and `trading-risk-management`.[^pdt]
- **Pricing-math seam.** Black-Scholes and put-call parity are presented as **intuition** here (the inputs, assumptions, failures), never as a derivation. The quantitative/stochastic-calculus treatment is out of scope for a retail educational spoke.

## References (sources)

Each reference file carries its own cited `## References` section anchored to primary authorities — **OCC / theocc.com, OIC / optionseducation.org, Cboe, CME Group, FINRA, SEC / Investor.gov**, plus corroborating brokerage education (Fidelity, Schwab, tastylive) and the standard derivatives literature where summarized. Volatile facts are dated *as of 2026* with verify-current pointers.

[^occ-odd]: Options Clearing Corporation, *Characteristics and Risks of Standardized Options* (the "Options Disclosure Document"), https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document — regulator/clearing (the mandatory pre-trade options risk disclosure). verified-as-of: 2026-06-16
[^occ-spec]: OCC, Equity Options Product Specifications (100-share contract unit; physical/share settlement; adjusted contracts), https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications — clearing/docs. verified-as-of: 2026-06-16
[^oic-exercise]: Options Industry Council (OIC), Options Exercise & Assignment FAQ (American vs European, OCC random assignment, exercise-by-exception / $0.01 ITM threshold), https://www.optionseducation.org/referencelibrary/faq/options-exercise — authoritative options education. verified-as-of: 2026-06-16
[^cboe-eu]: Cboe, Mini-SPX (XSP) / SPX European-style, cash-settled product pages, https://www.cboe.com/tradable_products/sp_500/mini_spx_options/european_style/ — exchange. verified-as-of: 2026-06-16
[^tax-1256]: Cboe, "Index Options Benefits & Tax Treatment" (Section 1256 60/40 applies to broad-based index options, not equity options), https://www.cboe.com/tradable_products/index-options-benefits-tax-treatment/ — exchange; corroborated by IRS Topic No. 427. Detail deferred to `trading-regulation-compliance-and-taxes`. verified-as-of: 2026-06-16
[^pdt]: FINRA, "Intraday Margin Requirements" Investor Insights (PDT designation/$25k minimum replaced by a risk-based intraday-margin framework, effective June 4, 2026; transition through Oct 20, 2027), https://www.finra.org/investors/insights/intraday-margin-requirements — regulator. verified-as-of: 2026-06-16
