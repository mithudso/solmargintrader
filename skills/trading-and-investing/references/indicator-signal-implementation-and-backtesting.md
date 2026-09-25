---
name: indicator-signal-implementation-and-backtesting
# provenance: built by /dr 2026-08-04 — do NOT hand-edit the frontmatter block.
# `name:` must sit immediately after the opening fence: persist-spoke.mjs anchors
# on /^---\nname:/ and reports "no YAML frontmatter found" if a comment precedes it.
hub: trading-and-investing
version: "1.3.0"
updated: "2026-08-04"
verified-as-of: "2026-08-04"
category: reference
description: >-
  SPOKE of trading-and-investing — price-derived signals as runnable
  pandas/numpy code, honestly validated. Educational ONLY, NOT financial advice;
  most edges fail after costs and data-snooping correction (2026). TRIGGER: code
  a signal (moving averages, MACD, ADX, RSI, Bollinger, ATR, OBV, VWAP,
  candlesticks, swing pivots, Fibonacci, double top, H&S); Wilder smoothing vs
  ewm(span=n); warm-up/burn-in; look-ahead/repainting bugs; TA-Lib vs pandas-ta
  mismatch; backtesting ONE signal (walk-forward, purging, embargo, break-even
  cost, Deflated Sharpe); which families fail by regime; redundancy & pairing.
  SPLIT 2026-08-04 — this file now holds §1-§4 (substrate plus the trend,
  momentum and volatility implementations); the backtest recipe (§5) and the
  regime record (§6) moved to signal-backtest-protocol-and-regime-evidence; pairing
  and redundancy (§7) plus the volume/breadth, candlestick, chart-pattern and
  price-action sets (§8-§10) moved to
  signal-pairing-volume-and-pattern-signal-sets.
  SKIP: what an indicator or pattern MEANS →
  technical-analysis (chart types, patterns, core indicators);
  volume/breadth definitions and TA meta-evidence →
  technical-analysis-breadth-frameworks-and-evidence; execution algos &
  stat arb → algorithmic-and-quant-trading; ML features →
  ai-and-ml-for-trading; sizing → trading-risk-management.
keywords:
  - indicator-signal-implementation
  - backtest
  - walk-forward
  - purged-cross-validation
  - wilder-smoothing
  - look-ahead-bias
  - break-even-cost
  - deflated-sharpe-ratio
  - data-snooping
  - signal-redundancy
  - regime-performance
  - pandas
  - technical-indicators
  - reality-check
tags:
  - trading-and-investing
  - technical-analysis
  - backtesting
  - quant
  - python
whenToUse:
  - When implementing a technical indicator in code and needing the exact equation, dependencies and a runnable pandas/numpy reference.
  - When an indicator's values disagree between your code, TA-Lib, pandas-ta or a charting platform.
  - When designing a backtest for a single signal and needing split design, a cost model, metrics and a multiple-testing correction (§5, now `references/signal-backtest-protocol-and-regime-evidence.md`).
  - When a backtest result looks too good and you need to audit it for look-ahead, warm-up or repainting bugs.
  - When deciding whether two indicators are independent confirmation or the same bet counted twice (§7, now `references/signal-pairing-volume-and-pattern-signal-sets.md`).
  - When asking under what market conditions a signal family has historically worked or failed, with citations (§6, now `references/signal-backtest-protocol-and-regime-evidence.md`).
changelog:
  - "2026-08-04 split v1.2.1->v1.3.0 — file had reached ~21.7k tokens (2.2x the ~10k reference ceiling). Split at top-level section boundaries, nothing removed or reworded: §5-§6 moved verbatim to references/signal-backtest-protocol-and-regime-evidence.md with the Concept 5 and Concept 6 footnote lists; §7-§10 moved verbatim to references/signal-pairing-volume-and-pattern-signal-sets.md with the Concept 7 list plus duplicated regime-2/6/10/11/22 definitions (cited from both halves). This file keeps §1-§4, Anti-Patterns, Troubleshooting, a pointer stub per moved section and a duplicated regime-11. Section numbering preserved across all three files so existing §N.M cross-references still resolve."
---

> **Educational information only — NOT financial, investment, or tax advice.**

## Contents

1. Signal implementation substrate (shared foundation)
2. Trend / moving-average signal set
3. Momentum-oscillator signal set
4. Volatility signal set
5. Per-signal backtest recipe
6. Regime-performance evidence
7. Pairing, independence and redundancy
8. Volume and market-breadth signal set
9. Candlestick and chart-pattern signals
10. Price-action and structure signals

**Scope.** This reference was split on 2026-08-04; §5-§10 now live in two sibling files.

| For… | Go to |
|---|---|
| §1-§4 — implementation substrate, trend/MA, momentum-oscillator and volatility signal sets | this file, below |
| §5 backtest recipe and §6 regime-performance evidence | `references/signal-backtest-protocol-and-regime-evidence.md` |
| §7 pairing/redundancy and §8-§10 volume, candlestick/chart-pattern and price-action sets | `references/signal-pairing-volume-and-pattern-signal-sets.md` |
| What an indicator or pattern *means*, rather than how to compute it | `references/technical-analysis.md` |
| Position sizing and risk limits for a signal that survives | `references/trading-risk-management.md` |

