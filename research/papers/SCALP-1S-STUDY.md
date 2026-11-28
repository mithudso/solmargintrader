# One-second bars and the next 30 seconds on Jupiter 1000x

Version: 1.0.0. Data: Jupiter Pyth oracle ticks, 2026-11-16 to 2026-11-17 and 2026-11-27.

On one-second bars of the Jupiter 1000x oracle price, recent direction persists a little: when twelve or more of sixteen trend readings agreed, the next 30 seconds went their way about 53% of the time. Fading an extreme lost. The 1000x payout needs 61% to 84% on moves of that size, so the read-out is a lean and not a rule that pays.

Nothing here was traded. Every figure is a count over recorded prices or the page's own payout arithmetic. The Chrome window built from these results is described in [the 1s scalp window guide](../../docs/JUPITER-1000X-SCALP.md).

## Short answers

| Question | Answer |
|---|---|
| Which 1s readings say anything about the next 30 seconds? | Trend readings, weakly. The best single one is a close beyond the previous 60 seconds' range: right 52.7%, 55.1% and 54.9% of the time on the three slices of the base recording, on about one second in six. |
| Do swing or reversal rules work at this scale? | No. Fading a Z-score beyond 2 was right 46% to 47% of the time. The repository's two-bar reversal rule was right 48.8% on the validation slice. Extremes continued more often than they reversed. |
| What is the most effective combined read-out? | A count of agreeing trend readings. Mixed grids were a coin flip (50.2%); grids with a net 12 or more of 16 one way were right 52.5%, 53.1% and 53.6%. |
| Does the slope ladder add anything? | A little at 5 and 10 seconds, when the slope and its second derivative agree: 52.5% to 53.4% at 5 seconds. From 20 seconds up, and for the 5 minute slope, following it was within a point of a coin flip. |
| How long before a slope reverses? | About as long as its own window: 5.9 s on average for the 5 second slope, 11 s for 10, 21 s for 20, 31 s for 30, 62 s for 60 and 287 s for 5 minutes. That is what a random walk gives. |
| Would following the call have made money at 1000x? | No. One call every 30 seconds lost 5.3% of collateral per trade on the held-out slice, with one trade in five liquidated inside 30 seconds. Strong calls alone averaged +0.7% with a standard error of 3.8, which is not distinguishable from zero. |

## Data

| Recording | Markets | Span | One-second bars per market | Used for |
|---|---|---|---|---|
| Base | BTC, ZEC | 2026-11-16 07:10 to 2026-11-17 16:27 UTC | 119,408 | Choosing readings; all three slices were seen during design |
| Live | SOL, BTC, ETH, ZEC, HYPE | 2026-11-27, 43 minutes | 2,604 | Untouched check: recorded after the design was fixed in code |

Both are ticks of the Jupiter Pyth oracle stream, the price the product opens and closes against. The stream published every 400 to 600 ms. A second with no tick repeats the last price; a silence over three seconds splits the series, and no reading spans the split. The base recording is the local `dual-quotes` capture (36 hourly files, 166 MB, kept outside the repository). The live ticks are in the repository at `research/json/scalp-1s-20261127/ticks-live.jsonl.gz`.

A typical 30 second move was 2.7 basis points for BTC and 6.8 for ZEC in the base recording (median absolute move), and 2.5 for SOL in the live one.

## Method

The target is the sign of the return from a bar's close to the close 30 seconds later. Each reading is computed from bars up to and including that bar, and a test checks that no reading changes when later bars change. A reading votes up when positive and down when negative.

The base recording was split by time: the first 60% to choose parameters, the next 20% to check that a reading's sign held, the last 20% as a held-out slice. Bars whose 30 second outcome crosses a split boundary were dropped. A reading earned a tile when following its sign was right more than half the time on both of the first two slices, with one parameter set per family and at most 90 seconds of warm-up.

**What was seen when.** The tile set was fixed after reading tables that included the held-out 20%. That slice is therefore not a clean test. The live recording is the only sample that played no part in any choice, and it is short.

**Error bars.** Seconds overlap: 30 consecutive bars share most of one outcome. Standard errors below treat every 30 bars as one observation.

## Single readings

Share of seconds on which following the reading's sign was right, on the train and validation slices of the base recording, for the best parameter set in each family. "Kept" means it passed the two-slice rule.

