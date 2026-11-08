---

id: tv_profile_bzo4yadb

name: "Per Bak Self-Organized Criticality"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: risk-tool

summary: "Per Bak SOC constructs a macro fragility score from options-tail pricing, volatility regime, credit stress and put/call positioning. It uses the sandpile analogy to motivate vulnerability to cascades, rather than predicting the size or exact timing of a crash. The concrete implementation is a weighted normalized indicator basket; its scientific narrative and forward-looking/non-repainting claims are not independently validated by the description."

registry_key: null

runner: null

evaluation: null

---

# Per Bak Self-Organized Criticality

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** risk-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Per Bak SOC constructs a macro fragility score from options-tail pricing, volatility regime, credit stress and put/call positioning. It uses the sandpile analogy to motivate vulnerability to cascades, rather than predicting the size or exact timing of a crash. The concrete implementation is a weighted normalized indicator basket; its scientific narrative and forward-looking/non-repainting claims are not independently validated by the description.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Raw tail and credit subscores is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Normalize tail, volatility, credit and positioning components with percentile ranks and absolute adjustments, then combine them with configurable weights.
- Tail uses SKEW; volatility uses VIX level/term-structure measures; credit uses LQD/HYG and TED; positioning uses put/call rank and normalized Z-score.
- C_tail=0.7*percentrank(SKEW,252)+0.3*((SKEW-115)/0.5). C_credit=0.65*percentrank(LQD/HYG,252)+0.35*(TED/0.75)*100. Require aligned source-unit inputs. No clipping/composite range is inferred; other components excluded.

## Outputs and intended use

- Read the aggregate fragility regime to contextualize exposure; the source distinguishes vulnerability from the market already falling.
- Usable scope: Raw tail and credit subscores. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- Default component weights are 0.34/0.26/0.18/0.22 and rank lookback is 252 days. Score regimes are Safe 0–39, Building 40–54, Elevated 55–69 and Critical 70–100.

## Failure modes and caveats

- Analytical: related macro proxies are not necessarily independent, source feed changes affect comparability, and heuristic thresholds do not establish calibrated crash risk.

## Missing information and implementation boundary

- VIX subcomponent formulas, positioning Z-score normalization, clipping, feed tickers/release alignment and missing-data behavior are incomplete.

## Data requirements

Required inputs: SKEW history, VIX and volatility term structure, LQD and HYG prices, TED spread, put/call ratio.

Repository input-class support: unavailable or unresolved. Multiple external macro/options/credit series are required; chart OHLCV is insufficient.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
w₁ = 0.34 (Tail Risk via SKEW)
w₂ = 0.26 (Volatility Regime via VIX term structure)
w₃ = 0.18 (Credit Stress via HYG/LQD + TED spread)
w₄ = 0.22 (Positioning Extremes via Put/Call ratio)
```

### E2: parameters, readiness

```text
252-day lookback
```

### E3: parameters, readiness

```text
Safe (0-39)
```

### E4: parameters, readiness

```text
Building (40-54)
```

### E5: parameters, readiness

```text
Elevated (55-69)
```

### E6: parameters, readiness

```text
Critical (70-100)
```

### E7: mechanism, parameters, outputs_and_use, readiness

```text
C_tail = 0.7·percentrank(SKEW, 252) + 0.3·((SKEW - 115)/0.5)
```

### E8: mechanism, parameters, outputs_and_use, readiness

```text
C_credit = 0.65·percentrank(LQD/HYG, 252) + 0.35·(TED/0.75)·100
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bzo4yadb_per_bak_self_organized_criticality](../tv_bzo4yadb_per_bak_self_organized_criticality.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/bZo4yadb-Per-Bak-Self-Organized-Criticality/

Publication ID: bZo4yadb. Source SHA-256: 1ef3cef8a2ab5ab2d3698718daa35e56bbdcd54bfc8db7877509ed6e57caa63e. Raw-description SHA-256: 92a41d51339fb0acd43dbfed8a7d7514d74c8c38a99f1ef34a163fe3eef1cd02.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
