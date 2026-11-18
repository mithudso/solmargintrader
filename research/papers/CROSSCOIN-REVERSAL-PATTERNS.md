# Ten-minute UP-bar reversals across coins

The two-UP-bars rule does not establish a general 70% probability. In the full 30-day KuCoin archive, the next 10-minute candle closed DOWN after UU in 148/420 HYPE cases (35.2%; 117 flat), 538/1032 ETH cases (52.1%), 548/1028 BTC cases (53.3%) and 524/972 SOL cases (53.9%). Native zero-volume rows matter: the conservative positive-volume screen leaves 89, 168, 138 and 44 UU observations respectively, with DOWN rates of 58.4%, 51.8%, 47.8% and 40.9%. These screens describe different subsets. Future positive-volume eligibility is known retrospectively and cannot serve as an entry filter.

The common Coinbase day produced BTC 19/24 (79.2%) and ZEC 19/24 (79.2%) next-bar DOWN counts. This is a small sample from a bearish day: the unconditional DOWN count was 83/144 (57.6%) for BTC and 78/143 (54.5%) for ZEC. The periods and venues differ, so these figures do not establish 70% live odds. The 30-day midpoint reversal results are near chance: after UU, prices were lower ten minutes after detection in 69/167 HYPE cases (41.3%), 389/703 ETH cases (55.3%), 336/687 BTC cases (48.9%) and 336/641 SOL cases (52.4%).

Descriptive replication with fixed ZEC definitions. Each row uses native one-minute OHLCV.
A DOWN endpoint means the price ten minutes after the signal close is lower than that close.
Maximum favorable excursion (MFE) is the largest later fall from the reference price; it is not an attainable profit.

## Midpoint rule: first eligible below-open one-minute close at minutes 5–9

| Venue / period | Coin | Setup | Lower after 10m | Mean MFE | Maximum MFE | Mean endpoint decline |
|---|---|---|---:|---:|---:|---:|
| KuCoin / 2026-10-10 | HYPE | one UP / bar 2 | 99/251 (39.4%) | 0.1788% | 1.5519% | 0.0050% |
| KuCoin / 2026-10-10 | HYPE | UU / bar 3 | 69/167 (41.3%) | 0.1638% | 1.2862% | -0.0246% |
| KuCoin / 2026-10-10 | ETH | one UP / bar 2 | 363/700 (51.9%) | 0.1363% | 2.8105% | 0.0155% |
| KuCoin / 2026-10-10 | ETH | UU / bar 3 | 389/703 (55.3%) | 0.1201% | 1.4361% | 0.0137% |
| KuCoin / 2026-10-10 | BTC | one UP / bar 2 | 367/710 (51.7%) | 0.0961% | 1.0108% | 0.0129% |
| KuCoin / 2026-10-10 | BTC | UU / bar 3 | 336/687 (48.9%) | 0.0827% | 0.9057% | 0.0010% |
| KuCoin / 2026-10-10 | SOL | one UP / bar 2 | 326/660 (49.4%) | 0.1553% | 2.5681% | 0.0192% |
| KuCoin / 2026-10-10 | SOL | UU / bar 3 | 336/641 (52.4%) | 0.1480% | 2.3785% | 0.0128% |
| Coinbase Exchange / 2026-11-12 | HYPE | one UP / bar 2 | 8/15 (53.3%) | 0.2910% | 0.7369% | -0.0036% |
| Coinbase Exchange / 2026-11-12 | HYPE | UU / bar 3 | 6/11 (54.5%) | 0.2966% | 0.5249% | 0.0290% |
| Coinbase Exchange / 2026-11-12 | ETH | one UP / bar 2 | 15/25 (60.0%) | 0.2063% | 0.7085% | 0.0778% |
| Coinbase Exchange / 2026-11-12 | ETH | UU / bar 3 | 16/28 (57.1%) | 0.1532% | 0.4278% | 0.0152% |
| Coinbase Exchange / 2026-11-12 | BTC | one UP / bar 2 | 15/23 (65.2%) | 0.2316% | 0.8480% | 0.0910% |
| Coinbase Exchange / 2026-11-12 | BTC | UU / bar 3 | 14/22 (63.6%) | 0.1343% | 0.3068% | 0.0530% |
| Coinbase Exchange / 2026-11-12 | SOL | one UP / bar 2 | 15/25 (60.0%) | 0.2056% | 0.6984% | 0.0213% |
| Coinbase Exchange / 2026-11-12 | SOL | UU / bar 3 | 12/20 (60.0%) | 0.1821% | 0.3650% | 0.0269% |
| Coinbase Exchange / 2026-11-12 | ZEC | one UP / bar 2 | 15/26 (57.7%) | 0.6569% | 2.4916% | 0.1788% |
| Coinbase Exchange / 2026-11-12 | ZEC | UU / bar 3 | 13/20 (65.0%) | 0.5390% | 2.1004% | 0.1400% |

