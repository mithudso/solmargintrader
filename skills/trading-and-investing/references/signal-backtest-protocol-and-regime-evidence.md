---
name: signal-backtest-protocol-and-regime-evidence
# provenance: split from indicator-signal-implementation-and-backtesting 2026-08-04
# (that file reached ~21.7k tokens; §5-§6 moved here verbatim, section numbers preserved).
# `name:` must sit immediately after the opening fence: persist-spoke.mjs anchors
# on /^---\nname:/ and reports "no YAML frontmatter found" if a comment precedes it.
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  SPOKE of trading-and-investing — how to backtest ONE price-derived signal
  without lying to yourself, and the cited empirical record of when each signal
  family has actually worked. Educational ONLY, NOT financial advice; most edges
  fail after costs and data-snooping correction (2026). TRIGGER: designing a
  single-signal backtest (anchored vs rolling walk-forward, purging, embargo,
  overlapping labels); cost model and break-even cost in bps; the metric set
  (Sharpe, Sortino, Calmar, PSR/DSR, MinTRL); mandatory multiple-testing
  correction (White Reality Check, Hansen SPA, FDR, PBO, Deflated Sharpe); "my
  backtest looks too good"; which indicator families fail by regime, asset class
  or era (BLL 1992 vs Sullivan-Timmermann-White 1999 vs Bajgrowicz-Scaillet 2012,
  decay evidence, TSMOM smile and its challenger, momentum crashes, crypto's
  four contested results). SKIP: implementing the indicator itself (substrate,
  trend, momentum, volatility — §1-§4) →
  indicator-signal-implementation-and-backtesting; pairing/redundancy (§7) and
  the volume, candlestick, chart-pattern and price-action sets (§8-§10) →
  signal-pairing-volume-and-pattern-signal-sets; window length and refit cadence as fitted
  parameters → walk-forward-window-length-and-refit-cadence; this hub's own
  measured runs → empirical-backtest-findings-log; live regime classification →
  regime-detection-and-classification.
keywords:
  - signal-backtest-protocol
  - walk-forward
  - purged-cross-validation
  - embargo
  - break-even-cost
  - deflated-sharpe-ratio
  - reality-check
  - data-snooping
  - regime-performance
  - technical-analysis-evidence
  - momentum-crashes
  - decay
tags:
  - trading-and-investing
  - backtesting
  - validation
  - quant
  - technical-analysis
whenToUse:
  - When designing a backtest for a single signal and needing split design, a cost model, metrics and a multiple-testing correction.
  - When a backtest result looks too good and you need the correction that most often kills it.
  - When asking under what market conditions a signal family has historically worked or failed, with citations.
  - When you need the break-even cost in bps rather than a net return at one cost assumption.
---

# Signal Backtest Protocol and Regime Evidence

> **Educational information only — NOT financial, investment, or tax advice.**

**What this is.** Sections 5 and 6 of
`references/indicator-signal-implementation-and-backtesting.md`, split out on
2026-08-04 when that file passed the reference size ceiling. §5 is the protocol
for testing one signal; §6 is the cited record of what such testing has found.
**Section numbers are preserved** (§5.x, §6.x), so every cross-reference to them
elsewhere in this family still resolves.

**Scope.**

| For… | Go to |
|---|---|
| The signal implementations this protocol tests — substrate, trend/MA, momentum, volatility (§1-§4) | `references/indicator-signal-implementation-and-backtesting.md` |
| Pairing, independence and redundancy (§7), and the volume/breadth, candlestick, chart-pattern and price-action sets (§8-§10) | `references/signal-pairing-volume-and-pattern-signal-sets.md` |
| Walk-forward window length and refit cadence as fitted parameters | `references/walk-forward-window-length-and-refit-cadence.md` |
| This hub's own measured backtest runs, including the falsified claims | `references/empirical-backtest-findings-log.md` |
| Whether a result generalises to another asset | `references/cross-asset-generalisation-testing.md` |
| Regime detection as a live mechanism rather than a historical record | `references/regime-detection-and-classification.md` |
| TA meta-evidence at the discipline level | `references/technical-analysis.md` |

