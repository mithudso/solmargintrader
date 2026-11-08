---

id: tv_profile_fxnublkt

name: "Revolution Volatility Bands With Range Contraction Signal VII"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Revolution Volatility Bands combines a volatility-envelope display with a contraction cue that the author relates to triangle or wedge structure. Its purpose is recognizing decreasing volatility and a developing contraction state rather than specifying a breakout direction. The description provides a visual legend but no equations, so the underlying bands cannot be reconstructed from the title or a conventional band assumption."

registry_key: null

runner: null

evaluation: null

---

# Revolution Volatility Bands With Range Contraction Signal VII

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Revolution Volatility Bands combines a volatility-envelope display with a contraction cue that the author relates to triangle or wedge structure. Its purpose is recognizing decreasing volatility and a developing contraction state rather than specifying a breakout direction. The description provides a visual legend but no equations, so the underlying bands cannot be reconstructed from the title or a conventional band assumption.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Band formula, volatility estimator, triangle/wedge detection, color/thickness thresholds and confirmation timing are missing.

- Band formula, volatility estimator, triangle/wedge detection, color/thickness thresholds and confirmation timing are missing.

## How it works

- Draw unspecified volatility bands and change price/outer-band appearance when volatility falls and contraction develops.

## Outputs and intended use

- Blue price text indicates falling overall volatility; thickening blue outer bands indicate a forming contraction signal.

## Parameters and stated settings

- The author says any chosen length can be used; no default length, band multiplier or contraction threshold is given.

## Failure modes and caveats

- Analytical: contraction can persist and a later expansion can occur in either direction; visual thickening is not an execution rule.

## Missing information and implementation boundary

- Band formula, volatility estimator, triangle/wedge detection, color/thickness thresholds and confirmation timing are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: outputs_and_use, readiness

```text
When price is written in blue, volatility overall is falling.
```

### E2: mechanism, outputs_and_use, readiness

```text
When the outer bands start to fatten up in blue, a contraction signal is forming.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_fxnublkt_revolution_volatility_bands_with_range_contraction_signal_vii](../tv_fxnublkt_revolution_volatility_bands_with_range_contraction_signal_vii.md)

## Source

https://www.tradingview.com/script/fXnublKt-Revolution-Volatility-Bands-With-Range-Contraction-Signal-VII/

Publication ID: fXnublKt. Source SHA-256: 776a9fe16699c70b0017ee180a74a6d7c1ab90060a2f0b4e67f1e5c9d5da7c50. Raw-description SHA-256: 6638fccc3e670850ae0ad46ab9ac8f7d745f301395498225b847612c14bc644d.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
