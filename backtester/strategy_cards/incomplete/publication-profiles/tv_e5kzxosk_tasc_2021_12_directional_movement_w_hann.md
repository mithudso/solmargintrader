---

id: tv_profile_e5kzxosk

name: "TASC 2021.12 Directional Movement w/Hann"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Directional Movement w/Hann applies a Hann-window filtering stage to the conventional directional-movement components. Its purpose is to explore a smoother representation of directional behavior in the Ehlers indicator family. The source starts with PlusDM and MinusDM, applies exponential averaging, then adds a finite-impulse-response smoothing stage. This explains the computational architecture without specifying a complete trend system. In particular, the description does not state whether the plotted output is a ratio, difference or another combination, so conventional DMI/ADX formulas should not be silently substituted."

registry_key: null

runner: null

evaluation: null

---

# TASC 2021.12 Directional Movement w/Hann

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Directional Movement w/Hann applies a Hann-window filtering stage to the conventional directional-movement components. Its purpose is to explore a smoother representation of directional behavior in the Ehlers indicator family. The source starts with PlusDM and MinusDM, applies exponential averaging, then adds a finite-impulse-response smoothing stage. This explains the computational architecture without specifying a complete trend system. In particular, the description does not state whether the plotted output is a ratio, difference or another combination, so conventional DMI/ADX formulas should not be silently substituted.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** Directional-movement combination/normalization and Hann-filter coefficients are missing.

- Directional-movement combination/normalization and Hann-filter coefficients are missing.

## How it works

- Calculate classic PlusDM and MinusDM components.
- Sum/smooth directional movements in an EMA and further smooth the result with a Hann-coefficient FIR over the calculation period.

## Outputs and intended use

- A configurable-width indicator line presents the filtered directional-movement result for analysis.

## Parameters and stated settings

- Rolling calculation length and line width are adjustable; numeric defaults are absent.

## Failure modes and caveats

- Additional smoothing can suppress noise while delaying directional changes.
- Without the final combination formula, the line’s scale and threshold interpretation remain uncertain.

## Missing information and implementation boundary

- Final normalization/combination, EMA settings, Hann coefficients, initialization, default length and trade rules are missing.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Directional movements use candle high/low relationships; OHLCV supplies the disclosed data class.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
classic definition of PlusDM and MinusDM.
```

### E2: mechanism

```text
summed in an exponential moving average (EMA).
```

### E3: mechanism

```text
finite impulse response (FIR) filter using Hann window coefficients
```

### E4: parameters

```text
rolling length can be modified
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_e5kzxosk_tasc_2021_12_directional_movement_w_hann](../tv_e5kzxosk_tasc_2021_12_directional_movement_w_hann.md)

## Source

https://www.tradingview.com/script/E5KzXOsk-TASC-2021-12-Directional-Movement-w-Hann/

Publication ID: E5KzXOsk. Source SHA-256: 7c09353e9cd6019c2244156397967323297a43ae3d5ab16fd47502602e678336. Raw-description SHA-256: b4d99c3db27212833ea97a953ea5f509e844e016cc92aa465a5418dae91e228f.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
