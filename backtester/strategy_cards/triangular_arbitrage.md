---
id: triangular_arbitrage
name: Triangular Arbitrage
kind: exposure-strategy
status: spec-only
family: arbitrage
summary: Three-leg currency cycle priced off parity. Not backtestable on this project's data, for a structural reason rather than a resolution one.
registry_key: null
runner: null
warmup_bars: null
evaluation: None
data_required: [l1-order-book, l2-order-book, cross-pair-quotes, single-venue-simultaneous]
data_available: false
success_likelihood: very-low
success_basis: a-priori
params:
  min_edge_bps: {default: 35.0, type: float, desc: "net edge required after all three legs' fees and spreads"}
  taker_fee_bps: {default: 10.0, type: float, desc: "per-leg taker fee assumption"}
presets: {}
---
# Triangular Arbitrage

## What it is
Trade a three-leg cycle `A -> B -> C -> A`. If the product of the executable rates
exceeds one after costs, the cycle returns more of asset A than it consumed.

## Equation

Let `r_XY` be units of Y received per unit X. **State the convention or you will
manufacture edges out of nothing** — mixing quote conventions across legs is the most
common implementation bug in this strategy.

No-arbitrage condition:

```
r_AB * r_BC * r_CA = 1
```

Executable form, where `p_i` is the rate actually available (the **ask** when buying the
base, the **bid** when selling it) and `f_i` the per-leg taker fee:

```
M = product over legs of  p_i * (1 - f_i)          profitable iff M > 1
```

Mid-price form — an approximation, and the one that lies:

```
product of r_mid,i  >  1 + sum(s_i / 2) + sum(f_i)      s_i = relative spread on leg i
```

**Spread is not an additive cost, it is which side of the book you take.** The additive
form is a linearisation. A cycle can satisfy the mid-price inequality and fail the
executable one at the same instant, and in the literature it usually does. That gap *is*
the difference between a quoted triangle and an executable one, and it is the whole
subject.

**Sizing the hurdle:** three legs at 10 bps taker is **30 bps of fee before any spread**.
At major-venue half-spreads of 1-2 bps per leg the mid triangle must deviate roughly
33-36 bps to break even. At the lowest fee tiers that hurdle collapses toward 5-10 bps —
so fee tier is not a detail, it is most of the edge, which is precisely why the surviving
participants are the ones with the lowest tier.

On an AMM the rate is a function of size rather than a price, and for constant-product
pools the three-leg cycle composes to a single CPMM-equivalent. Profit is concave in size,
so there is a maximum profitable trade **and**, because on-chain cost is fixed per attempt,
a minimum one. If that fixed cost is large enough the profitable interval is **empty**: the
opportunity is real and unexploitable at any size.

## Why this card is `spec-only` and not "needs finer bars"

The obvious reading is that 1d/1h bars are simply too coarse. True, but not the binding
reason, and the binding reason is more specific:

**BTC, ETH and SOL as held by this project are all quoted against USD, and three
USD-quoted series do not form a triangle.** `USD -> BTC -> USD` is not a cycle. A genuine
triangle needs a **cross pair** — `ETH/BTC`, `SOL/ETH`, `SOL/BTC`. Any "triangle" assembled
from three USD-quoted closes is a **synthetic cross**, and its apparent deviation from
parity is **a data artifact** — non-simultaneous bar closes, different last-trade times,
possibly different venues — not an opportunity.

A backtest built on that would produce a confident and entirely spurious equity curve, and
it would look better the coarser the bars, because the artifact grows with timestamp
misalignment. That is the failure this card exists to prevent someone rediscovering.

Four further reasons any bar-based evaluation fails, in ascending order:

1. **No bid/ask.** A close is a last or mid price, so only the mid-price inequality can be
   computed — the version the literature shows is non-executable. The backtest would be
   testing the known-false condition.
2. **No depth**, so no optimal size, no minimum size, no maximum size. You can answer "did
   a number exceed one" and not "was it worth anything".
3. **No cross-pair simultaneity.** The arb requires three rates to hold at one instant; bar
   closes are independent per-pair aggregates.
4. **Timescale mismatch of orders of magnitude.** Opportunity lifetimes are sub-second. An
   hourly bar averages thousands of appearances and disappearances into one number that
   corresponds to no tradable moment.

## Data that would make it evaluable

