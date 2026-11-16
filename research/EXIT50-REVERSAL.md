# BTC and ZEC 10-minute exit50 retrospective

This is an exploratory retrospective: the historical period and earlier shape tables were already seen. The splits do not create an independent holdout. The 200 ms observations and 1-minute no-touch envelopes do not prove a continuous keeper path. Current fee configuration is a scenario, not verified historical fees. Entry, network and keeper costs and actual fills are not qualified.

The paper model uses 10 JupUSD collateral, 1000x notional, fee-aware exact integer liquidation and the frontend payout formula. The first target or completed-minute EMA/MACD exit intent latches; close submission waits at least 15 seconds since entry, then the main scenario assumes 10 seconds to close. Liquidation has priority through the simulated close. A filled 50% target means the modeled payout is at least 1.5 times collateral; it is not a real venue fill.

The selector ranks each asset independently by validation modeled trade-fee-only mean ROE, requires at least 30 scored validation entries, and uses count then stable ID for ties. Only target+momentum, 10-second delay, and live-available shape or shape+BOP filters qualify; fallback is explicitly experimental. Final-test outcomes do not select. All returns exclude unverified entry/network/keeper costs.

Selected validation mean modeled ROE: BTC -8.7% over 44 scored entries; ZEC -6.4% over 126. These are relative paper-monitoring hypotheses, not evidence of a profitable or reliable edge. Selection among variants and the reused history limit interpretation.

Frozen family-model SHA-256: `bf7c432c5645a6da4e9e2771e0c455e7c401907aaaa63b5e8447f16e4ebf3d2a`. The independent numerical review covered 48,468 terminal times, 46,101 retained outcomes, 168 variants and 504 summaries, overlap/paired IDs, source bindings and EMA flags. Independent rederivation of training cell counts, shape labels, BTC taker-input transcription and native-pack readback was outside that review. Review receipt SHA-256: `50310f2e0dd6a4d312bd1c63ed7316bfd037093652836c6b8d8b74bc77e0b03c`.

## BTC

Frozen policy: `confirmed_uu/shape/target_momentum/10` (validation-selected). Result artifact: `art:705ae82e36393d95d49b700b634ae83b76a07a7a0efd25a2c7dff3242472f79f`.

| Split and cohort | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train selected | 125 | 118 | 118 | 0 | 76/118 | 53 | 40 | 21 | 4.8% |
| train standalone fixed baseline | 604 | 504 | 504 | 0 | 255/504 | 197 | 100 | 166 | -7.8% |
| train same-entry selected, common proof | n/a | 118 | 118 | 0 | 76/118 | 53 | 40 | 21 | 4.8% |
| train same-entry fixed, common proof | n/a | 118 | 118 | 0 | 76/118 | 55 | 24 | 27 | 4.1% |
| validation selected | 48 | 44 | 44 | 0 | 27/44 | 14 | 12 | 13 | -8.7% |
| validation standalone fixed baseline | 189 | 159 | 159 | 0 | 81/159 | 59 | 30 | 59 | -8.6% |
| validation same-entry selected, common proof | n/a | 44 | 44 | 0 | 27/44 | 14 | 12 | 13 | -8.7% |
| validation same-entry fixed, common proof | n/a | 44 | 44 | 0 | 27/44 | 14 | 7 | 14 | 7.4% |
| test selected | 48 | 46 | 46 | 0 | 28/46 | 21 | 16 | 14 | -7.1% |
| test standalone fixed baseline | 206 | 166 | 166 | 0 | 88/166 | 70 | 35 | 55 | -7.4% |
| test same-entry selected, common proof | n/a | 46 | 46 | 0 | 28/46 | 21 | 16 | 14 | -7.1% |
| test same-entry fixed, common proof | n/a | 46 | 46 | 0 | 28/46 | 22 | 13 | 19 | -3.2% |

Standalone fixed baseline is a separate one-position run, so it can take different entries. Same-entry comparisons retain only IDs with both terminal proofs; their independent counterfactual positions can overlap. Selected overlap skips: 13; baseline skips: 170.

