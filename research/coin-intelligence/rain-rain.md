---
name: rain-rain
description: Sceptical trader-facing reference on Rain (RAIN), an Arbitrum prediction-market token whose ~$8.6B headline market cap is not corroborated by tracked protocol activity, tradeable float, or order-book depth.
---

# Rain (RAIN)

> **Not investment advice.** This is a factual reference, written sceptically. Every figure carries a
> date and a source. Where the record does not support a claim, the document says so rather than
> filling the gap.

## Snapshot (AS OF 2026-08-04)

All figures fetched 2026-08-04 unless stated. **These decay fast**, and for this asset they were
already mutually inconsistent at the moment of capture — see the next section, which is the point of
this document.

| Metric | Value | Source (date) |
|---|---|---|
| Price | $0.01244 | CoinGecko and CoinMarketCap (2026-08-04) |
| Market cap | $8.641B (CoinGecko) / $8.643B (CMC) / $8.645B (DefiLlama) | all 2026-08-04 |
| **Rank by market cap** | **#14–15 (CoinGecko) / #201 (CMC) / #16 (DefiLlama)** | all 2026-08-04 |
| Circulating supply | 694.586B "Est." | CoinGecko (2026-08-04) |
| Total / max supply | 1,149,834,572,702 | CoinGecko (2026-08-04) |
| FDV | $14.30B — MC/FDV 0.6 | CoinGecko (2026-08-04) |
| 24h volume | $20.43M (CoinGecko) / $29.1M (CMC) / $19.53M (DefiLlama) | all 2026-08-04 |
| **Turnover (24h vol ÷ mcap)** | **0.24%** (using $20.43M / $8.641B) | computed |
| TVL | $23.23M, −17.7% over 30d — MC/TVL 372x, FDV/TVL 616x | DefiLlama (2026-08-04) |
| **Protocol fees, trailing 30d** | **$76** | DefiLlama (2026-08-04) |
| **Protocol revenue, trailing 30d** | **$46.24** | DefiLlama (2026-08-04) |
| **Protocol volume, trailing 30d** | **$40.99** | DefiLlama (2026-08-04) |
| Cumulative protocol volume since inception | $39.41M | DefiLlama (2026-08-04) |
| Cumulative protocol fees since inception | $1.35M | DefiLlama (2026-08-04) |
| Protocol treasury | $743.51M — of which $743.51M is **its own token** | DefiLlama (2026-08-04) |
| Holders | 170,200 | CMC (2026-08-04) |
| Venues | 11 exchanges / 13 markets — no Binance, Coinbase, Kraken, OKX, Bybit or Upbit | CoinGecko (2026-08-04) |
| **Total ±2% order-book depth, all listed venues** | **≈$294k bid-side (what you can sell into) / ≈$319k ask-side** | summed from CoinGecko markets table (2026-08-04) |
| All-time high | $0.01656 on 2026-06-29 (CoinGecko) / $0.016 on 2026-06-22 (DefiLlama) | 2026-08-04 |
| All-time low | $0.002221 on 2025-09-14 (CoinGecko) / **$0.0003934 on 2025-09-09 (CMC)** | 2026-08-04 |

Contract: `0x25118290e6A5f4139381D072181157035864099d` (Arbitrum, ERC-20). Website `rain.one`.
Whitepaper `whitepaper.rain.one`. GitHub `github.com/rain1-labs`.

## What could and could not be established

**This section is the finding. Read it before anything below it.**

### The one-line version

Rain's ~$8.6B headline market cap is arithmetically real — it is a real price multiplied by a real
token count — but **almost nothing corroborates it.** The protocol the token is supposed to represent
recorded **$76 in fees over the trailing 30 days** on DefiLlama. The entire visible order book within
2% of mid across every venue that lists it totals roughly **$294,000**. The largest disclosed holder
has an option to buy another 23.6% of supply from the issuer at **73% below market**. Treat the
market cap as an unreliable number.

### What IS established (multiple independent sources agree)

- **What it is and where.** Rain is a prediction-markets / decentralised-options protocol on
  Arbitrum. ERC-20, 18 decimals, contract verified on Arbiscan. Categorised by CoinGecko as Gambling
  (GambleFi), DeFi, Options and Prediction Markets.
- **When it launched.** August–September 2025, with an initial supply of 1.15 trillion tokens
  (CoinDesk; ATL dates of 2025-09-09/14 across aggregators). The unlock schedule runs from
  September 2025 into late 2027.
- **The allocation.** Marketing & Development Fund 20%, Reserve & Treasury 20%, Ecosystem Growth &
  Staking 15%, Launchpad/Exchanges/LPs 15%, Contributors/Advisors/Strategic Partners 10%, Team 10%,
  Strategic Sale 9%, Presale (Miners, Private Sale, Refund) 1% (Tokenomist via CoinGecko).

