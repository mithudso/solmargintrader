---

id: tv_profile_l6nreqzb

name: "Adaptive Trend Classification: Moving Averages [InvestorUnknown]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Blend moving-average trend signals using adaptive weights tied to decayed, recency-emphasized hypothetical performance."

registry_key: null

runner: null

evaluation: null

---

# Adaptive Trend Classification: Moving Averages [InvestorUnknown]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Blend moving-average trend signals using adaptive weights tied to decayed, recency-emphasized hypothetical performance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Despite substantial equity/update snippets, missing signal/aggregation equations and the HMA/SMA contradiction prevent reproducing the complete indicator.

- Base crossover signal and family aggregation
- HMA/SMA implementation clarification
- LSMA/KAMA/defaults and numerical bounds

## How it works

- Generate a central MA and eight nearby-length variations for each average family. Compute past-signal-signed returns multiplied by exponential growth, decay accumulated hypothetical equity and floor it, then use resulting performance to weight family signals and average the blend.

## Outputs and intended use

- Plot constituent averages, color bars/arrows and alert on selected crossovers or the combined threshold. Calibration mode isolates a family; Strategy View shifts displayed entries/exits one bar and is recommended for closed-bar alerts.

## Parameters and stated settings

- Families are labeled EMA,HMA,WMA,DEMA,LSMA,KAMA. Narrow perturbations are±1/2/3/4, medium±1/2/4/6, wide±1/3/5/7. Lambda,decay,cutout,lengths,weights and long/short thresholds are adjustable; equity floor is0.25.

## Failure modes and caveats

- The printed HMA branch calls SMA, so the family label contradicts supplied code. Exponentially amplified historical returns are weighting heuristics, not actual investable equity; non-repaint statements remain unverified.

## Missing information and implementation boundary

- Base signal generation, family/equity aggregation, LSMA/KAMA functions, costs/defaults and growth overflow constraints are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The described model uses ordinary market history; missing algorithms remain specification gaps, not missing raw price data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
L4 := length + 4
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
L4 := length + 6
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
L4 := length + 7
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
else if ma_type == "HMA"
        ta.sma(source, length)
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
x := math.pow(math.e, L * (bar_index - cutout))
```

### E6: purpose, mechanism, outputs_and_use, parameters, readiness

```text
e := (e[1] * d) * (1 + a)
```

### E7: purpose, mechanism, outputs_and_use, parameters, readiness

```text
if (e < 0.25)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_l6nreqzb_adaptive_trend_classification_moving_averages_investorunknown](../tv_l6nreqzb_adaptive_trend_classification_moving_averages_investorunknown.md)

## Source

https://www.tradingview.com/script/L6NreqzB-Adaptive-Trend-Classification-Moving-Averages-InvestorUnknown/

Publication ID: L6NreqzB. Source SHA-256: 8131f109988a54b0dada3477861e573ef495591a45bce42a5057266041e91a65. Raw-description SHA-256: 72bba968f3aa8018613b2faf4b10c4f34a1508f3d7dfbbc795963a85b7692816.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
