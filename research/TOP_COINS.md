# Top crypto coins — universe file

**AS OF 2026-08-05T02:15:22+00:00** (UTC). Source: CoinGecko `/coins/markets`, ranked by market cap.
Machine-readable copy: `research/results/top_coins.csv`. Regenerate rather than edit by hand —
every figure here came from that one API call and none is transcribed.

> Prices move. This is a snapshot for building a universe, not a quote. Cross-check before use:
> SOL reads $74.16 here, which agrees with the ~$73-74 the repo's own
> `research/RANKED_LISTS.md` snapshot ends on — that agreement is why this pull is trusted.

## The literal top 10 by market cap

| # | Symbol | Name | Price USD | Market cap $B | 24h vol $B | Pegged? | Local data? |
|---|---|---|---|---|---|---|---|
| 1 | `BTC` | Bitcoin | 64,401.0000 | 1,292.1 | 23.03 | no | yes |
| 2 | `ETH` | Ethereum | 1,873.8300 | 226.1 | 6.90 | no | yes |
| 3 | `USDT` | Tether | 0.9993 | 183.1 | 35.54 | **yes** | no |
| 4 | `BNB` | BNB | 602.7600 | 80.3 | 0.59 | no | no |
| 5 | `USDC` | USDC | 0.9997 | 72.2 | 10.36 | **yes** | no |
| 6 | `XRP` | XRP | 1.0740 | 67.2 | 0.92 | no | no |
| 7 | `SOL` | Solana | 74.1600 | 43.1 | 1.43 | no | yes |
| 8 | `TRX` | TRON | 0.3267 | 31.0 | 0.45 | no | no |
| 9 | `FIGR_HELOC` | Figure Heloc | 1.0030 | 21.0 | 0.04 | **yes** | no |
| 10 | `HYPE` | Hyperliquid | 55.4800 | 12.3 | 0.31 | no | no |

**3 of the top 10 are pegged assets.** They are in the list because the request said
market cap and that is what market cap says. They are marked because a trading universe that
treats them as directional candidates is broken by construction:

- `USDT` — fiat-collateralised stablecoin (quote asset)
- `USDC` — fiat-collateralised stablecoin (quote asset)
- `FIGR_HELOC` — tokenised HELOC / RWA, trades at ~$1.00

## The tradeable top 10 (pegged assets removed)

This is the list to actually point a directional strategy at.

| # | Symbol | Name | Price USD | Market cap $B | 24h vol $B | Local data? |
|---|---|---|---|---|---|---|
| 1 | `BTC` | Bitcoin | 64,401.0000 | 1,292.1 | 23.03 | yes |
| 2 | `ETH` | Ethereum | 1,873.8300 | 226.1 | 6.90 | yes |
| 3 | `BNB` | BNB | 602.7600 | 80.3 | 0.59 | **no** |
| 4 | `XRP` | XRP | 1.0740 | 67.2 | 0.92 | **no** |
| 5 | `SOL` | Solana | 74.1600 | 43.1 | 1.43 | yes |
| 6 | `TRX` | TRON | 0.3267 | 31.0 | 0.45 | **no** |
| 7 | `HYPE` | Hyperliquid | 55.4800 | 12.3 | 0.31 | **no** |
| 8 | `DOGE` | Dogecoin | 0.0702 | 10.9 | 0.38 | **no** |
| 9 | `RAIN` | Rain | 0.0125 | 8.7 | 0.02 | **no** |
| 10 | `ZEC` | Zcash | 513.2200 | 8.6 | 0.20 | **no** |

## The constraint that matters for this repo

**This project holds price data for 3 of them: BTC, ETH, SOL** (`data/`, plus `JLP_spot.csv`).
Nothing in `backtester/` can evaluate a strategy over the other seven until
`backtester.core.fetch` is pointed at them and a local cache is written. Any claim about a
top-10 universe strategy before that fetch is a claim about three assets wearing ten names.

Liquidity is the second constraint and it is steeper than the ranking suggests: 24h volume
spans 0.02B to 23.03B across the tradeable ten. A strategy sized for BTC's book
is not executable on the thin end, and a backtest that ignores that will report a number the
venue would never have filled.

## Why this lives in `research/` and not `data/`

`data/` is gitignored — it is the local price cache that `backtester.core.fetch` writes, and
nothing in it is tracked. This file is a decision record about which assets are worth
trading, not cached market data, so it belongs with the research it informs.

## Regenerate

```bash
curl -s 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd\
&order=market_cap_desc&per_page=15&page=1&sparkline=false'
```