| Family | Best parameter set | Train | Validation | Kept |
|---|---|---|---|---|
| Breakout of the prior range | 60 seconds | 52.7% | 55.1% | Yes |
| Momentum (rate of change) | 1 second | 52.1% | 52.2% | Yes |
| Heikin-Ashi run | | 51.7% | 52.0% | Yes |
| Slope ladder | 5 seconds | 51.5% | 51.5% | Yes |
| ZigZag leg | 1 basis point | 51.4% | 50.5% | Yes |
| Balance of power | 5 seconds | 51.3% | 51.3% | Yes |
| RSI (as trend) | 7 seconds | 51.3% | 50.5% | Yes |
| Efficiency ratio | 60 seconds | 51.1% | 50.6% | Yes |
| EMA cross | 3 / 10 seconds | 51.1% | 50.5% | Yes |
| Range position | 20 seconds | 51.0% | 50.5% | Yes |
| Z-score (as trend) | 20 seconds | 50.9% | 50.3% | Yes |
| Slope change (second derivative) | 10 seconds | 50.9% | 51.3% | Yes |
| Parabolic SAR | | 50.9% | 50.2% | Yes |
| Supertrend | 30 seconds | 50.9% | 50.9% | Yes |
| Regression slope t-statistic | 60 seconds | 50.7% | 50.9% | Yes |
| MACD histogram | 12, 26, 9 seconds | 50.3% | 51.1% | Yes |
| Directional movement | 30 seconds | 50.9% | 49.9% | No |
| Keltner position | 20 seconds | 51.1% | 49.9% | No |
| Two-bar reversal | 10 second bars | 50.4% | 48.8% | No |

The breakout reading is active on about 16% of seconds; the others on nearly all. The grid uses sixteen tiles: 2, 5 and 60 second momentum, 20 and 60 second breakouts, Heikin-Ashi run, balance of power, ZigZag leg, range position, efficiency, slope, RSI, Z-score, MACD histogram, Parabolic SAR and Supertrend. A 3/10 EMA cross passed narrowly and was left out as a near-duplicate of the momentum tiles.

Fading did worse than following. A close more than two standard deviations from its 20 second mean, traded as a reversal, was right 47.2%, 46.9% and 46.3% of the time on the three slices, and 41.0% on the live recording.

## The vote

Net votes out of sixteen. "Strong" is a net 12 or more, "lean" 6 to 11, "mixed" below 6. Each cell is the share of right calls with its standard error, then the share of seconds in that tier.

| Slice | Mixed | Lean | Strong | 60 s breakout alone |
|---|---|---|---|---|
| Train (first 60%) | 50.7% ± 1.5 | 51.1% ± 1.2 | 52.5% ± 1.2, 35% | 52.7% ± 1.8, 16% |
| Validation (next 20%) | 48.6% ± 2.6 | 49.8% ± 2.1 | 53.1% ± 2.2, 35% | 55.1% ± 3.1, 16% |
| Held-out (last 20%) | 50.1% ± 2.6 | 51.6% ± 2.0 | 53.6% ± 2.1, 34% | 54.9% ± 3.1, 16% |
| Base, BTC only | 50.3% ± 1.7 | 51.7% ± 1.3 | 53.9% ± 1.3, 36% | 54.7% ± 1.9, 17% |
| Base, ZEC only | 50.0% ± 1.7 | 50.2% ± 1.3 | 51.7% ± 1.4, 34% | 52.4% ± 2.0, 15% |
| Live, five markets | 48.4% ± 4.9 | 52.3% ± 4.0 | 54.3% ± 4.3, 33% | 57.7% ± 6.0, 16% |
| Live, SOL only | 45.2% ± 10.7 | 50.6% ± 8.8 | 55.6% ± 9.9, 31% | 59.2% ± 14.1, 15% |

The order mixed, lean, strong held on every slice, and the live recording agrees with the base in direction. Its error bars are wide: on their own the live figures do not separate 54% from 50%. The effect was larger for BTC than for ZEC.

The average move in the direction of a strong call was 0.45 to 0.96 basis points on the base slices and 0.24 on the live one. That is a fraction of the typical 30 second move.

## Slope ladder

For each window, the share of seconds on which following the slope's sign was right over the next 30 seconds, then the same when the slope's second derivative agreed with it ("steepening") and when it disagreed ("fading"). Train, validation, held-out.

| Window | Slope | Steepening | Fading |
|---|---|---|---|
| 5 s | 51.5%, 51.5%, 52.1% | 52.5%, 52.7%, 53.4% | 50.5%, 50.5%, 50.8% |
| 10 s | 50.9%, 50.8%, 51.5% | 51.8%, 52.2%, 52.7% | 49.9%, 49.5%, 50.4% |
| 20 s | 50.2%, 50.0%, 50.2% | 50.8%, 50.9%, 51.0% | 49.5%, 49.2%, 49.3% |
| 30 s | 49.8%, 50.0%, 50.3% | 50.0%, 50.5%, 50.6% | 49.7%, 49.4%, 50.0% |
| 60 s | 50.7%, 50.9%, 51.5% | 49.5%, 50.6%, 51.2% | 51.9%, 51.3%, 51.8% |
| 5 min | 49.3%, 49.2%, 51.5% | 50.2%, 49.7%, 51.5% | 48.4%, 48.7%, 51.5% |

A short slope that is still steepening is the useful case. At 60 seconds the pattern flips, by a small margin. The 5 minute slope carried no consistent information about the next 30 seconds.

### Time before a reversal

A run is the time a window's slope keeps one sign. Only runs with both ends inside a continuous stretch are counted. Base recording, both markets together.