## Contents

5. Per-signal backtest recipe
6. Regime-performance evidence

## 5. Per-signal backtest recipe

A protocol you can run per signal. The ordering is deliberate: the cheap
disqualifiers come first, so you stop before spending effort on a signal that
cannot survive costs.

### 5.1 Step 0 — audit before you measure

Run §1's three checks first. A backtest with one bar of leakage is not a weak
backtest, it is not a backtest (§1.3: +3.8 Sharpe from leakage alone). Confirm:
positions shifted, burn-in discarded, smoothing convention verified, no
repainting indicator.

### 5.2 Sample-size requirements

Count **independent trades**, not bars. A signal on 20 years of daily data that
trades four times a year has ~80 observations, which is a small sample regardless
of the 5,000 bars underneath it.

- Aim for **at least ~100 independent trades** before treating a per-trade
  statistic as meaningful, and expect wide confidence intervals below ~30.
- The standard error of a Sharpe estimate is roughly `sqrt((1 + SR²/2)/T)` for
  T periods, so short samples cannot distinguish a 0.5 Sharpe from zero. Bailey
  and López de Prado formalise this as the **Minimum Track Record Length** — the
  observation count needed for a given confidence at a given SR.[^bt-1]
- Overlapping windows inflate the effective sample. Ten trades held 30 days each
  inside a 60-day span are not ten independent observations.

### 5.3 Split design: walk-forward, purging, embargo

Standard k-fold cross-validation **leaks** on time series: a fold's training data
can sit chronologically after its test data, and label windows straddle the
boundary. Use instead:

- **Anchored walk-forward** — train on `[0, t]`, test on `(t, t+h]`, advance,
  always retraining from the start. Uses all history; adapts slowly.
- **Rolling walk-forward** — fixed-width training window that slides. Adapts to
  regime change; discards old data.
- **Purging** — drop training observations whose label window overlaps the test
  window. Without it, a 20-day-horizon label leaks 20 days across the boundary.
- **Embargo** — additionally drop a gap of observations immediately after the
  test window before resuming training, to break serial correlation that purging
  alone leaves.[^bt-2]

```python
def walk_forward_splits(n, train, test, anchored=True, embargo=0):
    """Yield (train_idx, test_idx) index arrays with an optional embargo gap.

    Purging for a label horizon h: also drop the last h observations of each
    training block, since their labels extend into the test block.
    """
    start = 0
    while start + train + test <= n:
        tr_lo = 0 if anchored else start
        tr_hi = start + train                 # exclusive
        te_lo = tr_hi + embargo
        te_hi = te_lo + test
        if te_hi > n:
            break
        yield list(range(tr_lo, tr_hi)), list(range(te_lo, te_hi))
        start += test                         # non-overlapping test blocks
```

### 5.4 Cost model — the step that kills most signals

Model costs explicitly per round trip; do not apply a single annual haircut.

| Component | Treatment |
|---|---|
| Commission | Per-share/per-contract/per-trade as your broker actually bills |
| Spread | Half the quoted bid-ask per side for a market order; a limit order pays zero spread but incurs non-fill risk you must also model |
| Slippage | Fixed bps for liquid instruments; a volume-participation model where your order is material relative to bar volume |
| Financing | Borrow cost for shorts, margin interest, futures roll |

Two calibration anchors from the literature: STW put the DJIA break-even at
**0.27% per trade**, and Bajgrowicz & Scaillet found in-sample technical
performance **completely offset by low transaction costs** (§6.1).[^regime-2][^regime-3]

**Report break-even cost, not just net return.** "This signal survives up to 18
bps round-trip" is a falsifiable claim a reader can check against their own
broker; "returns 12% net" hides the assumption.

```python
def apply_costs(positions, ret, cost_bps_round_trip=10.0):
    """positions in {-1,0,1}; charge on position CHANGE, not on holding."""
    turnover = positions.diff().abs().fillna(0) / 2.0   # 1.0 = full round trip
    return positions.shift(1) * ret - turnover * (cost_bps_round_trip / 10_000.0)

def break_even_cost_bps(positions, ret, lo=0.0, hi=500.0, tol=0.01):
    """Round-trip cost in bps at which net mean return reaches zero."""
    f = lambda c: apply_costs(positions, ret, c).mean()
    if f(lo) <= 0:
        return 0.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    return (lo + hi) / 2
```

