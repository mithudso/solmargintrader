---

id: tv_profile_yg0rpnzo

name: "Efficient Work [LucF]"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Measure directional close-to-close displacement relative to an OHLC-based estimate of distance traveled. Efficient Work interprets efficient movement as sentiment strength independent of amplitude, then compares that oscillator across chart and higher timeframes."

registry_key: null

runner: null

evaluation: null

---

# Efficient Work [LucF]

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Measure directional close-to-close displacement relative to an OHLC-based estimate of distance traveled. Efficient Work interprets efficient movement as sentiment strength independent of amplitude, then compares that oscillator across chart and higher timeframes.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Exact high/low travel equation, the full coloring conditions, ATR periods and divergence/state update edge cases are absent.

- Exact high/low travel equation, the full coloring conditions, ATR periods and divergence/state update edge cases are absent.

## How it works

- Resulting work is signed close displacement divided by estimated travel through the high and low. Averaging produces the signal; an optional external series can replace the instantaneous oscillator.
- Chart, medium and highest-timeframe values can be plotted separately or combined by weighted average, including only available components. Relative context uses Donchian extrema and saved divergence levels.
- Divergence here means disagreement between the same bar’s direction and signal direction, not conventional pivot divergence. Subsequent movement relative to that saved level determines state; selected coloring conditions must all hold, optionally filtered by short ATR exceeding long ATR.

## Outputs and intended use

- Three selectable lines, divergence dots/levels, Donchian channel, state markers/background and Data Window values support context analysis.
- Alerts and an invisible BTE Signal correspond to displayed markers, letting a separate engine evaluate entries.

## Parameters and stated settings

- Seven average choices, periods, external centerline, two higher-timeframe selection methods/multiples/fixed options, component weights and coloring filters.
- Default aggregate weights are equal; chart value repaints by default while higher-timeframe values are described as non-repainting.

## Failure modes and caveats

- OHLC does not reveal actual tick travel. The author’s repaint controls are source claims, not verified behavior.
- Aggregate composition changes when higher-timeframe history becomes available, affecting historical comparability.

## Missing information and implementation boundary

- Exact high/low travel equation, the full coloring conditions, ATR periods and divergence/state update edge cases are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical OHLCV at the chosen chart and lower/higher timeframes supplies the disclosed raw data class, subject to coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
the ratio of price movement from close to close ([i]resulting work[/i]) over the distance traveled to the high and low
```

### E2: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
A divergence is defined as a discrepancy between any bar's direction and the direction of the signal line on that same bar.
```

### E3: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The default is a repainting chart value and non-repainting higher timeframe values.
```

### E4: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
The default is equal weights for the three components
```

### E5: purpose, mechanism, parameters, outputs_and_use, risks, readiness

```text
Volatility is determined to be high when the short-term ATR is greater than the long-term ATR.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_yg0rpnzo_efficient_work_lucf](../tv_yg0rpnzo_efficient_work_lucf.md)

## Source

https://www.tradingview.com/script/yG0rpNzO-Efficient-Work-LucF/

Publication ID: yG0rpNzO. Source SHA-256: 2a1f8bca4ee853e3b67083d66f4e75fbe4f6dd4a9818950a44d0031183165696. Raw-description SHA-256: 78c7cfef0398bc888e121c1a08c5ab50c6acf9f2124b4cfd5a8cdd33905a8a16.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
