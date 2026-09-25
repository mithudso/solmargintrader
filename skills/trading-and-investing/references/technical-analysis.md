---
name: technical-analysis
description: >-
  Hub reference for the technical-analysis spoke of trading-and-investing — the price-chart half (§1-§7). Covers chart types (candlestick/OHLC/line), trend analysis, trendlines and channels, support/resistance and the polarity principle (Osler), candlestick patterns, chart patterns (head-and-shoulders, double top/bottom, rounding, triangles, flags, pennants, wedges), and the price-derived indicators (RSI, MACD, stochastics, SMA/EMA, golden/death cross, Bollinger Bands, ATR). Volume and breadth indicators (OBV, VWAP, Volume Profile, A/D line, McClellan, Zweig), Dow Theory, Elliott Wave, multi-timeframe analysis, the empirical evidence base (Fama/EMH, BLL 1992, Park & Irwin 2007, Lo et al. 2000, Adaptive Market Hypothesis) and the practitioner failure modes are §8-§12 in references/technical-analysis-breadth-frameworks-and-evidence.md. Educational only — NOT trading advice.
version: "1.1.0"
updated: "2026-08-04"
category: hub-reference
hub: trading-and-investing
spoke: technical-analysis
verified-as-of: "2026-06-21"
metadata:
  changelog:
    - "2026-08-04 SPLIT v1.0.0->v1.1.0 — file was ~15.6k tokens (~1.6x the ~10k reference ceiling). §8-§12 (volume & breadth indicators, Dow Theory & Elliott Wave, multi-timeframe analysis & signal combination, empirical evidence, common failure modes) moved verbatim to references/technical-analysis-breadth-frameworks-and-evidence.md; §1-§7 (chart types, trend/support-resistance, candlestick patterns, chart patterns, momentum oscillators, trend & volatility indicators) stay here. No content condensed, reworded or dropped. Section numbering unchanged across both files; footnotes 26-46 moved and footnotes 10, 19, 21, 22 duplicated so every citation resolves within its own file. Description, keywords and tags trimmed to the retained scope; three internal §-references in §2 repointed at the sibling file."
keywords:
  - technical-analysis
  - candlestick-patterns
  - chart-patterns
  - support-resistance
  - price-action
  - RSI
  - MACD
  - Bollinger-Bands
  - moving-averages
  - trend-analysis
  - ATR
  - stochastics
tags:
  - trading
  - technical-analysis
  - chart-patterns
  - indicators
  - price-action
---

# Technical Analysis

> **Hub reference** — part of `trading-and-investing`. Covers §1-§7 of the `technical-analysis` spoke.
> **Educational only — NOT financial, investment, or trading advice. Trading carries risk of loss.**
> verified-as-of: 2026-06-21