## Overview

The sibling spoke `technical-analysis` tells you what each
indicator **means**. This reference covers what happens when you try to **run**
one: the exact equation, its input dependencies, a runnable implementation, a
backtest protocol that will not lie to you, the cited empirical record of when
that signal family has worked, and whether it is independent of the signals you
already have.

Four findings shape everything here, and each was verified by execution or by
primary source rather than asserted:

1. **One bar of look-ahead is worth +3.8 Sharpe** on a series with no real
   signal (§1.3). Audit for leakage before interpreting any result.
2. **Wilder smoothing is not `ewm(span=n)`** — mean divergence 5.24 RSI points
   and 64% more trade signals (§1.1). This is the root of most library-parity
   disputes.
3. **Six "different" indicators collapsed to three effective bets**, with
   Stochastic %K and Williams %R proving numerically identical to 1.6e-14 (§7.2).
   Most confirmation is arithmetic, not evidence.
4. **The rule, not the indicator, defines the signal family.** The same RSI
   earns significantly with a centerline rule and loses significantly with a
   30/70 rule, in the same markets over the same period (§3.3, §6.3).

**The honest framing this reference takes.** Raw in-sample indicator signal is
real and often large. Three independent corrections — data-snooping, transaction
costs, and time/decay — remove most or all of it, and the strongest surviving
effects are *conditional* (trend's straddle-like payoff in large moves; reversal
in high-volatility states) with live top-journal challengers. That is stated
throughout rather than at the end, because a reference that hands you code
without it is handing you a way to lose money faster.

All code is pure pandas/numpy — no TA-Lib, no pandas-ta — so it is auditable
against the equations and runs in a bare environment (§1.6).

## 1. Signal implementation substrate (shared foundation)

Every signal in sections 2-4 depends on this layer, so it is stated once here.
Three failures in it will corrupt any indicator you compute, and all three are
demonstrated numerically below rather than asserted.

### 1.1 Wilder smoothing is not `ewm(span=n)` — and the gap is enormous

Wilder's 1978 indicators (RSI, ATR, ADX/DMI) use a recursive average with
smoothing factor **α = 1/n**. Pandas' `ewm(span=n)` uses **α = 2/(n+1)**. For
n = 14 that is 0.0714 vs 0.1333 — nearly double the responsiveness.

```
α: Wilder = 1/14 = 0.0714      ewm(span=14) = 2/15 = 0.1333
mean |difference| = 5.240 RSI points     max = 20.384
difference exceeds 2 points on 77.1% of bars
RSI-50 upcrossings: Wilder = 28   ewm(span=14) = 46
```

Those are not two calibrations of one indicator; they are two different
indicators, and the wrong one generates **64% more trades**. Correct forms:

```python
# Wilder smoothing -- use EITHER of these, they are identical
avg = series.ewm(alpha=1/n, adjust=False).mean()
avg = series.ewm(span=2*n - 1, adjust=False).mean()   # since 2/((2n-1)+1) = 1/n
```

`adjust=False` is required: `adjust=True` computes a differently-weighted
finite-sample average and will not match any reference implementation.

**This is the root of most library-parity complaints.** Before concluding that
TA-Lib, a charting platform, and your own code "disagree", check which smoothing
each applies. Verify a new implementation against a reference series and require
agreement to ~1e-8 after warm-up, not eyeball agreement on a chart.

### 1.2 Warm-up: recursive smoothers never fully forget their seed

An SMA(n) is undefined for the first n−1 bars and exact thereafter. A recursive
smoother is *never* exact — it converges. Same bar, same data, varying only how
much history was fed in:

```
history from bar   0 (400 bars): RSI[400] = 39.3190
history from bar 200 (200 bars): RSI[400] = 39.3191
history from bar 300 (100 bars): RSI[400] = 39.3328
history from bar 350 ( 50 bars): RSI[400] = 38.2263
history from bar 380 ( 20 bars): RSI[400] = 26.1026
```

With 20 bars of history the value is wrong by **13 RSI points** — enough to
invert an overbought/oversold decision. Convergence to 4 decimal places needs
roughly **200 bars for a 14-period Wilder average**.

**Rule: feed at least 10-15× the indicator period as burn-in, then discard that
burn-in region from the backtest.** Keeping it means your earliest signals are
seed artifacts, and because early bars are often the most profitable-looking part
of a long backtest, this biases results upward.

### 1.3 Look-ahead: one bar of leakage is worth +3.8 Sharpe

A signal computed from bar *t*'s close cannot be traded at bar *t*'s close. The
correct convention is to shift the position vector forward one bar.

```
same-bar (look-ahead) Sharpe : +4.676
next-bar (correct)    Sharpe : +0.870
inflation from one bar of leakage: +3.805 Sharpe
```

```python
ret    = close.pct_change()
signal = np.sign(rsi_wilder(close) - 50)
pnl    = signal.shift(1) * ret        # correct
# pnl  = signal * ret                 # WRONG: trades on information not yet available
```

**Read that result precisely.** The demonstration uses a synthetic
random walk, so the "correct" +0.87 is itself sampling noise over 600 bars — it
is *not* evidence that RSI has an edge. The finding is the **difference**: a
single bar of leakage manufactured 3.8 Sharpe out of a series with no real
signal. Any backtest reporting an implausible Sharpe should be audited for this
before anything else.

