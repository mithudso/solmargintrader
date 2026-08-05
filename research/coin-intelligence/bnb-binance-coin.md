---
name: bnb-binance-coin
description: Trader-facing reference for BNB (Binance Coin) — exchange-token mechanics, the Auto-Burn supply schedule, extreme address concentration, venue and issuer risk, and what its 0.73% headline turnover really means for sizing and backtesting.
---

# BNB (Binance Coin)

> Educational reference. Not investment advice. Every figure below carries a date because
> all of them decay — prices and volumes within hours, supply within a quarter, legal and
> listing status within weeks. **Re-pull anything you intend to act on.**

## Snapshot (AS OF 2026-08-04)

| Field | Value | Source / date |
|---|---|---|
| Price | $602.76 | CoinGecko, 2026-08-04 (user-supplied snapshot) |
| Price | $603.05 | CoinGecko API, retrieved 2026-08-05 03:03:59 UTC[^cg-bnb] |
| Market cap | ~$80.3B / $80,311,028,264 | CoinGecko, 2026-08-04 / API 2026-08-05[^cg-bnb] |
| 24h volume | ~$0.59B / $608,516,445 | CoinGecko, 2026-08-04 / API 2026-08-05[^cg-bnb] |
| Headline turnover (24h vol ÷ mcap) | **0.73%** (comparable[^turnover-std], lowest of the ten bar RAIN) / 0.758% on the later 2026-08-05 API pull | derived from the two rows above |
| Circulating supply | 133,164,808.15 BNB | CoinGecko API, 2026-08-05[^cg-bnb] |
| Total supply | 133,164,808.15 BNB (identical to circulating) | CoinGecko API, 2026-08-05[^cg-bnb] |
| Max / genesis supply | 200,000,000 BNB | CoinGecko API, 2026-08-05[^cg-bnb]; BNB Chain burn program[^bnb36] |
| All-time high | $1,369.99 on 2025-10-13 | CoinGecko API, 2026-08-05[^cg-bnb] |
| Drawdown from ATH | −56.0% | derived, 2026-08-05 |
| CoinGecko rank | #5 by market cap | CoinCarp page header, retrieved 2026-08-05[^coincarp] |

**Figures decay.** The price/volume rows above are a single instant. The supply row moves in
discrete ~1.37–1.62M BNB steps every quarter (next expected mid-October 2026). The
concentration and venue tables below are point-in-time chain and API reads. Treat this whole
document as stale after roughly one quarter, and treat the "For this backtester" section as
stale the moment Coinbase changes BNB's listing status.

---

## What it is, mechanically

BNB is a **centralized-exchange token that became a Layer-1 gas token**. Two identities,
one asset, and the tension between them explains most of its behaviour.

1. **Exchange-utility token (2017–present).** BNB launched in a July 2017 ICO with a genesis
   supply of 200,000,000 tokens, originally as an ERC-20 on Ethereum (contract
   `0xB8c77482e45F1F44dE1745F52C74426C631bDD52`, still listed as a legacy contract)[^coincarp].
   Its original purpose was a discount on Binance exchange trading fees, plus VIP-tier
   qualification and access to token-launch programs (Launchpool, Megadrop). *The current
   headline discount percentage is **unverified** in this pass — check Binance's live fee
   schedule before quoting a number.*
2. **Native gas asset of BNB Smart Chain (BSC).** BNB pays transaction fees on BNB Chain, is
   delegated to validators for staking, and is the base collateral asset across the chain's
   DeFi stack (PancakeSwap, Venus). VanEck cited Artemis data putting BNB Chain at **>14
   million transactions/day and >2.5 million daily active users**, with >$16B stablecoins and
   $3.6B tokenized RWAs on-chain (2026-05-28)[^coindesk-etf]. Those are vendor-cited figures,
   not independently verified here.

The mechanically important consequence: **BNB is not a neutral protocol asset.** Its supply
schedule is administered by an entity (the BNB Foundation / BNB Chain), its dominant trading
venue is that entity's affiliated exchange, and both its fee-discount utility and its
launch-platform utility are revocable business decisions. That is a different risk object from
BTC or ETH, and the general warning in this reference set's shared crypto-market-structure
corpus[^corpus-crypto] — that a CEX balance is "a liability on the exchange's balance sheet" —
extends here to the *asset itself*, not just to where you keep it.

---

## Supply, issuance and float

### There is no issuance. There is only destruction.

BNB has **no inflation, no block reward, and no staking emission**. The supply path runs one
way: 200,000,000 at genesis, targeting **under 100,000,000**[^bnb36][^academy]. Two independent
burn mechanisms drive it.

**1. Quarterly Auto-Burn (the large one).** Since replacing the original discretionary
"burn from exchange profits" scheme, the burn size is formula-driven and, per BNB Chain,
"independent of the Binance centralized exchange"[^bnb34]:

