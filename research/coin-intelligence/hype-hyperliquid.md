---
name: hype-hyperliquid
description: Trader-facing reference on Hyperliquid (HYPE) — on-chain CLOB perp DEX with its own L1, the HLP vault versus Jupiter's JLP, fee-funded buybacks, unlock overhang, and validator centralisation caveats.
---

# Hyperliquid (HYPE)

> **Not investment advice.** This is a factual reference. Every figure carries a date and a source
> because every figure decays.

## Snapshot (AS OF 2026-08-04)

All figures fetched 2026-08-04 unless stated. **Prices, supply, fee run-rates, validator counts and
buyback totals all move — treat anything here older than a few weeks as a starting point for
re-verification, not as current.** The fee run-rate in particular has moved fast in both directions
during 2026.

| Metric | Value | Source (date) |
|---|---|---|
| Price | $55.47 | CoinGecko (2026-08-04) |
| Market cap | $12.34B — rank #10 | CoinGecko (2026-08-04) |
| Circulating supply | 222.45M HYPE (est.) | CoinGecko (2026-08-04) |
| Total supply | 955.31M (net of Assistance Fund) | CoinGecko (2026-08-04) |
| Max supply | 1,000,000,000 | CoinGecko (2026-08-04) |
| FDV | $55.46B — MC/FDV 0.22 | CoinGecko (2026-08-04) |
| 24h volume | $280.8M | CoinGecko (2026-08-04) |
| **Turnover (24h vol ÷ mcap)** | **2.52%** — 4th of the ten coins here[^turnover-std] | single-timestamp pull, 2026-08-05T02:15:22Z |
| TVL | $6.247B — MC/TVL 1.98 | DefiLlama via CoinGecko (2026-08-04) |
| 24h protocol fees | $1,513,540 (−35.3% d/d) | Token Terminal via CoinGecko (2026-08-04) |
| 24h protocol revenue | $1,165,113 (−31.9% d/d) | Token Terminal via CoinGecko (2026-08-04) |
| Assistance Fund holdings | 44,528,131 HYPE (≈$2.47B at $55.47) | CoinGecko supply breakdown (2026-08-04) |
| All-time high | $76.87, 2026-06-16 (CoinGecko's FAQ on the same page says $76.70 — see conflict 7) | CoinGecko (2026-08-04) |
| All-time low | $3.81, 2024-11-29 | CoinGecko (2026-08-04) |
| Next scheduled unlock | 2026-08-06 — 9.92M HYPE (~$550M), Core Contributors, 1.0% of total supply | Tokenomist via CoinGecko (2026-08-04) |

Contract (HyperCore): `0x0d01dc56dcaaca66ad901c959b4011ec`. Chain: Hyperliquid L1.

## What could and could not be established

**Established with confidence.** Hyperliquid runs a fully on-chain central limit order book on a
purpose-built L1; the Assistance Fund buys HYPE on the open market with the overwhelming majority of
net protocol fees; there was no venture funding and therefore no early-investor cliff; the March 2025
JELLY intervention happened substantially as reported and was confirmed by the protocol itself; the
validator set is small and the node software is closed source. HYPE is listed on Coinbase for
spot USD trading.

**Contested or unresolved — do not treat any single number below as settled.**

1. **Are bought-back tokens burned, or held?** Sources disagree flatly.
   - "Permanently destroyed" / burned — perp.wiki (2026-03-28).
   - Explicitly **not** burned; "sits in the fund balance rather than going to a null address …
     anyone modeling HYPE should be aware of the distinction," with withdrawal conditions "narrow but
     not fully formalized" — Giants Tokenomics Lab (2026-04-17).
   - Purchased tokens "sent to an address that can never be accessed" — CoinShares via etfdb
     (2026-06-15).
   - Held in a protocol-controlled wallet, with "a portion of holdings subject to governance-approved
     permanent burns" — crypto.news (2026-05-27).

   CoinGecko's supply model (2026-08-04) is consistent with *hold, not burn*: it subtracts the
   Assistance Fund's 44,528,131 HYPE from **total** supply rather than treating it as destroyed.
   The practical difference is reversibility. A burn is final; a treasury balance is a governance
   decision away from being something else. Assume hold-in-fund and price the reversal risk.

2. **How much HYPE does the fund hold, and what did it cost?** The reported series does not
   reconcile: ~29.8M (Q3 2025, crypto.news); 44M at an average cost of $24.76, described as 4.4% of
   circulating supply (end-April 2026, VanEck); ~28.5M (March/May 2026, crypto.news); 44.4M worth
   ~$2.2B (June 2026, CoinShares); 44,528,131 (CoinGecko, 2026-08-04). The ~28–30M and ~44M clusters
   are probably measuring different things (net of burns? one strategy address versus all?), but no
   source I found reconciles them. The CoinGecko figure is the one with a visible on-chain address
   (`0xfefe…fefe`) behind it.

3. **Scheduled versus actual vesting.** The contract allows ~9.9M HYPE/month to Core Contributors
   through 2027 (CFBenchmarks, 2026-06-10). CoinShares reported (June 2026) that *actual* monthly
   distributions ran between 140,000 and 1.75M tokens — an order of magnitude below the allowance —
   which would make HYPE net deflationary rather than net inflationary. **Watch observed on-chain
   distributions, not the allowance.** These two framings produce opposite conclusions and I could
   not establish which one described August 2026.

4. **HLP's share of protocol fees.** DefiLlama's adapter methodology says HLP receives "1% of perp
   and spot trading revenue (excluding builders and unit revenue)". The Hyperliquid community wiki
   says "approximately 7% of platform fees". Unresolved.

5. **Volume headlines conflict.** For July 2026 the same news cluster carried "record $320B" and
   "$218B perpetual volume" (CoinGecko news feed, 2026-08-04). For Q1 2026: "over $633 billion …
   (perps and spot)" (VanEck, 2026-05-27) versus "$492.7 billion" (dailycoinbrief, 2026-07-05). These
   are probably different baskets (perps only vs perps+spot+builder markets), but the sources do not
   say so. Always ask *which* volume.

6. **Circulating supply differs by roughly 7%** between CoinGecko's 222.45M (2026-08-04) and VanEck's
   ~238M (2026-05-27), largely an Assistance-Fund netting question plus two months of unlocks. Minor,
   but it moves market cap by ~$0.9B.

7. **The all-time high differs by source.** CoinGecko's statistics block gives **$76.87 on
   2026-06-16**; CoinGecko's own FAQ on the same page gives **$76.70**; dailycoinbrief (2026-07-05)
   also reports $76.70. A 17-cent gap is immaterial for trading but matters if you are anchoring a
   drawdown calculation, and it is the same class of aggregator sloppiness catalogued above.

8. **Not established here:** a published Nakamoto coefficient; the exact size and cost basis of the
   Genesis airdrop in wallet counts; the structure of the points-farming programme that preceded it
   (season count, dates, scoring); and whether the node software has been open-sourced since the
   2026 reports that it had not been. The points programme and airdrop are covered below only to the
   depth the sources in this pass support — treat the detail as thin rather than as settled.

## What it is, mechanically

Hyperliquid is a perpetual-futures exchange that runs as its own Layer 1 rather than as a contract on
someone else's chain. Two components share one consensus layer:

- **HyperCore** — the exchange. A fully on-chain central limit order book. Every order, cancel, trade
  and liquidation is a transaction on the chain and is publicly verifiable. CoinGecko's project
  description (2026-08-04) states the chain supports 200,000 orders/second; HIPERWIRE (2026-03-04)
  reports one-block finality around 0.07 seconds.
- **HyperEVM** — a general-purpose EVM environment for third-party contracts, sharing the same
  validator set and consensus.

Consensus is **HyperBFT**, a HotStuff-derived BFT protocol using delegated proof of stake. Safety
requires an honest quorum of more than two-thirds of staked HYPE. The validator set is fixed within
each epoch of 100,000 rounds (~90 minutes) (Hyperliquid docs, staking page).

Product surface as of 2026: crypto perps (100+ markets, some sources say 200+), spot order books, and
builder-deployed markets in equities, commodities and FX auctioned under HIP-3 (a Hyperliquid
Improvement Proposal — the mechanism by which third parties bid for the right to deploy a new market)
(CFBenchmarks, 2026-06-10; CoinGecko, 2026-08-04).

### The order book, and why it differs from Jupiter's oracle-priced perps

This is the comparison that matters if you already trade Jupiter.

**Jupiter Perps (Solana).** There is no order book. A trader opens a position *against the JLP pool*
at an oracle price, paying a flat fee rather than crossing a spread. Jupiter's docs describe pricing
sourced from Edge by Chaos Labs as primary with Chainlink and Pyth for verification and fallback
(as of 2026); older documentation and third-party write-ups describe Pyth as the price source.
Ongoing cost is an **hourly borrow fee driven by pool utilisation**, not a funding rate:
`Hourly Borrow Fee = (Tokens Locked ÷ Tokens in Pool) × Hourly Borrow Rate × Position Size`
(Jupiter support docs). JLP holders receive **75% of fees** generated by trading, swaps and JLP
mint/burn.

**Hyperliquid.** You cross a real book. Price is discovered endogenously by competing limit orders.
Oracles exist, but they set the **mark price** used for funding and liquidation reference — they do
not set your fill.

The practical differences, in the order they will bite you:

| | Jupiter Perps | Hyperliquid |
|---|---|---|
| Fill price | Oracle price, no spread, no slippage on the fill | Book price — you pay spread and walk the book |
| Price discovery | Imported from off-venue oracles | Endogenous, on-venue |
| Counterparty | The JLP pool, always, by construction | Whoever is on the book — market makers, other traders, sometimes HLP |
| Can the counterparty refuse? | **No.** JLP cannot decline a trade or widen a quote | **Yes.** Makers widen or pull; depth vanishes in stress |
| Ongoing cost | Utilisation-based hourly borrow fee | Funding rate, plus maker/taker fees |
| Can you be the maker? | No | Yes — post limit orders, earn the spread |
| Market breadth | Majors only (SOL, ETH, wBTC) | 100+ crypto perps, plus spot, equities, commodities, FX |
| Main failure mode | Oracle latency/manipulation; pool utilisation caps | Thin-book manipulation; slippage; liquidation cascades |

For a backtester the consequence is concrete. **A Jupiter fill model is a price feed plus a fee.** A
Hyperliquid fill model is not: you need a slippage and depth assumption, or your backtest will
systematically overstate returns on anything but the deepest markets. Conversely, oracle-priced
execution has no slippage but inherits every pathology of the oracle — Jupiter's model is exposed to
oracle latency and manipulation in a way an order book is not, while an order book is exposed to
depth evaporating exactly when you need it.

### HLP versus JLP

**HLP (Hyperliquidity Provider)** is Hyperliquid's protocol-owned, community-funded vault. Per the
Hyperliquid docs it "provides liquidity to Hyperliquid through multiple market making strategies,
performs liquidations, supplies USDC in Earn, and accrues a portion of trading fees." Deposits are
USDC. There is no management or performance fee — all P&L flows pro-rata to depositors. Deposits
carry a **4-day lockup** measured from your most recent deposit (a top-up resets the clock for the
whole position).

Revenue streams: market-making spreads, funding capture, liquidation premiums as backstop liquidator,
interest on idle USDC, and an accrued share of exchange trading fees.

The single most important structural difference from JLP:

> **JLP is the counterparty to every Jupiter trade, by design and without exception. HLP is one
> participant among many on a book, and represents under 2% of Hyperliquid's daily volume** (Hyperliquid
> community wiki, citing on-chain analysis). Hyperliquid does not depend on HLP to function; Jupiter
> Perps cannot function without JLP.

