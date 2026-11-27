# Research

- [Papers and strategy research](papers/) holds write-ups, model comparisons and research-only strategy cards.
- [Scripts](scripts/) holds research runners. Existing Python module commands such as `python -m research.coin_week` still resolve from the repository root.
- [JSON evidence](json/) holds configurations, manifests and structured results. The sealed [ETH](json/eth-week-20261117/report.md), [HYPE](json/hype-week-20261127/report.md), [native-pair](json/native-pairs-week-20261117/report.md) and [strategy-comparison](json/strategy_experiment/REPORT.md) bundles keep their reports beside their data.
- [Tabular results](results/) holds CSVs consumed by the research tools and SolTUI.

## 1%/day target check

Read [Does any current strategy make 1% a day?](papers/results/target_1pct_day_2026-11-27.md). It replays ZEC Volty(10 × 1.5) 5m, the HYPE RSI dip buyer and buy-and-hold from 1x to 25x with fees, slippage, funding and liquidation over 295 days. Nothing reached the target. Rerun with `python3 -m research.scripts.target_1pct_day`; output lands in [`json/target-1pct-day/`](json/target-1pct-day/report.md).

## HYPE study

Read [HYPE: strategies, patterns and price levels](papers/HYPE-STUDY.md). It repeats the ZEC candle studies on one week of Binance HYPE/USDT minute bars, runs every registered strategy over two years of daily and 208 days of hourly Hyperliquid candles, and maps swing levels, volume by price and calendar effects. The [weekly report](json/hype-week-20261127/report.md) and the [price-structure report](json/hype-structure-20261127/structure.md) sit beside their data. `python -m research.coin_structure` produces the same structure report for any coin Hyperliquid lists. The [Coinbase HYPE suite](papers/results/hype_suite_20261127.md) is a second run of the same request on Coinbase HYPE-USD; the paper's last section compares the two.

## ZEC GUM 25× five-minute study

Read the [6,048-configuration walk-forward report](papers/results/zec_gum_25x_5m_walk_forward.md) and the [three strategy cards](papers/results/zec_gum_25x_5m_card_1.md). The report links to the other two cards, rankings, frozen selection and complete compressed replay. The [earlier 25×/50× sweep](papers/results/zec_gum_5m_10m_replay.md) covers the 5m and 10m comparison and the decoded archive leaders.

The [matched direction replay](papers/results/zec_gum_25x_5m_directions.md) compares long-only, short-only and two-sided entries on the three frozen profiles. It reproduces the original results for the two-sided accounts.
