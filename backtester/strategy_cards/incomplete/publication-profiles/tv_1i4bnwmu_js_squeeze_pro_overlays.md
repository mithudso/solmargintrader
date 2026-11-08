---

id: tv_profile_1i4bnwmu

name: "(JS) Squeeze Pro Overlays"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Place squeeze-state context, early-event candles, channel-breach cues and customizable signal timing directly on price."

registry_key: null

runner: null

evaluation: null

---

# (JS) Squeeze Pro Overlays

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Place squeeze-state context, early-event candles, channel-breach cues and customizable signal timing directly on price.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core squeeze, early-event and momentum algorithms are delegated to a companion system without equations.

- Squeeze-tier and momentum formulas
- Early entry/exit tests
- Composite scoring weights

## How it works

- Combine four overlays from the companion Squeeze Pro system. A twenty-period SMA basis changes color by squeeze tier and shade by Bollinger expansion/contraction. Breach markers require an ongoing squeeze and a close outside Bollinger/Keltner bounds. Signal arrows combine a selectable duration event with a selectable momentum/direction condition.

## Outputs and intended use

- Monitor low/mid/high squeeze conditions, early entries/exits and potential direction arrows. Color schemes match the companion indicator; the overlay does not independently disclose every squeeze or momentum calculation.

## Parameters and stated settings

- Six palettes are available. Arrow duration defaults six dots, with twelve/end/custom alternatives; default signal direction is momentum sign. Other modes include consistent rise/fall over six bars, zero cross, basis, divergence, change sum and a composite score.

## Failure modes and caveats

- Many selectable conditions permit tuning to past examples. Undefined early-event/companion calculations prevent assuming equivalence to a commercial squeeze system or independently validated signals.

## Missing information and implementation boundary

- Bollinger/Keltner multipliers, squeeze-tier tests, early smoothing formulas, momentum/divergence algorithm and composite-score weights are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; source-code parity and complete history remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
a 20 SMA
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The default is "6 Dots"
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
The default is the same as the original "+/-"
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
"Rising/Falling" will only generate a signal if the Squeeze momentum maintains consistently over the last 6 bars.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_1i4bnwmu_js_squeeze_pro_overlays](../tv_1i4bnwmu_js_squeeze_pro_overlays.md)

## Source

https://www.tradingview.com/script/1i4BNwMU-JS-Squeeze-Pro-Overlays/

Publication ID: 1i4BNwMU. Source SHA-256: 2d66470d142a24169d73370353b305e3f8f906be46454af2c2ae6434e2d35f05. Raw-description SHA-256: 3d800940a811b1e6f3486ed845ec3a07167419ababb212ff3b81b7428604b5d4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
