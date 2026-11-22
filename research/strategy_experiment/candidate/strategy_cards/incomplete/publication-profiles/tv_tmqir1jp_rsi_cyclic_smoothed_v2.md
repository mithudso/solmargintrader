---

id: tv_profile_tmqir1jp

name: "RSI cyclic smoothed v2"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Cyclic Smoothed RSI adapts RSI smoothing and overbought/oversold bands to a dominant-cycle input. The aim is to reflect the market’s current rhythm rather than use fixed responsiveness and static extremes. The author proposes signal-line crossings of adaptive bands as trading cues, but the provided historical anecdote does not establish improved forecasting or measured performance."

registry_key: null

runner: null

evaluation: null

---

# RSI cyclic smoothed v2

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Cyclic Smoothed RSI adapts RSI smoothing and overbought/oversold bands to a dominant-cycle input. The aim is to reflect the market’s current rhythm rather than use fixed responsiveness and static extremes. The author proposes signal-line crossings of adaptive bands as trading cues, but the provided historical anecdote does not establish improved forecasting or measured performance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Cyclic RSI smoothing and adaptive-band equations are undisclosed.

- Cyclic RSI smoothing and adaptive-band equations are undisclosed.

## How it works

- Use dominant cycle length to set signal behavior, smoothing and cyclic memory; form adaptive upper/lower bands.

## Outputs and intended use

- Inspect crossings above or below adaptive bands as the author’s highlighted signals; their precise direction/entry-versus-exit meaning is not fully explained.

## Parameters and stated settings

- Dominant cycle is an input. The description supplies no default cycle, RSI length, vibration setting or band parameters.

## Failure modes and caveats

- Analytical: an inaccurate cycle estimate can mistune the oscillator and adaptive thresholds can move while a signal forms.

## Missing information and implementation boundary

- Cycle estimation/source, smoothing recursion, band construction, confirmation timing and complete trade management are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports this calculation class; exact code parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, parameters, readiness

```text
using the current dominant cycle length as input
```

### E2: outputs_and_use, readiness

```text
signal line crosses above or below the adaptive lower/upper bands.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_tmqir1jp_rsi_cyclic_smoothed_v2](../tv_tmqir1jp_rsi_cyclic_smoothed_v2.md)
- [xs_momentum](../../../strategy_research/xs_momentum.md)

## Source

https://www.tradingview.com/script/TmqiR1jp-RSI-cyclic-smoothed-v2/

Publication ID: TmqiR1jp. Source SHA-256: 7c03bd5a21445c7627b1c46e52571eb954e920bdd5b5332508c031278f169437. Raw-description SHA-256: c0353e55b625f2a4ae1337897755a2bb14e607d58c745762e00f182d0bd49d5e.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
