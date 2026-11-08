---

id: tv_profile_viwa6cr8

name: "MA Sabres [LuxAlgo]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "MA Sabres identifies the first moving-average direction reversal after a sustained one-direction run and draws a curved projected shape from the preceding candle extreme. The author proposes that shape as a possible support/resistance, breakout or stop reference. It is an extrapolated geometry tied to MA length and recent volatility, not a forecast confidence envelope."

registry_key: null

runner: null

evaluation: null

---

# MA Sabres [LuxAlgo]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

MA Sabres identifies the first moving-average direction reversal after a sustained one-direction run and draws a curved projected shape from the preceding candle extreme. The author proposes that shape as a possible support/resistance, breakout or stop reference. It is an extrapolated geometry tied to MA length and recent volatility, not a forecast confidence envelope.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Caller-MA run/first-turn event is independently defined by the disclosed procedure; other missing outputs do not qualify.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Count consecutive same-direction MA bars, detect the next turn and place an origin marker at the prior high/low.
- Draw a polyline sabre whose reach uses the MA length and angle depends on prior ATR.
- Given caller MA and positive run count N,identify N consecutive strictly rising or falling MA steps;signal on first strictly opposite step. Equality breaks the run under an explicit study convention. Place marker one bar back as source describes,while recording event availability at the detecting bar. Sabre extrapolation/ATR angle excluded.

## Outputs and intended use

- Inspect the projected curve for contextual reactions or risk references, recognizing that it is offset to the previous bar after detection.
- Usable scope: Caller-MA run/first-turn event. Other advertised outputs remain subject to the listed missing information.

## Parameters and stated settings

- ATR uses fourteen bars; origin is one bar back. MA type, length and previous-trend duration are configurable; listed types include SMA/EMA/RMA/Hull/WMA/VWMA/DEMA/TEMA or off.

## Failure modes and caveats

- Analytical: back-offset drawing can imply earlier availability and the curve’s support/resistance relevance is unvalidated.

## Missing information and implementation boundary

- Sabre point/curvature equation, ATR-angle scaling, direction equality handling and numeric defaults are not supplied.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
ATR of the previous 14 bars.
```

### E2: parameters, risks, readiness

```text
drawn 1 bar back
```

### E3: mechanism, readiness

```text
tip lies as far as the user-set MA length.
```

### E4: mechanism, parameters, outputs_and_use, readiness

```text
This publication will look for a change in direction after the MA went in the same direction during x consecutive bars (settings: "[i]Reversal after x bars in the same direction[/i]").
```

### E5: mechanism, parameters, outputs_and_use, readiness

```text
Then a circle-shaped drawing will be drawn 1 bar back, at the previous high/low, dependable of the previous direction.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_viwa6cr8_ma_sabres_luxalgo](../tv_viwa6cr8_ma_sabres_luxalgo.md)

## Source

https://www.tradingview.com/script/viwa6CR8-MA-Sabres-LuxAlgo/

Publication ID: viwa6CR8. Source SHA-256: 5828dc0fe58bf30bdbbdd3cb56c41f879dd57fdc9122de67e082532461f98e33. Raw-description SHA-256: a311609aa02d08e0a10c15b3cb8231eb8d83610ffcfa90f23d20e6a16d71bdbe.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
