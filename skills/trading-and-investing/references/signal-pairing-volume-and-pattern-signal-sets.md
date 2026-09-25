---
name: signal-pairing-volume-and-pattern-signal-sets
# provenance: split from indicator-signal-implementation-and-backtesting 2026-08-04
# (that file reached ~21.7k tokens; §7-§10 moved here verbatim, section numbers preserved).
# `name:` must sit immediately after the opening fence: persist-spoke.mjs anchors
# on /^---\nname:/ and reports "no YAML frontmatter found" if a comment precedes it.
hub: trading-and-investing
version: "1.0.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  SPOKE of trading-and-investing — whether two signals are independent
  confirmation or one bet counted twice, plus the three signal families that are
  not price-oscillators: volume/breadth, candlestick and chart patterns, and
  price-action structure. Runnable pandas/numpy, no TA-Lib. Educational ONLY, NOT
  financial advice (2026). TRIGGER: is my "confirmation" redundant (correlation,
  agreement rate, PCA effective dimensionality — six indicators measured as three
  bets; Williams %R proven identical to Stochastic %K−100); which pairings are
  genuinely orthogonal; degrees-of-freedom budget; coding OBV, CLV, A/D line, CMF,
  Chaikin Oscillator, anchored VWAP, Force Index, Ease of Movement, Volume
  Profile/POC, McClellan Oscillator and Summation, Zweig Breadth Thrust; coding
  doji, marubozu, hammer, shooting star, engulfing, harami, morning/evening star;
  swing pivots, market structure/BOS/ChoCH, S/R zones, Fibonacci, floor-trader
  and Camarilla pivots, CPR, trendline fits, double top/bottom, head and
  shoulders, round-number levels; why breadth needs market-wide data, not one
  OHLCV frame. SKIP: the substrate and the trend, momentum and volatility
  implementations (§1-§4) → indicator-signal-implementation-and-backtesting; the
  backtest protocol (§5) and the regime record (§6) →
  signal-backtest-protocol-and-regime-evidence; what a pattern MEANS →
  chart-patterns-and-candlesticks, volume-and-market-breadth,
  trend-price-action-and-support-resistance.
keywords:
  - signal-redundancy
  - signal-pairing
  - effective-dimensionality
  - degrees-of-freedom
  - volume-indicators
  - market-breadth
  - anchored-vwap
  - candlestick-detection
  - chart-patterns
  - price-action-structure
  - swing-pivots
  - fibonacci
tags:
  - trading-and-investing
  - technical-analysis
  - backtesting
  - quant
  - python
whenToUse:
  - When deciding whether two indicators are independent confirmation or the same bet counted twice.
  - When implementing a volume, breadth, candlestick, chart-pattern or price-action signal and needing the exact rule and a runnable pandas/numpy reference.
  - When a stack of "confirming" indicators improved the backtest and you need the effective-dimensionality check.
  - When a breadth indicator cannot be computed from a single instrument's OHLCV and you need to know what data it actually requires.
  - When choosing which signal to add to an existing one so the addition carries new information.
---

# Signal Pairing, Volume and Pattern Signal Sets

> **Educational information only — NOT financial, investment, or tax advice.**

**What this is.** Sections 7 to 10 of
`references/indicator-signal-implementation-and-backtesting.md`, split out on
2026-08-04 when that file passed the reference size ceiling. §7 is the
independence and redundancy framework — the test for whether an added signal
carries new information — and §8-§10 are the signal families it is most often
used to judge: volume and breadth, candlesticks and chart patterns, and
price-action structure. **Section numbers are preserved** (§7.x-§10.x), so every
cross-reference to them elsewhere in this family still resolves.

**Scope.**

| For… | Go to |
|---|---|
| The implementation substrate and the trend/MA, momentum and volatility sets (§1-§4) | `references/indicator-signal-implementation-and-backtesting.md` |
| The per-signal backtest recipe (§5) and the cited regime record (§6) | `references/signal-backtest-protocol-and-regime-evidence.md` |
| What a candlestick, chart pattern or volume indicator *means* | `references/technical-analysis.md` |
| Strategy-level pairing (convex/concave sleeves) rather than signal-level | `references/strategy-failure-modes-and-synergy.md` |
| Sleeve weights and the objective that sets them | `references/sleeve-weighting-and-objective-selection.md` |
| Whether a pairing result survives on another asset | `references/cross-asset-generalisation-testing.md` |