For context, the following fixed ablations use the selected entry family, the 10-second delay and target+momentum. They are not retuned on the final split.

| Test filter | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| none | 206 | 184 | 184 | 0 | 100/184 | 74 | 58 | 42 | -3.1% |
| shape | 48 | 46 | 46 | 0 | 28/46 | 21 | 16 | 14 | -7.1% |
| shape_bop | 17 | 17 | 17 | 0 | 14/17 | 11 | 9 | 4 | 16.3% |
| shape_flow | 12 | 12 | 12 | 0 | 8/12 | 8 | 6 | 2 | 17.3% |

### Exit and close-delay sensitivity

These are fixed predeclared alternatives on the selected family and filter; each is a separate one-position run and can take a different set of entries. The final split is descriptive and never reranks the policy.

| Split, exit, delay seconds | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation fixed 0s | 48 | 48 | 48 | 0 | 30/48 | 16 | 10 | 15 | 8.3% |
| validation fixed 5s | 48 | 42 | 42 | 0 | 26/42 | 13 | 7 | 12 | 12.3% |
| validation fixed 10s | 48 | 42 | 42 | 0 | 26/42 | 13 | 7 | 12 | 12.5% |
| validation second_turn 0s | 48 | 48 | 48 | 0 | 30/48 | 16 | 10 | 15 | 8.3% |
| validation second_turn 5s | 48 | 42 | 42 | 0 | 26/42 | 13 | 7 | 12 | 12.3% |
| validation second_turn 10s | 48 | 42 | 42 | 0 | 26/42 | 13 | 7 | 12 | 12.5% |
| validation target 0s | 48 | 48 | 48 | 0 | 30/48 | 16 | 16 | 14 | -9.3% |
| validation target 5s | 48 | 44 | 44 | 0 | 27/44 | 14 | 11 | 13 | -8.6% |
| validation target 10s | 48 | 44 | 44 | 0 | 27/44 | 14 | 12 | 13 | -7.0% |
| validation target_momentum 0s | 48 | 48 | 48 | 0 | 30/48 | 16 | 16 | 14 | -11.4% |
| validation target_momentum 5s | 48 | 44 | 44 | 0 | 27/44 | 14 | 11 | 13 | -10.6% |
| validation target_momentum 10s | 48 | 44 | 44 | 0 | 27/44 | 14 | 12 | 13 | -8.7% |
| test fixed 0s | 48 | 48 | 48 | 0 | 30/48 | 23 | 13 | 18 | -2.6% |
| test fixed 5s | 48 | 44 | 44 | 0 | 27/44 | 21 | 12 | 18 | -4.2% |
| test fixed 10s | 48 | 44 | 44 | 0 | 27/44 | 21 | 12 | 18 | -3.5% |
| test second_turn 0s | 48 | 48 | 48 | 0 | 30/48 | 23 | 13 | 18 | -2.6% |
| test second_turn 5s | 48 | 44 | 44 | 0 | 27/44 | 21 | 12 | 18 | -4.2% |
| test second_turn 10s | 48 | 44 | 44 | 0 | 27/44 | 21 | 12 | 18 | -3.5% |
| test target 0s | 48 | 48 | 48 | 0 | 30/48 | 23 | 21 | 16 | -10.0% |
| test target 5s | 48 | 46 | 46 | 0 | 28/46 | 22 | 18 | 17 | -10.7% |
| test target 10s | 48 | 46 | 46 | 0 | 28/46 | 22 | 17 | 17 | -8.9% |
| test target_momentum 0s | 48 | 48 | 48 | 0 | 30/48 | 22 | 20 | 13 | -7.4% |
| test target_momentum 5s | 48 | 46 | 46 | 0 | 28/46 | 21 | 17 | 14 | -8.7% |
| test target_momentum 10s | 48 | 46 | 46 | 0 | 28/46 | 21 | 16 | 14 | -7.1% |

The 10-minute down-then-up second-turn baseline is capped at the next 10-minute close; a second completed bar cannot occur within that cap. It is therefore cap-equivalent, not a test of an extended second reversal.

