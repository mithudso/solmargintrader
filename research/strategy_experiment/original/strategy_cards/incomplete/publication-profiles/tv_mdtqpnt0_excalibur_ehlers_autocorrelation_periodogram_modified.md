---

id: tv_profile_mdtqpnt0

name: "[Excalibur] Ehlers AutoCorrelation Periodogram Modified"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: indicator

summary: "Estimate dominant price-cycle periods and expose them as dynamic inputs for other financial indicators."

registry_key: null

runner: null

evaluation: null

---

# [Excalibur] Ehlers AutoCorrelation Periodogram Modified

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** indicator. Native publication type: study. Review: independently reviewed.

## Idea and objective

Estimate dominant price-cycle periods and expose them as dynamic inputs for other financial indicators.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Partly disclosed computation.** The architecture is substantial,but modified filter,spectrum and dominant-period equations are unavailable.

- Modified roofing/ACF/Fourier equations
- SuperSmoother/power normalization
- Dominant-cycle COG selection/defaults

## How it works

- Roof-filter the source with selectable first/second-order high-pass treatment,calculate lag correlations,Fourier-decompose them, smooth spectral components with SuperSmoothers and normalize by peak power. Use a center-of-gravity calculation to estimate dominant period.

## Outputs and intended use

- Render a heatmap with period on the vertical axis,time horizontally and color as relative power. Export floating/integer,smoothed/rounded/floored cycle values for caller algorithms; a sine-wave source supports diagnostics.

## Parameters and stated settings

- Analyzed output periods span6-49. Source,roof passband/order,autocorrelation lag,Fourier smoothing,heat contrast,palette and dominant-value formatting are configurable. The code illustration clamps a caller cycle source into6-49.

## Failure modes and caveats

- Modified formulas and spectral smoothing determine timing; the claim of lower latency is unmeasured here. Adapting another indicator to the strongest recent cycle can overfit unstable market periodicity.

## Missing information and implementation boundary

- Modified roofing/ACF equations,spectral smoother coefficients,power/COG thresholds and default settings are not supplied; the source expressly says it differs materially from original Ehlers code.

## Data requirements

Required inputs: ohlcv or caller indicator source.

Repository input-class support: available. Price or another caller-supplied numerical series is sufficient; no external universe is required.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
y-axis ranges from 6 at the very bottom to 49 at the top
```

### E2: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
choose between 1st and 2nd order high-pass filters.
```

### E3: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
I decided to add SuperSmoothers.
```

### E4: purpose, mechanism, outputs_and_use, parameters, required_data, readiness

```text
Ehlers' "Center of Gravity" calculation
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_mdtqpnt0_excalibur_ehlers_autocorrelation_periodogram_modified](../tv_mdtqpnt0_excalibur_ehlers_autocorrelation_periodogram_modified.md)
- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)

## Source

https://www.tradingview.com/script/MdtqpNT0-Excalibur-Ehlers-AutoCorrelation-Periodogram-Modified/

Publication ID: MdtqpNT0. Source SHA-256: 568d2c4124ca7a82ff3396385ba12372dfa191e324910ee50f6f51e29990581c. Raw-description SHA-256: ef428a3d81ed8755d59e3d1f791860edd9f57d3740b6928d78638ecf162ca265.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
