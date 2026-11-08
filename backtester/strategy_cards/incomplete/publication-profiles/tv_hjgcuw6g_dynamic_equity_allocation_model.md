---

id: tv_profile_hjgcuw6g

name: "Dynamic Equity Allocation Model"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "DEAM recommends a changing US-equity versus cash allocation by combining market regime, risk capacity, valuation, sentiment and macro conditions. It is a tactical exposure model with a separate crisis override, not a documented executed portfolio or verified return record."

registry_key: null

runner: null

evaluation: null

---

# Dynamic Equity Allocation Model

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

DEAM recommends a changing US-equity versus cash allocation by combining market regime, risk capacity, valuation, sentiment and macro conditions. It is a tactical exposure model with a separate crisis override, not a documented executed portfolio or verified return record.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Numerous equations and thresholds are disclosed, but missing scoring maps, contradictory conventions and external-data contracts prevent a reproducible complete allocation.

- Define every component score mapping and resolve spread/term-structure signs.
- Provide point-in-time fundamental/yield inputs, fallback constants and aggregation rules.
- Specify risk feedback recurrence and crisis-cap/smoothing ordering.

## How it works

- Trend relationships, annualized volatility and drawdown form the regime score. Risk allocation compares target volatility with the larger close-return/Parkinson estimate and target drawdown with market drawdown; an exponential penalty reduces overutilized risk.
- Valuation blends earnings yield, buybacks, dividend-growth and shareholder-yield approaches to equity risk premium, then applies profitability, growth and leverage adjustments. Sentiment uses VIX normalization, term structure and safe-haven relative performance; macro scores use Treasury spreads, bond credit proxies and balance-sheet quality.
- Weighted component allocations receive a model-style adjustment and moving-average smoothing. A stress counter combines volatility, drawdown, credit, simultaneous stock/bond losses and panic volume; crisis states cap exposure.

## Outputs and intended use

- Allocation and complementary cash series, component scores, regime/crisis dashboard and threshold alerts support portfolio reviews. Optional allocation-dispersion bands describe recent recommendation variability, not calibrated confidence in future returns. Users must choose a rebalancing and execution policy.

## Parameters and stated settings

- Default target annual volatility is 12% and maximum drawdown 15%. Default component weights are regime/risk/valuation/sentiment/macro 35/25/20/15/5 percent; final smoothing uses three periods. Crisis and severe-crisis exposure caps are 25% and 10%. Conservative/aggressive adjustments subtract/add ten percentage points; balanced leaves output unchanged.
- Regime inputs: moving-average windows 20/50/200 days; log-return volatility window 20 days annualized by sqrt(252), compared with Parkinson volatility; drawdown from the 252-day high. Trend/volatility/drawdown weights 40/30/30%; regime score >80 strong bull, <10 crisis. VIX <15 improves and >35 reduces regime score; drawdown <3% maximally improves and >20% severely reduces it; intermediate score tables are absent.
- ERP component weights are 35/30/20/15% for earnings yield minus Treasury yield, earnings yield plus buybacks, dividend yield plus sustainable growth, and total shareholder yield plus implied growth. Sustainable growth=ROE*(1-payout ratio). ERP>4% maps to valuation 95; negative ERP maps to 10. Revenue growth >10% adds 10 points, >5% adds 5; net margin >15% adds 5, <8% subtracts 5; ROE>20% adds 5. D/E<1 multiplies score by 1.2, >2 by 0.8.
- For risk utilization u>1, adjustment=exp(-0.5*(u-1)). VIX z=(current-mean)/SD: below -1.5 adds 40 sentiment points, above +1.5 subtracts 40. The source calls VIX>1.05*VIX9D backwardation and >1.15 steep backwardation, deducting 15/30 points; preserve its convention conflict. Safe-haven relative performance uses 20 trading days; outperformance subtracts up to 20 points, underperformance adds up to 10.
- Source-labelled yield spreads above 1.5% and 2% yield 40 points; near zero 20, negative 10. Credit spread <200bp gives 30, >1000bp zero. Corporate D/E<0.5 with ROE>15% gives 20; D/E>1.5 gives 5. Missing intermediate maps and yield-sign contradictions remain.
- Crisis counter: VIX>40(default) +1, >60 +2 additional; drawdown>15% +1, >25% another +1; credit spread>500bp +1; SPY loss>10% and TLT loss>5% over five trading days +2; volume>2*20-day mean with falling price +1. Counter>=3 crisis, >=5 severe, with exposure caps 25%/10%. Source alternates weighted points and indicators terminology.
- Adaptive mode: 20-day market gain>5% adds five allocation percentage points; loss>5% subtracts five. Optional allocation bands are +/-1 SD over 20 periods. Allocation alerts at upward 80% and falling 20%; risk breach when utilization exceeds target by 20%; separate crisis/severe and regime-change alerts.

