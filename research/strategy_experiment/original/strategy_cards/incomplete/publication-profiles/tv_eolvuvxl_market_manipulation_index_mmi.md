---

id: tv_profile_eolvuvxl

name: "Market Manipulation Index (MMI)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Market Manipulation Index is described internally as Composite Manipulation Index, a contextual measure of price orderliness. It combines deviation from a synthetic cycle with error in a short-lag predictive model. The goal is to distinguish structured conditions from unstable conditions before choosing a strategy style. Neither component directly observes manipulative trading, so the manipulation label should not be treated as evidence about participant intent."

registry_key: null

runner: null

evaluation: null

---

# Market Manipulation Index (MMI)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Market Manipulation Index is described internally as Composite Manipulation Index, a contextual measure of price orderliness. It combines deviation from a synthetic cycle with error in a short-lag predictive model. The goal is to distinguish structured conditions from unstable conditions before choosing a strategy style. Neither component directly observes manipulative trading, so the manipulation label should not be treated as evidence about participant intent.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Sine fitting and ATR-adaptive normalization/smoothing equations are absent.

- Sine fitting and ATR-adaptive normalization/smoothing equations are absent.

## How it works

- Compare actual prices with a user-period sine wave and normalize fitting error by price variance.
- Estimate current price from two lagged closes in rolling linear regression and normalize its error by variance.
- Adapt smoothing windows using ATR, expanding during higher volatility, average the component scores and optionally smooth again.

## Outputs and intended use

- Use low values as the author’s structured-market context, high values as unstable-market context and the middle range as a caution zone.

## Parameters and stated settings

- Output is described as 0–1. Suggested thresholds are below 0.3 and above 0.7, with 0.3–0.7 transitional. Regression inputs are close[1] and close[2].

## Failure modes and caveats

- Analytical: sine mismatch or forecast error can reflect ordinary trends, shocks or model misspecification rather than manipulation.

## Missing information and implementation boundary

- Sine amplitude/phase fitting, adaptive-window formula, variance handling, clipping and defaults are not disclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, mechanism, readiness

```text
close[1] and close[2]
```

### E2: parameters, readiness

```text
scaled between 0 and 1
```

### E3: parameters, readiness

```text
CMI < 0.3
```

### E4: parameters, readiness

```text
CMI > 0.7
```

### E5: parameters, readiness

```text
CMI 0.3–0.7
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_eolvuvxl_market_manipulation_index_mmi](../tv_eolvuvxl_market_manipulation_index_mmi.md)

## Source

https://www.tradingview.com/script/EOLvUvxl-Market-Manipulation-Index-MMI/

Publication ID: EOLvUvxl. Source SHA-256: 51f922ff9633a96e27a5b9de30105614f95c27cc6d7ec81e43b205ef6dd23b9c. Raw-description SHA-256: 78eb241021cb24d93a808551d35ec9850d1b8448e5ea847dc19bcd2c3b0c07fc.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
