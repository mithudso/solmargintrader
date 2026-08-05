---
name: xrp-ripple
description: Trader-facing reference for XRP — XRPL mechanics, the 100B pre-mine and escrow release schedule, what Ripple actually holds, the SEC litigation record with dates, venue structure, and what its 1.37% turnover means for sizing and backtesting.
---

# XRP (XRP Ledger / Ripple)

> Educational reference. Not investment advice. Every figure below carries a date because
> all of them decay — prices and volumes within hours, escrow within a month, legal and
> listing status within weeks. **Re-pull anything you intend to act on.**

## Snapshot (AS OF 2026-08-04)

| Field | Value | Source / date |
|---|---|---|
| Price | $1.074 | CoinGecko, 2026-08-04 (user-supplied snapshot) and CoinGecko API 2026-08-05 03:03:18 UTC[^cg-xrp] |
| Market cap | ~$67.2B / $67,148,724,849 | CoinGecko, 2026-08-04 / API 2026-08-05[^cg-xrp] |
| Fully diluted valuation | $107,365,370,963 | CoinGecko API, 2026-08-05[^cg-xrp] |
| 24h volume | ~$0.92B / $927,366,523 | CoinGecko, 2026-08-04 / API 2026-08-05[^cg-xrp] |
| Headline turnover (24h vol ÷ mcap) | 1.37% / 1.381% | derived from the two rows above |
| Circulating supply (CoinGecko) | 62,533,271,955 XRP | CoinGecko API, 2026-08-05[^cg-xrp] |
| Total supply (on-ledger, primary) | **99,985,631,419.85 XRP** | XRP Ledger `ledger` RPC, ledger 106,078,752, closed 2026-08-05 03:01:50 UTC[^xrpl] |
| Max supply | 100,000,000,000 XRP (fixed at genesis; only decreases) | XRPL protocol; CoinGecko[^cg-xrp] |
| Escrowed (on-ledger, Ripple-labelled) | **35,000,000,000 XRP** | xrpscan rich-list API, retrieved 2026-08-05[^xrpscan] |
| All-time high | $3.65 on 2025-07-17 | CoinGecko API, 2026-08-05[^cg-xrp] |
| Drawdown from ATH | −70.6% | derived, 2026-08-05 |

**Figures decay.** Price and volume are one instant. Escrow steps down (and partially back up)
every month. The circulating-supply figure is a *tracker convention*, not a protocol fact —
see the reconciliation problem below. Legal status is settled as of the dates given but
policy around digital-asset classification is still moving. Treat this document as stale after
roughly one quarter.

---

## What it is, mechanically

XRP is the **native asset of the XRP Ledger (XRPL)**, a public blockchain that predates
Ethereum, launched in 2012 by the founders of what became Ripple Labs. Three mechanical facts
distinguish it from almost every other large-cap crypto asset:

**1. There is no mining and no issuance. Ever.** All **100,000,000,000 XRP were created at
genesis**. There is no block reward, no staking emission, and no way to mint more. The court
record describes the ledger and its fixed-token design directly[^torres].

**2. Supply only shrinks, by fee destruction.** Every XRPL transaction destroys a small
"transaction cost" — the fee is **burned, not paid to validators**. Verified live against the
ledger on 2026-08-05:

```
XRPL server_state, ledger 106,079,046, rippled 3.3.0-rc6
  base_fee      = 10 drops        = 0.00001 XRP per standard transaction
  reserve_base  = 1,000,000 drops = 1 XRP    (minimum account balance)
  reserve_inc   =   200,000 drops = 0.2 XRP  (per owned ledger object)
```

Cumulative destruction since 2012, derived from the live `total_coins` figure:
100,000,000,000 − 99,985,631,419.85 = **14,368,580 XRP burned in ~14 years** (0.0144% of
genesis supply). This is real but economically trivial — do **not** model XRP as deflationary
in any meaningful sense.

**3. Consensus is by a validator list, not by stake or work.** XRPL uses the XRP Ledger
Consensus Protocol: validators on each node's Unique Node List agree on ledger contents;
ledgers close in roughly three to five seconds. There is no staking yield, so **holding XRP
produces no protocol-level income.** The node queried reported 244 peers[^xrpl].

**Utility.** XRP is used to pay XRPL transaction costs, to meet account reserves, as a bridge
asset in Ripple's cross-border payment products, and as a base asset on the XRPL's native DEX
and AMM. As with any payments-utility narrative, distinguish *volume routed through a product*
from *demand to hold the token* — they are not the same thing and only the second supports price.

---

## Supply, issuance and float

### The pre-mine and the escrow

All 100B XRP existed on day one. A large majority was allocated to the company (then OpenCoin,
now Ripple) with the remainder to the founders — *the exact genesis split is **unverified** in
this pass; it is widely reported as ~80B to the company and ~20B to founders, but that was not
confirmed against a primary source here.*

In **December 2017**, Ripple placed **55 billion XRP into on-ledger escrow** — cryptographically
enforced time locks on the XRPL itself, not a corporate promise. The published mechanic:
**1 billion XRP is released per month, and the unused portion is returned to escrow**, which
stretches the schedule far beyond the nominal 55 months. Ripple's own Q1 2025 XRP Markets
Report describes the arrangement and states that "the remaining XRP released is put back into
the escrow each month," reporting **38,030,000,005 XRP** subject to on-ledger escrow at the
start of that quarter and **37,130,000,005 XRP** at the end[^ripple-q1-2025].

