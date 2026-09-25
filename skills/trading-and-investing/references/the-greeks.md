---
name: the-greeks
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  The risk sensitivities of an option position. Delta (direction, hedge ratio,
  and precisely why it is NOT the probability of profit — N(d1) vs N(d2)); gamma
  as convexity and the short-gamma failure mode; theta and why decay is
  non-linear; vega and where volatility exposure actually sits; rho and the one
  place it matters. The long-vs-short sign table and the single structural
  trade-off it encodes (long options are always +gamma/+vega, and -theta for any
  option with meaningful extrinsic value; short options mirror it). Position and portfolio aggregation, delta-neutral hedging and
  why it does not stay neutral, and the second-order Greeks (vanna, charm,
  vomma). Educational only — NOT financial advice.
keywords:
  - delta
  - gamma
  - theta
  - vega
  - rho
  - Greeks
  - hedge ratio
  - convexity
  - time decay
  - implied volatility sensitivity
  - short gamma
  - long premium
  - short premium
  - delta neutral
  - position Greeks
  - vanna
  - charm
  - vomma
  - N(d1)
  - N(d2)
---

# The Greeks

Sub-reference of **`options-trading-and-strategies`**. The contract itself is `options-fundamentals`; what it is worth and why is `volatility-and-pricing`; how legs combine is `strategies-and-risk`.

> **Educational information only — NOT financial, investment, or tax advice.** The Greeks are **model outputs, not measurements**. They are partial derivatives computed from a pricing model on assumptions the market violates — they describe sensitivity *right now, to a small move, holding everything else fixed*, and every one of those qualifiers fails in a real dislocation. A position that is Greek-neutral is not risk-free. A long option can lose 100% of premium; a naked short call can lose without limit.

## Contents

1. What a Greek is, and the four qualifiers that limit it
2. Delta — direction, hedge ratio, and the probability error
3. Gamma — convexity, and the short-gamma failure mode
4. Theta — decay, and why it is not linear
5. Vega — the volatility exposure
6. Rho — and the one place it matters
7. The sign table, and the trade-off it encodes
8. Position and portfolio Greeks
9. Delta-neutral hedging, and why it does not stay neutral
10. Second-order Greeks
11. Anti-patterns

## 1. What a Greek is, and the four qualifiers that limit it

Each Greek is a **partial derivative** of the option's theoretical value with respect to one input. Delta is ∂V/∂S, vega is ∂V/∂σ, and so on.

Four qualifiers travel with every one of them, and forgetting them is how the Greeks get misused:

1. **Local.** A derivative describes behaviour for an *infinitesimal* move. Delta 0.50 does not mean "gains $0.50 for a $10 move"; over $10 the delta itself has changed (that is gamma).
2. **Instantaneous.** Computed for right now. Every Greek changes as spot, time, and volatility change.
3. **Ceteris paribus.** ∂V/∂S holds volatility and time fixed. In reality a large spot move *arrives with* a volatility change — so the realised P&L is a delta effect plus a vega effect plus a gamma effect, and attributing it to delta alone will not reconcile.
4. **Model-dependent.** They come from a model (usually Black-Scholes-Merton or a binomial lattice) whose assumptions are known to be false — see `volatility-and-pricing` §8 for the assumption-by-assumption table. Two brokers can quote different Greeks for the same contract because they used different volatility inputs.

**The honest framing:** the Greeks are a **risk-decomposition language**, excellent for comparing positions and terrible as a forecast.

## 2. Delta — direction, hedge ratio, and the probability error

**Delta (Δ) = ∂V/∂S** — the change in option value per $1 change in the underlying.

- **Calls: 0 to +1.** Deep OTM → near 0; deep ITM → near +1.
- **Puts: −1 to 0.** Deep OTM → near 0; deep ITM → near −1.
- **ATM ≈ ±0.50.**

Three correct readings:

1. **Directional exposure.** A +0.40 delta call gains ≈ $0.40 per share ($40 per contract) on a $1 rise — *for a small rise*.
2. **Share equivalence.** A +0.40 delta contract behaves like **40 shares** of the underlying (0.40 × 100). This is the most practically useful reading: it converts an option book into a comparable stock position.
3. **Hedge ratio.** To neutralise 100 long shares, sell calls totalling +1.00 of delta.

