---

id: tv_profile_sg7vk6uh

name: "IQ Trend Beams [TradingIQ]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: drawing-tool

summary: "Maintain explicitly provisional versus committed support/resistance rails and attach trend-relative volume-density context to the currently live rails."

registry_key: null

runner: null

evaluation: null

---

# IQ Trend Beams [TradingIQ]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** drawing-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Maintain explicitly provisional versus committed support/resistance rails and attach trend-relative volume-density context to the currently live rails.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The central scoring, locking, break and lifetime/KDE models remain opaque despite explicit state semantics.

- Fit/lock/break equations and mode defaults
- Survival/maturity/remaining-length model
- Volume binning and KDE bandwidth

## How it works

- Fit forming rails to swing structure using a perceptual score and one-pole slope adjustment. Lock after sufficient geometric stillness, touches and span without channel inversion; freeze locked/broken geometry. Bin intrabar volume by rail distance, smooth it with kernel density and render calibration ribbons, density-scaled reach and peak ghost lines.

## Outputs and intended use

- Dotted/solid/restyled rails expose forming/locked/broken state. Audit badges show wick-through, modeled survival and maturity. Forecast layers refresh at the live edge without history and are explicitly model estimates rather than price predictions.

## Parameters and stated settings

- Mode sets fast/medium/slow evidence tempo; Precision controls fit window and intrabar sampling no finer than one minute. Wick-through target is ten percent. Layer/color/contrast and channel toggles are configurable.

## Failure modes and caveats

- Non-repaint geometry is an author design claim, not verified code behavior. Forming rails and live density projections change intentionally. Finite intrabar/drawing budgets constrain visible detail.

## Missing information and implementation boundary

- Perceptual score, tangency/stillness thresholds, break/survival/lifetime equations, KDE bandwidth and mode mappings are undisclosed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. OHLCV, including selected lower-timeframe history, supports the described data class. Missing computation details are separate specification gaps.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, readiness

```text
10% design target
```

### E2: purpose, mechanism, outputs_and_use, parameters, readiness

```text
Sampling is timeframe-aware and never drops below one minute.
```

### E3: purpose, mechanism, outputs_and_use, parameters, readiness

```text
kernel-density estimate
```

### E4: purpose, mechanism, outputs_and_use, parameters, readiness

```text
forecast[/b] (band, profile, ghost levels) [b]refreshes at the live edge
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_support_resistance](../tv_method_support_resistance.md)
- [tv_sg7vk6uh_iq_trend_beams_tradingiq](../tv_sg7vk6uh_iq_trend_beams_tradingiq.md)

## Source

https://www.tradingview.com/script/SG7Vk6uH-IQ-Trend-Beams-TradingIQ/

Publication ID: SG7Vk6uH. Source SHA-256: a57643a7899c1425507a7a0219ce5cdf42b0e1ff3da7267f1a87e7d53db09f0c. Raw-description SHA-256: d2759863386337cfe7a5926bdc2d64146c37aec43885f6990a9a90f033ea3c45.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
