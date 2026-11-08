---
id: triangular_arbitrage
name: Triangular Arbitrage
kind: bot
status: implemented
family: arbitrage
summary: Three-leg spot cycle at executable bid/ask. An L1 screening replay over quotes recorded from the live Coinbase ticker stream exists (core/trianglesim.py); the size-aware L2 replay and a measured result do not.
registry_key: null
runner: backtester.botcli
warmup_bars: null
evaluation: null
data_required: [l1-order-book, l2-order-book, cross-pair-quotes, single-venue-simultaneous]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  min_edge_bps: {default: 35.0, type: float, desc: "net edge required after all three legs' fees and spreads"}
  taker_fee_bps: {default: 10.0, type: float, desc: "per-leg taker fee assumption"}
  latency_s: {default: 1.0, type: float, desc: "seconds between detecting a cycle and executing all three legs at the later quotes"}
  notional_usd: {default: 100.0, type: float, desc: "USD per cycle before the displayed-size cap"}
  max_quote_age_s: {default: 5.0, type: float, desc: "a leg quoted longer ago than this is stale and blocks the cycle"}
  cooldown_s: {default: 5.0, type: float, desc: "seconds after an execution before the same triangle may fire again"}
  use_displayed_size: {default: true, type: bool, desc: "cap the cycle at the smallest top-of-book size of its legs"}
presets: {}
---
# Triangular Arbitrage

Design version: 2.1 (2026-11-08).
Delta: 2.0 to 2.1; an L1 screening replay and a live quote recorder now exist, so the
status moves from `spec-only` to `implemented`. Nothing is measured yet.

## What exists now (2026-11-08)

- **Recorder.** `soltui/pricefeed.py` subscribes to the public Coinbase Exchange `ticker`
  channel for every USD market and cross pair among the cached coins and writes one
  bid/ask/size snapshot per second to `<config dir>/prices/YYYY-MM-DD.jsonl.gz`. The
  available crosses on 2026-11-08 were ETH-BTC, SOL-BTC, SOL-ETH, ADA-BTC, ADA-ETH,
  AVAX-BTC, DOGE-BTC, LINK-BTC, LINK-ETH and XLM-BTC, which give ten USD triangles.
- **L1 screening replay.** `core/trianglesim.py` evaluates both directions of every
  triangle at the touch, detects at time *t* and executes all three legs at the first
  snapshot at or after `t + latency_s`, caps size at the displayed top-of-book size, and
  refuses quotes older than `max_quote_age_s`. Run it with
  `python -m backtester.botcli triangle --snapshots <files>` or from the soltui **Bots** tab.
- **Candle proxy.** The Bots tab can also replay one-minute closes with an assumed
  half-spread. It is labelled `candle-proxy` everywhere: closes are not synchronous and
  carry no bid or ask, so its edge is an upper bound on noise.

The replay implements this subset of the fixtures listed below: the 0.99 cycle loses and
the 1.012 illustration matches; synthetic ratios cancel; reciprocal ask and bid differ;
adverse change during the delay erases an edge; stale or missing legs cannot trade; the
displayed size caps the notional. It does **not** walk depth, round quantities, model
sequential legs with acknowledgements, partial fills or unwinds. Its realized edge is
therefore an upper bound on what a real three-order execution would capture, and the
status stays `implemented`, never `measured`, until the size-aware replay below exists.

## Feasibility and current state

**The mechanism works mathematically, and cyclic DEX trades have been observed.
A profitable implementation here remains unproven.** A cycle needs independent
markets whose executable rates briefly disagree enough to pay every cost. It does
not need any coin to rise in USD. Competition, spread, depth and execution delay
can remove the apparent profit before a participant completes the cycle.

This is the existing card for this mechanism, not a new trial in the strategy
count. Version 2.0 designed the backtest; version 2.1 records the L1 screening
replay above. `data_available` stays `false` until the recorder has accumulated
enough quotes for the 60/20/20 split described below. The USD OHLCV cache still
cannot support it. `success_likelihood: very-low`
is a qualitative prior for this project's current data and infrastructure, not a
measured probability or a proof that every venue is unprofitable.

## Equation and the user's example

Define `r_XY` as **units of Y received per unit of X sold**. Do not infer direction
from an ambiguous pair label. With frictionless independent rates:

```text
M_gross = r_AB * r_BC * r_CA
edge_bps = 10000 * (M_gross - 1)
```

If the example means ETH -> ZEC at 1, ZEC -> BTC at 1.1, BTC -> ETH at 0.9:

```text
1 ETH -> 1 ZEC -> 1.1 BTC -> 0.99 ETH
M_gross = 0.99                      loss = 1% before fees
M_reverse_ideal = 1 / 0.99           gain = about 1.0101% before fees
```

The ideal reverse uses reciprocal frictionless rates; actual reverse trades use
the opposite book sides, so that gain is not established by the example. For a
positive forward illustration, replace the last rate by 0.92:

```text
M_gross = 1 * 1.1 * 0.92 = 1.012
M_net = 1.012 * (1 - 0.001)^3 = 1.008967034988
net_edge_bps = 89.67034988
```

That illustration assumes 10 bps on each leg, fees deducted from output, no
additional impact or delay, and enough depth. It is arithmetic, not market data.
Three such fee deductions require a gross multiplier above
`1 / 0.999^3`, about 30.0601 bps above parity, even before execution deterioration.

For a market `BASE/QUOTE` quoted in QUOTE per BASE, use:

```text
sell BASE for QUOTE:    rate = bid
buy BASE using QUOTE:   rate = 1 / ask
M_net = product(rate_i * (1 - fee_i))
```

This product is only the small-size, output-fee screening formula. An executable
size must walk the book, round quantities and account for the actual fee currency.
Do not subtract spread again after already using bid/ask. Do not model a fee-token
payment as free; debit that balance and value its cost in the starting asset.

## Why the current cache cannot answer the question

For simultaneous USD prices `P_A`, `P_B`, `P_C`:

```text
(P_A / P_B) * (P_B / P_C) * (P_C / P_A) = 1
```

Any departure using those same values is numerical error. Mixing timestamps or
venues can create a false deviation. Adding fees to this identity only loses
money. An independently traded cross pair can disagree with the synthetic cross;
that is the input this experiment needs. A valid triangle may include a real
stablecoin market, for example ETH/BTC, BTC/USDT and ETH/USDT. Three non-USD pairs
are not mandatory; three independent tradable edges are.

OHLCV also lacks spread, size, queue/depletion state and event ordering. Smaller
bars do not fix those omissions. `research/ratio_rotation.py` studies relative
asset selection over time; it is a different mechanism and cannot validate this
card. The single-asset bar exposure engine must not simulate three instantaneous
fills from a closing-price signal.

## Backtest design: one-venue CEX event replay

This is the first experiment because it isolates the market-pricing hypothesis
from blockchain execution. Venue and pair availability must be audited before
collection. ETH/ZEC/BTC is a candidate, not a claim that all required markets are
listed for this account or period. If an edge is absent, mark that triangle
unavailable rather than reconstructing it from USD prices or another venue.

### Required local data and manifest

| Input | Required fields and rules |
|---|---|
| Book events | venue, market, exact base/quote asset IDs, exchange timestamp, local receipt timestamp, sequence/update IDs, snapshot/delta type, bids and asks as price/BASE-size levels |
| Market rules | point-in-time listing/delisting and halt status, price tick, quantity step, minimum quantity/notional, order support, balance and fee rounding rules |
| Fees | point-in-time account taker tier per market, fee currency, discounts and eligibility; never use an unattained VIP tier as the baseline |
| Timing | measured feed delay and decision/send/acknowledgment latency distributions; retain calibration provenance and measurement dates |
| Run manifest | source URLs/provider, acquisition date, checksums, coverage/gaps, timestamp units/clock uncertainty, venue, asset IDs, starting inventory, config, seed, code revision and all trials |

Store raw data locally through a separate explicit collector/importer. The replay
must be offline. Record delisted periods and outages as coverage, not silent row
deletion. At least L1 prices **and sizes** permit a capacity screen; sequence-valid
L2 snapshots plus updates are required for the proposed size-aware replay. A fixed
number of levels is not enough if a planned trade reaches beyond recorded depth.
Missing fees, precision rules, clocks or latency calibration block a credible
profit estimate. Assumed latency permits only a labeled sensitivity study.

### Replay and execution state machine