*Caveat on this list:* the launch venue, the audit and the Foundation's identity in the bullets above
originate from the project's own aggregator submission — see the provenance warning under "What could
NOT be established at all". Only the on-chain facts (contract, supply, holder count) and the
Enlivex disclosures are independently grounded.
- **The token mechanic as described.** A 5% trading fee, split 2.5% to participants and 2.5% to
  buy-and-burn RAIN; new tokens equal to 10% of the burned amount may be minted for team and
  ecosystem; holding RAIN grants "Trading Power" gating how much of a balance can be used
  (CoinDesk). Because burn and mint coexist, **there is no fixed maximum supply** despite aggregators
  displaying one.
- **The largest holder.** Enlivex Ltd. (Nasdaq: **ENLV**), an Israeli company in Nes Ziona that
  describes itself as "a quality longevity company powered by a prediction markets treasury."
  Its RAIN position and its option over further tokens are disclosed in SEC filings (below). This is
  the best-documented fact about RAIN, because a US-listed issuer is legally obliged to disclose it.
- **Where it trades.** Eleven venues, all tier-2/3 CEXs plus one Uniswap V3 pool on Arbitrum.

### What is CONTESTED — and cannot be reconciled from public sources

**1. The market-cap rank contradicts itself across aggregators, by an enormous margin.**

On the same day, at essentially the same market cap:

| Aggregator | Market cap | Rank |
|---|---|---|
| CoinGecko | $8.641B | **#14** in the header, **#15** in its own FAQ on the same page |
| CoinMarketCap | $8.643B | **#201** |
| DefiLlama | $8.645B | #16 |

A $8.6B asset cannot simultaneously be the 14th and the 201st largest. CMC displays #201 directly
beside a market cap that would place it in the top 30 by its own ordering — the page does not state
the basis for the rank, and neither aggregator explains the divergence. **I could not establish why.**
The plausible explanations (CMC excluding self-reported or unverified supply from its main ranking;
different circulating-supply methodologies) are inferences, not findings, and I am not asserting them.
CoinGecko cannot even keep its own page internally consistent — the header says #14, the FAQ says #15.

**2. Circulating supply is contested across a ~3x range, and CoinGecko contradicts itself.**

