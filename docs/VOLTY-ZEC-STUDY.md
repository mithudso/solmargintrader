# Volty Expan Close: ZEC study

Version: 1.0.0. Delta: source capture, 250 costed configurations and 25 walk-forward folds.

All five first-half winners lost on the held-out second half. Expanding daily walk-forward selection returned +22.69%, while passive ZEC gained +1783.71% across the same overall test dates. These exploratory results establish no tradable edge.

## Full-history leaders

| Interval | Length / multiplier | Full-history net return |
|---|---|---|
| 1m | 10 / 1.25 | -100.000% |
| 5m | 7 / 1.25 | -93.213% |
| 10m | 6 / 1.25 | -81.177% |
| 1h | 6 / 1.25 | -99.986% |
| 1d | 1 / 1.25 | 1203.522% |

These ranks use all history and are descriptive. The daily 1 / 1.25 leader gained +1203.52% in sample; this is not a held-out result. Future-paper specifications freeze these leaders for possible later observation. The walk-forward table below uses past-only selection instead.

## Results

| Interval | Training winner: length / multiplier | Frozen winner OOS | Five-fold walk-forward | Passive OOS |
|---|---|---|---|---|
| 1m | 10 / 1.25 | -99.999% | -99.999% | -38.166% |
| 5m | 7 / 1.25 | -71.917% | -71.997% | -38.191% |
| 10m | 8 / 1.25 | -64.734% | -60.648% | -37.872% |
| 1h | 8 / 1.25 | -99.378% | -99.024% | 1785.373% |
| 1d | 10 / 1.25 | -75.050% | 22.688% | 1783.710% |

Each interval searches lengths 1–10 and multipliers 0.25, 0.5, 0.75, 1 and 1.25. The first 50% selects a fixed winner by net return; the remaining 50% is held out. Separately, five expanding training windows reselect from the same 50 configurations before the next disjoint 10% test window. No test return enters its own selection. Each book starts flat, warms stops from past history, and pays its final exit cost. Fold returns compound. The adaptive procedure is different from one fixed strategy.

Five future-paper specifications are frozen separately using all data available at study time. Their status is `prepared_not_running`. No prospective performance or active paper service is claimed. The existing ensemble forward accounts were preserved.

## Observed history

| Interval | Bars | First UTC bar | Last UTC bar |
|---|---|---|---|
| 1m | 129,600 | 2026-08-13T01:27:00+00:00 | 2026-11-11T01:26:00+00:00 |
| 5m | 25,919 | 2026-08-13T01:30:00+00:00 | 2026-11-11T01:20:00+00:00 |
| 10m | 12,959 | 2026-08-13T01:30:00+00:00 | 2026-11-11T01:10:00+00:00 |
| 1h | 31,859 | 2023-03-24T14:00:00+00:00 | 2026-11-11T00:00:00+00:00 |
| 1d | 1,327 | 2023-03-25T00:00:00+00:00 | 2026-11-10T00:00:00+00:00 |

The input is checksum-bound Binance spot ZEC/USDT from the existing archive. Accounting remains in USDT. Minute data covers the latest 90 cached days. Five- and ten-minute candles require complete UTC-aligned minute buckets. Hourly and daily data use the latest contiguous span; a daily candle requires all 24 hourly observations. Missing bars are never synthesized. Different horizons prevent ranking across intervals.

## Rule and model limits

Stops for bar t+1 use close[t] plus/minus SMA(true range, length)[t] times the multiplier. This is simple averaging, not Wilder ATR. A close creates only next-bar stops. A gap fills at the observed open. If both stops are touched, the assumed path is open-high-low-close when the open is nearer the high, otherwise open-low-high-close. Both replacement stops remain eligible; same-side triggers never pyramid. This independent model has no certified TradingView broker-emulator parity.

New positions use one times current equity and retain fixed units until reversal. Sizing is an explicit study choice, not Pine's default quantity. Fees are 10 bps and adverse slippage is 2 bps per side. Carry is a synthetic 0.1 bps/hour scenario on end-of-bar notional, not observed funding. A close-mark insolvency guard is not a venue liquidation model. Spot candles do not establish an executable short venue. Passive spot pays entry/exit costs without borrow carry.

The fixed daily winner returned -75.05% under the default path and -50.18% under a low-first path. Doubled fees, slippage and carry reduced it to -81.04%. All fixed winners stayed negative under both fixed paths and doubled costs. There is no multiplicity-adjusted significance claim after 250 trials. Historical walk-forward is not prospective forward performance.

## Downloaded sources and supplied dossier

https://www.tradingview.com/support/solutions/43000599890-volty-expan-close-strategy/

https://community.ctrader.com/forum/ctrader-algo/44931/

Raw pages, a recovered Pine-rule excerpt and SHA256 source manifest are at `/Users/mitch/.local/share/solmargintrader/research/volty-zec-20261110/source`.

The owner also supplied `/Users/mitch/.gemini/antigravity-cli/brain/0e524dea-a3e5-4646-a99c-96aeb14eb8b4/volty_expan_close_strategy_dossier.md`. Its Pine example agrees with SMA(TR) and next-bar stop entries. Its separate TradeStation LX/SX exit components are not part of the shown Pine strategy, so this study uses the Pine stop-and-reverse entries. The dossier's literature efficacy and saturation claims were not independently validated or promoted into measured evidence.

## Saved results and reproduction

- `/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_sweep.csv`
- `/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_winners.csv`
- `/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_walk_forward.csv`
- `/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_forward_specs.json`
- `/Users/mitch/dev/solmargintrader/research/results/volty_zec_20261110_manifest.json`

Observed snapshots and the authoritative zero-exit run are at `/Users/mitch/.local/share/solmargintrader/research/volty-zec-20261110/final` and `/Users/mitch/.local/share/solmargintrader/research/volty-zec-20261110/final.log`.

Installed reproduction command; choose a fresh output directory:

```sh
/Users/mitch/.venvs/volty-zec-20261110/bin/python -I -m backtester.voltycli --data-dir /Users/mitch/.local/share/solmargintrader/research/zec-ensembles-20261110/data --output /Users/mitch/.local/share/solmargintrader/research/volty-zec-20261110/reproduction --minute-days 90
```

Focused verification:

```sh
cd /Users/mitch/dev/solmargintrader
INDEX_NO_AUTO=1 /Users/mitch/.venvs/soltui/bin/python -m unittest research.tests.test_volty_zec backtester.tests.test_strategy_cards -q
ruff check backtester/core/volty.py backtester/voltycli.py research/tests/test_volty_zec.py
```

All 49 focused tests passed. The installed full study exited zero and all nine artifact hashes match. Independent installed acceptance from `/tmp` with isolated Python confirmed both module hashes match source, CLI help works, and a no-cost gap replay returns exactly 115/110 − 1. Earlier exploratory attempts are retained locally; one failed only while printing a NumPy boolean as JSON. The final run is authoritative.