## Contents

7. Pairing, independence and redundancy
8. Volume and market-breadth signal set
9. Candlestick and chart-pattern signals
10. Price-action and structure signals

## 7. Pairing, independence and redundancy

The premise of "confirmation" is that two signals are independent evidence. Most
indicator pairs are not — they are algebraic transforms of the same input, so
agreement between them is arithmetic, not evidence. This section gives you a test
instead of a belief.

### 7.1 Redundancy is by construction, not by coincidence

Two families collapse almost entirely:

| Family | Members | Why they co-move |
|---|---|---|
| **Moving-average transforms** | SMA/EMA/WMA crossovers, price−SMA distance, MACD (difference of two EMAs), Supertrend and Ichimoku baselines (midpoint averages) | Each is a linear or near-linear function of one or two moving averages of the same close series. MACD *is* `EMA_fast − EMA_slow`; a crossover is the sign of that same quantity. |
| **Normalized momentum** | RSI, Stochastic %K, Williams %R, CCI, ROC | Each maps "where is price now relative to its own recent range or average change" onto a bounded scale. Williams %R is (up to sign and scaling) the complement of fast Stochastic %K over the same lookback. |

**The decisive evidence that the *rule* matters more than the *indicator*.**
Chong/Ng/Liew ran two rules over the *same* RSI, *same* markets, *same* period,
and got significant results with **opposite signs**: RSI(21,50) centerline
crossover earned **+2.268% per 10 days (t = 3.394)** while RSI(N,30/70)
overbought/oversold **lost** (Milan RSI(7): **−1.163%, t = −2.371**).[^regime-10]
Lento et al. reinforce it from the other side: inverting Bollinger logic beat the
standard rule in **8 of 12** tests.[^regime-11]

The operational consequence: **classify signals by rule family (trend-continuation
vs mean-reversion), not by indicator name.** "RSI" is not a mean-reversion signal;
RSI-with-30/70-thresholds is. The same indicator appears in both families.

### 7.2 The independence test — run this, don't assume

Test the **signal vectors** (the −1/0/+1 positions you would actually hold), not
only the raw indicator lines. Two indicators can differ numerically while
producing near-identical positions, and it is the positions that determine P&L.

```python
import numpy as np, pandas as pd

def signal_redundancy(signals: pd.DataFrame) -> dict:
    """signals: DataFrame of position vectors in {-1,0,1}, one column per rule.

    Returns the pairwise correlation matrix, the agreement rate, and the number
    of PCA components needed to explain 90% of variance -- the effective number
    of independent bets you are actually taking.
    """
    s = signals.dropna()
    corr = s.corr()

    # Agreement rate is the intuitive companion to correlation: how often do two
    # rules hold literally the same position?
    cols = s.columns
    agree = pd.DataFrame(index=cols, columns=cols, dtype=float)
    for a in cols:
        for b in cols:
            agree.loc[a, b] = (s[a] == s[b]).mean()

    # Effective dimensionality via PCA on the standardised signal matrix.
    x = (s - s.mean()) / s.std(ddof=0)
    x = x.dropna(axis=1, how="any")          # drop constant columns
    eigvals = np.linalg.svd(x.values, compute_uv=False) ** 2
    explained = eigvals / eigvals.sum()
    k90 = int(np.searchsorted(np.cumsum(explained), 0.90) + 1)

    return {
        "corr": corr,
        "agreement": agree.astype(float),
        "explained_variance": explained,
        "components_for_90pct": k90,
        "effective_independent_signals": k90,
        "nominal_signal_count": x.shape[1],
    }
```

**How to read it.** If the first one or two components explain **over ~90%** of
variance, most of your predictors are carrying the same information — that is the
standard PCA redundancy diagnostic, and it is why principal components are used
to remove multicollinearity before predictive regressions (the extracted factors
are pairwise orthogonal, which stabilises otherwise unstable coefficients and
inflated standard errors).[^pair-1][^pair-2] A bank of eight indicators that
resolves to `components_for_90pct = 2` is a two-signal system with six
decorative overlays.

Treat pairwise signal-vector correlation above roughly **0.8**, or an agreement
rate above **~0.9**, as redundant for position-sizing purposes. Those thresholds
are conventions for reading the diagnostic, not empirically calibrated constants —
the defensible claim is the *ordering* (higher = more redundant), not the cutoff.

