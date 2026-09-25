---
name: fixed-income-and-bond-markets
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  Bonds in depth. The price-yield inverse and what a yield actually assumes;
  duration as the first-order rate sensitivity and convexity as the correction,
  with DV01; the yield curve, its shapes, and inversion as a recession signal
  with its documented lag; credit spreads, ratings and the investment-grade/high-
  yield boundary that drives forced selling; the instrument map (bills, notes,
  bonds, TIPS, corporates, munis with taxable-equivalent yield, MBS); NEGATIVE
  convexity in callables and mortgages and why it is the asymmetry that hurts;
  repo and SOFR as the plumbing; bond ETFs vs individual bonds and their
  divergence in stress; and the 2022 rate shock as duration risk realised.
  Educational only — NOT financial advice.
keywords:
  - bond
  - fixed income
  - yield to maturity
  - price yield inverse
  - duration
  - modified duration
  - Macaulay duration
  - convexity
  - negative convexity
  - DV01
  - yield curve
  - inverted yield curve
  - term premium
  - credit spread
  - investment grade
  - high yield
  - Treasury
  - TIPS
  - municipal bond
  - taxable-equivalent yield
  - MBS
  - prepayment risk
  - callable bond
  - repo
  - SOFR
  - TRACE
  - bond ETF
---

# Fixed Income & Bond Markets (spoke)

A spoke of the **`trading-and-investing`** hub, which covers bonds at asset-class depth in `asset-classes-and-instruments`. This page owns the mechanics: how a bond is priced, how it responds to rates and credit, and where the asymmetries are.

> **Educational information only — NOT financial, investment or tax advice.** Bonds are not "safe". **2022 was among the worst years on record for high-grade bonds**, and long-duration Treasuries — the instrument most often described as risk-free — fell further than many equity indices. "Risk-free" in the academic sense means *free of default risk if held to maturity*, not free of price risk, and confusing the two is the most expensive error in this asset class. Municipal tax treatment is fact-specific. Yields, curve shapes and spread levels move constantly; every figure is stamped **as of 2026** and must be verified with the primary source (TreasuryDirect, the Federal Reserve, FINRA, MSRB).

## Contents

1. What a bond is, and the price-yield inverse
2. Yield measures, and what YTM assumes
3. Duration — the first-order sensitivity
4. Convexity — the correction, and DV01
5. Negative convexity: callables and mortgages
6. The yield curve, and inversion as a signal
7. Credit: spreads, ratings, and the IG/HY boundary
8. The instrument map
9. Repo, SOFR, and the plumbing
10. Individual bonds vs bond ETFs
11. 2022 — duration risk realised
12. Anti-patterns

## 1. What a bond is, and the price-yield inverse

A bond is a **loan you can trade**: the issuer owes periodic **coupons** and the **par** (face) value at **maturity**.

**Price and yield move in opposite directions, and this follows from arithmetic, not sentiment.** A bond's coupon is fixed in dollars. If market rates rise, a newly issued bond pays more, so the existing bond's fixed coupon is worth less — its price must fall until its *yield* matches. Formally, price is the present value of the cash flows, and yield is in the denominator:

```
P = Σ [ C / (1+y)^t ] + [ Par / (1+y)^n ]
```

- Price **above** par → **premium** → coupon exceeds market yield.
- Price **below** par → **discount** → coupon is below market yield.

**The consequence people find counter-intuitive:** you can lose substantial money on a Treasury without any default. The issuer will pay every coupon and return par — but if you must sell before maturity, you sell at the market's price, not yours. §11 is what that looks like at scale.

## 2. Yield measures, and what YTM assumes

- **Current yield** = annual coupon ÷ price. Ignores maturity and any capital gain or loss. Nearly useless alone.
- **Yield to maturity (YTM)** — the discount rate that equates the present value of all cash flows to the current price. The standard quote.
- **Yield to call / yield to worst** — YTM computed to each call date; **yield to worst** is the lowest. For a callable bond this is the number to look at (§5).
- **After-tax yield** — the only one that is comparable across a Treasury, a corporate and a muni (§8).