Second difference: **risk shape.** JLP is a basket of SOL, ETH, WBTC, USDC and USDT at target weights.
It is *not* delta-neutral — a JLP holder carries the directional beta of that basket, so JLP prints
attractive headline yield in a bull market and loses dollar value when crypto falls. HLP is
USDC-denominated and roughly market-neutral in intent, so it is far closer to dollar-stable. HLP's
tail risk is not beta; it is inheriting a toxic position.

HLP performance and size, with dates:

- Cumulative profit **$136.9M** since the May 2023 launch (CoinGecko HLP analysis, 2026-07-02).
- TVL peaked at **$603.9M in September 2025**, fell to roughly **$268.6M by June 2026** — down more
  than 55% in nine months (same source). DefiLlama showed **$219.88M**, down 15.8% over 30 days, as
  of the August 2026 fetch. The vault is shrinking.
- Returns are **lumpy, not a yield.** Two events supplied roughly 41% of the vault's all-time profit:
  the 2025-10-10 market-wide flash crash (~$41.5M, about a 10% depositor gain in under 48 hours) and
  the 2026-01-31 liquidation of a large leveraged ETH long (~$15M, a 5.8% single-event return). Long
  flat stretches in between. perp.wiki (2026-03-07) puts the historical range at roughly 10–30% APY
  with a midpoint near 17% and maximum historical drawdown around 4–5% of TVL — treat those as
  backward-looking and wide.

