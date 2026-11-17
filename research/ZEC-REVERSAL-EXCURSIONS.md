# ZEC reversal follow-through: one-minute observations of ten-minute setups

Version: 1.0.0
Date: 2026-11-15
Status: independently reproduced descriptive calculation on one previously examined day; no prospective probability, execution or profitability qualification.

## What the data says

A reversal during bar 2 after one completed UP candle did not usually remain lower at the tested horizons in this sample. The more favorable historical context followed two completed UP candles, during bar 3. Entry timing changes that comparison substantially.

For the existing banner's at-least-five-minute gate, price was lower ten minutes after detection in **7/17 cases (41.2%) after one UP**, versus **12/20 (60.0%) after two UP**. The average largest intervening fall was **$3.14 (0.326%)** and **$4.70 (0.488%)**, respectively. These favorable excursions can occur even when price subsequently recovers.

The earlier 19/24 next-candle-color fraction answers a different question. It is not the continuation rate after a detected intrabar reversal.

## Frozen definitions

Setup candles are ten minutes. The observed data is one-minute OHLC reconstructed from the accepted Coinbase ZEC-USD receipt-time trade tape. A prior ten-minute candle is UP when its close exceeds its open.

- **One UP / bar 2:** the most recent closed candle is UP and the preceding closed candle is DOWN or flat. The current candle is bar 2 of that setup.
- **Two UP / bar 3:** the last two closed candles are UP/UP. This is a rolling pair and can occur inside a longer UP run. The current candle follows that pair.
- **Primary intrabar trigger:** the first completed one-minute close below the current ten-minute candle's actual open, at elapsed minute 1 through 9. Do not require the developing candle to eventually close DOWN.
- **Current-banner timing sensitivity:** the first eligible below-open close at elapsed minute 5 through 9. An earlier breach can qualify if price is still below the open at minute 5. This is a one-minute proxy for the live banner, which also has its settlement delay and fresh-trade checks.
- **Close confirmation sensitivity:** wait until the current ten-minute candle closes DOWN, then measure only subsequent movement. This includes waiting until the second candle closes after one UP.

The reference price is the trigger minute's close. The measured future window contains only the next 5, 10 or 20 complete one-minute bars. Its low cannot come from the signal minute. Horizons start at the trigger, so they can extend beyond the live banner's current ten-minute target.

**Further fall** is `max(0, reference − lowest subsequent price)` per ZEC, with percentage calculated against that event's reference price. Zero falls remain in the mean. **Lower at horizon** means the final future close is below the reference, with unchanged outcomes retained in the denominator. A temporary lower low and a lower endpoint are different outcomes. The low is visible in hindsight; it is not a known exit price or realized return.

## Predeclared primary, gap-safe: reversal first observed at minute 1–9

| Setup before trigger | Following minutes | N | Mean further fall | Largest further fall | Lower at horizon |
| --- | ---: | ---: | ---: | ---: | ---: |
| One UP → bar 2 | 5 | 30 | $2.82 (0.296%) | $13.70 (1.445%) | 10/30 (33.3%) |
| One UP → bar 2 | 10 | 26 | $2.76 (0.288%) | $9.33 (0.969%) | 9/26 (34.6%) |
| One UP → bar 2 | 20 | 26 | $3.83 (0.398%) | $13.19 (1.333%) | 7/26 (26.9%) |
| Two UP → bar 3 | 5 | 22 | $3.57 (0.369%) | $17.57 (1.789%) | 16/22 (72.7%) |
| Two UP → bar 3 | 10 | 22 | $5.14 (0.532%) | $17.57 (1.789%) | 16/22 (72.7%) |
| Two UP → bar 3 | 20 | 20 | $7.51 (0.776%) | $19.32 (1.995%) | 16/20 (80.0%) |

These are mean maximum favorable excursions, not mean endpoint returns. For the one-UP context, the mean endpoint price change was upward at all three horizons despite those downward excursions. The one-UP five-minute maximum exceeds its ten-minute maximum because the eligible samples differ: N falls from30 to26, excluding three future-gap windows and one capture-end window. The five-minute maximum event is among the later gap exclusions. An individual event's maximum excursion cannot shrink when its valid window grows.

## Gap-safe timing that matches the current ≥5-minute banner gate

| Setup before trigger | Following minutes | N | Mean further fall | Largest further fall | Lower at horizon |
| --- | ---: | ---: | ---: | ---: | ---: |
| One UP → bar 2 | 5 | 17 | $2.12 (0.221%) | $11.28 (1.170%) | 7/17 (41.2%) |
| One UP → bar 2 | 10 | 17 | $3.14 (0.326%) | $12.32 (1.278%) | 7/17 (41.2%) |
| One UP → bar 2 | 20 | 17 | $3.82 (0.395%) | $12.32 (1.278%) | 6/17 (35.3%) |
| Two UP → bar 3 | 5 | 20 | $3.60 (0.374%) | $16.11 (1.662%) | 14/20 (70.0%) |
| Two UP → bar 3 | 10 | 20 | $4.70 (0.488%) | $20.36 (2.100%) | 12/20 (60.0%) |
| Two UP → bar 3 | 20 | 18 | $6.86 (0.709%) | $20.36 (2.100%) | 12/18 (66.7%) |

This table must not be replaced by the more favorable early-trigger primary rates when interpreting the live banner. In particular, the two-UP five-minute endpoint rate is14/20=70.0%, while its ten-minute rate is12/20=60.0%. This selected day does not establish a reliable70% live trading rule.

