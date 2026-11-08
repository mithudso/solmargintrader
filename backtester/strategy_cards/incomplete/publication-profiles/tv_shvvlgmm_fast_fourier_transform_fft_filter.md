---

id: tv_profile_shvvlgmm

name: "Fast Fourier Transform (FFT) Filter"

kind: research-tool

status: documentation-only

coin_test_ready: false

classification: analysis-tool

summary: "FFT Filter decomposes a selected series into frequency components, masks selected frequencies and reconstructs a filtered time-domain series. It supports either inspecting the latest window’s spectrum/reconstruction or applying the same operation in rolling windows and extracting each endpoint. The latter makes a causal windowed feature possible, while the full latest-window curve should not be mistaken for values historically available at every point."

registry_key: null

runner: null

evaluation: null

---

# Fast Fourier Transform (FFT) Filter

Version: 1.0.0. Delta: individual explanation of the complete saved publication.

**Classification:** analysis-tool. Native publication type: study. Review: independently reviewed.

## Idea and objective

FFT Filter decomposes a selected series into frequency components, masks selected frequencies and reconstructs a filtered time-domain series. It supports either inspecting the latest window’s spectrum/reconstruction or applying the same operation in rolling windows and extracting each endpoint. The latter makes a causal windowed feature possible, while the full latest-window curve should not be mistaken for values historically available at every point.

## Coin-test readiness: incomplete

No complete standalone coin-test contract or runnable coin-test implementation has been qualified for this card. Source disclosure alone does not establish that readiness.

## Source calculation and gaps

**Disclosed principal calculation.** The selected-range FFT, frequency masking, inverse reconstruction and endpoint extraction are specified; caller-selectable settings define the computation.

No blocking gap was identified for the principal computation described above. Runtime integration and performance remain separate questions.

## How it works

- Optionally standardize each input window by subtracting its mean and dividing by standard deviation, then perform FFT.
- Keep components in the selected index range, inverse-transform and display the reconstruction or use its final sample to form a rolling output.

## Outputs and intended use

- Inspect power spectrum, dominant-cycle table and selected pass components; suppress high-frequency noise or low-frequency trend according to purpose.

## Parameters and stated settings

- Source, Length, standardization, spectrum/table/row count, inverse display, rolling mode, Lowest/Highest Allowed N and filtering time range are configurable without numeric defaults. Zero-frequency mean is omitted from spectrum display.

## Failure modes and caveats

- The source warns rolling history can exceed runtime limits; analytical: finite-window spectral leakage and endpoint effects can distort cycle interpretation. Standardization discards original level.

## Missing information and implementation boundary

- FFT padding/window taper, exact power normalization, frequency symmetry handling and degenerate-standard-deviation behavior are not detailed.

## Data requirements

Required inputs: ohlcv.

Repository input-class support: available. Historical chart OHLCV supports the calculation class; exact implementation parity remains unverified.

This input review does not establish cached coverage for a market, code parity or a measured trading result.

## Evidence and interpretation

The explanation synthesizes the complete saved author description. Stated rules and settings are attributed to that description. Caveats include our analysis. No implementation, order connection or profitability result is created by this documentation card.

Quotation display normalizes line endings and omits trailing spaces/tabs. The manifest retains the exact raw quotations and offsets.

The saved script.content field is empty. Description snippets do not establish the complete Pine source.

### E1: mechanism, readiness

```text
last data point of the reconstructed​ and filtered dataset is used to build a new time series.
```

### E2: mechanism, readiness

```text
subtracting its mean and normalizing the result by the standard deviation
```

### E3: parameters, readiness

```text
does not display the 0th component
```

## Earlier catalog references

The earlier catalog associated this publication with the entries below. These links preserve that history; they do not establish exact equivalence to this complete publication or executable support.

- [tv_method_fourier_cycle](../tv_method_fourier_cycle.md)
- [tv_shvvlgmm_fast_fourier_transform_fft_filter](../tv_shvvlgmm_fast_fourier_transform_fft_filter.md)

## Source

https://www.tradingview.com/script/shVvlgMm-Fast-Fourier-Transform-FFT-Filter/

Publication ID: shVvlgMm. Source SHA-256: d96ba2a7f1a0f89dfeacb38a3be2e2892d16af409849d7b5015c6b72b0f24763. Raw-description SHA-256: e7e32084a1b60ebf4d03a50b61833986c693bfb4710e170f7274cfcb70c11308.

The all-script understanding manifest binds this card to its authored profile, exact source passages and independent review. Raw source captures remain local.
