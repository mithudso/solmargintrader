---

id: tv_profile_er9y7zmm

name: "Log Regression Oscillator Channel [BigBeluga]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Log Regression Oscillator Channel embeds a selected momentum oscillator inside a logarithmic price-trend channel. It aims to let traders read momentum extremes in the same panel as broader trend structure, rather than switch between separate panes. The overlay is a coordinate mapping: an oscillator touching a channel edge can reflect its threshold scale, not necessarily price itself touching a statistical band."

registry_key: null

runner: null

evaluation: null

---

# Log Regression Oscillator Channel [BigBeluga]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Log Regression Oscillator Channel embeds a selected momentum oscillator inside a logarithmic price-trend channel. It aims to let traders read momentum extremes in the same panel as broader trend structure, rather than switch between separate panes. The overlay is a coordinate mapping: an oscillator touching a channel edge can reflect its threshold scale, not necessarily price itself touching a statistical band.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Regression window/channel width, oscillator lengths, scaling equation, signal-average type and precise divergence rules are missing.

- Regression window/channel width, oscillator lengths, scaling equation, signal-average type and precise divergence rules are missing.

## How it works

- Fit a logarithmic regression channel and map RSI, MFI or stochastic values into its upper/lower bounds with adjustable threshold scaling.
- Draw a yellow moving-average signal line and live oscillator readout beside the channel.

## Outputs and intended use

- Inspect mapped overbought/oversold states, signal-line turns and potential divergence while considering channel slope.

## Parameters and stated settings

- Oscillator choices are RSI/MFI/Stochastic; source illustrates RSI thresholds 70/30. Scale, midline and signal/display settings are configurable without lengths/defaults.

## Failure modes and caveats

- Analytical: remapping can visually imply a price-channel event that is really an oscillator threshold; log fitting requires positive prices.

## Missing information and implementation boundary

- Regression window/channel width, oscillator lengths, scaling equation, signal-average type and precise divergence rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this deterministic calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
RSI 70/30
```

### E2: mechanism, readiness

```text
Projects your chosen oscillator inside the channel
```

### E3: outputs_and_use, readiness

```text
Adds a yellow moving average (signal line)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_er9y7zmm_log_regression_oscillator_channel_bigbeluga](../tv_er9y7zmm_log_regression_oscillator_channel_bigbeluga.md)

## Source

https://www.tradingview.com/script/eR9y7zmm-Log-Regression-Oscillator-Channel-BigBeluga/

Publication ID: eR9y7zmm. Source SHA-256: 4bb8fc23f25200c530f91b47e382ce2189605f8c71ddbdf2a6c656bf761bebf8. Raw-description SHA-256: 421ce140e8eb859a569083eafcd32ab0d74a9272ba2b109cfd53a62baa33c8e3.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