| Figure | Source | Implied mcap at $0.01244 |
|---|---|---|
| ~230–240B ("around one fifth of total") | CoinDesk asset description | ~$2.9B |
| 478.4B | TokenRadar snapshot dated 2026-05-14 | ~$6.0B (at that date's price, $3.60B) |
| 648.1B "unlocked and in circulation" | CoinGecko **tokenomics block**, 2026-08-04 | ~$8.06B |
| 694.586B "Est. Circulating Supply" | CoinGecko **statistics block**, same page, same day | $8.64B |

The last two appear **on the same page at the same moment** and differ by ~46 billion tokens, about
$580M of market cap. The headline figure everyone quotes is the largest one in the range.

**3. CoinGecko's circulating supply counts the issuer's own treasury as circulating.**

CoinGecko derives it as: total supply 1,149,834,572,702, minus the Claim Vesting contract
(`0xc41A…`, 8,531,234,195), minus the Sablier vesting contract (`0x467D…`, 446,716,886,628) =
694,586,451,878. **That is the entire deduction.** It does **not** deduct the 230,000,000,000 tokens
(20% of supply, ~$2.86B) that CoinGecko itself separately identifies as "Reserve & Treasury" when
computing a different metric ("Outstanding Supply", 917.25B). So the same page uses two incompatible
bases, and the one feeding the headline market cap treats ~33% of "circulating" supply as tradeable
public float when the aggregator's own data says it is treasury.

**4. Protocol activity: the issuer's number and the independent tracker differ by orders of
magnitude. This is the central unresolved conflict.**

- **Enlivex, SEC Form 6-K filed 2026-07-30 (Exhibit 99.1):** "trading volume on the Rain protocol
  reached **$860 million**" as of 2026-07-29, with "**622%** month-over-month growth in trading volume
  during July 2026 vs June 2026." The filing's own footnote reads: **"Data provided by the Rain
  Foundation."**
- **DefiLlama, fetched 2026-08-04:** protocol volume of **$40.99 over the trailing 30 days**, $4.99
  over 7 days, $0 over 24 hours. **Cumulative volume since inception: $39.41M.**

The Foundation's single-month claim is roughly **22 times DefiLlama's entire tracked lifetime
volume**. The fee record corroborates DefiLlama rather than the Foundation: at the protocol's own
stated 5% fee, $860M of monthly volume implies roughly $43M of monthly fees; DefiLlama recorded
**$76** in trailing-30-day fees and **$1.35M cumulative since inception**.

**In fairness to Rain, and stated plainly:** a DefiLlama adapter *can* break, and readings of $0/$4.99/
$40.99 look like an adapter that has stalled. I cannot rule that out. But two things cut against
dismissing it. First, DefiLlama's quarterly income statement for Rain shows a coherent multi-quarter
series — $228 (Q1 2025), $727 (Q2 2025), $4.1K (Q3 2025), $299.06K (Q4 2025), $114.17K (Q1 2026),
$805.86K (Q2 2026), $126.58K (Q3 2026 partial) — which is not the signature of an adapter that never
worked. Second, even taking the *cumulative* lifetime figure at face value and ignoring the recent
zeros, one claimed month still exceeds it 22-fold.

**I could not resolve this.** No independent source corroborates the $860M. The only attribution the
SEC filing offers is the Rain Foundation itself — which is to say, the counterparty that granted the
filer an option over 23.6% of the token supply.

**5. The Foundation's own forward targets are internally incoherent with its own current claim.**

Via the same Enlivex 6-K, the Rain Foundation projects protocol volume of **$1.3B in 2027**, $12B in
2028 and $33B in 2029, with net buy-and-burn fees of $24M / $216M / $600M. But if July 2026 alone
did $860M, the full-year 2027 "target" is about six weeks of the claimed current run-rate. Either
the $860M is cumulative-since-inception (which contradicts "622% month-over-month growth in July"),
or the forward targets describe a collapse. Both readings cannot be true.

**6. Reported daily token volume disagrees across venues, and DefiLlama disagrees with itself.**

CoinGecko $20.43M, CMC $29.1M, DefiLlama $19.53M — a 49% spread. DefiLlama's own page breaks $19.53M
into "$16.1M CEX + $7.1M DEX", which sums to $23.2M, not $19.53M.

**7. The aggregators do not agree on this token's own price history.** All-time low differs by a
factor of 5.6: CoinGecko $0.002221 on 2025-09-14 versus CMC $0.0003934 on 2025-09-09. All-time high
carries **four** different values across three sources — $0.01656 (CoinGecko statistics block,
06-29), $0.01614 (CoinGecko FAQ, same page, same day), $0.01638 (CMC, 06-29) and $0.016 (DefiLlama,
06-22). For a token barely eleven months old, on a chain with a public explorer, this should be a
solved problem.

### What could NOT be established at all

- **A provenance warning that applies to several "facts" above.** The team names, the Panama
  incorporation, the "Gems Launchpad" distribution and the Hacken audit all come from CoinGecko's
  project-description block. On every major aggregator that block is **submitted by the project and
  not independently verified** by the aggregator. For this asset, that means the issuer is the
  original source for most of what is "known" about the issuer. Treat those items as *claimed*, not
  established.
- **Who actually runs it.** CoinGecko's project description names a Rain Foundation in Panama City,
  Panama, founded by Lorena Del Carmen Diaz Moreira, with Ana Gabriela De Leon Macias as President
  and Rebeca Isabel Munoz Arosemena as Secretary. **I could not independently verify any of these
  individuals** — no confirmed professional history, prior projects, or engineering track record.
  A Panamanian foundation with a three-officer board is a structure equally consistent with a
  legitimate offshore entity and with nominee directors. I am not asserting either. There is a GitHub
  organisation (`rain1-labs`) but I did not verify commit history or contributor identity. **No named,
  doxxed engineering team was established.**
- **What "Presale (Miners…)" means.** The 1% presale bucket is labelled "Miners, Private Sale,
  Refund". A trillion-token supply, an Aug/Sep 2025 launch, and a "Miners" allocation are *consistent*
  with a tap-to-earn or mobile-mining distribution phase — but **I found no evidence that such a phase
  existed, and I am not going to assert one because the pattern fits.** Unverified.
- **Whether the buy-and-burn actually executes on-chain.** DefiLlama models revenue as "Platform Fees
  are used to buy back and burn RAIN Token," but I did not locate a burn address, a cumulative burn
  total, or on-chain burn evidence. **The mechanism is documented; its execution is unverified.**
- **Real usage.** No daily-active-user count, market count, or open-interest figure from an
  independent source. TVL of $23.23M and lifetime fees of $1.35M are the only independent activity
  signals I found, and both are tiny.
- **Independent journalism.** I found **no reported, independently-sourced journalism about Rain
  Protocol** — no investigation, no feature, no critical coverage. What exists is aggregator listing
  pages, price-prediction SEO content, and issuer press releases. Absence of critical coverage is not
  evidence of wrongdoing; it does mean **no third party has stress-tested any of the claims above.**
- **Wash-trading allegations.** I did not find specific documented allegations. I also did not find
  anyone who had looked.

## What it is, mechanically

Rain describes itself as decentralised prediction-market infrastructure on Arbitrum — a
"builder-first construction kit" of SDKs and APIs for launching custom forecasting platforms, marketed
as the "Uniswap of prediction markets."

Stated design (from CoinGecko's project description and CoinDesk, neither independently verified
against the contracts):

- **Market types.** Public markets, resolvable by an integrated AI oracle, and Private markets that
  are invitation-only with the creator acting as resolver.
- **Pricing.** An AMM mechanism prices outcomes by the proportion of liquidity allocated to each.
  Note this is *not* an order book, and not a Polymarket-style CLOB.
- **Resolution.** Public markets settle via "Olympus AI"'s oracle agent. Disputes go to an
  arbitration layer described as an AI "judge" plus human oracles.
- **Settlement currency.** Markets trade in USDT; RAIN itself is the utility and governance token.
- **Token gating.** Holding RAIN grants "Trading Power" that caps how much of a user's balance can be
  deployed in markets — so the token is a usage prerequisite, not merely a governance claim.
- **Fee flow.** 5% per trade: 2.5% to participants, 2.5% to buy back and burn RAIN. Up to 10% of the
  burned amount may be re-minted for team and ecosystem.
- **Governance.** A Rain DAO, described as voting on fees, oracle rules and funding — "once activated"
  in CoinGecko's phrasing, which implies it is not.
- **Audits.** Smart contracts audited by Hacken, per CoinGecko. I did not retrieve the report.

An "AI judge" resolving disputed real-money outcomes is a novel and untested oracle design. Whatever
its merits, it is not a battle-tested resolution mechanism and should not be assumed to behave like
UMA's optimistic oracle or a human-committee resolver under adversarial conditions.

**The gap between the description and the measured protocol is the story.** This is presented as
infrastructure for a category with a genuine bull case. DefiLlama measures $23.23M of TVL, $1.35M of
cumulative lifetime fees, and $76 of fees in the last month. On DefiLlama's own leaderboard Rain
ranks **#2 by TVL among 110 prediction-market protocols**, in a category totalling $385.58M — which
tells you more about how small the on-chain prediction-market category is than about Rain.

## Supply, issuance, float and unlocks

**Allocation** (Tokenomist via CoinGecko, 2026-08-04):

| Bucket | Share | Tokens (approx.) |
|---|---|---|
| Marketing & Development Fund | 20% | 230.0B |
| Reserve & Treasury | 20% | 230.0B |
| Ecosystem Growth & Staking | 15% | 172.5B |
| Launchpad, Exchanges & Liquidity Providers | 15% | 172.5B |
| Contributors, Advisors & Strategic Partners | 10% | 115.0B |
| Team | 10% | 115.0B |
| Strategic Sale | 9% | 103.5B |
| Presale (Miners, Private Sale, Refund) | 1% | 11.5B |

**Only 10% of supply was ever sold** — 9% strategic sale plus 1% presale. The other 90% was allocated
to the team, contributors, treasury, ecosystem and launchpad/exchange buckets. Distribution was via
"Gems Launchpad" (CoinGecko); I could not establish the raise size or offering price.

**Who holds what, as best as the record allows:**

| Bucket | Tokens | % of total supply | Value at $0.01244 |
|---|---|---|---|
| Sablier vesting contract `0x467D…` | 446,716,886,628 | 38.9% | $5.56B |
| Reserve & Treasury (counted as *circulating* by CoinGecko) | 230,000,000,000 | 20.0% | $2.86B |
| Enlivex Ltd. (Nasdaq: ENLV) | 78,819,756,062 | 6.9% | $980M |
| Claim vesting contract `0xc41A…` | 8,531,234,195 | 0.7% | $106M |
| **Subtotal** | **~764.1B** | **~66.4%** | **~$9.5B** |

**These buckets may overlap** — the aggregators do not disclose enough to net Enlivex's holding
against the vesting contracts. Taking the subtotal at face value leaves roughly 385.8B tokens (33.6%,
~$4.8B) outside locks, treasury and the single largest disclosed holder — and that is an *upper bound*
on genuine public float, not an estimate of it.

**The Enlivex option — the most consequential supply fact, and it is in an SEC filing.**

Per Enlivex's Exhibit 99.1 (SEC EDGAR, dated as of 2026-05-26):

> "Enlivex holds an option to acquire up to **271,372,418,179 RAIN tokens from the Rain Foundation, at
> a purchase price of $0.0033 per RAIN token**. The option's expiration date is **Dec. 31, 2027**. The
> option's intrinsic value was $2.23 billion as of May 26, 2026."

Unpack that:

- 271.37B tokens is **23.6% of total supply**.
- The strike, $0.0033, is **73.5% below** the 2026-08-04 market price of $0.01244. The market trades
  at **3.77x the price at which the issuer has contracted to sell nearly a quarter of the supply.**
- Total consideration if exercised: ~$896M, for tokens worth ~$3.38B at market.
- Combined with Enlivex's existing 78.8B, **one Nasdaq-listed company holds or controls roughly 30.5%
  of RAIN's total supply.**

This is a documented, dated statement of what the issuer itself considers an acceptable price for a
quarter of the token. It is the single most informative valuation datapoint available, and it is far
below the market.

**Unlock pace.** The schedule extends into late 2027 (Tokenomist). Analyst Stacy Muur, citing
Tokenomist data in a snapshot carried on BitMart's RAIN page (~July 2026), reported ~40.4B RAIN
unlocking in August 2026 (3.5% of supply) and ~90.1B over August–October 2026, and estimated that
burn offsets only about 3.8% of monthly unlock velocity. **This is second-hand and I could not verify
the underlying schedule directly — treat the specific numbers as indicative.**

**Observed dilution, which is verifiable.** TokenRadar's 2026-05-14 snapshot recorded circulating
supply of 478.4B at $0.0075 (market cap $3.60B). On 2026-08-04, CoinGecko showed 694.6B at $0.01244
($8.64B). That is **+45% supply and +66% price in under three months** — the market cap more than
doubled, and roughly half of that came from issuing tokens rather than from repricing them.

## Turnover and what the market cap actually means

$20.43M of 24h volume against $8.641B of market cap is **0.24% turnover** (CoinGecko, 2026-08-04).

For same-day, same-methodology calibration: **HYPE turned over 2.28%** on 2026-08-04 ($280.8M volume
against $12.34B market cap; **2.52%** on the single-timestamp pull[^turnover-std]). RAIN's turnover is roughly **one tenth** of that.

*A note on a common framing:* RAIN's turnover is sometimes described as "two orders of magnitude below
Bitcoin's." That overstates it. Bitcoin's daily turnover generally runs in the low single-digit
percent — **an approximation, not a figure I fetched or verified in this pass** — which would put RAIN
roughly **one** order of magnitude below, not two. Use the HYPE comparison above instead: it is
same-day, same-source and same-method, and it makes the point without needing a Bitcoin number. The
conclusion does not need exaggerating: 0.24% is dismal on its own.

**But turnover understates the problem, because turnover uses volume — and volume is the wrong
denominator when you want to know whether you can get out. Depth is.**

Summing the ±2% depth columns across every venue in CoinGecko's markets table (2026-08-04). *Column
convention: "−2% depth" is resting bid liquidity — what a seller can hit before price falls 2%.
"+2% depth" is resting ask liquidity — what a buyer can lift before price rises 2%. For an exit
question, the bid side is the one that matters.*

- **Bid side within 2% of mid (−2% column): ≈$294,000**
- **Ask side within 2% of mid (+2% column): ≈$319,000**

Against an $8.641B market cap, the visible bid depth is **0.0034%** of the notional valuation. CMC
reports the same relationship as "Liq/Mkt Cap 0.03%."

Put that next to the disclosed holdings:

- Enlivex's **$980M** position is roughly **3,300 times** the entire visible bid depth across all
  venues combined.
- The Reserve & Treasury bucket that CoinGecko counts as circulating, **$2.86B**, is roughly **9,700
  times** it.
- At $20.43M of daily volume, liquidating Enlivex's position alone would consume **48 days of the
  entire market's volume** — assuming, impossibly, that it were the only participant and that price
  did not move.

**Valuation ratios, computed from DefiLlama figures (2026-08-04):**

- Market cap $8.645B ÷ annualised fees $1.36M = **~6,400x fees**
- Market cap $8.645B ÷ annualised revenue $899,107 = **~9,600x revenue**
- Market cap ÷ TVL = **372x**; FDV ÷ TVL = **616x**
- DefiLlama's own interface surfaces "P/F at 12,075.1x" and "P/S 12,750.2x" (it does not state its
  basis, which is why I computed my own above)

