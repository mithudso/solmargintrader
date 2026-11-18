# TradingView single moving average: research draft

Version: 0.1.0. Delta: record source contract and preliminary evidence. This
is not a qualified rabbithole, registered strategy card, or performance result.

## Identity and signal

The TradingView built-in `STD;MovingAvg%1Cross%1Strategy`, Pine v6 source
version 31.0, is pinned in Mongo as `src:d009b1e195649778`, SHA-256
`3f4d5ec22e85d0fb70797001140574a78b73779c50852545f0b76eee7b2f5e68`.
It compares close to a single SMA of close, with default length 9. Each side
counts consecutive closes strictly beyond the average; an entry is issued
only when its side's counter equals default confirmation 1. Equality resets
both counters. A sequence that touches the average and resumes above it can
therefore issue a new same-side entry intent. The existing `ma_crossover`
strategy instead compares fast and slow averages and is not equivalent.

Official historical source versions 29.0 and 30.0 have identical source bytes
(`22405722377b28e8400ed1c1fdb25dd976aa213b7a9d449af8fbbdd0c19f67d9`).
Replacing only the strategy title with the version 31 title reproduces the
complete pinned version 31 source byte for byte. This comparison does not
identify which version was active on the user's chart.

The existing `research/json/tradingview-card-coverage.json` maps official help
publication 43000599885, MovingAvg Cross, to `ma_crossover` and calls it
`existing`. That mapping does not establish implementation parity: the
referenced code is the two-average 20/50 strategy. The coverage file also maps
the distinct MovingAvg2Line Cross publication to that code. Preserve the
checksum-bound readiness records while reconciling these mismatches through
their owning workflow.

The source submits market `strategy.entry` orders, long `MACrossLE` and short
`MACrossSE`, without specifying quantity. TradingView's strategy documentation
`src:6e1dd8adf7931dc7`, SHA-256
`9367214372491512932d135b9f03bbf123618a981e05598dc955b29c7fc78ecd`,
describes default next-available-tick fills and automatic reversal sizing.
Settings can change execution and costs. The user's settings for this
strategy have not been established; neither default zero fees nor sizing from
another strategy should be substituted as fact.

## Independent empirical context

Hudson and Urquhart (2019), https://link.springer.com/article/10.1007/s10479-019-03357-1 ,
report no out-of-sample predictability for Bitcoin in their selected daily
study, while reporting predictability for other sampled cryptocurrencies.
Their study does not test this ZEC perpetual strategy. Deprez and Frömmel,
https://backoffice.biblio.ugent.be/download/01HY3C3S169G1N6QNYR55NZMFB/01HY60XZGZYHNQ6188MSVJT0SG ,
report risk-adjusted out-of-sample Bitcoin results for portfolios of selected
rules with modeled transaction costs; their long-or-out Bitstamp design is not
the TradingView long/short perpetual. The latter study reports no significant
absolute outperformance and greater sensitivity to unexpected costs at higher
frequencies. These findings cannot establish a return for this strategy, venue,
or period. The papers differ in sample and method.

## Reconciliation proposal

Use a distinct source-specific single-SMA identity and card after independent
contract review. Correct the existing coverage mapping through its owning
helper, with its checksum and version gates. Preserve the generic 20/50
strategy and its historical results. Do not register the draft adapter until
the shared order engine, card defaults, schema, and trace tests agree.

## Backtest contract and outstanding gates

The owner confirmed 10-minute bars and default strategy inputs for
`COINBASE:ZECUSDC.P`. Obtain matched perpetual bars, exact date boundaries,
tester capital, quantity, margin, commissions, slippage, processing settings,
funding and liquidation assumptions before claiming reproduction. The
reported five-month return is a user observation, not independently reproduced.
Preserve all reserved intervals. Separately label any permissible proxy study,
including instrument, data gaps, costs and omissions.

The `research/scripts/tv_single_ma.py` draft emits close-time intents and deliberately
rejects nonfinite close values. It is not registered, and warmup, comparison
precision, missing-data semantics and complete emulator parity need further
verification against TradingView. The shared offline engine omits funding,
spread, margin and liquidation. Do not equate its traces with venue fills.

## Retrospective proxy sensitivity

The shared prior Jupiter ZEC/USD oracle window contains 41,640 contiguous
minutes from 2026-10-10 21:00 UTC through 2026-11-08 19:00 UTC exclusive.
The comparator uses $100,000 initial cash and $1,000 target notional based on
the signal close. The next-open fill notional can differ. A $1,000 unlevered
buy-and-hold position gained $33.31 before costs over the same window. Fresh
ZEC and BTC reservation checks surrounded each simulation. Open positions
are marked at the last close, not forcibly liquidated.

| Bars | Assumed cost per side | P&L | Closed trades | Max drawdown |
| --- | --- | ---: | ---: | ---: |
| 10 minutes | zero | +$570.81 | 731 | 0.208% |
| 10 minutes | 10 bp fee + 1 bp slippage | -$1,038.57 | 731 | 1.177% |
| 15 minutes | zero | +$530.94 | 487 | 0.183% |
| 15 minutes | 10 bp fee + 1 bp slippage | -$541.65 | 487 | 0.721% |

These are in-sample retrospective proxy results, not Coinbase perpetual or
TradingView replication, an out-of-sample evaluation, or live-net results.
Funding, spread beyond the slippage scenario, margin, liquidation, and actual
account settings are unknown. The native result is
`art:023f73b84f69c17606635974140b7cb8003dfcfb36590e0b6ca81017ce3113a5`.

Mongo run `run:2ceb379c607a2a79120f4d92639b671d5a6f9670129529994e098f847a0a7ed0`
remains unqualified. Complete authoritative family reconciliation, independent
negation, countable six-question passes, atomic evidence-bound claims, trusted
gate and publication receipts before any saturation or qualification claim.
