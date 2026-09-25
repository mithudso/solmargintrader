---
name: volatility-and-pricing
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  What an option is worth and why — the one input nobody can observe. Implied vs
  realised volatility and the variance risk premium; IV rank vs IV percentile and
  exactly how they diverge; the volatility smile and the equity put skew that
  appeared only after October 1987; term structure, inversion, and the volatility
  surface; IV crush as the mechanism behind "right on direction, still lost";
  the VIX and its model-free variance-swap construction; Black-Scholes-Merton at
  intuition depth — its six inputs, its assumptions, and the specific ways each
  one is false; binomial lattices for American exercise; and put-call parity as
  the one relationship that needs no model at all. Educational only — NOT
  financial advice.
keywords:
  - implied volatility
  - realised volatility
  - historical volatility
  - variance risk premium
  - IV rank
  - IV percentile
  - volatility smile
  - volatility skew
  - term structure
  - volatility surface
  - IV crush
  - VIX
  - Black-Scholes
  - Black-Scholes-Merton
  - binomial model
  - Cox-Ross-Rubinstein
  - put-call parity
  - no-arbitrage
  - vega
  - earnings volatility
---

# Volatility & Pricing

Sub-reference of **`options-trading-and-strategies`**. The contract is `options-fundamentals`; the sensitivities are `the-greeks`; the combinations are `strategies-and-risk`.

> **Educational information only — NOT financial, investment, or tax advice.** Nothing here is a valuation method you should trade on. Pricing models are **descriptive frameworks built on assumptions markets violate**; the volatility premium described in §2 is a *statistical tendency*, not a reliable income stream, and the strategies that harvest it have deep left tails (see `the-greeks` §3). Options can expire worthless.

## Contents

1. The unobservable input
2. Implied vs realised, and the variance risk premium
3. IV rank vs IV percentile — and how they disagree
4. IV crush: right on direction, still lost
5. The smile, the skew, and 1987
6. Term structure, inversion, and the surface
7. The VIX
8. Black-Scholes-Merton at intuition depth
9. Binomial lattices, and why American exercise needs them
10. Put-call parity — the model-free relationship
11. Anti-patterns

## 1. The unobservable input

A pricing model takes a handful of inputs. For Black-Scholes-Merton:

| Input | Observable? |
| --- | --- |
| Spot price *S* | yes |
| Strike *K* | yes, contractual |
| Time to expiry *T* | yes, contractual |
| Risk-free rate *r* | yes, near enough |
| Dividend yield *q* | yes, forecastable |
| **Volatility σ** | **no** |

Five of six are given. **Volatility over the option's remaining life is unknowable**, because it has not happened yet. That single fact organises this whole page:

- Traders do not really trade option *prices*; they trade **views on σ**.
- Since price is observable and σ is not, the model gets **inverted**: feed in the market price, solve for the volatility that reproduces it. That is **implied volatility (IV)**.
- **IV is therefore not a forecast — it is a quote translated into volatility units.** It is what the market is charging, expressed in the only unit that makes options on different strikes and expiries comparable.

That last point is IV's real job: it is a **common denominator**. A $2.40 call and a $17.80 call cannot be compared; 24% IV and 31% IV can.

## 2. Implied vs realised, and the variance risk premium

- **Realised (historical) volatility** — measured from past returns. Typically the standard deviation of log returns, annualised by ×√252 for daily data. Backward-looking and **observable**.
- **Implied volatility** — extracted from option prices. Forward-looking and **the market's price**, not its prediction.

**The empirical regularity.** On equity indices, implied volatility has tended to exceed subsequently realised volatility, on average, over long samples. The gap is the **variance risk premium**: buyers of options are paying for insurance, and the sellers earn a premium for supplying it.[^vrp]

**Three qualifications that matter more than the regularity:**

1. **It is an average over a fat-tailed distribution.** The premium is collected in many small increments and surrendered in a few enormous ones. A strategy harvesting it has a high win rate and a left tail that can exceed the sum of the wins — this is `the-greeks` §3 in economic dress.
2. **It is not a free lunch, it is compensation for bearing a risk** that shows up precisely when everything else in a portfolio is also losing. The premium exists *because* the risk is undesirable.
3. **It varies by asset and regime,** and single-name equities behave differently from indices, especially around events (§4).

**Where this sits relative to volatility *forecasting*.** Estimating future realised volatility (EWMA, GARCH, realised-variance estimators) is a distinct exercise from reading IV, and the trade is the *difference* between your forecast and the market's price. Forecasting method → `ai-and-ml-for-trading` and `regime-detection-and-classification`; volatility-targeted position sizing → `trading-risk-management`.

