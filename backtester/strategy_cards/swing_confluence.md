---
id: swing_confluence
name: Swing Trade Breakout with Confluence
kind: exposure-strategy
status: implemented
family: breakout
summary: Enter a breakout above the prior N-bar high when at least two of SMA, MACD, RSI and OBV agree; exit below the prior M-bar low.
registry_key: swing_confluence
runner: backtester.cli
warmup_bars: 50
data_required: [ohlcv, volume]
data_available: true
success_likelihood: very-low
success_basis: base-rate
params:
  breakout: {default: 20, type: int, desc: "bars whose prior high is the resistance level"}
  exit_lookback: {default: 10, type: int, desc: "bars whose prior low is the exit level"}
  ma_window: {default: 50, type: int, desc: "SMA window for the trend confirmation"}
  min_confirms: {default: 2, type: int, desc: "how many of the four confirmations must agree (1 to 4)"}
presets:
  short: {breakout: 12, exit_lookback: 6, ma_window: 24, min_confirms: 2}
  medium: {breakout: 20, exit_lookback: 10, ma_window: 50, min_confirms: 2}
  long: {breakout: 55, exit_lookback: 20, ma_window: 100, min_confirms: 2}
---
# Swing Trade Breakout with Confluence

## What it is
The guides describe swing trading as holding multi-day moves, with a breakout above resistance confirmed by SMA, Fibonacci, volume, MACD or RSI. This is that rule with the confirmations made explicit and countable.

## What it looks for
A breakout that other indicators back, to filter breakouts that fail.

## Equation
```
resistance = max(high over the PRIOR `breakout` bars)       (current bar excluded)
confirms   = [close > SMA(ma_window)] + [MACD hist > 0] + [RSI(14) > 50] + [OBV > mean(OBV, 20)]
enter  if close > resistance and confirms >= min_confirms
exit   if close < min(low over the PRIOR `exit_lookback` bars)
```

## Implementation
`backtester/core/strategies/textbook.py::SwingConfluence`. Fibonacci is not one of the four confirmations: it has its own card (`fib_retracement`) and a retracement level is not a state that confirms a breakout.

## Parameters
- **breakout / exit_lookback** are the Donchian entry and exit windows.
- **min_confirms** from 1 to 4. At 4 it almost never fires; at 1 it is a plain Donchian breakout.

## Works when
Breakouts that follow through, usually in a rising regime where the SMA, MACD and RSI are already positive.

## Fails when
False breakouts in a range, and any move where the confirmations are lagging (all four are derived from the same closes, so they are correlated, not independent evidence).

## Backtest notes
The four confirmations are not independent: SMA, MACD and RSI all read the same close history. `min_confirms` therefore counts agreement among near-duplicates and is a weaker filter than the number suggests. Counting four threshold tests multiplies the free choices (windows, 50 for RSI, 20 for the OBV mean), so the multiple-testing denominator grows with each one.

## Pairs with
A volatility filter (`vol_regime`), which none of the four confirmations measures.

## Measured on SOL
Smoke run only, not a sweep row: `python3 -m backtester.cli --split 0.7 --interval 1d`, SOL daily 2021-06-17..2026-08-04, default parameters, 8 bps round-trip costs, one 70/30 split. The split is structurally hostile to long-biased rules (see `research/RANKED_LISTS.md`), so read it as one regime transition, not an estimate. The queue (`soltui/bgqueue.py`) will produce the evaluated numbers; this card stays `implemented` until a sweep supplies them.

Full sample: +571.09% (Sharpe 0.913, 27 trades) vs buy-and-hold +87.61%. 70/30 split: IS +794.1% (Sharpe 1.238) -> OOS -7.54% (Sharpe 0.019), maxdd -33.77%. The best OOS row of the five new cards but flat, not positive; OOS trade count was not captured in this run, so it may sit under the 10-trade floor.

## Likelihood of success: very-low

*Basis: base-rate. A multi-indicator filter over correlated inputs, in the breakout family, which measured poorly out of sample.*

## Caveats and limitations
- Named by the cited trading guides catalogued in `tradingstrategyresults.json` (repo root, untracked source list). The guides give a verbal rule or a formula, not tested parameters; every default here is a convention, not a finding.
- Rated from the sweep's overall hit rate (14% of 311 rankable configurations had a positive out-of-sample Sharpe), not from this card's own result.

## How to run
```bash
python3 -m backtester.cli --strategy swing_confluence --interval 1d --split 0.7
```
