# Research

- [Papers and strategy research](papers/) holds write-ups, model comparisons and research-only strategy cards.
- [Scripts](scripts/) holds research runners. Existing Python module commands such as `python -m research.coin_week` still resolve from the repository root.
- [JSON evidence](json/) holds configurations, manifests and structured results. The sealed [ETH](json/eth-week-20261117/report.md), [HYPE](json/hype-week-20261127/report.md), [native-pair](json/native-pairs-week-20261117/report.md) and [strategy-comparison](json/strategy_experiment/REPORT.md) bundles keep their reports beside their data.
- [Tabular results](results/) holds CSVs consumed by the research tools and SolTUI.

## One-second bars on Jupiter 1000x

[One-second bars and the next 30 seconds on Jupiter 1000x](papers/SCALP-1S-STUDY.md) scores sixteen trend readings, a slope ladder and its second derivative against the next 30 seconds on recorded Jupiter oracle ticks, and prices a 30 second call with the product's payout formula. `python -m research.scalp_1s_study` writes [the tables](json/scalp-1s-20261127/summary.json), the extension's model constants and its parity fixture. The Chrome window built on it is described in [the 1s scalp window guide](../docs/JUPITER-1000X-SCALP.md).

## HYPE study

The working paper is [What holds up on HYPE? Strategies, patterns and price levels](papers/HYPE-STRATEGIES-PATTERNS-LEVELS.md), published with two figures at https://oraclebot.io/papers/hype-strategies-patterns-levels.pdf . Rebuild its figures with `python -m research.hype_paper_figures` and its PDF with `python -m website.scripts.build_paper research/json/hype-paper-20261127/paper.json`.

The study behind it is [HYPE: strategies, patterns and price levels](papers/HYPE-STUDY.md). It repeats the ZEC candle studies on one week of Binance HYPE/USDT minute bars, runs every registered strategy over two years of daily and 208 days of hourly Hyperliquid candles, and maps swing levels, volume by price and calendar effects. The [weekly report](json/hype-week-20261127/report.md) and the [price-structure report](json/hype-structure-20261127/structure.md) sit beside their data. `python -m research.coin_structure` produces the same structure report for any coin Hyperliquid lists. The [Coinbase HYPE suite](papers/results/hype_suite_20261127.md) is a second run of the same request on Coinbase HYPE-USD; the paper's last section compares the two.

## ZEC GUM 25× five-minute study

Read the [6,048-configuration walk-forward report](papers/results/zec_gum_25x_5m_walk_forward.md) and the [three strategy cards](papers/results/zec_gum_25x_5m_card_1.md). The report links to the other two cards, rankings, frozen selection and complete compressed replay. The [earlier 25×/50× sweep](papers/results/zec_gum_5m_10m_replay.md) covers the 5m and 10m comparison and the decoded archive leaders.

The [matched direction replay](papers/results/zec_gum_25x_5m_directions.md) compares long-only, short-only and two-sided entries on the three frozen profiles. It reproduces the original results for the two-sided accounts.