### Delta is not the probability of finishing in the money — and it is definitely not the probability of profit

You will constantly see "delta ≈ probability of expiring ITM". It is an approximation with two distinct errors, and both matter.

**Error 1 — the wrong quantity, and it points in opposite directions for calls and puts.** In
Black-Scholes a call's delta is **N(d₁)**, while the **risk-neutral probability of finishing ITM is
N(d₂)**, where `d₂ = d₁ − σ√T`. Since σ√T > 0, **N(d₂) < N(d₁)**:

- **For a call, delta OVERSTATES** the risk-neutral ITM probability.
- **For a put, delta UNDERSTATES it.** |Δ_put| = N(−d₁) and the ITM probability is N(−d₂); because
  −d₁ < −d₂, **|Δ_put| < N(−d₂)** — by exactly the amount the call overstates.

The gap widens with volatility and with time to expiry, and it gets large: a 2-year 10%-OTM put at
|Δ| = 0.258 has a risk-neutral ITM probability of about **0.411**. **Applying a blanket "delta
overstates" correction to a short put therefore moves you the wrong way** — it understates the risk
you are taking, which is the dangerous direction.[^hull]

**Error 2 — the wrong probability measure.** N(d₂) is a **risk-neutral** probability, a pricing construct. It is not the real-world likelihood of the event, because the risk-neutral measure prices in risk aversion.

**And a third, which is the practical killer:** finishing ITM is not the same as making money. A long option that finishes $0.05 ITM after you paid $2.00 expired 97.5% down. **Probability of touching, probability of finishing ITM, and probability of profit are three different
numbers**, and delta approximates only the middle one — badly, and with a sign that depends on
whether you hold a call or a put.

Use delta for exposure and hedging. Do not build a strategy on it as a probability.

## 3. Gamma — convexity, and the short-gamma failure mode

**Gamma (Γ) = ∂Δ/∂S = ∂²V/∂S²** — how fast delta changes.

Gamma is the mathematical content of the word **optionality**. A linear instrument (stock, future, forward) has **constant** delta — 1 per share of spot — and **gamma exactly zero**; its sensitivity never changes. (Constant is the property that matters; the *level* is not always 1, since a forward's delta with respect to spot is e^(−qT) and a future's is e^((r−q)T).) An option's does. Everything that makes options interesting, and dangerous, lives in gamma.

**Where gamma is large:**
- **At the money**, always.
- **Near expiry**, for ATM options — gamma spikes sharply as time runs out, because delta must resolve from ~0.50 to either 0 or 1 in a shrinking window.

**Long gamma (buying options):** your delta moves *in your favour* automatically. Rally and you get longer; sell off and you get shorter. Convexity works for you, and the price you pay is theta (§4).

**Short gamma (writing options):** your delta moves *against* you. This is the structural failure mode of premium selling:

> A short ATM straddle near expiry is short enormous gamma. As the underlying moves, the position's delta grows against the move — it gets longer as the market falls and shorter as it rallies. Losses accelerate rather than accumulate linearly, and hedging into that move means transacting at progressively worse prices.[^occ-odd-greeks]

This is what "**picking up pennies in front of a steamroller**" describes: a high win rate with a left tail deep enough to erase many wins. It is not an argument against selling premium — it is an argument for **defined-risk** structures (`strategies-and-risk` §2) and for sizing that survives the tail.

## 4. Theta — decay, and why it is not linear

**Theta (Θ) = ∂V/∂t** — value lost per day, all else equal. Conventionally quoted **negative for a long option**.

Only **extrinsic** value decays; intrinsic value does not (`options-fundamentals` §4). At expiry, extrinsic value is exactly zero.

**Decay is not a straight line, and the shape depends on moneyness:**

- **ATM options** decay slowly at first and then **accelerate sharply into expiry** — the classic convex curve, roughly proportional to 1/√T.
- **Deep OTM options** decay earlier and then flatten; there is little left to lose in the final days.
- **Deep ITM options** are mostly intrinsic, so little to decay.

