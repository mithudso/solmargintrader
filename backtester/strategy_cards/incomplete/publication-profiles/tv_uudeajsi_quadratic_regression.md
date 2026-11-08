---

id: tv_profile_uudeajsi

name: "Quadratic Regression"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Fit a local parabola to price and optionally extend it to explore curved trends that a straight regression cannot represent."

registry_key: null

runner: null

evaluation: null

---

# Quadratic Regression

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Fit a local parabola to price and optionally extend it to explore curved trends that a straight regression cannot represent.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** Least-squares fitting of a quadratic to the last caller-selected length of observations defines a reproducible computation; missing coefficient code and display edge behavior are nonblocking.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Minimize squared residuals for a quadratic over the chosen lookback and calculate R-squared. Draw fitted and extrapolated observations according to the offset control.

## Outputs and intended use

- Use curvature and fit statistics for exploratory trend description. A fitted turning point is a model feature, not an independently demonstrated forecast reversal.

## Parameters and stated settings

- Length, source, offset and R-squared display are configurable. Offset zero shows only extrapolation; fifty-five shows past fit only. R-squared defaults visible, and the stated drawing implementation displays at most fifty-four observations.

## Failure modes and caveats

- The author reports timestamp-drawing errors around session breaks and cautions about limited market usefulness. High in-sample R-squared is not forecast accuracy, and quadratic extrapolation can diverge quickly.

## Missing information and implementation boundary

- Coefficient calculation, time coordinate, extrapolation bounds, initialization and validated trading criteria are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supplies the described input class; this does not verify code parity, complete historical data or measured returns.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
if 0 only the extrapolated values are displayed, if 55 only the past fitted values are displayed.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Show R2 : Determine if the value of the R-squared must be displayed, by default true.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
only a maximum of 54 observations are displayed
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data

```text
This will happen when applying the indicator to symbols with session breaks
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_polynomial_regression](../tv_method_polynomial_regression.md)
- [tv_uudeajsi_quadratic_regression](../../tv_uudeajsi_quadratic_regression.md)

## Source

https://www.tradingview.com/script/uuDEajsI-Quadratic-Regression/

Publication ID: uuDEajsI. Source SHA-256: 22acb248d6438511fa74322d9f8523346a835b3df18f0e51c18d75f997423e0c. Raw-description SHA-256: fd0a098e91fdfece59ece533eeffb28df49a9c2d3ac66f01355517a2c27186f4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
