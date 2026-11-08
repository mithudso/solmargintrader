---

id: tv_profile_mk7uyofu

name: "Adjustable MA & Alternating Extremities [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Control moving-average lag and overshoot through a custom weighting kernel, then display alternating extremes or synthetic candles derived from that average."

registry_key: null

runner: null

evaluation: null

---

# Adjustable MA & Alternating Extremities [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Control moving-average lag and overshoot through a custom weighting kernel, then display alternating extremes or synthetic candles derived from that average.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The kernel is printed but conflicts with its stated special case, and extremity calculation/discretization are not supplied.

- Kernel special-case correction and normalization
- Discrete sampling grid
- Alternating-extremity calculation

## How it works

- Weight historical observations with a modified sine/power kernel whose alpha/beta controls shift lag and negative weights. Mark upper/lower extremes after price breaches them. Optional candles use the average of two prior MAs for open and separate high/low/close-input averages.

## Outputs and intended use

- Use the configurable average in crossover research or inspect band-like extreme reactions. Synthetic candles are smoothed representations and may differ from real price.

## Parameters and stated settings

- Length, extremity multiplier, candle mode, extreme visibility, lag and overshoot are inputs. Examples include length200/multiplier1 and length50 comparisons, not universal defaults.

## Failure modes and caveats

- The printed kernel sin(2π*x^alpha)*(1-x^beta) becomes zero at alpha0, yet the prose claims alpha0 yields 1-x^beta. The special case or actual parameter mapping is therefore unresolved. Negative weights can overshoot and amplify noise.

## Missing information and implementation boundary

- Discrete x-grid, kernel normalization, alpha-zero branch, extremity width/alternation recurrence and default parameters are absent.

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
sin(2πx^α)(1 - x^β)
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Using [i]α = 0
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
[pine]1 - x^β[/pine]
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Open = Average between MA(t-1) and MA(t-2)
```

### E5: purpose, mechanism, outputs_and_use, parameters, readiness

```text
length value of 200 with a multiplicative factor of 1.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_heikin_ashi](../../../strategy_research/tv_method_heikin_ashi.md)
- [tv_mk7uyofu_adjustable_ma_alternating_extremities_luxalgo](../tv_mk7uyofu_adjustable_ma_alternating_extremities_luxalgo.md)

## Source

https://www.tradingview.com/script/Mk7UyOFU-Adjustable-MA-Alternating-Extremities-LuxAlgo/

Publication ID: Mk7UyOFU. Source SHA-256: 6003345f684942164e3f1751dd8010042282f94525493925f68b578eee427dff. Raw-description SHA-256: b1e1fc3fa6f4b6c2806ee447d24d5b719eefaadc19a2f1e1f8f627791e70f790.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
