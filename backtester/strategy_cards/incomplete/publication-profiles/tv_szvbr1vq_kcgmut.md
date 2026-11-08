---

id: tv_profile_szvbr1vq

name: "KCGmut"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Track Keltner/center-of-gravity channel width, price location and unusual volume together in a compact subpanel."

registry_key: null

runner: null

evaluation: null

---

# KCGmut

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Track Keltner/center-of-gravity channel width, price location and unusual volume together in a compact subpanel.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** A core specification remains unresolved: Exact KeltCOG adaptation, center/outer equations, volume baseline, color thresholds and trade rules are missing.

- Exact KeltCOG adaptation, center/outer equations, volume baseline, color thresholds and trade rules are missing.

## How it works

- Use an automatically adapted KeltCOG calculation for channel and Donchian-derived center width. Plot positive/negative columns with a colored center patch positioned according to whether close is above, inside or below the center zone. Add a volume-spike histogram.

## Outputs and intended use

- Width expansion colors distinguish new center-range extremes from increased outer-channel volatility. Volume spikes are supplementary participation context; the author's whale/small-trader narrative is not directly observed by these inputs.

## Parameters and stated settings

- Lookback/channel-width controls are intentionally omitted to match companion defaults. Half outer-width percentage and full center-width percentage are plotted; blue volume spikes exceed twice recent normal, maroon signifies smaller increases.

## Failure modes and caveats

- Combined colors represent different underlying properties and can be mistaken for a single directional signal. Automatic adaptation and an undefined normal-volume baseline limit reproducibility.

## Missing information and implementation boundary

- Exact KeltCOG adaptation, center/outer equations, volume baseline, color thresholds and trade rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Ordinary OHLCV supports the disclosed calculation class; this does not establish source-code parity or verified historical coverage.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
For the channel-width-percent half of the value is used and for the COG-width-percent the whole
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data

```text
Blue spikes indicate more then twice as much volume then recently normal
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data

```text
I decided to not provide inputs to tweek lookback or channel width.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_szvbr1vq_kcgmut](../tv_szvbr1vq_kcgmut.md)

## Source

https://www.tradingview.com/script/sZvBR1Vq-KCGmut/

Publication ID: sZvBR1Vq. Source SHA-256: 2474f37c5e823718c453a71764821d443205139e2994998d0d9b775be627e00e. Raw-description SHA-256: ecd347beb18413178e3d8403101ab9c03d9ec7ecea9cae3ad6c1bbc41401c8cb.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