Related traps in the same family:

- **Repainting.** Any indicator using future bars (centered moving averages,
  ZigZag, some pivot implementations) looks superb in backtest and cannot be
  traded. If an indicator's historical values change as new bars arrive, it
  repaints.
- **Intrabar assumptions.** A stop and a target both touched within one bar is
  ambiguous at bar resolution; assuming the favourable fill is a silent
  look-ahead. Resolve with finer data or assume the adverse fill.
- **Signal on close, fill on close.** Even `shift(1)` overstates reality if you
  assume the next bar's *open* is the next bar's *close*. Fill at the open you
  can actually reach.

### 1.4 Input data requirements

- **Adjusted vs raw prices.** Splits and dividends change every moving average,
  every band, and therefore every crossing. Use a consistently adjusted series;
  mixing adjusted history with unadjusted recent bars creates artificial gaps
  that indicators read as real moves.
- **Survivorship.** A universe of instruments that exist *today* excludes the
  delisted and bankrupt. Any cross-sectional signal tested on it is measuring
  survivors.
- **Bar alignment and sessions.** Timezone drift, differing session boundaries,
  and holiday handling shift what "the 20-day average" means. Pin the session
  definition explicitly.
- **Gaps, halts and missing bars.** Forward-filling a halted instrument
  fabricates zero-return bars that suppress volatility estimates (ATR, Bollinger
  width). Prefer dropping to fabricating, and never interpolate prices.
- **Volume is a separate hazard.** Volume series are revised, and consolidated
  vs single-venue volume differ substantially — a live concern for any
  volume-based signal.

### 1.5 Vectorized vs streaming, and why live diverges from backtest

Vectorized pandas computation over a full history and incremental per-bar
computation in production are algebraically identical **only** if the recursion is
seeded identically and no lookback is truncated. Divergences almost always trace
to: a rolling window silently shortened at the series start; the live process
restarting with less warm-up than the backtest had (§1.2); or `adjust=True`
versus `adjust=False`. Reconcile by replaying live bars through the vectorized
path and requiring exact agreement.

### 1.6 Dependency footprint

Everything in this reference runs on **pandas and numpy only** — no TA-Lib, no
pandas-ta, no vectorbt. That is deliberate:

- the equations are the specification, so a self-contained implementation is
  auditable, whereas a library call hides which smoothing convention applies
  (§1.1);
- it avoids TA-Lib's C build dependency, the single most common installation
  blocker;
- it makes every code block in this document runnable in a bare environment.

Use a library in production if you prefer, but verify it against these
implementations first — and expect to discover a smoothing mismatch.

## 2. Trend / moving-average signal set

### 2.1 The reference module

Every implementation below is pure pandas/numpy (§1.6) and was executed as a
smoke test while writing this reference: **27 indicator outputs, 0 failures**,
each checked for finiteness and for staying inside its theoretical bounds
(RSI/Stochastic/MFI/Ultimate in [0,100], Williams %R in [−100,0], ATR ≥ 0,
Supertrend direction in {−1,+1}).

```python
import numpy as np, pandas as pd

def wilder(s, n): return s.ewm(alpha=1/n, adjust=False).mean()   # RSI/ATR/ADX -- see 1.1
def ema(s, n):    return s.ewm(span=n, adjust=False).mean()
def sma(s, n):    return s.rolling(n).mean()

def wma(s, n):
    w = np.arange(1, n+1)
    return s.rolling(n).apply(lambda x: np.dot(x, w)/w.sum(), raw=True)

def dema(s, n):
    e = ema(s, n); return 2*e - ema(e, n)

def tema(s, n):
    e1 = ema(s, n); e2 = ema(e1, n); e3 = ema(e2, n)
    return 3*e1 - 3*e2 + e3

def macd(c, f=12, sl=26, sig=9):
    line = ema(c, f) - ema(c, sl); s = ema(line, sig)
    return pd.DataFrame({"macd": line, "signal": s, "hist": line - s})

def true_range(h, l, c):
    pc = c.shift(1)
    return pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)

def atr(h, l, c, n=14): return wilder(true_range(h, l, c), n)

def adx(h, l, c, n=14):
    up, dn = h.diff(), -l.diff()
    plus  = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr_n = wilder(true_range(h, l, c), n)
    pdi = 100 * wilder(pd.Series(plus,  index=h.index), n) / tr_n
    mdi = 100 * wilder(pd.Series(minus, index=h.index), n) / tr_n
    dx  = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return pd.DataFrame({"plus_di": pdi, "minus_di": mdi, "adx": wilder(dx, n)})

def ichimoku(h, l, c, t=9, k=26, b=52):
    mid = lambda n: (h.rolling(n).max() + l.rolling(n).min()) / 2
    tenkan, kijun = mid(t), mid(k)
    return pd.DataFrame({"tenkan": tenkan, "kijun": kijun,
                         "senkou_a": ((tenkan + kijun)/2).shift(k),
                         "senkou_b": mid(b).shift(k),
                         "chikou": c.shift(-k)})   # NEGATIVE shift = future data, see below

def psar(h, l, af0=0.02, step=0.02, af_max=0.20):
    n = len(h); out = np.full(n, np.nan)
    bull = True; af = af0; ep = h.iloc[0]; sar = l.iloc[0]
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if bull:
            if l.iloc[i] < sar:  bull, sar, ep, af = False, ep, l.iloc[i], af0
            elif h.iloc[i] > ep: ep, af = h.iloc[i], min(af + step, af_max)
        else:
            if h.iloc[i] > sar:  bull, sar, ep, af = True, ep, h.iloc[i], af0
            elif l.iloc[i] < ep: ep, af = l.iloc[i], min(af + step, af_max)
        out[i] = sar
    return pd.Series(out, index=h.index)

def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n); hl2 = (h + l)/2
    ub, lb = hl2 + mult*a, hl2 - mult*a
    fu, fl = ub.copy(), lb.copy()
    for i in range(1, len(c)):
        fu.iloc[i] = ub.iloc[i] if (ub.iloc[i] < fu.iloc[i-1] or c.iloc[i-1] > fu.iloc[i-1]) else fu.iloc[i-1]
        fl.iloc[i] = lb.iloc[i] if (lb.iloc[i] > fl.iloc[i-1] or c.iloc[i-1] < fl.iloc[i-1]) else fl.iloc[i-1]
    dirn = pd.Series(1, index=c.index)
    for i in range(1, len(c)):
        dirn.iloc[i] = -1 if c.iloc[i] < fl.iloc[i] else (1 if c.iloc[i] > fu.iloc[i] else dirn.iloc[i-1])
    return pd.DataFrame({"upper": fu, "lower": fl, "dir": dirn})
```

