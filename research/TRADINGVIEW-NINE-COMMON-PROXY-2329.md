# Nine TradingView source strategies: common oracle sensitivity

Version: 0.1.0. This is a provisional code and model comparison, not trusted research publication, TradingView parity, a strategy recommendation, or evidence of live profitability.

The shared input is 41,640 previously observed one-minute Jupiter ZEC/USD oracle rows from 2026-10-10 21:00 UTC through 2026-11-08 19:00 UTC, end exclusive. It is not the Coinbase ZEC/USDC perpetual instrument on the owner's chart and is not an independent out-of-sample period. Each entry targets $1,000 notional at signal close, with $100,000 initial cash and a unit multiplier of one. Zero-cost and hypothetical 10-basis-point fee plus one-basis-point slippage per side are sensitivities, not actual venue fee estimates. The model excludes funding, margin, liquidation, contract multipliers, executable spread beyond the hypothetical slippage, and actual 1000x closing latency. Terminal equity marks open positions; it does not force a close. Source-sized cases are separate and must not be presented as equal-notional or automatically assumed feasible.

The table reports marked terminal equity in USD, rounded to cents, for the model's nearest-extreme OHLC path. The pivot row uses the explicit strict tie scenario; its tie behavior remains unverified. Momentum, SAR, Pivot and Channel Breakout use a hypothetical $0.01 tick where applicable. SAR warmup, pivot ties, crossover missing-value behavior, source order size and actual Pine/TradingView fill semantics remain provisional.

| Source strategy | 10m zero cost | 10m hypothetical costs | 15m zero cost | 15m hypothetical costs |
| --- | ---: | ---: | ---: | ---: |
| RS ZigZag, confirmed causal | 99,879.21 | 99,797.85 | 99,953.37 | 99,878.61 |
| Parabolic SAR | 100,384.74 | 99,597.91 | 100,558.55 | 100,040.21 |
| Pivot Reversal, strict ties | 100,855.84 | 100,454.19 | 100,681.26 | 100,409.24 |
| Single moving average, SMA 9 | 100,570.81 | 98,961.43 | 100,530.94 | 99,458.35 |
| Two moving averages, SMA 9/18 | 100,545.33 | 99,978.74 | 100,588.84 | 100,229.07 |
| Momentum | 100,754.22 | 100,046.74 | 100,413.17 | 99,912.46 |
| Price Channel | 100,699.74 | 100,427.88 | 100,713.64 | 100,551.82 |
| Channel Breakout | 100,721.90 | 99,688.52 | 100,524.89 | 99,795.26 |
| Volatility Expansion Close | 100,336.79 | 98,212.47 | 100,356.69 | 99,094.77 |

**Intrabar ordering materially changes outcomes.** At 10 minutes with hypothetical costs, Channel Breakout ends at $99,688.52 with the nearest-extreme path, $99,627.55 with an always-high-first path, and $99,633.81 with an always-low-first path. Volatility Expansion Close ends at $98,212.47, $98,034.78, and $98,195.11 respectively. These are three illustrative fixed paths, not global worst-case bounds. Positive historical cells do not establish a selected live edge.

The RS legacy future-leaking path is a reference only and is excluded from the table and any ranking. Source-default order quantities and equal-notional sensitivities are distinct. The single- and two-average implementations here use the pinned SMA 9 and SMA 9/18 source identities; the existing generic 20/50 persistent-exposure card is not equivalent. Existing source-specific research cards remain unchanged; two provisional source-specific moving-average cards accompany this report.

## Reproduction and evidence

Run `python -m research.tv_nine_common_proxy --source <pinned-oracle-source> --ledger <holdout-ledger> --output <new-private-output>` in an environment with the project dependencies. The loader checks source/page hashes, the exact contiguous window, and protected intervals before and after each simulation. The output is private; do not commit raw source data, private ledger contents, or individual screenshots.

Independent audit receipt SHA-256 `793e4806f036619326d14fba06df8173b7224887360c54c89eab3995748f7ac6` covers 56 numeric replay cases, 55,520 built-in bar/strategy intent comparisons, and 297 causal prefix samples with zero differences under the stated conventions. It does not certify native Pine semantics, market parity, funding or actual execution. The source files and card notes identify unresolved source-specific questions. Mongo source qualification, gates and publication remain separate and incomplete.

Provenance: RS/common engine/SAR/Pivot commits through `1308e7a`; moving-average source tip `b4e415a1118f44363bf7d7d50f51135858b34f8c`; Momentum/Price Channel/Channel Breakout/Volty source tip `4e12206`; source-contract tip `9450cd8`. Raw private result hashes and native artifact IDs are retained in the audit receipt, not represented as trusted publication.
