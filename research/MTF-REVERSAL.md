# Multi-timeframe reversal: retrospective paper study

This exploratory study asks whether completed 5, 10, 15 and 20 minute shapes add useful context to an up/up reversal. BTC and ZEC use 41,680 complete one-minute Jupiter Oracle observations each. The model uses only completed bars at the decision boundary. A chronological training split fits the shape cells; validation selects a base interval and threshold; the final split remains an evaluation, not another tuning set. Sparse cells are omitted. The score is a shrinkage-weighted combination of eligible shape cells and the base rate; overlapping timeframes are correlated, so the score is descriptive rather than a calibrated probability.

| Final split | Eligible | Taken | Direction correct | Correct and no adverse 9.8 bps touch |
| --- | ---: | ---: | ---: | ---: |
| BTC selected 10m strategy | 207 | 48 | 30 | 24 |
| BTC always DOWN on the same 48 | 48 | 48 | 30 | 24 |
| BTC always DOWN on all eligible | 207 | 207 | 114 | 101 |
| ZEC selected 5m strategy | 427 | 427 | 202 | 122 |
| ZEC always DOWN on all eligible | 427 | 427 | 202 | 121 |

BTC’s selected strategy chose DOWN on every one of its 48 taken events. Its result is identical to always DOWN on those same events; it filtered coverage to 48 of 207 rather than demonstrating an advantage in direction on that subset. ZEC took all 427 events, with 417 DOWN and 10 UP. Its one additional joint success relative to always DOWN is not evidence of an established profitable edge. Joint success requires both a correct target close and no adverse touch of the 9.8 bps threshold at any point in the available one-minute OHLC path. Touch counts as liquidation in this proxy. The threshold incorporates the study’s fee assumption; actual venue fees, latency, liquidation, keeper fills and execution can differ. Gross underlying moves are not net leveraged P&L.

The separately frozen literal shape-hypothesis diagnostic was correct on 22 of 39 taken BTC cases and 72 of 124 taken ZEC cases. These counts are descriptive; they do not establish that a bowl or cap makes the next move almost certain.

These are retrospective, overlapping observations, with multiple variants considered. They do not support “almost certain” predictions or prospective trading profitability. Small shape cells and correlated inputs widen uncertainty; the model does not establish causal effects. The paper observer uses fresh public Oracle prices, persists a decision before its outcome, and marks a result unscored if a complete 200ms path cannot be proven. It uses a separate ledger from the original frozen Coinbase paper trial. No funded execution is implied.

The independent audit reconstructed 742,128 comparisons and passed 15 targeted causality, boundary, sparse-cell and selection checks. Native draft artifacts and exact SHA-256 bindings are in `research/mtf-reversal-20261116/manifest.json`; draft persistence and this numerical audit are not trusted literature publication or proof of venue fills.