### 5.5 Metrics

Report all of these; any one alone is gameable.

- **CAGR** and **volatility**; **Sharpe** = mean/σ annualised. Sharpe assumes
  roughly normal, i.i.d. returns — both false for trend and option-like payoffs,
  so pair it with skew and kurtosis.
- **Sortino** (downside σ), **max drawdown**, **Calmar** (CAGR ÷ max DD),
  **time-in-drawdown**.
- **Hit rate together with payoff ratio.** Neither means anything alone: a 30%
  hit rate with 4:1 payoff and a 70% hit rate with 1:3 payoff can share an
  expectancy. Report **expectancy** = `hit·avg_win − (1−hit)·avg_loss`.
- **Turnover** and **average holding period** — these determine cost sensitivity
  (§5.4) and whether your sample is really independent (§5.2).
- **Exposure**. A signal in the market 20% of the time is not comparable to
  buy-and-hold at face value; compare exposure-matched or per-unit-risk.

### 5.6 Multiple testing — mandatory, not optional

If you tried more than one variant, your best result is a maximum over trials and
its nominal p-value is wrong. This is the single most consequential correction in
the whole literature: STW's best S&P futures rule went from nominal **p = 0.042**
to Reality-Check **p = 0.908** once the 7,846-rule search was accounted for
(§6.1).[^regime-2]

- **White's Reality Check** — bootstrap the null that the best of N rules has no
  superior performance over the benchmark.[^bt-3]
- **Hansen's SPA test** — a refinement with better power, less sensitive to poor
  and irrelevant alternatives.[^bt-4]
- **False discovery rate** — control the expected proportion of false positives
  among selected rules; the approach Bajgrowicz & Scaillet used (and the one
  routinely mislabeled as SPA).[^regime-3]
- **Probability of Backtest Overfitting (PBO)** via **CSCV** — combinatorially
  split the performance series and estimate how often the in-sample best
  underperforms the out-of-sample median.[^bt-5]
- **Deflated Sharpe Ratio** — corrects the Sharpe for both selection bias across
  N trials and non-normality (skew/kurtosis), asking whether the *selected best*
  Sharpe is genuinely positive.[^bt-1]

**Formula caveat, stated rather than papered over.** The DSR is built from the
Probabilistic Sharpe Ratio evaluated against a deflated benchmark `SR*`
representing the expected maximum Sharpe across N trials, and it requires: N
(trial count), the variance of Sharpe ratios across those trials, sample length
T, and return skewness and kurtosis. The widely reproduced benchmark form is

```
SR* = sqrt(Var[SR_n]) * [ (1 - g)*Phi^-1(1 - 1/N) + g*Phi^-1(1 - 1/(N*e)) ]
      g = Euler-Mascheroni ~ 0.5772,  Phi^-1 = inverse normal CDF,  e = Euler's number
```

However, the fetch of the primary PDF performed for this reference returned a
**different** asymptotic expression for `SR*` (a Gumbel-type form involving
`sqrt(Phi^-1(1-1/N)^2 - ln(2*pi*ln N))`), and a PSR denominator in a variant
parameterisation. Both forms circulate. **Treat the exact algebra here as
unverified and read the primary paper before implementing it**; the *inputs* and
the *purpose* above are not in dispute, the constants are.[^bt-1][^bt-6] Do not
copy either form into production without checking it against the source.

### 5.7 The protocol, end to end

1. Audit for leakage, burn-in and smoothing (§5.1).
2. Fix the rule and its parameters **before** looking at results. Write them down.
3. Split with anchored or rolling walk-forward, purged and embargoed (§5.3).
4. Compute costs per round trip and report **break-even cost** (§5.4).
5. Report the full metric set including turnover, exposure and trade count (§5.5).
6. **Count every variant you tried** — including the ones you abandoned — and
   apply a multiple-testing correction with that N (§5.6).
