---
name: leverage-cost-arithmetic-and-the-viable-region
# provenance: built in-thread 2026-08-05 — concept-family-explorer, CVS 5.00 (highest scored in this family)
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  What a leveraged perpetual position must overcome before it earns anything, and
  the counterintuitive result that reframes the question: LEVERAGE CANCELS OUT OF
  THE BREAK-EVEN EQUATION. A 2x and a 250x position need the same price move to
  break even. Covers the four costs (round-trip fee, borrow carry, liquidation,
  liquidation drift) and which strategy property each one kills; the fee/carry
  HINGE that splits leveraged trading into two regimes rewarding opposite
  behaviour; time-to-liquidation-from-carry-alone as the number that should
  govern leverage choice; and the carry asymmetry that puts the crowded side on
  the expensive side of the fee schedule. Educational only — NOT financial advice.
keywords:
  - leverage
  - perpetual futures
  - borrow fee
  - carry cost
  - break-even
  - funding rate
  - holding period
  - liquidation
  - Jupiter Perps
  - cost model
tags:
  - trading-and-investing
  - crypto
  - solana
  - leverage
  - risk
---

# Leverage Cost Arithmetic and the Viable Region

> **Educational information only — NOT financial, investment, or tax advice.** Leveraged
> perpetuals can lose your entire collateral, and on a venue with a liquidation penalty they
> routinely do.

**Scope.**

| For… | Go to |
|---|---|
| Why liquidation is not a stop, and ruin under an absorbing barrier | `references/liquidation-as-an-absorbing-barrier.md` |
| Why trade *count* specifically is fatal at leverage | `references/why-high-frequency-strategies-die-at-leverage.md` |
| Venue mechanics — oracle execution, the borrow-fee model, margin | `references/jupiter-perps-trading.md`; `references/jupiter-perps-leverage-and-liquidation.md` |
| Generic perp/funding theory | `references/crypto-and-digital-asset-trading.md` §2–§4 |
| Position sizing and risk of ruin generally | `references/trading-risk-management.md` §2–§3 |

## Contents

1. Leverage cancels
2. The four costs
3. The fee/carry hinge
4. The number that should govern leverage choice
5. Carry asymmetry and the crowded side
6. Anti-patterns

---

## 1. Leverage cancels

Write profit and loss as a percentage of **collateral**, at leverage `L`:

```
pnl%_collateral  = L·move − (fee_rt·L + rate·util·hours·L)
break_even_move  = fee_rt + rate·util·hours          ← L cancels
```

**A 2× and a 250× position need the identical price move to break even.** Leverage does not
make a trade harder to win.

What it changes is exactly two things, and both are survival terms rather than profitability
terms:

1. **How close the absorbing barrier sits** — at 10× a 10% adverse move ends you; at 250×,
   0.40%.
2. **How fast carry consumes collateral** — the same hourly rate applied to a larger notional.

**This matters because the common intuition is wrong in a specific, expensive way.** "High
leverage needs a bigger edge" is false: it needs the *same* edge, delivered before the barrier
is touched and before carry eats the position. The cost of leverage is concentrated entirely in
the ruin path, which is why it cannot be reasoned about with expected-value arithmetic alone.

## 2. The four costs

| Cost | Typical magnitude | What it kills |
|---|---|---|
| **Round-trip fee** | ~12 bps of notional (6 each way) | **Frequency** — multiplied by `L` *and* by trade count |
| **Borrow carry** | Hourly, utilisation-driven, **never negative** | **Duration** — pure theta, and nobody is ever paid to wait |
| **Liquidation** | Can forfeit **100% of remaining collateral** | **Being eventually right** — the barrier is absorbing |
| **Liquidation drift** | Carry accrues against collateral | **Fixed stops** — the barrier walks toward you while you hold |

**The borrow fee is the one most often misread, and the error is structural.** On a
borrow-fee venue it is **not** a funding rate: both sides always pay, the rate is never
negative, and there is no mechanism by which holding pays you. A trader who models it as
funding budgets for a cost that sometimes reverses, and it never does
(`jupiter-perps-trading.md` §2).

**Liquidation drift is the quietly dangerous one.** Because carry accrues against collateral,
effective leverage rises while you hold a position you have not touched. A stop placed at a
comfortable distance at entry converges on the liquidation price over time — the position
becomes more fragile the longer it is held, with no price move required.

## 3. The fee/carry hinge

Fees are paid **per round trip**; carry is paid **per hour**. So the dominant cost depends
entirely on holding period, and there is a crossover.

Using illustrative Jupiter-scale parameters (~12 bps round trip; ~0.016%/hr max on the
volatile custody, ~0.003%/hr on the stable one, at 50% utilisation):