## 3. IV rank vs IV percentile — and how they disagree

Absolute IV is close to meaningless across underlyings: 30% may be extreme for a utility and calm for a biotech. Both measures below normalise IV against the same underlying's own history, usually 52 weeks — and they answer **different questions**.

**IV rank** — where IV sits in its own *range*:
```
IV rank = (IV_now − IV_low) / (IV_high − IV_low)
```

**IV percentile** — the *fraction of days* IV was below where it is now:
```
IV percentile = (days with IV < IV_now) / total days
```

**They diverge sharply after a single spike, and the divergence is the informative part.** Suppose a stock traded at 20–25% IV for eleven months, spiked to 90% for three days on a rumour, and now sits at 30%:

- **IV rank** ≈ (30 − 20) / (90 − 20) = **0.14** → "IV is low."
- **IV percentile** ≈ **0.92–0.99** depending on how the decay path from 90% back to 30% is counted (≈231 of 234 named days = 0.99; over a full 252-day window with the unaccounted decay days at or above 30%, ≈0.92) → "IV is higher than on almost every day this year."

Both are correct. Rank is distorted by the outlier that set the range; percentile is not, because it counts days rather than measuring distance. **Rank answers "how far into the range?"; percentile answers "how unusual?"** Quoting one as though it were the other, in either direction, produces a confident and wrong read on whether premium is expensive.

## 4. IV crush: right on direction, still lost

The single most common losing experience in retail options, and it is a pure vega story.

**The mechanism**, using earnings as the canonical case:

1. Uncertainty about an upcoming event drives IV **up** in the days before it. Options get expensive because the *distribution* of outcomes is wide.
2. You buy a call, correctly anticipating good news.
3. The news is good. The stock rises 4%.
4. **The event has now happened.** The uncertainty it represented is gone, so IV collapses — often violently.
5. Your call's **intrinsic** value rose with the stock, but its **extrinsic** value fell further as vega worked against you. Net: a loss on a correct directional call.

**What makes it worse than it sounds:** the pre-event IV is, roughly, the market's price for the expected move. To profit from a long option through an event, the underlying must move **more than the option was priced for** — not merely in the right direction. The "expected move" implied by the straddle price is the bar, and being right about direction clears no part of it.

**Structural implications:**
- Long premium into a scheduled event is a bet on **magnitude exceeding the priced magnitude**, not on direction.
- Short premium into an event collects the crush — and carries the gap risk that the crush is compensation for.
- Calendar spreads can be a way to express a view on IV *term structure* around events rather than on direction (`strategies-and-risk` §7).

## 5. The smile, the skew, and 1987

Black-Scholes assumes **one** volatility for an underlying. Invert real market prices strike by strike and you get **different IVs at different strikes** — the assumption is visibly false, and the shape of its falseness is informative.

- **Smile** — IV higher at both wings than at the money. Common in FX.
- **Skew (equity)** — IV **higher for downside strikes** than upside. The characteristic shape for equity indices, sometimes called a smirk.

**The historical fact worth carrying:** the pronounced equity put skew is **not a permanent feature of markets — it appeared after the October 1987 crash.** Studies of pre- and post-crash S&P index option prices find a comparatively flat pattern before, and persistent negative skew after.[^rubinstein] Markets learned that a 20%+ single-day drop was possible and permanently repriced downside protection.

**What the skew tells you:**
- **Crash risk is priced.** Downside protection costs more per unit of volatility than upside speculation.
- Buying an OTM put is buying the *most expensive* volatility on the surface; selling one is selling it. Neither is a mispricing — it is the market's price for a real asymmetry.
- **Vertical spreads inherit the skew.** A put spread's cost is set by the *relative* IV of two strikes, so skew is not incidental to the structure — it is a determinant of its price.

## 6. Term structure, inversion, and the surface

Hold strike fixed and vary expiry, and IV changes again — the **term structure**.

- **Normal (upward-sloping)** in calm markets: longer-dated IV exceeds near-dated, reflecting greater uncertainty over longer horizons and volatility's tendency to mean-revert *upward* from low levels.
- **Inverted (downward-sloping)** in stress: near-dated IV spikes above longer-dated. The market is saying *the danger is now*, and expects it to subside. Inversion is one of the more reliable observable markers of acute stress.

Together, strike × expiry gives the **volatility surface** — the full IV(K, T) map. A dealer risk-manages the surface, not a number, and the second-order Greeks in `the-greeks` §10 are largely about how the surface moves.

