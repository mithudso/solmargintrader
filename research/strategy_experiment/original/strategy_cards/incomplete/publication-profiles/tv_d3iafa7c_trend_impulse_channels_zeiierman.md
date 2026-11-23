---

id: tv_profile_d3iafa7c

name: "Trend Impulse Channels (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Track trends as discrete ATR-scaled steps and use a surrounding channel to visualize pauses, retests and continuation."

registry_key: null

runner: null

evaluation: null

---

# Trend Impulse Channels (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Track trends as discrete ATR-scaled steps and use a surrounding channel to visualize pauses, retests and continuation.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The custom step-state recurrence and retest computation are not disclosed beyond descriptive parameter roles.

- Step recurrence and persistence scaling
- ATR period and state initialization
- Flip/retest conditions

## How it works

- Advance an internal trend state only after price crosses an ATR-scaled trigger. Scale each step with volatility and trend persistence, cap its size and wrap it in ATR-multiplied bands. A hold period limits flips.

## Outputs and intended use

- Circular markers show new steps and triangles show upper retests in bearish or lower retests in bullish context. The author proposes trend-aligned continuation and breakout uses, without a full execution plan.

## Parameters and stated settings

- Trigger threshold, maximum step size, band multiplier, trend-hold bars and retest trend filter are adjustable; ATR period and numerical defaults are absent.

## Failure modes and caveats

- A cooling-off slope is an author hypothesis, not a universal continuation condition. Hold constraints can delay real reversals, and intrabar breaches can differ from close-confirmed signals.

## Missing information and implementation boundary

- Step growth/persistence equation, initial state, ATR length, flip mechanics and retest tests are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. The disclosed calculations use ordinary OHLCV; missing equations are specification gaps, not missing external market data.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
progresses only when price crosses a predefined ATR-scaled trigger level
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
scaling with ATR and trend persistence.
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Trend Hold (bars)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_d3iafa7c_trend_impulse_channels_zeiierman](../tv_d3iafa7c_trend_impulse_channels_zeiierman.md)
- [tv_method_market_structure](../tv_method_market_structure.md)

## Source

https://www.tradingview.com/script/d3IaFa7c-Trend-Impulse-Channels-Zeiierman/

Publication ID: d3IaFa7c. Source SHA-256: 9255a2c08268523ce6b8767978fbe367c50234315ee7eeb670a65aa9274416a3. Raw-description SHA-256: a8405fecb29ecdd9f484cc09a06c64a9ee888666b0d0b563e2f57df01c89c097.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
