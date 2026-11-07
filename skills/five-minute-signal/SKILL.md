---
name: five-minute-signal
version: "1.7.0"
updated: "2026-11-07"
description: >-
  Produce and explain an UP / DOWN / FLAT call for the next five-minute bar of a crypto asset
  (SOL by default) from the solmargintrader compound scorecard: every metric scored -1..+1,
  families de-duplicated, regime-weighted, cost/liquidation/shock/news gates, with backtest and
  forward-test evidence beside the call. TRIGGER: "5 minute signal", "next 5m up or down",
  "score the metrics", "compound 5m call", "should I long/short SOL for 5 minutes", "check each
  metric", "forward test the 5m strategies", "backtest the 5m compound". SKIP: placing or
  sizing a real order (no order path; route to the extension and its risk rails), daily/hourly
  strategy research (soltui Strategies/Queue tabs, research/sweep.py), Aero LP (liquidity/).
---

# Five-minute signal

Answers one question: *will the next 5-minute bar close up or down, and is the evidence worth
anything after costs?* The scoring lives in the solmargintrader repo; this skill is the
procedure for running it and reading it honestly. **It never places an order.**

Repo: `/Users/mitch/dev/solmargintrader`. Interpreter with the dependencies:
`/Users/mitch/.venvs/soltui/bin/python`. Full design and measured findings:
`/Users/mitch/dev/solmargintrader/docs/COMPOUND-5M.md`.

## Procedure

1. **Score live.** From the repo root:

   ```bash
   /Users/mitch/.venvs/soltui/bin/python -m soltui.compound signal --asset SOL --json
   ```

   It fetches the last ~600 *closed* 5m candles (public Coinbase; the forming bar is dropped),
   plus Hyperliquid funding/premium/OI/book and RSS headlines only for metrics that need them.
   The saved configuration (switches, weights, parameters) is the one the soltui **Compound 5m**
   tab edits (`~/.config/soltui/compound/config.json`).

2. **Read every metric, not just the call.** For each row in `components`:
   - `status: scored` → `score` in [-1, 1]; `vote` up/down; `effective_weight` = weight × regime
     multiplier.
   - `unavailable` (a live input is missing) or `warming up` → it did not vote. Never treat it
     as 0 or invent a value.
   - `learned_hit`, `learned_calls`, `adaptive_mult`, `p_better_than_coinflip` (adaptive=1, the
     default): the metric's Bayesian record over the last two weeks (`adaptive_window`) and the
     multiplier it earned. A multiplier of 0 means
     it has not beaten a coin flip and did not count, however strong its score.
   - `tuned_params` (tune=1): settings the metric moved to on evidence; say so if present.
   - gates: `pass` or `blocking`. Any blocking gate makes the call FLAT; name it.
   Group the votes by family (trend, oscillator, bands, breakout, flow, positioning,
   lifecycle) and say which families agree. One family with five members is one opinion.

   - `wallet` and `sizing`: labelled `Hyperliquid (live)` when Settings has `hyperliquid_address`
     (free perp margin; spot USDC shown but not counted; open positions listed), else `wallet (live)`
     (SOL/USDC/USDT at the Settings Solana address). Quote the size that risks `risk_pct` to the
     stop: notional, collateral, loss at the stop and the liquidation price. If there is no size,
     give the reason it states (no address, read failed, or an empty account that needs a USDC
     deposit). Mention any open position in the same coin. Never ask for or read a key.

3. **Put the evidence beside the call.**

   ```bash
   /Users/mitch/.venvs/soltui/bin/python -m soltui.compound status --asset SOL   # forward test
   /Users/mitch/.venvs/soltui/bin/python -m soltui.compound results --asset SOL  # latest backtest run
   ```

   Report, for the compound and the strongest voting metrics: out-of-sample hit rate and its z,
   the base-up rate, gross bps per call, and `oracle_net_bps` (what a *perfect* one-bar call
   nets after costs). If there is no backtest row, say "unbacktested" and offer
   `python -m soltui.compound backtest --asset SOL`.