7. Ask the §6 question: is the result concentrated in one regime or one sub-period?
   A signal that works only in 2020 is a regime bet, not an edge.
8. Ask the §7 question: is this signal independent of what you already run, or a
   sixth view of the same bet?

**A signal that clears steps 1-6 has not been shown to work. It has failed to be
disproven, on this sample, at this cost level.** Given the decay evidence in
§6.1, treat that as perishable and re-test on an ongoing basis.

## 6. Regime-performance evidence

**Read this section before writing any signal code.** The honest aggregate of the
peer-reviewed record is not "these signals work in regime X" — it is that raw
in-sample signal is real and large, and that three independent corrections
remove most or all of it. Any regime table that omits those corrections is
marketing.

### 6.1 The three things that kill a documented edge

| Killer | Evidence |
|---|---|
| **Data-snooping** | Sullivan/Timmermann/White expanded Brock/Lakonishok/LeBaron's 26 rules to **7,846** and applied White's Reality Check. On S&P 500 futures the best rule went from nominal **p = 0.042** to Reality-Check **p = 0.908**.[^regime-2] Marshall/Cahan/Cahan ran the same 7,846-rule universe on intraday SPDR data (2002-03): **0 of 7,846 profitable** after snooping correction — in both a bear year (S&P −21.2%) and a bull year (+21.9%).[^regime-6] |
| **Transaction costs** | Bajgrowicz & Scaillet (DJIA 1897-2011) found in-sample performance **"completely offset by the introduction of low transaction costs."**[^regime-3] STW put the DJIA break-even at **0.27% per trade**.[^regime-2] BLL themselves warned costs "should be carefully considered" — and **never netted them**.[^regime-1] |
| **Time (the least appreciated)** | STW's rules fail out-of-sample 1987-96.[^regime-2] Neely/Weller/Ulrich date the FX structural break to the **early 1990s**.[^regime-4] Park & Irwin: profitable in stocks **until the late 1980s, not thereafter**; in currencies until the **early 1990s**.[^regime-9] Bollinger Bands lost profitability in their two home US markets **in the very period of their introduction**.[^regime-7] |

Bajgrowicz & Scaillet add the decisive practical point: persistence tests show
an investor **could never have selected the future best-performing rules ex
ante**.[^regime-3] Note their method is the **false discovery rate**, not the SPA
test — SPA runs through Hansen (2005). The two are routinely conflated.

Neely/Weller/Ulrich give the best available synthesis: the 1970s-80s returns
were **genuine, not data mining**, and were then arbitraged away — but *"at a
much slower speed than would be consistent with efficient markets."*[^regime-4]
Their evidence for this over pure data-mining is subtle and worth keeping: they
find little support for a mean break exactly at the end of each original study's
sample, which is the signature data mining would produce.

### 6.2 Trend / moving-average signals

- **Favoured by:** large, *prolonged* directional moves. AQR states the mechanism
  plainly — *"range-bound periods lead to negative trend performance"* — and
  their fitted model carries a **negative intercept** precisely because trend
  historically lost money in directionless markets.[^regime-5] Duration matters
  more than magnitude: the ten largest 60/40 drawdowns averaged **~15 months**.
- **Destroyed by:** chop, whipsaw, and fast reversals. Trend cannot reposition
  through a 1987-style crash.
- **Bear-market nuance:** Zakamulin finds timing rules generate many false
  signals in *both* bull and bear trends, yet **"tend to outperform the market in
  bear states."**[^regime-8]
- **Negation to carry:** Zakamulin shows Glabadanidis (2015)'s striking published
  MA results were produced by **look-ahead bias**; corrected, MA timing is
  *"statistically indistinguishable from buy-and-hold."*[^regime-8]

### 6.3 Momentum oscillators — the cleanest result in the literature

Chong/Ng/Liew tested two RSI logics **side by side** on five OECD indices
(1976-2002, 10-day returns). The signs are opposite and both significant:[^regime-10]