## Supply, issuance, float and unlocks

Genesis allocation (Tokenomist via CoinGecko, 2026-08-04):

| Bucket | Share |
|---|---|
| Future Emissions and Community Rewards (TBD) | 38.89% |
| Genesis Distribution (the airdrop) | 31.00% |
| Core Contributors | 23.80% |
| Hyper Foundation Budget | 6.00% |
| Community Grants | 0.30% |
| HIP-2: Hyperliquidity | 0.01% |

Three things make this unusual:

1. **No venture capital.** Hyperliquid Labs is self-funded and took no external capital (CoinGecko
   project description, 2026-08-04; CFBenchmarks, 2026-06-10). There is no early-investor cliff, no
   seed round at a discount, no lockup expiry from a fund. The scheduled supply overhang is
   *entirely* the team/contributor allocation.
2. **31% went to users** in the Genesis Distribution of 2024-11-29 (the date of the all-time low,
   $3.81), following a points-farming programme run through the closed beta. That is a very large
   community share by 2024-2026 standards.
3. **38.89% is undefined.** "Future Emissions and Community Rewards (TBD)" is more than a third of
   supply with no published schedule. CoinGecko's supply model parks 428,062,211 HYPE in a
   `0xdddd…dddd` future-emissions address. Any long-horizon supply model that ignores this bucket is
   assuming a policy that has not been announced.

