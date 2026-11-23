# Cross-chain short replay re-read with exchange fees removed

Date: 2026-11-22. Source: the frozen cross-chain replay of PR #361,
`/Users/mitch/.local/share/solmargintrader/audits/cross-chain-short-20261122/final/per-asset-results.csv`.
Reproduce with
`python3 /Users/mitch/.local/share/solmargintrader/audits/cross-chain-short-20261122/zero_fee_reread.py`
(output saved as
`/Users/mitch/.local/share/solmargintrader/audits/cross-chain-short-20261122/zero-fee-reread.json`).

## Method

The re-read adds each run's recorded `fees_usd` back to its net result.
It does not re-simulate any trade. Slippage (2 bps per side standard,
6 bps worse fills) and recorded funding stay in. Each coin and strategy
started with its own $1,000 paper balance and traded $250 notional at
modeled 25x from Oct 12 to Nov 16, 2026 on Binance USD-M one-minute data.
The original replay charged a 5 bps taker fee per side.

## Result: fees decide the Z-score short

| Strategy, fills | Median net with fees | Median net, zero fee | Profitable coins with fees | Profitable coins, zero fee | All 5 weeks positive, zero fee |
|---|---:|---:|---:|---:|---:|
| Z-score short, standard | -$15.27 | **+$2.26** | 50/300 | **170/300** | 19 |
| Z-score short, worse | -$26.57 | -$9.34 | 10/300 | 82/300 | 4 |
| Volty short, standard | -$63.94 | -$2.22 | 26/300 | 146/300 | 17 |
| Volty short, worse | -$118.41 | -$53.70 | 1/300 | 36/300 | 1 |

Fees took a median $17.15 per coin from the Z-score short (61 trades)
and $63.73 per coin from the Volty short (about 250 trades). Removing fees moves the median Z-score coin from a loss to a small
profit. Volty stays negative on the median coin even at zero fee.

## Strongest coins for the Z-score short at zero fee

Standard fills, $1,000 paper balance, Oct 12 - Nov 16, 2026.

| Coin | Zero-fee net | Net with fees | Trades | Max drawdown | Liquidations | Zero-fee positive weeks | Passed liquidity screen |
|---|---:|---:|---:|---:|---:|---:|---|
| T | +$45.89 | +$26.00 | 72 | 0.82% | 1 | 5/5 | no |
| SYRUP | +$42.84 | +$26.21 | 59 | 1.14% | 1 | 5/5 | no |
| POL | +$39.02 | +$26.04 | 52 | 0.57% | 0 | 5/5 | yes |
| DATA | +$34.56 | +$13.92 | 75 | 1.64% | 1 | 4/5 | no |
| JTO | +$31.43 | +$17.20 | 57 | 0.75% | 0 | 5/5 | yes |

Under worse fills T, SYRUP and POL stay positive in all five weeks;
JTO and FARTCOIN stay positive in four.

## Limits

- The ranking is in-sample. The top coins were picked from the same five
  weeks out of 300 tested, so some of the edge is selection luck. Treat
  POL and JTO, which also pass the liquidity screen and had no liquidation,
  as candidates for a fresh paper period, not as proven.
- Zero fee is not zero cost. A venue that waives fees can add a taker
  delay, a wider spread or a retail-only condition. The venue research
  below records those terms.
- Prices and funding are Binance's. Another venue's book, funding and
  listing set differ.

## Where the strategy can run at zero or near-zero fee

Venue research ran as `/dr` slug `zero-fee-perpetual-futures-venues-with-api-access`
(`/Users/mitch/.global-ai-hub/research/zero-fee-perpetual-futures-venues-with-api-access`).
Listings came from each venue's public market endpoint on 2026-11-22; the snapshot is in
`/Users/mitch/.local/share/solmargintrader/audits/zero-fee-venues-20261122/listings-20261122T2100Z`.

Evidence status, 2026-11-23. The run finished after research-gate/v4 validated 478 of
the 660 bound claims (513 SUPPORTED assertions, no unresolved conflicts). Gated claims
back the fee, delay, rate-limit and API cells for Lighter, Paradex, Bullet, Bitfinex and
MEXC, the Lighter, Paradex and Hyperliquid US-person bars, and Kraken's $0.0113
per-contract fee. These cells rest only on raw endpoint snapshots or direct page reads,
not on gated claims: the per-coin listing column, the Bullet and Bitfinex US-person
terms, Kraken's 16-contract list and Coinbase's coin coverage. The listing-count claims
were dropped because they were derived from API extracts with no bound raw response.
The gated reference is `trading-and-investing/references/zero-fee-perpetual-futures-venues-with-api-access.md`
in the skills repository; the family index is
`/Users/mitch/.global-ai-hub/llms-concepts/zero-fee-perpetual-futures-venues.family/llms.txt`.

| Venue | Perp fee for API orders | API order entry | Lists POL / JTO / SUI / SYRUP / FARTCOIN / HBAR | US persons |
|---|---|---|---|---|
| Lighter (Standard account) | 0 maker / 0 taker; taker orders and cancels wait 300 ms; 60 requests/min | Signed `sendTx` (official SDKs) | yes / yes / yes / yes / yes / yes | Barred by its terms |
| Paradex (Retail order via interactive token) | 0 / 0; 300 ms delay; 1,000 orders per 24 h. Default API orders are Pro and pay 0.5 bps maker, 1.75-4.5 bps taker | REST and WebSocket, Starknet signing | - / yes / yes / - / - / - | Barred |
| Bullet | 0 / 0; keeps 5% of funding payments | Binance-FAPI-compatible REST and WebSocket | only majors (30 markets) | Barred (T&C section 4) |
| Bitfinex | 0 / 0 on derivatives | REST and WebSocket | thin perp list | Barred except Eligible Contract Participants |
| MEXC | API orders pay 0.06% / 0.08%; the 0-fee offer excludes API users | REST | broad | not established |
| Kraken Derivatives US (Bitnomial perps) | $0.0113 per contract per side, about 0.44 bps on HBAR | FIX 4.4 order entry | HBAR only (16 contracts: ADA, AAVE, AVAX, BCH, BTC, DOGE, DOT, ETH, HBAR, LINK, LTC, SHIB, SOL, XLM, XRP, XTZ) | **Allowed (CFTC-regulated)** |
| Coinbase Derivatives (perp-style futures) | $0.10 exchange fee per contract plus commission; about 4.6 bps per side on SUI at the $0.15 floor | Advanced Trade API | SUI, HBAR (24 crypto underlyings) | Allowed |

Every offshore venue that waives fees bars US persons, and using a VPN to get around the
bar breaches each venue's terms. For a US person the practical near-zero route is Kraken
Derivatives US. Re-costing the replay at 0.5 bps per side (an upper bound for Kraken's
per-contract fee on these coins) gives the Z-score short, over $1,000 per coin:

| Coin on Kraken US | Standard fills | Worse fills | Positive weeks |
|---|---:|---:|---:|
| XTZ | +$24.16 | +$12.79 | 4/5 |
| HBAR | +$21.68 | +$11.60 | 4/5 |
| SOL | +$18.70 | +$5.54 | 4/5 |
| XRP | +$14.28 | +$2.39 | 4/5 |
| DOGE | +$12.85 | +$2.36 | 4/5 |

These use Binance prices and funding, not Kraken's, and Kraken's books may be thinner.
Whether a retail Kraken Pro account can obtain a FIX API key was not verified.
