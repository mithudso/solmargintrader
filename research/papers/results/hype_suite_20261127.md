# HYPE: the ZEC analysis suite, repeated

Date: 2026-11-27. Venue: Coinbase Exchange spot, HYPE-USD, with ZEC-USD and BTC-USD as the
same-protocol references. All prices, fees and equity are in USD.

## Answer

- **No HYPE strategy is validated.** Every validation-selected policy in the 294-day run lost
  money on its final test segment at all three cost levels. Several beat buy-and-hold only by
  being partly flat in a falling market (HYPE 1h buy-and-hold -28.0%; the selected policy -10.1%
  at 10 bp).
- **The 31-day suite shows one cost-robust test positive, and it is too short to count.** HYPE
  5m selections were +3.9%, +3.6%, +2.6% and +2.4% at 10, 15, 25 and 60 bp. The 5m series comes
  from a 46-hour 1m segment, so the 5m test covers about 9 hours of bars.
- **One family is positive on test, but it is not a validated policy.** RSI(14h) mean reversion
  (enter below 30, leave above 55) made +16.7% on HYPE 1h test at 10 bp (14 exits), +11.8% at
  25 bp and +0.9% at 60 bp. It was also positive in validation (+11.1%), but it had 8 validation
  exits and the protocol requires 10, so it was ineligible for selection. The same family on ZEC
  1h made +6.7% on test (6 exits; 5 validation exits, also ineligible). Treat it as a hypothesis
  for a pre-registered forward paper test.
- **No tradable short-horizon pattern.** Next-bar sign patterns show statistically detectable
  mean reversion on 5m for ZEC and BTC, but the mean next-bar move is 0.1 to 0.8 bp, far below
  the 10 bp cost floor. HYPE shows no Holm-significant pattern at 5m. A HYPE 1h pattern (after two
  down bars the next bar is up, 53.7%) reaches +7 bp gross but has Holm p = 0.054.
- **No support or resistance edge.** Confirmed swing pivots do not break less often than a
  moving-average touch control, on HYPE, ZEC or BTC. None survives multiple-test correction.

## What was run, mapped to the ZEC suite

| ZEC suite component | HYPE run | Where |
| --- | --- | --- |
| Candle-supported catalogue, 6 filter variants, 1m/5m/10m/1h, 4 fee scenarios, controls, Volty, grid/DCA references, correlations, cycle tests | `research.coin_week --coin HYPE --days 31`, and the same run for ZEC | `research/hype-suite/HYPE-31d/`, `research/hype-suite/ZEC-31d/` |
| Reversal / two-bar / shape studies | Not re-run. Those scripts hard-code ZEC inputs (`--target-day 2026-11-10`, fixed archives). Replaced by the pattern test below | `research/scripts/coin_levels.py` |
| Longer history (ZEC granular and ensemble work used about 180 days of 1m) | `research.coin_history`: Coinbase 5m, 1h and 1d from 2026-02-05, all three coins | `research/hype-suite/history/` |
| Long-history strategy family, patterns, support levels | `research.coin_levels` | `research/hype-suite/levels/coin-levels.json` |

## 31-day suite (same protocol, different reduced windows)

`coin_week` fixes the window at 31 days, and the 1m data have gaps. The "longest contiguous run"
policy therefore selected different segments for each coin:

- HYPE: 2,786 consecutive 1m bars, 2026-11-19 21:20 to 2026-11-21 19:46 (about 46 hours).
- ZEC: 4,193 consecutive 1m bars, 2026-11-23 11:49 to 2026-11-26 09:42 (about 70 hours).

These are not comparable weeks, and neither is a full week. Selected policy, final test, by fee:

| Coin, cadence | 10 bp | 15 bp | 25 bp | 60 bp | Exits at 10 bp |
| --- | ---: | ---: | ---: | ---: | ---: |
| HYPE 1m | +1.48% | +0.57% | -0.12% | -0.34% | 9 |
| HYPE 5m | +3.89% | +3.58% | +2.58% | +2.35% | 3 (40 at 25 bp) |
| HYPE 10m | +0.97% | +0.70% | +0.12% | -2.65% | 14 |
| ZEC 1m | +0.54% | +0.08% | -1.13% | -3.22% | 7 |
| ZEC 5m | -0.06% | -0.43% | -1.16% | -3.15% | 41 |
| ZEC 10m | +0.04% | -0.29% | -0.96% | -3.25% | 27 |

The HYPE 5m line is the only series positive at all four cost levels. Its test has 3 to 40
exits and covers roughly 9 hours, which is too little to distinguish a strategy from noise. The
other HYPE and ZEC lines turn negative at 25 to 60 bp. Source: `research/hype-suite/HYPE-31d/report.md`
and `research/hype-suite/ZEC-31d/report.md`, Frozen validation selections tables.

## Long history: strategies (294 days, longest contiguous run)