```
B = N / (100 × P) × K

B = BNB to burn this quarter
N = blocks produced on BNB Chain during the quarter
P = average BNB price in USD over the quarter
K = constant anchor, initially 1,000
```
Source: Binance Academy, retrieved 2026-08-05[^academy].

Note the sign: **price sits in the denominator, so a lower BNB price produces a larger burn.**
The mechanism is counter-cyclical by construction — it destroys more supply into weakness. Do
not model it as a bullish catalyst that scales with price.

**2. BEP-95 real-time burn (the small, continuous one).** Activated **November 2021**; burns a
share of gas fees block-by-block. The **initial** ratio was 10% of gas fees, adjustable by
validator governance[^academy]. *The **current** ratio is **unverified** — treat 10% as the
documented starting value, not as today's parameter.*

### Burn ledger

| Event | Date | BNB destroyed | Total supply after | Source |
|---|---|---|---|---|
| 34th quarterly burn | ~Jan 2026 | ~1.37M (~$1.28B) | 136,361,374.34 | BNB Chain blog[^bnb34] |
| 35th quarterly burn | 2026-04-15 | ~1,569,307 | ~134,786,916 | Binance Academy[^academy] |
| 36th quarterly burn | 2026-07-15 | 1,615,827.795 (~$932M) | 133,166,127.91 | BNB Chain blog / press[^bnb36] |
| Live supply | 2026-08-05 | — | 133,164,808.15 | CoinGecko API[^cg-bnb] |

**Note on the ledger deltas.** The supply drop between each named Auto-Burn event and the next
is consistently ~5,000 BNB larger than the quarterly burn amount stated for that event (e.g.
136,361,374.34 → 134,786,916 is a 1,574,458 BNB drop against a stated 35th-burn size of
~1,569,307). The 21-day gap between the 36th burn and the live 2026-08-05 read shows the same
pattern at smaller scale: 1,319.76 BNB destroyed with no Auto-Burn event in that window. Both
are consistent with the continuous BEP-95 real-time burn described above running between
snapshots — the ledger is not internally contradictory, but the two burn mechanisms are not
separated out numerically here.

**Cumulative destroyed (derived):** 200,000,000 − 133,164,808 = **66,835,192 BNB, or 33.4% of
the genesis supply**, as of 2026-08-05. Remaining to the 100M target: **~33.2M BNB**. At the
observed ~1.37–1.62M/quarter pace, Binance Academy's own estimate is **five to six more years**
(as of April 2026)[^academy] — and because the formula burns more when price is low, the
schedule accelerates in bear markets and decelerates in bull markets.

### The float caveat that matters more than the burn

CoinGecko reports **circulating supply = total supply = 133,164,808.15**[^cg-bnb]. There is no
locked-vesting discount, no escrow, no foundation carve-out in that number. **Every BNB in
existence is counted as circulating.** That is the single most important input to the turnover
puzzle below, and the next section shows why it is wrong as a description of tradable float.

---

## Concentration and real float

### The finding

**BNB's headline turnover is low because the denominator is wrong, not because the asset is
illiquid.** Five addresses hold **71.9% of the "circulating" supply**, and at least two of
them hold BNB that cannot trade at all.

### On-chain evidence (primary)

Native BNB balances read directly from a BNB Smart Chain RPC node (`bsc-rpc.publicnode.com`),
**block 114,089,029, 2026-08-05**[^bsc-rpc]:

| Address | BNB | % of 133.16M supply | Label |
|---|---:|---:|---|
| `0xff3f4285…18ac4d3` | 29,888,000 | 22.44% | **unlabelled**; note the exactly-round balance |
| `0x0000…00001004` | 25,972,154 | 19.50% | BSC Token Hub — cross-chain bridge system contract |
| `0xbe0eb53f…404d33e8` | 17,195,730 | 12.91% | Binance-labelled exchange wallet |
| `0x0000…0000dead` | 16,493,377 | 12.39% | burn address (provably unspendable) |
| `0xf977814e…7441acec` | 6,179,166 | 4.64% | "Binance 8"-labelled exchange wallet |
| **Sum of five** | **95,728,428** | **71.89%** | |

The `0xbe0eb53f…` and `0xf977814e…` labels are **explorer-community attributions**, widely used
but not independently confirmed here — treat the *label* as unverified and the *balance* as
verified. The `0xff3f4285…` address is a ~$18B position with no public label found in this
pass; **whose it is could not be verified.**

A third-party rich list is directionally consistent: CoinCarp reports **top-10 holders 75.63%,
top-20 77.79%, top-50 80.26%, top-100 82.07%** (retrieved 2026-08-05; the page's own
circulating figure of 133,164,809 BNB confirms the snapshot is current)[^coincarp]. Earlier
secondary reporting put "top 11 wallets over 55%" with a single whale at 19.9% (August
2025)[^ainvest] — consistent in character, different in vintage and method.

### Re-computing turnover on defensible float

Same 24h volume ($608,516,445), three denominators:

| Denominator | Float (units) | Float ($) | 24h turnover |
|---|---:|---:|---:|
| CoinGecko "circulating" (all supply) | 133,164,808 BNB | $80.3B | **0.76%** |
| Less burn address + bridge contract only | 90,699,277 BNB | $54.7B | **1.11%** |
| Less all five top addresses | 37,436,380 BNB | $22.6B | **2.70%** |
| *BTC circulating supply, for reference* | 20,065,943 BTC | $1,291.6B | *1.80%*[^cg-btc] |

Derived 2026-08-05 from the CoinGecko and RPC reads above.

**Conclusion: on any float definition that excludes provably immobile coins, BNB's turnover
is normal-to-high, not thin.** Strip only the burn address and the bridge contract — the two
you can defend on mechanical grounds alone — and BNB (1.11%) sits in the same neighbourhood as
BTC (1.80%). Strip the exchange and unlabelled mega-wallets too and BNB (2.70%) turns over
*faster* than BTC. The 0.7% headline is a **denominator artifact of counting locked and
immobile supply as circulating**, and any screen that ranks assets by volume/market-cap will
mis-rank BNB badly.

### But the real liquidity problem is somewhere else

Fixing the denominator does not make BNB liquid where you can reach it. See the next two
sections: the numerator is spread across venues of wildly varying quality, and the US-reachable
book is a rounding error.

---

## What drives the price

BNB is the closest thing in large-cap crypto to a **single-company equity proxy**. Five drivers,
roughly in order of weight:

**1. Binance's commercial fortunes.** Fee-discount demand, VIP tiers, and Launchpool access all
scale with Binance's volume and user base. Binance still runs the largest global spot and perps
book[^corpus-crypto]. If Binance's share erodes, the utility bid erodes with it. There is no
mechanism separating the two.