1. Reconstruct each book from its snapshot and ordered deltas. Detect sequence
   gaps, duplicates, corrupt/crossed books and clock problems. Pause eligibility
   until a valid resnapshot; never forward-fill through an outage.
2. At local decision time `t`, form the signal only from events received by `t`.
   Use backward as-of joins with quote-age and inter-market skew caps. Exchange
   timestamps diagnose alignment; future receipt events cannot inform a decision.
3. Enumerate both directions for each eligible triangle. Canonicalize its cyclic
   rotations so one opportunity does not become three independent observations.
   Require funded starting inventory; no leverage or shorting in this experiment.
4. Walk visible depth for the proposed size, apply exact venue rounding and fee
   debits at each leg, and require estimated net return above `min_edge_bps`.
   Starting-asset expected profit must also exceed any fixed execution costs.
5. Schedule leg 1 after the configured decision/send delay. Fill against the
   reconstructed exchange book at order arrival, not the book used for the
   signal. Process equal timestamps by documented sequence/priority; if ordering
   is unknowable, reject the event or take the adverse ordering. Never select
   the first favorable quote *after* arrival as a fill.
6. Use IOC semantics only where the market supports them. Leg 2 waits for the
   acknowledgment and uses the actual net filled output of leg 1; leg 3 does
   the same. Model each send/ack delay, new book state, fee and precision rule.
   Three orders at one CEX are not an atomic transaction.
7. On a partial fill, reject or halt, stop the intended cycle and unwind residual
   assets through available books after the same delays and costs. If an unwind
   cannot fill, carry and report the inventory; never erase the attempt. Mark it
   conservatively at executable liquidation value and report unpriceable balances
   as unresolved, which prevents promotion.
8. Reserve balances and consumed depth. Serialize cycles for the first version.
   A replay cannot repeatedly spend the same capital or count the same stale
   book liquidity as fresh. Reconcile hypothetical consumption against later book
   updates without minting liquidity; document the counterfactual limitation.

The replay cannot prove that historical displayed liquidity would have been
available to our hypothetical orders. A depth haircut and adverse execution cases
must bound this optimism. Observed book depth is an upper bound on capacity.

### Predeclared experiment settings

The frontmatter's `min_edge_bps = 35` means **35 bps remaining after all modeled
costs**, not a 35 bps gross signal with fees still to deduct. Its `taker_fee_bps =
10` is a synthetic-fixture assumption; real evaluation requires the actual fee
schedule. Neither is a tuned or measured optimum.

Before reading holdout outcomes, freeze the venue, triangle universe, starting
asset/quantity, test dates, quote-age/skew caps, depth haircut, latency model,
unwind policy and acceptable drawdown/inventory limit in the manifest. Starting
quantity and freshness caps need feed/market calibration; no universal default
is asserted here. Use training data for feasibility and those calibration choices.

Use chronological 60% development, 20% validation and 20% untouched test periods,
with calendar boundaries saved in the manifest. Purge attempts that cross a split
boundary, and embargo the maximum allowed cycle/unwind horizon. If the feed cannot
support three meaningful periods, report insufficient coverage instead of a
positive result. Fit latency only on prior measurements, never on holdout fills.

On the frozen configuration, report baseline plus these predeclared stresses:
latency 2x and 10x; displayed depth 50%; fees 2x; and the combined 2x-latency,
50%-depth, 2x-fee case. Zero latency is an optimistic diagnostic only. Record every
triangle, size and threshold explored in the trial count, even discarded ones.
Do not promote the best stress outcome as a new selected baseline.

### Outputs and decision gates

Emit a versioned manifest, per-attempt ledger and aggregate report. Each ledger
row binds its signal books, arrival books, times, direction, input amount, fills,
fee debits, residual inventory, unwind result and rejection/failure reason. Show:

- Gross apparent opportunities -> fresh/deep/cost-qualified candidates -> attempted
  cycles -> fully closed cycles -> positive net outcomes. Include the rejected
  and failed attempts and their losses in total economics.
- Net starting-asset gain versus holding the same starting inventory; USD equity
  separately so coin appreciation cannot masquerade as arbitrage profit.
- Total costs, executable capacity, fill/abort/unwind rates, quote ages, cycle
  duration, inventory exposure, drawdown and concentration by day/triangle.