**The unlock arithmetic, which is the whole supply story.** Core contributor tokens — roughly 238M —
vest linearly over 24 months from early 2026, close to 9.9M HYPE per month through 2027
(CFBenchmarks, 2026-06-10). The next tranche lands **2026-08-06: 9.92M HYPE, about $550M at
$55.47, 1.0% of total supply** (Tokenomist via CoinGecko, 2026-08-04).

Against that, the buyback spends a *fixed dollar amount* while the unlock releases a *fixed token
amount*. Compare them in tokens:

- At CFBenchmarks' June 2026 run-rate, the buyback retired about **one sixth** of each month's
  unlock, leaving net float growing ~8M HYPE/month, near 100M/year — roughly half of then-circulating
  supply annually.
- At the **2026-08-04** daily print ($1,165,113/day → ~$425M/year → ~$35.4M/month → about
  638,000 HYPE/month at $55.47), the buyback covers roughly **6%** of the 9.92M monthly allowance.

  **Mind the basis before comparing those two lines.** CFBenchmarks quoted ~$1.06B annualised *gross
  fees* alongside ~$0.88B *earnings* (what actually reaches holders through the buyback);
  Token Terminal's daily figures separate *fees* ($1,513,540) from *revenue* ($1,165,113). The
  like-for-like comparison is earnings-to-revenue: ~$425M annualised against CFBenchmarks' ~$0.88B is
  roughly a **halving** of the buyback's funding, which is consistent both with the one-sixth → 6%
  coverage drop and with the "50% revenue drop" framing in the trade press that day. *Two further
  caveats: annualising a single day is noisy, and that particular day's fees were down 35% day over
  day.*
- But if CoinShares is right that actual distributions have run 140k–1.75M/month rather than 9.9M,
  the buyback **exceeds** issuance and HYPE is net deflationary.

These three readings are not reconcilable from public secondary sources. The honest position: the
sign of net float change depends on a variable — observed contributor distributions — that you must
check on-chain yourself before relying on either narrative.

## Turnover and what the market cap actually means

On the comparable single-timestamp pull[^turnover-std], $311.4M of 24h volume against a $12.342B market
cap is **2.52% turnover** — 4th of the ten coins in this directory. (The 2026-08-04 snapshot in the
table above, $280.8M, gives 2.28%; the difference is the pull time, not the asset, and 2.52% is the
figure to use when ranking HYPE against the other nine.) Either way it is healthy: the asset trades across 62 exchanges and 79 markets, with real depth on
several of them, and the market cap is broadly backed by supply someone can actually buy or sell.

Two qualifications:

- **MC/FDV is 0.22.** Only about 22% of the eventual supply is priced into the circulating market cap.
  CFBenchmarks (2026-06-10) argued explicitly that FDV (~$53.7B then, $55.46B on 2026-08-04) is the
  honest denominator for HYPE precisely because contributor tokens are still vesting and the buyback
  must compete with them as they enter float, treating the circulating view as "the optimistic bound."
  That is a defensible position and worth internalising: **the circulating market cap flatters HYPE.**
- **CoinGecko removes the Assistance Fund's 44.5M HYPE from total supply.** That is a modelling
  choice, not a fact about the chain. Those tokens exist and are controlled by a protocol entity. If
  you disagree with the choice, add them back.

Valuation context, for calibration rather than as a view: at June 2026 numbers CFBenchmarks put HYPE
near **61x earnings on FDV** with a **1.6% earnings yield**, against roughly 18–26x forward earnings
for regulated listed trading venues, and noted earnings had "peaked in Q3 2025 and fallen for three
straight quarters." The multiple embeds substantial growth.

## What drives the price

1. **Trading volume, transmitted through the buyback.** This is the dominant mechanic and it is
   mechanical rather than narrative. Between 97% and 99% of net protocol fees flow to the Assistance
   Fund, which buys HYPE continuously on the open market (CFBenchmarks 2026-06-10; VanEck 2026-05-27;
   crypto.news 2026-05-27; CoinShares via etfdb 2026-06-15 says 99%). By May 2026 the fund had
   deployed over **$1.3B**; cumulative protocol revenue crossed **$1B on 2026-06-30**. Estimated
   annualised buyback intensity ran near **7% of market capitalisation** — several times Ethereum's
   burn rate, roughly six times BNB's, and materially above Solana's (crypto.news, 2026-05-27).

   The mechanism has **no floor**. It scales with usage in both directions. A sustained halving of
   volume roughly halves buyback intensity. The 2026-08-04 fee print was down 35% day over day, and a
   99Bitcoins piece the same day was headlined around a 50% revenue drop — the engine had clearly
   slowed from its June peak.