| RSI logic | Character | Result |
|---|---|---|
| **RSI(21, 50) centerline crossover** | trend-following | Milan buy−sell **+2.268% / 10 days, t = 3.394**; **+5.069% annual net** of 1% round-trip cost |
| **RSI(N, 30/70) overbought/oversold** | mean-reverting | Milan RSI(7): **−1.163%, t = −2.371**; DAX RSI(14): **−0.914%, t = −1.937**; Milan RSI(21): **−1.266%** |

Their conclusion: centerline crossover performs better, and the rules are **"not
robust to the choice of market"** — on the Nikkei 225 none beat buy-and-hold.

**Why 30/70 fails: trends overrun the thresholds.** Lento et al. put it
concretely — Bollinger-style counter-trend logic *"would be selling the indexes
all the way up and buying the indexes all the way down."*[^regime-11] A Brent
crude study found oversold *buying* works while overbought *shorting* does not,
attributing it to momentum extending rallies past the textbook threshold; a
**higher** threshold outperformed the standard one (RSI 75: 22.84% vs RSI 70:
12.91% vs RSI 65: 7.91%).[^regime-12]

**Correction to a common assumption.** Mean-reversion signals are *not*
documented to work in quiet range-bound markets — that specific claim is
practitioner lore, with no peer-reviewed support located. The evidence points to
**high-volatility liquidity-stress states**: Nagel shows reversal Sharpe ratios
*"increase enormously along with the VIX,"* reaching ~1%/day in 2007-09, while
for large liquid low-vol stocks reversal profits are **near zero when VIX is
low**.[^regime-13] Contradiction preserved deliberately — do not resolve it.

### 6.4 Volatility signals — separate the band from the state variable

These are two different claims and the literature treats them differently.

- **Band indicators as signals: evidence runs negative.** Lento et al. (2,421
  daily obs across TSX/DJIA/CAD-USD/NASDAQ, costs included): Bollinger profitable
  in only **2 of 12** tests, underperforming buy-and-hold by **5.8-18.8%**; at the
  5% level **none of 48** signals carried information about future prices. Their
  verbatim conclusion: **"the BB are not profitable."** Reversing the logic won
  **8 of 12**.[^regime-11]
- **Volatility as a state variable: robust, and exploitable in-sample.** Moreira &
  Muir scale exposure by inverse lagged realized variance: market alpha
  **4.9%/yr**, appraisal ratio 0.33, a **25% increase in buy-and-hold Sharpe**;
  momentum appraisal ratio **0.875**.[^regime-14] The precondition is explicit and
  load-bearing: *"our results rely on a large degree of variation in volatility to
  work... if volatility were constant, alphas would be zero."* Losses concentrate
  in **low-volatility eras** such as the 1960s.
- **Live contradiction:** Cederburg et al. confirm the spanning-regression alphas
  but argue the strategies are **"not implementable in real time"** — out-of-sample
  Sharpe **0.42 vs 0.46** for the unmanaged market, with only **8 of 94** anomalies
  showing significant gains, blaming structural instability.[^regime-15] Moreira &
  Muir claim the opposite. Both are top-3-journal. Unresolved.

### 6.5 Time-series momentum — strongest surviving effect, with a live challenger

Moskowitz/Ooi/Pedersen (58 liquid futures, 1985-2009): 12-month TSMOM Sharpe
**> 1**, roughly **2.5×** the equity market's.[^regime-16] The regime shape is the
key: the **"time series momentum smile"** — returns largest in the biggest up
**and** down moves, a straddle-like rather than directional payoff. Their own
stated failure mode: TSMOM *"suffers sharp losses when a crisis ends, as a sharp
trend reversal generates losses."*

**Challenger, same journal:** Huang/Li/Wang/Zhou, *"Time series momentum: Is it
there?"* — asset-by-asset regressions show little evidence in or out of sample;
the pooled t-statistic **"is not statistically reliable"** against a
size-distortion-corrected simulated null; profitability is **comparable to a
historical-sample-mean strategy requiring no predictability at all**.[^regime-17]
Both stand.