**Theta and gamma are the same coin.** For a long option, theta is the rent you pay for gamma. For a short option, theta is the income you collect for supplying it. This is why "theta is positive so this trade makes money" is incomplete: you are being paid for a risk, and the payment is calibrated so that, on the model's assumptions, it is fair. Any edge must come from the *volatility* being mispriced (`volatility-and-pricing` §2), not from theta existing.

**Weekends decay too.** Time value is a function of calendar time, not trading sessions, so a Friday-to-Monday hold pays three days of theta with no opportunity to trade the gamma.

## 5. Vega — the volatility exposure

**Vega = ∂V/∂σ** — change in value per **one percentage point** change in implied volatility. (Not a Greek letter; the name is conventional.)

- **Long options are always long vega**: rising IV raises the value of both calls and puts.
- **Short options are short vega.**

**Where vega is large:**
- **At the money.**
- **Longer-dated** — vega grows roughly with √T. A LEAPS is a volatility position far more than a directional one.

**Why it is the most under-appreciated Greek.** Vega explains the single most common complaint in options trading: *"the stock moved my way and I still lost money."* You were long vega into an IV collapse. The canonical case is earnings — see `volatility-and-pricing` §4 on IV crush.[^cboe-vol]

**Vega is not additive across expiries in any meaningful way.** A calendar spread can be vega-neutral in total while being materially exposed to the *term structure* changing shape. Aggregate vega by expiry bucket, not into one number.

## 6. Rho — and the one place it matters

**Rho (ρ) = ∂V/∂r** — sensitivity to the risk-free rate. Calls gain value as rates rise; puts lose.

For short-dated options rho is negligible and is routinely ignored. **It matters for LEAPS**, where the discounting of the strike over a multi-year horizon is material — and it became conspicuous again when rates moved sharply in the 2022–2024 cycle after a decade near zero. If you trade long-dated options, rho is not optional.

## 7. The sign table, and the trade-off it encodes

| Position | Delta | Gamma | Theta | Vega |
| --- | --- | --- | --- | --- |
| **Long call** | + | **+** | **−** | **+** |
| **Long put** | − | **+** | **−** | **+** |
| **Short call** | − | **−** | **+** | **−** |
| **Short put** | + | **−** | **+** | **−** |

Read the gamma, theta and vega columns and the whole subject collapses into one sentence:

> **Long options are always +gamma and +vega, and −theta for any option with meaningful extrinsic
> value. Short options are the mirror.**[^oic-greeks]
>
> The theta half carries one genuine exception, worth knowing so the table is not over-trusted: a
> **deep-ITM European put** can have **positive** theta (at S=60, K=100, r=5%, σ=25%, T=1 it gains
> about +$0.011/day), because the discounted strike accretes faster than the option's small extrinsic
> value decays. The same happens to a deep-ITM European call under a large dividend yield. Gamma and
> vega are always signed as tabulated; theta is not, quite. Of the four Greeks in that table, **delta is the only one whose sign you choose independently** — rho behaves the same way (long call +ρ, long put −ρ), but it is omitted above because it is negligible except on LEAPS (§6).

You cannot buy convexity and collect decay. Every options strategy is a position on that trade-off, and any strategy pitched as having neither drawback is being described inaccurately.

## 8. Position and portfolio Greeks

Scale each contract's Greek by **contracts × multiplier × sign**, then add:

```
position delta = Σ (contract delta × contracts × 100 × ±1)
```

A book of 10 long +0.40 calls and 5 short +0.60 calls is `(0.40×10×100) − (0.60×5×100) = 400 − 300 = +100` deltas — equivalent to 100 long shares.

Two cautions:

- **Aggregate within an underlying, never across.** Summing delta across AAPL and XOM produces a number with no meaning. Aggregate to a common risk factor only if you deliberately beta-adjust to an index.
- **Gamma and vega aggregate less honestly than delta.** Net gamma near zero can hide a large long-gamma near-dated leg against a short-gamma far-dated one — very different behaviour on a fast move. Bucket by expiry.

