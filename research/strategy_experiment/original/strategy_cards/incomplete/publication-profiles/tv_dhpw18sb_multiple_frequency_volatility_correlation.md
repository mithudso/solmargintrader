---

id: tv_profile_dhpw18sb

name: "Multiple Frequency Volatility Correlation"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Multiple Frequency Volatility Correlation attempts to show how volume relates to price volatility across different observation windows. Its financial purpose is to compare activity/volatility behavior at several horizons rather than judge only one lookback. Color indicates whether volatility is rising or falling, while darkness identifies shorter windows. The very brief source does not establish whether the displayed quantity is a formal correlation coefficient, a transformed score, or a set of volatility curves colored by direction. That distinction must remain unresolved instead of supplying a conventional Pearson formula from the title."

registry_key: null

runner: null

evaluation: null

---

# Multiple Frequency Volatility Correlation

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Multiple Frequency Volatility Correlation attempts to show how volume relates to price volatility across different observation windows. Its financial purpose is to compare activity/volatility behavior at several horizons rather than judge only one lookback. Color indicates whether volatility is rising or falling, while darkness identifies shorter windows. The very brief source does not establish whether the displayed quantity is a formal correlation coefficient, a transformed score, or a set of volatility curves colored by direction. That distinction must remain unresolved instead of supplying a conventional Pearson formula from the title.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Volatility estimator, correlation computation and window sequence are absent.

- Volatility estimator, correlation computation and window sequence are absent.

## How it works

- Examine volume and price-volatility relationships over multiple window lengths.
- Color rising volatility green and falling volatility purple; use darker shades for shorter windows.

## Outputs and intended use

- A multi-window colored display supplies comparative volatility context.

## Parameters and stated settings

- Window range is 2–512; exact included lengths, source and defaults are not listed.

## Failure modes and caveats

- Different windows overlap strongly, so agreement is not independent confirmation.
- Color direction is disclosed, but correlation magnitude/meaning is not.

## Missing information and implementation boundary

- Volatility estimator, correlation definition, window sequence, normalization, update timing and trade rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Disclosed volume and price-volatility inputs are compatible with OHLCV; missing calculations are algorithm gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
correlation between volume and price volatility.
```

### E2: outputs_and_use

```text
green while falling volatility is depicted with purple.
```

### E3: parameters, outputs_and_use

```text
darker == shorter in the 2 -> 512 window range.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dhpw18sb_multiple_frequency_volatility_correlation](../tv_dhpw18sb_multiple_frequency_volatility_correlation.md)

## Source

https://www.tradingview.com/script/DHPw18Sb-Multiple-Frequency-Volatility-Correlation/

Publication ID: DHPw18Sb. Source SHA-256: 98d3b39d416c4ea1a4e3606b6e09844b5ebfaa5074a626a1bf97ed66d3a31f3d. Raw-description SHA-256: e52e96ef6d3446cd752d733891d10736a8922f03c5e6a31b63ad5efcde8cc57b.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