**Momentum crashes** (Daniel & Moskowitz): partly forecastable, occurring in
**"panic states"** — after market declines, high volatility, contemporaneous
rebound. Loser-decile betas can exceed **3** while winner betas fall below
**0.5**, so momentum carries a conditionally large negative beta into rebounds;
in bear markets it behaves like a **written call**. WML monthly skewness
**−4.70**.[^regime-18] Barroso & Santa-Clara: **12% constant-volatility targeting**
nearly doubled momentum's Sharpe.[^regime-19]

**Sponsor caveat.** AQR's century-scale trend evidence (positive in every decade
since 1880; the smile; positive in 8 of the 10 largest 60/40 drawdowns) rests on
**hypothetical/simulated** returns published by a firm selling trend products in
a practitioner journal. Do not carry its Sharpe figures as fact, and do not
conflate the white paper's **portfolio-level 0.77** (1880-2013) with the JPM
version's **per-market average ≈ 0.4** (1880-2016) — different statistics.[^regime-20]

### 6.6 Asset class and timeframe

Park & Irwin's survey of **92 modern studies: 58 positive / 24 negative / 10
mixed** (AgMAS 2004 version — the often-quoted "95 studies" belongs to the 2007
journal version and is not verified here):[^regime-9]

| Market | Pos | Mixed | Neg | Verdict |
|---|---|---|---|---|
| Stock | 24 | 5 | 12 | Profitable **until the late 1980s, not thereafter** |
| Currency | 25 | 4 | 9 | Consistently profitable **until the early 1990s**, then declined |
| Futures | 7 | 1 | 3 | Late 1970s-mid 1980s; **channel and MA rules most consistent**; unprofitable in livestock |

Their own qualification matters: most studies suffer *"data snooping, ex post
selection of trading rules... and difficulties in estimation of risk and
transaction costs."*

**Crypto is genuinely four-way contested** — Hudson & Urquhart find 20-50% of
14,919 rules survive FWER *and* FDR correction yet **no out-of-sample
predictability for Bitcoin**; Gerritsen et al. find trading-range breakout beats
buy-and-hold on daily data but underperforms in the calm 2015-16 stretch; Corbet
et al. find TRB signals with the **opposite sign** on 1-minute data; Li et al.
find nothing profitable at all after snooping adjustment. The daily-vs-minute
frequency gap is a plausible reconciliation that **no paper tests**.[^regime-21]

**Timeframe:** intraday is where practitioners place most faith and where
evidence is weakest — 0 of 7,846 rules profitable intraday.[^regime-6]

### 6.7 Informative is not profitable

Lo/Mamaysky/Wang's kernel-regression pattern study found all 10 patterns
statistically significant for **Nasdaq** stocks but only **5 of 10** for
NYSE/AMEX — the effect concentrating in harder-to-value, less liquid names.
Their own caveat is the part usually dropped: *"this does not necessarily imply
that technical analysis can be used to generate 'excess' trading
profits."*[^regime-22] The paper is about incremental **information content**, and
it says so.

### 6.8 What must not be asserted

Three claims are unsupported by the located evidence and are excluded from this
reference deliberately:

1. That oscillator overbought/oversold logic works in quiet range-bound markets
   (§6.3 — lore; the evidence points to high-VIX states instead).
2. That band indicators such as Bollinger or Keltner have standalone
   profitability (§6.4 — evidence runs negative).
3. That any of this is net-profitable out-of-sample after realistic costs in
   liquid developed equity markets (§6.1).

## References

Footnote ids are scoped per concept (`[^<slug>-n]`) so adding a concept never
renumbers an earlier one.

### Concept 5 — backtest recipe

