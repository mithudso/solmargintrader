<!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/crypto-and-digital-asset-trading.md by scripts/persist-spoke.mjs. -->

## Contents

1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
   - [Spot Trading on CEX](#1-spot-trading-on-cex)
   - [Perpetual Futures](#2-perpetual-futures)
   - [Funding Rates](#3-funding-rates)
   - [Margin and Liquidation](#4-margin-and-liquidation)
   - [Stablecoins](#5-stablecoins)
   - [Spot Crypto ETFs/ETPs](#6-spot-crypto-etfsetps)
   - [Custody and Keys](#7-custody-and-keys)
   - [Crypto Market Structure](#8-crypto-market-structure)
3. [Exchange Comparison](#exchange-comparison)
4. [Practical Patterns](#practical-patterns)
5. [Anti-Patterns](#anti-patterns)
6. [Regulatory Landscape](#regulatory-landscape)
7. [References](#references)

---

## Overview

Crypto and digital asset trading takes place primarily on **centralized exchanges (CEX)** — custodial platforms that operate Central Limit Order Books (CLOBs) and hold assets on behalf of users. Unlike US equity markets, there is no Regulation NMS, no National Best Bid and Offer (NBBO), no consolidated tape, and no industry-wide circuit breakers on spot trading. Crypto markets trade **24 hours a day, 7 days a week, 365 days a year**.

The dominant trading instruments are:
- **Spot** — immediate delivery of the underlying asset
- **Perpetual futures** — the dominant derivatives product globally, with no expiry date; invented by BitMEX in 2016 and now representing ~93% of all crypto futures volume

The dominant stablecoins that serve as settlement and margin currency are **USDT (Tether)** and **USDC (Circle)**. All dollar figures in this reference are **USD unless otherwise noted**; all AUM figures carry individual as-of stamps because different sources captured different dates.

> **Educational note — not financial advice.** Crypto trading carries extreme risk of loss. Leverage, 24/7 markets, liquidation cascades, and exchange counterparty risk (FTX example) mean losses can be total and rapid. Nothing in this reference is investment advice.

---

## Core Concepts

### 1. Spot Trading on CEX

**What it is.** A spot trade on a CEX is an agreement to buy or sell a digital asset at the current market price, with immediate transfer of ownership (credited to your exchange account). No leverage is required.

**Order book mechanics.** CEX spot markets operate as CLOBs:
- **Bids** = buy orders at a maximum price; **asks** = sell orders at a minimum price
- **Spread** = best ask minus best bid; reflects liquidity and market-maker competition
- **Depth** = volume available at each price level; thin books are prone to slippage
- Orders execute at the best available price (market orders) or only at a specified price or better (limit orders)

Unlike US equities, there is **no NBBO** linking exchanges. BTC/USDT on Binance and BTC/USDT on Kraken are independent order books; arbitrageurs (not regulation) keep prices close.

**Trading pairs.** Most volume flows through pairs denominated in stablecoins (BTC/USDT, ETH/USDT, etc.) rather than fiat (BTC/USD, BTC/EUR). USDT leads approximately 79.7% of stablecoin pair volume on global CEX.^[verified-as-of: 2026-06-21, CoinMarketCap data]

**Maker/taker fee model.** CEX charge differentiated fees:
- **Maker** = adds liquidity (limit order resting in book) — lower fee
- **Taker** = removes liquidity (market order or aggressive limit) — higher fee
- High-volume traders and VIP tiers receive discounted rates; fee schedules vary by exchange (see [Exchange Comparison](#exchange-comparison))

**KYC/AML requirements.** All major CEX require identity verification (Know Your Customer / AML compliance). Under the US Bank Secrecy Act Travel Rule, transfers above $3,000 require originator/beneficiary information. Withdrawal limits tier up with verification level.

---

### 2. Perpetual Futures

**Origin.** Robert Shiller theoretically proposed non-expiring futures in 1992.[^1] BitMEX launched the first live crypto perpetual futures contract on **May 13, 2016** (co-founded by Arthur Hayes and Ben Delo).[^2] The instrument now dominates crypto derivatives: perpetuals represent approximately **93% of all crypto futures volume** and have surpassed $90T in cumulative notional volume.[^3]

**How they work.** A perpetual futures contract tracks the price of an underlying asset without an expiry date. Instead of converging to spot at expiry (like a traditional futures), perpetuals use a **funding rate** mechanism to anchor the futures price to spot (see [Funding Rates](#3-funding-rates)).

**Three prices — critical distinctions:**

| Price | Definition | Used for |
|---|---|---|
| **Index price** | Volume-weighted composite of spot prices across multiple exchanges; individual exchange components are capped at median ±3% to prevent manipulation | Funding rate calculation |
| **Mark price** | Median of (Exchange Price 1, Exchange Price 2, Last Price); manipulation-resistant | **Liquidations** — this is what triggers your liquidation, not the last price |
| **Last price** | Most recent executed trade on the derivatives order book | P&L display, fills |

> **Key insight for traders:** Because liquidations use mark price (not last price), a wick in the last price that doesn't move the mark will not liquidate you. Conversely, a slow drift in the index/mark can liquidate without a dramatic candle.

**Contract types:**
- **Linear (USDT-margined):** Quoted and settled in USDT; P&L is straightforward in USD terms; now dominant
- **Inverse (coin-margined, e.g., BTC-settled):** Margin and settlement in the underlying coin; P&L is nonlinear (a profitable long requires BTC price to rise to realize USD gain); used by those holding coin inventory

**Funding interval.** Standard is every **8 hours at 00:00, 08:00, and 16:00 UTC** (Binance, Bybit, OKX, BitMEX). Coinbase International and dYdX use hourly funding.

**Leverage limits:**
- Offshore CEX (Binance, Bybit, OKX): up to 100-125x on BTC/ETH [^4] (verified-as-of: 2026-06-21)
- US-regulated venues (Coinbase International, CFTC-regulated): approximately 10x
- EU retail (ESMA): 2:1 on crypto CFDs
- UK: FCA banned retail crypto derivatives in 2020

---

### 3. Funding Rates

**Purpose.** Funding rates are periodic cash transfers between long and short perpetual futures holders that prevent the perpetual price from diverging significantly from spot.

**Formula (Binance/industry standard):**

```
Funding Rate (F) = Average Premium Index (P) + clamp(Interest Rate − P, −0.05%, +0.05%)
```

- **Interest rate:** Fixed at **0.01% per 8-hour period** (~10.95% annualized); represents the cost-of-carry assumption
- **Premium index (P):** Reflects the premium or discount of the perpetual's mid-price relative to the index price
- **Clamp:** Prevents the interest-rate component from overwhelming the premium component; effective range is −0.05% to +0.05% per 8h

**Payment mechanics:**
- **Positive rate:** Longs pay shorts (futures above spot; bullish premium)
- **Negative rate:** Shorts pay longs (futures below spot; bearish discount)
- Payment calculated on **notional value**, not margin — so at 10x leverage, you pay/receive funding on the full notional, which can exceed your margin balance rapidly

**Normal vs extreme ranges:**
- Normal range: ±0.01%/8h (flat market)
- Bull market extremes: 0.05-0.30%/8h sustained over days (≈66-400% annualized if maintained — which they are not)
- Bear market (shorts dominant): negative rates, down to −0.05%/8h or beyond

**Sentiment signal:**
- Sustained positive funding (>+0.05%/8h for 3+ consecutive days) = overleveraged longs; historically precedes deleveraging events [^5]
- Deeply negative funding = shorts overcrowded; historically a contrarian buy signal
- **Caveat:** Funding is a lagging/coincident indicator, not a reliable predictive signal; do not use as a standalone entry signal

**Cash-and-carry (funding harvest) arbitrage:**
- Strategy: Long spot + short perpetual of same asset = delta-neutral position that collects positive funding
- Normal environment: 5-8% APY; bull market extremes: 25-50%+ APY (non-annualized funding spikes)
- Risks: funding rate reversal (sudden switch to negative), liquidation on short leg (requires adequate margin buffer), exchange counterparty risk, withdrawal/re-collateralization friction, fee drag

**Data sources:** Coinglass (coinglass.com/FundingRate), exchange APIs (e.g., Binance `/fapi/v1/fundingRate`), CryptoQuant, MacroMicro.

---

### 4. Margin and Liquidation

**Margin modes:**
- **Cross margin:** Your entire account balance serves as collateral for all open positions. A loss on one position draws down margin for others; avoids isolated-position liquidation but risks the entire account.
- **Isolated margin:** Each position has a fixed, capped margin allocation. Maximum loss per position = allocated margin. Protects other positions but liquidations are more frequent if margin is thin.

**Maintenance margin.** Typically 0.5-1% of position value (varies by exchange and position size tier). Your position is liquidated when remaining equity falls to maintenance margin level.

**Liquidation price (simplified, for long position):**
```
Liquidation Price ≈ Entry Price − (Margin / Position Size)
```
At 10x leverage with 10% margin per contract, a ~9% adverse move triggers liquidation.

**Mark price is what triggers liquidation** — not the last traded price (see [Perpetual Futures](#2-perpetual-futures)).

**Insurance fund.** When a position is liquidated at a price worse than the liquidation price (negative equity), the exchange's **insurance fund** absorbs the shortfall. Binance, Bybit, and OKX each maintain insurance funds of hundreds of millions of USD. [^6] This prevents socializing losses to counterparties in normal markets.

**Auto-Deleveraging (ADL).** If the insurance fund is depleted, ADL is the last resort: the exchange force-closes positions of the most profitable/leveraged traders on the winning side. Most retail traders never experience ADL in normal conditions, but it is the systemic risk of a severely capitalized exchange during extreme volatility.

**Liquidation cascades.** Large moves trigger cascading liquidations:
- **November 2025 event:** Approximately $1.9 billion liquidated in a 4-hour window; approximately 85% were long positions; Bitcoin open interest fell ~35%.[^7] (verified-as-of: 2026-06-21)
- **October 2025 event:** Approximately $3.21 billion liquidated in 60 seconds.[^8] (verified-as-of: 2026-06-21)

**Risk management tools:** Take-profit/stop-loss orders, reduce-only orders (can only decrease position size), trailing stops.

---

### 5. Stablecoins

Stablecoins are crypto tokens designed to maintain a peg to a reference currency (typically USD). They serve as settlement, margin collateral, and the primary "cash" layer on CEX.

#### USDT (Tether)

- **Market cap:** ~$186.4B (June 2026 data; Q4 2025 attestation showed $187.3B peak)[^9] verified-as-of: 2026-06-21
- **Market share:** ~59% of stablecoin market cap (down from ~66% mid-2025; total stablecoin market cap ~$318B as of early 2026)[^9a] verified-as-of: 2026-06-21
- **Reserve backing:** Claims fully backed by USD equivalents (cash, T-bills, corporate paper). Attestations provided by BDO Italia — these are **attestations, not full audits**; an audit would express an opinion on completeness and controls, which has never been completed.
- **Regulatory history:** NYAG fine of $18.5M in 2021 for misrepresenting reserves; Tether settled without admitting wrongdoing. Operations relocated to El Salvador in January 2025.[^10]
- **GENIUS Act status:** USDT is **ineligible** under the GENIUS Act (see Regulatory Landscape) because Tether is a non-US issuer.
- **MiCA status:** Delisted from EU-regulated venues as of March 31, 2025 MiCA enforcement; EU USDT volume fell approximately 70% following delisting.[^11]

#### USDC (Circle)

- **Market cap:** ~$75B (72% YoY growth as of mid-2025)[^12] verified-as-of: 2026-06-21
- **Reserve backing:** 100% US Treasuries and cash; monthly third-party attestations by Deloitte; MiCA-compliant
- **Circle IPO:** Circle went public on NYSE on **June 5, 2025** at $31/share (IPO price implied ~$6.8B pre-money valuation); shares soared 168% on debut, closing at a first-day market cap of ~$16.7B. Ticker: CRCL.[^13] verified-as-of: 2026-06-21
- **Regulatory status:** GENIUS Act compliant; USDC doubled its EU market share after MiCA forced USDT delistings

#### FDUSD (First Digital USD)

- **Background:** Replaced BUSD (Binance's stablecoin) after the SEC issued a Wells notice to Paxos regarding BUSD in February 2023
- **April 2025 depeg:** FDUSD temporarily fell to $0.87-0.91 amid concerns about First Digital Labs' financial health; recovered but volume contracted dramatically[^14] verified-as-of: 2026-06-21
- **Current state:** ~$374M market cap (from a peak of ~$4.8B)

#### UST/LUNA (Case Study — Algorithmic Failure)

The **Terra UST/LUNA collapse** (May 2022) destroyed approximately $40B in value in days. UST was an algorithmic stablecoin (no real-money reserves); it relied on a mint/burn arbitrage with LUNA to maintain its peg. When confidence broke, a death spiral ensued: depegging → LUNA hyperinflation → further depegging → total collapse. The contagion triggered failures at Three Arrows Capital (3AC), Celsius, BlockFi, Voyager, and ultimately contributed to the conditions that enabled the FTX collapse in November 2022. **This spoke does not cover DeFi or algorithmic stablecoins in depth; UST is included only as the load-bearing historical context for stablecoin counterparty risk.**

---

### 6. Spot Crypto ETFs/ETPs

**Why they matter.** Spot crypto ETFs allow investors to gain price exposure to Bitcoin or Ether through a standard brokerage account, without wallets, private keys, or exchange accounts. Accessible in IRAs, 401(k) brokerages, and ordinary taxable accounts.

#### Spot Bitcoin ETFs

- **Approval date:** January 10, 2024, SEC approved 11 spot Bitcoin ETP applications; trading began January 11, 2024.[^15]
- **Key products** (figures as of various 2025 reports; verify current before citing):

| Product | Issuer | AUM/Holdings (as-of) | Notes |
|---|---|---|---|
| IBIT | BlackRock | ~757,130 BTC (as of Feb 23, 2026; AUM at current BTC price — verify at issuer)[^16] | ~61% market share among US spot Bitcoin ETPs |
| FBTC | Fidelity | ~179,670 BTC (2024 figure) | Fidelity self-custodies FBTC |
| GBTC | Grayscale | ~143,983 BTC; 1.50% expense ratio | Converted from trust; massive outflows since conversion |

- **Total net inflows:** ~$48.7B in 2024; ~$46.3B in 2025 (verified-as-of: 2026-06-21)[^17]
- **GBTC history:** Traded at a ~50% NAV discount in December 2022 when conversion to ETF was uncertain; discount collapsed to ~1.18% within days of the January 2024 approval; now trades near NAV but has experienced massive net outflows as investors switched to lower-fee products
- **Creation/redemption:** Cash-based (not in-kind); authorized participants submit/receive cash, not Bitcoin. Coinbase Custody is the dominant custodian across multiple issuers; Fidelity self-custodies FBTC.
- **Expense ratios:** 0.15% (Grayscale Bitcoin Mini Trust) to 1.50% (GBTC); most launched at 0.19-0.25%

**BITO (futures-based predecessor):** ProShares Bitcoin Strategy ETF, launched October 2021; expense ratio 0.95%; subject to **negative roll yield** (futures contango drag) that causes persistent underperformance vs spot Bitcoin over time.

#### Spot Ether ETFs

- **Approval date:** July 22-23, 2024; 9 spot Ether ETFs launched. Staking was **excluded** from most products at launch — staking exposure creates regulatory complexity.
- **Grayscale ETHE/ETH:** First to announce a path to enable staking (pending regulatory clarity)[^18] verified-as-of: 2026-06-21

---

### 7. Custody and Keys

**"Not your keys, not your coins."** When you hold crypto on an exchange, you hold a claim on the exchange's balance sheet, not direct ownership of the blockchain asset. The FTX collapse illustrated this catastrophically.

**FTX collapse (November 2022):**
- Approximately $8 billion in customer assets were misappropriated by Alameda Research via an undisclosed backdoor in FTX's systems[^19]
- CFTC imposed a $12.7 billion judgment against FTX — the largest CFTC judgment in history at the time[^20]
- Sam Bankman-Fried (SBF) sentenced to **25 years in federal prison**, March 2024[^21]
- FTX bankruptcy estate was on track for near-full repayment to creditors by 2026 due to asset recovery and token appreciation[^22] verified-as-of: 2026-06-21

**Self-custody spectrum:**

| Type | Definition | Risk profile |
|---|---|---|
| **Exchange custody** | Exchange holds keys; you hold a claim | Counterparty risk (FTX); no blockchain ownership; subject to exchange insolvency/hack |
| **Hot wallet** | Software wallet on internet-connected device; you hold keys | Phishing, malware, SIM swap; suitable for active trading (1-10% of holdings rule of thumb) |
| **Cold wallet (hardware)** | Air-gapped hardware device (Ledger, Trezor); keys never touch internet | Physical loss/damage; seed phrase theft; highest security for bulk holdings |
| **MPC wallet** | Multi-party computation shards the private key across multiple parties; no single point of compromise | Used by institutional custodians; increasingly offered to retail via platforms |

**Blockchain confirmations before funds are spendable:**
- **Bitcoin (BTC):** 3-6 confirmations (approximately 30-60 minutes) considered safe for large sums; some exchanges accept 1-3 for smaller amounts
- **Ethereum (ETH):** 12-64 confirmations (under 5 minutes post-Merge); finality achieved in ~12.8 minutes
- **Solana (SOL):** Near-instant (~400ms per block); finality in seconds

**Proof of Reserves (PoR):** Post-FTX, major exchanges publish PoR reports using Merkle tree methodology to prove they hold the assets they claim. Binance uses zk-SNARK proofs. **Critical limitation:** PoR proves assets held, but does **not** prove liabilities or off-balance-sheet obligations. A PoR showing 1:1 Bitcoin backing is not solvency proof — Alameda's liabilities were off FTX's PoR. Verify which audit methodology an exchange uses.

---

### 8. Crypto Market Structure

**24/7 trading.** Crypto spot CEX operate continuously with no scheduled close. There are **no industry-wide circuit breakers** on spot CEX during crashes. CME Bitcoin futures (regulated US product) have ±10% price limits per 60-minute window as of 2026.

**Volatility.** Bitcoin annualized realized volatility is approximately 54% in recent periods vs approximately 13-15% for the S&P 500.[^23] Historical Bitcoin volatility range: 60-100%+ during major moves. Bitcoin set an all-time high of approximately $126,000 in October 2025.[^24] verified-as-of: 2026-06-21

**Market fragmentation.** Dozens of independent CEX operate with no consolidated tape. CEX account for approximately 75-80% of perpetual futures volume globally.

**Wash trading.** Bitwise (2019) estimated that 95% of reported spot volume on unregulated exchanges was fake; 26 exchanges faked up to 70% of reported volume. Chainalysis (2025) estimated approximately $2.57B in suspected wash trading on DEX in 2024 alone.[^25] Treat volume figures from unregulated exchanges with skepticism.

**Bitcoin halving cycle.** Approximately every 4 years, the Bitcoin block reward halves:
- April 2024 halving: 6.25 → 3.125 BTC per block
- Historical pattern: significant price appreciation in 12-18 months after halving, but the 2024 cycle produced only approximately 31% gains in the year following (vs 300%+ after the 2020 halving)[^26] verified-as-of: 2026-06-21
- The halving reduces new supply issuance; it does not guarantee price appreciation

**2022 crypto winter sequence.** Terra/LUNA collapse (May 2022) → Three Arrows Capital (3AC) insolvency → Celsius, BlockFi, Voyager failures → Genesis/Gemini Earn → FTX collapse (November 2022). Total market cap lost: approximately $2 trillion from the late 2021 peak.

---

## Exchange Comparison

| Exchange | Base jurisdiction | Maker/taker fee (spot, base tier) | Max leverage (perps) | US availability | Notes |
|---|---|---|---|---|---|
| **Binance** | Cayman Islands (post-2023) | 0.10% / 0.10% | 125x BTC | Binance.US (separate entity, reduced products) | Largest global volume; 2023 DOJ settlement ($4.3B); CZ departed; SEC/DOJ cases; reformed compliance |
| **Coinbase (Advanced)** | USA (NASDAQ: COIN) | 0.40% / 0.60% | ~10x (Coinbase International) | Full retail + institutional | Most US-regulated; largest US retail share; Coinbase Custody dominant for ETF custody |
| **Kraken** | USA | 0.25% / 0.40% | Available outside US | Available | US-regulated; lower leverage for US retail |
| **OKX** | Seychelles | 0.08% / 0.10% | 100x | Exited US market | Strong perps product; large Asian user base |
| **Bybit** | Dubai | 0.10% / 0.10% | 100x | Limited | Major perps volume; large insurance fund |
| **BitMEX** | Seychelles | 0.02% (maker rebate) / 0.075% | 100x | Limited | Invented perpetuals; smaller share now |

**Note on Binance regulatory status (verified-as-of: 2026-06-21):** SEC case against Binance was **dismissed with prejudice on 2025-05-29** (SEC Litigation Release 26316). February 13, 2025 was a 60-day *stay*, not the dismissal -- a distinction that is widely misreported and was corrected here on 2026-08-05; DOJ settlement from 2023 resulted in $4.3B penalty and departure of CZ (Changpeng Zhao) as CEO. Binance.US operates as a separate, significantly reduced entity. OKX exited the US market.

---

## Practical Patterns

**1. Position sizing with leverage.** At 10x leverage on a $1,000 margin deposit, you control $10,000 notional. A 10% adverse move = 100% margin loss (liquidation). Rule of thumb: at Nx leverage, your effective stop is approximately 1/N of entry price. Size positions so the worst realistic adverse move is a defined, acceptable dollar loss — not margin liquidation.

**2. Isolated margin for defined risk.** Use isolated margin when you want to cap the maximum loss on a position. Use cross margin only if you actively manage the whole account and understand that one position's loss draws from all margin.

**3. Funding rate monitoring.** Check funding rates before entering a directional perpetual position. High positive funding (>0.05%/8h) means you pay to hold longs — this adds cost drag and signals crowded positioning. Deeply negative funding reduces cost of longs and signals crowded shorts.

**4. Cash-and-carry setup.** To harvest funding without directional exposure: buy spot BTC/ETH on the same exchange (or another with hedged transfer risk), short equal notional perpetual, maintain sufficient margin on the short to survive a 10-20% BTC rally without liquidation. Unwind both legs simultaneously when funding normalizes.

**5. ETF vs direct crypto for passive exposure.** Spot Bitcoin/Ether ETFs offer familiar brokerage access, SIPC protections on the brokerage side, no key management, and possible IRA eligibility. Trade-offs: expense ratios (0.19-1.50%/year), no ability to move coins off-exchange, no DeFi access. Direct CEX/wallet ownership gives full asset control but adds custody risk and key management burden.

**6. Proof of reserves due diligence.** Before depositing large sums on a CEX: (a) check most recent PoR report date — monthly or recent is better than annual; (b) understand whether it is a Merkle-tree attestation (assets only) or includes liability verification; (c) check insurance fund size; (d) prefer exchanges that carry independent auditor relationships.

---

## Anti-Patterns

**1. Max leverage without a stop.** 125x leverage means a 0.8% adverse move triggers liquidation. At this leverage tier, most positions are closed by the market before any manual intervention is possible. High leverage amplifies funding costs proportionally too.

**2. Treating positive funding as a price signal.** Funding rate is coincident/lagging. High funding sustained during a bull run can persist for weeks before a deleveraging event. Do not short into positive funding based solely on the funding signal.

**3. Confusing exchange balance with self-custody.** Your CEX balance is a liability on the exchange's balance sheet. If the exchange fails (FTX), your funds are in bankruptcy proceedings. Anything you do not need for active trading should be in self-custody cold storage.

**4. Ignoring mark price for liquidation planning.** Assuming "the price has to hit X to liquidate me" based on the chart (last price) rather than the mark price. The mark price can differ by hundreds of dollars during illiquid periods.

**5. Assuming stablecoin equivalence.** USDT and USDC are not interchangeable in risk terms. USDT has unaudited reserves and significant regulatory exposure; USDC is MiCA-compliant with audited reserves. FDUSD nearly depegged in April 2025. Holding all margin in one stablecoin concentrates stablecoin issuer risk.

**6. Extrapolating halving cycle returns.** Each Bitcoin halving produced different price outcomes. The diminishing marginal supply reduction effect and growing market cap make historical % returns less predictive in later cycles.

**7. Treating PoR as a solvency guarantee.** A Merkle-tree PoR proves assets held at a snapshot date but not liabilities, off-balance-sheet obligations, or the operational health of the exchange.

**8. Spot Bitcoin ETF for leveraged or short exposure.** Spot ETFs are buy-and-hold exposure tools. They do not enable shorting, leverage, or intraday trading strategies the way direct CEX access does. BITO (futures-based) has negative roll yield drag and is not equivalent to spot exposure over longer periods.

---

## Regulatory Landscape

**US (verified-as-of: 2026-06-21):**
- **GENIUS Act:** Signed July 18, 2025 (Senate 68-30 on June 17; House 308-122 on July 17). Establishes federal stablecoin framework: issuers must maintain 100% liquid reserves (cash/T-bills), publish monthly disclosures, make no interest payments to holders, and give holders senior claims in insolvency. Non-US issuers (including Tether) are **ineligible**; OCC proposed implementing rulemaking published Federal Register March 2026.[^27]
- **CLARITY Act (H.R. 3633):** Passed the US House of Representatives on July 17, 2025 (294-134 vote); defines a 5-category taxonomy for digital assets (digital commodities, restricted digital assets, etc.); BTC, ETH, SOL, and XRP classified as digital commodities; as of June 2026, has **not passed the Senate** — pending companion legislation.[^28] verified-as-of: 2026-06-21
- **SEC/CFTC joint interpretation (March 17, 2026):** Joint formal interpretation published; 5-group token taxonomy (digital commodities, digital collectibles, digital tools, stablecoins, digital securities); identifies 18 major cryptocurrencies as digital commodities including BTC/ETH/SOL/XRP; binding on both agencies but modifiable by future administration without legislation.[^29] verified-as-of: 2026-06-21
- **Retail leverage:** CFTC limits crypto futures leverage to approximately 10x for retail; UK FCA banned retail crypto derivatives in 2020; EU ESMA caps retail crypto CFDs at 2:1.
- **Spot ETF:** 11 spot Bitcoin ETPs approved January 2024; 9 spot Ether ETPs approved July 2024.

**EU (MiCA):**
- MiCA stablecoin rules effective **March 31, 2025**; full MiCA regime effective December 30, 2024
- USDT delisted from EU-regulated venues; USDT volume on EU venues fell ~70%; USDC doubled EU market share
- 56+ Crypto Asset Service Providers (CASPs) authorized under MiCA as of 2026; approximately 40% drop in EU users of non-compliant exchanges[^30]

**Asia:**
- Japan: Licensed crypto exchanges since 2017 (FSA registration)
- Singapore: MAS licensing framework
- Hong Kong: SFC ASPIRe roadmap for licensed VATPs (Virtual Asset Trading Platforms)
- South Korea: Draft Digital Asset Basic Act

---

## References

[^1]: Shiller, R.J. (1992). *Macro Markets: Creating Institutions for Managing Society's Largest Economic Risks*. Oxford University Press. (Theoretical basis for perpetual futures.)

[^2]: BitMEX Blog (2016). "Announcement: BitMEX's Bitcoin Perpetual Swap." [https://blog.bitmex.com/](https://blog.bitmex.com/) — May 13, 2016 launch.

[^3]: arxiv preprint 2506.08573 (June 2026). Perpetual futures cumulative volume and market share analysis. [https://arxiv.org/abs/2506.08573](https://arxiv.org/abs/2506.08573) verified-as-of: 2026-06-21

[^4]: Binance Futures Help Center. "Leverage & Margin." [https://www.binance.com/en/support/faq/leverage-margin](https://www.binance.com/en/support/faq/leverage-margin) — 125x max on BTC/USDT. verified-as-of: 2026-06-21

[^5]: CryptoQuant (2025). Funding rate sentiment studies. [https://cryptoquant.com/](https://cryptoquant.com/)

[^6]: Bybit Insurance Fund. [https://www.bybit.com/en/help-center/article/Insurance-Fund-in-Derivatives-Trading](https://www.bybit.com/en/help-center/article/Insurance-Fund-in-Derivatives-Trading) — confirmed hundreds of millions maintained. verified-as-of: 2026-06-21

[^7]: Coinglass Liquidation Data. November 2025 cascade event. [https://www.coinglass.com/LiquidationData](https://www.coinglass.com/LiquidationData) verified-as-of: 2026-06-21

[^8]: Coinglass Liquidation Data. October 2025 cascade event. [https://www.coinglass.com/LiquidationData](https://www.coinglass.com/LiquidationData) verified-as-of: 2026-06-21

[^9]: CoinMarketCap. "Tether USDT." [https://coinmarketcap.com/currencies/tether/](https://coinmarketcap.com/currencies/tether/) — June 2026: $186.37B; Q4 2025 attestation peak: $187.3B. verified-as-of: 2026-06-21

[^9a]: CryptoNews. "Tether USDT Briefly Overtakes Ethereum in Market Cap: A $187B Wake-Up Call." [https://cryptonews.com/](https://cryptonews.com/) — market share ~59% as of early 2026; total stablecoin market cap ~$317.9B. verified-as-of: 2026-06-21

[^10]: Tether. "Tether Relocates to El Salvador." January 2025. [https://tether.to/](https://tether.to/) verified-as-of: 2026-06-21

[^11]: MiCA Stablecoin enforcement — EU venue USDT delistings. Kaiko Research (2025). [https://research.kaiko.com/](https://research.kaiko.com/) verified-as-of: 2026-06-21

[^12]: Circle. "USDC Transparency Report." [https://www.circle.com/en/transparency](https://www.circle.com/en/transparency) — 72% YoY growth figure. verified-as-of: 2026-06-21

[^13]: Circle Internet Group IPO — NYSE listing June 2025. [https://www.circle.com/](https://www.circle.com/) verified-as-of: 2026-06-21

[^14]: CoinDesk (April 2025). "FDUSD Depeg to $0.87 Amid First Digital Labs Controversy." [https://www.coindesk.com/](https://www.coindesk.com/) verified-as-of: 2026-06-21

[^15]: SEC. "Order Granting Accelerated Approval of Proposed Rule Changes." January 10, 2024. [https://www.sec.gov/](https://www.sec.gov/)

[^16]: BlackRock IBIT. Holdings: 757,130 BTC as of February 23, 2026 (per The Block/BestBrokers data, up 149% from post-approval levels); $50.5B AUM figure was from mid-2024 at ~$66K BTC — materially stale. At BTC's 2025-2026 range ($91K-$126K), current AUM is substantially higher; verify at [https://www.ishares.com/us/financial-professionals/investments/products/bitcoin-investing](https://www.ishares.com/us/financial-professionals/investments/products/bitcoin-investing). Market share of ~61% among US spot Bitcoin ETPs confirmed. verified-as-of: 2026-06-21

[^17]: Bloomberg Intelligence / BitMEX Research. Spot Bitcoin ETF flow data (2024-2025). [https://www.bloomberg.com/](https://www.bloomberg.com/) verified-as-of: 2026-06-21

[^18]: Grayscale Ether ETF staking announcement. [https://grayscale.com/](https://grayscale.com/) verified-as-of: 2026-06-21

[^19]: DOJ v. Bankman-Fried. Criminal complaint. SDNY, 2022. [https://www.justice.gov/](https://www.justice.gov/)

[^20]: CFTC. "CFTC Wins Default Judgment Against FTX — $12.7 Billion." [https://www.cftc.gov/PressRoom/PressReleases/](https://www.cftc.gov/PressRoom/PressReleases/) verified-as-of: 2026-06-21

[^21]: DOJ. "Samuel Bankman-Fried Sentenced to 25 Years." March 2024. [https://www.justice.gov/](https://www.justice.gov/)

[^22]: FTX Recovery Trust. Estate update. [https://restructuring.ra.kroll.com/FTX/](https://restructuring.ra.kroll.com/FTX/) verified-as-of: 2026-06-21

[^23]: CoinMetrics / Bloomberg. Bitcoin vs S&P 500 realized volatility comparison. [https://coinmetrics.io/](https://coinmetrics.io/) verified-as-of: 2026-06-21

[^24]: Bitcoin all-time high ~$126,000, October 2025. CoinGecko / TradingView. [https://www.coingecko.com/](https://www.coingecko.com/) verified-as-of: 2026-06-21

[^25]: Chainalysis Crypto Crime Report 2025. Wash trading on DEX analysis. [https://www.chainalysis.com/](https://www.chainalysis.com/) verified-as-of: 2026-06-21; Bitwise (2019): "The Real Bitcoin Market." [https://www.bitwiseinvestments.com/](https://www.bitwiseinvestments.com/)

[^26]: Bitcoin halving April 2024 price outcome analysis. Glassnode / Blockware Intelligence (2025). [https://glassnode.com/](https://glassnode.com/) verified-as-of: 2026-06-21

[^27]: GENIUS Act. Pub. L. No. 119-_ (2025). Signed July 18, 2025. Summary via Senate Banking Committee. [https://www.banking.senate.gov/](https://www.banking.senate.gov/) verified-as-of: 2026-06-21

[^28]: CLARITY Act. H.R. ___ (2025). Passed House July 17, 2025. [https://www.congress.gov/](https://www.congress.gov/) verified-as-of: 2026-06-21

[^29]: SEC/CFTC Joint Digital Asset Taxonomy. March 2026. [https://www.sec.gov/](https://www.sec.gov/) and [https://www.cftc.gov/](https://www.cftc.gov/) verified-as-of: 2026-06-21

[^30]: European Securities and Markets Authority (ESMA). MiCA implementation report. [https://www.esma.europa.eu/](https://www.esma.europa.eu/) verified-as-of: 2026-06-21

### Additional sources consulted during research

**Spot trading / CEX mechanics:**
- Binance Academy. "What is a Centralized Exchange?" [https://academy.binance.com/](https://academy.binance.com/)
- CoinMarketCap. "What is a CEX?" [https://coinmarketcap.com/alexandria/](https://coinmarketcap.com/alexandria/)
- Coinbase Learn. "What is a crypto exchange?" [https://www.coinbase.com/learn/](https://www.coinbase.com/learn/)
- Kraken Pro fee schedule. [https://www.kraken.com/features/fee-schedule](https://www.kraken.com/features/fee-schedule)
- OKX fee schedule. [https://www.okx.com/fees](https://www.okx.com/fees)
- FinCEN Travel Rule guidance. [https://www.fincen.gov/](https://www.fincen.gov/)

**Perpetual futures:**
- Binance Futures documentation. Mark Price, Index Price, Funding Rate. [https://www.binance.com/en/support/faq/](https://www.binance.com/en/support/faq/)
- Bybit Help Center. "Perpetual Contracts." [https://www.bybit.com/en/help-center/](https://www.bybit.com/en/help-center/)
- OKX Academy. "Perpetual Swaps Explained." [https://www.okx.com/learn/](https://www.okx.com/learn/)
- Coinbase International perp documentation. [https://www.coinbase.com/international](https://www.coinbase.com/international)

**Stablecoins:**
- Tether attestation reports (BDO Italia). [https://tether.to/en/transparency/](https://tether.to/en/transparency/)
- Circle USDC reserve reports. [https://www.circle.com/en/transparency](https://www.circle.com/en/transparency)
- NYAG Tether settlement (2021). [https://ag.ny.gov/](https://ag.ny.gov/)
- Congressional Research Service. "GENIUS Act Analysis." 2025.
- Kaiko. "MiCA impact on stablecoin market." [https://research.kaiko.com/](https://research.kaiko.com/)

**Spot ETFs:**
- SEC ETF approval orders, January 2024. [https://www.sec.gov/cgi-bin/browse-edgar](https://www.sec.gov/cgi-bin/browse-edgar)
- BlackRock iShares Bitcoin Trust IBIT prospectus. [https://www.ishares.com/](https://www.ishares.com/)
- Fidelity Wise Origin Bitcoin Fund FBTC. [https://www.fidelity.com/](https://www.fidelity.com/)
- ProShares BITO prospectus. [https://www.proshares.com/](https://www.proshares.com/)
- VanEck Bitcoin Trust. [https://www.vaneck.com/](https://www.vaneck.com/)
- Eric Balchunas / Bloomberg Intelligence ETF flow data.

**Custody / proof of reserves:**
- Binance PoR methodology. [https://www.binance.com/en/proof-of-reserves](https://www.binance.com/en/proof-of-reserves)
- Kraken PoR. [https://www.kraken.com/proof-of-reserves](https://www.kraken.com/proof-of-reserves)
- Ledger hardware wallet documentation. [https://www.ledger.com/](https://www.ledger.com/)
- Trezor hardware wallet documentation. [https://trezor.io/](https://trezor.io/)

**Market structure / volatility:**
- Glassnode. Bitcoin halving on-chain analysis. [https://glassnode.com/](https://glassnode.com/)
- CoinMetrics Network Data. [https://coinmetrics.io/](https://coinmetrics.io/)
- Coinglass OI and liquidation data. [https://www.coinglass.com/](https://www.coinglass.com/)
