# ZEC/USD five-minute mean-reversion strategy card

| Field | Value |
| --- | --- |
| Card ID | `zec_usd_5m_mean_reversion` |
| Evidence | Exploratory historical holdout |
| Market | Coinbase Exchange native `ZEC-USD` spot |
| Target | Long ZEC or hold USD cash |
| Runner | `python -m research.coin_week`, five-minute baseline row |
| Frozen candidate ID | `697f3b1dd4526147f43ca3d4` |
| Maximum target exposure | 100% of account equity, unlevered |
| Warm-up | 20 completed five-minute bars before the ensemble becomes eligible |

## Rules

Start each signal flat and carry its state between closed bars. Keep the current state until its entry or exit condition is met.

| Member | Enter long | Return to flat |
| --- | --- | --- |
| Wilder RSI, 14 periods | RSI < 30 | RSI > 50 |
| Close z-score, 20 closes | z ≤ −2 | z ≥ 0 |
| Bollinger reversion, 20 closes, 2 standard deviations | Close < lower band | Close > middle band |

The z-score is `(close − SMA20) / sample_std20`. The Bollinger lower band is `SMA20 − 2 × population_std20`. Both rolling windows include the just-closed bar. Wilder RSI starts with the mean of the initial gains and losses, then smooths each with weight `1/14`.

Set the next target to the arithmetic mean of the three binary exposures: `0`, `1/3`, `2/3` or `1` of equity. Rebalance at the next candle open with no strategy deadband, additional confirmation bar, trend/shape filter, or stop-loss. The simulation charges commission plus execution allowance on traded notional, constrains buys to available cash and liquidates any residual exposure at the end of the evaluation slice.

## Frozen configuration

This uses the existing research runner's ensemble format. The candidate is addressable by ID in the study output.

```json
{
  "members": [
    {"strategy": "rsi", "params": {"period": 14, "oversold": 30.0, "exit_level": 50.0}},
    {"strategy": "zscore", "params": {"window": 20, "entry_z": -2.0, "exit_z": 0.0}},
    {"strategy": "bb_reversion", "params": {"window": 20, "num_std": 2.0}}
  ],
  "mode": "mean",
  "persistence": 1,
  "rebalance_threshold": 0.0
}
```

The policy implementation is in [the weekly spot matrix](../scripts/coin_week.py), [the ensemble signal builder](../scripts/zec_granular.py) and [spot accounting](../scripts/zec_ensembles.py). Member rules use [RSI](../../backtester/core/strategies/rsi.py) and [z-score and Bollinger reversion](../../backtester/core/strategies/signals.py).

## Measured result and failure modes

The November 12, 2026 holdout had 104 five-minute bars. The strategy returned **+2.49%** at 10 bps commission plus 2 bps execution allowance per fill, with **1.32% drawdown** and **13 sell events**. The fixed policy returned **+1.56%** at 25 bps commission and **−0.56%** at 60 bps. A sustained decline can leave the strategy exposed while prices keep falling, and frequent partial rebalances consume more of a small rebound when costs rise.

This research card describes a configuration within the existing batch runner. See the [analysis and evidence files](ZEC-5M-MEAN-REVERSION.md) and the [commands for verifying or repeating the study](../../docs/RUNNING-TOOLS.md#inspect-or-repeat-the-zec-study).
