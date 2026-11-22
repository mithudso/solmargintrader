---

id: tv_profile_kjd8byiq

name: "Augmented Dickey–Fuller (ADF) mean reversion test"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This rolling ADF study tests whether a selected price sample rejects a unit-root model, providing context for considering mean-reversion strategies. It does not forecast the next trade’s direction or establish that the detected property will continue. A more negative statistic offers stronger evidence against the specified null within the chosen model, while the optional table exposes the latest result."

registry_key: null

runner: null

evaluation: null

---

# Augmented Dickey–Fuller (ADF) mean reversion test

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This rolling ADF study tests whether a selected price sample rejects a unit-root model, providing context for considering mean-reversion strategies. It does not forecast the next trade’s direction or establish that the detected property will continue. A more negative statistic offers stronger evidence against the specified null within the chosen model, while the optional table exposes the latest result.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Regression design/lag convention and finite-sample critical-value computation are not reproduced.

- Regression design/lag convention and finite-sample critical-value computation are not reproduced.

## How it works

- Fit an autoregressive test with a nonzero constant and no time trend over a rolling window, including selected lagged terms.
- Divide the estimated level-response coefficient by its standard error and compare the statistic with confidence-dependent critical values.

## Outputs and intended use

- Read the statistic relative to its critical line as a strategy-regime diagnostic; optionally show latest-bar results in an infobox.

## Parameters and stated settings

- Source, Length, Maximum lag, confidence and infobox are configurable. Confidence choices are 90%, 95% and 99%; the author suggests starting lag 0 or 1 for prices.

## Failure modes and caveats

- The source warns past stationarity may not persist and the test does not determine next-move direction; analytical: overlapping rolling tests and lag selection affect inference.

## Missing information and implementation boundary

- Critical-value implementation, finite-sample details, numerical regression method and exact default settings are not reproduced.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the described calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
confidence level (90%, 95%, or 99%)
```

### E2: parameters, readiness

```text
lag 0 or lag 1.
```

### E3: mechanism, readiness

```text
non-zero constant and zero time trend.
```

### E4: risks, readiness

```text
does not directly say whether the mean-reverting behavior will retain in the future.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_kjd8byiq_augmented_dickeyfuller_adf_mean_reversion_test](../tv_kjd8byiq_augmented_dickeyfuller_adf_mean_reversion_test.md)
- [tv_method_vix_timing](../tv_method_vix_timing.md)

## Source

https://www.tradingview.com/script/KjD8ByIQ-Augmented-Dickey-Fuller-ADF-mean-reversion-test/

Publication ID: KjD8ByIQ. Source SHA-256: 399c394ae8e9b386f6619b416ebff8272975c25dd13d1d1523cbd727c4db37be. Raw-description SHA-256: df9324bc00cda9566e20d7c025a277a14c7e590fc91ad6b2042728a635dbb940.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