### 2.2 Equations, dependencies and signal rules

`C`=close, `H`/`L`=high/low, `n`=period. **Dep** = what the indicator needs
beyond close.

| Signal | Equation | Dep | Signal rule | Warm-up |
|---|---|---|---|---|
| **SMA(n)** | `(1/n)·Σ C[t-i]`, i=0..n−1 | — | `sign(C − SMA)`; or fast/slow crossover | n |
| **EMA(n)** | `EMA_t = α·C_t + (1−α)·EMA_{t−1}`, `α = 2/(n+1)` | — | as SMA | ~3n |
| **WMA(n)** | `Σ(w_i·C_i)/Σw_i`, `w_i = i` (i=1..n, newest heaviest) | — | as SMA | n |
| **DEMA(n)** | `2·EMA(C,n) − EMA(EMA(C,n),n)` | — | as EMA, less lag | ~6n |
| **TEMA(n)** | `3·E1 − 3·E2 + E3` where `E1=EMA(C)`, `E2=EMA(E1)`, `E3=EMA(E2)` | — | as EMA, least lag, most whipsaw | ~9n |
| **MACD(12,26,9)** | `line = EMA₁₂ − EMA₂₆`; `signal = EMA₉(line)`; `hist = line − signal` | — | `sign(hist)`, or line crossing zero | ~80 |
| **ATR(n)** | `TR = max(H−L, \|H−C₋₁\|, \|L−C₋₁\|)`; `ATR = Wilder(TR,n)` | H,L | not directional — a volatility scale | 10-15n |
| **ADX/DMI(14)** | `+DM = H−H₋₁ if > L₋₁−L and >0 else 0`; `−DM` symmetric; `±DI = 100·Wilder(±DM)/Wilder(TR)`; `DX = 100·\|+DI−−DI\|/(+DI+−DI)`; `ADX = Wilder(DX)` | H,L | ADX is **strength, not direction**: gate with `ADX > 20-25`, take direction from `+DI vs −DI` | ~30n |
| **Ichimoku(9,26,52)** | `Tenkan = (H₉max+L₉min)/2`; `Kijun = (H₂₆+L₂₆)/2`; `SenkouA = (Tenkan+Kijun)/2` shifted **+26**; `SenkouB = (H₅₂+L₅₂)/2` shifted **+26**; `Chikou = C` shifted **−26** | H,L | TK cross; price vs cloud | 52+26 |
| **PSAR(0.02,0.2)** | `SAR_{t+1} = SAR_t + AF·(EP − SAR_t)`; on flip reset `AF=0.02`, `EP` = extreme of new side; `AF += 0.02` per new extreme, cap 0.20 | H,L | always-in: `sign` of side | ~50 |
| **Supertrend(10,3)** | `bands = (H+L)/2 ± mult·ATR(n)`, then ratchet each band monotonically until price closes through it | H,L | `dir` flips on close beyond the opposing final band | 10-15n |

### 2.3 Traps specific to this family

- **`Chikou` uses `shift(-26)` — a negative shift is future data.** It is
  legitimate for visual analysis of the past but **must never enter a signal**.
  Any rule referencing `chikou` at bar *t* is look-ahead (§1.3). This is the one
  genuinely dangerous line in the module.
- **Ichimoku's cloud is shifted forward by design.** `SenkouA/B` at bar *t*
  were computed 26 bars ago, so plotting them ahead is correct and not leakage —
  the opposite direction from `chikou`.
- **PSAR and Supertrend are path-dependent loops.** They cannot be vectorised
  without changing results, and they are the most warm-up-sensitive signals here
  because a single early flip propagates forever (§1.2). Seed them identically in
  backtest and live or the two will diverge permanently.