**2. The Auto-Burn formula, counter-cyclically.** ~1.37–1.62M BNB/quarter across the last three
burns[^bnb36][^bnb34][^academy]; the two of those three burns with disclosed USD notionals ran
~$0.93–1.28B[^bnb36][^bnb34] (the 35th burn's dollar figure was not captured in this pass) —
real, verifiable supply destruction, but the formula *increases* the burn when price falls.
Model it as a supply floor, not a rally trigger.

**3. Regulatory and enforcement exposure — the record, dated.** State these as facts; they are
price-relevant and frequently mis-summarised:

- **2023-06-05** — SEC filed its civil enforcement action, *SEC v. Binance Holdings Ltd., BAM
  Trading Services, BAM Management US Holdings, and Changpeng Zhao*, No. 1:23-cv-01599
  (D.D.C.)[^sec-binance].
- **2023-11-21** — Binance and CZ pleaded guilty to federal charges in a ~$4.3B resolution;
  Binance agreed to retain an **independent compliance monitor for three years** and to
  remediate its AML and sanctions programs[^doj].
- **2025-02-13** — the D.D.C. court granted a 60-day stay of the SEC litigation pending the
  agency's crypto task force[^law-com]. *(The local corpus records the SEC case as "dropped in
  February 2025"[^corpus-crypto] — that is the **stay**, not the dismissal. Corrected below.)*
- **2025-05-29** — the SEC filed a **joint stipulation dismissing the action with prejudice**
  against all defendants including Zhao (SEC Litigation Release No. 26316). The SEC stated the
  dismissal was "in the exercise of its discretion and as a policy matter" and did "not
  necessarily reflect the Commission's position on any other litigation"[^sec-binance].
- **2025-10-23** — President Trump pardoned Changpeng Zhao, who had served a four-month
  sentence; the pardon drew formal objection letters from members of Congress dated
  2025-10-28[^senate][^factcheck].

Residual exposure a trader should still price: the DOJ resolution's ongoing compliance
obligations and monitorship, jurisdictional restrictions (Binance.US is a separate, reduced
entity; OKX exited the US)[^corpus-crypto], and non-US regimes (MiCA compliance in the EU). One
secondary source reports that a monitor cleared Binance's KYC remediation as of March 2025
**with sanctions screening still under review** at that time, and that the settlement carries a
five-year compliance window[^eco] — **unverified**, and it is a secondary source; confirm
against DOJ filings before relying on it, including on the open sanctions-screening item.

Separately, per the local corpus, a **SEC/CFTC joint interpretation published 2026-03-17**
names 18 major cryptocurrencies as digital commodities[^corpus-crypto]; *whether BNB is among
them was **not confirmed** in this pass* — check the interpretation's own text before relying
on BNB's inclusion or exclusion for a classification thesis.

**4. US access expansion.** BNB spent years fenced out of US-regulated wrappers and only
recently got them: Coinbase roadmap 2025-10-15, listing confirmed 2025-10-22[^coindesk-cb];
**VanEck BNB ETF (VBNB) launched 2026-05-28 on Nasdaq**, 0.39% sponsor fee, Anchorage Digital
Bank custodian[^vaneck-pr][^coindesk-etf]. Access, however, is not demand — see the anaemic
uptake numbers in "Market structure".

**5. Beta to Bitcoin.** Measured below. BNB does not decouple.

Not a driver, despite frequent claims: the 100M "halving" target. It is a slow asymptote
five-plus years out, already fully disclosed, and the market has had nine years to price it.

---

## Market structure and liquidity

### Where BNB actually trades

CoinGecko ticker data, top 100 tickers totalling $617.6M, retrieved 2026-08-05[^cg-tick-bnb]:

| Venue | 24h USD volume | Share |
|---|---:|---:|
| Binance | $113,740,081 | 18.4% |
| P2B | $33,425,870 | 5.4% |
| GroveX | $32,450,036 | 5.3% |
| XT.COM | $31,608,717 | 5.1% |
| BTCC | $30,577,430 | 5.0% |
| FameEX | $21,415,957 | 3.5% |
| Toobit | $19,738,605 | 3.2% |
| Azbit | $18,273,455 | 3.0% |
| CoinW | $17,851,223 | 2.9% |
| BitMart | $17,032,431 | 2.8% |
| *(ranks 11–~35 omitted)* | | |
| **Coinbase Exchange (BNB/USD)** | **$2,497,477** | **0.4%** |

Coinbase is pulled out of its natural rank (well below 35th by volume) and appended here
because it is the venue this document's backtester section cares about — not because it is
the 11th-largest BNB venue.

Largest single pair: Binance BNB/USDT at $61.2M (9.9% of the total).

**Read this table adversarially.** Binance — the venue with the deepest genuine BNB book and
the most reason to have one — is only 18.4% of reported volume. The next nine venues are
mid-and-small-tier exchanges that collectively report roughly twice Binance's BNB volume
($222.4M vs. $113.7M, 36.0% vs. 18.4% of the top-100 aggregate). The corpus is blunt about
what that usually means: Bitwise (2019) found ~95% of
reported spot volume on unregulated exchanges was fake, and 26 exchanges faked up to 70% of
reported volume[^corpus-crypto]. **A material and unquantified fraction of BNB's $0.59B
headline volume is probably not real.** That cuts the *opposite* way from the float correction
above: the denominator was too big, and the numerator is probably too big as well.

CoinGecko also reports near-identical bid-ask spread values across unrelated venues
(e.g. 0.011656 / 0.011663 on several BNB/USDT books) — an aggregation artifact, so **spread
figures from that source are not used here.**

### Institutional and ETF footprint — small

- **VBNB (VanEck):** total net assets **$2,284,194** with **3,885.166 BNB in trust**, as of
  2026-07-31[^vaneck-fund]. Against Coinbase's own BNB book (below), that is roughly **one
  day** of Coinbase's current 24h BNB volume ($2,497,477) or **about two days** against its
  30-day average (~$1.1M/day) — two months after launch. US ETF demand for BNB is, so far,
  negligible.
- **Corporate treasuries:** CoinGecko tracks 3 institutions holding **686,076 BNB (~$409M,
  0.51% of supply)**; bitcointreasuries.net lists 5 entities holding **688,818.5 BNB
  (~$399M)**, largest CEA Industries at 515,544 BNB (both retrieved 2026-08-05)[^cg-treas][^btreas].
  The two trackers disagree slightly — normal for this data class.

### Structural notes

- No consolidated tape and no NBBO across crypto venues; BNB/USDT on Binance and BNB/USD on
  Coinbase are independent books kept together only by arbitrage[^corpus-crypto].
- 24/7 trading, no scheduled close, no industry-wide circuit breakers on spot[^corpus-crypto].
- Quote-asset fragmentation is real: BNB's second-largest Binance pair is **BNB/USD1**
  ($20.8M/day), a stablecoin distinct from USDT/USDC. Stablecoin issuer risk is not
  interchangeable[^corpus-crypto].

---

## Volatility and correlation

Measured directly from Coinbase Exchange daily bars (`api.exchange.coinbase.com`), close-to-close
log returns, computed 2026-08-05. BNB's Coinbase history begins 2025-10-22, so no window longer
than ~9.5 months is available on this venue.

| Asset | 90d annualised realised vol | 180d | 270d |
|---|---:|---:|---:|
| BNB-USD | 41.2% | 39.2% | 45.5% |
| XRP-USD | 43.5% | 43.7% | 61.0% |
| BTC-USD | 34.8% | 38.8% | 45.5% |

| Pair | 90d ρ | 180d ρ |
|---|---:|---:|
| BNB vs BTC | **+0.730** | **+0.788** |
| BNB vs XRP | +0.691 | +0.756 |
| XRP vs BTC | +0.869 | +0.857 |

Drawdowns over the available Coinbase window (to 2026-08-05):

| Asset | Window | Window high | Last | Drawdown |
|---|---|---:|---:|---:|
| BNB-USD | 2025-10-22 → 2026-08-05 (288 bars) | $1,139.32 | $598.21 | **−47.5%** |
| BTC-USD | 2025-08-21 → 2026-08-05 (350 bars) | $124,720.09 | $64,056.21 | −48.6% |
| XRP-USD | 2025-08-21 → 2026-08-05 (350 bars) | $3.121 | $1.067 | −65.8% |

**Interpretation.** BNB's realised-vol premium over BTC is regime-dependent, not a stable
spread: +18% at 90d (41.2% vs. 34.8%), narrowing to near-parity at 180d (39.2% vs. 38.8%), and
converging at 270d (45.5% vs. 45.5%). That last match was re-verified against the underlying
series at higher precision on 2026-08-05 — BTC 45.483%, BNB 45.481% over the identical
2025-11-09→2026-08-05 window — so it is a genuine coincidence of this window, not a rounding
artifact and not a structural constant. Do not carry it forward as one. BNB is strongly, but not perfectly, correlated with BTC (ρ ≈ 0.73–0.79); at that
range, 1−ρ² puts the idiosyncratic (non-BTC-explained) share of BNB's variance at **~38–47%**.
This document has not decomposed that residual quantitatively — no variance-attribution
analysis was run — but qualitatively it is consistent with the driver list above, and in
particular with *Binance headline risk* as a plausible major contributor, not a diversifying
factor. In a market-wide risk-off, BNB gives you BTC's drawdown with more vol; in a
Binance-specific event, it gives you a move BTC does not. That is the wrong shape of asymmetry
for a diversifier.

Every figure here is measured on a single venue over a bull-to-bear transition (BTC −48.6%
peak-to-current). **These are regime-specific numbers, not stable constants.** Recompute on
your own window.

---

## Known failure modes for traders

1. **Ranking or screening on volume/market-cap.** BNB's 0.73% headline turnover is a
   denominator artifact (locked bridge and burn balances counted as circulating). Any liquidity
   screen using CoinGecko circulating supply mis-ranks it. Use a float you can defend.
2. **Trusting the headline volume number.** ~80% of reported BNB volume sits on venues outside
   the top tier, in a market where fake volume is documented and large[^corpus-crypto]. Size
   against the venue you will actually execute on, not against the aggregate.
3. **Venue concentration risk — you are trading Binance's token, mostly on Binance.** The
   deepest book, the fee-discount utility, the launch-platform utility, and the burn
   administration are all connected to one commercial entity. A Binance-specific shock hits the
   asset's price, the asset's utility, *and* the venue where you would exit, simultaneously.
   That is correlated failure across position, thesis, and exit path.
4. **Issuer concentration risk — the supply schedule is administered, not consensus-bound.**
   The Auto-Burn formula's constant `K` and BEP-95's ratio are governance parameters. They can
   change. BTC's 21M cap cannot.
5. **A single unlabelled address holds ~22% of supply (~$18B).** Its owner could not be
   verified in this pass. Any distribution from it is an overhang you cannot see coming and
   cannot size.
6. **Misreading the Auto-Burn as pro-cyclical.** Price is in the denominator: lower price →
   bigger burn. Traders who model burns as a bullish catalyst that grows with price have the
   sign backwards.
7. **Assuming the 100M target is imminent.** ~33.2M BNB left, ~5–6 years at current
   pace[^academy]. It is not a near-term supply event.
8. **Stale legal summaries.** The SEC action was dismissed **2025-05-29**, not February 2025
   (February was a stay). The DOJ resolution and its compliance obligations are a separate
   matter that did **not** go away with the SEC dismissal. Both facts are routinely conflated.
9. **Assuming a US ETF means US liquidity.** VBNB held $2.28M at 2026-07-31[^vaneck-fund].
   The wrapper exists; the demand does not yet.
10. **Cross-chain bridge exposure.** ~19.5% of supply sits in one system contract. BNB Chain's
    cross-chain bridge was widely reported to have been exploited in October 2022 — a public,
    well-documented incident, though *not independently re-verified as part of this pass*; *the
    current security posture of that contract is **unverified** here.* A bridge event is a
    supply-and-confidence event at once. This document has not established a mechanical link
    between #3 and this item, but a trader should at least ask the question before assuming a
    Binance-specific shock and a bridge-contract event are independent for sizing purposes —
    both trace back to the same commercial and technical ecosystem, and neither is verified
    here to be structurally isolated from the other.
11. **Treating BNB as a diversifier because correlation to BTC is "only" ~0.73–0.79.** ~38–47%
    of BNB's variance is not explained by BTC (see "Volatility and correlation"), but this
    document has not quantitatively decomposed that residual — plausibly, not provenly, it
    runs substantially through Binance-specific headline risk rather than an uncorrelated
    return source. Either way, in a market-wide risk-off BNB moves with BTC at higher vol; in a
    Binance-specific event it moves alone. Neither scenario diversifies a book the way lower
    correlation numbers might suggest.
12. **Quote-asset fragmentation.** A meaningful share of BNB volume prints in BNB/USD1, a
    stablecoin distinct from USDT/USDC with its own issuer risk (see "Market structure and
    liquidity"). Composite prices and cost models that don't track which stablecoin a fill
    settled in carry an unmodelled basis.

---

## For this backtester

**Neither BNB nor XRP is held locally.** For BNB specifically:

### BNB **is** listed on Coinbase and **is** fetchable — with a serious caveat

Verified against the live Coinbase Exchange API on 2026-08-05:

```
GET https://api.exchange.coinbase.com/products
  → BNB-USD   status=online   trading_disabled=false   quote_increment=0.01
```

```
GET https://api.exchange.coinbase.com/products/BNB-USD/candles?granularity=86400
  → 288 daily bars, earliest 2025-10-22 (close $1,072.83, volume 356.1 BNB)
```

Only `BNB-USD` exists — no BNB-USDT, no BNB-EUR, no BNB-BTC on Coinbase Exchange. This matches
the public record: Coinbase added BNB to its listing roadmap **2025-10-15** and confirmed
support **2025-10-22**[^coindesk-cb].

**The caveat is history length.** You have **~288 daily bars (~9.5 months)** of Coinbase BNB
data and it starts *at the all-time-high region* ($1,072.83 on day one, ATH $1,369.99 on
2025-10-13, $603 today). The window's own high came slightly after day one ($1,139.32, per the
drawdown table above) before the sustained decline to $598.21 — a brief near-ATH rise, then an
overwhelmingly one-directional decline, not a literally monotonic one from bar one. Either way,
every Coinbase-sourced BNB backtest is run on a **single bull-to-bear regime** with essentially
no mean-reversion or range-bound period in it. That is not enough data for walk-forward
validation with any
meaningful number of folds, and it will make any short-biased or mean-reversion-from-above
strategy look brilliant. If you need pre-October-2025 BNB history you must source it from
another venue, and you then inherit that venue's quality and outage profile.

> For contrast, `XRP-USD` is also **online** on Coinbase (along with XRP-EUR and XRP-USDT;
> XRP-BTC and XRP-GBP are delisted) — so the "BNB is fetchable, XRP isn't" framing does not
> hold on the venue side. XRP's Coinbase problem is a **gap**, not an absence; see the XRP
> reference.

### What the thin turnover means for a realistic cost model

The honest summary is two-sided, and both sides matter:

**The float correction says BNB is more liquid than the headline.** At a defensible float
(excluding the burn address and bridge contract), turnover is ~1.11%; excluding the mega-wallets
too, ~2.70% — at or above BTC's 1.80%. **Do not build a cost model that penalises BNB for the
0.7% figure.** That figure is measuring supply accounting, not depth.

**The venue correction says the liquidity you can reach is far thinner than the headline.**
This is the binding constraint:

| Measure | Value | Source |
|---|---:|---|
| Global BNB 24h volume | $608,516,445 | CoinGecko API, 2026-08-05[^cg-bnb] |
| Coinbase Exchange BNB/USD 24h volume | $2,497,477 (**0.41% of global**) | CoinGecko tickers, 2026-08-05[^cg-tick-bnb] |
| Coinbase BNB-USD **30-day average** volume | 1,818.6 BNB/day ≈ **$1.1M/day** notional | measured from Coinbase daily candles, 2026-08-05 |

For comparison, Coinbase's XRP-USD book averaged **~37.97M XRP/day ≈ $41.5M/day** over the same
30 days — **~38× the BNB book on the same venue.**

Concrete implications for a cost model on Coinbase BNB:

1. **Cap position size by ADV, not by market cap.** At ~$1.1M/day, a 1% ADV participation cap
   is ~$11,000/day. A 1% position sized off the ~$80.3B market cap instead is ~$803M — nearly
   five orders of magnitude larger than the book can actually absorb in a day.
2. **Do not use a flat basis-point slippage assumption.** A flat 5–10bp cost model is
   calibrated for BTC-class depth and is *actively misleading* here. Model impact as a convex
   function of participation rate, and validate the curve against real fills before trusting it.
3. **Fees are not the dominant cost.** Coinbase Advanced base-tier spot is 0.40% maker / 0.60%
   taker[^corpus-crypto] — already 4–6× Binance's 0.10%. On a $1.1M/day book, market impact
   will often exceed the fee. A backtest that models fees but not impact understates cost
   badly, and the error grows with size.
4. **Expect gaps, wide prints, and stale quotes** in the daily bars — a $1.1M/day book has hours
   with negligible trade. Bar-close fills are an optimistic fiction. Sanity-check any strategy
   against a "fill at next bar's open, plus impact" variant.
5. **Cross-venue price references are not tradable prices.** CoinGecko's $603.05 is a
   volume-weighted composite dominated by Binance/USDT and by venues with questionable volume.
   If you backtest against composite prices and execute on Coinbase, you have a basis you never
   modelled.
6. **Survivorship/listing-date bias is live, not historical.** BNB became Coinbase-fetchable
   only after a specific 2025 commercial decision. A universe built from "what Coinbase lists
   today" quietly conditions on that decision. Anchor universe membership to each asset's
   listing date.
7. **The vol/correlation inputs above (BNB ρ≈0.73–0.79 to BTC, 41% 90d vol)** come from the same
   288-bar drawdown window. Any risk model calibrated on them is calibrated on one regime.

**Bottom line for sizing:** BNB is a genuinely liquid asset globally, traded on a venue-set
you should distrust, reachable from Coinbase through a book roughly 1/38th the size of the
XRP one. Size against the Coinbase book. Model impact convexly. And treat every BNB backtest
result from ~288 bars of one-directional tape as a hypothesis, not evidence.

---

## Sources

[^cg-bnb]: CoinGecko API, `/api/v3/coins/binancecoin`. Retrieved 2026-08-05 03:03:59 UTC (`last_updated` field). Price $603.05; market cap $80,311,028,264; FDV $80,311,027,244; 24h volume $608,516,445; circulating 133,164,808.15; total 133,164,808.15; max 200,000,000; ATH $1,369.99 on 2025-10-13. https://api.coingecko.com/api/v3/coins/binancecoin

[^cg-btc]: CoinGecko API, `/api/v3/coins/bitcoin`. Retrieved 2026-08-05 03:03:38 UTC. Price $64,363; market cap $1,291,599,527,457; circulating 20,065,943; 24h volume $23,203,709,215; turnover 1.797%. https://api.coingecko.com/api/v3/coins/bitcoin

[^cg-tick-bnb]: CoinGecko API, `/api/v3/coins/binancecoin/tickers?depth=true&order=volume_desc`. Retrieved 2026-08-05. Top 100 tickers, $617,625,805 aggregate. This is a different aggregation than the $608,516,445 24h volume in the Snapshot table ([^cg-bnb], the coin-detail endpoint) — the two CoinGecko endpoints use different methodologies and will not tie out exactly; treat them as two independently-sourced volume estimates, not a discrepancy to reconcile.

[^bsc-rpc]: BNB Smart Chain public JSON-RPC node, `bsc-rpc.publicnode.com`, `eth_getBalance` queried at block 114,089,029 (2026-08-05) for the five addresses in the on-chain concentration table above. Same primary read listed in "Primary data pulled live for this document" below.

[^bnb36]: BNB Chain, "36th BNB Burn." Burn executed 2026-07-15; 1,615,827.795 BNB destroyed; total supply 133,166,127.91. https://www.bnbchain.org/en/blog/36th-bnb-burn — corroborated by crypto.news and CryptoSlate coverage, July 2026 (~$932M notional). verified-as-of: 2026-08-05

[^bnb34]: BNB Chain, "34th BNB Burn." Remaining total supply 136,361,374.34 BNB; ~1.37M BNB (~$1.28B) destroyed. https://www.bnbchain.org/en/blog/34th-bnb-burn — corroborated by Yahoo Finance / CryptoRank coverage. verified-as-of: 2026-08-05

[^academy]: Binance Academy, "What Is BNB Auto-Burn?" Auto-Burn formula `B = N/(100×P)×K`, K initially 1,000; BEP-95 activated November 2021 with an initial 10% gas-fee burn ratio, adjustable by validator governance; 35th burn 2026-04-15 of ~1,569,307 BNB to ~134,786,916 supply; five-to-six-year estimate to the 100M target. https://www.binance.com/en/academy/articles/what-is-bnb-auto-burn — retrieved 2026-08-05

[^coincarp]: CoinCarp, "Top 100 Binance Coin Rich Address List." Top-10 75.63%, top-20 77.79%, top-50 80.26%, top-100 82.07%; page circulating supply 133,164,809 BNB (confirms current snapshot); exchange breakdown Binance 41.17%, Bybit 0.17%. https://www.coincarp.com/currencies/binance-coin/richlist/ — retrieved 2026-08-05. The per-address table on this page parsed with misaligned columns and is **not** relied upon here; the summary statistics block is.

[^ainvest]: AInvest, "Institutional Confidence Lifts BNB to New Heights Amid Centralization Concerns," 2025-08-24. Cites BscScan for "top 11 wallets control over 55% of BNB supply" and a single address at 19.9%. Secondary source, older vintage; included for directional corroboration only.

[^doj]: US Department of Justice, "Binance and CEO Plead Guilty to Federal Charges in $4B Resolution," 2023-11-21 (page updated 2025-02-06). Independent compliance monitor for three years; AML and sanctions remediation. https://www.justice.gov/archives/opa/pr/binance-and-ceo-plead-guilty-federal-charges-4b-resolution

[^sec-binance]: SEC Litigation Release No. 26316, 2025-05-29, "SEC Announces Dismissal of Civil Enforcement Action Against Binance Entities and Founder Changpeng Zhao." *SEC v. Binance Holdings Ltd., et al.*, No. 1:23-cv-01599 (D.D.C., filed 2023-06-05). Joint stipulation of dismissal **with prejudice**. https://www.sec.gov/enforcement-litigation/litigation-releases/lr-26316 — corroborated by Reuters and CNBC, 2025-05-29.

[^law-com]: Law.com / National Law Journal, "'Crypto Enforcement Is Dead': SEC Files to Dismiss Binance Litigation," 2025-05-29. Records the 2025-02-13 grant of a 60-day stay pending the SEC crypto task force.

[^senate]: US Senate Committee on Banking, Housing, and Urban Affairs, letter to DOJ and Treasury re: Binance pardon, 2025-10-28. Records the pardon of Changpeng Zhao granted 2025-10-23. https://www.banking.senate.gov/imo/media/doc/letter_to_doj_treasury_re_binance_pardon.pdf

[^factcheck]: FactCheck.org, "Addressing Trump's Claims About the Pardon of Binance Founder," November 2025. Confirms the 2025-10-23 pardon date.

[^eco]: Eco support article, "Binance Reserves, Regulation, and US Access in 2026." Reports (secondary, **unverified**) that a monitor cleared Binance's KYC remediation in March 2025 with sanctions screening still under review, and that the DOJ settlement carries a five-year compliance window.

[^coindesk-cb]: CoinDesk, "Coinbase Rolls Out the Blue Carpet for Binance's BNB Token," 2025-10-15 (roadmap addition); listing support confirmed 2025-10-22 per contemporaneous coverage. Corroborated by the Coinbase API's earliest BNB-USD daily candle of 2025-10-22.

[^vaneck-pr]: VanEck press release, "VanEck Launches First U.S. Spot BNB ETP: VBNB," 2026-05-28. Physically backed, cold storage, qualified custodian. https://www.vaneck.com/us/en/press-releases/vaneck-launches-first-us-spot-bnb-etp-vbnb/

[^coindesk-etf]: CoinDesk, "VanEck launches first U.S. spot BNB ETF on Nasdaq," 2026-05-28. Ticker VBNB, 0.39% sponsor fee, custodian Anchorage Digital Bank; cites Artemis data on BNB Chain activity.

[^vaneck-fund]: VanEck VBNB fund page, "ETF Statistics as of 07/31/2026." Total net assets $2,284,194; BNB in Trust 3,885.166; shares outstanding 100,000. https://www.vaneck.com/us/en/investments/bnb-etf-vbnb — retrieved 2026-08-05

[^cg-treas]: CoinGecko, "BNB Treasuries." 3 institutions, 686,076 BNB, ~$409M, 0.51% of total supply. https://www.coingecko.com/en/treasuries/bnb — retrieved 2026-08-05

[^btreas]: bitcointreasuries.net/bnb. 5 entities, 688,818.5 BNB, ~$399.45M; largest CEA Industries at 515,544 BNB. Retrieved 2026-08-05.

[^corpus-crypto]: Local corpus — `~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md` (verified-as-of: 2026-06-21 throughout). Used for: absence of NBBO across crypto venues; exchange fee comparison table (Coinbase Advanced 0.40%/0.60%, Binance 0.10%/0.10%); Bitwise 2019 and Chainalysis 2025 wash-trading estimates; 24/7 trading and absence of spot circuit breakers; CEX balance as exchange liability; stablecoin non-equivalence; Binance/OKX US-availability status; 2023 DOJ $4.3B settlement. **Note the correction above:** this file dates the SEC-Binance dismissal to February 2025; the primary SEC litigation release dates it 2025-05-29.

**Primary data pulled live for this document (all 2026-08-05):**
- Coinbase Exchange REST API — `/products` (listing status), `/products/{id}/candles` (daily OHLCV, volume, history depth). `https://api.exchange.coinbase.com`
- BNB Smart Chain JSON-RPC — `eth_getBalance` at block 114,089,029. `https://bsc-rpc.publicnode.com`
- CoinGecko API v3 — `/coins/{id}`, `/coins/{id}/tickers`.

**Explicitly unverified in this pass:** the identity of address `0xff3f4285…18ac4d3` (22.4% of
supply); the `0xbe0eb53f…` and `0xf977814e…` exchange-wallet labels (explorer-community
attributions — the balances are verified, the labels are not); VanEck's Artemis-sourced BNB
Chain activity figures (>14M tx/day, >2.5M DAU, >$16B stablecoins, $3.6B tokenized RWAs — vendor
cited, not independently confirmed); the current BEP-95 burn ratio (10% is the documented
*initial* value); the current Binance BNB fee-discount percentage; whether BNB is among the 18
assets named as digital commodities in the SEC/CFTC joint interpretation of 2026-03-17 (see
"What drives the price" for the interpretation itself); the current security posture of the BSC
Token Hub bridge contract; and the DOJ monitorship's present status.

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