- Returns on total funded capital over elapsed time, not only deployed notional
  or successful cycles. Mark ending dust/residual balances conservatively.
- Uncertainty clustered by day (preserve within-day dependence), including a 95%
  interval for mean daily net gain. Do not treat every quote update as an
  independent trade or annualize a handful of successes into a Sharpe claim.

Move from `spec-only` to `implemented` only when an offline runner and its
correctness fixtures exist. Use `measured` only when real-data results and their
provenance exist, including negative results. A favorable feasibility verdict
additionally requires positive untouched-test net gain after failed attempts,
a lower confidence bound above zero, acceptable predeclared risk limits, and
positive economics under the combined stress. If those fail or data are too thin,
report rejection or inconclusive evidence. Even passing supports a subsequent
forward paper test, not a claim of live capture or authorization to add live
trading to the backtester.

### Required correctness fixtures for a future runner

- The user's 0.99 cycle loses; the 1.012 illustration matches the fee arithmetic.
- Synthetic USD ratios cancel; reciprocal ask and bid differ; a mid-price-only
  apparent edge can vanish at executable prices.
- All fees, third-token debits, quantity rounding, minimums and dust reach P&L.
- Depth exhaustion and adverse price changes during delay erase an apparent edge.
- Leg 2 partial fill and leg 3 rejection produce unwind costs/residual inventory.
- Outages, stale quotes and sequence gaps cannot generate trades or free marks.
- Prefix invariance: changing future events cannot change past signals or fills.
- Restart/replay determinism, finite balances and no reuse of consumed liquidity.

## On-chain extension: separate execution model

Independent pools can create a genuine cycle on one chain. A single atomic
transaction can make all swaps succeed together and enforce a minimum final
balance. That removes partial-leg exposure when correctly implemented. It does
not guarantee inclusion or a profit after fees.

Such a replay needs historical pool state, exact token identities/decimals,
fee and curve rules, concentrated liquidity where applicable, state ordering,
size-dependent impact, transaction limits, and paid costs of failed included
attempts as well as successful ones. Model competition and inclusion using
observations; a reserve-price screen is not a capture estimate. Native ETH, BTC
and ZEC are not automatically three swappable assets on one chain. Wrapped or
bridged versions introduce distinct assets and risks. Cross-chain transfers or
cross-venue inventory strategies require another model and cannot inherit
atomicity from this card.

## Likelihood of success: very-low

Basis: a-priori. No capture test has run here. The data and execution requirements
are missing, and historical CEX evidence gives reason for a conservative prior.
A quote-replay study could revise that assessment; it cannot be inferred from
USD-price ratios or historical DEX revenue.

## Evidence and limitations

Sources checked through Parallel on 2026-11-07; these are historical studies,
not current venue quotes or estimates of this project's expected return.

- Wang et al., *Cyclic Arbitrage in Decentralized Exchanges* (2021/2022): the
  abstract reports 292,606 cyclic trades and over USD 138 million in revenue over
  eleven months on Uniswap V2. This establishes observed activity, not our net
  profitability or transferable present-day capacity.
  https://arxiv.org/abs/2105.02784
- Muck, Schmidl and Wolf, *Wish or reality? On the exploitability of triangular
  arbitrage in cryptocurrency markets* (2025): their BTC/LTC/USD Binance sample
  contains 4,879 possible opportunities; their abstract says transaction costs
  and limited book volume eliminate profitability. That finding is bounded to
  their sample and assumptions, not a theorem about every triangle.
  https://doi.org/10.1016/j.frl.2024.106508
  https://fis.uni-bamberg.de/entities/publication/0c9ed181-871f-4860-bc5f-b882cc81743e
- Fenn et al., *The Mirage of Triangular Arbitrage in the Spot Foreign Exchange
  Market* (2008/2009): executable-price simulations find short, small opportunities
  and a demanding capture-rate requirement. FX is supporting execution evidence,
  not direct evidence about ETH/ZEC/BTC today.
  https://arxiv.org/abs/0812.0913

Recommendation: keep this card as the experiment contract. Audit/obtain independent
book history before implementing its replay. No profitability, pair availability,
current fee tier or latency has been measured here; no equity curve is warranted.
