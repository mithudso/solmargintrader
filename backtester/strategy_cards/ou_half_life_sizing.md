---
id: ou_half_life_sizing
name: OU Half-Life Reversion (screened and hold-capped)
kind: exposure-strategy
status: measured
family: mean-reversion
summary: Z-score reversion with an Ornstein-Uhlenbeck hold cap and a stationarity screening rule.
registry_key: ou_reversion
runner: backtester.cli
warmup_bars: 251
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
success_likelihood: low
success_basis: measured-oos
params:
  fit_window: {default: 250, type: int, desc: "bars used to fit theta"}
  entry_z: {default: -2.0, type: float, desc: "z-score at or below which to enter"}
  hold_multiple: {default: 2.5, type: float, desc: "exit after this multiple of the half-life"}
  max_half_life_bars: {default: 30, type: int, desc: "above this, refuse to trade the series at all"}
presets: {}
---
# OU Half-Life Reversion (screened and hold-capped)

> **Implemented in this session** from spec-only mechanism #23 of
> `research/STRATEGIES.md`. Its stated gap was "implementable now — needs code, not
> data", so the code was written and it was measured on the same 1,875 daily SOL bars
> and the same 70/30 split as every other measured card.
## What it is
The reversion trade that both `bb_reversion.md` and `zscore.md` are missing: entry on
a stretched z-score, but with **a hold cap and a screening rule** derived from a
fitted Ornstein-Uhlenbeck process.

## Equation
```
dX = theta*(mu - X)dt + sigma*dW          fitted as an AR(1): regress dX on lagged X
half_life = ln(2) / theta

if half_life is infinite or > max_half_life_bars:  take NO position, ever
if z <= entry_z:                                   enter
exit when z >= 0  OR  bars_held > hold_multiple * half_life
```

## Why the two additions matter
- **Screening.** A series with no reversion has an infinite half-life. The rule
  refuses to trade it rather than running a model that does not describe it — and
  `indicators.ou_half_life` returns `inf` for a trending series, which is exactly
  what raw SOL price is over much of this sample.
- **Hold cap.** A reversion trade whose thesis has not played out within a few
  half-lives is no longer the trade that was entered; it is an unbounded bet that the
  mean will return.

## Implementation
`backtester/core/strategies/advanced.py::OuHalfLifeReversion`.

## Measured on SOL

| Leg | Return | Sharpe | Trades |
|---|---|---|---|
| In-sample | +69.0% | 0.781 | — |
| **Out-of-sample** | **-1.5%** | **+0.092** | **6** |

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

**A positive out-of-sample Sharpe (+0.092) and a near-flat return (-1.5%) on 6
trades.** Both halves of that matter. 6 trades is **below the 10-trade evidence
floor**, so this is listed and not ranked — no verdict is available.

What is visible is that the screening rule did its job: it took six positions where
`bb_reversion` took ten and `zscore` took ten, and it ended roughly flat through a
leg that cost buy-and-hold 70.8% and cost `bb_reversion` 4.8%. Refusing to trade is
the behaviour the design intended, and refusing to trade is most of what happened.

Rated low rather than moderate because a mechanism that mostly abstains has not
demonstrated an edge — it has demonstrated a filter. The next real test is using it
as the exit discipline on top of the two existing reversion cards, which is what the
original spec proposed and what remains undone.

## Caveats and limitations
- Theta fitted on a trending series is meaningless. That is the point of the
  screening rule, but it makes `fit_window` load-bearing rather than cosmetic.
- 6 trades. Do not rank this row.
- The z-score window is fixed at `min(fit_window, 20)` rather than exposed, so the
  entry threshold and the fit window are not independently tunable.

## How to run
```bash
python3 -m backtester.cli --strategy ou_reversion --interval 1d
```