- **DEMA/TEMA reduce lag by extrapolating**, which amplifies noise. Whipsaw rises
  monotonically from SMA → EMA → DEMA → TEMA. That is a variance/bias trade, not
  a free improvement.
- **ADX is not a direction.** Using ADX as a long/short signal is a category
  error; it is the regime gate of §7.3.
- **Every signal in this table is a moving-average transform**, so they are
  mutually redundant by construction — MACD histogram and a price-vs-SMA rule
  agreed 81% of the time in the §7.2 worked output. Do not treat two of them as
  confirmation.

### 2.4 Backtest, regime and pairing

Use §5's protocol as-is. Regime expectation for the whole family: **needs
prolonged directional moves; structurally loses in range-bound markets**
(§6.2) — AQR's fitted model carries a negative intercept for exactly this
reason. For pairing, treat the entire family as **one** signal dimension and
combine it with volume or a volatility gate rather than with another
moving-average variant (§7.3).

## 3. Momentum-oscillator signal set

### 3.1 Implementations

```python
def rsi(c, n=14):
    d = c.diff(); g = d.clip(lower=0); ls = -d.clip(upper=0)
    return 100 - 100/(1 + wilder(g, n)/wilder(ls, n))      # Wilder, NOT ewm(span=n)

def stoch(h, l, c, n=14, d=3):
    hh, ll = h.rolling(n).max(), l.rolling(n).min()
    k = 100*(c - ll)/(hh - ll)
    return pd.DataFrame({"k": k, "d": sma(k, d)})

def cci(h, l, c, n=20):
    tp = (h + l + c)/3
    md = tp.rolling(n).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)  # MEAN abs dev
    return (tp - sma(tp, n)) / (0.015 * md)

def williams_r(h, l, c, n=14):
    hh, ll = h.rolling(n).max(), l.rolling(n).min()
    return -100*(hh - c)/(hh - ll)

def roc(c, n=12): return 100*(c/c.shift(n) - 1)

def mfi(h, l, c, v, n=14):
    tp = (h + l + c)/3; mf = tp*v; up = tp.diff() > 0
    pos = mf.where(up,  0.0).rolling(n).sum()
    neg = mf.where(~up, 0.0).rolling(n).sum()
    return 100 - 100/(1 + pos/neg)

def tsi(c, long=25, short=13):
    m = c.diff()
    return 100 * ema(ema(m, long), short) / ema(ema(m.abs(), long), short)

def awesome(h, l, f=5, s=34):
    mp = (h + l)/2; return sma(mp, f) - sma(mp, s)

def ultimate(h, l, c, s=7, m=14, L=28):
    pc = c.shift(1)
    bp = c - pd.concat([l, pc], axis=1).min(axis=1)                      # buying pressure
    tr = pd.concat([h, pc], axis=1).max(axis=1) - pd.concat([l, pc], axis=1).min(axis=1)
    a = lambda n: bp.rolling(n).sum()/tr.rolling(n).sum()
    return 100*(4*a(s) + 2*a(m) + a(L))/7                                # weights 4:2:1
```

### 3.2 Equations, dependencies and signal rules

| Signal | Equation | Dep | Range | Signal rule |
|---|---|---|---|---|
| **RSI(14)** | `RS = Wilder(gain,n)/Wilder(loss,n)`; `RSI = 100 − 100/(1+RS)` | — | 0-100 | **Two distinct rules, opposite families** — see §3.3 |
| **Stochastic(14,3)** | `%K = 100·(C − L₁₄min)/(H₁₄max − L₁₄min)`; `%D = SMA₃(%K)` | H,L | 0-100 | %K/%D cross; or %K vs 50 |
| **CCI(20)** | `(TP − SMA(TP,n)) / (0.015 · MAD(TP,n))`, `TP=(H+L+C)/3` | H,L | unbounded | ±100 crossings |
| **Williams %R(14)** | `−100·(H₁₄max − C)/(H₁₄max − L₁₄min)` | H,L | −100-0 | −20/−80 thresholds |
| **ROC(12)** | `100·(C/C₋ₙ − 1)` | — | unbounded | zero-line cross |
| **MFI(14)** | volume-weighted RSI on typical price: `100 − 100/(1 + Σpos MF/Σneg MF)` | H,L,**V** | 0-100 | 20/80 thresholds |
| **TSI(25,13)** | `100 · EMA₁₃(EMA₂₅(ΔC)) / EMA₁₃(EMA₂₅(\|ΔC\|))` | — | ±100 | zero-line + signal cross |
| **Awesome Osc** | `SMA₅((H+L)/2) − SMA₃₄((H+L)/2)` | H,L | unbounded | zero cross, saucer |
| **Ultimate Osc** | `100·(4·avg₇ + 2·avg₁₄ + avg₂₈)/7`, `avg_n = ΣBP/ΣTR` | H,L | 0-100 | divergence-based |

**`0.015` in CCI** is Lambert's scaling constant, chosen so roughly 70-80% of
values fall within ±100. Note CCI uses **mean absolute deviation**, not standard
deviation — a frequent implementation error that changes the scale.

### 3.3 The single most important distinction in this section