- **CEX:** event-resolution L1 (`bid`, `ask`, and both sizes) plus L2 depth of 5-10 levels,
  from **one venue** — a triangle spanning venues is not atomic and is a different, worse
  strategy. Exchange and local receipt timestamps both. The real fee tier. A measured
  latency distribution, not an assumed constant.
- **Solana:** per-slot pool reserve state for every pool in the cycle, including in-range
  liquidity or active bin for concentrated-liquidity venues (headline TVL is close to
  meaningless for execution); priority-fee distribution scoped to the writable accounts the
  transaction touches, not a cluster-wide figure; and landed / dropped / reverted outcomes
  with fees paid, without which the landing probability cannot be estimated.

## Works when
Never, reliably, for a participant without co-location or the lowest fee tier. The
mechanism is sound and the opportunities are real; capturing them is an infrastructure
contest.

## Fails when
Always, in the specific sense that matters: opportunities are numerous, small, short-lived
and shrinking, and the gap between *counted* and *capturable* is the entire finding of
every study below.

## On Solana, atomicity changes the risk rather than removing it
All three legs in **one transaction** either execute or none do, so leg risk and inventory
risk genuinely disappear — and this needs no bundle. (A Jito bundle buys *ordering relative
to other transactions*, not atomicity; conflating the two is the standard error.)

What replaces leg risk:

- **Inclusion risk** — a dropped transaction never lands and costs nothing.
- **Revert cost** — a landed-but-failed transaction pays the full fee, and at scale this
  dominates.
- **Auction competition** — the priority fee is a product of price and requested compute
  units, ranked per-CU, so over-requesting costs money and priority simultaneously.
- **Size ceiling** — 1,232 bytes and 1.4M CU per transaction. A three-hop split route may
  simply not serialise; treat "the optimal route does not fit" as an expected case.
- **Sandwich exposure is *lower* than for an ordinary swap**, for a precise reason: an arb
  transaction that reverts unless profitable sets no slippage tolerance to squeeze. The
  adversarial exposure is being outraced, not being sandwiched.

## Evidence

| Finding | Source | Date |
|---|---|---|
| 292,606 cyclic arbitrages on Uniswap V2 over 11 months, >$138M revenue; most profitable *unexploited* opportunity persistently >1 ETH | Wang, Chen, Wu, Zhou, Deng & Wattenhofer, *Cyclic Arbitrage in Decentralized Exchanges*, arXiv:2105.02784 / WWW '22 | 2021-22 |
| **4,879 triangular opportunities found on Binance (BTC/LTC/USD) and transaction costs plus limited order-book volume eliminate their profitability.** Concludes opportunity count is not a reliable indicator of inefficiency | Muck, Schmidl & Wolf, *Wish or reality? On the exploitability of triangular arbitrage in cryptocurrency markets*, Finance Research Letters 73 | 2025 |
| FX triangular opportunities exist with short durations and a declining trend; a trader "would need to beat other market participants to an unfeasibly large proportion of arbitrage prices to profit" | Fenn, Howison, McDonald, Williams & Johnson, *The Mirage of Triangular Arbitrage in the Spot Foreign Exchange Market*, IJTAF 12(8) / arXiv:0812.0913 | 2008-09 |

Two independent literatures — FX in 2009, crypto CEX in 2025 — reached the same conclusion
by the same route. The one setting where measured revenue is large and real is on-chain,
and that is also the one requiring atomic execution and searcher infrastructure.

Commonly cited 2026 Solana aggregates (arbitrage as a share of DEX volume, searcher profit
totals, tip-as-share-of-profit) come from vendor and infrastructure blogs, are
single-sourced and commercially interested, and are **deliberately not quoted here**.

## Likelihood of success: very-low

*Basis: a-priori. `spec-only` cards cannot cite `measured-oos`, and nothing here was
measured on this project's data — by design, since §"Why this card is spec-only" argues
that measuring it on this data would produce a false number rather than a weak one.*

The mechanism is arithmetically sound, which is exactly why it is competed away. Every
peer-reviewed source above finds the same shape: real opportunities, negligible net profit
after costs for anyone without the lowest fee tier and the shortest path to the matching
engine or the leader.

## Caveats and limitations
- The single most important line on this card is that **three USD-quoted series cannot form
  a triangle**. If a future contributor adds `ETH/BTC` or `SOL/ETH` data, this becomes
  evaluable *in principle* and still not on bar data.
- `min_edge_bps` and `taker_fee_bps` are documented so the break-even arithmetic is
  reproducible. They are not tuned, because nothing was run.
- Not registered, so there is nothing to run. That is the correct state.
