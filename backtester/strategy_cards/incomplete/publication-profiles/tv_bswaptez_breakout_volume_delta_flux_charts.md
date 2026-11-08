---

id: tv_profile_bswaptez

name: "Breakout Volume Delta | Flux Charts"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Assess participation inside a swing-level breakout candle using lower-timeframe candle-direction volume and a split-color body overlay."

registry_key: null

runner: null

evaluation: null

---

# Breakout Volume Delta | Flux Charts

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Assess participation inside a swing-level breakout candle using lower-timeframe candle-direction volume and a split-color body overlay.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The principal pivot-break and sub-candle dominance rules are sufficiently explicit for a parameterized indicator; edge conventions must be documented during implementation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Aggregate swing-timeframe OHLC, confirm highs/lows with configurable left/right counts and retain level timestamps. On a wick or close break, sum bullish and bearish sub-candle volume into dominance percentages, optionally reject breaks below a directional threshold, and split the breakout body proportionally.

## Outputs and intended use

- Live levels extend until broken; accepted breaks lock them to the breakout bar and may show volume/percentage labels. Failed volume-filter levels are removed rather than marked broken.

## Parameters and stated settings

- Swing timeframe defaults chart timeframe. Left/right counts, lower volume interval, wick/close break, retained level count, dominance threshold, style and extension are configurable. Numerical defaults are not listed.

## Failure modes and caveats

- Sub-candle direction estimates participation rather than true bid/ask delta. Right-bar confirmation delays levels, and low-resolution sub-bars can hide conflicting flow. Failed-filter deletion changes visual history.

## Missing information and implementation boundary

- Doji-volume assignment, dominance zero denominator, simultaneous level breaks and exact threshold equality need documentation; principal swing-break/directional-volume workflow is parameterized.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary chart history supports the described input class; code parity and historical coverage remain unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bull volume sums volume from sub-candles where close is above open.
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Bear volume sums volume from sub-candles where close is below open.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Wick mode confirms a break when the wick crosses the level.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Close mode confirms a break only when the candle closes beyond the level.
```

### E5: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
If the filter fails, the affected level is removed
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_bswaptez_breakout_volume_delta_flux_charts](../tv_bswaptez_breakout_volume_delta_flux_charts.md)
- [tv_method_volume_delta](../../../strategy_research/tv_method_volume_delta.md)

## Source

https://www.tradingview.com/script/BsWaPtEz-Breakout-Volume-Delta-Flux-Charts/

Publication ID: BsWaPtEz. Source SHA-256: 57fa58a25fcd9cdc231fb6b545aca0c84801a32ea53ae0464ac04a05fbacc574. Raw-description SHA-256: 2531a65ee8541a71c063a84f7b6e2c3858eabbc2895e1c7e3a4f7bcdc78b62f4.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