For reference, the largest gap-safe midpoint-timed fall was **$20.36 per ZEC (2.100%)**, seen within ten minutes and also retained in the twenty-minute window. The setup began2026-11-12T13:00:00Z; the five-minute signal was2026-11-12T13:05:00Z at$969.36 and the subsequent low was$949.00. Price also traded as high as$972.72 in that future window. The earlier minute-one trigger in that same setup used$968.32 and therefore measured$19.32 (1.995%) to the same low over twenty minutes. The reference price and horizon matter. Neither maximum is a future bound. The less strict all-observed sensitivity reaches$24.75 after one UP over twenty minutes; it includes candidate-gap minutes and is not the gap-safe reference.

## Waiting until the current candle has closed DOWN

With close confirmation and a ten-minute subsequent horizon, the one-UP context remained lower in3/11 cases (27.3%); its mean favorable excursion was$4.07 (0.422%), maximum$11.12 (1.126%). The two-UP context remained lower in10/17 (58.8%), with mean$3.43 (0.356%), maximum$6.53 (0.685%). Its mean endpoint decline was negative (−0.051%): a majority of lower endpoints alone did not imply a favorable mean endpoint return.

## Sensitivities, coverage and limits

All72 summary rows retain both signal-close and next-minute-open references, all-observed versus conservative gap-safe data, each trigger timing, and all-events versus time-selected nonoverlapping windows. Nonoverlap selects by signal time before looking at future coverage and reserves the window even when its outcome is later censored. At the ten-minute horizon it leaves the listed primary and midpoint sample counts unchanged. For midpoint two-UP, the next-minute-open endpoint count is13/20 (65.0%), compared with12/20 (60.0%) using signal close; one-UP changes from7/17 to6/17. These are sensitivity results, not another strategy selection.

The capture runs2026-11-12T04:56:27.224912Z through2026-11-13T04:56:27.224912Z. It contains134746 accepted trades and1439 complete one-minute buckets. All1439 have observations;1430 remain after conservative gap screening against26 recorded candidate-gap intervals. Those candidates include receipt silence and trade-ID warnings and are not all proven data loss. Both prior ten-minute bars require all20 constituent minutes; the current prefix must be valid through the trigger. No missing minute is filled. Outcomes with missing/gapped future minutes or capture-end censoring are excluded with separate counts for each horizon. The gap-safe variants yield52 primary events,41 midpoint events and30 close-confirmation events. The269 tagged event records across masks/timings are not269 independent opportunities.

The historical clock is receipt time; the live banner uses exchange-time trade events and public completed candles. One-minute closes approximate intrabar detection and do not reveal the first tick-level crossing. The same day was already examined in prior research, signals can overlap, the sample is small and multiple timings/horizons are shown. No fresh forward test, p-value, calibrated likelihood or fee-adjusted P&L is claimed. Prices and extrema are gross; fees, spread, executable short availability, slippage and an exit policy would require a separate trade simulation. No capture was extended and no trade was placed.

## Banner interpretation

The three-line banner now states the number of confirmed closed UP candles, whether the current candle is bar 2 or bar 3, and whether it is WATCHING, has REVERSAL DETECTED, or lacks live data. A detected reversal after UP/UP keeps the two-UP/bar-3 label. Valid closed-bar context remains visible if a live quote becomes unavailable; unknown older history is labelled confirmed rather than asserting an exact run length. Live detection remains subject to the unchanged ≥5-minute gate, valid true open, freshness, gap and expiry rules. Further decline remains unproven. No symmetric DOWN/DOWN-to-UP alert was added.

## Evidence and reproduction

Canonical Mongo run: `run:125d5e7f32471c641a1400376b8e69c500cece918dee2fab8e639f576909c03c`.
Parent descriptive run: `run:3768d71af70c8382f508829ab67f0f7b91b367174baa7c372c02d432439c1e3c`.
Result archive: `art:b928dd19d998d969230eb66128698eeb4c08b1d2eb891867ff6251b9c31e12bf`, with readable primary rows and a lossless zlib/base64 complete JSON body. Native storage and numerical reproduction do not confer trusted literature or prospective research qualification. No existing concept, queue hold, global score or accepted historical artifact was changed. Discovery inspected complete selected-topic frontier/incomplete pages and all21 prior runs; the unrelated global queue inspection is partial and no queue or concept work was selected.

- Tape SHA256: `21db6ff5a1b6fdd12f887ef506f654ff634af3c355ca898d2f0838de09fd6f4c`.
- WAL SHA256: `eea4a026d1a093a2be996d32c552262358516ca27494f60df3091d54312f3d31`.
- Capture metadata SHA256: `89502534e0f80f17475c3212a98f01ed24a4b4c5ac00c52a5bf488e036325e88`.
- Complete decoded results SHA256: `e3b28398ecfcde1b633f7db241b8ba44812b30173d378965a2ef375fdc6f8f9c`.

The repository projections are `research/zec_reversal_excursions.py`, `research/tests/test_zec_reversal_excursions.py` and `research/zec-reversal-excursions-20261115/results.json`. The CLI accepts `--capture-dir` containing the fixed tape and metadata and `--wal` for the immutable original WAL; it prints JSON, fetches nothing and cannot submit an order. The optional `--packed` output is a lossless transport with a SHA256 binding. Private raw inputs are not redistributed. A separate implementation reproduced all1439 minute candles,269 tagged events and72×2 reference summaries; eleven adversarial timing checks passed.