## 9. Delta-neutral hedging, and why it does not stay neutral

Setting position delta to zero removes **first-order** directional exposure. It does not remove risk, and it does not persist:

- **Gamma undoes it continuously.** The moment spot moves, delta is no longer zero. A long-gamma book gets longer into a rally; a short-gamma book gets shorter. Maintaining neutrality means **continuous rehedging**, which costs spread and commission each time — real money that no model prices for you.
- **A delta-neutral book is still a volatility position.** Long gamma / short theta profits if realised volatility exceeds what you paid for in implied; short gamma / long theta profits if it does not. Delta-hedging does not eliminate the bet — **it isolates it**, which is the point.
- **Discrete hedging leaves residual P&L** even in theory. Continuous rehedging is a model assumption, not something anyone does.

## 10. Second-order Greeks

Sensitivities of sensitivities. Worth knowing by name; needed when a position is large or long-dated.

- **Vanna** = ∂Δ/∂σ = ∂vega/∂S — how delta shifts as volatility changes. The Greek behind skew-driven hedging flows.
- **Charm** (delta decay) = ∂Δ/∂t — how delta drifts purely from time passing. Matters into expiry: an ATM option's delta resolves toward 0 or 1 with no spot move at all.
- **Vomma** = ∂vega/∂σ — convexity of vega. **Its sign is sign(d₁·d₂), so it is positive in the wings
  and NEGATIVE at the money** (at the money d₁ > 0 > d₂). So "long options gain disproportionately in
  a volatility spike" is true of **OTM and ITM** options and false of ATM ones — vol-of-vol convexity
  is bought in the wings. This is the opposite of what the usual "long options are long vomma"
  shorthand implies.
- **Speed** = ∂Γ/∂S and **zomma** = ∂Γ/∂σ — third-order; relevant to dealer books, not retail sizing.

## 11. Anti-patterns

1. **Reading delta as probability of profit.** Two measure errors plus the ITM-vs-profitable gap (§2). This is the most common error in the family.
2. **Treating positive theta as an edge.** Theta compensates for gamma. The edge, if any, is in mispriced volatility (`volatility-and-pricing`).
3. **Ignoring vega on a directional trade.** "Right on direction, lost money" is almost always a vega story (§5).
4. **Selling near-expiry ATM premium without sizing for gamma.** Losses accelerate rather than accumulate (§3).
5. **Netting gamma or vega across expiries into one number.** It conceals the position that actually kills you (§8).
6. **Believing delta-neutral means risk-free.** It isolates the volatility bet; it does not remove it (§9).
7. **Ignoring rho on LEAPS.** Multi-year discounting is material (§6).
8. **Forgetting weekend theta** on a short-dated long option (§4).
9. **Comparing Greeks from different sources without checking the volatility input.** They are model outputs (§1).
10. **Using Greeks to reason about a crash.** Every one of them assumes a small, single-variable, instantaneous move — precisely the assumption a dislocation breaks (§1).

## References (sources)

[^hull]: John C. Hull, *Options, Futures, and Other Derivatives* — the standard reference for the Greek definitions, the Black-Scholes N(d₁) delta vs N(d₂) risk-neutral ITM probability distinction, and the second-order Greeks. tier-2 (standard academic/practitioner text). Supports §2's two probability errors and §10. verified-as-of: 2026-08-05
[^oic-greeks]: Options Industry Council — Greeks and options-pricing educational library. https://www.optionseducation.org/ — tier-1 (authoritative industry education, OCC-sponsored). Supports the definitions, sign conventions and moneyness/expiry behaviour in §2–§7. verified-as-of: 2026-08-05
[^cboe-vol]: Cboe — options education and volatility resources, including the relationship between implied volatility and option value that underlies §5. https://www.cboe.com/education/ — tier-1 (exchange). verified-as-of: 2026-08-05
[^occ-odd-greeks]: OCC — *Characteristics and Risks of Standardized Options*, on the risks of writing uncovered options that §3's short-gamma discussion describes in Greek terms. https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document — tier-1 (regulator-mandated disclosure). verified-as-of: 2026-08-05