| Window | Runs | Average | Median | 90th percentile | Longest |
|---|---|---|---|---|---|
| 5 s | 40,764 | 5.9 s | 4 s | 12 s | 72 s |
| 10 s | 21,541 | 11.1 s | 9 s | 23 s | 100 s |
| 20 s | 11,348 | 21.0 s | 17 s | 42 s | 188 s |
| 30 s | 7,695 | 30.9 s | 25 s | 62 s | 253 s |
| 60 s | 3,846 | 61.7 s | 48 s | 127 s | 446 s |
| 5 min | 802 | 287 s | 239 s | 561 s | 1,616 s |

The average run is about one window long at every scale. Down-runs were a little longer than up-runs (6.8 s against 5.4 s for BTC's 5 second slope, 310 s against 274 s for its 5 minute slope; closer for ZEC). There is no hidden cycle in these figures: a slope fitted over W seconds changes sign about every W seconds on a random walk too. The table is a baseline for reading the live "held" column, not a timer for the next turn.

## What a 30 second call is worth at 1000x

The page's payout is lopsided. Losses are linear in the adverse move. Wins are zero inside the first 0.2 basis points and reduced beyond it, and closing costs 2% of collateral at 1000x. Net result as a share of collateral, from the saved frontend arithmetic:

| Move | In your favour | Against you |
|---|---|---|
| 1 bp | −0.4% | −12% |
| 2 bp | +4.2% | −22% |
| 3 bp | +10.4% | −32% |
| 5 bp | +24.7% | −52% |
| 8 bp | +48.4% | −82% |
| 10 bp | +64.9% | −100% (liquidated at 9.8 bp) |
| 20 bp | +149.9% | −100% |

For equal-sized moves, breaking even needs a hit rate of 84% at 2 basis points, 76% at 3, 68% at 5, 63% at 8 and 61% at 10. A 1 basis point win cannot cover the close fee at any hit rate.

Following the vote, one decision every 30 seconds, filled two seconds later, held 30 seconds, closed two seconds late, liquidated if the observed path touched the boundary:

| Sample | Rule | Trades | Mean result | Winners | Liquidated |
|---|---|---|---|---|---|
| Held-out (BTC, ZEC) | Any call | 1,528 | −5.3% ± 2.1 | 42% | 20% |
| Held-out | Strong calls only | 569 | +0.7% ± 3.8 | 44% | 17% |
| Held-out | Always long | 1,596 | −7.9% ± 2.3 | 39% | 21% |
| Held-out | Always short | 1,596 | −9.5% ± 1.8 | 42% | 22% |
| Live (five markets) | Any call | 400 | −5.6% ± 2.7 | 42% | 8% |
| Live | Strong calls only | 115 | +4.6% ± 6.2 | 51% | 7% |

Strong calls did better than blind entries and their mean is within one standard error of zero on both samples. This is an observed-path simulation on oracle ticks: moves between ticks are unknown, and the two second fill delay is the documentation's figure, not a measurement.

## The 30 second range

The cone on the chart scales the last 30 seconds' 1s volatility by √30. In the first 80% of the base recording, 68% of 30 second moves ended within 1.39 times that figure and 90% within 2.67 times. On the held-out slice those bands held 68.6% and 90.5% of moves. On the live recording they held 62.2% and 83.0%: the range was too narrow that day.

## Limits

- **Two days.** The base recording covers 33 hours of two markets and the live one 43 minutes of five. Persistence at this scale may depend on the session and on how the oracle aggregates venues.
- **The held-out slice was seen.** Only the live recording is untouched, and it cannot confirm a three point edge by itself.
- **Selection.** About twenty families and seventy parameter sets were tried, and a family needed only to beat 50% on two slices to earn a tile. A reading with no information passes that rule about one time in four, and no correction for the number of tries was applied. The base figures, including the ones the window quotes, are therefore optimistic.
- **Oracle prices, not fills.** Opens and closes fill at a later oracle price with no price limit.
- **Overlapping seconds.** Error bars assume one independent observation per 30 seconds, which is approximate.
- **No costs beyond the page formula.** Network fees, rent and the wait for queued profit are left out.
- **One horizon.** Only 30 seconds was studied.

## What would count as evidence

A fixed rule (strong call, or 60 second breakout with the grid agreeing), a fixed hold and exit, and a paper record of at least a few hundred independent calls on live ticks, scored with the payout formula above. The window's session score is a rough guide to that; it counts overlapping seconds.

## Reproduce

```sh
python -m research.scalp_1s_study --base ~/.local/state/oracle-leverage/dual-quotes \
  --live research/json/scalp-1s-20261127/ticks-live.jsonl.gz --out research/json/scalp-1s-20261127 \
  --fixture extension/test/fixtures/1000x-scalp-parity.json --js extension/src/1000x/scalp-model-data.js
python -m unittest research.tests.test_scalp_1s
```

`research/json/scalp-1s-20261127/summary.json` holds every table above and the input hashes; `model.json` holds the constants the extension ships. The feature definitions are in `research/scripts/scalp_1s_features.py` and are ported to `extension/src/1000x/scalp-indicators.js`, with a parity test on recorded bars.
