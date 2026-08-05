---
id: obv_trend
name: On-Balance Volume Trend
kind: exposure-strategy
status: measured
family: volume-flow
summary: Long while cumulative signed volume is above its own moving average. Price-blind by construction.
registry_key: obv_trend
runner: backtester.cli
warmup_bars: 22
evaluation: cpcv-8-groups-k2
data_required: [ohlcv, volume]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  ma_window: {default: 20, type: int, desc: "SMA window applied to the OBV series"}
presets:
  short: {ma_window: 24}
  medium: {ma_window: 20}
  long: {ma_window: 60}
---
# On-Balance Volume Trend

## What it is
Long while cumulative signed volume sits above its own moving average.

## What it looks for
Accumulation against distribution — whether volume is arriving on up-bars or down-bars.

## Equation
```
OBV_t    = OBV_{t-1} + sign(c_t - c_{t-1}) * V_t
target_t = 1 if OBV_t > SMA(n) of OBV else 0
```

## Implementation
`backtester/core/strategies/signals.py::ObvTrend`.

## Works when
Volume genuinely leads price. **This signal is price-blind by construction**, which is
exactly what makes it a good *partner*: it sees something no price-based signal can.

## Fails when
Volume data is unreliable or venue-fragmented — a real crypto problem. OBV is also a
running cumulative sum, so it is **path-dependent and level-arbitrary**: only its slope
relative to its own average carries information.

## Backtest notes
Because OBV accumulates from an arbitrary origin, its absolute level is meaningless and
every comparison must be to its own history. **Splitting the series restarts the
accumulation**, so walk-forward legs are not directly comparable on OBV level — a
subtlety worth knowing before interpreting the numbers below.

## Pairs with
Any price-based trend or breakout signal. This is its highest and best use.

## Measured on SOL
Medium: **IS +1,932.1% (Sharpe 1.494) -> OOS -69.2% (Sharpe -1.383)**.
Long: IS +982.7% -> OOS -24.0%, and `any(rsi + obv_trend)` was the **best long-horizon
pair (OOS +0.226)** — though at -8.8% return, which means low well-behaved exposure
rather than profit.

The figures below come from a **single 70/30 walk-forward split**, and
`research/RANKED_LISTS.md` documents why that split is structurally hostile: its
in-sample window ends within one bar of the highest close in the entire series
($261.99 on bar 1311 of 1875). It separated a bull market from a bear leg almost
exactly, so any long-biased rule *had* to look excellent in-sample and terrible
out-of-sample. In-sample rank did not predict out-of-sample rank — the medium-horizon
Spearman correlation was **-0.419**, actively inverted.

Read these numbers as evidence about **one regime transition**, not as a performance
estimate. Across the whole sweep, 45 of 311 rankable configurations (14%) had a
positive out-of-sample Sharpe and 28 (9%) made money. The evidence floor is 10
out-of-sample trades: fewer than that and a row is listed, never ranked.

## Re-evaluated under CPCV — this supersedes the single-split reading above

Combinatorial purged cross-validation (`core/cpcv.py`), 8 groups, k=2, 28 paths, over all 25
registered configurations: `research/results/cpcv_results.csv`. **The single-split section above is
retained for contrast, not as the current estimate** — the split it used lands one bar from the
highest close in the series, and the README's rule is that when CPCV supersedes a card's numbers,
the `evaluation:` field and the numbers change together.

| Horizon (preset) | Median path Sharpe | IQR | Paths positive | Median path return | Trades | Rank |
|---|---|---|---|---|---|---|
| short (`ma_window` 24) | −1.580 | 1.668 | 24% | −18.0% | 852 | 9 of 25 |
| medium (`ma_window` 20) | +0.189 | 1.536 | 67% | −9.8% | 220 | 9 of 25 |
| **long (`ma_window` 60)** | **+0.774** | 1.571 | **81%** | **+44.6%** | 98 | **1 of 25** |

At the long horizon this is **the best single strategy of the 25 measured**, and the direction is
opposite to the single-split row above (which read −24.0%). One of the two is a statement about one
regime transition; the other is a distribution over 28 paths. The CPCV row is the one to believe.

### Parameter perturbation

`research/perturb.py --horizon long --single obv_trend` — ±10% on every parameter, full CPCV re-run:

| Variant | Median Sharpe | Paths positive |
|---|---|---|
| baseline | +0.774 | 81% |
| `ma_window` 60→54 | +0.751 | 86% |
| `ma_window` 60→66 | +0.575 | 76% |

**No sign flips.** Max absolute move 0.199, against the configuration's own path IQR of 1.571 — a
ratio of **0.13, the 4th most stable of the 24 perturbable singles.** It also has only two
perturbable parameters, so there are fewer ways for it to be a fitted artifact. This is the one row
in the study that gets *better* the harder it is looked at.

## Likelihood of success: low

*Basis: measured-oos. There is no 'high' rating in this scheme — across 311 rankable
configurations, 14% had a positive out-of-sample Sharpe and 9% made money.*

**Raised from `very-low` to `low` when CPCV superseded the single split.** `very-low` is defined as
"measured negative out-of-sample, or the mechanism's known failure mode is the dominant feature of
this market". Under the primary method this configuration is measured *positive* at the long
horizon and ranks first of 25, so `very-low` had become a false statement about the evidence.

It stops at `low` — "plausible mechanism, no confirming evidence here" — and not at `moderate`, for
three reasons that the CPCV rank does not answer:

1. **PBO at the daily horizons is 0.700**, above the 0.500 noise line. Ranking first in a set whose
   in-sample rank is anti-informative is not the same as having an edge; the rank itself is the
   suspect quantity.
2. **No cross-asset confirmation.** `hurst_regime_test` and `ou_half_life_sizing` carry
   `cpcv-8-groups-k2-sol-btc-eth`; this card does not. BTC and ETH have already sunk one surviving
   result in this project (`research/results/cpcv_all25_btc_eth_1d.csv`).
3. **The horizons disagree.** +0.774 at long, −1.580 at short on the same mechanism. A real edge
   that reverses sign with the bar size needs an explanation this card does not have.

The single-split reading — IS +1,932.1% to OOS −69.2% — is retained above as the textbook decay row
it is, and as the reason no single split is trusted here again.

## Caveats and limitations
- The best long-horizon pair still lost money. A positive Sharpe on a negative return
  describes a strategy that mostly stayed out of the way.
- The accumulation restart across split boundaries is a genuine measurement artifact
  here, not a hypothetical.

## How to run
```bash
python3 -m backtester.cli --strategy obv_trend --interval 1d
```