**Two assumptions inside YTM that make it a projection rather than a measurement:**

1. **You hold to maturity.** Sell early and your realised return depends on the price then.
2. **Every coupon is reinvested at the YTM itself.** This is **reinvestment risk**, and it rarely holds. A zero-coupon bond is the only case with no reinvestment assumption — which is why zeros are the clean instrument for locking a horizon return.

## 3. Duration — the first-order sensitivity

**Duration** answers: if yields move 1%, how much does the price move?

- **Macaulay duration** — the weighted-average time to receipt of the cash flows, in years.
- **Modified duration** — the practical one: **approximate percentage price change per 1 percentage point change in yield.**

```
ΔP/P ≈ − modified duration × Δy
```

A bond with modified duration 8 loses roughly **8%** if yields rise 1%. A 20-year Treasury can have duration near 17 — a 1% yield rise is then a ~17% loss.

**What raises duration:** longer maturity, lower coupon, lower yield. A zero-coupon bond's Macaulay duration equals its maturity — the maximum for that horizon.

**Duration is a linear approximation of a curved relationship**, and its error grows with the size of the yield move. That error is convexity.

## 4. Convexity — the correction, and DV01

**Convexity** is the second-order term — the curvature of the price-yield relationship:

```
ΔP/P ≈ − D_mod × Δy + ½ × convexity × (Δy)²
```

For an ordinary non-callable bond, convexity is **positive**, and positive convexity is **in the holder's favour**: prices rise more when yields fall than they fall when yields rise by the same amount. Duration alone therefore *understates* gains and *overstates* losses for a straight bond — a helpful bias.

**DV01** (dollar value of 01), or PV01, is the dollar price change per **one basis point** of yield movement. It is what a desk actually hedges with, because it is additive across a portfolio in dollars where duration is not.

**Duration and convexity are exactly the delta and gamma of a bond.** If `the-greeks` §2–§3 makes sense, this section is the same mathematics on a different instrument: a first derivative, a second derivative, and the warning that the first one alone fails on large moves.

## 5. Negative convexity: callables and mortgages

Some bonds have **negative** convexity — the asymmetry runs against the holder. This is the most important idea on the page and the one most often skipped.

**Callable bonds.** The issuer may redeem early, and will do so when rates fall — refinancing cheaply, exactly as a homeowner would. So:

- Rates **rise** → you take the full price loss.
- Rates **fall** → your upside is capped near the call price, because the bond is called away.

You have effectively **sold a call option on interest rates** to the issuer. Use **yield to worst**, not YTM.

**Mortgage-backed securities.** Homeowners **prepay** when rates fall (refinancing) and stop prepaying when rates rise. The result is the worst of both:

- Rates fall → **contraction risk**: principal returns early and must be reinvested at the new, lower rates.
- Rates rise → **extension risk**: prepayments stop, duration *lengthens*, and you are locked into a below-market coupon for longer.

**MBS duration extends precisely when you least want it to.** This is negative convexity in its purest form, and it is why MBS carry a yield premium over Treasuries that is not purely credit.

## 6. The yield curve, and inversion as a signal

The **yield curve** plots yield against maturity for one issuer, usually Treasuries.

- **Normal (upward-sloping)** — longer maturities yield more, compensating for time and uncertainty (**term premium**).
- **Flat** — little compensation for extending.
- **Inverted** — short yields exceed long. Historically associated with the market expecting rate cuts, i.e. expecting weakness.

**On inversion as a recession predictor, stated with its caveats.** The **10-year minus 3-month** spread has preceded every US recession in the modern record, which is a genuinely strong track record for a single indicator.[^fed-curve] But three qualifications matter more than the headline:

1. **The lag is long and variable** — historically many months to over two years. "Inverted" is not a timing signal.
2. **The sample is small.** A handful of recessions is not a large-N result, however clean it looks.
3. **It is not tradeable on its own.** By the time inversion is widely discussed it is in the price, and the interval between signal and event has historically included substantial equity gains.

## 7. Credit: spreads, ratings, and the IG/HY boundary

**Credit spread** = a bond's yield minus the yield of a comparable-maturity Treasury. It is the market's price for default risk plus a liquidity premium.

