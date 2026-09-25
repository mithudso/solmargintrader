---
name: strategies-and-risk
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  How option legs combine, organised by the one property that decides whether a
  position can ruin you — DEFINED vs UNDEFINED risk. Every core structure with
  construction, outlook, max profit, max loss and breakeven: long call/put,
  covered call, cash-secured put, protective put, collar, the four verticals,
  straddles and strangles, iron condor, iron butterfly, long butterfly, calendars
  and diagonals. Plus the break-even win-rate arithmetic that punctures
  "high-probability" premium selling, assignment and pin risk, leg risk on
  spreads, options approval levels and margin, and the multi-leg execution cost
  that eats theoretical edge. Educational only — NOT financial advice.
keywords:
  - defined risk
  - undefined risk
  - covered call
  - cash-secured put
  - protective put
  - collar
  - vertical spread
  - bull call spread
  - bear put spread
  - credit spread
  - debit spread
  - straddle
  - strangle
  - iron condor
  - iron butterfly
  - butterfly spread
  - calendar spread
  - diagonal spread
  - breakeven
  - max loss
  - pin risk
  - assignment
  - leg risk
  - options approval level
  - win rate
---

# Strategies & Risk

Sub-reference of **`options-trading-and-strategies`**. The contract is `options-fundamentals`; sensitivities `the-greeks`; pricing `volatility-and-pricing`.

> **Educational information only — NOT financial, investment, or tax advice, and NOT a recommendation of any strategy.** No structure below is safe, conservative, or an income guarantee, whatever it is commonly called. **Undefined-risk positions can lose more than your account holds**; a naked short call is theoretically unlimited. Assignment can occur at any time on American options and can convert a hedged position into an unhedged one. Sizing is not covered here — that is `trading-risk-management`, and it is the difference between a survivable strategy and a fatal one.[^sec-options]

## Contents

1. Reading the tables
2. The organising principle: defined vs undefined risk
3. The break-even win rate — the arithmetic that punctures "high probability"
4. Single-leg
5. Stock plus option
6. Vertical spreads
7. Straddles and strangles
8. Iron condors, iron butterflies, butterflies
9. Calendars and diagonals
10. Assignment, pin risk, and leg risk
11. Approval levels, margin, and execution cost
12. Anti-patterns

## 1. Reading the tables

All figures are **per share**; multiply by 100 per standard contract (`options-fundamentals` §3). Notation: `K` strike, `W` spread width (difference between strikes), `D` net debit paid, `C` net credit received, `B` stock cost basis, `N` net **debit** for a multi-leg overlay (**negative when it is a net credit** — collars frequently are, and plugging a positive number for a credit makes max profit, max loss and breakeven all wrong at once). Figures are **at expiration** and **ignore commissions, fees and the bid/ask spread** — all of which are real and all of which make the true breakeven worse (§11).

Every entry states **defined** or **undefined** risk. That column matters more than any other. Construction, maximum profit/loss and breakeven for every structure below are cross-checked against the OIC strategy library.[^oic-strategies]

## 2. The organising principle: defined vs undefined risk

**Defined risk** — the worst case is knowable at entry and bounded by the structure itself. Long options and every spread with a purchased protective wing.

**Undefined risk** — the worst case is not bounded by the structure. Strictly this is two tiers, and
collapsing them is imprecise:

- **Unbounded** — the short call. No arithmetic worst case exists.
- **Bounded but total** — short put, covered call. A finite number (`K − C`, `B − C`) that happens to
  be your whole position. Being "cash-secured" or "covered" changes the *funding* of that loss, not
  its size.

Both are unlike a spread, whose worst case is a small fraction of capital by construction.[^occ-odd-strat] The tables
use "equity-like downside: bounded but total" for the second tier rather than overloading
"undefined".

**Why this is the right primary axis, rather than bullish/bearish/neutral:**

- It determines whether a single event can end you. Direction determines whether a trade wins.
- It is invariant. A directional view can be wrong and recoverable; an unbounded loss is neither.
- **It is the axis most often obscured in how these strategies are sold.** Covered calls and cash-secured puts are routinely presented as conservative income. Their risk profile is not conservative: a covered call has the **same downside as owning the stock** less the premium, and **caps the upside** that was the reason to own it. That is a real trade-off, not a free yield.

