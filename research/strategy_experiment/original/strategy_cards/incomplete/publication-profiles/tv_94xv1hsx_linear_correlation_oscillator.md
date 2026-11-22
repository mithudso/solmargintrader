---

id: tv_profile_94xv1hsx

name: "Linear Correlation Oscillator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Linear Correlation Oscillator measures how closely an input series follows a linear sequence over a rolling window. As a trend gauge, a strong signed relationship indicates more consistent directional alignment than a weak relationship. The publication’s main contribution is computational: it explains that the correlation can be recovered without looping over every observation, using a normalized difference between weighted and simple moving averages. It also points to regression diagnostics and LSMA construction as related applications. These are analytical capabilities, not entry/exit instructions or proof that a linear relationship will persist."

registry_key: null

runner: null

evaluation: null

---

# Linear Correlation Oscillator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Linear Correlation Oscillator measures how closely an input series follows a linear sequence over a rolling window. As a trend gauge, a strong signed relationship indicates more consistent directional alignment than a weak relationship. The publication’s main contribution is computational: it explains that the correlation can be recovered without looping over every observation, using a normalized difference between weighted and simple moving averages. It also points to regression diagnostics and LSMA construction as related applications. These are analytical capabilities, not entry/exit instructions or proof that a linear relationship will persist.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The claimed WMA-minus-SMA correlation normalization is not given mathematically.

- The claimed WMA-minus-SMA correlation normalization is not given mathematically.

## How it works

- Obtain rolling input-versus-linear-sequence correlation from a normalized WMA-minus-SMA difference.
- Use closed-form linear-sequence mean/dispersion and cumulative-sum rolling statistics for the input.
- The approach can support rolling regression R-squared and sum of squared errors.

## Outputs and intended use

- A correlation oscillator provides trend context; related statistics can feed regression analysis.

## Parameters and stated settings

- Input series and rolling lookback are implied; no actual defaults or control list is supplied.

## Failure modes and caveats

- High correlation with time describes the fitted window and is not predictive certainty.
- Flat input series require a defined zero-variance policy, which the source omits.

## Missing information and implementation boundary

- Exact normalization, lookback, initialization, zero-variance handling, thresholds and order rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. A chart-price input series and its rolling statistics can use OHLCV data; arbitrary external series would require separate provision.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
normalized difference between a WMA and an SMA of the input series.
```

### E2: outputs_and_use

```text
rolling R-Squared of a linear regression, as well as its SSE.
```

### E3: mechanism

```text
rolling statistics for the input series can be computed using cumulative sums.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_94xv1hsx_linear_correlation_oscillator](../tv_94xv1hsx_linear_correlation_oscillator.md)

## Source

https://www.tradingview.com/script/94xv1HSx-Linear-Correlation-Oscillator/

Publication ID: 94xv1HSx. Source SHA-256: a832293ee0d85e0f09a6976f98646ffd852ed8d48b7bea32d0ecfcf5f531a771. Raw-description SHA-256: 52330c79f91ac8f59eb3f41e8d37d1841bf27881944f8d4ed4ebd329ea925df9.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