Every basis produces a ratio in the thousands. Whatever the denominator, there is no earnings story
here.

**The protocol treasury is $743.51M and consists of $743.51M of its own token**, $11.91 in major
assets, and **$0 in stablecoins** (DefiLlama, 2026-08-04). A treasury denominated entirely in the
asset it is meant to backstop provides no support in a drawdown — it falls at exactly the rate it
would need to be spent.

**The honest summary.** The market cap is a real price times a real token count. It is not evidence
that $8.6B of value could be realised, and it is not backed by tradeable supply: about two thirds of
supply sits in vesting contracts, treasury, or one disclosed holder; a further 23.6% is under option
to that holder at a 73% discount; and the entire tradeable buffer within 2% of mid is under
$300,000. **Treat the market cap as unreliable and do not use it in any ranking, index weight, or
position-sizing calculation without saying so.**

## What drives the price

Stated honestly: **not protocol usage**, which is measured in tens of dollars per month by the only
independent tracker.

What appears to move it:

1. **Enlivex press releases.** A Nasdaq-listed company issues periodic SEC-filed updates on Rain's
   trading metrics, sourced from the Rain Foundation, alongside a treasury dashboard. This is the
   primary information flow about the protocol, and its author holds ~6.9% of supply plus an option
   over 23.6% more. The incentive alignment is one-directional.
