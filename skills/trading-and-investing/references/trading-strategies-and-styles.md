<!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/trading-strategies-and-styles.md by scripts/persist-spoke.mjs. -->

# Trading Strategies and Styles

> **Educational information only — NOT financial, investment, or trading advice.** Trading carries risk of loss; the large majority of active retail traders lose money. Past strategy performance does not guarantee future results. All volatile claims (statistics, regulatory rules, capital requirements) are stamped **as of 2026**; verify current details before acting.

## Contents

1. [Overview](#overview)
2. [Trading Styles by Time Horizon](#1-trading-styles-by-time-horizon)
3. [Momentum Strategies](#2-momentum-strategies)
4. [Mean-Reversion Strategies](#3-mean-reversion-strategies)
5. [Trend Following and Breakout Trading](#4-trend-following-and-breakout-trading)
6. [Backtesting a Discretionary Strategy](#5-backtesting-a-discretionary-strategy)
7. [Strategy Development Workflow](#6-strategy-development-workflow)
8. [Anti-Patterns Consolidated](#anti-patterns-consolidated)
9. [Cross-References](#cross-references)
10. [References](#references)

---

## Overview

Trading strategy is the ruleset that defines when to enter a position, when to exit, and how large to be. This reference covers the *discretionary and semi-systematic* side of that ruleset — the trader's playbook organized by time horizon and by the two dominant market dynamics any strategy must handle:

- **Trending markets** → momentum and trend-following strategies
- **Range-bound markets** → mean-reversion and pairs-based strategies

For the fully systematic/algorithmic side (execution algorithms, cointegration statistics, market making, factor models), see `references/algorithmic-and-quant-trading.md`.

**Failure base rate (verified-as-of: 2026-06-21)**: A 14-year study of 360,000+ individual traders found only 1% consistently beat the market, only 13% were still trading after 3 years, and fewer than 7% remained active by year 5 [^4][^5]. FINRA data shows 72% of day traders end the year with net losses [^4]. These figures set the context: an edge that survives statistical validation is genuinely rare.

---

## 1. Trading Styles by Time Horizon

### Scalping (seconds to minutes)

Scalpers execute 50–200+ trades per day, targeting gains of 0.05–0.2% per trade. The math is unforgiving: transaction costs must be minimized because the profit margin per trade is tiny. Scalpers typically require **80%+ win rates** to remain profitable given unfavorable risk-reward ratios (often 1:0.5 — risking $1 to make $0.50). The high win rate compensates for a small reward-to-risk ratio [^1][^2].

Key requirements: instruments with narrow bid-ask spreads (tight forex majors, liquid futures, zero-commission liquid equities with actual execution quality), direct access execution (Level 2 quotes, direct routing), and very fast execution infrastructure.

**Common failure mode**: Beginners fail scalping "not because of strategy, but because they ignore transaction costs" — a 0.1% spread in both directions on a 0.15% target profit leaves 0.05% before commissions and slippage [^1].

### Day Trading (intraday — all positions closed before market close)

Day trading avoids overnight gap risk but requires the most active attention and operationally the highest regulatory compliance burden [^3][^6].

**PDT rule (US, as of 2026)**: FINRA's Pattern Day Trader rule was revised. The original fixed-count threshold (4+ day trades within 5 business days required $25,000 minimum account balance in a margin account) was replaced by a risk-based intraday margin framework focused on real exposure rather than trade count [^6]. Many practitioners still recommend $50,000–$100,000 to trade actively while managing risk.

**Day trading failure statistics (verified-as-of: 2026-06-21)** [^4][^5]:
- Only 1% of traders consistently profitable across a 14-year study of 360,000+ traders
- ~13% still trading after 3 years; ~7% after 5 years
- 72% end the year with net losses per FINRA data
- Profitable day traders represent approximately 1.6% of all participants in an average year

### Swing Trading (days to weeks)

Swing traders capture trend "swings" — entering after a pullback in a trending market or at range extremes. The time horizon allows for meaningful risk-reward setups [^7][^8]:
- Standard target: 1:2 minimum risk-reward; strong setups targeting 1:3
- Common win rates: 45–65% depending on setup type
- Stop-losses placed below recent support; profit targets at next resistance or measured-move projections
- Practical size rule: risk 1–2% of account per trade; size the position based on the stop distance

### Position Trading (weeks to months)

Position traders hold through the full lifespan of a macro trend. Unlike buy-and-hold, position traders define a specific catalyst or technical trigger and manage risk with defined stops [^9][^10]:
- Time horizon: 1 month to 2 years
- Require capital sufficient to withstand larger pullbacks than shorter-term traders
- Best suited for major sector rotations, macro trend shifts, or post-breakout thesis trades

### Style Comparison

| Style | Trade Duration | Practical Capital Floor (US) | Win Rate Range | Target Risk-Reward |
|-------|---------------|------------------------------|----------------|-------------------|
| Scalping | Seconds–minutes | Low per trade; execution speed matters most | 80%+ required | 1:0.5 typical |
| Day Trading | Minutes–hours | $25K–$100K (margin account) | 40–55% | 1:1.5–1:2 |
| Swing Trading | Days–weeks | $5K–$25K | 45–65% | 1:2–1:3 |
| Position Trading | Weeks–months | $10K+ | 35–55% | 1:3–1:5+ |

Sources: [^11][^12][^13]

---

## 2. Momentum Strategies

### The Academic Foundation: Jegadeesh-Titman (1993)

Jegadeesh and Titman's landmark paper *"Returns to Buying Winners and Selling Losers"* established cross-sectional momentum as a systematic anomaly [^14][^15][^16]. Strategy construction:
- **Formation period**: prior 3–12 months of returns (12-month is most common)
- **Skip**: exclude the most recent month (the 12-1 strategy) to avoid the 1-month reversal from bid-ask bounce
- **Universe**: rank all stocks; buy top decile (past winners), short bottom decile (past losers)
- **Holding period**: 3–12 months

Results across all 16 tested combinations of formation/holding periods: approximately **1% per month** in excess return from the Winner Minus Loser (WML) portfolio.

A 2022 review covering 30 years of post-publication evidence confirmed: momentum remains "perhaps the most pervasive contradiction of the efficient market hypothesis," robust across asset classes, geographies, and time periods [^15].

### Cross-Sectional vs. Time-Series Momentum

**Cross-sectional (relative) momentum**: Ranks securities against each other. Long the top cohort, short the bottom cohort. Does not require any particular absolute market direction — a stock is "momentum" if it outperformed its peers, even in a down market.

**Time-series / absolute momentum** (Moskowitz, Ooi & Pedersen, 2012): Compares each security's return to its own past. If a security's 12-month return is positive, go long; if negative, go to cash or short. Tested across 58 futures markets with documented Sharpe ratios in excess of 1.0. Unlike cross-sectional momentum, it exits the asset class entirely during bad periods, providing crash protection [^17][^18].

**Dual Momentum** (Antonacci): Combines both — first use absolute momentum to decide whether to be in risk assets at all (if equities have negative 12-month absolute momentum, hold T-bills instead), then use relative momentum to pick between risk assets. Backtested to 1974, showing improved Sharpe and dramatically lower drawdowns versus buy-and-hold [^17][^18].

Evidence for momentum is exceptional: documented back to 1801 in equities (Geczy & Samonov 2015) and across commodities since 1223 (Greyserman & Kaminski 2014).

### Momentum Crashes: The Critical Risk

Daniel and Moskowitz (2016) documented that momentum strategies experience infrequent but severe **crash events** — periods of persistent large negative returns [^19][^20].

**Mechanism**: Momentum strategies implicitly short out-of-the-money options on market recovery. After a severe market decline, past losers (the short leg) are like deeply distressed options. When markets rebound sharply, these losers can surge 20–50%+ while past winners stagnate, generating massive losses on the short side.

**Crash conditions**:
- Following large market declines (panic states)
- When market volatility is elevated
- During sharp, V-shaped market reversals
- After bear markets end

**Historical examples**: 2001–2002 recovery; Spring–Summer 2009 (momentum strategies lost 60–80% in some implementations).

**Mitigation**: A dynamic strategy that forecasts momentum's conditional mean and variance can reduce exposure before predicted crashes — this approach nearly doubles the Sharpe ratio relative to static momentum [^19].

### Anti-Patterns in Momentum Trading

- Running momentum in isolation without crash hedging or volatility scaling
- Using less than 6-month lookback (too noisy) or more than 12-month (too slow to signal)
- Ignoring the 1-month reversal effect — always skip the most recent month in the formation period
- Trading momentum in illiquid stocks where execution costs eliminate the premium
- Crowding: momentum strategies use similar methodology; over-owned names amplify crashes when funds unwind simultaneously [^20][^21]

---

## 3. Mean-Reversion Strategies

### Core Concept

Mean reversion assumes that prices exhibiting extreme deviations from their historical average will return to that average. The strategy family includes range trading, Bollinger Band strategies, oversold/overbought systems, and spread/pairs trading [^22][^23].

**The regime dependency problem**: Mean reversion works only in range-bound markets. In a sustained trend, "oversold" can become more oversold for weeks. Misidentifying a trending market as a ranging one is the primary failure mode. ADX > 25 indicates a trending market (where mean-reversion logic fails); ADX < 20 suggests a ranging market (where it thrives) [^26].

### Bollinger Band Mean Reversion

Bollinger Bands (20-period moving average ± 2 standard deviations) create a dynamic envelope [^23]:
- Price touching the **lower band**: signals oversold conditions; potential long entry
- Price touching the **upper band**: signals overbought conditions; potential short entry
- **Band squeeze** (bands narrowing): indicates low volatility; often precedes a breakout rather than continued mean reversion

**Signal quality rule**: Mean-reversion signals on Bollinger Band touches are far less reliable when price is in a sustained trend. The touch is a trend-continuation signal, not a reversal signal.

### Pairs Mean-Reversion and Cointegration

For pairs/spread trading (the quantitative version), see `references/algorithmic-and-quant-trading.md` §3. The core distinction:
- **Correlation** ≠ **Cointegration**: Two securities can move together (correlation) without maintaining a stable long-run relationship. Pairs trading requires cointegration — a stationary linear combination of price series.
- **Z-score thresholds**: Enter at ±2.0 standard deviations; exit at 0 or ±0.5; stop-loss at ±3.0 (divergence beyond 3σ is more likely regime change than opportunity) [^24][^25]

### Half-Life of Mean Reversion

The Ornstein-Uhlenbeck process models mean-reverting series and yields a **half-life** parameter: the expected time for the spread to revert halfway to its mean [^24][^25]:
- Set maximum hold period at 2–3× the half-life
- Example: half-life of 5 days → exit position at 10–15 days maximum regardless of status
- Half-life over 30 days → the series may not be mean-reverting in any tradeable sense

### When Mean Reversion Fails

1. **Trending markets**: RSI can remain overbought for weeks in a strong uptrend. The "overbought" reading is a trend-continuation indicator, not a reversal signal.

2. **Regime change**: When a market transitions from range-bound to trending, the mean itself shifts. Shorting "overbought" in a secular bull market produces compounding losses.

3. **Asymmetric P&L profile**: Mean-reversion strategies often show 60–80% win rates — attractive-looking — but hide rare catastrophic losing trades when the mean shifts permanently. This profile is characterized as "picking up nickels in front of a steamroller" [^26].

4. **Cointegration breakdown**: Historically correlated pairs can decouple permanently due to mergers, regulatory changes, or business-model divergence. The 2008 financial crisis broke many historically stable pairs [^26][^27].

---

## 4. Trend Following and Breakout Trading

### The Evidence Base: A Century of Trend-Following Returns

AQR's landmark paper *"A Century of Evidence on Trend-Following Investing"* (Hurst, Ooi & Pedersen, 2017) studied 67 markets across 4 asset classes from January 1880 to December 2016 [^28][^29]:
- **Every decade since 1880** produced positive average returns from time-series momentum
- Performed well in **8 of 10 largest 60/40 portfolio drawdowns**
- Works across recessions/booms, war/peacetime, high/low inflation, high/low interest rates
- Low correlation to traditional asset classes — a genuine portfolio diversifier

### The Turtle Trading Rules (1983–1988)

Richard Dennis's experiment proved systematic trend-following could be taught from first principles. The rules (now public) [^30][^31][^32]:

**System 1** (shorter-term): Enter on a **20-day Donchian channel breakout** (new 20-day high or low). Skip if the previous System 1 signal in the same direction was a winner.

**System 2** (longer-term): Enter on a **55-day Donchian channel breakout**.

**Position sizing**: Size in **ATR units** — each unit risks approximately 1% of account per ATR of price movement. Add up to 4 units, adding at ½ ATR intervals as the trade moves favorably.

**Stops**: **2 ATR from entry** for all positions.

**Exits**: System 1 exits on a 10-day *opposite* breakout; System 2 exits on a 20-day opposite breakout.

Performance characteristics: **30–35% win rates** — most trades are small losses from false breakouts. Large winners cover all losses. The original Turtles reportedly returned $175M over 5 years at 80%+ annual compounding. Practically: missing even a handful of big trends per year can ruin annual performance. This is the "all or nothing" nature of trend-following.

### ATR-Based Entry and Breakout Confirmation

ATR (Average True Range) provides a volatility-normalized unit for execution [^33][^34]:
- **Stop placement**: 1.5–2 ATR below entry (long) / above entry (short)
- **Breakout confirmation**: require the breakout candle body to exceed 70% of its range (filters wicks-only breakouts)
- **Position sizing**: target dollar risk = 1 ATR × shares = fixed percentage of account (typically 1%)

**Reducing false breakouts**:
- The **two-candle rule**: require two consecutive closes beyond the breakout level — eliminates most single-candle fakeouts
- Higher timeframes (4H, daily) produce more reliable breakouts with lower false-signal rates than intraday
- Volume confirmation: a genuine breakout typically shows above-average volume at the breakout candle

### Trend Following in Futures vs. Equities

Original Turtle rules targeted diversified futures: currencies, US Treasuries, metals, crude oil, grains — 20–24 liquid markets. Futures advantages for trend-following:
- Inherent leverage (capital efficiency)
- No uptick rule for shorts
- No borrowing costs
- Lower transaction costs at institutional scale
- Macro trend exposure (rates, currencies, commodities) uncorrelated to equities

**In equities**: Pure trend-following on individual stocks is harder due to survivorship bias in backtests and the equity drift bias (markets trend upward overall, so short signals are systematically disadvantaged). **Cross-sectional momentum** (buying top decile by trailing return, shorting bottom decile) is the more robust equity adaptation.

### When Trend Following Fails

- **Choppy, range-bound markets**: Trend systems get whipsawed — entering on breakouts that immediately reverse. Multiple whipsaws in succession create extended drawdowns.
- **V-shaped recoveries**: The system misses the initial rally leg by design (needs the trend to establish), then enters late and gets stopped out on consolidation.
- **Post-GFC period (2009–2013)**: The SG Trend Index returned −1.8% over 5 years as central bank rate suppression removed macro trends in rates and currencies.
- **"Year of the whipsaw" (2023)**: Multiple asset classes produced repeated false breakouts; trend systems underperformed after three strong years (2020–2022) [^35][^36].
- **Structural reality**: Trend-following underperformed the S&P 500 in roughly half of all years historically. Its value is crash protection and low correlation, not consistent equity-beating returns.

---

## Anti-Patterns Consolidated

| Anti-Pattern | Domain | Consequence |
|---|---|---|
| Trading mean-reversion signals in a trending market | Mean reversion | Systematic losses; "overbought" is a trend-continuation signal in a trend |
| "Feels strong" rules not translated to explicit if-then logic | All discretionary | Unreplicable backtest; no measurable edge |
| Testing on survivorship-biased universe (current members only) | Backtesting | Inflated backtest returns; live underperformance |
| Look-ahead bias in signal generation | Backtesting | Real-world performance fails to replicate |
| Evaluating win rate without risk-reward ratio | All styles | High win rate can be a losing strategy |
| Running momentum without crash protection | Momentum | 50–80% drawdowns in V-recovery environments |
| Ignoring transaction costs at the strategy's actual trade frequency | All styles | Edge destroyed by slippage + commissions |
| Applying trend-following to choppy range-bound markets | Trend following | Whipsaws destroy capital in repeated small losses |
| Confusing correlation with cointegration in pairs trading | Pairs/mean reversion | Spread diverges indefinitely; large losses on "convergence" entries |
| Modifying rules after observing OOS results | Backtesting | OOS test contaminated; data snooping re-enters |
| Portfolio-building without measuring inter-strategy correlation | Strategy portfolio | "Diversified" strategies correlated at worst moments |
| Backtesting on <100 trades | All styles | Results statistically unreliable; any outcome is possible by chance |
| Assuming alpha is permanent once found | Strategy lifecycle | Edge decays as competitors discover and arbitrage the same pattern |

---

## Cross-References

- **Algorithmic and quant trading** (execution algorithms TWAP/VWAP/IS/POV, cointegration math, market making, quant research pipeline, factor models) → `references/algorithmic-and-quant-trading.md` (sister spoke — shares backtesting methodology foundation)
- **Technical analysis** (indicator mechanics — RSI, MACD, moving averages, chart patterns at depth) → `references/technical-analysis.md` (planned spoke)
- **Order lifecycle and execution** (how a retail order reaches the market; PFOF, slippage, execution quality) → `references/order-lifecycle-and-execution.md`
- **Investing vs. trading** (evidence on active trader underperformance, time horizon and goal distinctions) → `references/investing-vs-trading.md`
- **Statistical methodology** (IC, walk-forward analysis, Deflated Sharpe, FDR correction mechanics) → `da-analytical-methods` hub

---

## Moved sections

The sections below were split out on 2026-08-05 to stay under the reference size ceiling. Numbering is preserved.

| Section | Now lives in | Covers |
|---|---|---|
| **§5 Backtesting a Discretionary Strategy** | `references/strategy-backtesting-and-development-workflow.md` | Sample construction, in-sample vs out-of-sample, walk-forward, cost modelling, and which metrics flatter a strategy. |
| **§6 Strategy Development Workflow** | `references/strategy-backtesting-and-development-workflow.md` | Hypothesis → build → validate → size → monitor, and where the process usually breaks. |

## References

[^1]: [Pepperstone: Scalping Trading Guide](https://pepperstone.com/en/learn-to-trade/trading-guides/scalping-trading/) — scalping mechanics, win rate requirements | educational | verified: 2026-06-21
[^11]: [Equiti: Compare Trading Styles — Day, Swing, and Position](https://www.equiti.com/sc-en/education/trading-strategies/compare-trading-styles-day-swing-and-position-trading/) — style comparison table | educational | verified: 2026-06-21
[^12]: [EdgeWonk: Choosing the Right Trading Style](https://edgewonk.com/blog/choosing-the-right-trading-style-day-trading-swing-trading-scalping-or-investing) — style selection framework | educational | verified: 2026-06-21
[^13]: [Admiral Markets: Style Comparison](https://admiralmarkets.com/education/articles/forex-strategy/scalping-vs-day-trading-vs-swing-trading) — capital and win rate survey | educational | verified: 2026-06-21
[^14]: [Jegadeesh-Titman 1993 / Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x) — original momentum paper | academic paper (seminal) | verified: 2026-06-21
[^15]: [Springer Nature: Returns to Buying Winners — 30 Years Later](https://link.springer.com/article/10.1007/s11408-022-00417-8) — 30-year post-publication review | academic paper | verified: 2026-06-21
[^16]: [SSRN: Jegadeesh-Titman Momentum](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=227349) — working paper version | academic paper | verified: 2026-06-21
[^17]: [Robot Wealth: Dual Momentum Review](https://robotwealth.com/dual-momentum-review/) — Antonacci dual momentum, absolute + relative | practitioner blog | verified: 2026-06-21
[^18]: [Optimal Momentum (Antonacci)](https://www.optimalmomentum.com/) — dual momentum methodology | practitioner reference | verified: 2026-06-21
[^19]: [NBER w20439: Daniel-Moskowitz Momentum Crashes](https://www.nber.org/papers/w20439) | [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0304405X16301490) — momentum crash anatomy, dynamic hedge | academic paper | verified: 2026-06-21
[^2]: [TMGM: Scalping Trading Strategy](https://www.tmgm.com/en/academy/trading-academy/scalping-trading-strategy) — scalping setup and cost considerations | practitioner blog | verified: 2026-06-21
[^20]: [AQR: Fact, Fiction, and Momentum Investing](https://www.aqr.com/-/media/AQR/Documents/Journal-Articles/JPM-Fact-Fiction-and-Momentum-Investing.pdf) — practical realities, crowding | practitioner paper | verified: 2026-06-21
[^21]: [Tandfonline: Crowding in Alternative Risk Premia](https://www.tandfonline.com/doi/full/10.1080/0015198X.2019.1600955) — crowding empirics and divergence premia | academic paper | verified: 2026-06-21
[^22]: [QuantInsti: Mean Reversion Strategies — Introduction and Building Blocks](https://blog.quantinsti.com/mean-reversion-strategies-introduction-building-blocks/) — mean reversion overview | educational | verified: 2026-06-21
[^23]: [CrossTrade: Bollinger Band Mean Reversion](https://crosstrade.io/learn/trading-strategies/bollinger-mean-reversion) — Bollinger Band mechanics | educational | verified: 2026-06-21
[^24]: [QuantVero: Mean Reversion Strategy Build and Test](https://www.quantvero.com/algo-trading/mean-reversion-trading-strategy/) — half-life, OU process | practitioner blog | verified: 2026-06-21
[^25]: [IBKR Quant News: Mean Reversion Strategies — Part I](https://www.interactivebrokers.com/campus/ibkr-quant-news/mean-reversion-strategies-introduction-trading-strategies-and-more-part-i/) — pairs mechanics, half-life | practitioner/educational | verified: 2026-06-21
[^26]: [HeyGoTrade: Mean Reversion in Trading](https://www.heygotrade.com/en/blog/mean-reversion-in-trading/) | [Quantum Algo: Mean Reversion Complete Guide](https://www.quantum-algo.com/blog/guides/mean-reversion-trading-complete-guide/) — regime failure modes | educational | verified: 2026-06-21
[^27]: [ForexTester: Mean Reversion Trading](https://forextester.com/blog/mean-reversion-trading/) — cointegration breakdown examples | practitioner blog | verified: 2026-06-21
[^28]: [AQR: A Century of Evidence on Trend-Following Investing](https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing) | [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026) — Hurst/Ooi/Pedersen 2017; 136 years of data | academic paper | verified: 2026-06-21
[^3]: [Admiral Markets: Scalping vs Day Trading vs Swing Trading](https://admiralmarkets.com/education/articles/forex-strategy/scalping-vs-day-trading-vs-swing-trading) — style comparison | educational | verified: 2026-06-21
[^30]: [Zaye Capital Markets: Turtle Trading Strategy](https://zayecapitalmarkets.com/turtle-trading-strategy/) — original Turtle rules walkthrough | educational | verified: 2026-06-21
[^31]: [Alchemy Markets: Turtle Trading Guide](https://alchemymarkets.com/education/strategies/turtle-trading-guide/) — Turtle system 1 and 2 mechanics | educational | verified: 2026-06-21
[^33]: [LuxAlgo: False Breakout Strategies for Traders](https://www.luxalgo.com/blog/5-false-breakout-strategies-for-traders/) — breakout confirmation, ATR | educational | verified: 2026-06-21
[^35]: [Man Group: Is This Time Different — Trend Following](https://www.man.com/insights/is-this-time-different) — trend following drawdowns and recovery | asset manager research | verified: 2026-06-21
[^36]: [TiltFolio: When Trend Following Underperforms](https://www.tiltfolio.com/insights/when-trend-following-underperforms/) | [Top Traders Unplugged: December 2023 Performance Report](https://www.toptradersunplugged.com/trend-following-performance-report-december-2023/) — whipsaws 2023, post-GFC | practitioner research | verified: 2026-06-21
[^4]: [Vetted Prop Firms: What Percentage of Day Traders Lose Money](https://vettedpropfirms.com/what-percentage-of-day-traders-lose-money/) — 14-year study, 360K+ traders | practitioner research | verified: 2026-06-21
[^5]: [Bookmap: Why Most Day Traders Lose Money and What Winners Do Differently](https://bookmap.com/blog/why-most-day-traders-lose-money-and-what-the-winners-do-differently) — failure statistics, patterns | practitioner blog | verified: 2026-06-21
[^6]: [NerdWallet: Pattern Day Trader Rule Change 2026](https://www.nerdwallet.com/investing/news/pattern-day-trading-rule-change) | [Britannica Money: Pattern Day Trader Rule](https://www.britannica.com/money/pattern-day-trader-rule) — PDT rule mechanics | financial education | verified: 2026-06-21
[^7]: [Elearnmarkets: Essential Elements of Swing Trading](https://www.elearnmarkets.com/school/units/swing-trading/essential-elements-of-swing-trading) — entries, exits, risk-reward | educational | verified: 2026-06-21
[^9]: [HeyGoTrade: What Is Position Trading Strategy](https://www.heygotrade.com/en/blog/what-is-position-trading-strategy/) — position trading overview | educational | verified: 2026-06-21