[^bt-1]: Bailey & López de Prado, "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality," *Journal of Portfolio Management*. Primary PDF fetched for this reference; see the §5.6 formula caveat — the fetched text returned a different `SR*` asymptotic form than the widely reproduced two-quantile expression. Also the source of Minimum Track Record Length. https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf · https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551 (paper)
[^bt-2]: López de Prado, *Advances in Financial Machine Learning* (Wiley) — purged and embargoed cross-validation for overlapping-label time series. Cited by name; no URL fetched this run.
[^bt-3]: White (2000), "A Reality Check for Data Snooping," *Econometrica* 68(5):1097-1126. Cited by name; its application is documented in `[^regime-2]`, which was fetched this run.
[^bt-4]: Hansen (2005), "A Test for Superior Predictive Ability," *Journal of Business & Economic Statistics* 23(4):365-380. Cited by name; no URL fetched this run.
[^bt-5]: Bailey, Borwein, López de Prado & Zhu, "The Probability of Backtest Overfitting" — PBO via combinatorially symmetric cross-validation (CSCV). Cited by name; no URL fetched this run.
[^bt-6]: Secondary explainers circulating the two-quantile `SR*` form, surfaced in this run's search log and used only to document the discrepancy in §5.6, never as primary support: https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio (encyclopedia) · https://paperswithbacktest.com/course/deflated-sharpe-ratio (blog)

### Concept 6 — regime-performance evidence

