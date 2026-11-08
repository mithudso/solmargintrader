---

id: tv_profile_dxc0pi3n

name: "SwingArm ATR Trend Indicator"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "SwingArm provides a simple color-based confirmation of a perceived trend change, designed to make directional interpretation accessible to a novice. The description establishes the intended bullish/bearish display, but does not explain the actual trend calculation. The ATR language in the title is insufficient evidence for an ATR length, trailing formula or reversal threshold."

registry_key: null

runner: null

evaluation: null

---

# SwingArm ATR Trend Indicator

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

SwingArm provides a simple color-based confirmation of a perceived trend change, designed to make directional interpretation accessible to a novice. The description establishes the intended bullish/bearish display, but does not explain the actual trend calculation. The ATR language in the title is insufficient evidence for an ATR length, trailing formula or reversal threshold.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** No trend-state computation is disclosed.

- No trend-state computation is disclosed.

## How it works

- Represent the author’s detected trend state through a color-coded SwingArm display; the calculation that generates that state is not given.

## Outputs and intended use

- Green is labeled bullish/BUY and red bearish/SELL; use those colors as the author’s intended directional confirmation.

## Parameters and stated settings

- No lookback, ATR multiplier, input series or defaults appear in the description.

## Failure modes and caveats

- Analytical: an unexplained state change cannot be independently reproduced or treated as a verified execution signal.

## Missing information and implementation boundary

- The trend-change algorithm, ATR role, confirmation timing, exit semantics and risk controls are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart data supports this deterministic analysis class; exact implementation is unavailable.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, readiness

```text
The general idea of using SwingArms is to provide a visual confirmation of a trend change.
```

### E2: outputs_and_use, readiness

```text
Green for bullish (BUY)
```

### E3: outputs_and_use, readiness

```text
Red for bearish (SELL)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_dxc0pi3n_swingarm_atr_trend_indicator](../tv_dxc0pi3n_swingarm_atr_trend_indicator.md)
- [tv_method_atr_trailing](../../../strategy_research/tv_method_atr_trailing.md)

## Source

https://www.tradingview.com/script/Dxc0Pi3n-SwingArm-ATR-Trend-Indicator/

Publication ID: Dxc0Pi3n. Source SHA-256: f6bcbb9f7cda463c599973799434eb3ac5ed51bcc2f98fd938ea868ad38a896b. Raw-description SHA-256: 2918ca9eea69931851413e2cc43de7b3ec3e9b2a83b0fd26e3646751067618cd.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