2. **Collateral yield, which is volume-independent.** Hyperliquid holds roughly $5B in USDC posted as
   trader collateral, earning 3.5–4%, with 90% of that income routed to the Assistance Fund and
   Coinbase acting as treasury manager. That contributes an estimated **$140–160M/year** and, crucially,
   keeps feeding the fund regardless of trading activity (CoinShares via etfdb, 2026-06-15).

3. **The unlock calendar**, running against the buyback, as set out above. Monthly, and dated.

4. **Product expansion** — spot, HyperEVM gas, HIP-3 builder-deployed equities/commodities/FX
   auctions. Each adds fee revenue into the same buyback. RWA trading hit a $4B all-time high on
   2026-08-04 (U.Today).

5. **Institutional access vehicles.** Grayscale's HYPG began trading on Nasdaq in June 2026, with
   Bitwise's BHYP and 21Shares' THYP following; spot HYPE ETF inflows were reported at $111M as of
   2026-06-30. Listed treasury companies hold HYPE directly: Hyperliquid Strategies Inc. (PURR.US)
   17.6M HYPE at a $129.5M cost basis, Hyperion DeFi (HYPD.US) 1.93M, Lion Group (LGHL) 194,727 —
   19,724,727 HYPE in tracked public treasuries in total (CoinGecko, 2026-08-04).

6. **Competitive share loss.** CFBenchmarks noted "incentive-driven rivals took share" as earnings
   fell through three quarters. A CoinGecko news item on 2026-08-04 flagged "Trade.xyz Dominance
   Poses Revenue Risk for Hyperliquid." Hyperliquid's ~70% share of on-chain perps volume
   (crypto.news, 2026-07-27) is the number to watch, because it is the numerator of the buyback.

## Market structure and liquidity

62 exchanges, 79 markets (CoinGecko, 2026-08-04). Top venues by 24h volume. *Column convention:
"+2% depth" is resting ask liquidity — what a buyer can lift before price rises 2%; "−2% depth" is
resting bid liquidity — what a seller can hit before price falls 2%.*

| Venue | Pair | 24h volume | Share | +2% depth | −2% depth |
|---|---|---|---|---|---|
| Tapbit | HYPE/USDT | $58.7M | 20.76% | $19,556 | $17,343 |
| Hyperliquid (DEX) | HYPE/USDC | $37.9M | 13.41% | $207,827 | $187,869 |
| Bybit | HYPE/USDT | $26.2M | 9.25% | $521,710 | $502,902 |
| Coinbase International | HYPE/USDC | $17.6M | 6.22% | — | — |
| OKX | HYPE/USDT | $15.5M | 5.49% | $859,722 | $580,296 |
| **Coinbase Exchange** | **HYPE/USD** | **$15.5M** | **5.48%** | **$3,441,465** | **$1,303,641** |
| Gate | HYPE/USDT | $12.9M | 4.54% | $788,377 | $843,705 |
| Hotcoin | HYPE/USDT | $7.9M | 2.78% | $2,033,726 | $1,535,451 |

Two observations worth carrying:

- **Reported volume and actual depth are not the same thing.** Tapbit shows the largest 24h volume
  (20.76% of the total) on roughly $19.5k of ±2% depth. Coinbase Exchange shows a third of Tapbit's
  volume on **$3.44M** of +2% depth — 176 times deeper. When sizing, rank venues by depth, not by
  the volume column.
- **Coinbase Exchange HYPE/USD is the deepest single book in the top ten on the bid side**, which
  matters both for execution and for the backtester section below.

Spread is tight across major venues (0.01–0.02% on Hyperliquid's own book, Bybit, OKX, Coinbase,
Gate). This is a liquid asset by any reasonable standard.

## Known failure modes for traders