**The honest statement of the covered call:** you have sold your upside for a premium and kept all of your downside.

## 3. The break-even win rate — the arithmetic that punctures "high probability"

Any defined-risk trade has a break-even win rate, ignoring costs:

```
break-even win rate = max loss / (max loss + max profit)
```

**This assumes binary outcomes** — every trade resolving at exactly max profit or exactly max loss.
Real spreads finish partially in between, and managing exits early changes the number materially. Use
it as the floor it is, not as a simulation.

Apply it to a typical "high-probability" credit spread — **$5 wide, sold for $0.50**:

- Max profit = $0.50. Max loss = $5.00 − $0.50 = **$4.50**.
- Break-even win rate = 4.50 / 5.00 = **90%**.

So the strategy needs to win **nine times in ten just to break even before costs**. A 90%-win-rate strategy is not profitable — it is exactly neutral. Add commissions and four bid/ask crossings and it loses.

**This is the single most useful number in this document.** It explains:

- Why a high win rate is not evidence of edge. Win rate and payoff ratio are two halves of one quantity, and quoting either alone is uninformative.
- Why sellers of far-OTM premium can be right for years and then surrender it. The distribution is designed that way, and `volatility-and-pricing` §2 explains why the market pays for it.
- Why the *ratio of credit to width* is the first thing to compute on any credit spread. Selling $0.50 of a $5 wing is a very different trade from selling $1.75 of it (break-even 65%).

**Run this before every premium-selling trade.** If the implied required win rate exceeds what you can honestly claim to achieve, the trade is not
"high probability" **in any sense that implies edge** — the payoff ratio is the other half of the
number. Note what this does *not* establish: the break-even win rate is an accounting identity in
`C/W` (`BE = 1 − C/W`), true whatever the volatility premium is, so it cannot tell you a trade is
*fairly* priced. `volatility-and-pricing` §2 finds implied volatility has historically **exceeded**
subsequent realised volatility, which points the other way. The identity tells you what you must be
right about; it does not tell you the odds are fair.

## 4. Single-leg

| Strategy | Construction | Outlook | Max profit | Max loss | Breakeven | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| **Long call** | buy 1 call `K`, debit `D` | strongly bullish, soon | unlimited | `D` | `K + D` | **defined** |
| **Long put** | buy 1 put `K`, debit `D` | strongly bearish | `K − D` (underlying → 0) | `D` | `K − D` | **defined** |
| **Naked short call** | sell 1 call `K`, credit `C` | neutral / bearish | `C` | **unlimited** | `K + C` | **UNDEFINED** |
| **Naked short put** | sell 1 put `K`, credit `C` | neutral / bullish | `C` | `K − C` | `K − C` | **UNDEFINED** |

**On long options.** The bounded loss is the whole appeal, and the common outcome is losing it. You are paying theta for gamma (`the-greeks` §7); the trade needs the move to be **larger and sooner** than priced (`volatility-and-pricing` §4).

**On naked shorts.** A naked call has no upper bound — a takeover bid overnight is the canonical destroyer. Most brokers require the highest approval tier and substantial margin (§11).

## 5. Stock plus option

| Strategy | Construction | Outlook | Max profit | Max loss | Breakeven | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| **Covered call** | own 100 sh at `B`; sell 1 call `K`, credit `C` | mildly bullish / flat | `(K − B) + C` | `B − C` (stock → 0) | `B − C` | **equity-like downside: bounded but total**, capped upside |
| **Cash-secured put** | sell 1 put `K`, credit `C`; hold `K×100` cash | mildly bullish / flat | `C` | `K − C` (→ 0) | `K − C` | **equity-like downside: bounded but total** |
| **Protective put** | own 100 sh at `B`; buy 1 put `K`, debit `D` | bullish, want a floor | unlimited | `(B − K) + D` | `B + D` | **defined** |
| **Collar** | own 100 sh at `B`; buy put `Kp`, sell call `Kc`; net `N` | protect a gain cheaply | `Kc − B − N` | `B − Kp + N` | `B + N` | **defined both ways** |