## Completed UU setup: next ten-minute candle color

This is the original two-completed-UP-bars question. It does not require an intrabar reversal.
| Venue | Coin | Next DOWN after UU | Unconditional DOWN | Flat next bars after UU |
|---|---|---:|---:|---:|
| KuCoin | HYPE | 148/420 (35.2%) | 1307/4320 (30.3%) | 117 |
| KuCoin | ETH | 538/1032 (52.1%) | 2174/4320 (50.3%) | 3 |
| KuCoin | BTC | 548/1028 (53.3%) | 2188/4320 (50.6%) | 3 |
| KuCoin | SOL | 524/972 (53.9%) | 2132/4320 (49.4%) | 28 |
| Coinbase Exchange | HYPE | 7/15 (46.7%) | 54/110 (49.1%) | 1 |
| Coinbase Exchange | ETH | 18/32 (56.2%) | 78/144 (54.2%) | 0 |
| Coinbase Exchange | BTC | 19/24 (79.2%) | 83/144 (57.6%) | 0 |
| Coinbase Exchange | SOL | 16/25 (64.0%) | 77/144 (53.5%) | 2 |
| Coinbase Exchange | ZEC | 19/24 (79.2%) | 78/143 (54.5%) | 0 |

## Coverage and qualifications

| Venue | Coin | Study window, UTC (end exclusive) | Input present / expected minutes (includes buffers) | Zero volume |
|---|---|---|---:|---:|
| KuCoin USDC | HYPE | 2026-10-10T20:20:00Z to 2026-11-09T20:20:00Z | 43200/43200 | 34008 |
| KuCoin USDC | ETH | 2026-10-10T20:20:00Z to 2026-11-09T20:20:00Z | 43200/43200 | 8441 |
| KuCoin USDC | BTC | 2026-10-10T20:20:00Z to 2026-11-09T20:20:00Z | 43200/43200 | 8802 |
| KuCoin USDC | SOL | 2026-10-10T20:20:00Z to 2026-11-09T20:20:00Z | 43200/43200 | 12670 |
| Coinbase Exchange USD | HYPE | 2026-11-12T05:00:00Z to 2026-11-13T05:00:00Z | 1411/1480 | 0 |
| Coinbase Exchange USD | ETH | 2026-11-12T05:00:00Z to 2026-11-13T05:00:00Z | 1480/1480 | 0 |
| Coinbase Exchange USD | BTC | 2026-11-12T05:00:00Z to 2026-11-13T05:00:00Z | 1480/1480 | 0 |
| Coinbase Exchange USD | SOL | 2026-11-12T05:00:00Z to 2026-11-13T05:00:00Z | 1480/1480 | 0 |
| Coinbase Exchange USD | ZEC | 2026-11-12T05:00:00Z to 2026-11-13T05:00:00Z | 1479/1480 | 0 |

- KuCoin uses USDC, Coinbase uses USD. Their periods differ. Do not pool them.
- Legacy *_usd numeric fields mean quote currency per coin: USDC for KuCoin and USD for Coinbase. Event IDs must be read with their coin, venue, quote and source hash. Positive endpoint decline means a fall; negative means a rise.
- Explicit zero-volume provider rows remain visible. Missing minutes are never filled. The complete positive-volume sensitivity is archived separately for every setup and outcome.
- The original ZEC study uses receipt-time trades. These histories use exchange-time candles; a candle-complete history does not establish the original tick-feed gap screening.
- Primary intrabar checks minutes 1–9; midpoint checks 5–9; close confirmation checks minute 10. A midpoint trigger may have first crossed below the open before minute 5.
- One UP means the previous bar is UP and the older bar is not UP. UU means the last two closed bars are UP, including longer runs. There is no DOWN/DOWN/UP signal.
- Each signal uses only already closed one-minute observations. Subsequent excursions exclude the signal minute. Five, ten and twenty minute outcomes, next-minute-open references and non-overlapping windows are retained. Overlap reservation occurs before checking future coverage.
- Flat endpoints stay in denominators. Endpoint DOWN, any lower low, and candle color answer different questions. MFE maxima are historical observations with event IDs, not targets.
- Descriptive Wilson intervals ignore temporal dependence. Events across policies, masks and nearby windows are not independent opportunities. No dates or parameters were selected by performance; this remains exploratory and has no prospective validation.
- There are no executable fills, spread/slippage/fee estimates or net profit here. These findings do not qualify any coin or strategy for live orders.