[^regime-1]: Brock, Lakonishok & LeBaron (1992), "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns," *Journal of Finance* 47(5):1731-1764. DJIA daily 1897-1986, 26 rules. Buy-day mean +0.042%/day vs sell-day −0.025%/day; buy-period SD 0.89% vs sell 1.34%. Costs never netted. https://www.kevinsheppard.com/files/teaching/mfe/advanced-econometrics/Brock_Lakonishok_LeBaron.pdf (paper)
[^regime-2]: Sullivan, Timmermann & White (1999), "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap," *Journal of Finance* 54(5):1647-1691. 7,846 rules, White's Reality Check. S&P futures nominal p=0.042 → RC p=0.908; DJIA break-even cost 0.27%/trade. https://eprints.lse.ac.uk/119144/1/dp303.pdf (paper)
[^regime-3]: Bajgrowicz & Scaillet (2012), "Technical trading revisited: False discoveries, persistence tests, and transaction costs," *Journal of Financial Economics* 106(3):473-491. DJIA 1897-2011, **false-discovery-rate** method (not SPA). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1095202 (paper)
[^regime-4]: Neely, Weller & Ulrich (2009), "The Adaptive Markets Hypothesis: Evidence from the Foreign Exchange Market," *JFQA* 44(2):467-488. https://fraser.stlouisfed.org/files/docs/publications/frbsl_wp/2006-046.pdf (paper)
[^regime-5]: Babu, Hurst, Ooi, Pedersen et al. (AQR), "You Can't Always Trend When You Want," *Journal of Portfolio Management*. Sponsor caveat: AQR sells trend products. https://images.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-You-Cant-Always-Trend-When-You-Want.pdf (paper, practitioner)
[^regime-6]: Marshall, Cahan & Cahan (2008), *Journal of Empirical Finance* 15(2):199-210. Intraday SPDR 2002-03; 0 of 7,846 rules profitable after snooping correction. https://www.sciencedirect.com/science/article/abs/pii/S0927539807000588 (paper)
[^regime-7]: "Popularity versus Profitability: Evidence from Bollinger Bands" (working paper). BB lose profitability in their home US markets in the period of introduction. https://acfr.aut.ac.nz/__data/assets/pdf_file/0007/29896/100009-Popularity-vs-Profitability-BB-August-Final.pdf (paper, WP)
[^regime-8]: Zakamulin, "A Comprehensive Look at the Empirical Performance of Moving Average Trading Strategies" (155-year dataset) and "Revisiting the Profitability of Market Timing with Moving Averages," *International Review of Finance* — documents look-ahead bias in Glabadanidis (2015). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2677212 · https://onlinelibrary.wiley.com/doi/10.1111/irfi.12132 (paper)
[^regime-9]: Park & Irwin, "The Profitability of Technical Analysis: A Review," AgMAS Project Research Report 2004-04. 92 studies: 58 positive / 24 negative / 10 mixed. https://ageconsearch.umn.edu/record/37487/files/AgMAS04_04.pdf (paper)
[^regime-10]: Chong, Ng & Liew (2014), "Revisiting the Performance of MACD and RSI Oscillators," *Journal of Risk and Financial Management* 7(1):1-12. Five OECD indices 1976-2002. https://www.mdpi.com/1911-8074/7/1/1 (paper)
[^regime-11]: Lento, Gradojevic & Wright (2007), "Investment information content in Bollinger Bands?" *Applied Financial Economics Letters* 3:263-267. https://www.researchgate.net/publication/46527151_Investment_information_content_in_Bollinger_Bands (paper)
[^regime-12]: Brent crude contrarian study (2025), *Energies* 18(11):2735. Oversold buying works, overbought shorting does not; RSI 75 > RSI 70 > RSI 65. https://www.mdpi.com/1996-1073/18/11/2735 (paper)
[^regime-13]: Nagel (2012), "Evaporating Liquidity," *Review of Financial Studies* 25(7):2005-2039. Reversal Sharpe rises with VIX; ~1%/day in 2007-09; near zero for large liquid names when VIX is low. https://www.nber.org/system/files/working_papers/w17653/w17653.pdf (paper)
[^regime-14]: Moreira & Muir (2017), "Volatility-Managed Portfolios," *Journal of Finance* 72(4):1611-1644. https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf (paper)
[^regime-15]: Cederburg, O'Doherty, Wang & Yan (2020), "On the performance of volatility-managed portfolios," *Journal of Financial Economics*. OOS Sharpe 0.42 vs 0.46; 8 of 94 anomalies significant. https://www.lehigh.edu/~xuy219/research/COWY.pdf (paper)
[^regime-16]: Moskowitz, Ooi & Pedersen (2012), "Time series momentum," *Journal of Financial Economics* 104(2):228-250. 58 instruments 1985-2009. https://w4.stern.nyu.edu/facdir/lpederse/papers/TimeSeriesMomentum.pdf (paper)
[^regime-17]: Huang, Li, Wang & Zhou (2020), "Time series momentum: Is it there?" *Journal of Financial Economics* 135(3):774-794. https://ink.library.smu.edu.sg/context/lkcsb_research/article/7520/viewcontent/Time_series_momentum_JFE_sv.pdf (paper)
[^regime-18]: Daniel & Moskowitz (2016), "Momentum crashes," *Journal of Financial Economics*. NBER w20439 used for figures; earlier Stern WP reports different crash percentages. https://www.nber.org/system/files/working_papers/w20439/w20439.pdf (paper)
[^regime-19]: Barroso & Santa-Clara (2015), "Momentum has its moments," *Journal of Financial Economics*. 12% constant-volatility targeting nearly doubles momentum's Sharpe. (paper)
[^regime-20]: Hurst, Ooi & Pedersen (2017), "A Century of Evidence on Trend-Following Investing," *JPM* 44(1):15-29, plus the 1880-2013 white paper. Hypothetical/simulated returns; AQR sells trend products. https://www.aqr.com/-/media/AQR/Documents/Insights/Journal-Article/AQR-JPM-Fall-2017.pdf (paper, practitioner)
[^regime-21]: Crypto, four contested results: Hudson & Urquhart (2019), *Annals of Operations Research* https://link.springer.com/article/10.1007/s10479-019-03357-1 ; Gerritsen et al. (2020), *Finance Research Letters* http://dirkgerritsen.nl/uploads/gerritsen_et_al_2020_bitcoin_trading_rules.pdf ; Corbet, Eraslan, Lucey & Sensoy, *Finance Research Letters* (1-minute Bitfinex) https://doras.dcu.ie/25053/1/The_effectiveness_of_technical_trading_rules_in_cryptocurrency_markets%5B1%5D.pdf ; Li, Wang, Wang & Yang (2023), *Journal of Accounting and Finance* 23(4) https://doi.org/10.33423/jaf.v23i4.6453 (papers)
[^regime-22]: Lo, Mamaysky & Wang (2000), "Foundations of Technical Analysis," *Journal of Finance* 55(4):1705-1765. All 10 patterns significant on Nasdaq, 5 of 10 on NYSE/AMEX. https://www.cis.upenn.edu/~mkearns/teaching/cis700/lo.pdf (paper)