**RSI is not a mean-reversion indicator. RSI-with-30/70-thresholds is.** The same
series supports two rules with empirically **opposite** signs (§6.3):

| Rule | Family | Measured result |
|---|---|---|
| `sign(RSI − 50)` centerline | **trend-continuation** | Milan **+2.268%/10d, t = 3.394**; +5.069% annual net of 1% cost |
| `RSI < 30` buy / `> 70` sell | **mean-reversion** | Milan RSI(7) **−1.163%, t = −2.371**; DAX RSI(14) **−0.914%** |

Classify by **rule**, never by indicator name (§7.1). This applies identically to
Stochastic, Williams %R and CCI: each has a centerline (trend) reading and a
threshold (reversion) reading.

### 3.4 Traps specific to this family

- **Wilder vs `ewm(span=n)` in RSI** — 5.24 RSI points mean error, 64% more
  crossings (§1.1). The single most common bug in this family.
- **Williams %R is Stochastic %K minus 100.** Verified numerically in this run to
  **1.6e-14** over the same lookback. Running both is running one signal twice.
- **Division by zero** when `H₁₄max == L₁₄min` (a fully flat window, common on
  illiquid instruments or halted sessions) — Stochastic and %R return inf/NaN.
  Guard explicitly rather than letting NaN propagate into positions.
- **MFI needs volume** and inherits every volume-quality problem in §1.4;
  consolidated vs single-venue volume will change the values.
- **Thresholds are not universal constants.** A Brent study found RSI **75**
  outperformed 70 (22.84% vs 12.91%), consistent with trends overrunning
  textbook levels (§6.3). Treat 30/70 as one candidate parameterisation, and
  count every variant you test against your multiple-testing N (§5.6).

### 3.5 Backtest, regime and pairing

Regime expectation: the **threshold/reversion** reading is documented to pay in
**high-volatility, liquidity-stressed states** (reversal Sharpe rises with VIX),
**not** in quiet ranges — the common claim to the contrary is lore with no
peer-reviewed support located (§6.3). The **centerline** reading behaves like the
§2 trend family and should be paired accordingly. All five bounded oscillators
here are normalized-momentum transforms and mutually redundant (§7.1): in §7.2's
run, RSI-vs-50 and price-vs-SMA20 agreed **91%** of the time.

## 4. Volatility signal set

### 4.1 Implementations

```python
def bollinger(c, n=20, k=2.0):
    mid = sma(c, n); sd = c.rolling(n).std(ddof=0)      # POPULATION sd -- see 4.3
    up, lo = mid + k*sd, mid - k*sd
    return pd.DataFrame({"mid": mid, "upper": up, "lower": lo,
                         "bandwidth": (up - lo)/mid,
                         "pct_b": (c - lo)/(up - lo)})

def keltner(h, l, c, n=20, natr=10, mult=2.0):
    mid = ema(c, n); a = atr(h, l, c, natr)
    return pd.DataFrame({"mid": mid, "upper": mid + mult*a, "lower": mid - mult*a})

def donchian(h, l, n=20):
    up, lo = h.rolling(n).max(), l.rolling(n).min()
    return pd.DataFrame({"upper": up, "lower": lo, "mid": (up + lo)/2})

def chaikin_volatility(h, l, n=10):
    e = ema(h - l, n); return 100*(e/e.shift(n) - 1)

def squeeze(h, l, c, n=20):
    bb, kc = bollinger(c, n), keltner(h, l, c, n)
    return (bb["upper"] < kc["upper"]) & (bb["lower"] > kc["lower"])
```

### 4.2 Equations, dependencies and signal rules

| Signal | Equation | Dep | Signal rule |
|---|---|---|---|
| **Bollinger(20,2)** | `mid = SMA₂₀`; `upper/lower = mid ± k·σ₂₀`; `%B = (C−lower)/(upper−lower)`; `bandwidth = (upper−lower)/mid` | — | **Two opposite rules**: band-touch reversion, or squeeze→breakout |
| **Keltner(20,10,2)** | `mid = EMA₂₀`; `± mult·ATR₁₀` | H,L | breakout beyond band |
| **Donchian(20)** | `upper = H₂₀max`, `lower = L₂₀min` | H,L | close beyond channel = breakout (the Turtle rule) |
| **Chaikin Volatility(10)** | `100·(EMA₁₀(H−L) / EMA₁₀(H−L)₋₁₀ − 1)` | H,L | expansion/contraction of range |
| **Squeeze** | Bollinger bands **inside** Keltner bands | H,L | compression → expect expansion |
| **ATR(n)** | see §2.2 | H,L | not a signal: a **sizing and stop scale** |

### 4.3 Traps specific to this family

- **`ddof` in the Bollinger standard deviation.** Bollinger's definition uses the
  **population** standard deviation (`ddof=0`). Pandas defaults to `ddof=1`
  (sample), which widens bands and changes every touch. This is the Bollinger
  analogue of the Wilder/EMA error in §1.1 — small in appearance, structural in
  effect.
- **Bollinger's normality assumption.** `±2σ` implies ~95% containment only for
  normally distributed returns. Financial returns are fat-tailed, so band
  excursions are more frequent than the nominal 5% — the statistical basis of
  "walking the band."
