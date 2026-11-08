---

id: tv_profile_ujgvguvt

name: "Volatility Risk Premium"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Volatility Risk Premium compares VIX-implied volatility with trailing realized volatility to describe the market’s apparent insurance premium. It aims to contextualize equity risk and option strategy selection, with regime labels, historical standardization and momentum. This is a backward-looking realized-versus-forward-looking implied comparison, not an ex-post matched-horizon variance premium. The source discusses academic evidence but does not validate this implementation or make its illustrative options applications risk-free. It is calibrated for S&P 500 context and explicitly warns that other assets require recalibration."

registry_key: null

runner: null

evaluation: null

---

# Volatility Risk Premium

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Volatility Risk Premium compares VIX-implied volatility with trailing realized volatility to describe the market’s apparent insurance premium. It aims to contextualize equity risk and option strategy selection, with regime labels, historical standardization and momentum. This is a backward-looking realized-versus-forward-looking implied comparison, not an ex-post matched-horizon variance premium. The source discusses academic evidence but does not validate this implementation or make its illustrative options applications risk-free. It is calibrated for S&P 500 context and explicitly warns that other assets require recalibration.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Usable for chosen-lookback daily log-return realized volatility annualized by √252, VIX-minus-RV and default EMA5 smoothing. Missing N default, variance convention, other estimators and regime/reversal rules remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Narrow close-to-close output: compute daily log returns ln(C_t/C_(t−1)), their rolling standard deviation over chosen N daily returns, and annualize by √252. Express realized volatility on the same percent-volatility scale as VIX; raw VRP=VIX−annualized realized volatility, and displayed smoothed VRP is EMA(raw VRP,5) at the source default. Sample/population deviation convention and zero/missing observations remain parity caveats.
- Estimate realized volatility from close-return standard deviation, Parkinson high/low range or Garman-Klass OHLC, annualize and subtract from VIX.
- EMA-smooth the difference, classify regimes and compare short/long realized-volatility windows.
- Compute trailing z-score, percentile and momentum; flag extreme z-scores beginning to reverse.

## Outputs and intended use

- VRP/regime, duration, IV/RV, percentile/z-score, slope, momentum and mean-reversion state plus alerts support volatility-context research.

## Parameters and stated settings

- Close-return annualization uses √252; smoothing defaults five days; short/long windows ten/sixty days.
- Regimes described above 10, 5–10, 0–5, -2–0 and negative; last definition overlaps LOW.
- Z-score extremes ±2 relative to trailing year; momentum lookback is unspecified.
- For the usable close-return path, caller chooses realized-volatility lookback N; no main N default is stated. Five daily periods is the disclosed EMA smoothing default. Other RV estimators and regime labels are outside this narrow scope.

## Failure modes and caveats

- Regime prose overlaps for negative readings; exact boundaries are unclear.
- VIX volatility versus trailing RV is not the same as risk-neutral-minus-expected-realized variance.
- Selling volatility bears crash/tail risk and implementation costs.

## Missing information and implementation boundary

- Main RV lookback, full Garman-Klass equation, variance convention, z-score window, slope formula and exact reversal predicates are absent.

## Data requirements

Required inputs: VIX history, S&P 500-compatible underlying ohlcv.

Repository input-class support: unavailable or unresolved. Requires aligned external VIX and underlying histories; availability and maturity/horizon consistency are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
square root of 252
```

### E2: parameters, readiness

```text
default smoothing period of five days
```

### E3: parameters

```text
default ten days
```

### E4: parameters

```text
default sixty days
```

### E5: parameters

```text
exceeds ten percentage points
```

### E6: parameters

```text
between five and ten percentage points
```

### E7: parameters

```text
between zero and five percentage points
```

### E8: parameters

```text
between negative two and zero
```

### E9: parameters, mechanism, readiness

```text
Z-score below negative two and rising
```

### E10: mechanism, readiness

```text
subtract realized volatility from implied volatility.
```

### E11: mechanism, parameters, readiness

```text
It calculates the standard deviation of logarithmic daily returns over a specified lookback period, then annualizes this figure by multiplying by the square root of 252
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_covered_call](../../tv_method_covered_call.md)
- [tv_method_iron_condor](../../tv_method_iron_condor.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)
- [tv_ujgvguvt_volatility_risk_premium](../../tv_ujgvguvt_volatility_risk_premium.md)

## Source

https://www.tradingview.com/script/UJgVgUvT-Volatility-Risk-Premium/

Publication ID: UJgVgUvT. Source SHA-256: 9292be3b60d7b65f1bdc5da7e4e08b35c4308cae09b7fb06f779024a71b73854. Raw-description SHA-256: ca7eeb62b9d66b93fe6f7a60d7ee6494a247b087fb9841a4f5edae7805bba6f5.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