#### Worked output — six "different" indicators are three bets

Running §7.2's function over six centered signals (MA 10/50 crossover, price vs
SMA20, MACD histogram, RSI vs 50, Stochastic %K vs 50, Williams %R vs −50) on a
3,000-bar series:

```
nominal signals            : 6
components for 90% variance: 3
explained variance ratios  : [0.684 0.168 0.075 0.05 0.024 0.0]

signal-vector correlation
                 ma_cross  price_sma20  macd_hist  rsi_50  stoch_50  willr
ma_cross_10_50       1.00         0.38       0.08    0.51      0.28   0.28
price_vs_sma20       0.38         1.00       0.62    0.83      0.82   0.82
macd_hist            0.08         0.62       1.00    0.47      0.63   0.63
rsi_center50         0.51         0.83       0.47    1.00      0.73   0.73
stoch_center50       0.28         0.82       0.63    0.73      1.00   1.00
willr_center         0.28         0.82       0.63    0.73      1.00   1.00
```

Three things to take from it:

1. **Stochastic %K and Williams %R are correlation 1.00 with a 1.00 agreement
   rate — the identical signal under two names.** Over the same lookback,
   `%R = %K − 100`, so centering both puts them on the same threshold. Anyone
   running "Stochastic confirmed by Williams %R" is counting one signal twice.
   The final explained-variance ratio of **0.000** is that exact linear
   dependency showing up in the spectrum.
2. **Six indicators resolve to three effective bets**, with the first component
   alone carrying **68%** of the variance.
3. **"Price above its 20-day average" and "RSI above 50" agree 91% of the time**
   (correlation 0.83) despite living in textbook chapters labeled *trend* and
   *momentum*.

**Scope caveat, stated because it changes what you may conclude.** This run uses a
synthetic geometric-Brownian-motion series, which has no genuine autocorrelation
or volatility clustering. The **structural** findings are data-independent and
will reproduce on any series: the %K/%R identity, the exact linear dependency,
and the within-family clustering all follow from the algebra. The **magnitudes**
of cross-family correlations are data-dependent — rerun the function on your own
instrument and timeframe before trusting any specific number above. Use it as a
diagnostic on your own signal bank, not as a table of universal constants.

### 7.3 Pairings that are defensibly independent

Independence comes from using a **different input series** or a **different
statistical question**, not a different indicator name:

| Pairing | Why it is not circular |
|---|---|
| Trend/direction filter **+** momentum timing | Different questions: "which way" vs "is the move extended". Still both price-derived — partial, not full, independence. |
| Price signal **+** volume signal (OBV, CMF, volume profile) | Genuinely different input series. Volume is not a transform of close. |
| Volatility/regime gate (ADX, realized vol) **+** directional entry | The gate answers "is any directional signal admissible now", which is orthogonal to direction. This is the pairing with the best theoretical footing, and it connects to the strongest regime evidence in §6.2 and §6.4. |
| Price signal **+** a non-price signal (fundamentals, positioning, flow) | Fully different data-generating process. The only pairing that escapes the price-transform trap entirely. |

### 7.4 The cost of searching for a good combination

This is the part practitioner writing omits. Every combination you try is another
test, and the correction for that search is brutal and measured: expanding a
26-rule universe to **7,846** turned the best rule's nominal **p = 0.042** into a
Reality-Check **p = 0.908**.[^regime-2] Marshall/Cahan/Cahan got **0 of 7,846**
profitable on intraday data after the same correction.[^regime-6] If you screen
combinations, you must report the size of the search and correct for it — see §5.

Practitioner sources converge on keeping optimizable parameters to roughly
**three or four at most**, on the reasoning that each additional parameter gives
the optimizer another degree of freedom to fit noise.[^pair-3][^pair-4] That is a
sound *direction* but a **practitioner heuristic, not a measured optimum** — no
located study establishes an optimal indicator count.

### 7.5 EVIDENCE vs LORE — read this before repeating anything

