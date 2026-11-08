---

id: tv_profile_c7z3p2xh

name: "Dynamic Money Flow"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dynamic Money Flow modifies Chaikin-style money flow to account for gaps, close-to-close movement and the fading influence of older data. It aims to confirm trends and breakouts through a volume-weighted pressure oscillator. A true-range-based accumulation/distribution component and a close-change component share volume automatically, then combine into a multiplier. Exponential averaging reduces the abrupt effect of observations leaving a simple window. The author suggests zero-line crosses and divergences alongside chart analysis, not as isolated order instructions."

registry_key: null

runner: null

evaluation: null

---

# Dynamic Money Flow

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dynamic Money Flow modifies Chaikin-style money flow to account for gaps, close-to-close movement and the fading influence of older data. It aims to confirm trends and breakouts through a volume-weighted pressure oscillator. A true-range-based accumulation/distribution component and a close-change component share volume automatically, then combine into a multiplier. Exponential averaging reduces the abrupt effect of observations leaving a simple window. The author suggests zero-line crosses and divergences alongside chart analysis, not as isolated order instructions.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core source rules need the listed gaps resolved.

- The core automatic allocation and true-range multiplier equations are unspecified.

## How it works

- Replace range-only accumulation/distribution scaling with true-range-aware logic.
- Compare consecutive closes with true range and automatically distribute volume between that component and close-within-range contribution.
- Exponentially average flowing volume and divide by averaged total volume.

## Outputs and intended use

- Zero-centered money-flow oscillator supports trend/breakout confirmation and divergence inspection.

## Parameters and stated settings

- Exponential averaging is described; no lengths, allocation controls or defaults are disclosed.

## Failure modes and caveats

- Money flow is a candle-price/volume proxy, not observed capital movement.
- Missing or zero volume/range requires defined fallback behavior.

## Missing information and implementation boundary

- Automatic volume-allocation equation, true accumulation/distribution formula, smoothing lengths and signal timing are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. True range, close changes and volume use OHLCV.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism

```text
average of flowing volume divided by average of total volume.
```

### E2: mechanism, readiness

```text
volume can be distributed between close to range comparison
```

### E3: readiness

```text
close to close comparison automatically.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_c7z3p2xh_dynamic_money_flow](../tv_c7z3p2xh_dynamic_money_flow.md)

## Source

https://www.tradingview.com/script/c7z3p2xh-Dynamic-Money-Flow/

Publication ID: c7z3p2xh. Source SHA-256: 88de870b062c3b479a60e095dbf4f653e7e510629172b823d0887bdd65ad17a7. Raw-description SHA-256: b308f31f568b1ddf67b594ce29b847298d052de0ea41ed4fa1b8f1e94907c900.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