| Hold | Break-even move, long | Break-even move, short |
|---|---:|---:|
| 1 hour | 0.128% | 0.121% |
| 1 day | 0.312% | 0.156% |
| 1 week | 1.464% | 0.372% |
| 1 month | **5.880%** | 1.200% |

**Carry overtakes the round-trip fee at roughly 15 hours for longs and 80 hours for shorts**
(7.5 h and 40 h at full utilisation).

**That hinge splits leveraged trading into two regimes that reward opposite behaviour:**

- **Below it — fee-dominated.** Trade *count* is the enemy. Fewer, larger trades win.
- **Above it — carry-dominated.** *Time* is the enemy. Conviction must resolve quickly.

**A strategy that straddles the hinge pays both costs and is optimised for neither.** Deciding
which side of it you are on is a design decision, not an outcome — and it is upstream of
signal choice.

## 4. The number that should govern leverage choice

Not "how much can I control?" but **how long can I survive doing nothing?**

Time until carry *alone* zeroes the collateral, with the price perfectly flat:

| Leverage | util 50% | util 100% | Adverse move to liquidate |
|---|---:|---:|---:|
| 5× | 104.2 d | 52.1 d | 20.00% |
| 10× | 52.1 d | 26.0 d | 10.00% |
| 20× | 26.0 d | 13.0 d | 5.00% |
| 50× | 10.4 d | 5.2 d | 2.00% |
| 100× | 5.2 d | 2.6 d | 1.00% |
| 250× | **2.1 d** | **1.0 d** | **0.40%** |

**At 250× you are liquidated in about a day by rent, on a flat chart.** And 0.40% is routine
intraday noise on a volatile asset — the position does not need a thesis to be wrong, only a
wick.

**These are the optimistic readings.** They show when collateral reaches zero, *before* the
liquidation penalty and *before* price impact.

**The practical rule this suggests:** pick leverage from the two survival columns — the hold
time you actually need, and the adverse move you must tolerate — rather than from the return
you want. The return follows from the move; the survival does not.

## 5. Carry asymmetry and the crowded side

On a venue where longs borrow the **volatile** custody and shorts borrow the **stable** one,
the two sides do not pay the same rent. Illustratively ~140% APR against ~23% APR — roughly a
**5× asymmetry** in carry cost.

**And the crowd is typically on the expensive side.** Measured open interest on Jupiter Perps
runs **85–90% long** (`jlp-risk-profile-and-anti-patterns.md` §3). The majority position is
also the one paying materially more to wait.

That is not a trade recommendation — a cheaper carry does not make a direction correct, and the
crowd being long is not evidence it is wrong. It is a **cost fact that belongs in the
break-even calculation before direction is chosen**, and it is routinely omitted.

## 6. Anti-patterns

1. **Believing high leverage requires a bigger edge.** It requires the same move; it just
   removes your margin for being early (§1).
2. **Modelling the borrow fee as a funding rate.** Funding can pay you; borrow never does (§2).
3. **Choosing leverage from the return you want** rather than the survival time and adverse
   move you need (§4).
4. **Holding a position across the fee/carry hinge** without deciding which regime you are
   trading (§3).
5. **Treating the liquidation price as fixed.** Carry drifts it toward you with no price move
   (§2).
6. **Comparing long and short setups without their different carry** (§5).
7. **Quoting a break-even that omits price impact.** It is strictly additive and, on this
   venue, not computable from public documentation (`jupiter-perps-trading.md` §1).

## References

Internal: `references/liquidation-as-an-absorbing-barrier.md` (the ruin path);
`references/why-high-frequency-strategies-die-at-leverage.md` (the frequency term);
`references/jupiter-perps-trading.md` §1–§2 (oracle execution, the borrow-fee model);
`references/jupiter-perps-leverage-and-liquidation.md` §3 (margin, drift, penalty);
`references/jlp-risk-profile-and-anti-patterns.md` §3 (the 85–90% long open-interest skew);
`references/trading-risk-management.md` §2–§3 (sizing, risk of ruin);
`references/crypto-and-digital-asset-trading.md` §2–§4 (generic perp and funding theory).

**Evidence note.** The tables are **closed-form arithmetic over published venue parameters**,
not a backtest — reproduce with `~/dev/solmargintrader/research/leverage_economics.py`
(`--self-test` asserts the seven load-bearing claims). The per-custody borrow rates are
**Gauntlet's May-2024 recommendation, not a live read**, and utilisation moves continuously, so
every figure is an order-of-magnitude frame rather than a quote. **Price impact is not
modelled** — the per-custody parameters are on-chain and undocumented — nor are keeper latency,
priority fees, failed transactions, or the liquidation penalty itself. **Every omission makes
the real picture worse, never better.** Venue parameters change; verify at `docs.jup.ag`.
**This is a cost model and says nothing about edge** — see the caveat in
`references/why-high-frequency-strategies-die-at-leverage.md` §5.
