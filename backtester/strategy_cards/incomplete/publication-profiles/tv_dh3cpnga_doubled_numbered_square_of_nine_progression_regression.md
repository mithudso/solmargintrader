---

id: tv_profile_dh3cpnga

name: "Doubled Numbered Square of Nine Progression | Regression"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Generate Square-of-Nine price-reference levels from a manually chosen pivot and compare their alignment with subsequent market swings."

registry_key: null

runner: null

evaluation: null

---

# Doubled Numbered Square of Nine Progression | Regression

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Generate Square-of-Nine price-reference levels from a manually chosen pivot and compare their alignment with subsequent market swings.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Square numbering mechanics, pivot confirmation, rounding, exact angle-to-cell mapping and actionable risk rules are not provided.

- Square numbering mechanics, pivot confirmation, rounding, exact angle-to-cell mapping and actionable risk rules are not provided.

## How it works

- Advance or regress a selected high/low pivot through a numbered square using a chosen price increment. Rotation/rung count changes the available levels; selected cardinal/diagonal angles project corresponding cell prices onto the chart.

## Outputs and intended use

- Plot labeled levels and pivots both on price and the square, including current close. The author recommends reviewing which angle aligns with early pivots and explicitly warns that the square does not make price form pivots.

## Parameters and stated settings

- Choose pivot, high/low basis, positive/negative increment, rotation, dimensions, angle and pivot colors. The worked example uses two hundred dollars per cell and a 315-degree diagonal.

## Failure modes and caveats

- Manual selection of angles after observing pivots introduces fitting bias. The regression-from-high mode has a disclosed delay: current close appears only after that candle closes.

## Missing information and implementation boundary

- Square numbering mechanics, pivot confirmation, rounding, exact angle-to-cell mapping and actionable risk rules are not provided.

## Data requirements

Required inputs: ohlcv, user-selected pivot and geometric settings.

Repository input-class support: available. OHLCV provides prices; the selected pivot, increment and angle are manual inputs rather than external feeds.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
progressing from the significant low at a rate of $200 per cell
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
selected the 315-degree angle on the diagonal cross
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Close price plotted on the Square of Nine in Regression "from a high pivot" takes a current candle to close
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dh3cpnga_doubled_numbered_square_of_nine_progression_regression](../tv_dh3cpnga_doubled_numbered_square_of_nine_progression_regression.md)
- [tv_method_gann](../tv_method_gann.md)
- [tv_method_support_resistance](../tv_method_support_resistance.md)

## Source

https://www.tradingview.com/script/dh3Cpnga-Doubled-Numbered-Square-of-Nine-Progression-Regression/

Publication ID: dh3Cpnga. Source SHA-256: 3695861348eae3aba1e73079ad7829b1b808e8893dcd41b07ab3df6a0b77f874. Raw-description SHA-256: de2988bca1828ec1f6483b8b0976f8d0b6a7edc498ee5cdb375cfdf2a5b4b839.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