2. **Unlock cadence.** ~45% supply growth in under three months, with the schedule running to late
   2027. Cliffs concentrate pressure; linear vesting supplies steady sell-side flow.
3. **The buy-and-burn narrative**, whose actual scale — if DefiLlama is right about fees — is
   negligible against unlock velocity. Muur's estimate that burn offsets ~3.8% of monthly unlocks is
   in the right order of magnitude given $1.35M of cumulative lifetime fees.
4. **The prediction-markets category narrative.** Polymarket and Kalshi are genuinely large; Rain is
   positioned as a peer. The Rain Foundation announced a "$100 million liquidity commitment" in May
   2026 — $50M USDT plus $50M in RAIN tokens — which Enlivex said made Rain "the third-largest
   prediction market" behind Polymarket (~$450M TVL) and Kalshi, ahead of the FIFA World Cup.
   **DefiLlama's TVL for Rain never approached $100M and stood at $23.23M on 2026-08-04, down 17.7%
   over 30 days.** Either the commitment was not deployed into tracked contracts, or it was not
   deployed. Note also that half of the headline was denominated in the protocol's own token.
5. **Name-collision noise — this is real and documented.** CoinGecko's RAIN page on 2026-08-04 ran the
   headline **"Rain Drops 2.1% Despite Western Union Visa Card Launch in 37 Markets"** under its "Why
   RAIN is moving" module, plus three news items about Western Union and Rain launching a USDPT Visa
   stablecoin card on Solana. **That is a different company** — Rain, the card-issuing fintech — with
   no relationship to Rain Protocol on Arbitrum. A major aggregator is attributing this token's price
   movement to news about an unrelated business that happens to share its name. If the aggregator
   cannot keep them apart, neither will retail flow, nor will a naive news-sentiment signal.

