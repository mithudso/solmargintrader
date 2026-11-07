---
id: fib_retracement
name: Fibonacci Retracement Pullback
kind: exposure-strategy
status: implemented
family: mean-reversion
summary: Buy a pullback into the 0.382-0.786 retracement zone of an up-swing once price turns up; exit on the swing high or a break of the zone.
registry_key: fib_retracement
runner: backtester.cli
warmup_bars: 61
data_required: [ohlcv]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  lookback: {default: 60, type: int, desc: "bars that define the swing high and swing low"}
  entry_ratio: {default: 0.382, type: float, desc: "retracement depth at or below which entry is allowed"}
  invalid_ratio: {default: 0.786, type: float, desc: "retracement depth beyond which the swing is treated as failed"}
presets:
  short: {lookback: 24, entry_ratio: 0.382, invalid_ratio: 0.786}
  medium: {lookback: 60, entry_ratio: 0.382, invalid_ratio: 0.786}
  long: {lookback: 120, entry_ratio: 0.382, invalid_ratio: 0.786}
---
# Fibonacci Retracement Pullback

## What it is
Measure the latest up-swing, then buy a pullback to a conventional retracement level.

## What it looks for
A shallow-to-moderate correction (38.2% to 78.6% of the swing) inside an advance that then resumes.

## Equation
```
swing_high = max(high over lookback);  swing_low = min(low over lookback)
valid      = argmin(low) < argmax(high)           (low came first: an UP swing)
level(r)   = swing_high - (swing_high - swing_low) * r
enter  if valid and level(invalid) <= close <= level(entry) and close > prev_close
exit   if close >= swing_high or close < level(invalid)
```

## Implementation
`backtester/core/strategies/textbook.py::FibRetracement`, over `indicators.fib_level`. Stateful (`_holding`), derived from past bars only.

## Parameters
- **lookback** sets the swing scale.
- **entry_ratio / invalid_ratio** with `0 < entry < invalid < 1`. 0.382 and 0.786 are the conventional levels; 0.5 and 0.618 sit between them, inside the zone.

## Works when
A real trend with orderly pullbacks, where the retracement level coincides with where buyers return.

## Fails when
A trend that is ending. A pullback that reaches 0.618 is indistinguishable in real time from the start of a reversal. The turn-up confirmation trades some entries for fewer falling-knife fills.

## Backtest notes
The swing is recomputed every bar from a rolling window, so the levels move as old extremes age out; a held position can see its own invalidation level shift. No levels are fitted to price: the ratios are fixed constants. Fibonacci levels are a self-fulfilling-prophecy claim, and nothing in the repo tests whether price clusters at them more than at arbitrary ratios; this card does not either.

## Pairs with
A regime filter such as `sma_regime`, to refuse pullback entries in a downtrend.

## Measured on SOL
Smoke run only, not a sweep row: `python3 -m backtester.cli --split 0.7 --interval 1d`, SOL daily 2021-06-17..2026-08-04, default parameters, 8 bps round-trip costs, one 70/30 split. The split is structurally hostile to long-biased rules (see `research/RANKED_LISTS.md`), so read it as one regime transition, not an estimate. The queue (`soltui/bgqueue.py`) will produce the evaluated numbers; this card stays `implemented` until a sweep supplies them.

Full sample: -57.65% (Sharpe -0.261, 26 trades) vs buy-and-hold +87.61%. 70/30 split: IS -44.81% (Sharpe -0.250) -> OOS -23.27% (Sharpe -0.290). It lost money in both windows, so unlike the trend cards its failure is not a regime-split artifact.

## Likelihood of success: very-low

*Basis: base-rate. Retracement levels have no mechanism beyond convention, and the nearest measured mean-reversion cards rated low or very-low.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
python3 -m backtester.cli --strategy fib_retracement --interval 1d --split 0.7
```