**The equivalence worth knowing:** a **covered call and a cash-secured put at the same strike have the same payoff shape** — both are short a put, synthetically (`volatility-and-pricing` §10). They differ in capital mechanics, **dividend entitlement, assignment trigger** and tax treatment — not
in **payoff shape**. Three precisions the shorthand drops: it needs the **same expiry** as well as the
same strike; the levels coincide only when the stock is bought at the current price (a buy-write), not
at an arbitrary basis `B`; and the covered-call holder **receives dividends** while the put seller does
not, with the assignment triggers **opposite** (short call bites in a rally, short put in a decline).
People who consider the covered call conservative and the short put reckless are still describing the
same risk twice.

**Protective put** is the one genuinely defensive structure here, and it is not free: the premium is a recurring cost that drags on returns in every period the insurance is not needed. That is what insurance is.

**Collar** finances the put by selling the call. It defines both ends and is the standard way to protect a large appreciated holding — at the cost of giving away the upside above `Kc`.

## 6. Vertical spreads

Same expiry, same type, two different strikes. Width `W = |K₂ − K₁|`. All four are **defined risk** — the reason to prefer them.

| Strategy | Construction | Outlook | Max profit | Max loss | Breakeven |
| --- | --- | --- | --- | --- | --- |
| **Bull call (debit)** | buy call `K₁`, sell call `K₂` (`K₂>K₁`); debit `D` | bullish | `W − D` | `D` | `K₁ + D` |
| **Bear put (debit)** | buy put `K₂`, sell put `K₁`; debit `D` | bearish | `W − D` | `D` | `K₂ − D` |
| **Bull put (credit)** | sell put `K₂`, buy put `K₁`; credit `C` | bullish / flat | `C` | `W − C` | `K₂ − C` |
| **Bear call (credit)** | sell call `K₁`, buy call `K₂`; credit `C` | bearish / flat | `C` | `W − C` | `K₁ + C` |

**Debit vs credit is largely presentation.** A bull call spread and a bull put spread at the same strikes express the same view with near-identical risk graphs. Real differences: assignment exposure (the credit version has a short ITM leg as it goes wrong), capital treatment, and which side of the **skew** you are on (`volatility-and-pricing` §5).

**The spread caps your upside to buy down your cost** — that is the trade. And per §3, always compute `C / W` on a credit spread before anything else.

## 7. Straddles and strangles

Volatility structures: a view on **magnitude**, not direction.

| Strategy | Construction | Outlook | Max profit | Max loss | Breakeven | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| **Long straddle** | buy call + put, same `K`; debit `D` | big move, either way | unlimited up; `K − D` down | `D` | `K ± D` | **defined** |
| **Short straddle** | sell call + put, same `K`; credit `C` | very quiet | `C` | **unlimited up; `K − C` down** | `K ± C` | **UNDEFINED both sides** |
| **Long strangle** | buy OTM put `Kp` + OTM call `Kc`; debit `D` | very big move | unlimited up; `Kp − D` down | `D` | `Kc + D`, `Kp − D` | **defined** |
| **Short strangle** | sell OTM put + OTM call; credit `C` | quiet, range-bound | `C` | **unlimited up; `Kp − C` down** | `Kc + C`, `Kp − C` | **UNDEFINED upside** |

**Long straddle is expensive by construction** — you are buying the two most vega-rich options on the board and paying theta on both. It profits only if realised movement exceeds the *priced* movement, which is precisely `volatility-and-pricing` §4's point about events.

**Short straddles and strangles are the archetypal short-gamma position.** High win rate, and losses that accelerate rather than accumulate as the underlying moves (`the-greeks` §3). This is the structure the "pennies in front of a steamroller" phrase was coined for. The **iron** versions in §8 are the defined-risk equivalents and exist precisely to bound this.

## 8. Iron condors, iron butterflies, butterflies

Four-leg defined-risk structures. These are short straddles/strangles with **purchased wings** that convert unbounded loss into a known one.