## Market structure and liquidity

Eleven exchanges, thirteen markets. Full top-ten table (CoinGecko, 2026-08-04):

| # | Venue | Type | Price | Spread | +2% depth | −2% depth | 24h vol | Share |
|---|---|---|---|---|---|---|---|---|
| 1 | HTX | CEX | $0.01241 | 0.19% | $28,573 | $23,498 | $6.07M | 22.56% |
| 2 | BloFin | CEX | $0.01238 | 0.57% | $1,809 | $3,919 | $3.84M | 14.28% |
| 3 | BingX | CEX | $0.01238 | 0.41% | $38,028 | $29,424 | $2.61M | 9.72% |
| 4 | **BitMart** | CEX | **$0.01374** | 0.83% | $2,916 | $764 | $2.54M | 9.28% |
| 5 | MEXC | CEX | $0.01241 | 0.20% | $28,843 | $32,031 | $2.02M | 7.52% |
| 6 | Uniswap V3 (Arbitrum) | DEX | $0.01242 | 0.60% | $9,762 | $9,733 | $1.72M | 6.40% |
| 7 | Gate | CEX | $0.01243 | 0.01% | $28,706 | $25,220 | $1.36M | 5.04% |
| 8 | GroveX | CEX | $0.01241 | 0.46% | $147,726 | $146,666 | $1.25M | 4.65% |
| 9 | Bitrue | CEX | $0.01238 | 0.43% | $4,392 | $2,322 | $1.13M | 4.19% |
| 10 | KuCoin | CEX | $0.01242 | 0.19% | $28,615 | $20,360 | $0.24M | 0.88% |

Observations that matter:

- **No tier-1 venue lists it.** No Binance, no Coinbase, no Kraken, no OKX, no Bybit, no Upbit. Every
  listing is a tier-2/3 CEX plus one DEX pool. That is a market-structure fact about a nominal top-20
  asset, and it is unusual.
- **The BitMart row is flagged by CoinGecko itself** as "Inactive — No trades in the last 3 hours" and
  "Anomaly — Trading price or volume is an outlier against the average," with a last-updated timestamp
  of **7 days ago**. Its price, $0.01374, is **roughly 10–11% above** every other venue in the table
  (which quote $0.01238–$0.01243). Yet it is still counted as 9.28% of reported 24h volume. The
  conclusion is that **BitMart's RAIN quote is stale and does not arbitrage against the rest of the
  market** — roughly 9% of RAIN's headline volume comes from a venue whose price is disconnected.
  (A separate BitMart page snapshot circulating in search results shows a price ~20% *below* the
  other venues, i.e. the same disconnection in the opposite direction; I did not fetch that page, so
  treat it as suggestive only. The fetched, aggregator-flagged anomaly above is sufficient on its
  own.)
- **Depth is concentrated in an odd place.** GroveX — a small venue supplying 4.65% of volume —
  carries roughly $147k on each side, which is **46% of all visible ask-side depth and 50% of all
  visible bid-side depth across every venue combined**. The venue with the most volume (HTX, 22.56%)
  carries $28.6k. Depth and volume do not correlate, which is itself a warning sign about the quality
  of reported volume — and it means half your theoretical exit route runs through a single small
  exchange.