Costs: 10, 25 and 60 bp per fill plus the 2 bp execution allowance (the suite's convention). Fills
at the next open. Long-flat only. Thirteen policies per coin and cadence: buy-and-hold, four EMA
crosses, three Donchian breakouts, two RSI mean-reversion settings, one Bollinger reversion, two
momentum rules. Selection: best validation return among policies with at least 10 validation
exits. The test segment is the last 20% of each run and was reported once.

| Coin, cadence | Test window | Selected policy (10 bp) | Val | Test | Buy-and-hold test |
| --- | --- | --- | ---: | ---: | ---: |
| HYPE 1h | 2026-09-29 to 11-26 | momentum 168h | +38.1% | -10.1% | -28.0% |
| HYPE 5m | 2026-07-22 to 08-08 (short) | momentum 168h | -7.6% | -7.0% | -10.8% |
| ZEC 1h | 2026-10-17 to 11-26 | Bollinger 20h | -4.0% | -2.6% | -41.0% |
| ZEC 5m | 2026-10-17 to 11-26 | Donchian 24h | +9.7% | -29.8% | -41.0% |
| BTC 1h | 2026-10-17 to 11-26 | Donchian 24h | -1.6% | -7.2% | -25.8% |
| BTC 5m | 2026-10-17 to 11-26 | EMA 12h/48h | -3.6% | -14.9% | -25.7% |

Every selected policy is negative on test at all three cost levels. For HYPE 1h, momentum 168h is
-10.1% / -14.6% / -24.2% at 10 / 25 / 60 bp.

**The RSI family is the only long-history positive test result.** Full HYPE 1h table, 10 bp
(validation / test), with the same policies at 25 and 60 bp on test:

| Policy | Validation | Test | Test at 25 bp | Test at 60 bp |
| --- | ---: | ---: | ---: | ---: |
| RSI(14h) 30/55 (8 validation exits: ineligible) | +11.1% | **+16.7%** (14 exits) | +11.8% | +0.9% |
| RSI(14h) 25/50 (0 validation exits: ineligible) | 0.0% | +5.3% (7 exits) | +3.1% | -1.8% |
| Momentum 168h (selected) | +38.1% | -10.1% (17 exits) | -14.6% | -24.2% |
| Buy-and-hold | +66.7% | -28.0% | -28.0% | -28.0% |

ZEC 1h: RSI(14h) 25/50 test +6.7% / +4.8% / +0.5% at 10 / 25 / 60 bp, with 5 validation exits
(ineligible). Every other ZEC 1h policy is negative on test. BTC 1h: no policy is positive on test.

The 1h test windows are falling markets for all three coins (buy-and-hold -26% to -41%). Long-flat
mean reversion can outperform in a sell-off that partly reverses. That is one regime-specific
explanation for the RSI result. It has not been separated from luck: 13 policies per coin, no
correction across policies, and 2 to 14 test exits for the RSI rows.

## Long history: patterns (Holm across 24 tests)

Outcome: sign of the next bar after the two previous bars' signs (U = up, D = down).

| Coin, cadence | Pattern | n | P(next down) | Mean next move | Holm p |
| --- | --- | ---: | ---: | ---: | ---: |
| HYPE 1h | DD | 1,600 | 0.463 | +7.0 bp (t 3.2) | 0.054 |
| HYPE 5m | UU | 5,558 | 0.517 | (not significant) | 0.15 |
| ZEC 5m | UU | 13,366 | 0.530 | -0.1 bp | <0.001 |
| ZEC 5m | DU | 14,910 | 0.525 | -0.8 bp | <0.001 |
| ZEC 5m | DD | 14,358 | 0.484 | +0.5 bp | 0.003 |
| BTC 5m | UU | 13,906 | 0.520 | -0.2 bp | <0.001 |
| BTC 5m | DU | 14,908 | 0.515 | -0.1 bp | 0.005 |
| BTC 5m | DD | 14,287 | 0.481 | +0.2 bp | <0.001 |
| BTC 1h | UU | 1,122 | 0.547 | -0.1 bp | 0.028 |

HYPE does not show the momentum pattern in the earlier KuCoin 10-minute note (after UU, the next
10m bar closed down in 35% of cases). On Coinbase 5m it closes down 51.7% after UU, and the
difference is not significant (Holm 0.15). The KuCoin result is a different venue, cadence and
30-day window, and this run does not reproduce it.

Costs decide these patterns. The 5m effects are significant on ZEC and BTC but worth well under
1 bp per bar. The HYPE 1h DD effect is +7 bp gross, below the 10 bp cost floor, and not significant
after correction.

## Long history: support and resistance (1h, 6-bar pivots, 24-bar horizon)

A confirmed swing low (or high) becomes a level. Its first touch within 0.5% after confirmation is
an event. The break is a close more than 1% through the level within 24 bars. The control is the
same touch test on the 24-bar moving average, which has no pivot structure. Events are
non-overlapping.

| Coin, side | Real events | Control events | Break rate, real | Break rate, control | Diff (pp) | p (unadjusted) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| HYPE support | 149 | 175 | 64.4% | 60.6% | +3.9 | 0.48 |
| HYPE resistance | 141 | 184 | 54.6% | 57.6% | -3.0 | 0.59 |
| ZEC support | 95 | 131 | 71.6% | 58.8% | +12.8 | 0.048 |
| ZEC resistance | 97 | 128 | 64.9% | 64.8% | +0.1 | 0.99 |
| BTC support | 121 | 96 | 33.9% | 33.3% | +0.6 | 0.93 |
| BTC resistance | 118 | 103 | 22.0% | 30.1% | -8.1 | 0.17 |

No level improves on the control. The ZEC support result (p 0.048) has the opposite sign from a
support effect: swing lows broke more often. It does not survive correction across the six tests
(Holm p about 0.29).

Descriptive only, as of the 2026-11-26 close of 62.20 (not evidence that these levels hold).
Recent confirmed daily swing lows: 55.74 (2026-11-21), 60.00 (2026-11-14), 72.73 (2026-10-26).
Recent confirmed swing highs: 69.77 (2026-11-23), 96.99 (2026-10-29). The highest close in the
history is 97.23 (2026-09-22). The 2026-02-23 low close is 26.40.

## Market context (descriptive)

- HYPE 1h log-return correlation: 0.58 with BTC, 0.48 with ZEC. HYPE beta to BTC is about 1.1.
  The 31-day same-minute correlation with BTC was 0.71 (`research/hype-suite/HYPE-31d/report.md`).
- Annualised daily realised volatility: HYPE 82%, ZEC 128%, BTC 43%.
- HYPE daily max drawdown: -38.4%, from the 97.23 close on 2026-09-22 to 59.86 on 2026-11-24.
- Fees: Hyperliquid's published base taker fee is 4.5 bp (`research/json/results/hyperliquid-costs-2026-11-07.json`).
  The 10 bp scenario is above that. Coinbase spot fees depend on the account's volume tier and were
  not checked here, so the 25 and 60 bp scenarios matter more for spot.

## Limitations

1. The history is short. Coinbase HYPE-USD begins 2026-02-05, so the long-history runs cover about
   9.7 months and roughly one regime. Hyperliquid's perp history starts with its listing in late 2024
   (`backtester/core/funding.py` records that HYPE funding starts then). Its candle history was not
   checked here, and it would extend the sample several times over if it is available.
2. The 5m tests are shorter than the 1h tests. HYPE 5m uses a 2.5-week test segment (the longest
   run is May 13 to Aug 8), so its 5m policy results are not informative. In the 31-day suite the
   5m test covers about 9 hours. The 1h and 5m longest runs cover different periods, so compare
   across cadences with care.
3. Longest-run selection discards gaps: 125 missing 5m slots on HYPE split the series into 124
   runs. The protocol is kept for comparability with the suite. Gaps are not filled.
4. Selection uses 13 policies per coin and cadence, with no multiple-testing correction across
   policies. The 1h test segments are about 40 to 58 days and contain 2 to 30 exits per policy.
5. The 31-day suite windows differ between coins and are too short for any strategy claim.
6. Support tests use one horizon, one band and one break threshold. Other horizons, volume-profile
   levels and round numbers were not tested.
7. `research/papers/coin-intelligence/hype-hyperliquid.md` is a snapshot from 2026-08-04. Its
   figures are superseded. This data has a higher Coinbase close (97.23 on 2026-09-22) after that
   snapshot date.
8. `backtester/core/universe.py` and `backtester/core/fetch_minutes.py` describe HYPE history as
   roughly six months. Coinbase HYPE 5m and 1h data now cover about 9.7 months. This report does
   not change those files.

## Recommended next step (not run)

Pre-register RSI(14h) mean reversion (enter below 30 or 25, leave above 55 or 50) on HYPE 1h and
ZEC 1h as a forward paper test. Fix the rule, the cost (25 bp), and the sample size before the
first bar. Extend the HYPE history from a second source before any further claim.

## Reproduce

```sh
PY=/Users/mitch/.venvs/solmargin-research/bin/python   # numpy>=2.5.4, pandas>=3.1.0; ruff==0.17.4 for lint
cd /Users/mitch/dev/solmargintrader
PYTHONPATH=. $PY -m research.coin_week --coin HYPE --quote USD --days 31 --end 2026-11-27T00:00:00Z --output research/hype-suite/HYPE-31d --phase all
PYTHONPATH=. $PY -m research.coin_week --coin ZEC  --quote USD --days 31 --end 2026-11-27T00:00:00Z --output research/hype-suite/ZEC-31d --phase all
PYTHONPATH=. $PY -m research.coin_history --coins HYPE ZEC BTC --granularity 300 3600 86400 --start 2026-02-05T00:00:00Z --end 2026-11-27T00:00:00Z --output research/hype-suite/history
PYTHONPATH=. $PY -m research.coin_levels --history research/hype-suite/history --coins HYPE ZEC BTC --output research/hype-suite/levels
PYTHONPATH=. $PY -m unittest research.tests.test_coin_history research.tests.test_coin_levels -v
```

Bound hashes: `research/hype-suite/history/manifest.json` (SHA-256 `ef7efe73960dbfe5…`, the value
`coin-levels.json` records as `history_manifest_sha256`). `research/hype-suite/levels/coin-levels.json`
has SHA-256 `47d71c2d52865e95…`. The analysis is deterministic given that manifest.