| Strategy | Construction | Outlook | Max profit | Max loss | Breakeven | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| **Iron condor** | sell OTM put spread + sell OTM call spread; credit `C`, each wing width `W` | range-bound | `C` | `W − C` | short-put strike `− C`; short-call strike `+ C` | **defined** |
| **Iron butterfly** | sell ATM put + ATM call, buy both wings; credit `C`, width `W` | pinned at `K` | `C` | `W − C` | `K ± C` | **defined** |
| **Long call butterfly** | buy `K₁`, sell 2× `K₂`, buy `K₃` (equidistant); debit `D` | expires near `K₂` | `(K₂ − K₁) − D` | `D` | `K₁ + D` and `K₃ − D` | **defined** |

**Why max loss is one wing, not two.** At expiration the underlying cannot be simultaneously below the put spread and above the call spread. Only one side can finish in the money, so the condor's loss is bounded by the **wider single wing** less the credit — not the sum. This is the structural reason the condor is capital-efficient relative to two separate credit spreads.

**Iron butterfly vs iron condor:** the butterfly sells the ATM straddle, so it collects a much larger credit and has a much narrower profit zone. Higher credit-to-width ratio means a **lower break-even win rate** (§3) — and a far lower probability of achieving it. The two are points on one continuum, and §3's arithmetic is how to compare them honestly rather than by "probability of profit" alone.

**Long butterfly** is the debit expression of the same pinned view: cheap, defined, and profitable only in a narrow band.

## 9. Calendars and diagonals

The only structures here that trade the **term structure** (`volatility-and-pricing` §6).

- **Long calendar spread** — same strike; **sell** the near expiry, **buy** the far. Net debit. Profits from the near leg decaying faster than the far leg (theta differential) and from **rising IV in the back month** — it is a **long-vega** position, unlike most credit structures.
- **Diagonal spread** — different strikes *and* different expiries. A calendar with a directional tilt.

