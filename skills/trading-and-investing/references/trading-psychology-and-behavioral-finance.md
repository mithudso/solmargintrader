---
name: trading-psychology-and-behavioral-finance
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-05"
verified-as-of: "2026-08-05"
category: reference
description: >-
  The documented biases and what actually mitigates them. Prospect theory and
  loss aversion; the disposition effect (selling winners, holding losers) with the
  Odean 1998 measurement; overconfidence and the Barber-Odean turnover results
  including the gender study; attention-driven trading; mental accounting, the
  house-money effect, anchoring, recency, confirmation, hindsight, sunk cost,
  gambler's fallacy and herding — each with its observable signature at the
  account level rather than as a vocabulary list. Then the honest half: awareness
  does not fix bias, so the remedies that work are STRUCTURAL (pre-commitment,
  written invalidation criteria, position limits, automation) and the reporting
  choices that manufacture bias — with this family's measured closed-trade
  illusion as the worked example. Educational only — NOT financial advice.
keywords:
  - trading psychology
  - behavioral finance
  - prospect theory
  - loss aversion
  - disposition effect
  - overconfidence
  - turnover
  - attention
  - mental accounting
  - house money effect
  - anchoring
  - recency bias
  - confirmation bias
  - hindsight bias
  - sunk cost
  - gambler's fallacy
  - herding
  - revenge trading
  - tilt
  - pre-commitment
  - trading journal
  - checklist
  - bias blind spot
---

# Trading Psychology & Behavioral Finance (spoke)

A spoke of the **`trading-and-investing`** hub. `investing-vs-trading` carries the headline evidence that most active retail traders underperform; **this page is about the mechanisms that produce that result**, and about which countermeasures have any support.

> **Educational information only — NOT financial, investment, or psychological advice.** Two honest cautions specific to this topic. First, **knowing a bias does not remove it** — the *bias blind spot* is itself documented, and reading a list of biases reliably makes people better at spotting them in others rather than in themselves. Everything in §12 is structural for that reason. Second, if trading is causing genuine distress, or shows the pattern of a behavioural addiction — chasing losses, concealing activity, trading money you need — that is outside the scope of a trading reference and worth taking to a professional.

## Contents

1. Why this is not a vocabulary list
2. Prospect theory and loss aversion
3. The disposition effect
4. Overconfidence and turnover
5. Attention, and what gets traded
6. Mental accounting and the house-money effect
7. Anchoring, recency, and availability
8. Confirmation and hindsight
9. Sunk cost, and the gambler's fallacy
10. Herding
11. Tilt: revenge trading and the loss spiral
12. What actually works: structure, not willpower
13. Reporting choices that manufacture bias
14. Anti-patterns

## 1. Why this is not a vocabulary list

Naming biases is cheap and nearly useless. What makes a bias actionable is its **observable signature in your own records** — a pattern you can detect after the fact and pre-commit against before it recurs. So each entry below states the signature, not just the name.

The underlying reason any of this matters: markets are the one domain where being wrong is expensive, feedback is noisy and delayed, and randomness is dense enough that **a bad process can produce good outcomes for a long time**. That combination is close to optimal for forming and then reinforcing false beliefs.

## 2. Prospect theory and loss aversion

Kahneman and Tversky's **prospect theory** (1979) replaced the assumption that people evaluate absolute wealth with three findings:[^kt79]

1. **Outcomes are evaluated as gains and losses relative to a reference point**, not as final wealth levels. The reference point is usually the purchase price — which has no economic significance whatever.
2. **Loss aversion** — losses hurt more than equivalent gains please, commonly estimated around **2:1**.
3. **Diminishing sensitivity** — the value function is concave in gains and **convex in losses**, so people become *risk-seeking* when facing losses. This is the piece that matters most for traders.

**The direct trading consequence:** at a loss, the convex region makes the gamble ("hold on, maybe it comes back") feel preferable to the certain small loss of closing. That is not weakness; it is the shape of the value function, and it is why §3 happens.

## 3. The disposition effect

**The tendency to sell winners too early and hold losers too long** (Shefrin & Statman, 1985). Odean measured it in 10,000 discount-brokerage accounts and found investors sold winners at a **significantly higher rate** than losers — and, in the sharpest part of the result, **the winners they sold went on to outperform the losers they kept**.[^odean98]