1. **The validator put.** On **2025-03-26** a trader opened a large short (reported variously at
   $4.1M / $6M / $8M notional, ~398–430M tokens) on JELLYJELLY, a memecoin with roughly a $9–25M
   market cap, then withdrew margin to self-liquidate and force the position onto HLP. The attacker
   (and others catching on) bid JELLY on spot venues, pushing it up several hundred percent. HLP's
   unrealised loss peaked somewhere between $10M and $13.5M depending on the source, against a vault
   holding roughly $230–290M. Validators convened, voted to delist JELLY perps, and **force-settled
   every open position at $0.0095 — the attacker's entry — rather than the ~$0.50 oracle price**.
   HLP booked a ~$700k *profit*. The Hyper Foundation reimbursed non-flagged users. The attacker's
   remaining withdrawals were frozen.

   Consensus was reached in about two minutes. At the time, five Hyper Foundation validators
   controlled roughly 78% of the 422M staked HYPE (The Defiant, 2025-03-26). Blockworks (2025-03-27)
   named the resulting dynamic a **"validator put"**: an implicit backstop where, if HLP's losses grow
   large enough, the protocol intervenes to cap them. Criticism came from Bitget's Gracy Chen
   ("immature, unethical, and unprofessional", "FTX 2.0"), Arthur Hayes, ZachXBT, Hasu, and
   Wintermute's Evgeny Gaevoy. Binance and OKX listed JELLY perps mid-incident.

   **What this means for you as a trader:** on Hyperliquid, extreme outcomes in illiquid markets can
   be resolved by discretionary governance rather than by the published rules. That protects the
   vault and, in this case, protected most users. It also means your position in a thin market is not
   guaranteed to settle at the price the rulebook implies. Do not model tail scenarios in low-cap
   Hyperliquid perps as if the rules are the whole story.

2. **HLP tail risk, which recurs with new vectors.** JELLY (March 2025, ~$12M realised, resolved by
   validator delist). A POPCAT manipulation using a fake ~$10M buy wall left HLP with ~$4.9M in bad
   debt and prompted a temporary pause of the Arbitrum bridge (CoinGecko HLP analysis, 2026-07-02;
   that source does not date the event). FARTCOIN (April 2026): four freshly funded wallets built a
   $15M long, pushed price ~27%, then triggered a "suicide liquidation" in thin liquidity — this time
   the toxic position reached HLP via **auto-deleveraging (ADL)** — the exchange's mechanism for
   force-closing profitable opposing positions when a liquidation cannot be absorbed — rather than a
   validator delist, costing the vault ~$1.5M, with ~$849k randomly awarded to short traders by ADL.
   Post-JELLY hardening
   (leverage caps cut to 40x BTC / 25x ETH, revised listing rules, dynamic OI caps scaling with market
   cap, liquidator vault capped as a share of HLP with isolated collateral) reduced blast radius from
   ~$12M to ~$1.5M. **Progress, not a solved problem.** Every newly listed perp is a fresh surface.

3. **A 27-validator network securing a $200B+/month venue.** The set grew 4 → 16 (Jan 2025) → 21
   (permissionless from 2025-04-21) → 24 → 27 (June 2026). Foundation-run validators — five of the 27 —
   held about **49.3% of staked HYPE** as of the June 2026 redelegations, down from a reported 81% in
   early 2025 (crypto.news, 2026-07-27). Other counts circulate: ~31 registered with 24 active and
   ~430M HYPE staked (CoinTab, 2026-05-27). Governance is **stake-weighted, not headcount-weighted**,
   so the concentration figure *is* the governance figure.

   Compare 27 validators to roughly 1,800 on Solana and hundreds of thousands on Ethereum. The
   technical defence is legitimate — BFT safety needs an honest supermajority, not a large set, and
   the small set is what buys sub-second finality and makes an on-chain order book viable at all. The
   risk it leaves is not cryptographic but social and regulatory: 27 operators are 27 jurisdictions
   to subpoena and 27 relationships to pressure, and the Foundation's near-half stake means far fewer
   conversations decide most outcomes.

4. **Closed-source node software.** Validators run a binary they cannot audit (HIPERWIRE 2026-03-04;
   ainvest 2026-08-02). Single-client architecture means protocol upgrades are mandatory for consensus
   participation, concentrating implementation risk in the Foundation's codebase. There is also **no
   automatic slashing anywhere in the system** — no operator loses stake for a mistake, and none loses
   stake for misbehaviour either. The unstaking queue and social consequences are the enforcement
   layer.

5. **Validator jailing and curated expansion.** Validators can be jailed by peer vote for latency and
   reliability failures (no slashing attached), which is standard PoS practice — but peer voting is
   stake-weighted, and when Foundation-affiliated nodes hold near half the stake, the mechanism is
   only as neutral as the stake distribution. The Delegation Program that helps new validators reach
   the active set requires KYC/KYB and excludes several jurisdictions including the **United States**
   and Ontario, so set expansion is curated rather than open.

6. **Regulatory posture.** Singapore's MAS added Hyperliquid to its **Investor Alert List on
   2026-06-26** — a register of entities consumers might wrongly believe are licensed. Not a ban, not
   an enforcement action, no finding of wrongdoing; Bybit was added nine days earlier, KuCoin in
   February, Binance since 2021. But it is a data point on how regulators view a high-leverage,
   no-KYC venue. Gracy Chen's 2025 critique that Hyperliquid "operates more like an offshore CEX with
   no KYC/AML" is self-interested and also not obviously wrong.