## Failure modes and caveats

- Fallback fundamental averages can hide stale or unavailable inputs rather than ensure unbiased signals. The stated yield-spread direction and VIX/VIX9D backwardation convention conflict with their verbal interpretations. Equity allocation does not generally scale realized portfolio drawdown linearly after dynamic rebalancing. No detailed validation or transaction-cost model is supplied.

## Missing information and implementation boundary

- Complete piecewise score tables, fallback constants, fundamental aggregation/universe and point-in-time release handling are absent. Bond ETF prices alone do not define the claimed yield spreads. Crisis cap ordering relative to final smoothing is unclear.
- Disclosed endpoints/bonuses do not define complete intermediate scoring maps. Exact weighting of risk-utilization channels and feedback recurrence remain unclear despite the printed exponential penalty.

## Data requirements

Required inputs: SPY OHLCV, VIX and VIX9D histories, Treasury maturity yields, HYG/LQD/TLT data and credit-yield mapping, point-in-time aggregated fundamentals, gold, dollar and yen histories.

Repository input-class support: unavailable or unresolved. OHLCV alone cannot supply implied volatility, historical yields, fundamental release vintages and index-level aggregation. Description does not establish an available point-in-time input contract.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, risks, required_data, readiness

```text
default 12% annualized
```

### E2: mechanism, parameters, risks, required_data, readiness

```text
default 15%
```

### E3: mechanism, parameters, risks, required_data, readiness

```text
Market Regime 35%, Risk Management 25%, Valuation 20%, Sentiment 15%, Macro 5%
```

### E4: mechanism, parameters, risks, required_data, readiness

```text
simple moving average over 3 periods
```

### E5: mechanism, parameters, risks, required_data, readiness

```text
caps equity allocation at maximum 25%. In a severe crisis, the cap is set at 10%
```

### E6: mechanism, parameters, risks, required_data, readiness

```text
DEAM calculates two spread measures: the 2-year-minus-10-year spread and the 3-month-minus-10-year spread.
```

### E7: mechanism, parameters, risks, required_data, readiness

```text
identifies backwardation (VIX > 1.05 × VIX9D)
```

### E8: mechanism, parameters, risks, required_data, readiness

```text
While this document does not present detailed backtest analysis
```

### E9: mechanism, parameters, risks, required_data, readiness

```text
Fundamental corporate metrics are retrieved via TradingView's Financial Data API.
```

### E10: mechanism, parameters, risks, required_data, readiness

```text
Conservative mode subtracts 10 percentage points
```

### E11: mechanism, parameters, risks, required_data, readiness

```text
Aggressive mode adds 10 percentage points
```

### E12: mechanism, parameters, readiness

```text
The model calculates three moving averages with different time windows: a 20-day average (approximately one trading month), a 50-day average (approximately one quarter), and a 200-day average (approximately one trading year). The relationship of the current price to these averages and the relationship of the averages to each other provide information about trend strength and direction. When the price trades above all three averages and the short-term average is above the long-term, this indicates an established uptrend. The model assigns points based on these constellations, with longer-term trends weighted more heavily as they are considered more persistent.
```

### E13: mechanism, parameters, readiness

```text
The model calculates current drawdown as the percentage distance from the highest price of the last 252 trading days (one year). A drawdown below 3% is considered negligible and maximally increases the regime score. As drawdown increases, the score decreases progressively, with drawdowns above 20% classified as severe and indicating a crisis or bear market regime. These thresholds are empirically motivated by historical market cycles, in which corrections typically encompassed 5-10% drawdowns, bear markets 20-30%, and crises over 30%.
```

### E14: mechanism, parameters, readiness

```text
Final regime classification occurs through aggregation of scores from trend (40% weight), volatility (30%), and drawdown (30%). The higher weighting of trend reflects the empirical observation that trend-following strategies have historically delivered robust results (Moskowitz, Ooi, and Pedersen, 2012). A total score above 80 signals a strong bull market with established uptrend, low volatility, and minimal losses. At a score below 10, a crisis situation exists requiring defensive positioning. The six regime categories enable a differentiated allocation strategy that not only distinguishes binarily between bullish and bearish but allows gradual gradations.
```

### E15: mechanism, parameters, readiness

```text
The logarithmic return is calculated as ln(P_t / P_{t-1}), where P_t is the price at time t. The standard deviation of these returns over a rolling 20-trading-day window is then multiplied by √252 to obtain annualized volatility. This annualization is based on the assumption of independently identically distributed returns, which is an idealization but widely accepted in practice.
```

### E16: mechanism, parameters, readiness