Ripple publishes a **quarterly XRP Markets Report** giving its own accounting of holdings and
sales. *The Q2 2026 edition could not be located in this pass — the Q1 2025 report is the most
recent one confirmed here. Check ripple.com/insights for the current quarter before quoting
company-reported holdings.*

### What Ripple actually holds, on-chain (primary)

Aggregated from the xrpscan rich-list API (top 10,000 accounts), retrieved **2026-08-05**[^xrpscan]:

| Category | XRP | % of 99.986B total |
|---|---:|---:|
| Ripple-labelled accounts — **escrowed** | 35,000,000,000 | 35.0% |
| Ripple-labelled accounts — **liquid** | 3,781,163,323 | 3.8% |
| **Ripple-labelled total (26 accounts)** | **38,781,163,323** | **38.8%** |
| All escrow on the ledger (incl. non-Ripple) | 35,145,515,359 | 35.2% |
| Sum of *balances* across top 10,000 accounts | 53,609,305,759 | 53.6% |

The non-Ripple escrow is small and identifiable — chiefly the Flare Core Vault at 140,000,000
XRP, plus ~5.5M scattered.

**Ripple controls roughly 38.8% of all XRP in existence**, of which about 90% is time-locked
and about 10% is immediately spendable. That is the single most important supply fact for a
trader: the largest holder by a wide margin is a private company with a disclosed, mechanical
distribution schedule. (Like the founder addresses below, this is an XRPSCAN account-label
aggregation — see the sourcing note on that table — not independently confirmed here.)

### The circulating-supply reconciliation problem

These three numbers do not add up cleanly, and you should know it before you use any of them:

| Quantity | Value | Source |
|---|---:|---|
| Total supply, on-ledger | 99,985,631,420 | XRPL RPC, 2026-08-05[^xrpl] |
| Less all on-ledger escrow | −35,145,515,359 | xrpscan, 2026-08-05[^xrpscan] |
| **= Unlocked XRP** | **64,840,116,061** | derived |
| CoinGecko "circulating supply" | 62,533,271,955 | CoinGecko API, 2026-08-05[^cg-xrp] |
| **Unexplained gap** | **~2.31B XRP (~$2.5B)** | derived |

*The composition of that ~2.31B gap is **unverified**.* Plausible explanations include a lagged
escrow snapshot on CoinGecko's side, additional Ripple-held balances excluded by their
methodology, or definitional differences in what counts as circulating. **Do not treat
"circulating supply" as a measured quantity for XRP.** It is a vendor convention, and every
turnover, market-cap, and float statistic you compute inherits that convention.

Note also the FDV: at **$107.4B** versus a **$67.1B** market cap[^cg-xrp], roughly 37% of XRP's
notional value sits in supply the market-cap figure excludes. That escrow is not hypothetical
future issuance — it is existing tokens on a published release timetable.

---

## Concentration and real float

### The finding

**XRP is not the turnover outlier the headline pairing suggests — BNB is.** At 1.37%[^turnover-std], XRP's
24h turnover sits within the same order of magnitude as BTC's 1.78%, and float adjustments move
it *closer* to BTC, not further away. The genuinely striking concentration fact about XRP is
not thin trading; it is **who holds it**.

### Turnover on different denominators

Same 24h volume ($927,366,523), 2026-08-05:

| Denominator | Float (XRP) | Float ($ at $1.074) | 24h turnover |
|---|---:|---:|---:|
| Total supply, incl. escrow | 99,985,631,420 | $107.4B | 0.86% |
| CoinGecko "circulating" | 62,533,271,955 | $67.1B | **1.38%** |
| Circulating less Ripple's liquid 3.78B | 58,752,108,632 | $63.1B | **1.47%** |
| *BTC, for reference* | 20,065,943 | $1,291.6B | *1.80%* |
| *BNB, headline, for reference* | 133,164,808 | $80.3B | *0.76%* |

Derived 2026-08-05. **Whatever float definition you pick, XRP lands between 0.86% and 1.47% —
a modest discount to BTC, not a different regime.** Presenting XRP and BNB as one phenomenon
("both strikingly thin") flattens a real distinction: BNB's 0.76% is a supply-accounting
artifact that inverts under correction; XRP's 1.38% is close to the honest number already.

### Holder concentration (primary)

Top accounts by liquid balance, xrpscan rich-list API, **2026-08-05**[^xrpscan]:

| Holder (label) | XRP (liquid) | Nature |
|---|---:|---|
| Ripple (26 accounts) | 3,781,163,323 | issuer / company treasury |
| Upbit | 6,414,045,193 | exchange omnibus (customer funds) |
| Binance | 2,589,370,955 | exchange omnibus |
| **chrislarsen** (co-founder) | **2,533,688,437** | individual founder holding |
| Bithumb | 1,841,653,858 | exchange omnibus |
| Uphold | 1,630,639,031 | exchange omnibus |
| **ahbritto** (co-founder) | **1,299,999,959** | individual founder holding |
| bitbank | 577,983,899 | exchange omnibus |
| Coincheck | 555,781,968 | exchange omnibus |
| eToro | 480,876,546 | exchange omnibus |
| Crypto.com | 345,184,953 | exchange omnibus |
| Coinone | 313,116,896 | exchange omnibus |
| bitFlyer | 192,062,082 | exchange omnibus |
| Bitget | 103,755,948 | exchange omnibus |
| Coinbase | 102,127,005 | exchange omnibus |