Technical analysis (TA) is the study of past price and volume data to forecast future price direction. Unlike fundamental analysis (which examines a company's financial condition), TA operates on the premise that all fundamental information is already reflected in price and that price history contains exploitable patterns. This file covers §1-§7: chart types, trend analysis, support/resistance, candlestick patterns, major chart patterns, and the price-derived indicators. The rest of the spoke — volume/breadth indicators, the classical frameworks (Dow Theory, Elliott Wave), multi-timeframe analysis, the empirical evidence for and against TA effectiveness, and the common practitioner failure modes — is §8-§12 in `references/technical-analysis-breadth-frameworks-and-evidence.md`.

## Contents

1. [Chart Types](#1-chart-types)
2. [Trend Analysis and Support/Resistance](#2-trend-analysis-and-supportresistance)
3. [Candlestick Patterns](#3-candlestick-patterns)
4. [Chart Patterns — Reversals](#4-chart-patterns--reversals)
5. [Chart Patterns — Continuations](#5-chart-patterns--continuations)
6. [Key Indicators — Momentum Oscillators](#6-key-indicators--momentum-oscillators)
7. [Key Indicators — Trend and Volatility](#7-key-indicators--trend-and-volatility)
8. [§8-§12 — moved to the breadth/frameworks/evidence file](#8-12--moved-to-technical-analysis-breadth-frameworks-and-evidencemd)
9. [References](#references)

---

## 1. Chart Types

Three chart types dominate TA practice. Each represents the same underlying data differently.

### Line Chart
Plots only closing prices connected by a line. Simplest form; loses intraday range information. Useful for identifying long-term trend direction; hides noise.

### OHLC Bar Chart
Each vertical bar encodes four data points:
- **O**pen: short tick extending left
- **H**igh: top of vertical bar
- **L**ow: bottom of vertical bar
- **C**lose: short tick extending right

Bar width (time) is determined by the chart's period setting (daily, weekly, hourly, etc.).

### Candlestick Chart
Same four data points as OHLC, presented as a filled or hollow body plus wicks ("shadows"):
- **Body**: open-to-close range. Hollow/white or green = close above open (bullish). Filled/black or red = close below open (bearish).
- **Upper shadow**: high above the body.
- **Lower shadow**: low below the body.

Candlestick charts originated in 18th-century Japanese rice trading; introduced to Western audiences by Steve Nison in *Japanese Candlestick Charting Techniques* (1991).[^1] They are now the dominant chart type for short-to-medium-term analysis.

---

## 2. Trend Analysis and Support/Resistance

### Trend Definition
A trend is a directional price tendency over time. Dow Theory (see §9 in `references/technical-analysis-breadth-frameworks-and-evidence.md`) recognizes three scales:
- **Primary** (months to years): the major bull or bear market
- **Secondary** (weeks to months): corrective moves within the primary trend
- **Minor** (days): noise within secondary moves

### Trendlines
- **Uptrend line**: Drawn by connecting successive higher lows. A minimum of two lows required to draw the line; three touches validates it.
- **Downtrend line**: Connects successive lower highs.
- **Channel**: A parallel line drawn at the same angle as the trendline, shifted to connect highs (in an uptrend) or lows (in a downtrend).

A breakout through a trendline on high volume is a reversal signal; a pullback retest of the broken line can offer an entry.

### Support and Resistance

**Support** is a price level where buying interest is sufficient to halt further decline. **Resistance** is a level where selling pressure prevents further advance.

Sources of support/resistance:
- Prior price highs and lows (the market's "memory")
- Round numbers (prices ending in 00 or 50 — order clustering around these numbers is documented)
- Moving averages (especially the 50- and 200-day MAs, which institutions monitor)
- Prior high-volume nodes (see Volume Profile, §8 in `references/technical-analysis-breadth-frameworks-and-evidence.md`)

**The polarity principle** (Murphy): once a support level is decisively broken, it typically becomes resistance on any subsequent rally, and vice versa.[^2] This role reversal is widely accepted by practitioners and is backed by the FRBNY order-flow research of Osler (2003): stop-loss orders cluster just below support and take-profit orders cluster just above resistance, creating a mechanical self-reinforcing effect.[^3]

**Academic evidence (FX markets):** Osler (2000) used support/resistance levels provided by six FX market firms and found strong evidence that these levels predict intraday trend interruptions in currency markets.[^4] Osler (2003) documented the order-clustering mechanism in USD/JPY, USD/GBP, and EUR/USD.[^3]

**Academic evidence (equities):** Positive but weaker and time-decaying — horizontal resistance levels showed positive excess returns in early periods, declining toward zero in more recent data.[^5] Consistent with the Adaptive Market Hypothesis (§11 in `references/technical-analysis-breadth-frameworks-and-evidence.md`).

---

## 3. Candlestick Patterns

Candlestick patterns use one to five candles to signal potential reversals or continuations. **All require trend context** — the same candle shape means different things in an uptrend vs. a downtrend.

### Single-Candle Patterns

| Pattern | Description | Signal |
|---|---|---|
| **Doji** | Open ≈ Close; cross-shaped. Indecision between bulls and bears. | Potential reversal when at extremes; confirms with next candle |
| **Hammer** | Small body near top, long lower shadow (≥2× body), little/no upper shadow. In downtrend. | Bullish reversal |
| **Hanging Man** | Same visual as hammer but in uptrend. | Bearish reversal |
| **Shooting Star** | Small body near bottom, long upper shadow. In uptrend. | Bearish reversal |
| **Inverted Hammer** | Small body near top, long upper shadow. In downtrend. | Potentially bullish reversal (confirm required) |

### Two-Candle Patterns

| Pattern | Description | Signal |
|---|---|---|
| **Bullish Engulfing** | White/green candle body completely envelops prior black/red body in downtrend | Bullish reversal |
| **Bearish Engulfing** | Black/red candle completely envelops prior white/green body in uptrend | Bearish reversal |
| **Harami** | Small candle contained within the body of the prior large candle | Reversal warning (weaker) |

### Three-Candle Patterns

| Pattern | Description | Signal |
|---|---|---|
| **Morning Star** | Large bearish candle → small-body candle (gap down) → large bullish candle (closes into first candle's body) | Strong bullish reversal |
| **Evening Star** | Mirror of Morning Star | Strong bearish reversal |
| **Three White Soldiers** | Three consecutive strong bullish candles, each opening within prior body | Strong bullish trend confirmation |
| **Three Black Crows** | Three consecutive bearish candles | Strong bearish trend confirmation |

### Empirical Evidence on Candlestick Patterns

Results are genuinely mixed and market-specific:

**Positive evidence:** Caginalp & Laurent (1998) tested 8 three-day reversal patterns on all S&P 500 stocks from 1992–1996 and found statistical significance at 36 standard deviations from the null; ~1% average profit over a 2-day holding period.[^6] Goo, Chen & Chang (2007) found strong support in Taiwanese stocks.[^7]

**Negative evidence (US large-cap):** Marshall, Young & Rose (2006) tested candlestick strategies on DJIA component stocks (1992–2002) using randomly generated OHLC comparison series and found candlestick strategies "do not have value" for these stocks — no statistically significant excess returns.[^8]

**Interpretation:** The market efficiency of the target is the key moderating variable. Candlestick evidence is stronger in less-efficient emerging/Asian markets and weaker in US large-cap equities. For US stocks, candlestick patterns are best treated as one signal among many, not a standalone strategy.

---

## 4. Chart Patterns — Reversals

Reversal patterns signal that a prior trend is ending and a new trend in the opposite direction is beginning.

### Head-and-Shoulders (H&S) Top

The most studied reversal pattern. Structure:
1. **Left shoulder**: rally to a high, then decline
2. **Head**: rally above the prior high (new high), then decline
3. **Right shoulder**: rally that fails to reach the head, then decline
4. **Neckline**: a line drawn through the two intervening lows (between shoulders and head). May slope up or down.

**Confirmation**: Close below the neckline (on high volume ideally). Without a neckline break, the pattern is not confirmed.

**Price target** (measure rule): Project the distance from the head to the neckline downward from the breakout point.

**Inverse/Bottom H&S**: Mirror image; signals a bullish reversal.

**Practitioner statistics (Bulkowski, Encyclopedia of Chart Patterns):** H&S Top has a 19% break-even failure rate; ~51% achieve the measured-move price target; average post-breakout decline ~16%; 68% experience a pullback to the neckline after breakout.[^9]

**Academic evidence:** Lo, Mamaysky & Wang (2000) used nonparametric kernel regression on US stocks from 1962–1996 and found head-and-shoulders (and inverse H&S) "provide incremental information" — conditional return distributions differ significantly from unconditional.[^10] Savin, Weller & Zvingelis (2007) found risk-adjusted excess returns of 5–7% per year when H&S is used as a conditional filter (not a standalone strategy) on S&P 500 and Russell 2000 from 1990–1999.[^11]

### Double Top and Double Bottom

**Double Top ("M")**: Price tests the same resistance level twice, fails both times, then declines through the intermediate trough (confirmation point). Bearish reversal.

**Double Bottom ("W")**: Mirror image — tests the same support level twice, then rallies through the intermediate peak. Bullish reversal.

**Price target**: Height of the pattern projected from the confirmation point.

Lo et al. (2000) specifically found double-bottoms provide incremental information.[^10] Friesen, Weller & Dunham (2009) developed a behavioral model showing confirmation bias in traders mechanically generates double-top and H&S shapes in prices.[^12]

### Rounding Top and Bottom (Saucer)

A gradual curved reversal — price rounds over a period of months. Volume typically mirrors the pattern (heavy → declining → heavy). Relatively rare; when it appears, the subsequent move is often powerful. No widely cited academic study on rounding tops/bottoms specifically.

---

## 5. Chart Patterns — Continuations

Continuation patterns represent pauses within an existing trend — temporary consolidations before the trend resumes.

### Triangles

All triangles form as price contracts into a narrowing range bounded by two converging trendlines. Volume typically declines as the triangle forms and surges on breakout.

| Type | Upper Line | Lower Line | Typical Breakout |
|---|---|---|---|
| **Ascending** | Flat (horizontal resistance) | Rising (higher lows) | Upward (bullish continuation) |
| **Descending** | Declining (lower highs) | Flat (horizontal support) | Downward (bearish continuation) |
| **Symmetrical** ("Coil") | Declining | Rising | Either direction; usually continues prior trend |

Murphy's rule: breakout from a symmetrical triangle typically occurs about 2/3 of the way to the apex.[^2]

**Caution (Bulkowski):** Symmetrical triangles rank near the bottom of all patterns for performance (rank 36 of 39 upward; 34 of 36 downward). Ascending triangles perform better (upward breakouts: avg. +43% move, 70% hit price target) but "descending triangle performance has dropped substantially since the 1990s" — consistent with markets adapting.[^9]

### Flags and Pennants

Both form after a sharp directional move ("flagpole") and represent brief consolidations before the trend resumes:

- **Flag**: A short rectangular consolidation channel, parallel lines sloping *against* the prior trend. Volume declines during the flag, surges on breakout.
- **Pennant**: A small symmetrical triangle rather than a parallel channel — converging trendlines. Same volume pattern.

Both are continuation signals. Price target: the flagpole length projected from the breakout.

Bulkowski's measured move statistics for flags use a shorter-term measurement basis than other patterns (~9% average, ~46% target achievement, ~44% failure rate).[^9] Leigh et al. (2002) found positive excess returns from bull flag recognition on the NYSE Composite.[^13]

### Rising and Falling Wedges

Two trendlines **both sloping in the same direction** (unlike symmetrical triangles where they converge from opposite directions):

- **Rising Wedge**: Both lines slope upward, narrowing range. In an uptrend = bearish reversal. In a downtrend = bearish continuation.
- **Falling Wedge**: Both lines slope downward. In a downtrend = bullish reversal. In an uptrend = bullish continuation.

Volume typically declines throughout the wedge. No dedicated academic study on wedge patterns found in the literature.

---

## 6. Key Indicators — Momentum Oscillators

### RSI — Relative Strength Index

**Creator:** J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978).[^14]

**Formula:**
```
RSI = 100 − [100 / (1 + RS)]

where RS = Average Gain / Average Loss
  (using Wilder's smoothing over 14 periods)

First Average Gain = Sum of gains over first 14 periods ÷ 14
Subsequent Average Gain = (Prior Avg Gain × 13 + Current Gain) ÷ 14
[same for Average Loss]
```

**Standard parameters:** 14-period lookback; **overbought ≥ 70**; **oversold ≤ 30**. Shorter periods (9–10) increase sensitivity; longer periods (20–21) smooth the signal.

**What RSI signals:**
- Momentum: how rapidly price is moving and whether that pace is likely to continue
- **Overbought/oversold** interpretation: above 70 / below 30 signals extreme momentum (possible mean-reversion). **Important caveat:** In strong trends, RSI can remain overbought or oversold for extended periods without reversing.
- **Divergence** (more reliable): Price makes a new high while RSI makes a lower high (bearish divergence); price makes a new low while RSI makes a higher low (bullish divergence).
- RSI crossing the 50 line: trend direction signal (above 50 = bullish, below 50 = bearish).

**Academic evidence:** Marek & Šedivá (2017) found RSI can produce gains over short periods but "in longer time it is usually overcome by simple buy-and-hold strategy."[^15] One academic reframing argues RSI more accurately reflects *trend persistence* than imminent reversal — the overbought/oversold interpretation may misread RSI's actual behavior in trending markets.[^16]

---

### MACD — Moving Average Convergence Divergence

**Creator:** Gerald Appel, developed ~1977, published 1979 in *The Moving Average Convergence-Divergence Trading Method*. The MACD histogram was added by Thomas Aspray in 1986.[^17]

**Formula:**
```
MACD Line   = EMA(12) − EMA(26)    [of closing prices]
Signal Line = EMA(9) of MACD Line
Histogram   = MACD Line − Signal Line
```

**Standard parameters:** 12/26/9. Note: these periods were designed for a 6-day trading week (12 ≈ 2 weeks; 26 ≈ 1 month); they persisted unchanged into today's 5-day week.

**What each component signals:**
- **MACD Line**: Relationship between short-term and longer-term momentum. Above zero = short-term EMA above long-term EMA (bullish). Below zero = bearish.
- **Signal Line**: Smoothed version of MACD. Primary trade signal: MACD Line crossing above Signal Line = bullish; crossing below = bearish.
- **Histogram**: Visual representation of the spread. Expanding histogram = momentum building; shrinking = fading momentum. Histogram crossing zero = same signal as the line crossover.
- **Divergence**: As with RSI, MACD divergence from price action (especially in the histogram) is regarded by practitioners as a stronger signal than crossovers.

**Academic evidence:** A 2022 study of US markets (DJIA, Nasdaq, S&P 500) from 2015–2021 found MACD alone has a win rate below 50%.[^18] MACD shows stronger evidence in emerging markets and weaker/declining evidence in developed equity markets — the pattern Park & Irwin (2007) identified across technical indicators generally.[^19]

---

### Stochastic Oscillator

**Creator:** George C. Lane (~1957, at Investment Educators in Chicago; published 1960 in *How to Make Money in Commodities*).[^20]

**Formula (Fast Stochastics):**
```
%K = [(Close − Lowest Low_n) / (Highest High_n − Lowest Low_n)] × 100
     [n = lookback period, default 14]

%D = 3-period SMA of %K    [signal line]
```

**Slow Stochastics** (Lane's original, and the more commonly used form):
```
Slow %K = Fast %D  (i.e., 3-period SMA of Fast %K)
Slow %D = 3-period SMA of Slow %K
```

**Standard parameters:** 14-period lookback; **overbought ≥ 80**; **oversold ≤ 20**.

**What it signals:** Measures where price closes relative to its high-low range over n periods. Lane's own description: "Stochastics measures the momentum of price. If you visualize a rocket going up in the air — before it can turn down, it must slow down. Momentum always changes direction before price." Primary signal: %K crossing %D. Divergence between %D and price in extreme zones is the higher-confidence signal.

**Note on naming:** The "slow" vs "fast" terminology is confusing. Lane's actual method was what is now called "Slow Stochastics." Fast stochastics is the raw %K, which is more volatile.

---

## 7. Key Indicators — Trend and Volatility

### Moving Averages: SMA and EMA

No single inventor; developed from statistical smoothing methods. The specific periods and crossover terminology emerged from market practice.

**Formulas:**

```
SMA(n) = (P₁ + P₂ + ... + Pₙ) / n
         [equal weight to each period]

EMA:
k = 2 / (n + 1)    [smoothing factor]
EMA_t = Price_t × k + EMA_{t-1} × (1 − k)
```

**Wilder's smoothing** (used in RSI and ATR) differs: k = 1/n (e.g., 1/14 for 14-period), making it slower to react than standard EMA.

**SMA vs EMA:** EMA weights recent prices more heavily, reacting faster to price changes. SMA is smoother and better for identifying long-term trend direction. Neither is universally superior — the choice depends on the application.

**Standard periods:**
- **10, 20**: Short-term (intraday, daily swing trading)
- **50**: Medium-term institutional focus
- **100, 200**: Long-term trend (institutional benchmarks)

**Key signals:**

| Signal | Description |
|---|---|
| **Golden Cross** | 50-day MA crosses *above* 200-day MA → bullish; signals potential start of long-term uptrend |
| **Death Cross** | 50-day MA crosses *below* 200-day MA → bearish; signals potential bear market |
| Price above/below MA | Simple trend filter; price above its MA = bullish |
| MA crossover (fast vs slow) | Shorter-period MA crossing longer-period MA — the basis of the BLL (1992) trading rule tests |

**Academic evidence:** Brock, Lakonishok & LeBaron (1992) tested MA crossover rules on DJIA from 1897–1986 and found "strong support for technical strategies" not consistent with four market equilibrium models.[^21] Sullivan, Timmermann & White (1999) extended the analysis with White's Reality Check and found no significant outperformance after correcting for data-snooping bias.[^22] Zakamulin (2015) studied 155 years of data and found no statistically significant evidence that MA strategies outperform in the second half of the sample.[^23] **The pattern is consistent:** MA rules appear profitable in historical data but profitability declines materially after the early 1990s.

---

### Bollinger Bands

**Creator:** John Bollinger, developed early 1980s (commonly cited as 1983); formalized in *Bollinger on Bollinger Bands* (McGraw-Hill, 2002).[^24]

**Formula:**
```
Middle Band = SMA(20)
Upper Band  = SMA(20) + (2 × σ₂₀)
Lower Band  = SMA(20) − (2 × σ₂₀)
[σ₂₀ = 20-period standard deviation of closing prices]

%B = (Price − Lower Band) / (Upper Band − Lower Band)
     [1.0 = at upper band; 0.0 = at lower band; 0.5 = at middle band]

Bandwidth = (Upper Band − Lower Band) / Middle Band
            [normalized band width]
```

**Standard parameters:** 20-period SMA, 2.0σ multiplier. Bollinger recommends bands contain 88–89% of price action.

**What it signals:**
- Bands expand during high volatility, contract during low volatility.
- **Squeeze** (Bandwidth at a multi-period low): signals an impending directional move; direction is not predicted.
- Price at/beyond the upper band is NOT automatically a sell signal per Bollinger himself: "a tag of the upper band is not in-and-of-itself a sell signal." In trending markets, price can walk along the bands.
- %B above 1.0 or below 0.0 (price outside the bands) flags a statistically significant move.
- Typical mean-reversion use: buy at lower band + other confirmation; sell at upper band + confirmation. Continuation use: buy on a squeeze breakout.

**Academic evidence:** Mixed and dependent on market. Balsara, Chen & Zheng (2009) found Bollinger Band strategies underperform the market for DJIA, Nasdaq, S&P 500 (1990–2007); the contrarian version (buying the lower band) showed positive results — consistent with Bollinger's own intent.[^25] Results are notably better in emerging/Asian markets and currencies.[^25]

---

### ATR — Average True Range

**Creator:** J. Welles Wilder Jr., *New Concepts in Technical Trading Systems* (1978). Created because simple high-low range fails to capture volatility from gap openings.[^14]

**Formula:**
```
True Range (TR) = max of:
  (High − Low)              [normal intraday range]
  |High − Close_prev|       [gap-up case]
  |Low − Close_prev|        [gap-down case]

Equivalently: TR = max(High, Close_prev) − min(Low, Close_prev)

ATR(14):
  Initial = simple average of first 14 TR values
  Subsequent = (Prior ATR × 13 + Current TR) / 14
               [Wilder's 1/n smoothing]
```

**Standard parameters:** 14-period (Wilder's recommendation).

**What ATR measures — and does NOT measure:**
- **Measures:** Degree of price volatility — how much prices are moving in absolute terms.
- **Does NOT measure:** Direction of price movement. ATR is purely a volatility indicator.

**Primary applications:**
- **Stop-loss placement:** Set stops as a multiple of ATR (e.g., 2× ATR below entry), adapting to current volatility rather than using a fixed-dollar stop.
- **Position sizing:** In the trading-risk-management spoke, ATR feeds the position-size formula: risk-per-trade / (ATR multiplier × contract value).
- **Volatility regime identification:** Rising ATR = increasing volatility; declining ATR = contraction; breakouts from ATR squeeze are significant.

ATR is a tool for *managing* a trade rather than *finding* one — it does not generate directional signals. No dedicated academic study testing ATR's directional predictive power was found (which is appropriate — it is a volatility measure, not a forecasting indicator).

---

## §8-§12 — moved to `technical-analysis-breadth-frameworks-and-evidence.md`

These five sections were moved verbatim on 2026-08-04 to keep each file under the reference token
ceiling. Section and footnote numbering is unchanged, so a §9 reference or a footnote-37 citation
means the same thing in either file.

| Section | Now in | What it holds, and what it supports |
|---|---|---|
| **§8. Volume and Breadth Indicators** | `references/technical-analysis-breadth-frameworks-and-evidence.md` §8 | OBV (Granville 1963) and the "volume precedes price" divergence claim with the Tsang & Chong evidence; VWAP and anchored VWAP as the institutional execution benchmark; Volume Profile, POC and value area — the high-volume nodes §2 cites as a source of support and resistance; and the market-internals breadth measures (advance-decline line, McClellan Oscillator and Summation Index, Zweig Breadth Thrust). |
| **§9. Classical Frameworks: Dow Theory and Elliott Wave** | `references/technical-analysis-breadth-frameworks-and-evidence.md` §9 | Dow Theory's six tenets, three trend scales and three market phases — the source of the primary/secondary/minor taxonomy §2 uses — plus Brown, Goetzmann & Kumar's risk-adjusted evidence; and Elliott Wave's 5-3 wave structure, its three inviolable rules and Fibonacci guidelines, with the Batchelor & Ramyar finding that those ratios are statistically spurious. |
| **§10. Multi-Timeframe Analysis and Signal Combination** | `references/technical-analysis-breadth-frameworks-and-evidence.md` §10 | How the §6-§7 indicators and §3-§5 patterns are meant to be stacked: higher timeframe as trend filter, worked trend-following / mean-reversion / breakout component sets, and why signals drawn from different categories diversify while two momentum oscillators do not. |
| **§11. Empirical Evidence — What the Research Actually Shows** | `references/technical-analysis-breadth-frameworks-and-evidence.md` §11 | Whether the tools defined in this file actually pay — weak-form EMH (Fama 1970/1991), Brock, Lakonishok & LeBaron 1992, the data-snooping correction (Sullivan/Timmermann/White 1999, White 2000, Bajgrowicz & Scaillet 2012), Park & Irwin's 95-study meta-analysis, Lo/Mamaysky/Wang 2000, momentum (Jegadeesh & Titman; Moskowitz et al.), the Adaptive Market Hypothesis behind §2's decay note, Menkhoff's 692-manager survey, and the claim-by-claim evidence-quality table. |
| **§12. Common Failure Modes and Practitioner Pitfalls** | `references/technical-analysis-breadth-frameworks-and-evidence.md` §12 | The eight ways the tools defined here get misused — overfitting the historical chart, ignoring the pattern base rates quoted in §3-§5, survivorship bias, transaction costs, statistical vs economic significance, single-indicator decisions, post-hoc Elliott wave counts, and treating all markets as equivalent. |

---

## SKIP routing

- **Fundamental analysis** (earnings, valuation, balance sheets) → not covered here; fundamental analysis is a separate domain
- **Backtesting frameworks and strategy automation** → `algorithmic-and-quant-trading`
- **Specific strategy styles** (momentum, mean-reversion, breakout systems as trading methodologies) → `trading-strategies-and-styles`
- **Position sizing and stop-loss methodology** (how to size a position using ATR) → `trading-risk-management`
- **Charting entry/exit timing for options** → `options-trading-and-strategies`
- **Forex-specific TA application** (pip values, session-specific patterns) → `forex-and-currency-trading`
- **Crypto-specific TA** → `crypto-and-digital-asset-trading`
- **Automated/systematic TA signal execution** → `algorithmic-and-quant-trading`
- **Volume/breadth indicators, Dow Theory, Elliott Wave, multi-timeframe stacking, the academic evidence base, and TA failure modes** → `references/technical-analysis-breadth-frameworks-and-evidence.md`

---

## References

> Footnotes 26-46 moved with §8-§12 to `references/technical-analysis-breadth-frameworks-and-evidence.md`. Footnotes 10, 19, 21 and 22 are
> cited on both sides of the split and appear in both files. Numbering is unchanged across the
> two files.

[^1]: Nison, S. (1991/2001). *Japanese Candlestick Charting Techniques* (2nd ed.). New York: Portfolio/Penguin. ISBN: 9780735201811. Primary Western source for candlestick pattern definitions.

[^2]: Murphy, J.J. (1999). *Technical Analysis of the Financial Markets*. New York: New York Institute of Finance. The standard practitioner reference; covers all major chart patterns, trend analysis, and support/resistance.

[^3]: Osler, C.L. (2003). Currency Orders and Exchange-Rate Dynamics: Explaining the Success of Technical Analysis. *Journal of Finance*, 58(5), 1791–1820. Documents stop-loss and take-profit order clustering at round numbers in USD/JPY, GBP/USD, EUR/USD (1999–2000) at NatWest Markets; provides mechanical explanation for S/R effectiveness.

[^4]: Osler, C.L. (2000). Support for Resistance: Technical Analysis and Intraday Exchange Rates. *FRBNY Economic Policy Review*, July 2000, 53–68. Empirical evidence that S/R levels from six FX firms predict intraday trend interruptions in currency markets.

[^5]: *Applied Financial Economics* (2012), 22(19). Study on horizontal resistance levels in US tech stocks; positive excess returns in early periods, declining toward zero in more recent data.

[^6]: Caginalp, G., & Laurent, H. (1998). The Predictive Power of Price Patterns. *Applied Mathematical Finance*, 5(3–4), 181–205. Tested 8 three-day candlestick reversal patterns on all S&P 500 stocks, 1992–1996; found statistical significance at 36 standard deviations from null.

[^7]: Goo, Y., Chen, D., & Chang, Y. (2007). The Application of Japanese Candlestick Trading Strategies in Taiwan. *Investment Management and Financial Innovations*, 4(4), 49–71. Tested 26 candlestick patterns on Taiwanese stocks 1997–2006; found strong support, especially for short holding periods.

[^8]: Marshall, B.R., Young, M.R., & Rose, L.C. (2006). Candlestick Technical Trading Strategies: Can They Create Value for Investors? *Journal of Banking & Finance*, 30(8), 2303–2323. DOI: 10.1016/j.jbankfin.2005.08.001. Tested on DJIA component stocks, 1992–2002; no statistically significant excess returns.

[^9]: Bulkowski, T.N. (2021). *Encyclopedia of Chart Patterns* (3rd ed.). Hoboken, NJ: Wiley. Practitioner empirical database covering 75+ patterns on large stock samples; each pattern scored by failure rate, average move, price target achievement. See also: thepatternsite.com for pattern-specific statistics.

[^10]: Lo, A.W., Mamaysky, H., & Wang, J. (2000). Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation. *Journal of Finance*, 55(4), 1705–1765. DOI: 10.1111/0022-1082.00265. NBER Working Paper 7613. Used nonparametric kernel regression on US stock data 1962–1996; found chart patterns (H&S, double bottoms) provide "incremental information."

[^11]: Savin, G., Weller, P., & Zvingelis, J. (2007). The Predictive Power of "Head-and-Shoulders" Price Patterns in the U.S. Stock Market. *Journal of Financial Econometrics*, 5(2), 243–265. Found 5–7% risk-adjusted excess returns when H&S used as a conditional filter on S&P 500 and Russell 2000, 1990–1999.

[^12]: Friesen, G.C., Weller, P.A., & Dunham, L.M. (2009). Price Trends and Patterns in Technical Analysis: A Theoretical and Empirical Examination. *Journal of Banking & Finance*, 33(6), 1089–1100. DOI: 10.1016/j.jbankfin.2008.12.010. Behavioral model showing confirmation bias mechanically generates H&S and double-top price patterns.

[^13]: Leigh, W., Modani, N., Purvis, R., & Roberts, T. (2002). Stock Market Trading Rule Discovery Using Technical Charting Heuristics. *Expert Systems with Applications*, 23(2), 155–159. Found positive excess returns from bull flag recognition on NYSE Composite, 1980–1999, before transaction costs.

[^14]: Wilder, J.W. (1978). *New Concepts in Technical Trading Systems*. Greensboro, NC: Trend Research. Primary source for RSI (pp. 63–70), ATR, ADX, and other Wilder indicators.

[^15]: Marek, P., & Šedivá, B. (2017). Optimization and Testing of RSI. *Procedia Computer Science*, 109, 481–488. Found RSI produces gains over short periods but is typically overcome by buy-and-hold over longer periods.

[^16]: RSI as trend-following indicator reframing. Available: https://www.academia.edu/144363742. Argues RSI more accurately reflects trend persistence than imminent reversal in trending markets.

[^17]: Appel, G. (1979). *The Moving Average Convergence-Divergence Trading Method*. Great Neck, NY: Signalert. Original MACD publication. Histogram addition: Aspray, T. (1986). *Futures* magazine. See also CMT Association profile: https://cmtassociation.org/presenter/gerald-appel/

[^18]: arXiv:2206.12282 (2022). MACD performance study on US markets (DJIA, Nasdaq, S&P 500), 2015–2021; found MACD alone produced win rate below 50%.

[^19]: Park, C.H., & Irwin, S.H. (2007). What Do We Know About the Profitability of Technical Analysis? *Journal of Economic Surveys*, 21(4), 786–826. DOI: 10.1111/j.1467-6419.2007.00519.x. Meta-analysis of 95 modern studies: 56 positive, 20 negative, 19 mixed; identifies pervasive methodological concerns.

[^20]: Lane, G.C. (1957/1960). Stochastic oscillator. First presented at Investment Educators seminars (1957); published in *How to Make Money in Commodities* (1960). See: Wikipedia, George Lane (technical analyst): https://en.wikipedia.org/wiki/George_Lane_(technical_analyst)

[^21]: Brock, W., Lakonishok, J., & LeBaron, B. (1992). Simple Technical Trading Rules and the Stochastic Properties of Stock Returns. *Journal of Finance*, 47(5), 1731–1764. DOI: 10.2307/2328994. Foundational positive TA study; tested MA and trading-range break rules on DJIA 1897–1986; found results inconsistent with four null models.

[^22]: Sullivan, R., Timmermann, A., & White, H. (1999). Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. *Journal of Finance*, 54(5), 1647–1691. DOI: 10.1111/0022-1082.00163. Applied White's Reality Check to TA rules; found no outperformance after data-snooping correction.

[^23]: Zakamulin, V. (2015). A Comprehensive Look at the Empirical Performance of Moving Average Trading Strategies. SSRN Working Paper 2677212. 155 years of data; found no statistically significant evidence of MA strategy outperformance in second half of sample. https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2677212

[^24]: Bollinger, J. (2002). *Bollinger on Bollinger Bands*. New York: McGraw-Hill. Primary source for Bollinger Bands formula, parameters, and intended use. See also: https://www.bollingerbands.com/bollinger-band-rules

[^25]: Balsara, N.J., Chen, G., & Zheng, L. (2009). The Chinese Stock Market: An Examination of the Random Walk Model and Technical Trading Rules. *Quarterly Journal of Business and Economics*. Also: Fang, J., Qin, Y., & Jacobsen, B. (2014). SSRN 2484322 — tested 93 technical market indicators; none beat buy-and-hold after costs.