**Practical reading:** a calendar or diagonal spread is a position on the *term structure*, and can be profitable or not entirely independently of direction (`strategies-and-risk` §9).

## 7. The VIX

The **Cboe Volatility Index** measures the market's expected volatility of the S&P 500 over the **next 30 days**, in annualised percentage points, computed from **SPX option prices**.[^vix-wp]

Four properties that are routinely misstated:

1. **It is model-free.** Since the 2003 methodology, VIX is computed by **variance-swap-style replication** — a weighted integral across a strip of OTM SPX puts and calls — *not* by inverting Black-Scholes. The original 1993 index did use ATM Black-Scholes implied vols on OEX; material describing VIX that way is describing the pre-2003 index.[^vix-wp]
2. **It is forward-looking but not a forecast.** Like any IV, it is a price. It routinely exceeds subsequent realised volatility (§2).
3. **It is not directly tradeable.** You cannot buy the index. Exposure comes via **VIX futures**, options on them, or ETPs built on futures — all of which carry the term structure. Because VIX futures are in contango most of the time, long-volatility ETPs bleed on the roll; this is the `derivatives-futures-and-swaps` §7 roll-yield problem in its most extreme form, and it is why long-VIX products are poor buy-and-hold instruments even when the volatility view is right.
4. **"Fear gauge" is a loose label.** VIX rises with *expected movement*, and because of the put skew (§5) it is dominated by demand for downside protection — so it correlates with fear, but it is measuring price, not sentiment.

## 8. Black-Scholes-Merton at intuition depth

The 1973 Black-Scholes model, with Merton's extensions, is the field's common language. Presented here as intuition — the derivation is out of scope for a retail educational reference.

**The core idea.** A continuously rebalanced portfolio of the underlying and cash can replicate an option's payoff. If replication is possible, then **by no-arbitrage the option must cost what the replicating portfolio costs** — and, strikingly, that cost does not depend on the underlying's expected return, only on its volatility. That is the insight: **risk-neutral valuation**.

**The six inputs:** spot, strike, time, risk-free rate, dividend yield, volatility (§1).[^bs-crr]

**The assumptions, and how each is false:**

| Assumption | Reality |
| --- | --- |
| Returns are lognormal (GBM), continuous paths | Returns have **fat tails** and **jumps**; gaps happen overnight and on news |
| Volatility is **constant** | Volatility is stochastic, clusters, and mean-reverts — and the smile (§5) is the market pricing exactly this |
| Continuous, costless trading; no transaction costs | Spreads, commissions and discrete rebalancing are material (`the-greeks` §9) |
| Constant known risk-free rate | Rates move; matters for LEAPS |
| **European** exercise | US equity options are **American** (§9) |
| Unlimited borrowing/lending at *r*, freely shortable | Financing is not symmetric; borrow can be constrained or expensive |

**Why it is still used despite all of that.** Not as a truth claim but as a **coordinate transform**. Its most valuable output is not a price but **implied volatility** — the device that makes heterogeneous contracts comparable (§1). The market quotes in IV *because of* the model, then prices a smile that contradicts the model's central assumption. Both things are true at once, and that is the honest state of affairs.

## 9. Binomial lattices, and why American exercise needs them

Black-Scholes prices a **European** option — exercisable only at expiry. US equity and ETF options are **American**, and early exercise can be optimal (`options-fundamentals` §7). Closed-form BSM cannot represent that decision.

The **binomial model** (Cox-Ross-Rubinstein, 1979) discretises time into steps where the underlying moves up or down, then values the option by **backward induction** from expiry. At every node it takes:

```
value = max(intrinsic value now, discounted expected value of holding)
```

That `max` **is** the early-exercise decision, evaluated at every node — which is precisely what a closed form cannot do. Refine the step count and the European case converges to Black-Scholes; the American case converges to
something **higher or equal**, and the difference is the **early-exercise premium**.

**"Or equal" is not a hedge — it is the most useful special case.** An **American call on a
non-dividend-paying stock is worth exactly its European value**: early exercise is never optimal, so
the premium is identically zero. Exercising such a call early forfeits its remaining extrinsic value
for nothing. Strict inequality needs either a **put with r > 0**, or a **call with a dividend large
enough** to beat the extrinsic value given up (`options-fundamentals` §7).

Practical relevance: it is why American options on dividend-paying stocks are not simply BSM values, and why an accurate model must know the dividend calendar.

## 10. Put-call parity — the model-free relationship

For European options on the same underlying, strike and expiry:

```
C − P = S − K·e^(−rT)
```

With discrete dividends, subtract their present value from *S*.

**Why this is the most trustworthy statement on this page:** parity follows from **arbitrage alone**.[^oic-pricing] No volatility, no distributional assumption, no model. A long call plus a short put replicates a forward on the stock; if the equality breaks by more than transaction costs, there is a riskless profit, so it does not break.

Uses:
- **Sanity-check quotes.** A violation usually means stale data, a missed dividend, hard-to-borrow financing, or an early-exercise premium — not free money.
- **Synthetic positions.** Long call + short put ≈ long stock; the identity is what makes synthetics and conversions/reversals work.
- **Skew is not a parity violation.** Calls and puts at the *same* strike share one IV under parity. The skew is across **different strikes**, which parity says nothing about. Confusing these two is common.

For **American** options parity relaxes into inequalities, because early exercise has value.

## 11. Anti-patterns

1. **Reading IV as a forecast.** It is a price, and on average it exceeds subsequent realised volatility (§2).
2. **Treating the variance risk premium as income.** It is compensation for a fat left tail that arrives with everything else going wrong (§2).
3. **Quoting IV rank when you mean IV percentile.** After one spike they can say opposite things (§3).
4. **Buying premium into earnings on a directional view.** You need the move to exceed the *priced* move, not merely to go your way (§4).
5. **Comparing raw IV across underlyings.** 30% is not a level; normalise (§3).
6. **Assuming one volatility per underlying.** The smile and term structure are the market's statement that this is false (§5, §6).
7. **Holding a long-VIX ETP as a volatility view.** Contango roll drag will beat you (§7).
8. **Describing VIX as an average of Black-Scholes implied vols.** That was the pre-2003 index (§7).
9. **Using European BSM on American options over a dividend.** Early exercise has value that the closed form cannot express (§9).
10. **Calling the skew an arbitrage.** Parity constrains one strike's call against its own put, not one strike against another (§10).

## References (sources)

[^vrp]: Peter Carr & Liuren Wu, "Variance Risk Premiums," *Review of Financial Studies* 22(3), 2009; Gurdip Bakshi & Nikunj Kapadia, "Delta-Hedged Gains and the Negative Market Volatility Risk Premium," *RFS* 16(2), 2003; Tim Bollerslev, George Tauchen & Hao Zhou, "Expected Stock Returns and Variance Risk Premia," *RFS* 22(11), 2009. tier-2 (peer-reviewed). These measure the IV-minus-subsequent-realised gap directly, which is what §2 claims. **Deliberately not cited to Cboe's BXM/PUT benchmarks** — those are buy-write/put-write *return* series, not measurements of the variance premium, and using them here would be a citation that does not support its sentence. The premium is a documented historical average, not a guarantee. verified-as-of: 2026-08-05
[^rubinstein]: Mark Rubinstein, "Implied Binomial Trees," *Journal of Finance* 49(3), 1994, pp. 771–818; see also Jackwerth & Rubinstein, "Recovering Probability Distributions from Option Prices," *J. Finance* 51(5), 1996, as the stronger companion cite — documents the emergence of persistent negative skew in S&P index option implied volatilities after the October 1987 crash, against a comparatively flat pre-crash pattern. tier-2 (peer-reviewed). Supports §5's historical claim. verified-as-of: 2026-08-05
[^vix-wp]: Cboe — *VIX White Paper: Cboe Volatility Index* (the model-free variance-replication methodology adopted in 2003; the 30-day SPX construction; the contrast with the original 1993 OEX/Black-Scholes index). https://www.cboe.com/tradable_products/vix/ — tier-1 (exchange, methodology owner). Supports all four points in §7. verified-as-of: 2026-08-05
[^bs-crr]: Fischer Black & Myron Scholes, "The Pricing of Options and Corporate Liabilities," *JPE* 81(3), 1973; Robert C. Merton, "Theory of Rational Option Pricing," *Bell J. Econ.* 4(1), 1973; John Cox, Stephen Ross & Mark Rubinstein, "Option Pricing: A Simplified Approach," *JFE* 7(3), 1979. tier-2 (foundational peer-reviewed). Supports §8's inputs and assumptions and §9's backward-induction treatment of American exercise. verified-as-of: 2026-08-05
[^oic-pricing]: Options Industry Council — options pricing, implied volatility and put-call parity educational library. https://www.optionseducation.org/ — tier-1 (authoritative industry education, OCC-sponsored). Supports §1, §3 and §10. verified-as-of: 2026-08-05
