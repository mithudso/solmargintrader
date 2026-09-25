<!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/trading-risk-management.md by scripts/persist-spoke.mjs. -->

# Trading Risk Management (spoke)

A spoke of the **`trading-and-investing`** hub. It covers the **sizing and protection of trading capital** — the discipline of deciding how much to risk on each trade, where to place stops, how to measure and limit drawdown, and how to evaluate risk-adjusted performance.

> **Educational information only — NOT financial, investment, or trading advice.** Risk management frameworks reduce but cannot eliminate losses; trading carries significant risk of capital loss, especially with leverage. Verify all formulas and calculations with your specific instrument, broker, and account currency.

## Contents

1. [The Foundation: Risk per Trade](#1-the-foundation-risk-per-trade)
2. [Position Sizing Methods](#2-position-sizing-methods)
3. [Kelly Criterion](#3-kelly-criterion)
4. [R-Multiples and Expectancy](#4-r-multiples-and-expectancy)
5. [Stop Placement](#5-stop-placement)
6. [Drawdown Control](#6-drawdown-control)
7. [Risk of Ruin](#7-risk-of-ruin)
8. [Portfolio Heat and Correlated Positions](#8-portfolio-heat-and-correlated-positions)
9. [Margin and Leverage as a Risk Discipline](#9-margin-and-leverage-as-a-risk-discipline)
10. [Performance Metrics: Sharpe, Sortino, Calmar](#10-performance-metrics-sharpe-sortino-calmar)

---

## 1. The Foundation: Risk per Trade

The single most important input to every sizing formula is **how many dollars you are willing to lose if the trade hits your stop** — your dollar risk per trade, or **1R** (see Section 4).

The standard starting convention for retail traders is **1% of account equity per trade**. Aggressive traders may use 2%; professional quant funds typically use 0.25–0.5% per position. Never confuse *position size* (total dollars deployed) with *risk* (dollars lost at the stop).

**Core formula:**

```
Dollar Risk (1R) = Account Equity × Risk % per trade
Position Size    = Dollar Risk ÷ Stop Distance (in dollars per unit)
```

*Example:* $50,000 account, 1% risk, stop $2.00 below entry on a $40 stock:
- Dollar Risk = $50,000 × 0.01 = **$500**
- Position Size = $500 ÷ $2.00 = **250 shares**

For forex, the stop distance is in pips; pip value converts pips to dollars (see `references/forex-and-currency-trading.md` for the pip value calculation).

---

## 2. Position Sizing Methods

### 2a. Fixed Fractional (Percent Risk)

The most common retail approach. Risk a constant fraction *f* of current equity on each trade. The position size scales up with profits and down with losses, providing **asymmetric recovery** — a loss requires a proportionally smaller percentage gain to recover.

**Formula:**
```
Position Size = (Account Equity × f) ÷ Stop Distance per Unit
```

*f* = 1–2% for most retail traders; professional quant strategies typically 0.1–0.5%. [^1]

**Property:** A 10-trade losing streak at 1% leaves the account at (0.99)^10 = ~90% of starting equity. At 2%, that same streak leaves ~82%.

### 2b. Fixed Dollar Risk

Risk the same dollar amount per trade regardless of account size changes. Simpler to calculate but does not compound — after a drawdown, position sizes stay the same even though equity is lower.

```
Position Size = Fixed Dollar Risk ÷ Stop Distance per Unit
```

### 2c. Volatility-Based (ATR) Sizing

Use the instrument's **Average True Range (ATR)** as the stop and size the position so that the ATR-based stop equals your dollar risk. This adjusts position size automatically for current market conditions — smaller positions in high-volatility regimes, larger in quiet ones.

**Formula:**
```
Stop Distance = N × ATR(period)          [e.g., 2 × ATR(14)]
Position Size = Dollar Risk ÷ (N × ATR)
```

**Maximum Adverse Excursion (MAE):** The largest unrealized loss a trade ever reaches before closing. MAE analysis — plotting MAE vs. final P&L across a large trade sample — validates whether the ATR multiple chosen actually contains losing trades. If winning trades rarely exceed 1× ATR adverse move, an ATR stop is probably well-calibrated. [^2]

### 2d. Percent of Volatility (Alternative)

```
Position Size = (Account Equity × f) ÷ (N × Price × Daily Volatility)
```

Used in systematic strategies to equalize the *volatility contribution* of each position, creating a more homogeneous risk exposure across instruments.

---

## 3. Kelly Criterion

### Derivation and Formula

Developed by John L. Kelly Jr. at Bell Labs in 1956, the Kelly Criterion gives the **fraction of capital** that maximizes the **long-run geometric growth rate** of the account. [^3]

**Standard form (binary outcomes):**
```
f* = (b × p − q) / b
```
where:
- `f*` = optimal fraction to wager
- `b` = net odds received per unit wagered (reward-to-risk ratio)
- `p` = probability of winning
- `q` = probability of losing = 1 − p

**Simplified trading form (Win Rate and R:R):**
```
Kelly % = W − [(1 − W) / R]
```
where:
- `W` = historical win rate
- `R` = average win ÷ average loss (reward-to-risk ratio)

*Example:* 55% win rate, 1.5:1 R:R:
```
Kelly % = 0.55 − [(0.45) / 1.5] = 0.55 − 0.30 = 25%
```
→ Full Kelly says risk 25% per trade — far too large for most traders.

### Why Full Kelly Is Rarely Used

Full Kelly maximizes *growth rate* but produces **drawdowns exceeding 50%** that are psychologically devastating and operationally dangerous (margin calls, forced liquidation). Full Kelly is also highly sensitive to estimation error: if your true win rate is 5 percentage points lower than estimated, full Kelly can risk substantially more than optimal. [^4]

### Fractional Kelly in Practice

| Fraction | Growth Rate Retained | Max Drawdown Profile |
|---|---|---|
| Full Kelly (1/1) | 100% | Often >50% |
| Half Kelly (1/2) | ~75% | Roughly halved |
| Quarter Kelly (1/4) | ~50% | Very conservative |

Half-Kelly retains approximately 75% of the maximum compound growth rate while roughly halving the drawdown — a derived mathematical property, not a rule of thumb. Most quantitative funds use **quarter to half Kelly**. [^4]

**Practical guidance:**
- Estimate Kelly conservatively (use 90% confidence interval on win rate, not point estimate).
- Treat Kelly as an upper bound, not a target.
- A Kelly fraction > 5% per trade is extremely aggressive for active trading.

---

## 4. R-Multiples and Expectancy

Developed by Dr. Van Tharp, the R-multiple framework standardizes all trade outcomes in units of **initial risk**, making performance comparable across instruments, position sizes, and time. [^5]

### Defining 1R

```
1R = (Entry Price − Stop Price) × Position Size
   = the dollar amount lost if the stop is hit
```

Every trade outcome is then expressed as a multiple of 1R:
- Win of $300 on a trade where 1R = $100 → **+3R**
- Loss to the stop → **−1R**
- Slippage below the stop causing $120 loss → **−1.2R**

### Expectancy Formula

```
Expectancy = (Win Rate × Average Win in R) − (Loss Rate × Average Loss in R)
           = p × W_R − (1 − p) × |L_R|
```

*Example:* 45% win rate, average win = +2R, average loss = −1R:
```
Expectancy = (0.45 × 2) − (0.55 × 1) = 0.90 − 0.55 = +0.35R per trade
```
→ On average, the system makes 0.35R per trade — positive expectancy.

**Why expectancy matters more than win rate:** A system winning 70% of the time with average wins of 0.5R and average losses of 2R has expectancy = (0.70 × 0.5) − (0.30 × 2) = 0.35 − 0.60 = **−0.25R** — it loses money despite a high win rate.

### Van Tharp's CPR Formula

```
Position Size (P) = Capital at Risk (C) ÷ Risk per Unit (R)
```

"Capital at Risk" is the dollar amount you're willing to lose; "Risk per Unit" is the stop distance in dollars per share/unit. [^5]

---

## 5. Stop Placement

The stop defines 1R. Where you place it is a strategic decision — too tight and you get stopped out by normal price noise; too loose and your dollar risk exceeds the acceptable fraction of account.

### 5a. Technical Stops

Place the stop **beyond a key level** that, if breached, invalidates the trade thesis:
- **Below support** (for a long): 1 ATR below the swing low, or just below the last significant swing low
- **Above resistance** (for a short): just above the swing high
- **Below a moving average**: for trend-following entries, stop below the 20-day or 50-day EMA

### 5b. ATR-Based Volatility Stops

```
Long Stop  = Entry − (N × ATR)
Short Stop = Entry + (N × ATR)
```
Common multipliers: N = 1.5 to 3× ATR(14). The ATR adapts to current volatility — stops widen in volatile conditions and tighten in quiet ones, preventing arbitrary stop-outs.

### 5c. Fixed-Percentage Stops

```
Stop Price = Entry × (1 − stop %)      [for a long]
```
e.g., Entry = $50, 5% stop → stop at $47.50. Simple but not calibrated to the instrument's actual volatility — a 5% stop may be too tight for a volatile small-cap and too loose for a stable large-cap.

### 5d. Mental vs. Hard Stops

**Hard stops** (resting orders at the broker): executed automatically; avoid emotional overrides; subject to slippage in fast markets and stop-hunting by market makers.

**Mental stops** (monitored only): require discipline to execute; no slippage from stop-hunting; risky if the trader overrides in the moment. Most retail traders should use hard stops.

### 5e. MAE Validation

After 50+ trades, plot MAE (intra-trade max loss) vs. final outcome:
- Winning trades should cluster at low MAE
- Losing trades may show MAE near or at the stop
- Outliers (winners with high MAE, or losses far beyond the stop) signal stop calibration problems [^2]

---

## 6. Drawdown Control

### Definitions

```
Drawdown at time t = (Peak Equity before t − Equity at t) / Peak Equity before t
Max Drawdown (MDD) = max over all time periods of [Drawdown at t]
```

A drawdown has three phases:
1. **Decline**: from the peak to the trough
2. **Trough**: the bottom of the drawdown
3. **Recovery**: from the trough back to a new equity high (the drawdown period ends)

*Example:* Account peaks at $100,000, falls to $70,000, recovers to $105,000:
- Drawdown = ($100k − $70k) / $100k = **30%**
- Recovery required from trough = $30k / $70k = **42.9%** gain on the reduced equity

### The Asymmetric Recovery Problem

| Loss % | Recovery % Needed |
|---|---|
| 10% | 11.1% |
| 20% | 25.0% |
| 30% | 42.9% |
| 40% | 66.7% |
| 50% | 100.0% |

This asymmetry is why position sizing is about **survival first**: a 50% drawdown requires a 100% gain to recover — while you're in the drawdown, your psychology is at its worst and your equity is at its lowest.

### Drawdown Reduction Tactics

1. **Size reduction after drawdown**: After a 10–20% drawdown, halve position size until the account recovers; scale back up as equity recovers (the "half-size in drawdown" rule)
2. **Maximum daily loss limit**: If a single day loses more than N% (e.g., 3%), stop trading for the day
3. **Monthly loss limit**: If a month's losses exceed a threshold (e.g., 8%), reduce size by half for the remainder of the month
4. **Correlation audit**: In drawdowns, correlations between instruments tend to spike — audit the portfolio for hidden concentration risk

---

## 7. Risk of Ruin

Risk of ruin (RoR) is the probability that a series of losing trades reduces the account to zero (or an unusable threshold) before it recovers. It is the ultimate risk metric — capturing the interplay of win rate, reward-to-risk ratio, and percent risked per trade.

### Formula

```
RoR = ((1 − Edge) / (1 + Edge))^N
```

where:
- `Edge` = per-trade advantage = (Win Rate × Avg Win in R) − (Loss Rate × Avg Loss in R), normalized by Avg Loss
- `N` = number of risk units in the account = Account Size / Dollar Risk Per Trade [^6]

*Example:* 55% win rate, 1.5:1 R:R, $50,000 account risking 1% ($500):
- Edge ≈ 0.375 (derived from the expectancy calculation)
- N = $50,000 / $500 = 100 risk units
- RoR = ((1 − 0.375) / (1 + 0.375))^100 = (0.455)^100 ≈ **essentially zero**

*Risk scenario — 3% per trade:*
- N = $50,000 / $1,500 ≈ 33 risk units
- RoR increases dramatically; Balsara's research shows even positive-expectancy systems face significant ruin probability when per-trade risk exceeds 3–5% of account [^6]

### Key Sensitivity

Reducing per-trade risk has a larger impact than slightly improving win rate. Halving risk from 2% to 1% typically cuts RoR by far more than going from a 50% to 55% win rate. **Position sizing is the primary lever on RoR.**

---

## 8. Portfolio Heat and Correlated Positions

**Portfolio heat** = the total open risk across all simultaneous positions, expressed as a percentage of account equity.

```
Portfolio Heat = Sum of (Dollar Risk per Position) / Account Equity
```

*Example:* 5 open trades, each risking 1% of a $50,000 account:
- Each trade: 1% × $50,000 = $500 at risk
- Total portfolio heat: 5 × $500 / $50,000 = **10% of equity at risk**

### Correlation Adjustment

When positions are positively correlated (e.g., multiple tech stocks, or EUR/USD + GBP/USD which tend to move together), the portfolio heat *understates* the true risk. In a sharp correlated selloff, all positions can hit their stops simultaneously.

**Rule of thumb:** For correlated positions, treat them as a single position for heat calculation purposes. If two highly correlated positions each risk 1%, treat the combined exposure as 1.5–2% rather than 2%.

### Sector/Theme Concentration

Maximum recommended heat varies by practitioner:
- Aggressive active traders: 5–10% total heat
- Conservative systematic traders: 2–5% total heat
- Professional quant funds: often 1–3% total heat across all open positions

---

## 9. Margin and Leverage as a Risk Discipline

Leverage amplifies both gains and losses proportionally. The risk discipline perspective treats leverage not as an opportunity but as a **risk amplifier that compresses the time to ruin**.

### Effective Leverage

```
Effective Leverage = Total Position Size / Account Equity
```

*Example:* $10,000 account controlling $100,000 worth of positions → 10:1 effective leverage.

### The Leverage Trap

With 10:1 leverage, a 1% adverse move in the underlying produces a **10% loss on equity**. A 10% adverse move produces a 100% loss — total wipe-out without a stop. This is why stop placement becomes **mandatory** when using leverage, not optional.

### Margin Call Mechanics

When account equity falls below the broker's maintenance margin requirement, a margin call occurs:
1. Broker demands additional funds (margin call)
2. If not met, broker liquidates positions — often at the worst possible moment in a fast market
3. Slippage in liquidation can produce losses *beyond* the account balance (negative equity)

The risk discipline approach: **size positions so that the stop loss is hit before the margin call is ever approached**. Your stop should be the trigger for exit, not a margin call. See `references/forex-and-currency-trading.md` for FX-specific margin call and stop-out levels.

---

## 10. Performance Metrics: Sharpe, Sortino, Calmar

These ratios measure **risk-adjusted return** — not just how much the account made, but how much was made *relative to the risk taken*. They enable comparison between strategies with different return/risk profiles.

### Sharpe Ratio

```
Sharpe = (R_p − R_f) / σ_p
```

where:
- `R_p` = portfolio/strategy annualized return
- `R_f` = risk-free rate (e.g., T-bill yield)
- `σ_p` = annualized standard deviation of returns (total volatility)

**Interpretation:** >1.0 generally considered acceptable; >2.0 good; >3.0 excellent. The Sharpe ratio penalizes *all* volatility including upside volatility (large gains reduce the Sharpe if they add variance).

### Sortino Ratio

```
Sortino = (R_p − R_f) / σ_d
```

where `σ_d` = downside deviation (standard deviation of *negative* returns only).

**Why Sortino is preferred by many practitioners:** It only penalizes downside volatility — unexpected losses — not upside volatility (unexpected gains). A strategy with large, lumpy wins but small, consistent losses will score better on Sortino than Sharpe, which may better reflect a skilled trader's actual risk. [^7]

Target thresholds: >1.5 considered good; >2.0 excellent.

### Calmar Ratio

```
Calmar = Annualized Return / Maximum Drawdown
```

Named by Terry Young (1991, *Futures* magazine). Uses *actual worst-case loss experience* rather than statistical volatility. Typically calculated over a 3-year period.

**Why Calmar matters:** It captures the lived experience of trading a strategy — the worst single event you would have endured. A strategy with a great Sharpe but a 60% max drawdown may be unlivable in practice; the Calmar captures that. [^7]

Target: >3.0 considered excellent for active trading strategies.

### Comparative Use

| Ratio | Risk Measure | Best For |
|---|---|---|
| Sharpe | Total volatility (σ) | General comparison, symmetric strategies |
| Sortino | Downside deviation only | Asymmetric strategies (more upside than downside) |
| Calmar | Maximum drawdown | Trend-following, strategies with fat-tail risk |

A strong strategy scores well on all three. If Sortino >> Sharpe, that's a signal the strategy's volatility is mostly to the upside — potentially good. If the Calmar is low despite an acceptable Sharpe, the strategy has a tail-risk problem (catastrophic drawdowns).

---

## Anti-Patterns

1. **Risking a fixed *number of shares* or *contracts* rather than a fixed *percent of risk*** — this leads to inconsistent exposure as account size changes.
2. **Using full Kelly** — dramatically over-allocates and produces devastating drawdowns in practice; always use fractional Kelly.
3. **Moving the stop after entry** — overrides the position-sizing framework; the stop defines 1R and changing it invalidates the expectancy calculation.
4. **Ignoring portfolio heat** — running 15 correlated 2% positions is 30% heat, not 2% per trade; the trades are not independent.
5. **Averaging down into losers** — increases exposure in the direction a trade is already failing; violates fixed-fractional discipline by raising 1R after entry.
6. **Letting losers run and cutting winners short** — the behavioral disposition effect; produces negative expectancy even in systems with good entries.
7. **Confusing win rate with edge** — high win rates with small wins and large losses produce negative expectancy (see Section 4).

---

## Disconfirming Evidence and Limitations

- **Kelly criterion relies on accurate parameter estimation**: If your win rate estimate is biased (e.g., limited backtest data, look-ahead bias), Kelly can misallocate badly. Real trading rarely offers the perfectly repeating distributions Kelly assumes.
- **Fixed fractional doesn't prevent ruin from catastrophic events**: A gap down far below a stop (earnings gap, overnight news) can create a single loss far larger than 1R, making risk-of-ruin calculations optimistic.
- **Position sizing "accounts for 91% of variability in performance"** (Van Tharp's claim)[^5] — this figure refers to variance in final outcomes given a *fixed* system; it does not mean a bad trading system becomes good with optimal sizing.
- **Drawdown calculations are path-dependent**: The same strategy can show different max drawdowns in different time periods; a 3-year Calmar may miss a catastrophic event outside the window.

---

## References

[^1]: Quantstrategy.io — "The Power of Fixed Fractional Position Sizing" — https://quantstrategy.io/blog/the-power-of-fixed-fractional-position-sizing-calculating/

[^2]: Quantstrategy.io — "Backtesting Position Sizing Models: Measuring Drawdown and MAE" — https://quantstrategy.io/blog/backtesting-position-sizing-models-measuring-drawdown-and/

[^3]: Coriva — "Kelly Criterion and Position Sizing: From Formula to Quant Practice" — https://coriva.eu.org/en/kelly-criterion-position-sizing/

[^4]: Enlightened Stock Trading — "Kelly Criterion: The Smartest Way to Manage Risk & Maximize Profits" (half-Kelly growth rate retention) — https://enlightenedstocktrading.com/kelly-criterion/; Backtestbase — "Kelly Criterion Calculator" — https://www.backtestbase.com/education/how-much-risk-per-trade

[^5]: Van Tharp Institute — "Tharp Think Trading Concepts" (R-multiples, expectancy, CPR formula) — https://vantharpinstitute.com/tharp-think-trading-concepts/; P&L Ledger — "Expectancy & R-multiples: the plain-English guide" — https://www.pnlledger.com/expectancy-r-multiples-the-plain-english-guide/

[^6]: New Trader U — "Risk of Ruin Formula" — https://www.newtraderu.com/2021/03/13/risk-of-ruin-formula/; The Arca Labs — "Risk of Ruin: Drawdown Math & Survival" — https://thearcalabs.com/en/insights/risk-of-ruin-trading/; Balsara, N.J. (1992) *Money Management Strategies for Futures Traders* — Wiley (foundational research cited across risk of ruin literature).

[^7]: Foxholm Financial — "Risk-Adjusted Return Metrics: Sharpe, Sortino & Calmar Ratios" — https://foxholm.com/q/concepts/risk-adjusted-returns/; Optimized Portfolio — "Sharpe Ratio vs. Sortino vs. Calmar" — https://www.optimizedportfolio.com/risk-adjusted-return/

*verified-as-of: 2026-06-21*