## ZEC

Frozen policy: `near_end/shape_bop/target_momentum/10` (validation-selected). Result artifact: `art:d7d271e436cbfccd11499813d6d85fbef8eecb322e5906fd56cf27374a2383ce`.

| Split and cohort | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train selected | 371 | 371 | 371 | 0 | 205/371 | 204 | 136 | 165 | -6.5% |
| train standalone fixed baseline | 620 | 591 | 591 | 0 | 323/591 | 327 | 133 | 442 | 14.2% |
| train same-entry selected, common proof | n/a | 371 | 371 | 0 | 205/371 | 204 | 136 | 165 | -6.5% |
| train same-entry fixed, common proof | n/a | 371 | 371 | 0 | 205/371 | 204 | 81 | 279 | 3.5% |
| validation selected | 126 | 126 | 126 | 0 | 61/126 | 69 | 48 | 57 | -6.4% |
| validation standalone fixed baseline | 198 | 190 | 190 | 0 | 95/190 | 107 | 33 | 146 | -15.1% |
| validation same-entry selected, common proof | n/a | 126 | 126 | 0 | 61/126 | 69 | 48 | 57 | -6.4% |
| validation same-entry fixed, common proof | n/a | 126 | 126 | 0 | 61/126 | 69 | 19 | 98 | -22.8% |
| test selected | 139 | 139 | 139 | 0 | 75/139 | 72 | 56 | 66 | -9.8% |
| test standalone fixed baseline | 207 | 200 | 200 | 0 | 102/200 | 110 | 35 | 158 | 0.7% |
| test same-entry selected, common proof | n/a | 139 | 139 | 0 | 75/139 | 72 | 56 | 66 | -9.8% |
| test same-entry fixed, common proof | n/a | 139 | 139 | 0 | 75/139 | 73 | 27 | 107 | 7.1% |

Standalone fixed baseline is a separate one-position run, so it can take different entries. Same-entry comparisons retain only IDs with both terminal proofs; their independent counterfactual positions can overlap. Selected overlap skips: 0; baseline skips: 44.

For context, the following fixed ablations use the selected entry family, the 10-second delay and target+momentum. They are not retuned on the final split.

| Test filter | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| none | 207 | 207 | 207 | 0 | 106/207 | 111 | 79 | 95 | -9.1% |
| shape | 188 | 188 | 188 | 0 | 101/188 | 103 | 76 | 84 | -6.2% |
| shape_bop | 139 | 139 | 139 | 0 | 75/139 | 72 | 56 | 66 | -9.8% |

### Exit and close-delay sensitivity

These are fixed predeclared alternatives on the selected family and filter; each is a separate one-position run and can take a different set of entries. The final split is descriptive and never reranks the policy.