Cumulative liquid balances, same source and date:

| Cohort | XRP | % of CoinGecko circulating (62.53B) |
|---|---:|---:|
| Top 10 accounts | 11,980,019,272 | 19.2% |
| Top 20 accounts | 16,980,019,904 | 27.2% |
| Top 50 accounts | 26,810,254,465 | 42.9% |
| Top 100 accounts | 32,974,190,753 | **52.7%** |

**This cohort table does not reconcile against the per-holder table above it.** Summing just
the top four rows above (Upbit + Ripple + Binance + `chrislarsen` = 15,318,267,908) already
exceeds the stated "Top 10 accounts" total of 11,980,019,272. The exact aggregation basis
XRPSCAN applies to produce the cumulative cohort figures (raw address vs. labeled-entity
grouping, and whether Ripple's 26 accounts are folded into one cohort slot or several) **was
not verified in this pass.** Treat the per-holder table as the more legible source for
named-entity exposure and the cohort percentages as directionally indicative only.

**Read this table correctly.** The bulk of the top cohort is **exchange omnibus wallets** —
Upbit's 6.41B is thousands of customers' coins, not one owner's position, and those balances
are arguably the most tradable XRP in existence rather than the least. So "top 100 hold 52.7%"
is **not** the same claim as "52.7% is controlled by 100 decision-makers."

What *is* a genuine concentration claim, and it is a large one:

- **Ripple: 38.78B XRP (38.8% of total supply)** — 35.0B escrowed, 3.78B liquid.
- **Two named co-founder addresses: 3.83B XRP (~3.8% of total, ~$4.1B)** — `chrislarsen`
  2.53B and `ahbritto` 1.30B. *These are explorer-attributed labels; the attribution is
  widely used but was not independently confirmed here.*
- Combined issuer plus named-founder holdings: **~42.6B XRP, ~42.6% of all XRP.**

**Geographic and venue concentration is a second axis.** Six of the ten largest exchange
holders are South Korean or Japanese (Upbit, Bithumb, Coincheck, Coinone, bitbank, bitFlyer) —
ranking exchange entities only (Ripple and the two founder addresses are not exchanges, so
they're excluded from this ranking).
XRP has an unusually strong East Asian retail base, which means a meaningful slice of the float
sits behind exchanges whose regulatory regime, operating hours, KRW/JPY quote currencies, and
retail behaviour differ from the USD venues you are likely trading on.

### So what does XRP's turnover actually reflect?

Not locked supply — the escrow is already excluded from the circulating denominator. Not thin
genuine float either, at 1.4%. The most defensible reading is that **XRP's turnover is normal
for a large-cap with a substantial buy-and-hold retail base and no yield mechanism.** There is
no staking to lock coins up and no DeFi sink of consequence, so what you see is close to what
there is: a large, dispersed, mostly dormant retail holder base that trades in bursts around
news.

---

## What drives the price

**1. The SEC litigation — resolved, with a dated record.** State the holdings and dates; avoid
characterising the outcome. Both "the court ruled XRP is not a security" and "Ripple lost" are
inaccurate summaries.

| Date | Event |
|---|---|
| **2020-12-22** | SEC filed suit against Ripple Labs, Bradley Garlinghouse, and Christian Larsen, *SEC v. Ripple Labs, Inc.*, No. 20-cv-10832 (AT) (S.D.N.Y.), alleging unregistered offer and sale of securities[^sec-2020][^torres]. |
| **2020-12-28 → 2021-01-19** | Coinbase moved XRP to limit-only on 2020-12-28 and **fully suspended XRP trading on 2021-01-19 at 10:00 PST**[^cb-suspend]. Numerous US venues did likewise. |
| **2023-07-13** | Judge Analisa Torres issued summary judgment (Doc. 874)[^torres]. See the holdings below. |
| **2023-07-13** | **Coinbase relisted XRP the same day**, "Updated July 13th at 5:35pm ET"[^cb-relist]. |
| **2024-08-07** | Final Judgment entered: Ripple **permanently enjoined** from violating Section 5 of the Securities Act, and ordered to pay a civil penalty of **$125,035,150**[^sdny-2025]. |
| **2024 Q4** | Both sides appealed to the Second Circuit (Ripple cross-appealed); the appeal was **stayed in April 2025** pending settlement discussions[^vitallaw]. |
| **2025-05-08** | The SEC and Ripple signed an agreement to settle in both the district court and the Second Circuit, contingent on the district court dissolving the injunction and reducing the penalty[^sdny-2025]. |
| **2025-06-26** | Judge Torres **denied** the joint request; the injunction was not dissolved and the penalty was not reduced[^sdny-2025][^bloomberg]. |
| **2025-08-07/08** | Ripple and the SEC **dismissed their appeals**, ending the litigation. The August 2024 Final Judgment stands: injunction in place, **$125 million penalty intact**[^reuters-2025][^bloomberg]. |

**What the July 2023 summary judgment actually held** — the operative paragraph, verbatim:

> "For the foregoing reasons, the SEC's motion for summary judgment is GRANTED as to the
> Institutional Sales, and otherwise DENIED. Defendants' motion for summary judgment is
> GRANTED as to the Programmatic Sales, the Other Distributions, and Larsen's and
> Garlinghouse's sales, and DENIED as to the Institutional Sales."[^torres]

And on the token itself, verbatim:

> XRP, as a digital token, is not in and of itself a "contract, transaction[,] or scheme"
> that embodies the Howey requirements of an investment contract. Rather, the Court examines
> the totality of circumstances surrounding Defendants' different transactions and schemes
> involving the sale and distribution of XRP.[^torres]

(Howey refers to the Howey test, the U.S. Supreme Court framework — from *SEC v. W.J. Howey
Co.* — for what counts as an "investment contract" under securities law.)

The distinction the court drew was **manner of sale**, not intrinsic token status:

- **Institutional Sales** (~$728.9M alleged): direct sales to institutional buyers, hedge
  funds and ODL (On-Demand Liquidity, Ripple's cross-border payments product) customers under
  written contracts — held to be offers and sales of investment contracts[^torres].
- **Programmatic Sales** (~$757.6M alleged): algorithmic sales on digital asset exchanges,
  described by the court as **"blind bid/ask transactions"** in which "Ripple did not know who
  was buying the XRP, and the purchasers did not know who was selling it" — summary judgment
  for defendants[^torres].
- **Other Distributions** (XRP paid for services, including to employees) and **Larsen's and
  Garlinghouse's personal sales** — summary judgment for defendants[^torres].

The court also cabined its own reach in footnote 20: "Because the Court finds that only the
Institutional Sales constituted the offer and sale of investment contracts, the Court does not
address Defendants' asserted fair notice defense as to the other transactions and
schemes"[^torres]. This is a district-court summary judgment that was never reviewed on appeal
— the appeals were dismissed, not decided. Its precedential weight is correspondingly limited.

**2. The broader US classification framework.** Per the local corpus (verified-as-of 2026-06-21):
the **CLARITY Act (H.R. 3633)** passed the House on 2025-07-17 by 294–134, classifying BTC, ETH,
SOL and XRP as digital commodities, but **had not passed the Senate** as of June 2026; and a
**SEC/CFTC joint interpretation published 2026-03-17** identifies 18 major cryptocurrencies as
digital commodities, XRP among them, binding on both agencies but changeable by a future
administration without legislation[^corpus-crypto]. Classification risk is reduced, not eliminated.

**3. Escrow releases.** 1B XRP unlocks monthly with the unused portion re-escrowed. This is a
known, scheduled, published overhang. It is not a surprise, but it is a persistent supply
headwind that BTC and ETH do not have.

**4. ETF access.** The 2025 wrapper build-out (details in the next section) opened US brokerage
access. Whether it opened durable *demand* is a separate question; see the AUM caveat.

**5. Beta to Bitcoin.** ρ ≈ 0.86 to BTC on both 90d and 180d windows — see below. XRP does not
decouple from crypto beta, whatever the payments narrative implies.

---

## Market structure and liquidity

### Where XRP actually trades

CoinGecko ticker data, top 100 tickers totalling $893.4M, retrieved 2026-08-05[^cg-tick-xrp]:

| Venue | 24h USD volume | Share |
|---|---:|---:|
| BitMart | $74,868,684 | 8.4% |
| OKX | $67,676,067 | 7.6% |
| Binance | $64,520,079 | 7.2% |
| KuCoin | $39,459,373 | 4.4% |
| Coinbase International Exchange | $38,834,858 | 4.3% |
| **Coinbase Exchange (XRP/USD)** | **$37,618,224** | **4.2%** |
| BVOX | $31,718,190 | 3.6% |
| BTCC | $28,182,638 | 3.2% |
| WEEX | $27,296,020 | 3.1% |
| Upbit | $24,742,145 | 2.8% |
| Poloniex | $20,544,520 | 2.3% |
| Gate | $20,524,543 | 2.3% |

**XRP's venue profile is materially healthier than BNB's.** No venue exceeds 8.4%; the
distribution is genuinely broad; and tier-1 regulated venues (OKX, Binance, Coinbase Exchange,
Coinbase International, Upbit, Gate, KuCoin) carry a large share. The standard crypto caveat
still applies — the corpus records Bitwise's 2019 finding that ~95% of reported spot volume on
unregulated exchanges was fake, and Chainalysis's ~$2.57B DEX wash-trading estimate for
2024[^corpus-crypto] — and several venues on this list are second-tier. But XRP does not have
BNB's pattern of a token trading mostly on venues you would not choose.

CoinGecko reports near-identical bid-ask spreads across unrelated venues (~0.0193% on many
books), which is an aggregation artifact; **spread figures from that source are not used here.**

### ETF and wrapper access

| Product | Date | Note |
|---|---|---|
| REX-Osprey XRP ETF (XRPR) | launched 2025-09-18 | First US XRP ETF; 1940-Act structure, not a spot trust[^etf] |
| Canary Capital XRP ETF (XRPC) | approved 2025-11-12, trading 2025-11-13 | Reported as the first US **spot** XRP ETF[^etf] |
| Bitwise XRP ETF (ticker XRP) | began trading NYSE 2025-11-20 | [^etf] |
| 21Shares XRP ETF | Cboe BZX listing certified December 2025 | [^etf] |

*Current (2026) AUM for these products could not be verified in this pass.* One 2025 datapoint:
REX-Osprey XRPR passed $100M AUM by late October 2025[^etf]. **Do not assume the XRP ETF complex
is large** — the comparable BNB product (VanEck's VBNB) held only $2.28M as of
2026-07-31[^vaneck-fund], and wrapper existence has repeatedly failed to imply wrapper demand
in this cycle.

### Structural notes

- No consolidated tape, no NBBO; XRP/USDT on Binance and XRP/USD on Coinbase are independent
  books linked only by arbitrage[^corpus-crypto].
- 24/7 trading, no scheduled close, no spot circuit breakers[^corpus-crypto].
- XRPL has a native on-ledger DEX and AMM, so some XRP liquidity exists outside CEXs — *its
  depth relative to CEX books was **not** measured in this pass.*
- Quote-currency fragmentation matters more for XRP than for most large caps: significant
  volume prints in USDT, USDC, USD, KRW and JPY. Your basis depends on which one you use.

---

## Volatility and correlation

Measured directly from Coinbase Exchange daily bars (`api.exchange.coinbase.com`), close-to-close
log returns, computed 2026-08-05.

| Asset | 90d annualised realised vol | 180d | 270d |
|---|---:|---:|---:|
| XRP-USD | **43.5%** | **43.7%** | **61.0%** |
| BTC-USD | 34.8% | 38.8% | 45.5% |
| BNB-USD | 41.2% | 39.2% | 45.5% |

| Pair | 90d ρ | 180d ρ |
|---|---:|---:|
| XRP vs BTC | **+0.869** | **+0.857** |
| XRP vs BNB | +0.691 | +0.756 |
| BNB vs BTC | +0.730 | +0.788 |

Drawdowns over the available Coinbase window (to 2026-08-05):

| Asset | Window | Window high | Last | Drawdown |
|---|---|---:|---:|---:|
| XRP-USD | 2025-08-21 → 2026-08-05 (350 bars) | $3.121 | $1.067 | **−65.8%** |
| BTC-USD | 2025-08-21 → 2026-08-05 (350 bars) | $124,720.09 | $64,056.21 | −48.6% |
| BNB-USD | 2025-10-22 → 2026-08-05 (288 bars) | $1,139.32 | $598.21 | −47.5% |

**Interpretation.** XRP runs roughly 1.15–1.35× BTC's realised vol depending on window, and is
the *more* BTC-correlated of the two assets in this pair (ρ ≈ 0.86 vs BNB's ≈ 0.73–0.79). It
also fell substantially further than BTC in this drawdown: −65.8% versus −48.6% from the
respective 350-bar highs, and −70.6% from its 2025-07-17 ATH of $3.65[^cg-xrp].

That combination — high beta, high correlation, deeper drawdown — is the profile of a
**leveraged expression of crypto beta**, not a diversifier. The 270d vol figure (61.0%) versus
the 90d (43.5%) also shows meaningful vol clustering: the numbers here are regime-specific,
measured across a single bull-to-bear transition, and should be recomputed on your own window.

---

## Known failure modes for traders

1. **Misstating the legal outcome.** "A court ruled XRP is not a security" is wrong. The court
   held that XRP *as a token* is not itself an investment contract, that Ripple's Institutional
   Sales *were* unregistered securities offerings, and that its Programmatic Sales, Other
   Distributions, and the individuals' sales were not[^torres]. A permanent injunction and a
   $125,035,150 penalty remain in force[^sdny-2025][^reuters-2025]. If your thesis depends on
   the summary, get the summary right.
2. **Treating an unreviewed district-court ruling as settled precedent.** The appeals were
   dismissed, not decided. No appellate court has ruled on the reasoning.
3. **Issuer concentration risk.** One private company holds ~38.8% of all XRP, with a
   mechanical monthly release schedule[^xrpscan]. Add two named founder addresses and the
   figure is ~42.6%. There is no comparable single-entity overhang in BTC or ETH.
4. **Venue concentration risk, geographic flavour.** A large share of the identifiable float
   sits in Korean and Japanese exchange omnibus wallets[^xrpscan]. Regulatory action, an
   outage, or a withdrawal freeze at one of those venues is a float event, not just a venue event.
5. **The listing-suspension precedent is not hypothetical.** Coinbase suspended XRP trading
   entirely from 2021-01-19 to 2023-07-13 in response to a regulatory filing[^cb-suspend][^cb-relist].
   Any US venue can do this again if classification shifts. Have an exit that does not depend
   on one jurisdiction's venues staying open.
6. **Trusting "circulating supply."** There is a ~2.31B XRP gap between on-ledger unlocked
   supply and CoinGecko's circulating figure that this pass could not explain. Market cap,
   turnover and any float-weighted sizing all inherit that ambiguity.
7. **Reading escrow as a hidden supply cliff.** It is disclosed, time-locked on-chain, and
   released on a published schedule with re-escrow of the unused portion[^ripple-q1-2025]. The
   overhang is real but it is not a surprise, and monthly-unlock narratives usually overstate
   its marginal impact.
8. **Assuming the payments narrative is a demand floor.** XRP earns no protocol yield, and
   volume routed through a corporate product is not the same as demand to hold the token.
9. **Ignoring quote-currency basis.** XRP prints in USD, USDT, USDC, KRW and JPY across venues
   with no NBBO. Backtesting on a composite and executing on one book leaves you an unmodelled basis.
10. **Assuming ETF wrappers imply depth.** Four wrappers launched in late 2025; 2026 AUM is
    unverified here, and the comparable BNB ETF is minuscule.

---

## For this backtester

**Neither BNB nor XRP is held locally.**

### XRP *is* on Coinbase and *is* fetchable — the framing to correct

The task premise implied BNB is Coinbase-fetchable in contrast to XRP. Verified against the
live Coinbase Exchange API on **2026-08-05**, that contrast does not hold on the venue side:

```
GET https://api.exchange.coinbase.com/products
  XRP-USD    status=online     trading_disabled=false   quote_increment=0.0001
  XRP-USDT   status=online     trading_disabled=false
  XRP-EUR    status=online     trading_disabled=false
  XRP-BTC    status=delisted   trading_disabled=true
  XRP-GBP    status=delisted   trading_disabled=true
  BNB-USD    status=online     trading_disabled=false   quote_increment=0.01
```

XRP is not only listed, it is the **far more liquid** of the two on Coinbase — see the table
below. The real XRP data problem is a **gap**, not an absence.

### The 2021–2023 hole in Coinbase XRP history

Coinbase suspended XRP trading on **2021-01-19** and relisted on **2023-07-13**[^cb-suspend][^cb-relist].
A probe of the candles endpoint on 2026-08-05 returned data for a 2023-07-01 → 2023-08-05 window
with the **earliest bar at 2023-07-13**, matching the relisting date exactly. *Probes of 2020 and
2022 windows returned empty responses that could not be cleanly distinguished from rate-limiting,
so the **absence** of pre-2021 data on this endpoint is **unverified** — but the ~2.5-year
suspension is a matter of public record.*

**Assume a ~30-month hole in any Coinbase-sourced XRP series covering 2021–2023, and handle it
explicitly.** A naive fetch will silently concatenate January 2021 to July 2023 and produce a
single bar containing a multi-year return. That will destroy any volatility estimate, any
drawdown calculation, and any signal that differences prices. Options: start the series at
2023-07-13; splice a different venue across the gap and accept the basis discontinuity (this
creates its own price-level jump at the splice date — inspect it the same way you would the
concatenation artifact above); or mask the period and exclude it from all windows.

This is also a **live example of listing-driven survivorship bias**: a universe defined as
"assets Coinbase lists today" includes XRP because of a court ruling in 2023 and includes BNB
because of a commercial decision in 2025. Anchor universe membership to per-asset listing dates
or your backtest is conditioning on the future.

### What the turnover figure means for a realistic cost model

**Start from the corrected finding: XRP's 1.37% turnover is not anomalous.** It is a modest
discount to BTC's 1.80%, and float adjustments narrow the gap. Do not apply an illiquidity
penalty on the strength of that number. **BNB is the asset whose headline turnover is
misleading — and it is misleading in the opposite direction.**

The number that should drive your cost model is venue depth:

| Measure | XRP | BNB | Source |
|---|---:|---:|---|
| Global 24h volume | $927,366,523 | $608,516,445 | CoinGecko API, 2026-08-05[^cg-xrp] |
| Coinbase Exchange 24h volume | $37,618,224 (4.1% of global) | $2,497,477 (0.41% of global) | CoinGecko tickers, 2026-08-05[^cg-tick-xrp] |
| Coinbase **30-day average** volume | ~37.97M XRP/day ≈ **$41.5M/day** | ~1,818.6 BNB/day ≈ **$1.1M/day** | measured from Coinbase daily candles, 2026-08-05 |
| Coinbase daily bars available | 350+ (with a 2021–2023 gap) | 288, from 2025-10-22 | Coinbase candles API, 2026-08-05 |

**The Coinbase XRP book is roughly 38× the Coinbase BNB book on the 30-day average** (the 24h
snapshot alone shows a smaller ~15× gap — use the 30-day figure for sizing, since a single day
is noisier). Treat the two assets as different liquidity tiers even though their market caps
are within 20% of each other.

Concrete implications:

1. **Size against ADV.** At ~$41.5M/day, a 1% participation cap is ~$415k/day of XRP — workable
   for most retail-to-small-fund sizing. The same 1% rule on Coinbase BNB gives ~$11k/day. Two
   assets, one venue, a ~38× difference in capacity (matching the book-size ratio above).
2. **A flat slippage assumption is defensible for XRP, marginal for BNB.** For XRP on Coinbase
   at small size, a fixed-bp cost model plus fees is a reasonable first approximation. Validate
   the participation-rate threshold where it breaks down; do not assume the same threshold
   transfers to BNB.
3. **Fees are the dominant modelled cost for XRP at small size.** Coinbase Advanced base-tier
   spot is 0.40% maker / 0.60% taker[^corpus-crypto] — for a strategy turning over daily,
   ~1.0% round-trip in fees swamps most signal edges. **Model fees before you model anything
   else.** Many indicator strategies that look profitable gross are negative net at these rates.
4. **Handle the history gap explicitly** (above). This is the single largest source of silent
   error in a Coinbase-sourced XRP backtest.
5. **Beware regime-specific parameters.** XRP's 90d vol (43.5%) versus 270d (61.0%) differ by
   nearly 40%; ρ to BTC is ~0.86. Anything calibrated on the current 350-bar window is
   calibrated on one bull-to-bear transition.
6. **Do not model XRP as an uncorrelated payments asset.** At ρ ≈ 0.86 to BTC with higher vol
   and a deeper drawdown, an XRP sleeve is close to a levered BTC sleeve for portfolio-risk
   purposes. If your allocation logic assumes diversification, measure the correlation on your
   own window before you rely on it.
7. **Escrow releases are a schedulable exogenous variable.** ~1B XRP unlocks monthly. If you
   are testing calendar or event-driven effects, this is a real, known, dateable series — and
   also an obvious multiple-testing trap. Any "monthly unlock" effect you find on ~350 bars is
   about a dozen events; that is not enough for an inference.

**Bottom line for sizing:** XRP is a normally-liquid large cap with a well-distributed venue
profile, comfortably tradable on Coinbase at retail-to-small-fund size, whose real hazards are
(a) a ~30-month hole in Coinbase history, (b) 0.40%/0.60% fees that kill high-turnover
strategies, and (c) a single-issuer overhang of ~38.8% of supply that no volume statistic will
warn you about.

---

## Sources

[^cg-xrp]: CoinGecko API, `/api/v3/coins/ripple`. Retrieved 2026-08-05 03:03:18 UTC (`last_updated` field). Price $1.074; market cap $67,148,724,849; FDV $107,365,370,963; 24h volume $927,366,523; circulating 62,533,271,955; total 99,985,635,707; max 100,000,000,000; ATH $3.65 on 2025-07-17. BTC comparison figures (price $64,363; market cap $1,291,599,527,457; 24h volume $23,203,709,215; turnover 1.797%) from `/api/v3/coins/bitcoin`, retrieved 2026-08-05 03:03:38 UTC. https://api.coingecko.com/api/v3/coins/ripple

[^cg-tick-xrp]: CoinGecko API, `/api/v3/coins/ripple/tickers?depth=true&order=volume_desc`. Retrieved 2026-08-05. Top 100 tickers, $893,368,570 aggregate.

[^xrpl]: XRP Ledger public JSON-RPC, `s1.ripple.com:51234`. `ledger` command on the validated ledger 106,078,752, closed 2026-08-05 03:01:50 UTC: `total_coins` = 99,985,631,419,854,851 drops = 99,985,631,419.85 XRP. `server_state` at ledger 106,079,046: `rippled` 3.3.0-rc6, `base_fee` 10 drops, `reserve_base` 1,000,000 drops (1 XRP), `reserve_inc` 200,000 drops (0.2 XRP), 244 peers.

[^xrpscan]: XRPSCAN API, `https://api.xrpscan.com/api/v1/balances` (top 10,000 accounts by balance). Retrieved 2026-08-05. Aggregates computed locally: Ripple-labelled 26 accounts with 3,781,163,323 XRP liquid and 35,000,000,000 XRP escrowed; total listed escrow 35,145,515,359 XRP; total listed balances 53,609,305,759 XRP; top-10 11,980,019,272; top-20 16,980,019,904; top-50 26,810,254,465; top-100 32,974,190,753. Account labels (Ripple, Upbit, Binance, chrislarsen, ahbritto, etc.) are XRPSCAN's, not independently verified.

[^torres]: *SEC v. Ripple Labs, Inc., Bradley Garlinghouse, and Christian A. Larsen*, No. 20 Civ. 10832 (AT), Opinion and Order on cross-motions for summary judgment, ECF Doc. 874, filed **2023-07-13** (S.D.N.Y., Torres, J.). Text extracted directly from the court's published PDF on 2026-08-05 and every quoted span below re-checked against that extraction by exact string match after whitespace/curly-quote normalisation. Quoted passages: the CONCLUSION paragraph; the "not in and of itself a 'contract, transaction[,] or scheme'" holding; footnote 20 on the limits of the holding; the "blind bid/ask transactions" characterisation of Programmatic Sales; alleged amounts of ~$728.9M (Institutional Sales) and ~$757.6M (Programmatic Sales). https://www.nysd.uscourts.gov/sites/default/files/2023-07/SEC%20vs%20Ripple%207-13-23.pdf

[^sec-2020]: SEC Press Release 2020-338, 2020-12-22 (complaint filing), as cited in the SDNY docket and in Coinbase's contemporaneous notice[^cb-suspend].

[^sdny-2025]: *SEC v. Ripple Labs*, S.D.N.Y. order dated **2025-06-26** denying the parties' joint request for an indicative ruling. Recites that on **2024-08-07** the court entered Final Judgment permanently enjoining Ripple from violating Section 5 and directing payment of a civil penalty of **$125,035,150**, and that on **2025-05-08** the parties signed an agreement to settle in the district court and the Second Circuit. https://www.nutter.com/assets/htmldocuments/SEC%20v%20Ripple%20Labs%202025.06.26.pdf

[^reuters-2025]: Reuters, "SEC ends lawsuit against Ripple, company to pay $125 million fine," 2025-08-08. Both parties agreed to dismiss their appeals, leaving the $125M fine intact. https://www.reuters.com/legal/government/sec-ends-lawsuit-against-ripple-company-pay-125-million-fine-2025-08-08/

[^bloomberg]: Bloomberg Law, "Ripple, SEC Drop Appeal After Settlement Path Blocked by Judge." Second Circuit No. 24-2648, dated 2025-08-07.

[^vitallaw]: VitalLaw (Wolters Kluwer) blockchain coverage of the SDNY docket, "S.D.N.Y.: SEC tells court its crypto backdown is 'exceptional circumstances' justifying Ripple penalty reduction": both sides appealed the July 2023 ruling to the Second Circuit; the appeal was paused in April 2025 after the parties indicated a settlement path. Retrieved 2026-08-05. https://www.vitallaw.com/news/blockchain-s-d-n-y-sec-tells-court-its-crypto-backdown-is-exceptional-circumstances-justifying-ripple-penalty-reduction/sld0149c9baed89cd452490ef33cc062241b4 — secondary source; the underlying stay is corroborated by the 2025-06-26 SDNY order[^sdny-2025], which recites the May 2025 settlement agreement.

[^cb-suspend]: Coinbase blog, "Coinbase will suspend trading in XRP on January 19," published 2020-12-28. Limit-only from 2020-12-28 14:30 PST; full suspension **2021-01-19 10:00 PST**. https://www.coinbase.com/blog/coinbase-will-suspend-trading-in-xrp-on-january-19 — corroborated by Reuters, 2020-12-28.

[^cb-relist]: Coinbase Help Center, "Ripple SEC Lawsuit": "Updated July 13th at 5:35pm ET - Coinbase has relisted XRP on Coinbase." Notes XRP unsupported in Japan, New York State, and Singapore due to restrictions. https://help.coinbase.com/en/coinbase/trading-and-funding/cryptocurrency-trading-pairs/ripple-sec — corroborated by Reuters and The Block, 2023-07-13.

[^ripple-q1-2025]: Ripple, "Q1 2025 XRP Markets Report." Describes the escrow arrangement ("the remaining XRP released is put back into the escrow each month") and reports Total XRP Subject to On-Ledger Escrow of 38,030,000,005 (quarter start) and 37,130,000,005 (quarter end). https://ripple.com/insights/q1-2025-xrp-markets-report/ — most recent Ripple markets report confirmed in this pass; **the Q2 2026 report was not located.**

[^etf]: XRP ETF timeline assembled from contemporaneous coverage retrieved 2026-08-05: REX-Osprey XRP ETF (XRPR) launched 2025-09-18 and passed $100M AUM by late October 2025; Canary Capital's XRP ETF (XRPC) approved 2025-11-12 and listed 2025-11-13, reported as the first US spot XRP ETF; Bitwise XRP ETF (ticker XRP) began trading on NYSE 2025-11-20 (Bitwise newsroom); Cboe BZX certified 21Shares' XRP ETF listing in December 2025 (CoinDesk, 2025-12-11). **2026 AUM figures unverified.**

[^vaneck-fund]: VanEck VBNB fund page, "ETF Statistics as of 07/31/2026." Total net assets $2,284,194. Cited here only as a comparator for BNB wrapper demand; see the BNB reference for the primary discussion. https://www.vaneck.com/us/en/investments/bnb-etf-vbnb — retrieved 2026-08-05.

[^corpus-crypto]: Local corpus — `~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md` (verified-as-of: 2026-06-21). Used for: absence of NBBO; Coinbase Advanced fee tiers (0.40% maker / 0.60% taker); Bitwise 2019 and Chainalysis 2025 wash-trading estimates; 24/7 trading and no spot circuit breakers; CLARITY Act House passage 2025-07-17 (294–134) with XRP classified as a digital commodity and no Senate passage as of June 2026; SEC/CFTC joint interpretation of 2026-03-17 naming 18 digital commodities including XRP.

**Primary data pulled live for this document (all 2026-08-05):**
- XRP Ledger JSON-RPC — `ledger`, `server_state`. `https://s1.ripple.com:51234`
- XRPSCAN API — `/api/v1/balances` rich list. `https://api.xrpscan.com`
- Coinbase Exchange REST API — `/products` (listing status), `/products/{id}/candles` (daily OHLCV, volume, history depth). `https://api.exchange.coinbase.com`
- CoinGecko API v3 — `/coins/{id}`, `/coins/{id}/tickers`.
- Court opinion text extracted locally from the SDNY-published PDF of ECF Doc. 874.

**Explicitly unverified in this pass:** the exact genesis allocation split between the company
and the founders; the composition of the ~2.31B XRP gap between on-ledger unlocked supply and
CoinGecko's circulating figure; the contents of any Ripple XRP Markets Report after Q1 2025;
current (2026) AUM of the XRP ETF complex; the depth of XRPL's native DEX/AMM relative to CEX
books; the `chrislarsen` and `ahbritto` address attributions (explorer labels); whether
Coinbase's candles endpoint truly holds no pre-2021 XRP data (probes were inconclusive); and
the aggregation basis XRPSCAN uses for the Top 10/20/50/100 cohort table, which does not
reconcile against the per-holder table above it.

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
