---

id: tv_profile_qetnobdk

name: "Half Causal Estimator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Half Causal Estimator smooths intraday activity using recent observations plus typical upcoming time-of-day values learned from earlier sessions. It aims to reduce the delay of a trailing average without consuming actual future observations. The future half is a seasonal expectation, not knowledge of the next bars. Suitable inputs are nonnegative activity measures such as volume, percentage true range or absolute percentage change. The source’s non-causal terminology describes a centered composite window; whether its implementation truly uses only prior-session profiles remains unverified without code."

registry_key: null

runner: null

evaluation: null

---

# Half Causal Estimator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Half Causal Estimator smooths intraday activity using recent observations plus typical upcoming time-of-day values learned from earlier sessions. It aims to reduce the delay of a trailing average without consuming actual future observations. The future half is a seasonal expectation, not knowledge of the next bars. Suitable inputs are nonnegative activity measures such as volume, percentage true range or absolute percentage change. The source’s non-causal terminology describes a centered composite window; whether its implementation truly uses only prior-session profiles remains unverified without code.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Core computation needs the listed source gaps resolved.

- Exact kernel weighting/bandwidth and historical slot-profile update rules are unspecified.

## How it works

- Store observations by time of day and estimate a historical profile for each slot.
- Combine recent actual observations with upcoming-slot historical averages in a centered composite window.
- Apply normalized Gaussian, Epanechnikov or triangular kernel weights.

## Outputs and intended use

- A responsive activity average supports volume-climax, volatility and momentum-context analysis.

## Parameters and stated settings

- Data period controls retained days; zero uses all available history.
- Filter length gives total window length×2−1; kernel width/type and line styling are configurable.
- Requires minute-based intraday charts and sufficient seasonal history.

## Failure modes and caveats

- Unexpected news and seasonal regime changes can make typical future activity misleading.
- The claim that positive inputs lack DC components is technically unclear; nonnegative series can have nonzero means.

## Missing information and implementation boundary

- Kernel formulas/bandwidth convention, profile averaging/update cutoff, session/missing-slot handling and numeric defaults are absent.

## Data requirements

Required inputs: minute-based intraday ohlcv, session/time-of-day alignment.

Repository input-class support: unavailable or unresolved. Requires repeated intraday slot coverage across sessions; suitable history and alignment are not established.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters

```text
total window size is length × 2 - 1
```

### E2: parameters

```text
0 uses all available data
```

### E3: parameters, mechanism

```text
Gaussian, Epanechnikov, and Triangular
```

### E4: mechanism, readiness

```text
historical averages for upcoming time periods from previous sessions
```

### E5: required_data

```text
minute-based intraday timeframes
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_seasonality](../tv_method_seasonality.md)
- [tv_qetnobdk_half_causal_estimator](../tv_qetnobdk_half_causal_estimator.md)

## Source

https://www.tradingview.com/script/QETnobDk-Half-Causal-Estimator/

Publication ID: QETnobDk. Source SHA-256: 5d29af638f3ec863e2e04dcd122e3b4e99b08621512f7190803df28d73546fb6. Raw-description SHA-256: 74ddd9649a35e17cad0bc3cd04f9836540997e0313ae4dfe52f5848d5aa64306.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
