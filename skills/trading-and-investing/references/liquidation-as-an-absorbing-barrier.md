---
name: liquidation-as-an-absorbing-barrier
# provenance: built in-thread 2026-08-05 — concept-family-explorer, CVS 4.65
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  Liquidation is not a stop-loss, and treating it as one is the most expensive
  category error in leveraged trading. Covers the three properties that separate
  them — liquidation is ABSORBING (you cannot be eventually right), it can forfeit
  100% of remaining collateral rather than closing at the price you chose, and it
  is PATH-dependent so a wick that fully reverts still ends the position; why this
  makes expected-value reasoning invalid and forces you to think about the ruin
  path instead; why the barrier DRIFTS toward you as carry accrues, so a stop safe
  at entry converges on it; the stop-versus-liquidation race and why the gap
  between them is the entire risk budget; and why a high win rate is compatible
  with certain ruin. Educational only — NOT financial advice.
keywords:
  - liquidation
  - absorbing barrier
  - risk of ruin
  - stop loss
  - path dependence
  - margin call
  - leverage
  - Kelly
  - perpetual futures
tags:
  - trading-and-investing
  - crypto
  - leverage
  - risk
---

# Liquidation as an Absorbing Barrier

> **Educational information only — NOT financial, investment, or tax advice.**

**Scope.**

| For… | Go to |
|---|---|
| The cost model, and how far the barrier sits at each leverage | `references/leverage-cost-arithmetic-and-the-viable-region.md` §4 |
| Why high trade counts compound this | `references/why-high-frequency-strategies-die-at-leverage.md` |
| Venue-specific liquidation mechanics, penalty and drift | `references/jupiter-perps-leverage-and-liquidation.md` |
| Who executes the liquidation, and the stop-vs-liquidation race | `references/solana-execution-agents-keepers-and-rfq.md` |
| Kelly, fractional Kelly, risk of ruin generally | `references/trading-risk-management.md` §2–§3 |

## Contents

1. Three properties that separate liquidation from a stop
2. Why expected value stops being the right tool
3. The barrier drifts toward you
4. The gap between stop and liquidation is the risk budget
5. A high win rate is compatible with certain ruin
6. Anti-patterns

---

## 1. Three properties that separate liquidation from a stop

They are both "the trade ends at a loss," which is why they get conflated. They are not
comparable events.

| | Stop-loss | Liquidation |
|---|---|---|
| **Who chooses the level** | You | The margin engine |
| **What you keep** | Collateral minus the realised loss | Possibly **nothing** — the penalty can take 100% of what remains |
| **Reversibility** | You can re-enter | Position is gone; capital is gone |
| **Trigger** | Your price | The oracle's price, on *its* cadence |
| **Effect on the strategy** | One losing trade | **Removal from the game** |

**Absorbing** is the technical property and the load-bearing one: it is a state you cannot
leave. Every model that assumes you can hold through an adverse excursion and be vindicated —
mean reversion, averaging down, "the thesis is still intact" — silently assumes a
*non*-absorbing barrier. At leverage that assumption is false, and it is false precisely when
it matters.

**Path dependence is the second trap.** A stop and a liquidation both trigger on a touch, but
the consequences of a touch differ by an order of magnitude. **A wick that fully reverts within
seconds still ends the position permanently** — and on an oracle-priced venue the trigger is the
oracle's print, which may not correspond to any trade you could have seen
(`solana-oracles-pyth-switchboard.md`).

## 2. Why expected value stops being the right tool

Without a barrier, expected value composes: a positive-expectancy strategy repeated enough
times converges to its expectation.

**With an absorbing barrier it does not**, because reaching the barrier removes the remaining
trials. The quantity that matters becomes **the probability of touching the barrier before the
edge compounds** — a first-passage problem, not an averaging one.

Two consequences that follow directly, and are routinely missed:

- **Two strategies with identical expected return can have completely different survival
  probabilities**, decided by volatility and barrier distance rather than by expectancy.
- **Increasing leverage raises expected return linearly and ruin probability non-linearly.**
  There is a leverage beyond which raising it *lowers* long-run growth even with positive
  expectancy — the standard Kelly result, and the barrier makes overshooting terminal rather
  than merely sub-optimal (`trading-risk-management.md` §3).

**Practical translation: size from the adverse move you must survive, not from the return you
want.** The return follows from the move; survival does not.

## 3. The barrier drifts toward you