```text
The Parkinson estimator uses additional information from the trading range (High minus Low) of each day. The formula is: σ_P = (1/√(4ln2)) × √(1/n × Σln²(H_i/L_i)) × √252, where H_i and L_i are high and low prices. Under ideal conditions, this estimator is approximately five times more efficient than the close-to-close estimator (Parkinson, 1980), as it uses more information per observation.
```

### E17: mechanism, parameters, readiness

```text
Mathematically, a risk adjustment factor r_adjust is calculated: if risk utilization u > 1, then r_adjust = exp(-0.5 × (u - 1)). This exponential function ensures that moderate overutilization is gently corrected, while strong overutilization triggers drastic reductions. The factor 0.5 in the exponent was empirically calibrated to achieve a balanced ratio between sensitivity and stability.
```

### E18: mechanism, parameters, readiness

```text
The first method (35% weight) uses earnings yield, calculated as 1/P/E or directly from operating earnings data, and subtracts the 10-year Treasury yield. This method follows Fed Model logic (Yardeni, 2003), although this model has theoretical weaknesses as it does not consistently treat inflation (Asness, 2003).
```

### E19: mechanism, parameters, readiness

```text
The second method (30% weight) extends earnings yield by share buyback yield. Share buybacks are a form of capital return to shareholders and increase value per share. Boudoukh et al. (2007) showed in "The Total Shareholder Yield" that the sum of dividend yield and buyback yield is a better predictor of future returns than dividend yield alone.
```

### E20: mechanism, parameters, readiness

```text
The third method (20% weight) implements the Gordon Growth Model (Gordon, 1962), which models stock value as the sum of discounted future dividends. Under constant growth g assumption: Expected Return = Dividend Yield + g. The model estimates sustainable growth as g = ROE × (1 - Payout Ratio), where ROE is return on equity and payout ratio is the ratio of dividends to earnings. This formula follows from equity theory: unretained earnings are reinvested at ROE and generate additional earnings growth.
```

### E21: mechanism, parameters, readiness

```text
The fourth method (15% weight) combines total shareholder yield (Dividend + Buybacks) with implied growth derived from revenue growth. This method considers that companies with strong revenue growth should generate higher future earnings, even if current valuations do not yet fully reflect this.
```

### E22: mechanism, parameters, readiness

```text
The final ERP is the weighted average of these four methods. A high ERP (above 4%) signals attractive valuations and increases the valuation score to 95 out of 100 possible points. A negative ERP, where stocks have lower expected returns than bonds, results in a minimal score of 10.
```

### E23: mechanism, parameters, readiness

```text
Revenue growth above 10% annually adds 10 points to the valuation score, moderate growth above 5% adds 5 points. This adjustment reflects that growth has independent value (Modigliani and Miller, 1961, extended by later growth theory). Net margin above 15% signals pricing power and operational efficiency and increases the score by 5 points, while low margins below 8% indicate competitive pressure and subtract 5 points.
```

### E24: mechanism, parameters, readiness

```text
Return on equity (ROE) above 20% characterizes outstanding capital efficiency and increases the score by 5 points. Piotroski (2000) showed in "Value Investing: The Use of Historical Financial Statement Information" that fundamental quality signals such as high ROE can improve the performance of value strategies.
```

### E25: mechanism, parameters, readiness

```text
Capital structure is evaluated through the debt-to-equity ratio. A conservative ratio below 1.0 multiplies the valuation score by 1.2, while high leverage above 2.0 applies a multiplier of 0.8. This adjustment reflects that high debt constrains financial flexibility and can become problematic in crisis times (Korteweg, 2010).
```

### E26: mechanism, parameters, readiness

```text
A Z-score below -1.5 (VIX is 1.5 standard deviations below average) signals exceptionally low risk perception and adds 40 points to the sentiment score. This may seem counterintuitive—shouldn't low fear be bullish? However, the logic follows the contrarian principle: when no one is afraid, everyone is already invested, and there is limited further upside potential (Zweig, 1973). Conversely, a Z-score above 1.5 (extreme fear) adds -40 points, reflecting market panic but simultaneously suggesting potential buying opportunities.
```

### E27: mechanism, parameters, readiness

```text
The model compares the VIX with VIX9D (9-day volatility) and identifies backwardation (VIX > 1.05 × VIX9D) and steep backwardation (VIX > 1.15 × VIX9D).
```

### E28: mechanism, parameters, readiness

```text
The model subtracts 15 points for backwardation and 30 for steep backwardation, as these constellations signal elevated risk. Simon and Wiggins (2001) analyzed the VIX futures curve and showed that backwardation is associated with market declines.
```

### E29: mechanism, parameters, readiness

```text
The safe-haven component is calculated as the difference between safe-haven performance and stock performance. Positive values (safe havens outperform) subtract up to 20 points from the sentiment score, negative values (stocks outperform) add up to 10 points. The asymmetric treatment (larger deduction for risk-off than bonus for risk-on) reflects that risk-off movements are typically sharper and more informative than risk-on phases.
```

