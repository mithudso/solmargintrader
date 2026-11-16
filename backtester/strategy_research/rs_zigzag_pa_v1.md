---
id: rs_zigzag_pa_v1
name: "RS ZigZag PA Strategy V4.1"
kind: exposure-strategy
status: spec-only
family: source-defined
summary: "Legacy harmonic ZigZag strategy with higher-timeframe lookahead; research only."
registry_key: null
runner: null
warmup_bars: null
evaluation: null
data_required: [ohlcv]
data_available: false
success_likelihood: low
success_basis: a-priori
params: {}
presets: {}
---
# RS ZigZag PA Strategy V4.1

Version: 1.0.0. Delta: initial source-bound research card.

This card describes the owner-supplied source and a non-production research
prototype. It is not a registered strategy, TradingView reproduction or
claim that the screenshot's profit is achievable. The supplied source's
SHA-256 is `a708103541426c6746c1cb33b0ad5016094ce29b4342c2f92375bcadbb01e5a9`;
it is private and not included in this repository. The supplied text contains
stray tokens and its identity with the script run in the screenshot is not
established.

## Mechanism and defaults

The legacy source changes directional state when consecutive hourly candles
change up/down direction. It emits a two-hour high or low and keeps the latest
five non-missing pivots. The strategy compares XABCD ratios against harmonic
pattern intervals, and uses Fibonacci levels from the last two pivots for
entry and close conditions. A short or long entry submits a 10,000-unit order
by default; that explicit quantity overrides the tester's default quantity.
The catalog requires an a-priori `low` likelihood field; it is not a measured probability.
The first target defaults to entry ratio 0.236, take-profit ratio 0.618 and
stop ratio -0.236; the second target and optional Heikin Ashi request are off.
The alternate timeframe defaults to 60 minutes. Close conditions examine the
completed chart bar's high/low and call market close; do not assume resting
TP/SL orders or executable fills at those thresholds.

The file has no version directive. TradingView documents that such a file is
Pine v1 and that v1/v2 unoffset higher-timeframe `security` behaves like
`lookahead_on`. If the supplied source executes on 10- or 15-minute charts,
its historical hourly pivots can appear before the hour has finished. The
legacy calculation is a biased diagnostic, not a deployable signal. Two plot
labels are backdated independently of that signal leak. See
`research/RS-ZIGZAG-PA-SOURCE-CONTRACT-2333.md` for source evidence, exact
version/hashes and observed screenshot limits.

## Research implementation and acceptance

`research/rs_zigzag.py` is an offline, unregistered prototype with a legacy
future-revealing path and a one-hour-confirmed path. It requires contiguous
aligned OHLC bars and rejects gaps. Its next-open execution sensitivity is a
simplification with a one-unit contract multiplier: explicit fees, slippage and
optional conservative margin stress are scenarios, not exchange or TradingView parity; funding and spread are absent.
An independent reviewer reproduced its 17 pattern branches and 16 proxy scenarios, but the model has not been compared to TradingView source fills or an exact matching market.

Before evaluating a strategy result, use the same verified market, interval and
window for both paths; preserve reserved holdouts and publish costs, rejected
orders, drawdown, funding and liquidation assumptions. Verify the exact script
and tester settings, source-to-runner signal and order parity, and prefix
invariance. A historical screenshot is an observation, not an independent
real-money result. If matching perpetual history is unavailable, clearly mark
any other dataset as a proxy and do not claim TradingView replication.
