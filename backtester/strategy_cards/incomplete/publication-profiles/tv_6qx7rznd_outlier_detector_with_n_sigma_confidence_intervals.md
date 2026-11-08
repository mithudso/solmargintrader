---

id: tv_profile_6qx7rznd

name: "Outlier Detector with N-Sigma Confidence Intervals"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "This outlier detector looks for unusually large changes in a price series after detrending through first differences. It standardizes those changes and compares them with sigma-style bounds, providing an event screen rather than a directional forecast. The source itself warns that independence and constant variance are questionable assumptions in markets; its confidence language must therefore be treated as an intended statistical interpretation, not calibrated coverage."

registry_key: null

runner: null

evaluation: null

---

# Outlier Detector with N-Sigma Confidence Intervals

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

This outlier detector looks for unusually large changes in a price series after detrending through first differences. It standardizes those changes and compares them with sigma-style bounds, providing an event screen rather than a directional forecast. The source itself warns that independence and constant variance are questionable assumptions in markets; its confidence language must therefore be treated as an intended statistical interpretation, not calibrated coverage.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Studentization centering, scale estimate and difference convention remain ambiguous.

- Studentization centering, scale estimate and difference convention remain ambiguous.

## How it works

- First-difference a time series to obtain changes around zero, then studentize those observations.
- Compare standardized observations with upper and lower limits to spot unusually large candles.

## Outputs and intended use

- Inspect crossings of the confidence boundaries as outlier events; no subsequent long/short or reversal instruction is supplied.

## Parameters and stated settings

- The source discusses sample periods above 30 for a normal approximation, N=3 for its intended approximately 99% extreme screen, and N=2 for approximately 95% intervals. These are author claims.

## Failure modes and caveats

- Independence and constant variance are explicitly questioned; analytical: fat tails and changing volatility can invalidate the quoted coverage.
- The wording “99% bigger than average” is not a conventional confidence statement and is preserved as ambiguity rather than a literal size rule.

## Missing information and implementation boundary

- Exact centering, scale estimation, default lookback and whether the first difference uses the stated subtraction order are unclear.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
back periods > 30, at least
```

### E2: parameters, risks, readiness

```text
candles that are at least 99% bigger than average (using N = 3)
```

### E3: parameters, readiness

```text
N = 2 would roughly provide a 95% confidence interval.
```

### E4: risks, readiness

```text
assuming equal variance, what is also probably not true as volatility changes over time for different pairs
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_6qx7rznd_outlier_detector_with_n_sigma_confidence_intervals](../tv_6qx7rznd_outlier_detector_with_n_sigma_confidence_intervals.md)

## Source

https://www.tradingview.com/script/6QX7rznd-Outlier-Detector-with-N-Sigma-Confidence-Intervals/

Publication ID: 6QX7rznd. Source SHA-256: fb5709224e477682eaeef4f8b56be07eb21b52ced3c962a1959265b16b4d1e30. Raw-description SHA-256: 4e5366670e04a5ee79b8b2088e053c137032ad519faf26dccc9ce7b4ae2851d2.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