### E30: mechanism, parameters, readiness

```text
The model calculates the performance of these assets relative to stocks over the last 20 trading days. When gold or the dollar strongly rise while stocks fall, this indicates elevated risk aversion.
```

### E31: mechanism, parameters, readiness

```text
DEAM calculates two spread measures: the 2-year-minus-10-year spread and the 3-month-minus-10-year spread. A steep, positive curve (spreads above 1.5% and 2% respectively) signals healthy growth expectations and generates the maximum yield curve score of 40 points. A flat curve (spreads near zero) reduces the score to 20 points. An inverted curve (negative spreads) is particularly alarming and results in only 10 points.
```

### E32: mechanism, parameters, readiness

```text
A narrow spread below 200 basis points signals healthy credit conditions and risk appetite, contributing 30 points to the macro score. Very wide spreads above 1000 basis points (as during the 2008 financial crisis) signal credit crunch and generate zero points.
```

### E33: mechanism, parameters, readiness

```text
A low leverage level below 0.5 combined with high ROE above 15% signals robust corporate balance sheets and generates 20 points. This combination is particularly valuable as it represents both defensive strength (low debt means crisis resistance) and offensive strength (high ROE means earnings power). High leverage above 1.5 generates only 5 points, as it implies vulnerability to interest rate increases and recessions.
```

### E34: mechanism, parameters, readiness

```text
The first indicator is a VIX above the crisis threshold (default 40), adding one point. A VIX above 60 (as in 2008 and March 2020) adds two additional points, as such extreme values are historically very rare. This tiered approach captures the intensity of volatility.
```

### E35: mechanism, parameters, readiness

```text
The second indicator is market drawdown. A drawdown above 15% adds one point, as corrections of this magnitude can be potential harbingers of larger crises. A drawdown above 25% adds another point, as historical bear markets typically encompass 25-40% drawdowns.
```

### E36: mechanism, parameters, readiness

```text
The third indicator is credit market spreads above 500 basis points, adding one point. Such wide spreads occur only during significant credit market disruptions, as in 2008 during the Lehman crisis.
```

### E37: mechanism, parameters, readiness

```text
The fourth indicator identifies simultaneous losses in stocks and bonds. Normally, Treasury bonds act as a hedge against equity risk (negative correlation), but when both fall simultaneously, this indicates systemic liquidity problems or inflation/stagflation fears. The model checks whether both SPY and TLT have fallen more than 10% and 5% respectively over 5 trading days, adding two points.
```

### E38: mechanism, parameters, readiness

```text
The fifth indicator is a volume spike combined with negative returns. Extreme trading volumes (above twice the 20-day average) with falling prices signal panic selling. This adds one point.
```

### E39: mechanism, parameters, readiness

```text
A crisis situation is diagnosed when at least 3 indicators trigger, a severe crisis at 5 or more indicators. These thresholds were calibrated through historical backtesting to identify true crises (2008, 2020) without generating excessive false alarms.
```

### E40: mechanism, parameters, readiness

```text
Adaptive mode implements procyclical adjustment based on short-term momentum: if the market has risen more than 5% in the last 20 days, 5 percentage points are added; if it has declined more than 5%, 5 points are subtracted. This logic follows the observation that short-term momentum persists (Jegadeesh and Titman, 1993), but the moderate size of adjustment avoids excessive timing bets.
```

### E41: mechanism, parameters, readiness

```text
These are calculated as ±1 standard deviation of allocation over a rolling 20-period window. Wide bands indicate high volatility of model recommendations, suggesting uncertain market conditions. Narrow bands indicate stable recommendations.
```

### E42: mechanism, parameters, readiness

```text
An alert is generated when allocation reaches 80% (from below), signaling strong bullish conditions. Another alert triggers when allocation falls to 20%, indicating defensive positioning.
```

### E43: mechanism, parameters, readiness

```text
A specialized alert triggers when actual portfolio risk utilization exceeds target parameters by 20%. This is a warning signal that the risk management system is reaching its limits, possibly because market volatility is rising faster than allocation can be reduced. In such situations, investors should consider manual interventions.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hjgcuw6g_dynamic_equity_allocation_model](../tv_hjgcuw6g_dynamic_equity_allocation_model.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_method_value_investing](../tv_method_value_investing.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/HjgCUw6g-Dynamic-Equity-Allocation-Model/

Publication ID: HjgCUw6g. Source SHA-256: 1cb19c911bb68ebf1041eed512dc65992088ea9e805d38304ecbe37a23957dcf. Raw-description SHA-256: a2f166fa591586c4292d6ddc06947914c063fdc618af7456c92f81d9e8c214ed.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
