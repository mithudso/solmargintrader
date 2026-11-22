---
id: ichimoku_cloud
name: Ichimoku Cloud
kind: exposure-strategy
status: measured
family: trend
summary: Long while price is above the cloud that was projected onto this bar displacement bars ago.
registry_key: ichimoku
runner: backtester.cli
warmup_bars: 78
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  tenkan: {default: 9, type: int, desc: "conversion-line period"}
  kijun: {default: 26, type: int, desc: "base-line period"}
  senkou_b: {default: 52, type: int, desc: "leading span B period"}
  displacement: {default: 26, type: int, desc: "bars the cloud is projected forward"}
presets:
  short: {tenkan: 9, kijun: 26, senkou_b: 52, displacement: 26}
  medium: {tenkan: 9, kijun: 26, senkou_b: 52, displacement: 26}
  long: {tenkan: 18, kijun: 52, senkou_b: 104, displacement: 52}
---
# Ichimoku Cloud

> **Implemented in this session** from spec-only mechanism #21 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
## What it is
Long while the close is above both leading spans of the cloud overhead.

## Equation
```
Tenkan_t  = (max(H, 9) + min(L, 9)) / 2
Kijun_t   = (max(H, 26) + min(L, 26)) / 2
SenkouA_t = (Tenkan_t + Kijun_t)/2      projected 26 bars FORWARD
SenkouB_t = (max(H,52) + min(L,52))/2   projected 26 bars FORWARD
target_t  = 1 if c_t > max(SenkouA, SenkouB) as projected onto t
```

## The displacement trap, and how this avoids it
The cloud sitting at the current bar was computed **`displacement` bars ago**.
Reading a span computed *at* the current bar as if it were the current cloud reads 26
bars of future data — the classic Ichimoku look-ahead error, and it produces
spectacular backtests.

This implementation slices history to what was visible `displacement` bars back and
compares that cloud against today's close. `test_advanced_strategies.py` asserts the
value used equals the cloud computed from the truncated slice **and** that it differs
from the full-history cloud, so the distinction is verified rather than assumed.

## Implementation
`backtester/core/strategies/advanced.py::IchimokuCloud`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +336.3% | 0.967 | — |
| **Out-of-sample** | **-33.3%** | **-0.531** | **11** |

For reference on the same split: buy-and-hold made **+565.2% (Sharpe 1.030)**
in-sample and **-70.8% (Sharpe -0.651)** out. That row reproduces the figure the
existing cards document exactly, which is how these new numbers are known to be
comparable to them.


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

## Likelihood of success: low

*Basis: measured-oos.*

**The best-behaved loser among the trend mechanisms measured here.** -33.3% and a
-0.531 Sharpe out-of-sample on 11 trades, against buy-and-hold's -70.8%: it halved
the drawdown of simply holding, through a leg where every trend rule lost. The
displaced cloud is a genuinely conservative entry condition, and 11 trades clears
the evidence floor.

It is still a loss, and the mechanism carries six parameters with heavy component
overlap that no experiment here separated. "Lost less than holding" is the honest
ceiling on this claim.

## Caveats and limitations
- Six parameters; attribution between the components is untested.
- Only the price-vs-cloud condition is implemented. The Tenkan/Kijun cross and the
  Chikou confirmation, both part of the full system, are not.

## How to run
```bash
python3 -m backtester.cli --strategy ichimoku --interval 1d
```
