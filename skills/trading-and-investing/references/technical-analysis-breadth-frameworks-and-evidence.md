---
name: technical-analysis-breadth-frameworks-and-evidence
# provenance: split out of references/technical-analysis.md 2026-08-04 — §8-§12 moved
# verbatim so both halves clear the ~10k-token reference ceiling. The content itself was
# researched and verified-as-of 2026-06-21; the split did not re-verify its sources.
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-06-21"  # content split from technical-analysis.md on 2026-08-04; NOT re-verified at split time
category: reference
description: >-
  SPOKE of trading-and-investing — the market-internals, framework and evidence half of
  technical analysis (§8-§12 of the technical-analysis spoke; §1-§7 stay in
  references/technical-analysis.md). Covers volume and breadth indicators (OBV/Granville,
  VWAP and anchored VWAP, Volume Profile/POC/value area, advance-decline line, McClellan
  Oscillator and Summation Index, Zweig Breadth Thrust); the classical frameworks (Dow
  Theory's six tenets, three trend scales and three phases, Brown-Goetzmann-Kumar; Elliott
  Wave's 5-3 structure, Fibonacci guidelines and the Batchelor & Ramyar critique);
  multi-timeframe analysis and signal combination; and the empirical evidence base —
  weak-form EMH (Fama 1970/1991), Brock-Lakonishok-LeBaron 1992, the data-snooping critique
  (Sullivan-Timmermann-White 1999, White 2000, Bajgrowicz & Scaillet 2012), Park & Irwin's
  95-study meta-analysis, Lo-Mamaysky-Wang 2000, momentum (Jegadeesh & Titman;
  Moskowitz et al.), the Adaptive Market Hypothesis, Menkhoff's 692-manager survey — plus
  the common practitioner failure modes. Educational only — NOT financial, investment, or
  tax advice.
keywords:
  - volume-indicators
  - OBV
  - VWAP
  - anchored-VWAP
  - volume-profile
  - market-breadth
  - advance-decline-line
  - McClellan-Oscillator
  - Zweig-Breadth-Thrust
  - Dow-Theory
  - Elliott-Wave
  - multi-timeframe-analysis
  - signal-combination
  - efficient-market-hypothesis
  - data-snooping
  - adaptive-market-hypothesis
  - technical-analysis-evidence
  - momentum
tags:
  - trading
  - technical-analysis
  - market-breadth
  - volume
  - indicators
  - evidence
---

# Technical Analysis — Breadth, Frameworks and Evidence

> **Hub reference** — part of `trading-and-investing`. Covers §8-§12 of the `technical-analysis` spoke.
> **Educational information only — NOT financial, investment, or tax advice.**
> content verified-as-of: 2026-06-21 · split out of `references/technical-analysis.md` 2026-08-04

Volume and breadth read the market's *participation*; Dow Theory and Elliott Wave impose a
*structure* on it; multi-timeframe analysis governs how the pieces are stacked; and the last two
sections mark the whole discipline to the academic record. Section and footnote numbering is
inherited from the parent file and is deliberately **not** restarted, so section 8 and footnote 37
mean the same thing on both sides of the split.

**Scope.**

| For… | Go to |
|---|---|
| Chart types, trendlines, support/resistance and the polarity principle (§1-§2) | `references/technical-analysis.md` |
| Candlestick patterns and chart patterns — H&S, double top/bottom, triangles, flags, wedges (§3-§5) | `references/technical-analysis.md` |
| Price-derived indicator definitions used by §10's combinations — RSI, MACD, stochastics, SMA/EMA, Bollinger Bands, ATR (§6-§7) | `references/technical-analysis.md` |
| Implementing any of these signals in pandas/numpy — substrate, trend/MA, momentum, volatility (§1-§4) | `references/indicator-signal-implementation-and-backtesting.md` |
| Backtesting one signal honestly, and the cited regime record (§5-§6) | `references/signal-backtest-protocol-and-regime-evidence.md` |
| Runnable volume/breadth, candlestick, chart-pattern and price-action implementations, plus signal-level redundancy (§7-§10) | `references/signal-pairing-volume-and-pattern-signal-sets.md` |
| Why strategies fail in practice, and which signals are redundant with each other | `references/strategy-failure-modes-and-synergy.md` |
| Detecting the regime an indicator is being asked to work in | `references/regime-detection-and-classification.md` |
| Bar interval and indicator-period coupling underneath any "multi-timeframe" claim | `references/sampling-frequency-and-bar-aggregation.md` |
| Strategy styles and discretionary backtesting; multiple testing | `references/trading-strategies-and-styles.md` §5, `references/algorithmic-and-quant-trading.md` §5.3 |
| Position sizing, stops and portfolio heat | `references/trading-risk-management.md` |
| ML/statistical-learning treatment of the same predictability question | `references/ai-and-ml-for-trading.md` |

## Contents

8. [Volume and Breadth Indicators](#8-volume-and-breadth-indicators)
9. [Classical Frameworks: Dow Theory and Elliott Wave](#9-classical-frameworks-dow-theory-and-elliott-wave)
10. [Multi-Timeframe Analysis and Signal Combination](#10-multi-timeframe-analysis-and-signal-combination)
11. [Empirical Evidence — What the Research Actually Shows](#11-empirical-evidence--what-the-research-actually-shows)
12. [Common Failure Modes and Practitioner Pitfalls](#12-common-failure-modes-and-practitioner-pitfalls)
13. [References](#references)

---

## 8. Volume and Breadth Indicators

Volume confirms or questions price action. The core principle: **price moves on high volume are more significant than price moves on low volume.**

### On-Balance Volume (OBV)

**Creator:** Joseph Granville, *Granville's New Key to Stock Market Profits* (1963). The technique was earlier called "continuous volume" by Woods and Vignola; Granville popularized it and coined the name.[^26]

**Formula:**
```
If Close > Close_prev: OBV = OBV_prev + Volume
If Close < Close_prev: OBV = OBV_prev − Volume
If Close = Close_prev: OBV = OBV_prev
```

The absolute value of OBV is arbitrary (starting point dependent); only the direction and relative change matter.

**Core principle ("volume precedes price"):** When positive volume consistently outpaces negative volume (rising OBV even as price is flat), buying pressure will eventually drive prices higher. When OBV diverges from price, it signals weakening conviction.

**Signals:**
- OBV rising with price: volume confirms the uptrend
- OBV falling with price: volume confirms the downtrend
- **OBV rising while price flat/declining** (bullish divergence): pending upside move
- **OBV falling while price flat/rising** (bearish divergence): pending downside move

**Academic evidence:** Tsang & Chong (2009) found the OBV trading rule profitable in Greater China equity markets.[^27] Evidence in US and European markets is weaker — strategies become unprofitable after transaction costs are applied in developed markets.[^27] The paper's authors noted "a lack of empirical studies documenting the profitability of volume-based technical indicators" when they wrote in 2009.

---

### VWAP — Volume-Weighted Average Price

**Formula:**
```
VWAP = Σ(Typical Price × Volume) / Σ(Volume)   [cumulative from session open]
where Typical Price = (High + Low + Close) / 3
Resets at each trading session open.
```

**Use cases:**
- **Institutional execution benchmark:** VWAP-based orders represent approximately 50% of institutional investor order flow; institutional traders aim to buy below VWAP and sell above VWAP to minimize market impact.[^28]
- **Intraday support/resistance:** Price above VWAP = buyers in control; below VWAP = sellers. Many institutional algorithms reference VWAP as a dynamic price anchor.
- **VWAP slippage** (executed price vs. VWAP) is a standard broker performance metric.
- **Anchored VWAP**: Calculation anchored to a user-specified event (earnings, key high/low) rather than the session open, popularized by Brian Shannon. Used for tracking longer-term institutional footprints.

VWAP is primarily a short-term trading and execution tool, not a long-term trend signal.

---

### Volume Profile

**Origin:** Derived from Market Profile, developed by J. Peter Steidlmayer at the Chicago Board of Trade (CBOT) in the early 1980s; formally introduced as part of the CBOT's Liquidity Data Bank in 1984.[^29] Volume Profile is the volume-at-price evolution of the original time-based Market Profile.

**Key concepts:**
| Term | Definition |
|---|---|
| **Point of Control (POC)** | Price level with the highest traded volume for the measured period; represents "fair value" — where the most market participants agreed to transact |
| **Value Area (VA)** | Price range containing ~70% of the period's total volume (based on ≈1 standard deviation of a normal distribution) |
| **Value Area High (VAH)** | Upper boundary of the Value Area; acts as dynamic resistance |
| **Value Area Low (VAL)** | Lower boundary; acts as dynamic support |
| **High Volume Node (HVN)** | Price level with heavy historical volume; price tends to stall or consolidate near HVNs |
| **Low Volume Node (LVN)** | Price level with thin historical volume; price tends to move rapidly through LVNs |

**Trading applications:** Price opening above prior VAH with follow-through suggests a trending move. Price opening inside the VA suggests mean-reversion toward POC. Price moving outside the VA ("out of balance") often initiates trending moves. The "80% rule" (practitioners say: when price enters the prior VA, it traverses the full VA ~80% of the time) is widely cited but lacks peer-reviewed validation.

---

### Market Breadth: Advance-Decline Line

**Formula:**
```
A/D Line_t = A/D Line_{t-1} + (Advancing Issues_t − Declining Issues_t)
[running cumulative total; most commonly applied to NYSE issues]
```

**Signals:**
- A/D Line confirming new index highs = healthy, broad-based rally
- **Bearish divergence:** Index makes new highs but A/D Line fails to confirm → narrowing breadth, fewer stocks participating; potential topping signal. Appeared 3–6 months before the 1987 crash, 2000 dot-com top, and 2007–2008 bear market.
- **Bullish divergence:** Index makes new lows but A/D Line makes a higher low → selling breadth is fading; potential bottoming signal.

**Caveats:** (1) Market-cap blind — each stock equally weighted regardless of size. (2) Nasdaq A/D Line can trend down persistently due to frequent delistings of failed companies, even as the Nasdaq index rises — use NYSE A/D Line for broader market signals.

**Academic evidence:** Zaremba et al. (2021) found that high advance-decline ratio is a robust predictor of future cross-sectional stock returns across developed, emerging, and frontier equity markets, controlling for size, style, volatility, skewness, momentum, and trend-following.[^30]

---

### McClellan Oscillator and Summation Index

**Creator:** Sherman McClellan and Marian McClellan, *Patterns for Profit* (1970).

**Formula:**
```
McClellan Oscillator = EMA(19) of Net Advances − EMA(39) of Net Advances
[where Net Advances = Advancing Issues − Declining Issues]
```

The 19-day EMA (≈10% smoothing) represents short-term breadth momentum; the 39-day EMA (≈5% smoothing) represents intermediate-term breadth.

**Signals:** Above zero = bullish short-term breadth; below zero = bearish. A rapid swing from deeply negative (below −50) to strongly positive (above +50) = **breadth thrust** signal.

**McClellan Summation Index:** The cumulative running total of daily McClellan Oscillator values. Used to identify major trend shifts.

---

### Zweig Breadth Thrust

**Creator:** Martin Zweig, *Winning on Wall Street* (1986).

**Formula:**
```
Breadth Thrust Indicator = 10-day EMA of [Advancing Issues / (Advancing + Declining Issues)]
Signal: moves from below 0.40 to above 0.615 within any 10-day period
```

**Historical record:** As of the time of most cited analyses, this signal had occurred 19 times since WWII, with markets higher in every subsequent 12-month period. **Important caveat:** This track record is based on a very small sample (~19 occurrences over ~80 years) and has not been peer-reviewed as a standalone predictive test.

---

## 9. Classical Frameworks: Dow Theory and Elliott Wave

### Dow Theory

Charles Dow never formally codified the theory — it is derived from ~255 Wall Street Journal editorials he wrote between 1900 and 1902 before his death. William Hamilton systematized it in *The Stock Market Barometer* (1922); Robert Rhea formalized the six tenets in *The Dow Theory* (1932).[^31]

**The Six Tenets:**

1. **The market discounts everything.** All known information (economic, political, psychological) is already reflected in prices. A precursor to the Efficient Market Hypothesis.

2. **Three types of trends (movements):**
   - *Primary:* Less than a year to several years; the main bull or bear market.
   - *Secondary reaction:* 10 days to 3 months; Rhea specified retracements of 33%–66% of the primary move.
   - *Minor:* Hours to a month; too brief to trade reliably.

3. **Three phases of a primary trend:**
   - *Bull:* (1) Accumulation — informed investors buy against pessimism; (2) Public participation — strongest price movement; (3) Excess/distribution — speculative fever, smart money exits.
   - *Bear:* (1) Distribution — smart money sells to speculators; (2) Public participation — panic spreads; (3) Despair — forced liquidation.

4. **The averages must confirm each other.** The Dow Jones Industrial Average and the Dow Jones Transportation Average must both confirm a primary trend signal. Divergence between the two is a warning sign. (Hamilton's original rationale: manufactured goods must be shipped; industrial strength validates transportation strength.)

5. **Volume confirms the trend.** Volume expands in the direction of the primary trend and contracts on secondary reactions.

6. **A trend persists until a reversal signal appears.** The presumption is continuation; distinguishing a genuine reversal from a secondary reaction is the most difficult judgment in applying Dow Theory.

**Empirical evidence:** Cowles (1933) originally found Hamilton's market calls (1902–1929) underperformed buy-and-hold by ~3.5% annualized.[^32] Brown, Goetzmann & Kumar (1998) re-examined Hamilton's 255 editorials using a neural network model and found Hamilton was correct ~60% of the time on market direction; the Dow Theory portfolio returned ~2% less than buy-and-hold in raw terms but produced **superior risk-adjusted returns** (positive Sharpe ratio alpha) due to lower volatility.[^33] **Published in the *Journal of Finance*, 1998.**

---

### Elliott Wave Theory

**Creator:** R.N. Elliott, *The Wave Principle* (August 31, 1938).[^34]

**Core structure:**

**Impulse (motive) waves — 5-wave pattern:**
- Waves 1, 3, 5: move in the direction of the trend
- Waves 2 and 4: corrective retracements within the impulse
- Each impulse wave subdivides into 5 smaller waves; each correction subdivides into 3

**Three inviolable rules** (violations invalidate the wave count):
1. Wave 2 never retraces more than 100% of Wave 1 (cannot go below Wave 1's starting point)
2. Wave 3 cannot be the shortest of the three impulse waves (1, 3, and 5)
3. Wave 4 never enters the price territory of Wave 1 (no overlap — with an exception for futures contracts)

**Corrective waves — 3-wave A-B-C pattern:**
- **Zigzag (5-3-5):** Sharp counter-trend move
- **Flat (3-3-5):** Sideways correction; most common is the expanded flat
- **Triangle (3-3-3-3-3):** Five sub-waves; typically in Wave 4 or Wave B position
- **Complex:** Combinations of the above (double and triple threes)

**Fibonacci relationships (guidelines, not rules):**
Elliott's own claim: "The Fibonacci Summation Series is the basis of The Wave Principle." Wave 2 typically retraces 38.2–61.8% of Wave 1; Wave 3 often extends to 1.618× Wave 1; Wave 4 retraces ~38.2% of Wave 3; Wave 5 often equals Wave 1. These are guidelines with wide variability — practitioners frequently revise wave counts after the fact.

**Empirical evidence (largely negative):** Batchelor & Ramyar (2005) tested whether Fibonacci ratios appear non-randomly in DJIA data and found "no significant difference between the frequencies with which price and time ratios occur in cycles in the Dow Jones Industrial Average, and frequencies which we would expect to occur at random."[^35] Mandelbrot cautioned: "Wave prediction is a very uncertain business... The record of this, as of most technical analysis, is at best mixed." Aronson (*Evidence-Based Technical Analysis*, 2007) argued the Elliott Wave Principle "as popularly practiced, is not a legitimate theory, but a story" due to its loosely defined rules permitting excessive post-hoc interpretation.[^36]

**The core problem:** The wave count is subjective. Asking ten Elliott Wave practitioners the same question routinely produces ten different answers. Practitioners can almost always construct a valid wave count that fits history, but the rules do not produce unambiguous real-time signals. Prechter's rebuttal to Batchelor & Ramyar: their study examined filtered trends, not actual Elliott wave counts — so it does not test wave theorists' actual claims.

**Verdict:** Elliott Wave is widely used in practitioner communities but lacks scientific validation. It is most useful as a descriptive vocabulary for market structure rather than a precise forecasting tool.

---

## 10. Multi-Timeframe Analysis and Signal Combination

Individual indicators generate many false signals; the practitioner consensus is to use multiple, non-correlated signals in alignment before acting.

### Multi-Timeframe Approach

- **Higher timeframe = trend direction filter**: Use a weekly chart to identify the primary trend; use a daily chart for entries in the direction of that trend; use an intraday chart for fine-tuning entries.
- The principle: trade lower-timeframe setups only when they align with the higher-timeframe trend.
- Timeframe hierarchy commonly used: Weekly → Daily → 4-hour → 1-hour (adjust for style; day traders typically Daily → 4h → 15m).

### Signal Combination Examples

| Setup Type | Components |
|---|---|
| Trend-following | Price above 200-day MA (trend filter) + 50-day MA above 200-day MA (golden cross) + MACD histogram expanding positive + RSI >50 but <70 (momentum, not overbought) |
| Mean-reversion | Price pulls back to rising 50-day MA + RSI reaches oversold (30–40 in uptrend) + Volume declining on pullback + Bullish candlestick reversal |
| Breakout | Price consolidating in triangle or flag → Volume contracting → Breakout on high volume → ATR-based stop below the breakout level |

### Why Multiple Signals Matter

The false-signal rate of any single indicator used in isolation is high. Combination filters reduce false signals (at the cost of fewer signals overall). Indicators from different categories (trend-following vs. momentum oscillator vs. volume) provide more genuine diversification than combining two momentum oscillators, which tend to give correlated readings.

A key practitioner principle: **never use an indicator to predict price; use it to confirm what price is already doing.**

---

## 11. Empirical Evidence — What the Research Actually Shows

This section presents the academic literature fairly — both the evidence *for* and *against* TA effectiveness. The evidence is genuinely contested.

### The Efficient Market Hypothesis (Weak Form)

Fama (1970) defined three forms of market efficiency; the **weak form** — that current prices already incorporate all historical price and volume data — directly precludes technical analysis from generating abnormal returns.[^37] Fama updated this in 1991, acknowledging that return predictability exists at some horizons but interpreting it as rational time-varying expected returns rather than exploitable inefficiency.[^38]

The early empirical support for weak-form efficiency: Kendall (1953) found statistical independence in weekly British stock index returns; Roberts (1959) showed DJIA patterns consistent with a random walk; Cowles (1933) found professional forecasters unable to beat chance.[^32]

### The Foundational Positive Study

Brock, Lakonishok & LeBaron (1992) tested moving average crossover rules and trading range break rules on 90 years of DJIA data (1897–1986) using bootstrap simulation against four null models (random walk, AR(1), GARCH-M, Exponential GARCH). They found "strong support for technical strategies" — buy signals consistently generated higher returns than sell signals, with lower volatility; sell signal returns were *negative*. The results were inconsistent with all four null models tested.[^21]

**This is the most-cited academic paper supporting TA effectiveness.** But it was directly challenged.

### The Data-Snooping Critique

Sullivan, Timmermann & White (1999) extended BLL's methodology using **White's Reality Check** — a formal bootstrap test that accounts for the multiple-comparisons problem when many rules are tested on the same data. After applying this correction to a larger universe of trading rules on the same DJIA data and adding a 10-year out-of-sample period, **no evidence was found that technical trading rules provide excess returns net of data-snooping bias.**[^22]

Bajgrowicz & Scaillet (2012) extended this further using the **False Discovery Rate** (FDR), a more powerful data-snooping control than White's Reality Check. Their result: even with better statistical controls, TA performance is "completely offset by introduction of low transaction costs."[^39]

White (2000) provided the formal statistical framework for testing data snooping (*Econometrica*).[^40]

**The data-snooping problem is critical to understand:** When researchers test hundreds of rules on the same historical data, some will appear profitable by chance. Unless the test corrects for the number of rules tried, the apparent best rule reflects selection bias, not genuine predictive power.

### The Large Meta-Analysis

Park & Irwin (2007) reviewed 95 modern studies of technical trading profitability.[^19]
- **56 studies (59%)** found positive results; **20 (21%)** negative; **19 (20%)** mixed.
- Early studies: profitable in **foreign exchange and futures markets** but not consistently in stock markets.
- Modern studies: consistent profits "at least until the early 1990s."
- After the early 1990s: profitability declined, especially in stock markets.
- Key methodological concern: **most studies fail to consistently outperform when accounting for transaction costs.** Park & Irwin explicitly identify data snooping, ex post rule selection, inadequate risk measurement, and transaction cost estimation as major flaws in the positive-results literature.

### Studies Finding Incremental Information

Lo, Mamaysky & Wang (2000) used nonparametric kernel regression (eliminating subjective pattern identification) on US stock data from 1962–1996. They found "several technical indicators do provide incremental information and may have some practical value" — conditional return distributions given the occurrence of patterns (H&S, double bottoms) differ significantly from unconditional distributions.[^10] However, they did not demonstrate that this statistical information is economically exploitable after transaction costs.

Neely, Rapach, Tu & Zhou (2014) found technical indicators (including moving averages and momentum) have "statistically and economically significant forecasting power" for the US equity risk premium, comparable to macroeconomic variables and complementary over the business cycle — better at predicting declines near cycle peaks.[^41]

Jegadeesh & Titman (1993) documented that winners outperform losers by approximately 12% per year over 3-to-12-month horizons (1965–1989), the foundational academic **momentum** result.[^42] Moskowitz, Ooi & Pedersen (2012) found significant **time-series momentum** across 58 liquid futures contracts (equity, currency, commodity, bond).[^43] These are TA-adjacent results using price history, though they differ from classical chart-pattern TA.

### Where TA Works Better

Consistent patterns across the literature:
- **Foreign exchange markets:** Stronger evidence than equities. Multiple studies find profitable MA and filter rules in FX, with the clearest mechanism: central bank intervention creates exploitable trends.
- **Futures markets:** Also stronger than equities (Moskowitz et al., Park & Irwin).
- **Emerging/developing markets:** Consistently more positive results, attributed to lower market efficiency.
- **Historical (pre-1990s):** Most positive evidence clusters in earlier periods; profitability has declined as markets have become more efficient and transaction costs have fallen.

### The Adaptive Market Hypothesis

Lo (2004) proposed the **Adaptive Market Hypothesis (AMH)** to reconcile the EMH with behavioral alternatives by applying evolutionary principles to markets.[^44] Core insight: **market efficiency is not binary but varies over time** as investor populations adapt and the financial landscape changes. Profitable patterns arise, attract capital, and self-destruct as they become widely known. TA may work in some regimes and not others — the same strategy that generated returns in the 1970s–1980s may have been arbitraged away by the 1990s–2000s.

The AMH predicts regime-dependent TA profitability, which is broadly consistent with the empirical record: evidence is positive in earlier periods, weaker in later periods, and stronger in less-efficient markets.

### Menkhoff (2010) — Practitioner Evidence

Menkhoff (2010) surveyed **692 fund managers in five countries** and found the vast majority use TA; 87% place "at least some importance" on it; TA is considered more important than fundamentals for forecasting over short horizons (up to several weeks).[^45] Critically: there was "no evidence that technical analysis is preferred by less rational or inferior fund managers." Sophisticated practitioners find TA useful — the question is whether they find it useful because it works, or because widespread use creates self-fulfilling prophecies (if enough traders watch the same levels, those levels become important).

### Summary: What the Evidence Supports

| Claim | Evidence Quality | Notes |
|---|---|---|
| MA/pattern rules showed profits on DJIA pre-1990 | HIGH | BLL 1992 (but see data-snooping critique) |
| Data-snooping explains much of the positive evidence | HIGH | Sullivan et al. 1999, Bajgrowicz & Scaillet 2012 |
| Transaction costs eliminate most remaining TA profits in developed markets | HIGH | Bajgrowicz & Scaillet 2012, Fang et al. 2014 |
| TA provides "incremental statistical information" (chart patterns) | HIGH | Lo et al. 2000 (but not necessarily exploitable) |
| Price momentum is a real, documented phenomenon | HIGH | Jegadeesh & Titman 1993, Moskowitz et al. 2012 |
| TA more effective in FX and futures than equities | HIGH | Park & Irwin 2007 across 95 studies |
| TA more effective in emerging markets than developed | HIGH | Multiple studies |
| TA effectiveness has declined post-1990 in developed equity markets | HIGH | Sullivan 1999, Zakamulin 2015, Park & Irwin 2007 |
| Dow Theory adds risk-adjusted value | MEDIUM | Brown et al. 1998 (1 study; Journal of Finance) |
| Elliott Wave Fibonacci ratios are statistically spurious | HIGH | Batchelor & Ramyar 2005 |
| Candlestick patterns work in US large-cap | LOW | Marshall et al. 2006 negative; Caginalp & Laurent 1998 positive; contradictory |
| S/R levels predict intraday reversals in FX | HIGH | Osler 2000, 2003 (mechanistic explanation via order clustering) |

---

## 12. Common Failure Modes and Practitioner Pitfalls

1. **Overfitting the historical chart.** Retrospectively, a pattern can always be identified that "predicted" the move. This is apophenia — the human mind imposes patterns on noise. The Lo et al. (2000) algorithmic approach deliberately removes this subjectivity; manual pattern identification does not.

2. **Ignoring the base rate.** Head-and-shoulders patterns fail ~19% of the time (Bulkowski); symmetrical triangles are nearly coin-flip on both direction and achievement of target. Acting on any single setup without considering base rates inflates expected losses.

3. **Survivorship bias in backtesting.** TA signals tested on stock indices that survived (e.g., DJIA, S&P 500) exclude companies that went bankrupt or were delisted. This inflates backtested returns. Park & Irwin (2007) identify this as a pervasive flaw.

4. **Neglecting transaction costs.** Multiple studies find that strategies which appear profitable on paper disappear after accounting for bid-ask spreads, commissions, and market impact. This effect is larger for higher-frequency strategies.

5. **Confusing statistical significance with economic significance.** A pattern that generates a statistically significant 0.1% edge per trade is economically irrelevant after costs. Malkiel (2003) makes this distinction explicitly.[^46]

6. **Single-indicator decisions.** Every momentum indicator generates false signals in trending markets; every trend-following indicator generates false signals in ranging markets. No indicator works in all regimes.

7. **Post-hoc wave count revision (Elliott Wave).** If wave counts can always be revised after the fact to fit observed price action, the framework is unfalsifiable in practice. Aronson (2007) characterizes this as the primary problem with Elliott Wave.[^36]

8. **Treating all markets as equivalent.** Evidence suggests TA works better in FX, futures, and emerging markets than in developed-market equities. Applying US large-cap TA evidence to EM or FX trading (or vice versa) ignores the most important moderating variable.

---

## References

> Footnote numbers are inherited from `references/technical-analysis.md` and are **not**
> renumbered. The gaps (1-9, 11-18, 20, 23-25) are definitions cited only by §1-§7 and live in
> that file. Footnotes 10, 19, 21 and 22 are cited on both sides of the split and are duplicated
> here deliberately so that every citation in this file resolves locally.

[^10]: Lo, A.W., Mamaysky, H., & Wang, J. (2000). Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation. *Journal of Finance*, 55(4), 1705–1765. DOI: 10.1111/0022-1082.00265. NBER Working Paper 7613. Used nonparametric kernel regression on US stock data 1962–1996; found chart patterns (H&S, double bottoms) provide "incremental information."

[^19]: Park, C.H., & Irwin, S.H. (2007). What Do We Know About the Profitability of Technical Analysis? *Journal of Economic Surveys*, 21(4), 786–826. DOI: 10.1111/j.1467-6419.2007.00519.x. Meta-analysis of 95 modern studies: 56 positive, 20 negative, 19 mixed; identifies pervasive methodological concerns.

[^21]: Brock, W., Lakonishok, J., & LeBaron, B. (1992). Simple Technical Trading Rules and the Stochastic Properties of Stock Returns. *Journal of Finance*, 47(5), 1731–1764. DOI: 10.2307/2328994. Foundational positive TA study; tested MA and trading-range break rules on DJIA 1897–1986; found results inconsistent with four null models.

[^22]: Sullivan, R., Timmermann, A., & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), 1647–1691. DOI: 10.1111/0022-1082.00163. Applied White's Reality Check to TA rules; found no outperformance after data-snooping correction.

[^26]: Granville, J.E. (1963). *Granville's New Key to Stock Market Profits*. Englewood Cliffs, NJ: Prentice-Hall. Primary source for On-Balance Volume. The technique was originally called "continuous volume" by Woods and Vignola.

[^27]: Tsang, W.W.H., & Chong, T.T.L. (2009). Profitability of the On-Balance Volume Indicator. *Economics Bulletin*, 29(3), 2424–2431. Tested OBV in Greater China equity markets (mainland China, Hong Kong, Taiwan); found profitable results. Authors noted "a lack of empirical studies documenting the profitability of volume-based technical indicators."

[^28]: VWAP as institutional execution benchmark. Multiple sources: Corporate Finance Institute; Britannica Money; ScienceDirect — "Improving VWAP strategies: A dynamic volume approach" (2007). ~50% of institutional order flow figure cited in institutional trading research literature.

[^29]: Steidlmayer, J.P. (2003). *Steidlmayer on Markets: Trading with Market Profile* (2nd ed.). Hoboken, NJ: Wiley. Market Profile/Volume Profile origin at CBOT Liquidity Data Bank, introduced 1984.

[^30]: Zaremba, A. et al. (2021). Herding for Profits: Market Breadth and the Cross-Section of Global Equity Returns. *Economic Modelling*. High advance-decline ratio is a robust predictor of future stock returns across developed, emerging, and frontier markets.

[^31]: Hamilton, W.P. (1922). *The Stock Market Barometer*. New York: Harper & Brothers. Rhea, R. (1932). *The Dow Theory*. New York: Barron's. Primary sources systematizing Dow's editorial writings into six tenets.

[^32]: Cowles, A. (1933). Can Stock Market Forecasters Forecast? *Econometrica*, 1(3), 309–324. Foundational test of market forecasting: 45 professional forecasting services, Hamilton's Dow Theory calls 1902–1929; buy-and-hold outperformed Dow Theory in raw returns.

[^33]: Brown, S.J., Goetzmann, W.N., & Kumar, A. (1998). The Dow Theory: William Peter Hamilton's Track Record Re-Considered. *Journal of Finance*, 53(4), 1311–1333. Re-analyzed Hamilton's 255 WSJ editorials; found ~60% directional accuracy and superior risk-adjusted returns vs. buy-and-hold on a volatility-adjusted basis.

[^34]: Elliott, R.N. (1938). *The Wave Principle*. Published as a monograph, August 31, 1938. See also: Prechter, R.R., & Frost, A.J. (1978). *Elliott Wave Principle: Key to Market Behavior*. Gainesville, GA: New Classics Library.

[^35]: Batchelor, R., & Ramyar, R. (2005). Magic Numbers in the Dow. Paper presented at the 25th International Symposium on Forecasting, San Antonio, TX. Tested Fibonacci ratio frequencies in DJIA; found no significant non-random occurrence.

[^36]: Aronson, D.R. (2006/2007). *Evidence-Based Technical Analysis: Applying the Scientific Method and Statistical Inference to Trading Signals*. Hoboken, NJ: Wiley. Applied scientific hypothesis testing to 6,402 technical trading rules on S&P 500 index futures; argued Elliott Wave "as popularly practiced, is not a legitimate theory, but a story."

[^37]: Fama, E.F. (1970). Efficient Capital Markets: A Review of Theory and Empirical Work. *Journal of Finance*, 25(2), 383–417. Defines three forms of market efficiency; weak form directly precludes technical analysis from generating abnormal returns.

[^38]: Fama, E.F. (1991). Efficient Capital Markets: II. *Journal of Finance*, 46(5), 1575–1617. DOI: 10.1111/j.1540-6261.1991.tb04636.x. Updated review; acknowledges return predictability but interprets as rational time-varying expected returns.

[^39]: Bajgrowicz, P., & Scaillet, O. (2012). Technical Trading Revisited: False Discoveries, Persistence Tests, and Transaction Costs. *Journal of Financial Economics*, 106(3), 473–491. Used False Discovery Rate (FDR) controls; found TA profits "completely offset by introduction of low transaction costs."

[^40]: White, H. (2000). A Reality Check for Data Snooping. *Econometrica*, 68(5), 1097–1126. DOI: 10.1111/1468-0262.00152. Formal bootstrap test for whether a superior model exists in a universe of models, accounting for multiple comparisons.

[^41]: Neely, C.J., Rapach, D.E., Tu, J., & Zhou, G. (2014). Forecasting the Equity Risk Premium: The Role of Technical Indicators. *Management Science*, 60(7), 1772–1791. DOI: 10.1287/mnsc.2013.1838. Technical indicators have statistically and economically significant forecasting power for the equity risk premium.

[^42]: Jegadeesh, N., & Titman, S. (1993). Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency. *Journal of Finance*, 48(1), 65–91. Foundational momentum study; winners outperform losers by ~12% per year over 3–12-month horizons, 1965–1989.

[^43]: Moskowitz, T.J., Ooi, Y.H., & Pedersen, L.H. (2012). Time Series Momentum. *Journal of Financial Economics*, 104(2), 228–250. Documents time-series momentum across 58 liquid futures contracts (equity, currency, commodity, bond).

[^44]: Lo, A.W. (2004). The Adaptive Markets Hypothesis: Market Efficiency from an Evolutionary Perspective. *Journal of Portfolio Management*, 30(5), 15–29. DOI: 10.3905/jpm.2004.442611. Proposes AMH reconciling EMH with behavioral alternatives; predicts regime-dependent TA profitability. Extended in: Lo, A.W. (2017). *Adaptive Markets: Financial Evolution at the Speed of Thought*. Princeton University Press.

[^45]: Menkhoff, L. (2010). The Use of Technical Analysis by Fund Managers: International Evidence. *Journal of Banking & Finance*, 34(11), 2573–2586. Survey of 692 fund managers in five countries; 87% place "at least some importance" on TA; no evidence TA use associated with inferior fund managers.

[^46]: Malkiel, B.G. (2003). The Efficient Market Hypothesis and Its Critics. *Journal of Economic Perspectives*, 17(1), 59–82. DOI: 10.1257/089533003321164958. Argues statistical significance does not imply economic significance; documented anomalies disappear once published.
