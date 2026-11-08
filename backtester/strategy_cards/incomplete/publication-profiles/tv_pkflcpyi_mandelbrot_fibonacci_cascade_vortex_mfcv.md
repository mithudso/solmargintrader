---

id: tv_profile_pkflcpyi

name: "Mandelbrot-Fibonacci Cascade Vortex (MFCV)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "MFCV combines a Hurst-based regime estimate, ATR-spaced bands, price-centered sinusoidal curves and Fibonacci retracement context. It aims to describe persistence, complexity and confluence across several visual components. Its fractal and sacred-geometry narrative is motivational language; the disclosed mechanics are finite-window statistics and deterministic oscillations, not proof of hidden market structure or predictive probability."

registry_key: null

runner: null

evaluation: null

---

# Mandelbrot-Fibonacci Cascade Vortex (MFCV)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

MFCV combines a Hurst-based regime estimate, ATR-spaced bands, price-centered sinusoidal curves and Fibonacci retracement context. It aims to describe persistence, complexity and confluence across several visual components. Its fractal and sacred-geometry narrative is motivational language; the disclosed mechanics are finite-window statistics and deterministic oscillations, not proof of hidden market structure or predictive probability.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Vortex and ATR cascade numeric components is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Estimate Hurst with a rescaled-range expression and derive fractal dimension as its complement to two.
- Add sine oscillations indexed by bar number to price, scaled by ATR and optional relative-volume amplification; construct ATR-based cascade envelopes.
- Combine Hurst, RSI, trend-strength, volatility-expansion and vortex-alignment conditions into fractal/cascade signals with cooldown; highlight converging levels.
- Vortex(n)=Price+sin(bar_index*0.618/Fn)*ATR(Fn)*VF; Fn=8,13,21,34,55; VF=1+(Volume/SMA(Volume,50)-1)*0.5. Cascade offset Level(i)=ATR(20)*phi^i. The source reuses phi for cascade ratio(default1.618) and vortex0.618; preserve this distinction. Fibonacci drawings update every50 bars or volatility spikes. Opaque signals/confluence excluded.

## Outputs and intended use

- Inspect regime dashboards, bands, spirals and confluence boxes. Suggested uses include trend following at high Hurst, mean reversion at low Hurst and breakout-context monitoring.
- Usable scope: Vortex and ATR cascade numeric components. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Hurst expression is H=log(R/S)/log(n/2); D=2-H. Listed spiral periods are 8/13/21/34/55; cascade ratio defaults to 1.618 and cooldown is 15 bars.
- Signal examples use Hurst >0.65 or <0.35, RSI <35 / >60 / <40 and trend-strength >0.4 or >0.3; exact Boolean grouping is not clear.
- Source ranges: cascade levels3–8,Hurst period20–200,cascade ratio1.0–3.0(default1.618),fractal memory21–233.
- Rotation Speed ranges from0.1 to2.0 and controls spiral oscillation frequency;0.618 is the source-described balanced setting. Dynamic Fibonacci drawings update every50 bars or on volatility spikes; spike logic remains unspecified.

## Failure modes and caveats

- Analytical: deterministic sine phase depends on bar indexing, Hurst estimation is noisy, and many configurable confirmations create fitting risk. Marketing confluence claims do not establish measured success.

## Missing information and implementation boundary

- Trend-strength formula, vortex direction/alignment, confluence tolerance, precise Boolean grouping, Fibonacci update rules and dimension-based sizing formula remain incomplete.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; source-code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
H = log(R/S) / log(n/2)
```

### E2: mechanism, parameters, readiness

```text
D = 2 - H
```

### E3: parameters, readiness

```text
Fn = Fibonacci number (8, 13, 21, 34, 55)
```

### E4: parameters, readiness

```text
1.618: Golden ratio (default)
```

### E5: parameters, readiness

```text
15-bar cooldown
```

### E6: parameters, mechanism, readiness

```text
Hurst > 0.65 (strong trend) AND volatility expanding
Hurst < 0.35 (mean reversion) AND RSI < 35
Trend strength > 0.4 AND vortex alignment
```

### E7: parameters, mechanism, readiness

```text
RSI > 60 AND price > SMA(50) AND bearish vortex
RSI < 40 AND price < SMA(50) AND bullish vortex
Volatility expansion AND trend strength > 0.3
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
[b]Vortex Calculation:[/b] Vortex(n) = Price + sin(bar_index × φ / Fn) × ATR(Fn) × Volume_Factor
```

### E9: mechanism, parameters, outputs_and_use, readiness

```text
Volume_Factor = 1 + (Volume/SMA(Volume,50) - 1) × 0.5
```

### E10: mechanism, parameters, outputs_and_use, readiness

```text
[b]Cascade Level Calculation:[/b] Level(i) = ATR(20) × φ^i
```

### E11: mechanism, parameters, outputs_and_use, readiness

```text
Updates every 50 bars or on volatility spikes
```

### E12: mechanism, parameters, outputs_and_use, readiness

```text
[b]Cascade Levels (3-8):[/b]
```

### E13: mechanism, parameters, outputs_and_use, readiness

```text
[b]Hurst Period (20-200):[/b]
```

### E14: mechanism, parameters, outputs_and_use, readiness

```text
[b]Cascade Ratio (1.0-3.0):[/b]
```

### E15: mechanism, parameters, outputs_and_use, readiness

```text
[b]Fractal Memory (21-233):[/b]
```

### E16: parameters, mechanism, readiness

```text
Rotation Speed (0.1-2.0)
```

### E17: parameters, mechanism, readiness

```text
0.618: Golden ratio (balanced)
```

### E18: parameters, mechanism, readiness

```text
Updates every 50 bars or on volatility spikes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_market_structure](../tv_method_market_structure.md)
- [tv_method_risk_based_sizing](../../../strategy_research/tv_method_risk_based_sizing.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_pkflcpyi_mandelbrot_fibonacci_cascade_vortex_mfcv](../tv_pkflcpyi_mandelbrot_fibonacci_cascade_vortex_mfcv.md)

## Source

https://www.tradingview.com/script/PkfLCPYI-Mandelbrot-Fibonacci-Cascade-Vortex-MFCV/

Publication ID: PkfLCPYI. Source SHA-256: cf52f39e6c9af3f4279c8dbf96079720de59cd35eb3fc2de41326c91e4bdd33b. Raw-description SHA-256: 7940aa3dfceb81e4fe0860cba3de516065ef2fefb7cd73d5a0a0f16cc8f0a0e1.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