**Signature in your records:** average holding period of winners materially shorter than losers; realised gains small and frequent, realised losses large and rare; a tail of long-held positions all underwater.

**Why it is expensive twice.** Economically it truncates the right tail — a trend-following edge cannot exist if winners are cut early. And in a taxable account it is **backwards for tax**: it realises gains (taxable) and defers losses (deductible), the opposite of tax-loss harvesting (`trading-regulation-compliance-and-taxes` §6–§7).

**The reference-point insight:** your entry price is known only to you and has no bearing on the asset's future distribution. "I'll sell when it gets back to break-even" is a statement about your own history.

## 4. Overconfidence and turnover

The most robustly documented finding in retail trading, and it is a finding about **turnover**.

Barber & Odean, "Trading Is Hazardous to Your Wealth" (2000): across 66,465 households, those trading **most actively** earned annual net returns substantially below the market, while average households did modestly less badly. **Gross** returns were roughly similar — so the underperformance is largely **trading costs plus poor selection**, not bad luck.[^bo2000]

"Boys Will Be Boys" (2001) added the mechanism test: if overconfidence causes excess trading, groups measured as more overconfident should trade more and lose more. Men traded about **45% more** than women and underperformed them by roughly a further percentage point annually.[^bo2001]

**The honest reading:** the finding is not "men trade badly". It is that **turnover is the mediating variable**, and overconfidence is what drives turnover. Any strategy whose edge must overcome high turnover is fighting the best-documented result in the field.

**Signature:** trade count rising after a winning streak; position sizes rising after wins; conviction language in your notes increasing while your hit rate does not.

## 5. Attention, and what gets traded

Barber & Odean, "All That Glitters" (2008): individual investors are **net buyers of attention-grabbing stocks** — those in the news, with abnormal volume, or with extreme one-day returns.[^bo2008]

**The structural reason:** buying requires choosing from thousands of candidates, and attention prunes that set. Selling, for someone who does not short, is a choice among the few things already owned. **Attention therefore biases the buy side specifically**, which is why "what am I not seeing?" is a more useful question than "is this a good buy?"

**Signature:** entries clustering after news, unusual volume, or a large single-day move; a watchlist that is really a list of things that were recently loud.

## 6. Mental accounting and the house-money effect

**Mental accounting** (Thaler) — treating money differently by which bucket it sits in, though money is fungible. "Playing with profits" is the canonical trading version.

**House-money effect** (Thaler & Johnson, 1990) — increased risk-taking with money recently won.[^tj90] After a gain, the next stake feels free, so size creeps up. Combined with §4's post-winning-streak turnover, this is how an account gives back a good run: **the largest position arrives at the moment of greatest confidence and least justification.**

**Signature:** position size correlated with recent P&L rather than with volatility or conviction. The remedy is mechanical — size from a rule, not a feeling (`trading-risk-management`).

## 7. Anchoring, recency, and availability

- **Anchoring** — over-weighting a salient number. Entry price, an all-time high, a round number, an analyst target. The anchor's power comes from being *available*, not from being *informative*.
- **Recency** — over-weighting recent observations. It is why volatility feels permanent during a drawdown and impossible during a calm stretch, and why regime-conditioned strategies get adopted at the end of the regime that favoured them.
- **Availability** — judging probability by how easily an example comes to mind. A vivid crash story distorts the probability more than a table of frequencies.

**Signature:** targets and stops sitting on round numbers or on your own entry; a strategy adopted right after its best stretch.

**This is also a data problem, not only a psychological one.** The measured version of recency in this family: `walk-forward-window-length-and-refit-cadence` found **monthly refitting sub-optimal at 7 of 7 window lengths** — refitting frequently is recency implemented in code, and the data disagreed with it.

## 8. Confirmation and hindsight

**Confirmation bias** — seeking and privileging evidence for what you already believe. In trading this is nearly frictionless: for any position there is a community, a chart interval, and an indicator that agrees with you.

**Hindsight bias** — after an outcome, believing it was predictable. This is the one that **corrupts learning specifically**, because it converts "I got a good outcome from a bad decision" into "I made a good decision." A journal written *after* the outcome records the bias rather than the reasoning.

