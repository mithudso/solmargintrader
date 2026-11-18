# ZEC and BTC: two-bar reversal conditioned on graph shape

Frozen 5/10/15/20-minute study. Two completed UP bars predict DOWN only under a reversal rule; two DOWN bars predict UP. Shapes use the previous48 completed bars.

The study ends before the existing unsealed BTC holdout. The60/20/20 split is chronological. The last20% was excluded from selection in this run; these histories were used by older studies, so prospective paper testing remains necessary.

## Selected prospective candidates

Selection uses validation Wilson lower bound, then mean gross return, sample count and stable ID. Each asset has64 predeclared candidates. Intervals are descriptive and unadjusted for overlapping events or multiple selection.

| Asset/source | Frozen rule | Validation n/hit | Final test n/hit | Test gross bps | Test net16bps |
|---|---|---:|---:|---:|---:|
| ZEC / Binance spot | 15m:DD:reversal:range → UP | 64 / 64.06% | 73 / 53.42% | -8.26 | -24.26 |
| BTC / Binance spot | 20m:DD:continuation:all → DOWN | 113 / 61.95% | 107 / 48.60% | 2.27 | -13.73 |

## Does a rising graph change the third bar?

Final-split rows below compare third-bar DOWN rates after UU. Sparse cells remain descriptive. Rising shapes are trend_up, bowl and v_rebound; falling shapes are trend_down, cap and inverted_v. Range/compression is a separate group.

| Asset | Minutes | Shape | n | Third bar DOWN |
|---|---:|---|---:|---:|
| ZEC | 5 | all | 412 | 49.5% |
| ZEC | 5 | bowl | 16 | 50.0% |
| ZEC | 5 | cap | 26 | 26.9% |
| ZEC | 5 | compression | 10 | 40.0% |
| ZEC | 5 | inverted_v | 19 | 57.9% |
| ZEC | 5 | range | 245 | 51.8% |
| ZEC | 5 | trend_down | 18 | 33.3% |
| ZEC | 5 | trend_up | 31 | 67.7% |
| ZEC | 5 | v_rebound | 47 | 42.6% |
| ZEC | 10 | all | 210 | 51.4% |
| ZEC | 10 | bowl | 21 | 52.4% |
| ZEC | 10 | cap | 9 | 33.3% |
| ZEC | 10 | compression | 1 | 100.0% |
| ZEC | 10 | inverted_v | 17 | 52.9% |
| ZEC | 10 | range | 120 | 50.8% |
| ZEC | 10 | trend_down | 7 | 42.9% |
| ZEC | 10 | trend_up | 10 | 70.0% |
| ZEC | 10 | v_rebound | 25 | 52.0% |
| ZEC | 15 | all | 139 | 46.8% |
| ZEC | 15 | bowl | 12 | 50.0% |
| ZEC | 15 | cap | 10 | 30.0% |
| ZEC | 15 | compression | 1 | 0.0% |
| ZEC | 15 | inverted_v | 11 | 36.4% |
| ZEC | 15 | range | 74 | 50.0% |
| ZEC | 15 | trend_down | 8 | 62.5% |
| ZEC | 15 | trend_up | 9 | 33.3% |
| ZEC | 15 | v_rebound | 14 | 50.0% |
| ZEC | 20 | all | 106 | 48.1% |
| ZEC | 20 | bowl | 7 | 85.7% |
| ZEC | 20 | cap | 7 | 57.1% |
| ZEC | 20 | compression | 3 | 33.3% |
| ZEC | 20 | inverted_v | 4 | 50.0% |
| ZEC | 20 | range | 63 | 41.3% |
| ZEC | 20 | trend_down | 5 | 80.0% |
| ZEC | 20 | trend_up | 5 | 40.0% |
| ZEC | 20 | v_rebound | 12 | 50.0% |
| BTC | 5 | all | 388 | 54.4% |
| BTC | 5 | bowl | 7 | 57.1% |
| BTC | 5 | cap | 24 | 37.5% |
| BTC | 5 | compression | 14 | 57.1% |
| BTC | 5 | inverted_v | 26 | 76.9% |
| BTC | 5 | range | 224 | 51.3% |
| BTC | 5 | trend_down | 13 | 61.5% |
| BTC | 5 | trend_up | 33 | 63.6% |
| BTC | 5 | v_rebound | 47 | 55.3% |
| BTC | 10 | all | 202 | 54.5% |
| BTC | 10 | bowl | 6 | 33.3% |
| BTC | 10 | cap | 15 | 53.3% |
| BTC | 10 | compression | 7 | 42.9% |
| BTC | 10 | inverted_v | 5 | 40.0% |
| BTC | 10 | range | 125 | 54.4% |
| BTC | 10 | trend_down | 7 | 71.4% |
| BTC | 10 | trend_up | 16 | 68.8% |
| BTC | 10 | v_rebound | 21 | 52.4% |
| BTC | 15 | all | 116 | 56.0% |
| BTC | 15 | bowl | 7 | 28.6% |
| BTC | 15 | cap | 7 | 57.1% |
| BTC | 15 | compression | 2 | 50.0% |
| BTC | 15 | inverted_v | 3 | 66.7% |
| BTC | 15 | range | 71 | 59.2% |
| BTC | 15 | trend_down | 4 | 50.0% |
| BTC | 15 | trend_up | 12 | 41.7% |
| BTC | 15 | v_rebound | 10 | 70.0% |
| BTC | 20 | all | 97 | 52.6% |
| BTC | 20 | bowl | 3 | 66.7% |
| BTC | 20 | cap | 3 | 66.7% |
| BTC | 20 | compression | 6 | 50.0% |
| BTC | 20 | inverted_v | 2 | 50.0% |
| BTC | 20 | range | 63 | 50.8% |
| BTC | 20 | trend_down | 4 | 50.0% |
| BTC | 20 | trend_up | 9 | 55.6% |
| BTC | 20 | v_rebound | 7 | 57.1% |

## Execution and forward-test limits

The16bps roundtrip scenario uses8bps per fill. Report8/16/24bps sensitivities separately. These are spot open-to-close proxies, not observed Jupiter fees/fills, borrow or funding. The10x sensitivity multiplies notional return; it does not simulate liquidation. Minute candles cannot establish executable1000x profitability.

Historical ZEC and BTC are Binance spot USDT candles. The forward worker uses newly observed Coinbase ZEC-USD and BTC-USD prices, records decisions before outcomes, and never sends orders. Venue transfer is unqualified.

No candidate is described as profitable or qualified merely because it is the highest ranked. The full artifact retains every candidate, both UU/DD directions, shape cells, unconditional baselines, gaps and sample counts.
