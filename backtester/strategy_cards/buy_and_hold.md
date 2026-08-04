---
id: buy_and_hold
name: Buy & Hold
kind: exposure-strategy
status: measured
family: baseline
summary: Fully invested from the first tradeable bar. The null hypothesis every other card must beat.
registry_key: buy_and_hold
runner: backtester.cli
warmup_bars: 0
evaluation: single-split-70-30
data_required: [ohlcv]
data_available: true
params: {}
presets: {}
---
# Buy & Hold

## What it is
Fully invested, always. No signal, no exit.

## What it looks for
Nothing. It exists to be beaten. Any strategy that cannot beat it after costs is a
cost-generating machine wearing a strategy's clothes.

## Equation
```
target_exposure_t = 1.0     for all t
```

## Implementation
`backtester/core/strategies/buy_and_hold.py`.

```python
def on_bar(self, history: BarWindow) -> float:
    return 1.0
```

## Parameters
None. That is the point — there is nothing to overfit, which is exactly why it is
the reference.

## Works when
The asset appreciates over the holding period. Structurally unbeatable on *return*
in a monotonic bull market, though not on drawdown.

## Fails when
Any sustained drawdown, because it has no exit. Measured max drawdown on full-sample
SOL daily: **-96.27%**.

## Backtest notes
This is the harness's known-answer test. With zero costs and `fill_delay=0`, total
return must equal `last_close / first_close - 1` **exactly**, to 12 decimal places.
If that identity ever breaks, the accounting is wrong and no other card in this
directory means anything. `backtester/tests/test_engine.py` asserts it.

## Pairs with
Nothing. It is the baseline. `backtester/cli.py` adds it to every run whether you
ask for it or not, deliberately.

## Measured on SOL
Full-sample daily: **+87.61%**, Sharpe 0.617, max drawdown -96.27%, 1 trade.
Walk-forward: **IS +565.2% (Sharpe 1.030) -> OOS -70.8% (Sharpe -0.651)**.

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

## Caveats and limitations
- A -96% drawdown is survivable on a spreadsheet and not survivable with leverage or
  with money you need.
- "Beat the baseline" is a weak claim when the baseline lost 71% out-of-sample. Losing
  less is not the same as making money.

## How to run
```bash
python3 -m backtester.cli --strategy buy_and_hold --interval 1d
```
