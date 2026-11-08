---

id: tv_profile_qaaxkw1p

name: "AI Predictive Flow (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Estimate forward movement by matching multibar price-feature patterns with historical analogues. A smoothed nearest-neighbor output becomes an oscillator and projected-price regime, offering model-based directional context rather than a validated prediction guarantee."

registry_key: null

runner: null

evaluation: null

---

# AI Predictive Flow (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate forward movement by matching multibar price-feature patterns with historical analogues. A smoothed nearest-neighbor output becomes an oscillator and projected-price regime, offering model-based directional context rather than a validated prediction guarantee.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Definition of tot/base, storage/alignment of Y outcomes, forecast maturity and initialization are omitted.

- Definition of tot/base, storage/alignment of Y outcomes, forecast maturity and initialization are omitted.

## How it works

- Features comprise log one-bar return, lookback momentum, centered RSI and normalized fast/slow EMA spread. Separate matrices store sequences, and equal feature-weight squared differences across the pattern are summed before taking a square root.
- The nearest distances select outcome labels. Each outcome weight is one minus its distance divided by the selected distance sum, with a special single-neighbor/zero-distance branch. The shown function sums weighted labels without normalizing total weight.
- Prediction passes through EMA stages and a signal EMA. Projected price is base times exp(prediction); ATR-offset projected references set a state when their rolling extrema are reached, with the bearish assignment last if both tests fire.

## Outputs and intended use

- Oscillator zero side, signal crossovers, histogram and background regime provide directional alignment context.
- The author favors aligned oscillator/regime signals; no allocation, costs or empirical forecasting performance is supplied.

## Parameters and stated settings

- Pattern length, memory, neighbor count, prediction and signal smoothing; feature lengths, forecast horizon, oscillator/regime lengths and ATR band multiplier appear as code variables without concrete defaults.

## Failure modes and caveats

- Unnormalized neighbor weights change prediction magnitude with neighbor count. Differently scaled features can dominate despite equal nominal weights.
- Historical labels must mature before entering memory; leakage cannot be ruled out without the missing alignment logic.

## Missing information and implementation boundary

- Definition of tot/base, storage/alignment of Y outcomes, forecast maturity and initialization are omitted.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV supplies the raw feature inputs, without establishing label timing or code parity.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, readiness

```text
s += math.pow(d1.get(j), 2) * 0.25 +
```

### E2: purpose, mechanism, parameters, outputs_and_use, readiness

```text
w = useN > 1 ? (sumD != 0 ? (1 - d / sumD) : 1.0) : 1.0
```

### E3: purpose, mechanism, parameters, outputs_and_use, readiness

```text
avg += Y.get(ix.get(i)) * w
```

### E4: purpose, mechanism, parameters, outputs_and_use, readiness

```text
y := math.log(base) - math.log(base[ahead])
```

### E5: purpose, mechanism, parameters, outputs_and_use, readiness

```text
predLine := base + base * (math.exp(pred) - 1)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_knn_prediction](../tv_method_knn_prediction.md)
- [tv_qaaxkw1p_ai_predictive_flow_zeiierman](../tv_qaaxkw1p_ai_predictive_flow_zeiierman.md)

## Source

https://www.tradingview.com/script/qaaxkW1P-AI-Predictive-Flow-Zeiierman/

Publication ID: qaaxkW1P. Source SHA-256: e5682a5aa7073e30fba4782d9e3a534fc81a8a82bda4af7db576057c3f81c4ce. Raw-description SHA-256: 788f6f140e98ae6453e5956bf6360f726612183e81ef08c4c9fbc2c9ae711434.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