- **Two contradictory rules share one indicator.** Band-touch reversion and
  squeeze-breakout point opposite ways from the same bands. As with RSI (§3.3),
  the rule defines the family, and running both on one instrument is not
  confirmation, it is hedging yourself to zero minus costs.
- **ATR is not directional.** Its correct uses are position sizing, stop
  distance, and the volatility gate of §7.3.
- **Keltner has two incompatible historical definitions** — Keltner's original
  used a price range around a typical-price SMA; the modern form (implemented
  here) uses EMA ± ATR. Charting platforms differ on which they ship, so state
  which you mean.

### 4.4 Backtest, regime and pairing

**Read §6.4 before trusting any band signal.** Band indicators as standalone
signals have a negative evidence record: Bollinger profitable in only **2 of 12**
tests after costs, underperforming buy-and-hold by **5.8-18.8%**, with **none of
48** signals informative at the 5% level — and the **inverted** rule beat the
standard one in **8 of 12** tests.[^regime-11]

Volatility as a **state variable** is a different and far better-supported story
(Moreira & Muir: **4.9%** market alpha, a **25%** Sharpe improvement) — but only
when volatility genuinely varies, and its real-time implementability is contested
by Cederburg et al. (§6.4). That is the defensible use of this family: **gate and
size other signals with it** rather than trading its bands directly (§7.3).

## 5. Per-signal backtest recipe — see the backtest-protocol reference

**Moved to `references/signal-backtest-protocol-and-regime-evidence.md` §5**, verbatim
and still numbered §5. What is there, and which claim in this file it supports:

| In §5 | Supports |
|---|---|
| Anchored vs rolling walk-forward, purging, embargo, overlapping labels (§5.1-§5.3) | The Anti-Pattern "reporting the best of many variants" and every §2-§4 signal's validation |
| Explicit cost model and **break-even cost in bps** (§5.4) | The Anti-Pattern "reporting only net return at one cost assumption" |
| Metric set — Sharpe, Sortino, Calmar, PSR, MinTRL (§5.5) | How to report a §2-§4 signal's result honestly |
| Mandatory multiple-testing correction — Reality Check, SPA, FDR, PBO, Deflated Sharpe (§5.6) | The STW p=0.042 → 0.908 figure quoted in Anti-Patterns and in §1's framing |

## 6. Regime-performance evidence — see the backtest-protocol reference

**Moved to `references/signal-backtest-protocol-and-regime-evidence.md` §6**, verbatim
and still numbered §6, together with its Concept 6 footnote
list (regime-1 to regime-22). What is there, and which claim in this file it
supports:

| In §6 | Supports |
|---|---|
| BLL 1992 vs Sullivan-Timmermann-White 1999 vs Bajgrowicz-Scaillet 2012 (§6.1) | The Overview's "three independent corrections remove most or all of it"; the Troubleshooting row on decay |
| Trend/MA record, TSMOM smile and its challenger (§6.2) | The §2 trend/moving-average set's realistic expectation |
| Oscillator record — the same RSI wins on a centerline rule and loses on 30/70 (§6.3) | The Overview's fourth finding and the §3.3 rule-defines-the-family point |
| Volatility-state conditioning: reversal in high-vol states, vol-managed portfolios (§6.4) | The §4 volatility set and the §7.3 regime gate |

## 7. Pairing, independence and redundancy — see the pairing reference

**Moved to `references/signal-pairing-volume-and-pattern-signal-sets.md` §7**, verbatim and
still numbered §7, together with its Concept 7 footnote
list (pair-1 to pair-5). What is there, and which claim in this file it supports:

| In §7 | Supports |
|---|---|
| Correlation, agreement rate and PCA effective dimensionality, with runnable code (§7.1-§7.2) | The Overview's third finding — six "different" indicators collapsed to three bets; Williams %R ≡ Stochastic %K−100 to 1.6e-14 |
| Which pairings are genuinely orthogonal, and the volatility regime gate (§7.3) | Why §2-§4 signals are not independent of each other |
| Degrees-of-freedom budget, ~3-4 parameters (§7.4) | The Anti-Pattern "optimizing 6+ parameters on one instrument" and the Troubleshooting row "adding indicators improved the backtest" |

## 8. Volume and market-breadth signal set — see the pairing reference

**Moved to `references/signal-pairing-volume-and-pattern-signal-sets.md` §8**, verbatim and
still numbered §8. It holds OBV, CLV, the A/D line, CMF, the Chaikin Oscillator,
anchored VWAP, Force Index, Ease of Movement, and the breadth indicators that
need market-wide advance/decline counts rather than one OHLCV frame (McClellan
Oscillator and Summation, Zweig Breadth Thrust). **Supports** this file's
recurring claim that volume is the one family that is *not* price-derived, and so
the main candidate for genuine independence from §2-§4.

## 9. Candlestick and chart-pattern signals — see the pairing reference

**Moved to `references/signal-pairing-volume-and-pattern-signal-sets.md` §9**, verbatim and
still numbered §9, with the regime-22 definition (Lo, Mamaysky & Wang 2000) it
shares with §6. It holds the detection rules and code for doji, marubozu, hammer,
shooting star, engulfing, harami and morning/evening star. **Supports** the
tolerance-parameter problem that makes pattern families the most exposed to the
multiple testing described in §5.6.