| Split, exit, delay seconds | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| validation fixed 0s | 126 | 122 | 122 | 0 | 59/122 | 69 | 21 | 94 | -17.9% |
| validation fixed 5s | 126 | 122 | 122 | 0 | 59/122 | 69 | 19 | 94 | -19.9% |
| validation fixed 10s | 126 | 122 | 122 | 0 | 59/122 | 69 | 19 | 94 | -20.3% |
| validation second_turn 0s | 126 | 122 | 122 | 0 | 59/122 | 69 | 21 | 94 | -17.9% |
| validation second_turn 5s | 126 | 122 | 122 | 0 | 59/122 | 69 | 19 | 94 | -19.9% |
| validation second_turn 10s | 126 | 122 | 122 | 0 | 59/122 | 69 | 19 | 94 | -20.3% |
| validation target 0s | 126 | 126 | 126 | 0 | 61/126 | 69 | 62 | 58 | -16.4% |
| validation target 5s | 126 | 126 | 126 | 0 | 61/126 | 69 | 51 | 58 | -10.2% |
| validation target 10s | 126 | 126 | 126 | 0 | 61/126 | 69 | 48 | 58 | -6.7% |
| validation target_momentum 0s | 126 | 126 | 126 | 0 | 61/126 | 69 | 62 | 57 | -16.0% |
| validation target_momentum 5s | 126 | 126 | 126 | 0 | 61/126 | 69 | 51 | 57 | -9.9% |
| validation target_momentum 10s | 126 | 126 | 126 | 0 | 61/126 | 69 | 48 | 57 | -6.4% |
| test fixed 0s | 139 | 136 | 136 | 0 | 74/136 | 72 | 30 | 104 | 12.2% |
| test fixed 5s | 139 | 136 | 136 | 0 | 74/136 | 72 | 29 | 104 | 10.1% |
| test fixed 10s | 139 | 136 | 136 | 0 | 74/136 | 72 | 27 | 104 | 9.5% |
| test second_turn 0s | 139 | 136 | 136 | 0 | 74/136 | 72 | 30 | 104 | 12.2% |
| test second_turn 5s | 139 | 136 | 136 | 0 | 74/136 | 72 | 29 | 104 | 10.1% |
| test second_turn 10s | 139 | 136 | 136 | 0 | 74/136 | 72 | 27 | 104 | 9.5% |
| test target 0s | 139 | 139 | 139 | 0 | 75/139 | 73 | 68 | 66 | -18.2% |
| test target 5s | 139 | 139 | 139 | 0 | 75/139 | 73 | 51 | 66 | -13.7% |
| test target 10s | 139 | 139 | 139 | 0 | 75/139 | 73 | 56 | 67 | -9.7% |
| test target_momentum 0s | 139 | 139 | 139 | 0 | 75/139 | 72 | 67 | 65 | -18.4% |
| test target_momentum 5s | 139 | 139 | 139 | 0 | 75/139 | 72 | 50 | 65 | -14.0% |
| test target_momentum 10s | 139 | 139 | 139 | 0 | 75/139 | 72 | 56 | 66 | -9.8% |

The 10-minute down-then-up second-turn baseline is capped at the next 10-minute close; a second completed bar cannot occur within that cap. It is therefore cap-equivalent, not a test of an extended second reversal.

## Source and interpretation limits

Shape scores use only completed 5/10/15/20-minute contexts and family-specific training counts. BOP is the trailing three completed 1-minute (close-open)/(high-low) price-only average, with flat bars set to zero; it is not an order count. BTC taker-flow ablation uses retained Binance completed-minute executed quote turnover as a spot proxy, not resting liquidity or Jupiter venue flow. BTC true order-book history was not available for this run.

## Separate ZEC visible-book diagnostic

Result artifact: `art:82ce2836012edc1ffe85ea480584af172349eae54b57cdc7ec03b7087f18322c`. This is one previously seen 24-hour Coinbase capture, not Jupiter house orders or a measure of Jupiter fills. It is not eligible for policy selection. All 55 eligible decisions had qualified visible book data; report the negative/complement subsets and one-position overlap separately.

| Family, 10s target+momentum | Eligible | Attempted | Scored | Unscored | Bar3 down / known | Target touched | Closed at >=50% | Liquidations | Mean modeled fee-only ROE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| confirmed_uu qualified | 26 | 26 | 26 | 0 | 20/26 | 16 | 14 | 10 | 30.8% |
| confirmed_uu negative | 12 | 12 | 12 | 0 | 10/12 | 9 | 8 | 3 | 79.0% |
| confirmed_uu complement | 14 | 14 | 14 | 0 | 10/14 | 7 | 6 | 7 | -10.5% |
| near_end qualified | 29 | 29 | 29 | 0 | 16/29 | 15 | 7 | 14 | -29.0% |
| near_end negative | 18 | 18 | 18 | 0 | 9/18 | 8 | 3 | 10 | -44.7% |
| near_end complement | 11 | 11 | 11 | 0 | 7/11 | 7 | 4 | 4 | -3.4% |

Other exit policies have their own one-position overlap skips; the fixed and cap-equivalent second-turn near-end all/qualified groups each skip three entries, and the complement group skips one. Exact same-entry comparisons must not be confused with separately capacity-constrained groups.

