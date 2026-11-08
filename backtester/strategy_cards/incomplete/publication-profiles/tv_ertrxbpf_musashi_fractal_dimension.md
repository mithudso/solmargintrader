---

id: tv_profile_ertrxbpf

name: "Musashi_Fractal_Dimension"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Combine several fractal-dimension estimates with momentum and volatility context to distinguish relatively trend-like from reversal-prone market behavior."

registry_key: null

runner: null

evaluation: null

---

# Musashi_Fractal_Dimension

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Combine several fractal-dimension estimates with momentum and volatility context to distinguish relatively trend-like from reversal-prone market behavior.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The principal FDI transform is explicit but its Hurst estimator and contradictory reversal band prevent reproducible regime output.

- Hurst calculation method
- Reversal interval correction
- Baseline/dot/percentile equations

## How it works

- Define FDI as two minus a Hurst estimate, compare fast and slow FDIs, and mark their crossovers. Add a Bollinger-midpoint-style baseline, optional RSI pair/divergences and Bollinger-width percentile.

## Outputs and intended use

- Colored dots mark fast/slow/baseline interactions; clusters are suggested as attractor regions. Low FDI is used to support trend following, high FDI to frame mean reversal, without specifying automatic orders.

## Parameters and stated settings

- Default fast lengths are 11,12,13 and slow21. Baseline uses21-period Bollinger bands with1.618 deviations; optional RSIs are9 and7. Trend band is1.0-1.4, random reference1.5; the printed reversal inequality is contradictory.

## Failure modes and caveats

- The source prints 1.6>=FDI>=2.0, an impossible ordinary interval; this must remain an unresolved author error. FDI is direction-agnostic, and short-window Hurst estimates can be unstable.

## Missing information and implementation boundary

- Hurst estimator, baseline input, dot direction/color mapping, percentile lookback and divergence detection are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary price/volume history supports the input class. Missing custom algorithms remain specification gaps rather than missing raw data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
FDI' = 2 - 'Hurst Exponent
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
3 fast 'FDI's (11,12,13) + 1 Slow 'FDI' (21)
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
21 period Bollinger bands with 1.618
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
1.6≥ 'FDI' ≥2.0
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
two RSI’s (9 and a 7 periods)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_ertrxbpf_musashi_fractal_dimension](../tv_ertrxbpf_musashi_fractal_dimension.md)
- [tv_method_rsi_divergence](../../tv_method_rsi_divergence.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/ertRXbpf-Musashi-Fractal-Dimension/

Publication ID: ertRXbpf. Source SHA-256: 1513b42caae43aa7ba60d2a871a20be1f5bfddca43d45cb996aa0f5326a8b437. Raw-description SHA-256: 09e9660e1818a042ed663172526bc71cc36990640a32f46e44262c35ac04d839.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