## 10. Price-action and structure signals — see the pairing reference

**Moved to `references/signal-pairing-volume-and-pattern-signal-sets.md` §10**, verbatim
and still numbered §10. It holds swing-pivot detection, market structure
(BOS/ChoCH), S/R zones, Fibonacci levels, floor-trader, Camarilla and CPR pivots,
trendline fits, double top/bottom, head and shoulders and round-number levels.
**Supports** the §10.4 conclusion that these are price-derived and therefore *not*
independent confirmation of §2-§4 — the same argument the Anti-Patterns table
below makes about stacked oscillators.

## Anti-Patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Trading the signal on the bar that produced it | Manufactured **+3.8 Sharpe** from a random walk (§1.3) | `positions.shift(1)` and fill at a price you could reach |
| `ewm(span=n)` for RSI/ATR/ADX | 5.24 RSI points of error, 64% more trades (§1.1) | `ewm(alpha=1/n, adjust=False)` or `span=2n−1` |
| Starting the backtest at bar 0 | Early values are seed artifacts, biasing the most-compounded region upward (§1.2) | Discard 10-15× the period as burn-in |
| Stacking RSI + Stochastic + Williams %R as "confirmation" | %R ≡ %K−100 (verified to 1.6e-14); all are normalized momentum (§7.1-7.2) | Run §7.2's redundancy check; count effective dimensions |
| Reporting only net return at one cost assumption | Hides the assumption that decides the result | Report **break-even cost** in bps (§5.4) |
| Reporting the best of many variants with a nominal p-value | STW: p=0.042 → **0.908** after correcting for the search (§5.6) | Count every variant tried; apply Reality Check / SPA / FDR / DSR |
| Using ADX as a long/short signal | ADX measures strength, not direction (§2.3) | Gate with ADX; take direction from ±DI |
| Any rule referencing Ichimoku `chikou` | `shift(-26)` is future data (§2.3) | Restrict `chikou` to visual/retrospective use |
| Optimizing 6+ parameters on one instrument | Each parameter is another degree of freedom to fit noise (§7.4) | Keep to ~3-4; validate walk-forward |
| Treating 30/70 or ±2σ as universal constants | RSI 75 beat 70 on Brent; fat tails break the 95% band claim (§3.4, §4.3) | Treat as one candidate parameterisation, counted in your N |
| Concluding "it works" after a clean backtest | Costs, snooping and decay each remove most of the edge (§6.1) | Conclude "not disproven, on this sample, at this cost" |

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| My RSI/ATR/ADX differs from TradingView or TA-Lib | Wilder vs `ewm(span=n)`, or `adjust=True` | §1.1 — use `alpha=1/n, adjust=False`; require agreement to ~1e-8 after warm-up |
| Live values differ from backtest values on the same bar | Restarted with less warm-up than the backtest had, or a truncated rolling window | §1.2, §1.5 — replay live bars through the vectorized path and require exact agreement |
| Sharpe above ~3 on a simple indicator rule | Look-ahead; the leakage test in §1.3 reproduces exactly this | Shift positions; re-run |
| Stochastic or Williams %R returns `inf`/`NaN` | `H_max == L_min` — a flat window (illiquid or halted) | §3.4 — guard the zero denominator explicitly |
| Backtest strong early, weak later | Burn-in artifacts in the early region, or genuine decay | Discard burn-in (§1.2); then test sub-periods (§6.1 — decay is the most consistent finding in the literature) |
| Adding indicators improved the backtest | In-sample fit rising while out-of-sample falls | §7.4 — check effective dimensionality (§7.2) and correct for the combination search |
| Bollinger bands wider than the charting platform's | Pandas `std()` defaults to `ddof=1`; Bollinger uses population sd | §4.3 — pass `ddof=0` |
| Break-even cost computes as 0 bps | Gross mean return is already negative — the signal has no edge before costs | Expected on noise; confirm on real data before drawing conclusions |
| PSAR/Supertrend diverge between two runs | Path-dependent loops seeded differently | §2.3 — seed identically; they cannot be vectorized |
| Signal trades far more or less than expected | Wrong smoothing (§1.1) or unguarded NaN propagating into positions | Compare crossing counts against a reference implementation |

## References

Footnote ids are scoped per concept (`[^<slug>-n]`) so adding a concept never
renumbers an earlier one.

The full footnote lists moved with the sections that cite them: **Concept 5
(backtest recipe, bt-1 to bt-6) and Concept 6 (regime evidence, regime-1 to
regime-22)** are in `references/signal-backtest-protocol-and-regime-evidence.md`; **Concept 7 (pairing, pair-1 to
pair-5)** is in `references/signal-pairing-volume-and-pattern-signal-sets.md`.
The one entry cited by a section that stayed here is duplicated below.

### Concept 6 — regime-performance evidence (entry cited from §4.3; the full Concept 6 list lives in `references/signal-backtest-protocol-and-regime-evidence.md`)

[^regime-11]: Lento, Gradojevic & Wright (2007), "Investment information content in Bollinger Bands?" *Applied Financial Economics Letters* 3:263-267. https://www.researchgate.net/publication/46527151_Investment_information_content_in_Bollinger_Bands (paper)
