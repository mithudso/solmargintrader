---

id: tv_profile_nzvqcush

name: "Detrended Rhythm Oscillator (DRO)"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "Detrended Rhythm Oscillator makes cycle inspection easier by marking turns in detrended price and labeling distances between comparable turns. It is designed to identify recurring or harmonic intervals that could tune other indicators, not to predict an exact next turning point. The extra detrended-zigzag display removes amplitude differences so timing patterns are easier to see."

registry_key: null

runner: null

evaluation: null

---

# Detrended Rhythm Oscillator (DRO)

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

Detrended Rhythm Oscillator makes cycle inspection easier by marking turns in detrended price and labeling distances between comparable turns. It is designed to identify recurring or harmonic intervals that could tune other indicators, not to predict an exact next turning point. The extra detrended-zigzag display removes amplitude differences so timing patterns are easier to see.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** DPO offset/window, zigzag reversal threshold, amplitude-detrending transform and pivot confirmation are unspecified.

- DPO offset/window, zigzag reversal threshold, amplitude-detrending transform and pivot confirmation are unspecified.

## How it works

- Detrend price with DPO, find turns with zigzag, remove zigzag amplitude and measure high-to-high/low-to-low pivot bar distances.

## Outputs and intended use

- Look for repeated distances and harmonic relationships, then use an investigated cycle estimate as another indicator’s parameter; source discourages direct turn forecasting.

## Parameters and stated settings

- Example distances cluster around 40/80/120 bars. Display options include DPO, zigzag/DRO, detrended zigzag and length labels; no numerical calculation defaults are supplied.

## Failure modes and caveats

- Analytical: zigzag turning points require later information, and apparent harmonic clusters can arise from threshold selection or chance.

## Missing information and implementation boundary

- DPO offset/window, zigzag reversal threshold, amplitude-detrending transform and pivot confirmation are unspecified.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: parameters, readiness

```text
around 40,80 and 120
```

### E2: risks, readiness

```text
should not be used to forecast the next turn per se.
```

### E3: mechanism, readiness

```text
Measure the distance from last detrended zigzag pivot (high-high / low-low)
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_nzvqcush_detrended_rhythm_oscillator_dro](../tv_nzvqcush_detrended_rhythm_oscillator_dro.md)

## Source

https://www.tradingview.com/script/nzvqcuSh-Detrended-Rhythm-Oscillator-DRO/

Publication ID: nzvqcuSh. Source SHA-256: 64633b3d63fabf481c4c8cf7a1b8c4b2202d17991d8a24fd7be15d59d4c26e5f. Raw-description SHA-256: 5098f6afa529c3f06ce85824ad44d0d870974759232cb1ae35598a2ddfa28e6a.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
