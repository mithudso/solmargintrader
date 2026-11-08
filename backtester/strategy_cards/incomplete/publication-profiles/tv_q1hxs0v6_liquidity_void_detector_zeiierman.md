---

id: tv_profile_q1hxs0v6

name: "Liquidity Void Detector (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Liquidity Void Detector emphasizes unusually large recent returns when volume is weak relative to its own baseline. It explicitly offers a practical OHLCV proxy, not measured order-book emptiness. The narrative associates upward low-volume moves with potential downside refill and downward moves with upside refill, but its settings section reverses those buy/sell labels, so consumers must preserve that contradiction rather than wire labels into orders."

registry_key: null

runner: null

evaluation: null

---

# Liquidity Void Detector (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Liquidity Void Detector emphasizes unusually large recent returns when volume is weak relative to its own baseline. It explicitly offers a practical OHLCV proxy, not measured order-book emptiness. The narrative associates upward low-volume moves with potential downside refill and downward moves with upside refill, but its settings section reverses those buy/sell labels, so consumers must preserve that contradiction rather than wire labels into orders.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Parameterized numerical void oscillator is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Compute log volume relative to its SMA and Z-score that shock; compute and Z-score one-bar log return.
- Multiply return Z-score by full weight in low-volume conditions or by a configurable fade otherwise.
- volTrend=SMA(volume,L);vs=log(volume)-log(volTrend) for positive inputs;vsZ=ZScore(vs,vzLen);lowVS=(vsZ<=vzThr). r1=log(close/close[1]);retZ=ZScore(r1,rLen);osc=retZ*(1 if lowVS else fadeNoLow). ZScore=(x-mean)/std under caller convention with nonzero std;fadeNoLow in[0,1]. Contradictory side labels and signal decisions remain excluded.

## Outputs and intended use

- Inspect signed low-participation displacement alongside price zones and other tools; do not assume voids necessarily fill.
- Usable scope: Parameterized numerical void oscillator. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Low-volume threshold examples are -0.5 to -1.0. Fade ranges 0–1, with zero ignoring non-low-volume bars and one ignoring the volume condition. Lengths/oscillator thresholds are configurable without defaults.

## Failure modes and caveats

- Analytical: weak reported volume is not actual depth, standardized returns can be unstable and the narrative/settings side labels contradict.

## Missing information and implementation boundary

- Exact zScore convention, zero-variance/invalid-volume behavior, default lookbacks and unambiguous trigger-label mapping are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
Typical: −0.5 to −1.0.
```

### E2: parameters, readiness

```text
Fade When Volume Not Low (0–1)
```

### E3: mechanism, readiness

```text
osc    = retZ * weight
```

### E4: risks, readiness

```text
Upper Threshold (Osc ≥)[/b] — Trigger for Sell-Side Imbalance (void below).
```

### E5: risks, readiness

```text
Positive readings ⇒[/b] strong up-move on low volume → potential Buy-Side Imbalance
```

### E6: mechanism, parameters, outputs_and_use, readiness

```text
volTrend = ta.sma(volume, L)
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
vs       = (volume > 0 and volTrend > 0) ? math.log(volume) - math.log(volTrend) : na
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
vsZ      = zScore(vs, vzLen)  // z-scored volume shock
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
lowVS    = (vsZ <= vzThr)     // low-volume condition
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
r1   = math.log(close / close[1])
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
retZ = zScore(r1, rLen)  // z-scored prior return
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
weight = lowVS ? 1.0 : fadeNoLow
```

### E13: mechanism, parameters, outputs_and_use, readiness

```text
osc    = retZ * weight[/pine]
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fair_value_gap](../../../strategy_research/tv_method_fair_value_gap.md)
- [tv_q1hxs0v6_liquidity_void_detector_zeiierman](../tv_q1hxs0v6_liquidity_void_detector_zeiierman.md)

## Source

https://www.tradingview.com/script/q1hXS0v6-Liquidity-Void-Detector-Zeiierman/

Publication ID: q1hXS0v6. Source SHA-256: a2dd2be11379148db33c64a0e06f54465f30b1682fdd1d6e994cbce65ee78e7f. Raw-description SHA-256: 72e53876489a4884481047c58577798b05d11220ff38eeaf23de4b700e222df4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
