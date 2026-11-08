---

id: tv_profile_h4xuu8kn

name: "Dynamic RSI Regression Bands (Zeiierman)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Dynamic RSI Regression Bands re-anchors its regression window when RSI enters an overbought or oversold zone. It treats an extreme-momentum event as a reason to reconsider the current trend model, then grows the fitted sample until a maximum length. The purpose is event-driven channel context and rejection monitoring, not a proof that RSI extremes always introduce a new regime."

registry_key: null

runner: null

evaluation: null

---

# Dynamic RSI Regression Bands (Zeiierman)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Dynamic RSI Regression Bands re-anchors its regression window when RSI enters an overbought or oversold zone. It treats an extreme-momentum event as a reason to reconsider the current trend model, then grows the fitted sample until a maximum length. The purpose is event-driven channel context and rejection monitoring, not a proof that RSI extremes always introduce a new regime.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Regression source, raw-versus-residual deviation, minimum-sample behavior, cap-anchor semantics and exact rejection inequalities are unspecified.

- Regression source, raw-versus-residual deviation, minimum-sample behavior, cap-anchor semantics and exact rejection inequalities are unspecified.

## How it works

- Reset the channel when RSI crosses above OB or below OS, fit a custom linear regression from that point forward and cap the growing lookback.
- Add standard-deviation envelopes and mark price touching an outer band then closing back inside.

## Outputs and intended use

- Inspect reset triangles, channel slope and optional rejection circles for possible failed-breakout context.

## Parameters and stated settings

- Inputs include RSI length, OB/OS levels, maximum regression length, standard-deviation multiplier, minimum post-reset bars and marker toggles. No numeric defaults are supplied.

## Failure modes and caveats

- Analytical: repeated extremes can reset frequently, and growing-window/channel updates can change apparent rejection context before close.

## Missing information and implementation boundary

- Regression source, raw-versus-residual deviation, minimum-sample behavior, cap-anchor semantics and exact rejection inequalities are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
lookback grows with each bar after the reset, up to a user-defined max
```

### E2: mechanism, outputs_and_use, readiness

```text
price hits the upper/lower band and then closes back inside it
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_h4xuu8kn_dynamic_rsi_regression_bands_zeiierman](../tv_h4xuu8kn_dynamic_rsi_regression_bands_zeiierman.md)
- [tv_method_liquidity_sweep](../../../strategy_research/tv_method_liquidity_sweep.md)
- [tv_method_volume_footprint](../tv_method_volume_footprint.md)

## Source

https://www.tradingview.com/script/h4xuU8kN-Dynamic-RSI-Regression-Bands-Zeiierman/

Publication ID: h4xuU8kN. Source SHA-256: 5830233db93cccb62fd0a79d4a3d901084d6024b940e45b07554b0a4cbdeb707. Raw-description SHA-256: 78bf4bf6db56b90ea9a28b902da4f27e3203f3ace859a12bd5734a2bfdcd848c.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