**Ratings** (Moody's / S&P / Fitch) split the market at one line:

- **Investment grade** — down to **Baa3 / BBB−**.
- **High yield ("junk")** — **Ba1 / BB+** and below.

**Why the boundary is a market-structure fact, not just a label.** Many institutional mandates prohibit holding below investment grade. A downgrade across the line therefore forces selling by holders who have no view on the credit — a **"fallen angel"** event where price falls because of a rule rather than a reassessment. That reflexivity makes the boundary the single most consequential rating distinction, and it is why BBB− credits trade with more spread volatility than their default probability alone implies.

**Spreads widen in stress and correlate with equities.** High-yield is not a diversifier against equity risk in a crisis; it is closer to a leveraged equity position with a bond's upside cap.

## 8. The instrument map

| Instrument | Issuer | Notes |
| --- | --- | --- |
| **T-bills** | US Treasury | ≤1 year, sold at a discount, no coupon |
| **T-notes** | US Treasury | 2–10 years, semi-annual coupons |
| **T-bonds** | US Treasury | 20–30 years — the longest duration, the largest rate risk |
| **TIPS** | US Treasury | principal indexed to CPI; the yield is **real**, so nominal-vs-real is the comparison |
| **Agency / MBS** | GSEs | negative convexity (§5) |
| **Corporates** | companies | credit spread (§7); fully taxable |
| **Munis** | states / localities | interest generally **exempt from federal** income tax, sometimes state |

**Munis and the taxable-equivalent yield.** A tax-exempt yield is not comparable to a taxable one until converted:

```
taxable-equivalent yield = tax-exempt yield / (1 − marginal tax rate)
```

A 3.5% muni at a 35% marginal rate ≈ **5.38%** taxable-equivalent. **Munis are therefore a function of your tax bracket** — attractive at a high marginal rate, often not at a low one, and generally pointless inside a tax-advantaged account. Detail → `trading-regulation-compliance-and-taxes` and `personal-income-taxes`.

**Transparency note:** corporate and muni bonds trade OTC with far less pre-trade transparency than equities. **TRACE** (FINRA) publishes corporate trade reports and **EMMA** (MSRB) publishes muni data — use them, because a dealer quote is not a market.[^finra-trace]

## 9. Repo, SOFR, and the plumbing

A **repurchase agreement (repo)** is a collateralised loan: sell a security now, agree to buy it back shortly at a slightly higher price. Economically secured overnight borrowing, and the mechanism by which the whole fixed-income system funds itself.

**SOFR** — the Secured Overnight Financing Rate — is derived from Treasury repo transactions and replaced USD LIBOR as the primary reference rate; **USD LIBOR ceased for remaining tenors on 30 June 2023**.[^arrc] Any material describing LIBOR as a current benchmark is stale. Swaps referencing SOFR → `derivatives-futures-and-swaps` §9.

**Why a retail participant should care at all:** repo stress is an early and reliable indicator of funding stress, and it transmits. The September 2019 repo spike and the March 2020 "dash for cash" — when even Treasuries became hard to transact — both showed that the instrument assumed to be most liquid can gap when everyone needs cash simultaneously.

## 10. Individual bonds vs bond ETFs

| | Individual bond | Bond ETF |
| --- | --- | --- |
| Maturity | **has one** — hold to par | **none**; perpetually rolling |
| Rate risk | resolves at maturity if you hold | permanent |
| Diversification | one credit | many |
| Liquidity | OTC, wide spreads for retail | intraday, exchange-traded |
| Price in stress | marked, but par is contractual | can trade at a **discount to NAV** |

**The distinction that matters most:** an individual bond held to maturity returns par regardless of the intervening price. **A bond fund has no maturity**, so a rate shock is a permanent capital loss unless yields come back down. Investors who believed "bonds are safe if you hold on" and owned a *fund* discovered these are different statements in 2022.

**ETF discounts in stress are a feature of the wrapper, not a failure of it.** When the underlying bonds cannot be transacted, the ETF price becomes the better price discovery and NAV becomes stale — which looks like a broken ETF and is closer to the opposite.

## 11. 2022 — duration risk realised

Worth its own section because it is the clearest available demonstration that this asset class carries real risk.

Rates rose sharply from a near-zero base. Because **duration is highest when yields are lowest** (§3), the sensitivity was at a maximum precisely when the shock arrived. High-grade aggregate bond indices posted their worst calendar year in modern record-keeping, and long-duration Treasury exposure fell by more than many equity indices — with **no default and no credit event**.

Three lessons, each of which contradicts a common belief:

1. **"Risk-free" means default-free, not price-stable.** A 30-year Treasury is the most rate-sensitive instrument in the market.
2. **Bonds and equities can fall together.** The negative correlation is a regime, not a law — see `sleeve-weighting-and-objective-selection` on how badly correlation-dependent allocation behaves when the input moves.
3. **The starting yield does the work.** Low yields mean a thin coupon cushion and maximum duration at once.

## 12. Anti-patterns

1. **Calling Treasuries "safe" without distinguishing default risk from price risk** (§1, §11).
2. **Using YTM on a callable bond.** Use yield to worst (§2, §5).
3. **Using duration alone on a large yield move.** It is a linear approximation; convexity is the correction (§4).
4. **Assuming all convexity is positive.** Callables and MBS are negatively convex — capped upside, extending duration into a selloff (§5).
5. **Treating inversion as a timing signal.** The lag has been months to years (§6).
6. **Holding high yield as an equity diversifier.** Spreads widen when equities fall (§7).
7. **Comparing a muni yield to a taxable yield directly.** Convert to taxable-equivalent (§8).
8. **Holding munis in a tax-advantaged account.** The exemption is already there (§8).
9. **Treating a bond fund like a bond.** A fund has no maturity, so the loss does not self-heal (§10).
10. **Reading an ETF discount to NAV as a broken ETF.** In stress the ETF is often the fresher price (§10).
11. **Quoting LIBOR as a current benchmark.** It ended 30 June 2023 (§9).
12. **Taking a dealer quote as the market.** Check TRACE or EMMA (§8).

## References (sources)

[^finra-bond]: FINRA — Bond Yield and Return; bond basics including the price-yield inverse, coupon, par, premium/discount and duration. https://www.finra.org/investors/insights/bond-yield-return — tier-1 (SRO). Supports §1–§3. verified-as-of: 2026-08-05
[^treasury]: TreasuryDirect — marketable securities: bills, notes, bonds, TIPS, and their auction and coupon conventions. https://www.treasurydirect.gov/marketable-securities/ — tier-1 (US Treasury). Supports §8. verified-as-of: 2026-08-05
[^fed-curve]: Federal Reserve Bank of New York — the yield-curve-as-recession-predictor research and the 10-year/3-month spread series; Federal Reserve H.15 for curve data. https://www.newyorkfed.org/research/capital_markets/ycfaq — tier-1 (Federal Reserve). Supports §6 **including its caveats**: the lag is long and variable and the recession sample is small. verified-as-of: 2026-08-05
[^finra-trace]: FINRA — TRACE corporate bond trade reporting; MSRB EMMA for municipal securities. https://www.finra.org/finra-data/fixed-income and https://emma.msrb.org/ — tier-1 (SRO / MSRB). Supports §8's transparency note. verified-as-of: 2026-08-05
[^arrc]: Federal Reserve Bank of New York / Alternative Reference Rates Committee — SOFR, and USD LIBOR cessation for remaining tenors on 30 June 2023. https://www.newyorkfed.org/arrc — tier-1 (Federal Reserve). Supports §9. verified-as-of: 2026-08-05
[^sec-bonds]: SEC / Investor.gov — bonds and fixed-income products, including interest-rate risk and the risks of bond funds. https://www.investor.gov/introduction-investing/investing-basics/investment-products/bonds-or-fixed-income-products-0 — tier-1 (regulator). Supports §10 and §11. **The 2022 drawdown magnitudes should be verified against index provider data before being quoted numerically; this page deliberately describes them qualitatively rather than asserting figures.** verified-as-of: 2026-08-05
