---

id: tv_profile_b4jcgfrd

name: "Linear Continuation"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Linear Continuation displays an extrapolation associated with several moving averages. The complete saved description is only one sentence, establishing the display’s broad objective without enough detail to identify the average types or the continuation rule. It remains a financial indicator profile with an explicit source gap rather than a guessed regression or slope formula."

registry_key: null

runner: null

evaluation: null

---

# Linear Continuation

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Linear Continuation displays an extrapolation associated with several moving averages. The complete saved description is only one sentence, establishing the display’s broad objective without enough detail to identify the average types or the continuation rule. It remains a financial indicator profile with an explicit source gap rather than a guessed regression or slope formula.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Average definitions, linear-fit/slope method, horizon, initialization and output format are absent.

- Average definitions, linear-fit/slope method, horizon, initialization and output format are absent.

## How it works

- Show a linear continuation for moving-average series; how the linear extension is obtained is not stated.

## Outputs and intended use

- Use the displayed extensions as visual moving-average context; no trade interpretation is supplied.

## Parameters and stated settings

- The source specifies three moving averages but no lengths, types, forecast horizon or defaults.

## Failure modes and caveats

- Analytical: an undefined extrapolation cannot be treated as a reproducible or validated forecast.

## Missing information and implementation boundary

- Average definitions, linear-fit/slope method, horizon, initialization and output format are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, readiness

```text
Shows a linear continuation 3 moving averages.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_b4jcgfrd_linear_continuation](../tv_b4jcgfrd_linear_continuation.md)

## Source

https://www.tradingview.com/script/b4JCGfRD-Linear-Continuation/

Publication ID: b4JCGfRD. Source SHA-256: 359dc73b96aaaa570adc3f29d96fce528b8d1fe52348fbe5b5b62b0d3003693e. Raw-description SHA-256: cffbccefc9c3b0e4675835574a112300a76d76cc3d8de044ef4683455114456c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