- **BloFin shows $3.84M of 24h volume on $1,809 of +2% depth** — a volume-to-depth ratio of over
  2,100x. Draw your own conclusion; I am not alleging wash trading, because I did not verify it, but
  the ratio is not what an organic book looks like.
- **Exit reality.** With ~$294k of visible bid depth, a $300k market sell would move price more than
  2%. A $3M sell has no visible book at all. Position sizing must be driven by depth, not by the
  $20M volume headline and certainly not by the $8.6B market cap.

## Known failure modes for traders

1. **The market cap is not a liquidity claim, and index/ranking systems will mislead you.** A #14
   CoinGecko rank places RAIN beside genuinely liquid top-20 assets. Its tradeable buffer is roughly
   three orders of magnitude thinner. Any screen, index weight, or "top 20 by market cap" universe
   that includes RAIN is silently including something structurally different from its neighbours.
2. **The Enlivex option is a permanent, dated overhang.** 271.37B tokens (23.6% of supply) exercisable
   at $0.0033 until **2027-12-31**. Every dollar of price appreciation above $0.0033 increases the
   incentive to exercise, and the resulting tokens would face a book with under $300k of depth. This
   is the dominant supply risk and it is disclosed in a US securities filing — there is no ambiguity
   about its existence.
3. **Reflexivity between ENLV equity and the RAIN token.** Enlivex's own risk factors state it
   plainly: "the risk that the price and liquidity of the Company's ordinary shares may be correlated
   with the price or liquidity of the digital assets it holds." The token's largest holder is a
   micro-cap biotech whose equity is now a levered proxy for the token, and the token's most active
   promoter is that same company. If ENLV needs liquidity — it funded the treasury with a $212M
   private placement and $21M of convertible debt — the sale hits a market with $294k of depth.
4. **Reported volume includes at least one stale, disconnected venue** (BitMart, ~9% of the total).
   Any volume-based signal, liquidity filter, or VWAP built on aggregated RAIN data inherits that
   contamination.
5. **Aggregator data is unreliable for this asset specifically.** Two ranks 187 places apart. Two
   circulating supplies on one page. An all-time low that differs by 5.6x. News about a different
   company attributed to this one. **Do not build anything automated on RAIN aggregator data without
   per-field validation.**
6. **The information monopoly.** The only substantive flow of operating metrics comes from the
   Foundation, relayed by its largest optionholder, with no independent verification and no
   journalism. When the sole source of good news is a party holding 30% of supply, the base rate for
   that news being conservative is low.
7. **Novel, untested resolution.** An AI oracle plus an AI "judge" settling real-money outcomes has no
   adversarial track record. Prediction markets fail at resolution, not at matching, and this
   resolution layer has not been stress-tested publicly.
8. **A treasury denominated entirely in its own token** ($743.51M of RAIN, $0 stablecoins) provides no
   drawdown support.
9. **No fixed max supply.** The mint-10%-of-burns mechanism means the "1.15T max supply" displayed by
   every aggregator is not a hard cap (CoinDesk).
10. **Jurisdictional opacity.** A Panamanian foundation with unverifiable officers, a token gating
    real-money prediction markets, and no tier-1 exchange willing to list it. Whatever the reason for
    that last fact, tier-1 listing desks conduct diligence that this asset has not publicly passed.

## For this backtester

**RAIN is not listed on Coinbase and cannot be retrieved by this project's fetcher at all.**

- **No Coinbase listing exists** — not spot, not on Coinbase International, not on Coinbase Advanced.
  CoinGecko's full venue list for RAIN (11 exchanges, 13 markets, 2026-08-04) contains no Coinbase
  entry. A Coinbase-API OHLCV request for a `RAIN-USD` product will fail.
- **A coinbase.com price page is not a listing.** Coinbase publishes informational price pages for
  assets it does not trade. If you find `coinbase.com/price/rain`, that is a content page, not a
  tradeable product, and its existence must not be taken as evidence of fetchability.
- **The ticker `RAIN` is dangerously ambiguous.** CoinGecko alone carries Rain Coin, Precipitate.ai
  (RAIN), Raini (RAINI), Rain by Virtuals (RAIN), Rainmaker Games (RAIN), and this Rain Protocol
  (RAIN). Separately, there is Rain the card-issuing fintech (the Western Union partner) and Rain the
  MENA exchange, neither of which is this token. **A symbol-keyed fetcher is unsafe for `RAIN` on any
  venue.** If you ever need to identify this asset, key on the contract address
  `0x25118290e6A5f4139381D072181157035864099d` on Arbitrum, or the CoinGecko API id `rain`, or the CMC
  UCID `38341` — never on the symbol.