| Claim | Status |
|---|---|
| MACD, MA crossovers and price−SMA are moving-average transforms of the same series | **EVIDENCE** (algebraic; verifiable with §7.2's code) |
| Same indicator + opposite rule = opposite, significant results | **EVIDENCE** — Chong/Ng/Liew; Lento et al.[^regime-10][^regime-11] |
| PCA/orthogonalization removes indicator multicollinearity; >90% variance in 1-2 PCs signals redundancy | **EVIDENCE** (established method)[^pair-1][^pair-2] |
| Searching many rule combinations destroys significance under correction | **EVIDENCE** — STW; Marshall et al.[^regime-2][^regime-6] |
| "Stacking three moving averages measures the same thing three times" | **LORE**, but algebraically correct — the reasoning holds even though the sources are blog-tier[^pair-5] |
| Confluence requires signals from different categories (price / momentum / volume) | **LORE** — widely repeated, no controlled test located |
| Keep to 3-4 optimizable parameters | **LORE** (practitioner heuristic)[^pair-3][^pair-4] |
| **"Three diverse tools lift win rate to ~70% vs ~40% for one indicator"** | **LORE — do not repeat.** This figure circulates with no study, sample, period, or cost assumption attached. Cited here only so it can be recognised and discarded.[^pair-5] |

### 7.6 Honest limit of this section

Peer-reviewed work testing *indicator combination* specifically is thin; most of
what exists tests single rules or large mechanical rule universes. The strong
claims above are either algebraic (redundancy by construction), transferred from
the single-rule literature (the multiple-testing cost), or methodological (PCA).
The pairing advice itself is **reasoned, not empirically validated** — and it is
labeled that way rather than dressed up.

## 8. Volume and market-breadth signal set

Volume matters disproportionately here for one reason established in §7.3: it is
the **only input series in this reference that is not a transform of close**.
Every signal in §2-4 is price algebra; a volume signal is the cheapest genuine
independence you can add.

### 8.1 Implementations

All 14 outputs below were executed as a smoke test: **0 failures**, with `CLV`
and `CMF` confirmed inside [−1,1] and session-anchored VWAP confirmed to reset
at each session boundary.

```python
def obv(c, v):
    return (np.sign(c.diff()).fillna(0) * v).cumsum()

def clv(h, l, c):
    """Close Location Value: where the close sits in the bar's range, in [-1,1]."""
    rng = (h - l).replace(0, np.nan)          # guard the flat-bar divide
    return ((c - l) - (h - c)) / rng

def ad_line(h, l, c, v):
    return (clv(h, l, c).fillna(0) * v).cumsum()

def cmf(h, l, c, v, n=21):
    return (clv(h, l, c).fillna(0) * v).rolling(n).sum() / v.rolling(n).sum()

def chaikin_oscillator(h, l, c, v, fast=3, slow=10):
    ad = ad_line(h, l, c, v); return ema(ad, fast) - ema(ad, slow)

def vwap(h, l, c, v, session=None):
    """Anchored VWAP. session = grouping key (e.g. dates); None = whole series."""
    tp = (h + l + c)/3
    if session is None:
        return (tp*v).cumsum() / v.cumsum()
    return (tp*v).groupby(session).cumsum() / v.groupby(session).cumsum()

def force_index(c, v, n=13):
    return ema(c.diff() * v, n)

def ease_of_movement(h, l, v, n=14, scale=1e6):
    mid_move = ((h + l)/2).diff()
    box = (v/scale) / (h - l).replace(0, np.nan)
    return sma(mid_move/box, n)

def volume_profile(c, v, bins=24):
    """Returns (profile, poc_price) -- volume per price bin and the point of control."""
    lo, hi = float(c.min()), float(c.max())
    edges = np.linspace(lo, hi, bins+1)
    idx = np.clip(np.digitize(c.values, edges) - 1, 0, bins-1)
    prof = pd.Series(0.0, index=range(bins))
    for i, vol in zip(idx, v.values): prof.iloc[i] += vol
    centers = (edges[:-1] + edges[1:]) / 2
    return prof, float(centers[int(prof.idxmax())])

# ---- market breadth: needs MARKET-WIDE advance/decline counts, not one OHLCV ----
def ad_ratio(adv, dec): return adv / (adv + dec)

def mcclellan_oscillator(adv, dec, fast=19, slow=39):
    net = adv - dec; return ema(net, fast) - ema(net, slow)

def mcclellan_summation(adv, dec, fast=19, slow=39):
    return mcclellan_oscillator(adv, dec, fast, slow).cumsum()

def zweig_breadth_thrust(adv, dec, n=10, lower=0.40, upper=0.615):
    r = sma(ad_ratio(adv, dec), n)
    was_low = (r < lower).rolling(n).max().fillna(0).astype(bool)
    return (r > upper) & was_low.shift(1, fill_value=False)
```

### 8.2 Equations, dependencies and signal rules

| Signal | Equation | Dep | Signal rule |
|---|---|---|---|
| **OBV** | `Σ sign(ΔC)·V` — cumulative signed volume | V | divergence vs price; slope |
| **CLV** | `((C−L)−(H−C))/(H−L)`, range [−1,1] | H,L | building block, not a signal |
| **A/D line** | `Σ CLV·V` | H,L,V | divergence vs price |
| **CMF(21)** | `Σ(CLV·V)/ΣV` over n | H,L,V | sign; ±0.05 thresholds |
| **Chaikin Osc** | `EMA₃(A/D) − EMA₁₀(A/D)` | H,L,V | zero-line cross |
| **VWAP** | `Σ(TP·V)/ΣV`, `TP=(H+L+C)/3` | H,L,V | price vs VWAP; the institutional benchmark |
| **Force Index(13)** | `EMA₁₃(ΔC · V)` | V | zero cross |
| **Ease of Movement** | `SMA_n( Δmidpoint / ((V/scale)/(H−L)) )` | H,L,V | zero cross |
| **Volume Profile** | volume histogram by price bin → **POC**, value area | V | POC/value-area as S/R |
| **A/(A+D) ratio** | `advances/(advances+declines)` | **breadth** | 0.5 = neutral |
| **McClellan Osc** | `EMA₁₉(net adv) − EMA₃₉(net adv)` | **breadth** | zero cross; ±100 extremes |
| **McClellan Summation** | cumulative McClellan Oscillator | **breadth** | long-term breadth trend |
| **Zweig Breadth Thrust** | 10-day `A/(A+D)` moving from **< 0.40 to > 0.615 within 10 days** | **breadth** | rare bullish thrust |

### 8.3 Traps specific to this family

- **Breadth needs a market, not an instrument.** The last four rows require
  exchange-wide advance/decline counts. You cannot compute McClellan or Zweig
  from one symbol's OHLCV — a category error that silently produces
  nonsense if you feed it single-instrument data.
- **VWAP must be anchored.** Un-anchored cumulative VWAP over years is
  meaningless; it is a session (or explicitly anchored) statistic. The
  implementation takes a `session` key for exactly this reason, and the reset
  behavior was verified rather than assumed.
- **VWAP is also a benchmark, not only a signal.** Institutional execution is
  measured against it (§5.4 ties to TCA), which is part of why it is
  self-fulfilling intraday.
- **Cumulative series have no meaningful level.** OBV and A/D line depend
  entirely on the start bar, so only their *slope* and *divergence* carry
  information. Comparing OBV levels across instruments or across differently
  truncated histories is meaningless.
- **Flat bars break CLV.** `H == L` divides by zero — guarded above with
  `replace(0, np.nan)`. Common on illiquid names and halted sessions (§1.4).
- **Volume data quality is its own hazard** (§1.4): consolidated vs single-venue
  volume differ materially, and volume is revised.
- **Zweig thrusts are genuinely rare.** On real history they occur a handful of
  times in decades. My synthetic-data run fired 16 in 900 bars purely because
  uniform-random advance/decline counts oscillate far more than real breadth
  does — a caution about testing breadth rules on synthetic data, not a bug.

### 8.4 Backtest, regime and pairing

Backtest with §5 unchanged. On evidence: volume-based rules are the **least
badly** supported price-derived family — Gerritsen et al. found trading-range
breakout beat buy-and-hold on Bitcoin daily data while RSI and Bollinger
significantly underperformed, and VWAP's institutional-anchor role gives it a
mechanism the pure oscillators lack (§6.4, §6.6). That is a low bar, not an
endorsement; the §6.1 corrections apply here too.

**Pairing is where this family earns its place.** Per §7.3, a price signal plus a
volume signal is one of only two pairings in this reference with genuine
input-series independence. If you run one confirmation signal alongside a trend
rule, a volume signal is the defensible choice — not a second moving average.

## 9. Candlestick and chart-pattern signals

Usually taught together; must be separated for implementation, because **one is
precisely definable and the other is not**.

### 9.1 Candlestick patterns — exact definitions, verified

Every candlestick pattern reduces to arithmetic on `(O,H,L,C)`. The
implementations below were asserted against hand-built textbook bars — **10/10
candlestick assertions pass**, including negative controls (a hammer must *not*
register as a shooting star; a marubozu must *not* register as a doji).

```python
def body(o, c):            return (c - o).abs()
def rng(h, l):             return (h - l).replace(0, np.nan)   # guard flat bars
def upper_shadow(o, h, c): return h - pd.concat([o, c], axis=1).max(axis=1)
def lower_shadow(o, l, c): return pd.concat([o, c], axis=1).min(axis=1) - l

def doji(o, h, l, c, max_body=0.1):
    return body(o, c) <= max_body * rng(h, l)

def hammer(o, h, l, c, shadow_mult=2.0, max_upper=0.25):
    b = body(o, c)
    return (lower_shadow(o, l, c) >= shadow_mult * b) & \
           (upper_shadow(o, h, c) <= max_upper * rng(h, l)) & (b > 0)

def engulfing(o, c):
    """+1 bullish, -1 bearish, 0 none (2-bar)."""
    po, pc = o.shift(1), c.shift(1)
    bull = (pc < po) & (c > o) & (c >= po) & (o <= pc)
    bear = (pc > po) & (c < o) & (c <= po) & (o >= pc)
    return bull.astype(int) - bear.astype(int)

def star(o, h, l, c, max_mid_body=0.3):
    """Morning (+1) / evening (-1): big bar, small-bodied middle, reversal close."""
    b, r = body(o, c), rng(h, l)
    small_mid = b.shift(1) <= max_mid_body * r.shift(1)
    morning = (c.shift(2) < o.shift(2)) & small_mid & (c > o) & (c > (o.shift(2)+c.shift(2))/2)
    evening = (c.shift(2) > o.shift(2)) & small_mid & (c < o) & (c < (o.shift(2)+c.shift(2))/2)
    return morning.astype(int) - evening.astype(int)
```

| Pattern | Definition | Bars |
|---|---|---|
| **Doji** | `abs(C−O) <= 0.1·(H−L)` | 1 |
| **Marubozu** | `abs(C−O) >= 0.9·(H−L)` | 1 |
| **Hammer** | lower shadow ≥ 2·body, upper shadow ≤ 0.25·range | 1 |
| **Shooting star** | upper shadow ≥ 2·body, lower shadow ≤ 0.25·range | 1 |
| **Engulfing** | prior body fully inside current body, opposite colours | 2 |
| **Harami** | current body fully inside prior body | 2 |
| **Morning/evening star** | large bar → small-bodied bar → reversal bar closing past the first bar's midpoint | 3 |

**The thresholds are parameters, not physics.** `0.1`, `2.0`, `0.25`, `0.3` are
conventions. Vary one and the pattern count changes — so each variation is another
test to count against your multiple-testing N (§5.6).

### 9.2 Chart patterns — there is no canonical definition

Head and shoulders, double tops, triangles and wedges have **no agreed numeric
definition**. Every implementation silently encodes tolerances a human analyst
would eyeball: how equal two peaks must be, how far apart, how dominant the head.
That is the most important fact about this family, and why these implementations
take those tolerances as **explicit arguments**:

```python
def double_extreme(h, l, k=3, tol=0.02, min_sep=5, max_sep=60):
    """Double top (+1) / bottom (-1) at the confirming pivot. Heuristic."""

def head_and_shoulders(h, l, k=3, shoulder_tol=0.03, head_min=0.01):
    """+1 H&S top, -1 inverse. Three same-type pivots, dominant middle, outer
    extremes within shoulder_tol of each other. Heuristic."""

def converging_trendlines(h, l, k=3, lookback=60, min_r2=0.5):
    """Fits a line to pivot highs and another to pivot lows; opposite-signed
    converging slopes = triangle. Returns shape plus both r2 values, so a
    'pattern' that is really two bad fits through noise can be rejected."""
```

Verified on constructed shapes: double top flagged at the confirming pivot, H&S
flagged at the right shoulder, and a synthetic converging series correctly
classified `symmetric_triangle`.

**What the evidence says.** Lo, Mamaysky & Wang made pattern detection objective
with kernel regression — the honest way to test this family — and found all 10
patterns significant on **Nasdaq** but only **5 of 10** on NYSE/AMEX, explicitly
cautioning that this **does not imply excess trading profits** (§6.7).[^regime-22]
Treat chart patterns as a claim about information content, not profitability.

## 10. Price-action and structure signals

### 10.1 Everything here rests on swing pivots — and the naive version looks ahead

```python
def swing_pivots(h, l, k=3):
    """Fractal pivots: +1 pivot high, -1 pivot low, 0 otherwise."""
    win = 2*k + 1
    is_hi = h == h.rolling(win, center=True).max()
    is_lo = l == l.rolling(win, center=True).min()
    return is_hi.astype(int) - is_lo.astype(int)

def confirmed_pivots(h, l, k=3):
    """The SAME pivots shifted forward by k, so they are tradable."""
    return swing_pivots(h, l, k).shift(k).fillna(0)
```

**`center=True` reads k bars into the future.** A pivot at bar *t* is only knowable
at *t+k*. Using `swing_pivots` directly in a signal is the §1.3 look-ahead bug in
different clothes, and it contaminates every downstream construct — trendlines,
S/R zones, market structure, pattern detection. Verified: `confirmed_pivots`
reports the peak at index 8 where `swing_pivots` reports it at index 5, for `k=3`.

Two consequences, both verified rather than assumed:

1. **Pivots are undetectable within k bars of either series edge** — the centered
   window is incomplete, so nothing is emitted. Pinned as a regression test: a
   textbook head-and-shoulders whose first shoulder sits at index 1 yields only
   **2** pivot highs instead of 3, so H&S cannot fire. Pattern detectors need `k`
   bars of lead-in, exactly as indicators need warm-up (§1.2).
2. **Any pattern built on pivots inherits the +k confirmation lag.** A "double top
   at the peak" is knowable only k bars after the peak.

### 10.2 Levels, structure and their evidence

| Construct | Definition | Evidence status |
|---|---|---|
| **Round-number levels** | price within tolerance of a round increment | **Best-supported S/R effect** — order clustering at round numbers has peer-reviewed support; studies are catalogued in the sibling `trend-price-action-and-support-resistance` spoke |
| **Floor-trader pivots** | `P=(H+L+C)/3`, `R1=2P−L`, `S1=2P−H`, `R2=P+(H−L)`, `S2=P−(H−L)` | Mechanical; partly self-fulfilling via algorithmic order clustering |
| **Camarilla / CPR** | `C ± (H−L)·1.1/{12,6,4,2}`; CPR = `P`, `BC=(H+L)/2`, `TC=2P−BC` | Practitioner convention |
| **S/R zones** | clustered pivot prices, `min_touches` to qualify | Zone identification is subjective; the clustering tolerance is a free parameter |
| **Fibonacci retracement** | `high − r·(high−low)`, `r ∈ {0.236, 0.382, 0.5, 0.618, 0.786}` | **No robust peer-reviewed support** that these levels predict reversals better than random levels of comparable salience; frequently retrofitted after the move |
| **Market structure (HH/HL vs LH/LL)**, **BOS / ChoCH** | pivot-sequence labelling | Descriptive bookkeeping — useful, not predictive on its own |
| **Order blocks / ICT / SMC** | institutional-footprint framework | **Practitioner lore** — limited peer-reviewed validation. Deliberately not implemented here |

Verified deterministically: the 0.500 retracement equals the swing midpoint
exactly; 0.618 and the 1.618 extension match their closed forms; floor-trader `P`,
`R1`, `S1` match their formulas; and `trendline` recovers slope 2.0 with r² = 1.0
on an exact line.

### 10.3 Traps specific to these families

- **The look-ahead in `center=True`** (§10.1) — the dominant bug in this family.
- **Tolerance sensitivity is unbounded.** Loosening `shoulder_tol` from 0.03 to
  0.06 roughly doubles the H&S count. Fix tolerances before looking at results
  (§5.7 step 2) and count variants in your N.
- **`r2` is your noise filter.** `converging_trendlines` returns r² for both fitted
  lines precisely so a "triangle" that is two badly-fitted lines through noise can
  be rejected. Do not discard it.
- **Pattern counts are not trade counts.** A detector firing 40 times is not 40
  independent observations if the patterns overlap (§5.2).
- **Subjectivity is the honest headline.** Two competent analysts disagree on
  whether a shape is a head and shoulders. A backtest of this family tests *your
  tolerances*, not "head and shoulders".

### 10.4 Backtest and pairing

Backtest with §5 unchanged, plus one addition: because tolerances are free
parameters, this family is the most exposed to multiple testing in the whole
reference (§5.6). Report the tolerance set you fixed and how many you tried.

For pairing (§7): pattern and price-action signals are **price-derived**, so they
are *not* independent of §2-4. A double top "confirmed" by RSI divergence is one
bet, not two. The independent companions remain volume (§8) and a volatility
regime gate (§7.3).

## References

Footnote ids are scoped per concept (`[^<slug>-n]`) so adding a concept never
renumbers an earlier one.

### Concept 7 — pairing, independence and redundancy

Sourcing note: peer-reviewed work on indicator *combination* is thin. The load-bearing
claims in §7 are algebraic (demonstrated by the §7.2 worked output), transferred from the
single-rule literature (`[^regime-2]`, `[^regime-6]`, `[^regime-10]`, `[^regime-11]`), or
methodological. Practitioner-tier sources are marked and used only for claims labeled LORE.

[^pair-1]: Macrosynergy, "Using principal components to construct macro trading signals." PCA compresses standardised signals to reduce dimensionality and information redundancy; components are pairwise orthogonal, removing multicollinearity that otherwise produces unstable coefficients and inflated standard errors. https://macrosynergy.com/research/using-principal-components-to-construct-macro-trading-signals/ (blog, practitioner-quant)
[^pair-2]: "A Correlation-Embedded Attention Module to Mitigate Multicollinearity: An Algorithmic Trading Application," *Mathematics* 10(8):1231. Multicollinearity among correlated technical features as a modelling problem in algorithmic trading. https://www.mdpi.com/2227-7390/10/8/1231 (paper)
[^pair-3]: Carver, "The three kinds of (over)fitting." Degrees-of-freedom framing of overfitting. https://qoppac.blogspot.com/2015/11/the-three-kinds-of-overfitting.html (blog, practitioner)
[^pair-4]: Quanthop, "Parameter Optimization Without Overfitting: Walk-Forward Analysis and Out-of-Sample Testing." Source of the 3-4-parameter heuristic. https://quanthop.com/learn/backtesting-optimization/parameter-optimization (blog)
[^pair-5]: Confluence practitioner literature, blog tier — e.g. https://www.vtmarkets.com/discover/confluence-in-trading-why-it-improves-entries/ and https://thexbrat.com/confluence-trading-strategy-a-complete-guide/ . These are the circulating source of the unsupported "~70% vs ~40% win rate" claim; cited so the figure can be identified and discarded, NOT as support for it. The algebraic core of their "stacking three moving averages measures the same thing three times" argument is nonetheless correct.

### Concept 6 — regime-performance evidence (entries cited from §7 and §9; the full Concept 6 list lives in `references/signal-backtest-protocol-and-regime-evidence.md`)

[^regime-2]: Sullivan, Timmermann & White (1999), "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap," *Journal of Finance* 54(5):1647-1691. 7,846 rules, White's Reality Check. S&P futures nominal p=0.042 → RC p=0.908; DJIA break-even cost 0.27%/trade. https://eprints.lse.ac.uk/119144/1/dp303.pdf (paper)
[^regime-6]: Marshall, Cahan & Cahan (2008), *Journal of Empirical Finance* 15(2):199-210. Intraday SPDR 2002-03; 0 of 7,846 rules profitable after snooping correction. https://www.sciencedirect.com/science/article/abs/pii/S0927539807000588 (paper)
[^regime-10]: Chong, Ng & Liew (2014), "Revisiting the Performance of MACD and RSI Oscillators," *Journal of Risk and Financial Management* 7(1):1-12. Five OECD indices 1976-2002. https://www.mdpi.com/1911-8074/7/1/1 (paper)
[^regime-11]: Lento, Gradojevic & Wright (2007), "Investment information content in Bollinger Bands?" *Applied Financial Economics Letters* 3:263-267. https://www.researchgate.net/publication/46527151_Investment_information_content_in_Bollinger_Bands (paper)
[^regime-22]: Lo, Mamaysky & Wang (2000), "Foundations of Technical Analysis," *Journal of Finance* 55(4):1705-1765. All 10 patterns significant on Nasdaq, 5 of 10 on NYSE/AMEX. https://www.cis.upenn.edu/~mkearns/teaching/cis700/lo.pdf (paper)