**Max profit has no clean closed form**, because the position's value at the near expiry depends on where IV and the term structure sit then — not just on the underlying's price. Max loss is approximately the debit paid. Treat "max loss = debit" as a good approximation, **not a
guarantee**, and know the two mechanisms that break it: **early assignment of the short near leg**
(§10's leg risk, leaving you holding stock against a long option), and — for put calendars or around a
large dividend — the longer-dated option not necessarily being worth more than the shorter, so the
spread's value can go **negative**.

**Where calendars are used:** to express "IV is low in the back month relative to the front", or to hold a longer-dated view while financing it with near-dated decay. **Where they surprise people:** a parallel collapse in the whole IV surface hurts the long back-month leg most, so a calendar can lose while the underlying does exactly what you wanted.

## 10. Assignment, pin risk, and leg risk

Three operational risks that turn a defined-risk position into something else. All three are why "max loss" at expiry is not the same as "worst case".

**Early assignment.** American shorts can be assigned any time (`options-fundamentals` §7). The reliably predictable case is a **short call just before ex-dividend** when the dividend exceeds remaining extrinsic value. Covered-call and call-credit-spread writers are the routine casualties.

**Pin risk.** The underlying closes *at or extremely near* your short strike at expiry. You do not know whether you were assigned until after the close, and you cannot hedge a position you do not know you have. A weekend gap then lands on an unintended stock position. Cash-settled index options (SPX) have **no pin risk** — there are no shares to deliver.[^cboe-strat] That is a real
structural advantage, but **it is not strictly safer**: cash settlement *substitutes* settlement-value
risk. A standard third-Friday SPX contract settles against Friday's **opening** Special Opening
Quotation, which cannot be traded against and whose last trading day is the Thursday before. See
`options-fundamentals` §5 — do not read "no pin risk" as "no expiry risk".

**Leg risk / one-sided assignment.** On a spread, the short leg is assigned and the long leg expires worthless (or is not exercised). The defined-risk position becomes a **naked stock position**, financed on margin, over a weekend. This is the mechanism by which a "max loss $450" trade produces a loss far larger than $450.

**Mitigations, in order of reliability:** close before expiry rather than letting positions run to it; prefer cash-settled index products for short premium; know the ex-dividend calendar on anything you are short calls in; never assume the wings will offset automatically.

## 11. Approval levels, margin, and execution cost

**Approval levels.** Brokers gate options by tier, roughly: covered calls and long options at the lowest, spreads next, naked/undefined-risk highest. Tier names and requirements are **broker-specific and change** — verify with yours (as of 2026).[^finra-options]

**Margin.** Defined-risk spreads are typically margined at max loss — capital-efficient and predictable. **Undefined-risk positions carry formula-based requirements that can expand sharply as the position moves against you**, which is exactly when you least want a capital call. That reflexivity — the requirement growing as the loss grows — is a distinct risk from the loss itself.

**Execution cost, which is where theoretical edge goes to die.** Options spreads are wide relative to their premium, and multi-leg structures cross the spread **on every leg, twice** (open and close). An iron condor is eight crossings. On a $0.50 credit, eight crossings at $0.05 each is **$0.40 — 80% of
the theoretical maximum profit before commissions**. (Count four if you assume winners are left to
expire worthless so only the opening is paid: $0.20, still 40%.)

Consequences that should shape strategy selection, not just execution:
- **Trade liquid underlyings.** Liquidity is a selection criterion (`options-fundamentals` §9).
- **Use a single net debit/credit combination order.** Never leg in.
- **Recompute §3's break-even win rate using the price you can actually transact at**, not the mid. That is the only version of the number that means anything.

## 12. Anti-patterns

1. **Calling covered calls and cash-secured puts conservative income.** Full downside, capped upside; and they are the same synthetic position (§5).
2. **Selling a narrow credit for a small fraction of the width.** A $5 wing for $0.50 needs a 90% win rate to break even (§3).
3. **Quoting win rate without payoff ratio, or probability of profit without max loss.** Each is half a number (§3).
4. **Believing a defined-risk spread cannot exceed its max loss.** One-sided assignment makes it a naked stock position (§10).
5. **Holding short options through expiry near the strike.** Pin risk (§10) plus exercise-by-exception (`options-fundamentals` §8).
6. **Being short calls through an ex-dividend date** without checking the dividend against remaining extrinsic value (§10).
7. **Sizing undefined-risk positions on the credit received.** The credit is the maximum *gain*; it says nothing about the risk (§2).
8. **Ignoring that undefined-risk margin expands as you lose** (§11).
9. **Comparing structures on mid prices.** Eight crossings on a condor can consume most of the theoretical edge (§11).
10. **Treating a long calendar as direction-neutral and vega-neutral.** It is long vega and exposed to the term structure (§9).
11. **Trading a long straddle into a scheduled event on a directional view.** You need to beat the priced move (§7).
12. **Using this page for sizing.** Max loss per contract is not a position size — that is `trading-risk-management`.

## References (sources)

[^occ-odd-strat]: OCC — *Characteristics and Risks of Standardized Options*, the mandatory pre-trade disclosure; the authority for the uncovered-writing risk statements underpinning §2 and §4. https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document — tier-1 (regulator-mandated disclosure). verified-as-of: 2026-08-05
[^oic-strategies]: Options Industry Council — strategy library with construction, maximum profit/loss and breakeven for each of the structures tabulated in §4–§9, plus exercise-and-assignment guidance behind §10. https://www.optionseducation.org/strategies — tier-1 (authoritative industry education, OCC-sponsored). verified-as-of: 2026-08-05
[^finra-options]: FINRA — options investor guidance, including account approval, suitability and the risks of options strategies marketed as income. https://www.finra.org/investors/investing/investment-products/options — tier-1 (SRO). Supports §11's approval-level framing and §2's caution about how these strategies are sold. verified-as-of: 2026-08-05
[^cboe-strat]: Cboe — strategy education and index-option product characteristics, including the absence of pin risk on cash-settled index options (§10). https://www.cboe.com/education/ — tier-1 (exchange). verified-as-of: 2026-08-05
[^sec-options]: SEC / Investor.gov — investor bulletins on options and on the risks of leveraged strategies. https://www.investor.gov/ — tier-1 (regulator). verified-as-of: 2026-08-05