- **If you obtain data anyway, it is not usable as-is.** The only venues are tier-2/3 CEXs and one
  Uniswap V3 pool. Roughly 9% of aggregated volume comes from a venue whose last print was 7 days
  stale and 10.6% off-market. There is under $300k of ±2% depth in total. Any backtest that assumes
  fills at mid, or that sizes positions off market cap or off the volume headline, will produce
  results that are unattainable in practice by a wide margin.
- **Practical recommendation.** Exclude RAIN from the tradeable universe, and if it appears in a
  market-cap-ranked screen, exclude it explicitly with a comment pointing at the depth figure rather
  than letting it fail silently at fetch time.

## Sources

Fetched 2026-08-04 unless noted. Load-bearing figures were taken from fetched pages, not from search
snippets.

**Primary / regulatory**

- Enlivex Ltd. (Nasdaq: ENLV), **SEC Form 6-K filed 2026-07-30**, Exhibit 99.1, "Enlivex Treasury
  Portfolio Update: RAIN Trading Volume Reaches $860MM, 622% Month-Over-Month Growth in July vs June"
  — the $860M figure, the 622% growth claim, the Rain Foundation forward targets, and the footnote
  "Data provided by the Rain Foundation."
  https://www.sec.gov/Archives/edgar/data/1596812/000121390026083074/ea0299702-6k_enlivex.htm
- Enlivex Ltd., **SEC Exhibit 99.1** (as of 2026-05-26), "Rain Protocol Jumps Into Top Three Global
  Prediction Markets…" — 79,568,550,005 RAIN held (~$919M), **the option over 271,372,418,179 RAIN at
  $0.0033 expiring 2027-12-31** with $2.23B intrinsic value, and the Rain Foundation's $100M liquidity
  commitment. https://www.sec.gov/Archives/edgar/data/1596812/000121390026061243/ea029224001ex99-1.htm
- Enlivex press release (2026-03-24), "$21 Million Debt Financing … and $20 Million Share Repurchase
  Program" — convertible at $2.69175/share, "a 264% premium to the Nasdaq closing price."
  https://investors.enlivex.com/press-releases/enlivex-announces-21-million-debt-financing-decentralized-prediction-markets-rain-token-related-updates-and-20-million-share-repurchase-program/
- FT market announcements (as of 2026-05-27) — same 79,568,550,005 token count valued at ~$1.16B,
  one day after the $919M figure above.

**Aggregators (fetched pages)**

- DefiLlama — Rain protocol: TVL $23.23M, fees 30d $76, revenue 30d $46.24, protocol volume 30d
  $40.99, cumulative volume $39.41M, cumulative fees $1.35M, treasury $743.51M in own tokens,
  quarterly income statement, adapter methodology and GitHub links, prediction-market category
  ranking. https://defillama.com/protocol/rain
- CoinGecko — Rain (RAIN) coin page: price, the two conflicting circulating-supply figures, the
  supply-derivation showing the Sablier and Claim vesting deductions, allocation chart, full markets
  and depth table with the BitMart anomaly flags, the Enlivex treasury row, the Rain Foundation /
  Panama project description, and the Western Union news misattribution.
  https://www.coingecko.com/en/coins/rain
- CoinMarketCap — Rain page: **rank #201** beside an $8.64B market cap, TVL $23.22M, MC/TVL 372.13,
  Liq/Mkt Cap 0.03%, 170.2K holders, UCID 38341, and an all-time low of $0.0003934 (2025-09-09) that
  conflicts with CoinGecko's. https://coinmarketcap.com/currencies/rain/
- CoinDesk asset page — the 5% fee split, mint-10%-of-burns (hence no fixed max supply), "Trading
  Power" gating, the vesting-bucket description, and a circulating-supply estimate of "roughly
  230–240 billion RAIN (around one fifth of total supply)" that conflicts with every other source.
  https://www.coindesk.com/price/rain
- Tokenomist — vesting schedule extending into 2027, linear vesting for the Marketing & Development
  Fund, cliff mechanisms elsewhere. https://tokenomist.ai/rain
- TokenRadar snapshot dated 2026-05-14 — price $0.00751668, market cap $3.60B, circulating
  478,417,328,746 — the baseline for the observed-dilution calculation. https://tokenradar.co/rain
- BitMart RAIN page (2026-07-25 snapshot) — carries the Tokenomist/Stacy Muur unlock commentary
  (~40.4B August 2026, ~90.1B August–October 2026, burn offsetting ~3.8% of monthly unlock velocity)
  and shows a price 20%+ away from other venues. https://www.bitmart.com/price/rain

**Project**

- rain.one and whitepaper.rain.one (referenced by the aggregators; not independently audited here).
- Arbiscan token page: https://arbiscan.io/token/0x25118290e6A5f4139381D072181157035864099d
- GitHub organisation `rain1-labs` (existence noted via DefiLlama; contents not verified).

**Not found**

No independent investigative journalism on Rain Protocol was located. No on-chain burn evidence, no
verified identities for the named Foundation officers, no user or open-interest metrics from any
source other than the Rain Foundation itself.

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