7. **The buyback is policy, not a contract.** CFBenchmarks makes this explicit: the buyback "is a
   protocol policy, not a contractual dividend, and could in principle be changed by governance."
   Combine that with un-formalised Assistance Fund withdrawal conditions (Giants, 2026-04-17) and the
   whole value-accrual thesis rests on continued governance choices by an entity holding ~49% of stake.

8. **Concentration in the token itself.** Public treasury companies hold ~19.7M HYPE. Hyperliquid
   Strategies Inc.'s 17.6M position alone is ~8% of circulating supply and sits on a ~7.5x unrealised
   gain against its $129.5M cost basis. Forced or discretionary selling from these vehicles is a real
   flow.

## For this backtester

**HYPE is listed on Coinbase and is fetchable.**

- **Coinbase Exchange spot, `HYPE-USD`**, live since **2026-02-05** (Coinbase Markets announcement).
  24h volume $15.5M with +2% depth of $3.44M and −2% depth of $1.30M on 2026-08-04 — the deepest book
  in the top ten on the bid side. A Coinbase-API OHLCV fetcher should retrieve `HYPE-USD` cleanly.
- **History starts 2026-02-05 on Coinbase, but the token launched 2024-11-29.** That is roughly
  14 months of price history that Coinbase does *not* have. If your study needs the 2024–2025 period —
  which includes the JELLY incident, the October 2025 flash crash, and the entire first bull leg from
  $3.81 to the mid-$50s — you must source it elsewhere (Hyperliquid's own API, or an aggregator) and
  reconcile the venues. **Do not silently splice.**
- Coinbase International Exchange has carried `HYPE-PERP` since **2025-06-05** and `HYPE/USDC` spot.
  Different venue, different API, different fee schedule.
- Deep secondary venues exist if you need cross-checks: Bybit, OKX, Gate, and Hyperliquid's own
  HYPE/USDC book (which had $207.8k/$187.9k ±2% depth on 2026-08-04 — thinner than Coinbase's).
- **Modelling note.** If you are comparing a HYPE strategy against a Jupiter-perps strategy, the
  execution models are not interchangeable. Jupiter fills at an oracle price with a flat fee and no
  slippage; Hyperliquid fills against a book. Reusing a Jupiter zero-slippage fill assumption on
  Hyperliquid data will overstate returns, and the error grows with size and with market thinness.
- **Regime-break warning.** Protocol revenue peaked in Q3 2025 and fell for three straight quarters
  (CFBenchmarks, 2026-06-10), while price roughly tripled from a ~$25 January 2026 open to a $76.87
  June high. Fundamentals and price decoupled sharply over that window. Any factor model that assumes
  a stable price-to-revenue relationship will fit one regime and fail in the other.

## Sources

Fetched or consulted 2026-08-04 unless noted.

- CoinGecko — Hyperliquid (HYPE) coin page: price, supply model with named on-chain addresses,
  allocation, unlock schedule, fee/revenue via Token Terminal, markets and depth table, treasuries.
  https://www.coingecko.com/en/coins/hyperliquid
- CFBenchmarks, "Pricing the Perp DEX Leader: A Valuation Framework for Hyperliquid" (2026-06-10) —
  FDV-based valuation, ~$1.06B annualised fees / ~$0.88B earnings, 97–99% fee share to the Assistance
  Fund, ~9.9M/month contributor vesting, buyback-versus-unlock arithmetic, ETF listings.
  https://www.cfbenchmarks.com/blog/pricing-the-perp-dex-leader-a-valuation-framework-for-hyperliquid
- VanEck, "Exploring Hyperliquid: Redefining Derivatives Trading" (2026-05-27) — Q1 2026 volume,
  cumulative buybacks to end-April 2026, fund holdings and average cost, 11-person core team.
  https://www.vaneck.com/pl/en/blog/digital-assets/exploring-hyperliquid-redefining-derivatives-trading/
- Giants Tokenomics Lab, "HYPE Tokenomics: How Hyperliquid's Fee-Funded Buyback Actually Works"
  (2026-04-17) — the accumulate-versus-burn distinction and un-formalised fund withdrawal conditions.
  https://giantslabs.pro/models/hype-tokenomics/
- CoinShares via etfdb, "Inside Hyperliquid: How the Fee Engine Works" (2026-06-15) — 99% fee routing,
  ~$5B USDC reserve yield ($140–160M/yr), actual versus scheduled vesting distributions.
  https://etfdb.com/coinshares-crypto-etf-hub/coinshares-channel/hyperliquid-fee-engine-works/
- crypto.news, "Why HYPE is different: inside Hyperliquid's buyback" (2026-05-27) — ~7% of market cap
  annualised buyback, comparison to ETH/BNB/SOL burn rates, volume-decline sensitivity.
  https://crypto.news/why-hype-is-different-inside-hyperliquids-buyback/
- crypto.news, "Who actually runs Hyperliquid? The governance audit" (2026-07-27) — validator set
  growth 4→27, 49.3% foundation stake, jailing mechanics, no slashing, MAS Investor Alert List.
  https://crypto.news/who-actually-runs-hyperliquid-the-governance-audit/
- perp.wiki, "HYPE Buyback & Burn" (2026-03-28) and "HLP Vault Review" (2026-03-07) — describes
  buybacks as burns (conflicts with other sources); HLP return range and drawdown history.
  https://perp.wiki/learn/hype-buyback-burn-explained · https://perp.wiki/learn/hlp-vault-guide
- CoinGecko Research, "How Hyperliquid's HLP Vault Turns Market Chaos Into Profit" (2026-07-02) —
  $136.9M cumulative profit, TVL peak and decline, Oct 2025 and Jan 2026 event attribution, POPCAT.
  https://www.coingecko.com/learn/hyperliquid-hlp-vault-analysis
- VaultVision, "Hyperliquid HLP Model Explained" (2026-04-17) — 4-day lockup, FARTCOIN April 2026 ADL
  incident, post-JELLY leverage caps.
  https://vaultvision.tech/blog/how-hlp-works-hyperliquid-vault
- DefiLlama — Hyperliquid HLP: TVL $219.88M, HLP fee-share methodology (1% of perp/spot revenue),
  quarterly income statement. https://defillama.com/protocol/hyperliquid-hlp
- Hyperliquid docs — HyperCore staking: delegated PoS, 10k HYPE self-delegation locked 1 year,
  quorum >2/3 stake, 100k-round (~90 min) epochs, commission rules.
  https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/staking
- Hyperliquid docs — protocol vaults (HLP definition).
  https://hyperliquid.gitbook.io/hyperliquid-docs/hypercore/vaults/protocol-vaults
- Hyperliquid community wiki — validator requirements, Delegation Program KYC/jurisdiction
  restrictions, HLP strategy addresses, HLP ≈7% of platform fees and <2% of daily volume, and the
  2025-03-26 incident timeline with transaction hashes.
  https://hyperliquid-co.gitbook.io/wiki/architecture/hyperbft/validator ·
  https://hyperliquid-co.gitbook.io/community-docs/introduction/roadmap/2025-26-03_incident
- Blockworks, "A perp too far: Hyperliquid's 'validator put'" (2025-03-27) — the governance critique.
  https://blockworks.co/news/hyperliquid-decentralization-validator-put
- The Defiant (2025-03-26) — five foundation validators controlling ~78% of 422M staked HYPE at the
  time of the JELLY vote.
  https://thedefiant.io/news/defi/hyperliquid-token-tanks-as-another-vault-attack-sparks-controversy
- CoinDesk (2025-03-26), Decrypt (2025-03-26), Bitcoin.com News (2025-03-26), FXStreet (2025-03-26),
  Halborn (2025-04-02) — JELLY incident figures, which differ between sources.
- HIPERWIRE, "How Hyperliquid Governance Works" (2026-03-04) — HyperBFT finality/throughput,
  closed-source node software, bridge multisig.
  https://hiperwire.io/explainers/hyperliquid-governance-validators-decentralization
- Coinbase Markets announcement — HYPE spot trading live 2026-02-05; Coinbase International HYPE-PERP
  from 2025-06-05.
- Jupiter documentation and support — JLP 75% fee share, utilisation-based hourly borrow fee formula,
  oracle sourcing. https://docs.jup.ag/user-docs/trade/perps-and-jlp ·
  https://support.jup.ag/hc/en-us/articles/18735045234588-What-are-the-fees-associated-with-Jupiter-Perps
- dailycoinbrief (2026-07-05) — $1B cumulative protocol revenue crossed 2026-06-30, Q1 2026 volume,
  ETF inflows. https://dailycoinbrief.com/hype-just-crossed-1-billion-in-protocol-revenue/

[^turnover-std]: **Comparable turnover.** All ten coins' turnover figures in this directory come from ONE CoinGecko `/coins/markets` call, `~/dev/solmargintrader/research/results/top_coins.csv`, **2026-08-05T02:15:22Z**. Turnover is 24h volume / market cap and both terms move continuously, so figures pulled at different times cannot be ranked against each other — doing that produced a real error, a claim that SOL had the highest turnover of the ten when the single-timestamp pull puts DOGE ahead. Canonical table, highest to lowest: DOGE 3.44%, SOL 3.32%, ETH 3.05%, HYPE 2.52%, ZEC 2.30%, BTC 1.78%, TRX 1.45%, XRP 1.37%, BNB 0.73%, RAIN 0.24% — a 14.4x spread, one order of magnitude. Regenerate and verify with `python3 research/turnover_table.py` and `--check`. verified-as-of: 2026-08-05
