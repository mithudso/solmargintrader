<!-- Provenance: reference under the `trading-and-investing` hub. Mirrored from ~/.claude/skills/trading-and-investing/references/forex-and-currency-trading.md by scripts/persist-spoke.mjs. -->

# Forex and Currency Trading (spoke)

A spoke of the **`trading-and-investing`** hub. It covers the **foreign exchange (FX) market mechanics** for a retail participant — how the market is structured, how currency pairs work, how to calculate pip values and P&L, leverage and margin mechanics, carry trade dynamics, and when to trade.

> **Educational information only — NOT financial, investment, or trading advice.** The FX market is large, liquid, and highly leveraged. ESMA-regulated brokers are required to disclose that **74–89% of retail CFD accounts lose money** when trading leveraged products including forex (verified-as-of: 2026). CFTC data shows similar figures for US retail forex (~75–80% lose money over time). Verify current regulatory requirements, broker terms, and leverage caps before trading.

## Contents

1. [Market Structure and Participants](#1-market-structure-and-participants)
2. [Currency Pairs: Majors, Minors, Exotics](#2-currency-pairs-majors-minors-exotics)
3. [Reading a Forex Quote](#3-reading-a-forex-quote)
4. [Pips: Definition and Value Calculation](#4-pips-definition-and-value-calculation)
5. [Lot Sizes](#5-lot-sizes)
6. [Leverage and Margin Mechanics](#6-leverage-and-margin-mechanics)
7. [P&L Calculation](#7-pl-calculation)
8. [Carry Trade and Rollover Rates](#8-carry-trade-and-rollover-rates)
9. [FX Sessions and Overlap Timing](#9-fx-sessions-and-overlap-timing)
10. [Transaction Costs: Spread and Commission](#10-transaction-costs-spread-and-commission)

---

## 1. Market Structure and Participants

The foreign exchange market is the **world's largest financial market** with average daily turnover of **$9.6 trillion** (BIS Triennial Survey, April 2025, up 28% from $7.5 trillion in April 2022). [^1]

### OTC Structure (Not an Exchange)

Unlike stocks (NYSE/Nasdaq), forex has **no central exchange**. It is an **over-the-counter (OTC) market** where participants trade directly with each other or through intermediaries. This means:
- No single centralized order book
- Prices vary slightly between providers
- 24-hour operation (Monday open in Wellington → Friday close in New York)
- No circuit breakers; price discovery is continuous

### The Tier System

| Tier | Participants |
|---|---|
| 1 (Interbank) | Central banks, tier-1 commercial banks (JPMorgan, Deutsche Bank, Citi), sovereign wealth funds — trade directly with each other at the tightest spreads |
| 2 (Institutional) | Hedge funds, asset managers, large corporates — access interbank through prime brokers |
| 3 (Retail) | Retail traders accessing the market through retail forex brokers, who act as intermediaries to the tier-1/2 market |

### Broker Types

| Type | How It Works | Conflict of Interest? |
|---|---|---|
| **Market Maker (Dealing Desk)** | Broker takes the other side of your trade; sets its own bid/ask | Yes — broker profits from your losses |
| **ECN (Electronic Communication Network)** | Routes your order to a pool of liquidity providers (banks, other brokers); charges commission | No — broker earns commission regardless |
| **STP (Straight-Through Processing)** | Passes your order directly to a liquidity provider without a dealing desk | Minimal — broker adds a markup to the spread |

**Key distinction for retail traders:** An ECN/STP broker's interests are aligned with the trader's success (more trading = more commission); a market-making broker profits when traders lose.

### USD Dominance

The US dollar is on one side of **89.2%** of all forex transactions (BIS 2025). EUR/USD is the most traded pair, accounting for approximately 22% of global FX turnover. [^1]

---

## 2. Currency Pairs: Majors, Minors, Exotics

All forex transactions involve the simultaneous **buying of one currency and selling of another**, quoted as a pair: **BASE/QUOTE**.

### Major Pairs (involve USD on one side; highest liquidity, lowest spreads)

| Pair | Nickname | Base / Quote |
|---|---|---|
| EUR/USD | "Fiber" | Euro / US Dollar |
| GBP/USD | "Cable" | British Pound / US Dollar |
| USD/JPY | "Ninja" | US Dollar / Japanese Yen |
| USD/CHF | "Swissie" | US Dollar / Swiss Franc |
| AUD/USD | "Aussie" | Australian Dollar / US Dollar |
| NZD/USD | "Kiwi" | New Zealand Dollar / US Dollar |
| USD/CAD | "Loonie" | US Dollar / Canadian Dollar |

### Minor Pairs / Cross Pairs (no USD; moderate liquidity)

Cross pairs are currency pairs that do not include the USD:
- EUR/GBP, EUR/JPY, GBP/JPY ("Geppy"), EUR/CHF, AUD/JPY, etc.
- Generally wider spreads than majors; can exhibit sharp moves when both constituent currencies move simultaneously

### Exotic Pairs (one emerging market currency; low liquidity, wide spreads)

- USD/TRY (Turkish Lira), USD/ZAR (South African Rand), EUR/PLN, USD/MXN
- High volatility, high spread costs, susceptible to political/economic shocks
- Generally not recommended for new traders

---

## 3. Reading a Forex Quote

A forex quote: **EUR/USD = 1.0852 / 1.0854**

| Element | Value | Meaning |
|---|---|---|
| Base currency | EUR | The currency you're buying (going long) or selling (going short) |
| Quote currency | USD | The currency in which the price is expressed |
| Bid price | 1.0852 | Price at which the broker will **buy** the base (you sell at this) |
| Ask price | 1.0854 | Price at which the broker will **sell** the base (you buy at this) |
| Spread | 0.0002 (2 pips) | The broker's built-in cost on the transaction |

**Reading the quote:** EUR/USD = 1.0852 means 1 Euro buys 1.0852 US Dollars. If you buy EUR/USD, you believe the Euro will strengthen (EUR goes up, USD goes down relative to EUR).

---

## 4. Pips: Definition and Value Calculation

### What Is a Pip?

A **pip** (percentage in point) is the standard unit of movement for a forex pair:
- For most pairs (EUR/USD, GBP/USD, etc.): **1 pip = 0.0001** (4th decimal place)
- For JPY pairs (USD/JPY, EUR/JPY, etc.): **1 pip = 0.01** (2nd decimal place, because JPY trades in much larger whole numbers)

Many brokers now quote to a **5th decimal** (or 3rd for JPY pairs), called a **pipette** (0.1 pip = fractional pip).

*Example:* EUR/USD moves from 1.0852 to 1.0862 → moved **10 pips**. USD/JPY moves from 149.50 to 150.50 → moved **100 pips**.

### Pip Value Formula

The value of one pip depends on:
1. The pip size in decimal (0.0001 or 0.01)
2. The current exchange rate (for pairs where USD is not the quote currency)
3. The lot size (number of units)

**General formula:**
```
Pip Value = (Pip in Decimal / Exchange Rate) × Lot Size
```

### EUR/USD (USD-quoted pair with USD account)

For pairs where USD is the quote currency, the exchange rate cancels out, giving a **fixed pip value**:
```
Pip Value = (0.0001 / 1.0854) × 100,000 ≈ $9.21 per pip per standard lot
```

In practice, the pip value for EUR/USD in a USD account is approximately $10 (the rate fluctuates slightly as EUR/USD moves). The standard simplification used by brokers:

| Lot Type | Units | Pip Value (USD-quoted pairs, USD account) |
|---|---|---|
| Standard | 100,000 | ~$10.00 per pip |
| Mini | 10,000 | ~$1.00 per pip |
| Micro | 1,000 | ~$0.10 per pip |
| Nano | 100 | ~$0.01 per pip |

### USD/JPY (USD-base pair, JPY quote)

For JPY pairs, the pip value in USD depends on the current exchange rate:
```
Pip Value = (0.01 / USD/JPY rate) × Lot Size
```

*Example at USD/JPY = 150.50:*
- Standard lot: (0.01 / 150.50) × 100,000 = **$6.64 per pip**
- At USD/JPY = 130.00: (0.01 / 130.00) × 100,000 = **$7.69 per pip**

**Key insight:** JPY pip values change as the exchange rate changes. A 16% change in USD/JPY (130 → 150) produces a 16% change in per-pip dollar value — an important consideration when sizing FX positions by dollar risk. [^2]

### Connecting to Position Sizing

To apply the `trading-risk-management` position sizing formulas to forex:
```
Position Size (lots) = Dollar Risk per Trade / (Stop Distance in Pips × Pip Value)
```

*Example:* $500 risk budget, 30-pip stop on EUR/USD (pip value = $10/pip, standard lot):
```
Position Size = $500 / (30 × $10) = $500 / $300 = 1.67 standard lots
```
→ Approximately 1.6 standard lots (or 16 mini lots).

---

## 5. Lot Sizes

| Lot Type | Units of Base Currency | Typical USD Pip Value (USD pairs) |
|---|---|---|
| Standard lot | 100,000 | ~$10.00 |
| Mini lot | 10,000 | ~$1.00 |
| Micro lot | 1,000 | ~$0.10 |
| Nano lot | 100 | ~$0.01 |

**Practical note:** Many retail brokers allow fractional lots (e.g., 0.25 standard lots = 25,000 units). This enables precise position sizing to match a specific dollar risk.

Most brokers set the minimum trade size at 0.01 lots (1 micro lot = 1,000 units). For a trader with a $1,000 account risking 1% ($10) with a 20-pip stop: position size = $10 / (20 × $0.10) = 5 micro lots — well within most broker minimums.

---

## 6. Leverage and Margin Mechanics

### Leverage Defined

```
Leverage ratio = Trade Notional Value / Margin Required
```

*Example:* $1,000 margin controls $50,000 notional → 50:1 leverage.

### Required Margin Formula

```
Margin Required = Notional Value / Leverage Ratio
                = Trade Size × Contract Value / Leverage
```

*Example:* 1 standard lot EUR/USD at 1.0852, with 50:1 leverage:
- Notional = 100,000 × 1.0852 = $108,520
- Margin Required = $108,520 / 50 = **$2,170.40**

### US Leverage Caps (CFTC/NFA) `verified-as-of: 2026-06-21`

The Commodity Futures Trading Commission (CFTC) and National Futures Association (NFA) cap retail forex leverage for US residents: [^3]

| Currency Type | Maximum Leverage | Minimum Margin Required |
|---|---|---|
| Major pairs (see below) | 50:1 | 2% of notional |
| All other pairs | 20:1 | 5% of notional |

**Major pairs per CFTC/NFA:** GBP, CHF, CAD, JPY, EUR, AUD, NZD, SEK, NOK, DKK (vs USD).

### European Leverage Caps (ESMA MiFID II)

| Currency Type | Maximum Leverage |
|---|---|
| Major forex pairs | 30:1 |
| Non-major forex pairs | 20:1 |
| Gold | 20:1 |
| Other commodities | 10:1 |

### Margin Call and Stop-Out Mechanics

1. **Initial margin:** Deposited to open the position (e.g., 2% for majors at 50:1)
2. **Used margin:** Total margin committed to all open positions
3. **Free margin:** Equity − Used Margin = available for new positions or absorbing losses
4. **Margin level:** (Equity / Used Margin) × 100%
5. **Margin call level:** When margin level falls below a broker threshold (commonly 100%), the broker sends a warning to deposit funds or close positions
6. **Stop-out level:** When margin level falls further (commonly 50%), the broker begins automatically closing the largest losing position(s) until margin level recovers

CFTC regulations require that when a customer's security deposits fall below required minimums, the Forex Dealer Member must collect additional funds or liquidate positions. [^3]

**Risk:** In fast-moving markets, brokers may liquidate before a formal margin call notice is received. Slippage during liquidation can produce a final account balance below zero (negative equity) — some brokers have negative balance protection that caps losses at zero, others do not.

### Effective Leverage vs. Permitted Maximum

Just because leverage up to 50:1 is permitted does not mean 50:1 is appropriate. Using a 30-pip stop on USD/JPY at 50:1 leverage with a $2,000 account:
- 30 pips × $6.64/pip × 1 standard lot = $199.20 loss to the stop
- That's ~10% of account on one trade — far exceeding the 1–2% risk management guideline
- Effective risk management typically implies using **far less than the maximum permitted leverage**

---

## 7. P&L Calculation

### General Formula

```
P&L (in quote currency) = (Exit Price − Entry Price) × Lot Size × Units per Lot
                        = Price Change × Total Units
```

For a **long** (buy) position: profit when exit > entry.
For a **short** (sell) position: profit when exit < entry.

### Example 1: Long EUR/USD (USD-quoted pair, USD account)

- Buy 1 standard lot EUR/USD at **1.0852**
- Sell (close) at **1.0882**
- Price change = 1.0882 − 1.0852 = **0.0030 = 30 pips**
- P&L = 30 pips × $10.00/pip = **+$300**

*Using the formula directly:*
- P&L = (1.0882 − 1.0852) × 100,000 = 0.0030 × 100,000 = **$300**
- (Already in USD since USD is the quote currency)

### Example 2: Short EUR/USD

- Sell 1 standard lot EUR/USD at **1.0852**
- Buy (close) at **1.0822** (price fell 30 pips)
- P&L = (1.0852 − 1.0822) × 100,000 = 0.0030 × 100,000 = **+$300**

- If price instead rose to 1.0882: P&L = (1.0852 − 1.0882) × 100,000 = −0.0030 × 100,000 = **−$300**

### Example 3: Long USD/JPY (JPY quote currency, USD account)

P&L is first calculated in the quote currency (JPY), then converted to USD.

- Buy 1 standard lot USD/JPY at **150.50**
- Sell (close) at **151.50** (moved 100 pips in favor)
- P&L (JPY) = (151.50 − 150.50) × 100,000 = 1.00 × 100,000 = **¥100,000**
- Convert to USD at close rate (151.50): P&L (USD) = ¥100,000 / 151.50 = **$660.07**

*Pip-method shortcut:* 100 pips × $6.64/pip (at 150.50) ≈ $664 (slight difference due to rate change during trade).

### Example 4: Short USD/JPY

- Sell 1 standard lot USD/JPY at **150.50**
- Buy back at **149.50** (moved 100 pips in favor)
- P&L (JPY) = (150.50 − 149.50) × 100,000 = ¥100,000
- Convert at close rate (149.50): P&L (USD) = ¥100,000 / 149.50 = **$668.90**

### Converting P&L to Account Currency

When the account currency is neither the base nor quote currency, an additional conversion step is required. For a EUR account trading USD/JPY:
1. Calculate P&L in JPY (quote currency)
2. Convert JPY to EUR at current EUR/JPY rate

Most brokers perform this conversion automatically and display P&L in the account's home currency. [^4]

### Realized vs. Unrealized P&L

- **Open (unrealized) P&L:** mark-to-market value of open positions at current market price; fluctuates continuously
- **Closed (realized) P&L:** P&L locked in when position is closed; affects account equity permanently

---

## 8. Carry Trade and Rollover Rates

### Carry Trade Mechanics

The **carry trade** exploits the interest rate differential between two currencies. A trader:
1. **Borrows** (short sells) a low-interest-rate currency (e.g., Japanese yen, historically near-zero or negative interest rates)
2. **Invests** (buys) a high-interest-rate currency (e.g., USD, AUD, during periods of elevated rates)
3. Earns the **interest rate differential** as long as the position is held

The P&L has two components:
- **Price appreciation/depreciation** (the standard FX trade)
- **Carry income** (daily rollover credits/debits)

### Rollover / Swap Rates

Every forex position held past the daily **rollover time** (typically 5:00 PM New York time) receives a daily credit or debit based on the interest rate differential between the two currencies:

```
Swap Credit/Debit ≈ (Interest Rate of Long Currency − Interest Rate of Short Currency)
                    × Notional Value / 365 (or 360 for some currencies)
```

The broker keeps a portion of the differential as a fee. Triple rollover applies on Wednesday (settling Friday trades to account for the weekend).

*Example:* Long AUD/USD when AUD interest rate = 4.35% and USD = 5.25%:
- Differential = 5.25% − 4.35% = **−0.90%** (negative carry — you pay because you're borrowing at the higher rate, i.e., short USD, which now has the higher rate)
- Daily swap ≈ −0.90% × $100,000 / 365 ≈ **−$2.47 per day** per standard lot

*Positive carry example:* Long USD/JPY when USD rate >> JPY rate (Japan maintained near-zero rates for decades):
- If USD rate = 5.25%, JPY = 0.10%: differential = +5.15%
- Daily swap ≈ +5.15% × $100,000 / 365 ≈ **+$14.11 per day** per standard lot

### Historical JPY Carry Trade

The Japanese yen has been the archetypal **funding currency** for carry trades for decades because the Bank of Japan maintained near-zero and negative interest rates from the late 1990s through 2024, while higher-yielding currencies (AUD, USD, EM currencies) provided strong carry income.

### The Carry Unwind Risk

The carry trade is not risk-free income — it carries **asymmetric risk**: carry income accumulates slowly (daily), while a carry unwind can occur rapidly and violently.

**August 2024 JPY carry unwind:** Estimates suggested over **$4 trillion** in yen-funded carry positions globally as of mid-July 2024. When the Bank of Japan raised rates and simultaneously the US labor market showed weakness (driving USD lower), USD/JPY fell from above 161.00 to approximately 142.00 — an 11% move in about 3 weeks. This wiped out years of accumulated carry income for many participants. [^5]

**Carry unwind mechanics:**
1. Event triggers concern (rate policy change, risk-off sentiment, macro shock)
2. Carry traders begin closing positions (selling high-yield, buying back funding currency)
3. This further strengthens the funding currency, causing more carry unwinding
4. Self-reinforcing spiral: sharp, fast appreciation of the funding currency (JPY strengthening)

**Key risk management implication:** Carry trades require position sizing that accounts for sharp adverse moves, not just the expected steady-state appreciation. A 10–15% move against a leveraged carry position can exceed the account's total equity. [^5]

---

## 9. FX Sessions and Overlap Timing

The forex market operates **24 hours a day, 5 days a week** (Sunday evening UTC to Friday evening UTC). It is divided into regional trading sessions based on major financial center hours. All times in **UTC (Universal Coordinated Time)**. [^6]

### Session Hours (standard time; DST shifts ±1 hour)

| Session | Open (UTC) | Close (UTC) | Characteristics |
|---|---|---|---|
| **Wellington/Sydney** | 21:00 (Sun) | 06:00 | Lowest volume; AUD/NZD pairs most active |
| **Tokyo (Asian)** | 00:00 | 09:00 | Medium volume; JPY crosses most active; generally calmer range trading |
| **London** | 07:00 | 16:00 | **Largest session** by volume; high volatility especially at open; EUR, GBP most active |
| **New York** | 13:00 | 22:00 | Second largest; USD pairs highly active; major US data releases |

*Note: Daylight Saving Time (US vs UK) can shift overlaps by 1 hour seasonally. The UK observes BST (UTC+1) March–October; the US observes EDT (UTC−4) March–November. Clocks align in spring and fall for ~3-week periods.*

### Session Overlaps (Peak Liquidity and Volatility)

| Overlap | UTC Time | Why It Matters |
|---|---|---|
| **Tokyo–London** | 07:00–09:00 | One hour of both sessions open; moderate volume increase; EUR/JPY active |
| **London–New York** | 13:00–16:00 | **Highest volume of any time in the 24-hour cycle;** two largest financial centers simultaneously active; tightest spreads; most major economic data releases (US and European) |

**London-New York overlap (13:00–16:00 UTC) is the prime forex trading window:**
- Highest liquidity → tightest bid/ask spreads → lower transaction costs
- Most institutional order flow → cleaner price action
- Major US and European economic releases (NFP, CPI, ECB press conferences)
- EUR/USD, GBP/USD, USD/JPY most active

### Session-Specific Trading Characteristics

**Tokyo session:**
- Lower volatility; pairs tend to range-trade rather than trend
- JPY pairs (USD/JPY, EUR/JPY, AUD/JPY) most responsive to Bank of Japan news
- Good for range strategies on JPY crosses

**London session:**
- Largest single session; sets the dominant trend for the day on most pairs
- Major institutional order flow; opens with breakout moves common (especially in EUR/GBP, EUR/USD)
- UK economic data releases at session open drive GBP volatility

**New York session:**
- Dominant driver: USD-related news (Fed statements, NFP, CPI, GDP)
- Session close sees volume drop sharply; spreads widen from ~20:00 UTC onward
- End-of-session (after 20:00 UTC) through Asian open tends to be the lowest-liquidity period of the week

---

## 10. Transaction Costs: Spread and Commission

Transaction costs directly subtract from every trade's P&L. For a round-turn trade (open + close), the total cost is paid twice (once at open bid/ask, once at close).

### Spread-Only Brokers (Market Makers)

Broker earns revenue by widening the bid-ask spread above the interbank rate.

*Example:* Interbank EUR/USD spread = 0.1 pip. Broker charges 1.5 pips to retail customer. The 1.5-pip spread represents the full transaction cost per round-turn **per side** (so 3 pips total for open + close).

For 1 standard lot EUR/USD with 1.5-pip spread:
- Open cost: 1.5 pips × $10/pip = $15.00
- Close cost: 1.5 pips × $10/pip = $15.00
- **Total round-turn cost: $30.00**

### Commission-Based Brokers (ECN/STP)

Broker passes through near-interbank pricing and charges a commission per trade.

*Example:* 0.2-pip spread + $7.00/standard lot commission:
- Open cost: 0.2 pips × $10/pip + $7.00 = $2.00 + $7.00 = $9.00
- Close cost: same
- **Total round-turn cost: $18.00** — meaningfully cheaper for high-volume or scalping traders

### Rollover/Swap Costs

Positions held overnight incur the swap credit/debit (Section 8). For short-term day traders who close all positions before rollover, swap is irrelevant. For swing traders holding multi-day positions, the cumulative swap cost (or credit) can meaningfully affect total P&L.

### Typical Spread Ranges (verified-as-of: 2026-06-21)

| Pair | Typical Spread (spread-only broker) | Typical Spread (ECN + commission) |
|---|---|---|
| EUR/USD | 0.8–1.5 pips | 0.1–0.3 pips |
| GBP/USD | 1.0–2.0 pips | 0.3–0.8 pips |
| USD/JPY | 0.8–1.5 pips | 0.1–0.5 pips |
| AUD/USD | 1.0–2.0 pips | 0.3–0.8 pips |
| Exotics (USD/TRY, etc.) | 10–50+ pips | 5–20+ pips |

Spreads widen significantly during low-liquidity periods (Asian session, economic data releases, Friday afternoon, Sunday open).

---

## Anti-Patterns

1. **Using maximum permitted leverage (50:1) without position sizing by dollar risk** — the leverage cap is a regulatory maximum, not a recommendation. Full 50:1 leverage on a standard lot with a typical 30-pip stop can risk 10–15% of a small account on a single trade.
2. **Ignoring pip value changes for JPY pairs** — treating JPY pip value as fixed ($10/pip like EUR/USD) leads to systematically incorrect position sizing; recalculate based on current rate.
3. **Holding carry trades without accounting for unwind risk** — the 2008 and 2024 JPY carry unwinds destroyed years of accumulated carry income in days; carry positions require stops sized for adverse price moves, not just carry income.
4. **Trading during low-liquidity windows (Asian session close, Sunday open)** — wide spreads and thin order books produce erratic price action and higher costs.
5. **Confusing the bid price with the ask price when calculating costs** — always buy at the ask (higher) and sell at the bid (lower); the spread is always paid by the retail trader.
6. **Not accounting for swap costs on multi-day positions** — overnight negative swaps can erode edge on short-duration strategies; check the broker's swap schedule before holding positions overnight.

---

## Key Statistics

- **Market size:** $9.6 trillion average daily turnover (BIS Triennial Survey, April 2025) [^1]
- **USD dominance:** on one side of 89.2% of all trades (BIS 2025) [^1]
- **Retail loss rate:** 74–89% of retail CFD accounts lose money (ESMA-regulated brokers, data 2026) [^7]
- **US retail forex:** ~75–80% of retail customers lose money (CFTC data) [^7]
- **Largest 2024 carry unwind:** USD/JPY fell ~11% in 3 weeks (July–August 2024), from ~161 to ~142, representing an estimated $4 trillion+ unwind [^5]

---

## References

[^1]: Bank for International Settlements — "OTC foreign exchange turnover in April 2025," BIS Triennial Central Bank Survey — https://www.bis.org/statistics/rpfx25_fx.htm; BIS Press Release — "Global FX trading hits $9.6 trillion per day in April 2025" — https://www.bis.org/press/p250930.htm

[^2]: Trade That Swing — "The Definitive Guide on Forex Pip Value Calculation" — https://tradethatswing.com/the-definitive-guide-on-forex-pip-value-calculation/; BabyPips — "Pip Value Calculator" — https://www.babypips.com/tools/pip-value-calculator; Wiley (Kathy Lien) — "How to Calculate Pip Values and Examples" — https://onlinelibrary.wiley.com/doi/pdf/10.1002/9781119204831.app2

[^3]: CFTC — "Final Rule Regarding Retail Foreign Exchange Transactions" (sets 50:1/20:1 leverage caps) — https://www.cftc.gov/sites/default/files/idc/groups/public/@newsroom/documents/file/forexfinalrulefactsheet.pdf; NFA — "Forex Transactions: Regulatory Guide" — https://www.nfa.futures.org/members/member-resources/files/forex-regulatory-guide.html; CFTC — "Customer Advisory: Eight Things You Should Know Before Trading Forex" — https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html

[^4]: Darwinex Docs — "How to calculate the P&L of a Forex trade" — https://darwinexzero.document360.io/docs/profit-loss-forex-trade; B2Broker — "How to Calculate Profit and Loss" — https://b2broker.com/news/how-to-calculate-profit-and-loss-for-your-trading-positions/; Fortrade — "What Is P/L & How Is It Calculated in Forex Trading?" — https://www.fortrade.com/a/answers/forex/what-is-pl-and-how-is-pl-calculated-in-forex-trading/

[^5]: BIS — "The market turbulence and carry trade unwind of August 2024," BIS Bulletin No. 90 — https://www.bis.org/publ/bisbull90.pdf; TastyFX — "How the carry trade works and position unwinds explained" — https://www.tastyfx.com/news/how-the-carry-trade-works-and-position-unwinds-explained/; Equiti — "Forex Carry Trade Strategy: Interest Rate Differentials & Swap Rates" — https://www.equiti.com/jo-en/news/trading-ideas/forex-carry-trade-explained-how-interest-rate-differentials-move-currencies/

[^6]: OANDA — "Forex Trading Sessions: Times, Overlaps & Best Hours" — https://www.oanda.com/us-en/trade-tap-blog/trading-knowledge/when-is-the-best-time-for-forex-trading/; FXOpen — "Global Forex Trading Time Zones: How Trading Hours Shape Strategies" — https://fxopen.com/blog/en/forex-trading-time-zones-market-hours-and-overlaps/; Startrader — "Forex Trading Sessions: Times, Overlaps & Best Hours" — https://www.startrader.com/knowledge-basics/forex-trading-sessions/

[^7]: BabyPips — "Data Confirms Grim Truth: 70-80% of Retail Traders are Unprofitable" — https://www.babypips.com/news/almost-80-percent-of-retail-traders-are-unprofitable; ESMA — MiFID II CFD loss disclosure requirements (effective January 2018); CFTC — "Customer Advisory" (cites similar US figures) — https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html

*verified-as-of: 2026-06-21*