**The countermeasure that follows directly:** write the **invalidation criterion before entering** — what observation would tell you this thesis is wrong. It is falsifiable in advance and cannot be rewritten by the outcome. Everything in this family about pre-registering a protocol is the same idea applied to research (`signal-backtest-protocol-and-regime-evidence`).

## 9. Sunk cost, and the gambler's fallacy

**Sunk cost** — letting money already spent justify further commitment. "I'm too deep to stop now." Only the *forward* distribution matters; what you have lost is information about the past.

**Averaging down** is the sunk-cost fallacy with a spreadsheet: it lowers your average entry, which lowers your *reference point*, which feels like progress while **increasing** exposure to the thing that is already going against you. It can be a legitimate pre-planned scale-in. It is only legitimate if it was planned before the loss.

**Gambler's fallacy** — expecting a reversal because of a run ("five reds, black is due"). Its inverse, the **hot-hand** belief, expects continuation. Both are pattern-detection applied to a process with far less structure than it appears to have. Note the two are contradictory, and people hold whichever supports the position they have.

## 10. Herding

Following the crowd, which is not always irrational — the crowd sometimes has information. It becomes dangerous when:

- **The crowd is the only evidence.** "Everyone is long" is a positioning fact, not a thesis.
- **Crowding creates the risk.** A crowded trade is one where many holders will need the same exit simultaneously, which is what makes liquidations cascade. In this family's own domain: `jlp-risk-profile-and-anti-patterns` records net open interest running **85–90% long** on Jupiter Perps, making the LP structurally short leverage into rallies. Crowding is measurable, and it is a risk factor rather than a sentiment.
- **Social feedback replaces P&L as the reward.** Posting a thesis creates a commitment to defend it, which converts §8's confirmation bias into a public obligation.

## 11. Tilt: revenge trading and the loss spiral

The acute failure mode, and the one that empties accounts fastest. The sequence is consistent enough to be worth memorising:

1. A loss, often larger than planned.
2. **Prospect theory's convex loss region** (§2) makes a recovery gamble feel rational.
3. Size increases — to "make it back in one trade".
4. The time horizon collapses; process is abandoned because process is slow.
5. Losses compound, and each one intensifies steps 2–4.

**This is not a character flaw, it is a predictable state**, which is why the remedy is a pre-committed circuit breaker rather than resolve: a daily loss limit that ends the session automatically, decided when calm and not negotiable while trading. `trading-risk-management` owns the sizing side.

**Signature:** largest position sizes and shortest holding periods immediately following the largest losses.

## 12. What actually works: structure, not willpower

The evidence for "learn the biases and avoid them" is weak — the **bias blind spot** means education mostly improves detection in others. What has support is **removing the decision from the moment**:

- **A written plan, before the trade** — entry, exit, size, and the **invalidation criterion** (§8). Written in advance, it cannot be rewritten by the outcome.
- **Pre-committed limits** — risk per trade, portfolio heat, a daily stop that ends the session. Set when calm; the entire point is that they bind when you disagree with them.
- **Automation** — code executes the plan without a reference point or a losing streak. This is much of the honest case for systematic trading, and it introduces its own failure modes: `trading-bot-infrastructure-and-monitoring` on monitoring **equity rather than trades**, and alerting on absence.
- **A journal written at entry, not exit** — recording the reasoning and the invalidation criterion *before* the outcome is known. A post-hoc journal records hindsight bias.
- **Checklists** — mechanical, and effective precisely because they do not depend on judgement being available.
- **Reduce turnover** — the single change with the strongest direct evidence behind it (§4).
- **Measure the process, not the outcome.** Over short samples outcome is dominated by noise; adherence is observable immediately and is the only thing you control.

## 13. Reporting choices that manufacture bias

The underrated point, and the reason this page sits in a research family: **how you report results can create a bias that no amount of discipline will overcome, because the number you are looking at is the wrong one.**

This family's measured example is exact. `grid-trading-strategy` documents a bear month in which the strategy's **closed-trade log showed +$95 at a 100% win rate while the account fell 37.5%** — because closed trades exclude the open inventory the grid accumulated against the trend. Every psychological mechanism above then operates on the flattering number: confirmation finds support, overconfidence raises size, and the disposition effect is invisible because losers were never closed.

**The general rule:** a reporting convention that systematically omits open positions, unrealised losses, or costs will produce confident wrong beliefs in a disciplined person. **Fix the report before working on the mindset.** Equity-curve reporting, gross-versus-net, and cost attribution → `onchain-pnl-and-tax-accounting` and `empirical-backtest-findings-log`.