On a borrow-fee venue, carry accrues against collateral continuously. Collateral shrinks, so
**effective leverage rises and the liquidation price moves toward the current price — with no
price move at all** (`jupiter-perps-leverage-and-liquidation.md` §3).

Two implications:

- **A stop placed at entry becomes less protective over time**, because the barrier it was
  measured against has moved. A stop safe at entry can be *behind* the barrier days later.
- **A position held long enough is liquidated by rent alone.** At illustrative Jupiter-scale
  rates, 250× is exhausted by carry in roughly a day and 50× in about ten days, on a
  perfectly flat chart (`leverage-cost-arithmetic-and-the-viable-region.md` §4).

**So "I'll just wait it out" is not a strategy on a borrow-fee venue — waiting is itself the
mechanism of loss.**

## 4. The gap between stop and liquidation is the risk budget

If the stop and the liquidation price coincide, the stop is decorative: the same adverse move
triggers both, and the liquidation penalty decides the outcome.

**The distance between them is the entire risk budget**, and it needs to be sized deliberately:

- **Too tight** — normal volatility stops you out repeatedly, and each round trip pays the fee
  twice (`why-high-frequency-strategies-die-at-leverage.md` §1).
- **Too wide** — the stop sits at or beyond the barrier and never fires first.

**And the stop is not guaranteed to win the race even when it is closer.** A conditional order
requires someone to execute it, and keeper reliability degrades exactly when volatility spikes —
which is the moment the stop matters (`solana-execution-agents-keepers-and-rfq.md`). Liquidation,
by contrast, is executed by a liquidator who is *paid* to be fast. **The two sides of the race
are not equally motivated**, and the asymmetry runs against you.

## 5. A high win rate is compatible with certain ruin

The property that makes barriers counterintuitive: **win rate says nothing about survival.**

A strategy taking small frequent profits and rare large losses can show a 90%+ win rate and
still touch the barrier, because one touch is terminal regardless of the ninety wins that
preceded it. This is the same structure behind grid's measured **100% win rate against a 37.5%
account decline** (`grid-trading-strategy.md` §5.3) — and leverage converts "account decline"
into "account gone."

**The diagnostic that does work is time-to-barrier under an adverse path**, not hit rate, and
not average trade. Ask "what sequence ends me, and how likely is that sequence?" — a question
hit rate cannot answer.

## 6. Anti-patterns

1. **Treating liquidation as a stop.** Different chooser, different residual, different
   reversibility (§1).
2. **Reasoning about a leveraged strategy in expected value alone.** The barrier invalidates
   the composition (§2).
3. **Planning to hold through an adverse excursion.** That assumes a non-absorbing barrier
   (§1–§2).
4. **Assuming the liquidation price is fixed.** Carry drifts it toward you (§3).
5. **Setting a stop once and not moving it** as the barrier drifts (§3).
6. **Placing a stop at or beyond the liquidation price** — decorative (§4).
7. **Assuming a stop beats a liquidator to the trigger.** Only one side is paid for speed (§4).
8. **Reading a high win rate as evidence of safety** (§5).

## References

Internal: `references/leverage-cost-arithmetic-and-the-viable-region.md` §4 (barrier distance
and time-to-liquidation-from-carry); `references/why-high-frequency-strategies-die-at-leverage.md`
(fee multiplication and the martingale pairing); `references/jupiter-perps-leverage-and-liquidation.md`
§3 (venue liquidation mechanics, the penalty, and the drift);
`references/solana-execution-agents-keepers-and-rfq.md` (keeper reliability and the
stop-vs-liquidation race); `references/solana-oracles-pyth-switchboard.md` (the oracle print is
the trigger); `references/trading-risk-management.md` §2–§3 (Kelly, fractional Kelly, risk of
ruin); `references/grid-trading-strategy.md` §5.3 (the measured 100%-win-rate case).

**Evidence note.** This reference is **structural reasoning about an absorbing barrier**, not a
measurement — the first-passage and Kelly arguments in §2 are standard results, stated without
external citation and not re-derived here. The figures it borrows are sourced: the drift and
penalty mechanics from `jupiter-perps-leverage-and-liquidation.md`, the carry-exhaustion times
from `leverage-cost-arithmetic-and-the-viable-region.md` §4 (closed-form arithmetic over venue
parameters, reproducible via `~/dev/solmargintrader/research/leverage_economics.py`), and the
100%-win-rate case from a first-party unlevered SOL backtest. **No levered scenario in this file
has been simulated**, and nothing here indicates that any leveraged strategy is profitable — it
describes only how one ends.
