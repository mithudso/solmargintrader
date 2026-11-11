# Volty: tests that inform a forward decision

Version: 1.0.0. Delta: freeze the inspected chart parameters and measure cost,
execution-delay, candle-path and block uncertainty sensitivities.

The exact inspected chart settings (length5, multiplier1,1minute) fail the new
cost sensitivity test on the previously examined ZEC history. Lower Jupiter
fees do not rescue this replay. The separate prospective paper watcher now has
a concrete hypothesis to test; neither historical results nor a running process
establish a live trading edge.

## Completed diagnostic

The runner fixes the chart parameters before evaluating six scenarios. It never
searches or selects parameters. The input is the checksum-bound129,600minute
Binance ZECUSDT snapshot used in the earlier study. Each account starts flat at
the midpoint, warms stops from preceding bars, and pays its terminal exit.
The evaluated segment contains64,800bars ending2026-11-11 01:26UTC.

| Scenario | Net return | Closed trades |
| --- | ---: | ---: |
| Gross diagnostic: zero fees/slippage/carry | +391.866% | 9,433 |
| GUM fee snapshot3.5bps +2bps slippage/side; synthetic0.1bps/hour carry | −99.985% | 9,433 |
| 10bps slippage/side; synthetic0.2bps/hour carry | approximately−100% | 9,433 |
| High-first candle path, base cost scenario | −99.986% | 9,433 |
| Low-first candle path, base cost scenario | −99.987% | 9,449 |
| One additional bar of signal delay, base cost scenario | −99.999% | 11,980 |

Both stops were touched in128evaluated candles. Their actual order is unknown
from OHLC alone. Passive spot over the same dates returns−38.086% under the
base execution-cost scenario. This compares a synthetic long/short strategy
with a long-only baseline; it is not proof of GUM perpetual execution.

The paired uncertainty check resamples seven-day blocks of daily log-growth
differences using2,000draws and seed20261111. It keeps44complete UTC days and
excludes partial edge days. The base scenario's95%descriptive interval for
mean daily log-growth excess over passive is[−0.212494,−0.152241]. The interval
remains negative for both alternative candle paths, adverse execution and the
extra delay. The gross diagnostic is positive. Resampling assumes approximately
stationary blocks; this short sample and prior strategy selection prevent a
formal significance or future-profit probability claim.

These dates have already been examined. Calling their later half a new untouched
holdout would be false. All figures describe a1xsynthetic reference book using
spot data and declared carry scenarios. No2xliquidation, actual historical GUM
funding, venue basis, market impact, minimum lot or TradingView fill parity is
modeled. The3.5bpsfee comes from the documented2026-11-11venue snapshot, not a
historical fee series. Do not multiply this return by leverage to predict a
leveraged account.

## Next evidence that is more predictive

1. **Frozen prospective paper observation.** Issue and timestamp decisions before
   their eligible bar, retain unchanged parameters and a durable restart cursor,
   report missed intervals, and compare net results with cash and passive. The
   dedicated watcher observes the exact chart setting and the five previously
   frozen study specifications. Its results are modeled Binance reference fills.
2. **Venue-matched execution replay.** Collect timestamped GUM bid/ask depth,
   trades, mark prices and realized funding. Replay actual webhook receipt-to-fill
   latency, rejected/partial fills, lot sizes and fees. Paired TradingView order
   events are needed to establish signal and broker-emulator parity. Existing
   unit fixtures establish handling, not those market observations.
3. **Locked later-time validation.** For any future parameter search, freeze the
   selection objective and test window first. Purge overlapping label/holding
   windows and embargo adjacent training samples where appropriate. Keep every
   trial and adjust for the whole search family. Reusing the same test period
   after tuning invalidates its untouched status.
4. **Stability and downside tests.** Repeat comparisons across independent market
   regimes and venue data, retain unfavorable results, stress outages and costs,
   and simulate margin/liquidation from the actual venue contract. A confidence
   interval or win rate alone cannot justify live sizing.

These tests evaluate evidence quality; they do not add an Oracle timeframe or
prediction veto to the explicitly configured webhook execution path.

## Artifacts and reproduction

Source: `research/volty_predictive_checks.py`. Compact complete result:
`research/results/volty_predictive_20261111.json`. The result binds its source
candle and implementation SHA-256 hashes. It records all six scenarios, exact
costs, full-precision metrics, block settings and limitations. Existing source
mechanics and new diagnostic tests run in the backtester CI job.

Run from the repository root, using a fresh output path:

```sh
/Users/mitch/.venvs/volty-zec-20261110/bin/python -m research.volty_predictive_checks \
  --data /Users/mitch/.local/share/solmargintrader/research/volty-zec-20261110/final/ZEC_1m.csv \
  --expected-sha256 7803d0184c2a4437a89deda2e65869ef7d290576a1324e20bf52b8826ae3cd6f \
  --output /Users/mitch/.local/state/soloracle-tradingview/predictive-20261111/reproduction.json
```

Checks: `python -m unittest research.tests.test_volty_zec
research.tests.test_volty_predictive_checks -q` and
`ruff check research/volty_predictive_checks.py research/tests/test_volty_predictive_checks.py`.
The watcher lifecycle and honest prospective boundaries are documented in
[the service runbook](VOLTY-FORWARD-SERVICE.md).