## 14. Anti-patterns

1. **Using your entry price as a reference point.** It has no bearing on the forward distribution (§2, §3).
2. **"I'll sell when it gets back to break-even."** A statement about your history, not the asset (§3).
3. **Increasing size after wins.** House money plus overconfidence, arriving together (§4, §6).
4. **Buying what is in the news.** Attention biases the buy side specifically (§5).
5. **Averaging down without having planned it.** Sunk cost with a spreadsheet (§9).
6. **Writing the journal after the outcome.** That records hindsight bias, not reasoning (§8).
7. **Entering without an invalidation criterion.** Then no evidence can ever falsify the thesis (§8).
8. **Trading after a large loss without a circuit breaker.** The tilt sequence is predictable (§11).
9. **Adopting a strategy right after its best stretch.** Recency, and the data disagrees with frequent refitting (§7).
10. **Treating "everyone is long" as a thesis.** It is a positioning fact and a crowding risk (§10).
11. **Posting a thesis publicly and then defending it.** Confirmation bias with a social obligation (§10).
12. **Reading this page and considering the problem addressed.** The bias blind spot means education mostly helps you diagnose others; §12 is structural for that reason.
13. **Working on mindset while the report is wrong.** A closed-trade log showed +$95 at 100% win rate in a month the account fell 37.5% (§13).

## References (sources)

[^kt79]: Daniel Kahneman & Amos Tversky, "Prospect Theory: An Analysis of Decision under Risk," *Econometrica* 47(2), 1979 — the reference-point framing, loss aversion, and the concave-in-gains/convex-in-losses value function that §2 and §11 rest on. tier-2 (peer-reviewed, foundational; Nobel-recognised). verified-as-of: 2026-08-05
[^odean98]: Terrance Odean, "Are Investors Reluctant to Realize Their Losses?", *Journal of Finance* 53(5), 1998 — measures the disposition effect in ~10,000 discount-brokerage accounts, and finds the winners sold subsequently outperformed the losers retained. Hersh Shefrin & Meir Statman, "The Disposition to Sell Winners Too Early and Ride Losers Too Long," *J. Finance* 40(3), 1985, named the effect. tier-2 (peer-reviewed). Supports §3. verified-as-of: 2026-08-05
[^bo2000]: Brad Barber & Terrance Odean, "Trading Is Hazardous to Your Wealth: The Common Stock Investment Performance of Individual Investors," *Journal of Finance* 55(2), 2000 — 66,465 households; the most active traders substantially underperformed while gross returns were similar, locating the loss in costs and selection rather than luck. tier-2 (peer-reviewed). Supports §4. verified-as-of: 2026-08-05
[^bo2001]: Brad Barber & Terrance Odean, "Boys Will Be Boys: Gender, Overconfidence, and Common Stock Investment," *Quarterly Journal of Economics* 116(1), 2001 — men traded ~45% more and underperformed by roughly a further percentage point annually; the study's purpose is to test **turnover as the mediating variable**, which is how §4 presents it. tier-2 (peer-reviewed). verified-as-of: 2026-08-05
[^bo2008]: Brad Barber & Terrance Odean, "All That Glitters: The Effect of Attention and News on the Buying Behavior of Individual and Institutional Investors," *Review of Financial Studies* 21(2), 2008 — individual investors are net buyers of attention-grabbing stocks, with the buy/sell asymmetry §5 describes. tier-2 (peer-reviewed). verified-as-of: 2026-08-05
[^tj90]: Richard Thaler & Eric Johnson, "Gambling with the House Money and Trying to Break Even: The Effects of Prior Outcomes on Risky Choice," *Management Science* 36(6), 1990 — the house-money effect and the break-even effect. tier-2 (peer-reviewed). Supports §6 and §11. verified-as-of: 2026-08-05
[^finra-behav]: FINRA Investor Education Foundation — research on investor behaviour, overconfidence and risk-taking; SEC / Investor.gov investor bulletins on emotional decision-making. https://www.finrafoundation.org/ and https://www.investor.gov/ — tier-1 (SRO foundation / regulator). Supports §12's emphasis on written plans and pre-commitment. verified-as-of: 2026-08-05
