# Auxiliary paired comparison

research output, not investment advice; simulation only

Frozen defaults, historical final 30%; no parameter search or promotion. Grid rails +/-15% first evaluation open, 7 geometric rungs at $100; $10000 capital. Spot fees 6bps, slippage 2bps.

| Mechanism | Dataset | Status | Old/new identical | Original return/P&L | Candidate return/P&L |
| --- | --- | --- | --- | --- | --- |
| ladder_grid | SOL_1d | ran | True | -0.100% | -0.100% |
| dca_bot | SOL_1d | ran | True | -1.784% | -1.784% |
| ladder_grid | BTC_1d | ran | True | -0.249% | -0.249% |
| dca_bot | BTC_1d | ran | True | -1.164% | -1.164% |
| ladder_grid | ETH_1d | ran | True | 1.053% | 1.053% |
| dca_bot | ETH_1d | ran | True | -1.182% | -1.182% |
| ladder_grid | SOL_1h | ran | True | -0.520% | -0.520% |
| dca_bot | SOL_1h | ran | True | -0.893% | -0.893% |
| peer_spread | SOL/BTC_1d | ran | True | 0.000% | 0.000% |
| peer_spread | SOL/ETH_1d | ran | True | 0.000% | 0.000% |
| triangle | 2026-11-08.jsonl.gz | ran | True | $0.093036 | $0.093036 |
| scorecard | SOL_5m_last30d | ran | False | n/a | n/a |

## Directional accuracy

Scorecard common executable next-open-to-close accuracy: 149/318 (46.86%) original, 149/318 (46.86%) candidate. Flat calls abstain; coverage 11.87%; same-active-bar majority baseline 50.00%. Ties count as incorrect in this common diagnostic.

Native forecast reporting uses a different interval boundary and excludes ties. Its old/new percentages change because the label changed from previous-close to executable next-open. That is a measurement correction, not an improved signal. Exact native panels are retained in the JSON.

All 46 scorecard components have coverage records in the JSON. Components requiring absent auxiliary inputs or prospective history are gaps. Gates do not make directional predictions.

Unchanged auxiliary copies should produce parity; this does not establish independent engine agreement.
Auxiliary mechanisms did not receive all 273 DSO passes; no full convergence claim.
Realized-fill win rate is not episode win rate. No suitable directional accuracy for resting-order bots.

Exact configs, inputs, source hashes, errors and indicator accuracy denominators are in auxiliary.json.
