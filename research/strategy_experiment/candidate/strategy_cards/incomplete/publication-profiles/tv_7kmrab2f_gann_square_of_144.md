---

id: tv_profile_7kmrab2f

name: "Gann Square of 144"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Automate placement of Gann Square-of-144 geometry for price/time reference instead of manually moving many connected lines."

registry_key: null

runner: null

evaluation: null

---

# Gann Square of 144

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Automate placement of Gann Square-of-144 geometry for price/time reference instead of manually moving many connected lines.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The display settings are detailed but the exact geometric mapping and scale contract are not.

- Square coordinate/scale mapping
- Automatic start and candle-division rules
- Preset line definitions

## How it works

- Build a square from a start date and upper/lower prices, optionally setting the latest bar at its midpoint and deriving bounds from recent extrema. Add configurable corner connections, divisions, grid and auxiliary lines, with optional updating each new bar.

## Outputs and intended use

- Use the geometry to inspect possible trend/support-resistance relationships. The author says it is part of a broader approach and does not supply standalone entries, exits or risk controls.

## Parameters and stated settings

- Automatic bounds refer to the latest seventy-two bars or more with Candles Per Division. The square divides into nine equal parts, with optional connections through levels thirty-six and 108. Axis labels, patterns, colors and extensions are configurable.

## Failure modes and caveats

- Manually choosing a major low/high or updating the entire square changes historical alignment. The author's claims about Gann accuracy are not validated by the description.

## Missing information and implementation boundary

- Full coordinate mapping, Candles Per Division scaling, line-pattern presets, start-bar selection and endpoint rules are absent.

## Data requirements

Required inputs: ohlcv, manual start/bounds or auto-anchor settings.

Repository input-class support: available. Price history supports bounds, while geometry settings/anchors are user inputs.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
latest 72 bars (or more based on the Candles Per Division parameter)
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
divide the square into 9 equal parts
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
connecting the center to the 36 and 108 levels
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_7kmrab2f_gann_square_of_144](../tv_7kmrab2f_gann_square_of_144.md)
- [tv_method_gann](../tv_method_gann.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/7KmrAB2f-Gann-Square-of-144/

Publication ID: 7KmrAB2f. Source SHA-256: 3a55ce663875b3e30dae70a5a042786d0e8cc08ebcf4161086759e5c4f0a266a. Raw-description SHA-256: 944a5a97df9480a89a86fc5cffdf58d953b1a6c1a7b3b633c6cecf3ca58dfba8.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