## Positive-volume sensitivity: midpoint rule, following ten minutes

| Venue | Coin | Setup | Lower endpoint | Mean MFE | Maximum MFE | Mean endpoint decline |
|---|---|---|---:|---:|---:|---:|
| KuCoin | HYPE | one UP / bar 2 | 33/73 (45.2%) | 0.1686% | 0.8145% | -0.0243% |
| KuCoin | HYPE | UU / bar 3 | 35/64 (54.7%) | 0.1755% | 0.9251% | 0.0232% |
| KuCoin | ETH | one UP / bar 2 | 59/120 (49.2%) | 0.2215% | 1.8030% | 0.0096% |
| KuCoin | ETH | UU / bar 3 | 57/108 (52.8%) | 0.2045% | 0.8322% | -0.0071% |
| KuCoin | BTC | one UP / bar 2 | 37/74 (50.0%) | 0.1823% | 1.0108% | 0.0080% |
| KuCoin | BTC | UU / bar 3 | 37/84 (44.0%) | 0.1655% | 0.9057% | -0.0187% |
| KuCoin | SOL | one UP / bar 2 | 18/28 (64.3%) | 0.2951% | 1.8681% | 0.0218% |
| KuCoin | SOL | UU / bar 3 | 11/22 (50.0%) | 0.2398% | 0.8692% | -0.0215% |

## Early intrabar rule: minutes 1–9, following ten minutes

| Venue | Coin | Setup | Lower endpoint | Mean MFE | Maximum MFE |
|---|---|---|---:|---:|---:|
| KuCoin | HYPE | one UP / bar 2 | 108/269 (40.1%) | 0.1742% | 1.3295% |
| KuCoin | HYPE | UU / bar 3 | 78/187 (41.7%) | 0.1686% | 1.2862% |
| KuCoin | ETH | one UP / bar 2 | 427/839 (50.9%) | 0.1280% | 3.9537% |
| KuCoin | ETH | UU / bar 3 | 444/804 (55.2%) | 0.1212% | 1.1040% |
| KuCoin | BTC | one UP / bar 2 | 443/843 (52.6%) | 0.0933% | 1.3480% |
| KuCoin | BTC | UU / bar 3 | 418/800 (52.2%) | 0.0878% | 1.7245% |
| KuCoin | SOL | one UP / bar 2 | 404/787 (51.3%) | 0.1374% | 1.4818% |
| KuCoin | SOL | UU / bar 3 | 407/736 (55.3%) | 0.1499% | 2.5078% |
| Coinbase Exchange | HYPE | one UP / bar 2 | 12/19 (63.2%) | 0.2919% | 1.1185% |
| Coinbase Exchange | HYPE | UU / bar 3 | 7/12 (58.3%) | 0.3462% | 1.2811% |
| Coinbase Exchange | ETH | one UP / bar 2 | 16/30 (53.3%) | 0.1799% | 1.0278% |
| Coinbase Exchange | ETH | UU / bar 3 | 16/31 (51.6%) | 0.1746% | 0.6749% |
| Coinbase Exchange | BTC | one UP / bar 2 | 18/31 (58.1%) | 0.1808% | 0.9604% |
| Coinbase Exchange | BTC | UU / bar 3 | 16/23 (69.6%) | 0.1521% | 0.4303% |
| Coinbase Exchange | SOL | one UP / bar 2 | 12/32 (37.5%) | 0.2010% | 0.7592% |
| Coinbase Exchange | SOL | UU / bar 3 | 16/25 (64.0%) | 0.2073% | 0.8345% |
| Coinbase Exchange | ZEC | one UP / bar 2 | 18/34 (52.9%) | 0.5027% | 1.5165% |
| Coinbase Exchange | ZEC | UU / bar 3 | 17/23 (73.9%) | 0.6308% | 2.1429% |

## Reproduction and native evidence

Version: 1.1.0. All windows and policies were frozen before calculation. Repository .json.zlib containers preserve the exact native artifact text and its decoded content; the family manifest records both hashes. The nine immutable source archives retain original provider responses and their SHA256 values. Each result archive contains72 aggregate rows, exact selected event records and all5/10/20-minute outcomes. The family llms index binds every input/output to the Mongo run and its immutable artifact ID. Client archival records remain unverified empirical material; they are not trusted literature publication proof. No paid research, embeddings or concept/queue edits were performed.

Native run: `run:81ab918bd3e5d5aa8ad4ef4f4a691f32a289c9ad27ffccfeb3deff540dc3e10d`. Independent numerical audit and final delivery receipts are linked from the family llms index.
