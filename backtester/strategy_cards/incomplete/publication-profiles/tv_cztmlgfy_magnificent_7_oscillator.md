---

id: tv_profile_cztmlgfy

name: "Magnificent 7 Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Compare momentum in a fixed group of large technology companies with an equal-weight market benchmark. The publication combines absolute momentum, relative leadership and breadth to help assess concentration and rotation; cited academic research does not validate this particular implementation."

registry_key: null

runner: null

evaluation: null

---

# Magnificent 7 Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Compare momentum in a fixed group of large technology companies with an equal-weight market benchmark. The publication combines absolute momentum, relative leadership and breadth to help assess concentration and rotation; cited academic research does not validate this particular implementation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Raw ROC/equal-weight momentum and breadth is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Each active constituent receives equal weight; market-cap weighting is explicitly reserved for a future enhancement. Momentum is percentage price change over a lookback.
- Modes display the group composite, benchmark momentum, or their difference. Alternative RSI, stochastic, Williams %R and CCI transformations provide different oscillator views.
- Breadth counts constituents with positive momentum. Threshold and zero-line alerts summarize direction and relative leadership.
- For each active constituent ROC_i=100*(P_i[t]-P_i[t-n])/P_i[t-n],requiring nonzero lagged price. Composite=sum(ROC_i)/active_count;breadth%=100*count(ROC_i>0)/active_count. Benchmark differential=composite-benchmark_ROC. Caller defines n and complete active set;this fixed named basket does not imply historical membership reconstruction. Alternative transforms/smoothing excluded.

## Outputs and intended use

- Oscillator, component/status/breadth table and hidden component plots support analysis and downstream testing.
- The author proposes exposure timing and breadth deterioration monitoring but supplies no allocation or execution rule.
- Usable scope: Raw ROC/equal-weight momentum and breadth. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Default momentum lookback is 14; bullish/bearish thresholds default to +2%/-2%, relative thresholds +1%/-1%.
- Momentum period range 5–100, smoothing 1–50; breadth above 60% is strong and below 40% weak.

## Failure modes and caveats

- A fixed current-name basket can introduce selection bias in historical research; the prose does not define a historical membership policy.
- Alternative oscillators have incompatible natural units, making percentage threshold interpretation ambiguous.

## Missing information and implementation boundary

- Transformation scaling, smoothing method and order, missing-constituent policy and exact benchmark/security contracts are unspecified.

## Data requirements

Required inputs: aligned OHLCV for fixed named Apple Microsoft Alphabet Amazon NVIDIA Tesla Meta basket, caller-selected equal-weight S&P500 benchmark price history.

Repository input-class support: available. Ordinary historical OHLCV/price inputs for caller-selected symbols are a supported data class. Exact selected-symbol cache coverage, synchronization and adjustments remain unverified; no dynamic point-in-time universe is required by the source.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
Momentum(t) = [P(t) - P(t-n)] / P(t-n) × 100
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
(Apple, Microsoft, Alphabet, Amazon, NVIDIA, Tesla, and Meta)
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
(default: 14 periods)
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Bullish: Oscillator > Upper Threshold (default: +2.0%)
- Bearish: Oscillator < Lower Threshold (default: -2.0%)
```

### E5: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Outperformance: Relative momentum > +1.0%
- Underperformance: Relative momentum < -1.0%
```

### E6: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Momentum Period (5-100)
```

### E7: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Smoothing Period (1-50)
```

### E8: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Strong Breadth (>60%)
```

### E9: purpose, mechanism, parameters, outputs_and_use, readiness

```text
- Weak Breadth (<40%)
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
Momentum(t) = [P(t) - P(t-n)] / P(t-n) × 100
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
- Equal Weight: Each active stock receives identical weighting (1/n)
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
The indicator incorporates market breadth analysis, calculating the percentage of constituent stocks with positive momentum. This feature provides insights into:
```

### E13: mechanism, parameters, outputs_and_use, readiness

```text
Formula: Relative Performance = MAG7_Momentum - SP500EW_Momentum
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_cztmlgfy_magnificent_7_oscillator](../tv_cztmlgfy_magnificent_7_oscillator.md)
- [tv_method_risk_based_sizing](../../tv_method_risk_based_sizing.md)
- [xs_momentum](../../xs_momentum.md)

## Source

https://www.tradingview.com/script/CztMLgfY-Magnificent-7-Oscillator/

Publication ID: CztMLgfY. Source SHA-256: 64961cff16ea503cd5059602401fec9b82e99b0270f66ba434fac1acef74c0f7. Raw-description SHA-256: 5dbb56e65b6ed0ceb2ec6f86612f0fb199f0a3c123048de19038344993f998f9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
