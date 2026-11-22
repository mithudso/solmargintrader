---

id: tv_profile_mb0famot

name: "Advanced Fed Decision Forecast Model (AFDFM)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Combine macroeconomic categories and policy-rule context into a proposed Federal Reserve cut/hold/hike assessment."

registry_key: null

runner: null

evaluation: null

---

# Advanced Fed Decision Forecast Model (AFDFM)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine macroeconomic categories and policy-rule context into a proposed Federal Reserve cut/hold/hike assessment.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The formulas expose important probability/data inconsistencies,and core category/regime calculations are undisclosed.

- Component/regime/scale equations
- Probability normalization and series-identity correction
- Point-in-time macro release histories

## How it works

- Score Taylor-rule,labor,financial-condition,inflation-expectation,growth and liquidity components; normalize by rolling Z-scores capped at±3,apply regime multiplier and scale composite to±10. Map it to cut/hike exceedance and linear hold-score formulas.

## Outputs and intended use

- Use index/category output for discretionary rate-exposure scenarios. Source accuracy/lead-time/crisis claims have no underlying dataset or receipts here and must not be presented as measured results.

## Parameters and stated settings

- Weights are25/20/18/15/12/10percent. Regime multiplier1-1.5,hawkish/dovish thresholds±2 and hold expression100-abs(index)*15 are disclosed. Series include inflation,unemployment,GDP,rates,breakevens,NFCI,JOLTS,wages,money,loans,VIX,SPX,DXY.

## Failure modes and caveats

- The hold formula becomes negative at large allowed index values and cut/hike can exceed100; these are unnormalized scores as printed,not valid mutually exclusive probabilities. CPILFESL is labeled core PCE in the source,an instrument-identity conflict requiring verification.

## Missing information and implementation boundary

- Neutral-rate/NAIRU estimates,component aggregation,regime/tone analysis,normalization window,scale mapping and publication-vintage alignment are absent.

## Data requirements

Required inputs: FRED macroeconomic series, market series and financial-condition data, Fed communication/tone inputs.

Repository input-class support: unavailable or unresolved. Multiple external macro/market feeds and possible text-derived regime inputs are required; release timing/vintages are not supplied.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 25%
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 20%
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 18%
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 15%
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 12%
```

### E6: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Weight: 10%
```

### E7: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Z-scores bounded at ±3
```

### E8: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
regime multiplier (1.0-1.5)
```

### E9: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
P(Hold) = 100 - |AFDFM<sub>t</sub>| × 15
```

### E10: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
T<sub>hawkish</sub> = +2.0
```

### E11: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Core PCE Price Index (CPILFESL)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mb0famot_advanced_fed_decision_forecast_model_afdfm](../tv_mb0famot_advanced_fed_decision_forecast_model_afdfm.md)
- [tv_method_neural_prediction](../tv_method_neural_prediction.md)
- [tv_method_value_investing](../tv_method_value_investing.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/Mb0faMoT-Advanced-Fed-Decision-Forecast-Model-AFDFM/

Publication ID: Mb0faMoT. Source SHA-256: eeda6974d990a90b97e3ddbc87088525db5f5af983aa0cc3e27cf7011de64650. Raw-description SHA-256: a01861bdcd58f6e651356eac84334b732fcedc3937f6f41228d190069e66295f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
