---

id: tv_profile_hl1sw0i4

name: "Uhl MA Crossover System"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Uhl MA Crossover System pairs a corrected moving average with a faster corrected trend step to reduce unwanted crosses in sideways markets. Both adapt smoothing according to squared tracking error relative to rolling variance. When price is already close to the fast line, the line can hold its previous value rather than chase small movements. Larger departures increase responsiveness. The intended result is a slow/fast crossover framework whose filters adapt to conditions, but the source explicitly leaves strategy analysis to possible future work rather than supplying validated performance."

registry_key: null

runner: null

evaluation: null

---

# Uhl MA Crossover System

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Uhl MA Crossover System pairs a corrected moving average with a faster corrected trend step to reduce unwanted crosses in sideways markets. Both adapt smoothing according to squared tracking error relative to rolling variance. When price is already close to the fast line, the line can hold its previous value rather than chase small movements. Larger departures increase responsiveness. The intended result is a slow/fast crossover framework whose filters adapt to conditions, but the source explicitly leaves strategy analysis to possible future work rather than supplying validated performance.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The CTS principal output is reproducible: compare squared close/prior-output error with variance, hold below threshold and use one minus variance/error as exponential weight above it. Full CMA parity and equality/initialization conventions remain caveats.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- CMA derives exponential smoothing from squared distance between prior CMA and SMA, using rolling variance as threshold.
- CTS instead compares current close with prior CTS; below the variance threshold it holds steady.
- Above threshold, smoothing uses one minus variance divided by squared error; Mult scales the variance threshold.

## Outputs and intended use

- Fast CTS and slow CMA provide crossover and trend context.

## Parameters and stated settings

- Length controls both filters and Mult scales variance; example length is 200, not stated as default.

## Failure modes and caveats

- Threshold-driven freezing can delay recognition of a gradual trend.
- Variance/error ratios need defined zero handling and initialization.
- Reduced sideways crosses are an aim, not demonstrated performance here.

## Missing information and implementation boundary

- Exact CMA recurrence, variance convention/window, Mult/default values, crossover timing and trade-management rules are absent.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Close, SMA, rolling variance and adaptive averages are OHLCV-derived.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
1 - variance/squared error
```

### E2: mechanism

```text
CTS is equal to the precedent value of the CTS.
```

### E3: parameters

```text
length = 200
```

### E4: parameters

```text
Mult multiply the rolling variance
```

### E5: risks

```text
A possible strategy analysis could be presented in the future.
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_hl1sw0i4_uhl_ma_crossover_system](../tv_hl1sw0i4_uhl_ma_crossover_system.md)

## Source

https://www.tradingview.com/script/Hl1Sw0I4-Uhl-MA-Crossover-System/

Publication ID: Hl1Sw0I4. Source SHA-256: 629a85a31c43d55c1caec70564be9d21c651a2d708a48cc8dceca56b77af46b5. Raw-description SHA-256: d371dc79d3fd36b6d751df60431723221cdce7cb8c433d0a136112589f8b1277.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