4. **Answer in this shape.**

   ```
   SOL next 5m (from HH:MM UTC): UP | DOWN | FLAT   composite +0.31, coverage 0.95, agreement 0.72
   Regime: range · trend stage: mature · cycle phase: accumulation · round trip 13 bps
   For:     reversion family (rsi +0.75, zscore +0.92, bollinger +1.0), liquidity_sweep +1.0
   Against: trend family (ema_cross -0.76, htf_trend -0.59), breakout (donchian -1.0)
   Gates:   gate_cost BLOCKING (typical move < round trip)   [or: all pass]
   Evidence: compound OOS hit 46% (z -1.1), oracle net -7.5 bps/trade; forward: 12 calls, 58%
   Read:    <one or two sentences: what would have to be true for this call to pay>
   ```

   Always state that a hit rate above 50% is not profit: at 5m the round trip (~13 bps on
   Hyperliquid, ~16 on Jupiter) usually exceeds the average move (6–9 bps on BTC/ETH/SOL), so
   only a call held through several bars can pay.

## Several coins

The compound's coins are BTC, ETH, SOL, XRP, HYPE, DOGE, LINK, NEAR, SUI and AVAX, chosen on
2026-11-07 from a screen of the top 50 (`research/results/top50-screen-2026-11-07.json` in the repo
says why each other coin is out). If asked about a coin outside the ten, say it was screened out and
give the recorded reason before scoring it. The owner trades them on Hyperliquid (all ten have
perps there; Jupiter lists only SOL, ETH and BTC), and the default costs are Hyperliquid's taker fee.

Every coin has its own settings, learned record and ledger: pass `--asset BTC` (etc.) to `signal`,
`status` and `results`, and compare coins with `python3 -m soltui.compound sweep --assets BTC,ETH,SOL`
or the tab's overview. Never quote one coin's evidence for another.

## Things to check that the score cannot

- **Scheduled events** (CPI, FOMC, token unlocks, network upgrades) in the next 30 minutes. If
  one is near and not in the events list, say so and treat the call as FLAT. Add it with
  `compound.save` (`events: [{"ts": <epoch>, "title": "..."}]`).
- **Headlines**: if `gate_news` is off, glance at news before trusting a call; it is a risk
  check, not a predictor. Headline sentiment is not scored (no archive to test it on).
- **Lifecycle**: `trend_stage` exhausted → continuation calls are late; `cycle_phase` tells which
  side the last day favours. A token's own lifecycle (unlocks, listing age) is coin selection
  context, not a 5m input.
- **Liquidation distance** at the leverage the user means: `gate_liquidation` uses the saved
  leverage; recompute if they name another.

## Measured, 2026-11-07 (30 days, five coins, 1,420 configurations)

- No configuration was profitable out-of-sample beyond what luck explains.
- Reversion metrics (RSI, z-score, Bollinger, Stochastic) beat 50% on every coin; trend metrics
  (EMA cross, higher-timeframe trend, ADX, 5m continuation) fell below 50% on nearly every coin.
  Part of the reversion edge is likely Coinbase bid-ask bounce, which neither Jupiter's oracle
  fills nor a Hyperliquid taker order can capture.
- So the catalogue's "favour continuation in trends" is backwards at 5m; say this when a call
  rests on trend votes.
- Trend and stretch metrics are mirror images at 5m (correlation -0.75 to -0.93); `relations`
  in the signal lists any enabled pair that fights or repeats. Say so when a call rests on one
  side of such a pair. Inverting the reliably wrong metrics (`adaptive_flip`, default on) is why a
  trend metric can vote the "wrong" way: its record says it is wrong.
- Adaptive weighting (default on) learns this by itself: on the same data it raised the
  compound's OOS hit rate on four of five coins (DOGE 44% -> 55%), and live it gives weight only
  to the reversion metrics. Returns stayed negative: fees, not direction, are the binding limit.

## Boundaries

- No order path exists in soltui. Real orders go through `extension/` and its risk rails, never
  from this skill.
- Do not tune weights on the same window you then quote as evidence. Quote OOS only.
- Do not quote a forward-test hit rate under ~100 resolved calls as anything but noise.
